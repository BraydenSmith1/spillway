"""
benchmark.py — how much did real ERCOT batteries earn, versus what they could have?

For each storage unit with a settlement-point link, every day in the window:

    fixed_schedule      charge 10:00-15:00, discharge 18:00-21:00, ignore prices
    persistence         optimise on yesterday's real-time prices, run today
    dam_informed        optimise on today's day-ahead prices, settle real-time
    perfect_foresight   optimise on today's real-time prices (the ceiling)
    pf_window           the ceiling, re-solved inside the SOC window the operator
                        declared that day (daily median of Min/Max SOC)
    pf_window_awards    ... and with the unit's actual reserve awards imposed as
                        headroom and stored-energy constraints (NPRR1282-style
                        durations: Reg/RRS 0.5 h, ECRS 1 h, NonSpin 4 h)
    actual              the unit's real dispatch from SCED telemetry

The last three, read as a sequence, are the capture-gap anatomy (anatomy.py).

Every strategy is settled at the unit's own real-time node price. Each day
opens at the SOC the real battery actually had. Each unit-day carries
`on_share`, the fraction of 5-minute rows with status ON, so downstream work
can exclude commissioning (ONTEST) and outage days.

If ancillary-service prices are on disk, the real battery's AS revenue
(awards x real-time clearing price) is recorded as `actual_as_only`. NOTE:
this is priced at real-time MCPC only; day-ahead awards paid at DAM MCPC
(typically 2-4x higher) need the DAM ESR disclosure, not yet downloaded, so
AS revenue here is a lower bound.

    python -m optimization.benchmark --units 30 --start 2025-12-05 --end 2026-07-10
    python -m optimization.benchmark --all --tag fleet
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from optimization import data as D
from optimization.model import Battery
from optimization.strategies import (Optimiser, dam_informed, fixed_schedule,
                                     perfect_foresight, persistence, revenue)

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "optimization" / "results"
DT = D.DT
N = int(24 / DT)  # intervals per day

# Hours of stored energy a unit must hold per MW of each upward reserve
# product, and of headroom per MW of RegDown. From the user-specified
# NPRR1282 durations; FFR is folded into RRS here (see data.as_awards).
DURATION_H = {"regup": 0.5, "rrs": 0.5, "ecrs": 1.0, "nonspin": 4.0, "regdn": 0.5}
ON_THRESHOLD = 0.95


def award_arrays(g: pd.DataFrame, bat: Battery, wmin: float, wmax: float) -> dict:
    """Turn a day's 15-min award means into the model's four parameter arrays,
    clipped to what the unit could physically back."""
    cap = max(wmax - wmin, 1e-6)
    up = (g.regup + g.rrs + g.ecrs + g.nonspin).to_numpy()
    dn = g.regdn.to_numpy()
    ereq = (DURATION_H["regup"] * g.regup + DURATION_H["rrs"] * g.rrs
            + DURATION_H["ecrs"] * g.ecrs + DURATION_H["nonspin"] * g.nonspin).to_numpy()
    edn = (DURATION_H["regdn"] * g.regdn).to_numpy()
    return dict(up=np.clip(up, 0, bat.p_dis), dn=np.clip(dn, 0, bat.p_chg),
                ereq=np.clip(ereq, 0, 0.95 * cap), edn=np.clip(edn, 0, 0.95 * cap))


def run_unit(row, start, end, deg, cycles, as_prices=None, milp=True):
    bat = Battery(row.unit, p_chg=float(row.p_chg), p_dis=float(row.p_dis),
                  soc_min=float(row.soc_min), soc_max=float(row.soc_max),
                  c_deg=deg, cycles_max=cycles)
    rt = D.rt_prices(row.node, start, end)
    dam = D.dam_prices(row.node, start, end)
    act = D.actual_dispatch(row.unit, start, end)
    aw = D.as_awards(row.unit, start, end)

    frame = pd.concat([rt.rename("rt"), dam.rename("dam"), act], axis=1, join="inner")
    frame = frame.join(aw, how="left").fillna({c: 0.0 for c in aw.columns})
    if as_prices is not None:
        frame = frame.join(as_prices, how="left", rsuffix="_px").fillna(0.0)
    frame["day"] = frame.index.date
    opt = Optimiser(bat, DT, milp=milp)
    rows, intervals, yesterday_rt = [], [], None

    for day, g in frame.groupby("day"):
        if len(g) != N:                       # DST days, gaps: skip rather than fudge
            yesterday_rt = None
            continue
        rtp, damp = g.rt.to_numpy(), g.dam.to_numpy()
        hours = g.index.hour.to_numpy()
        soc0 = float(np.clip(g.soc_mwh.iloc[0] if not np.isnan(g.soc_mwh.iloc[0]) else bat.soc_min,
                             bat.soc_min, bat.soc_max))
        on_share = float(g.on_share.mean())

        # The operator's declared window for the day: daily median, clipped to
        # the physical envelope, falling back to the envelope if degenerate.
        wmin = float(np.nanmedian(g.decl_min)) if g.decl_min.notna().any() else bat.soc_min
        wmax = float(np.nanmedian(g.decl_max)) if g.decl_max.notna().any() else bat.soc_max
        wmin = float(np.clip(wmin, bat.soc_min, bat.soc_max))
        wmax = float(np.clip(wmax, bat.soc_min, bat.soc_max))
        if not wmax > wmin + 1.0:
            wmin, wmax = bat.soc_min, bat.soc_max
        soc0w = float(np.clip(soc0, wmin, wmax))
        awards = award_arrays(g, bat, wmin, wmax)

        pf = perfect_foresight(opt, rtp, soc0)
        pfw = opt.run(rtp, soc0w, smin=wmin, smax=wmax)
        pfwa = opt.run(rtp, soc0w, smin=wmin, smax=wmax, awards=awards)

        results = {
            "fixed_schedule": fixed_schedule(bat, hours, DT, soc0).net_mw,
            "dam_informed": dam_informed(opt, damp, soc0).net_mw,
            "perfect_foresight": pf.net_mw,
            "pf_window": pfw.net_mw,
            "pf_window_awards": pfwa.net_mw,
            "actual": g.net_mw.to_numpy(),
        }
        if yesterday_rt is not None:
            results["persistence"] = persistence(opt, yesterday_rt, soc0).net_mw

        base = dict(unit=row.unit, node=row.node, county=row.county, owner=row.owner,
                    day=pd.Timestamp(day), p_dis=bat.p_dis, capacity=bat.capacity,
                    on_share=on_share, wmin=wmin, wmax=wmax, slack_mwh=pfwa.slack_mwh,
                    up_mean_mw=float(awards["up"].mean()), dn_mean_mw=float(awards["dn"].mean()))
        for strat, net in results.items():
            rows.append({**base, "strategy": strat,
                         "energy_rev": revenue(net, rtp, DT),
                         "cycles": float(np.sum(np.clip(net, 0, None)) * DT / bat.capacity)})

        if as_prices is not None:
            as_rev = 0.0
            for prod in aw.columns:
                px = f"{prod}_px" if f"{prod}_px" in g.columns else prod
                if px in g.columns and prod in g.columns:
                    as_rev += float(np.sum(DT * g[prod].to_numpy() * g[px].to_numpy()))
            rows.append({**base, "strategy": "actual_as_only", "energy_rev": as_rev, "cycles": 0.0})

        intervals.append(pd.DataFrame({
            "unit": row.unit, "ts": g.index, "rt": rtp,
            "pf_net": pf.net_mw, "pfwa_net": pfwa.net_mw, "actual_net": g.net_mw.to_numpy(),
        }))
        yesterday_rt = rtp
    return rows, intervals


ORDER = ["fixed_schedule", "persistence", "dam_informed", "actual", "actual_as_only",
         "actual_total", "pf_window_awards", "pf_window", "perfect_foresight"]


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    """$/kW-year by strategy, plus capture rates against perfect foresight."""
    days = df.groupby("unit").day.nunique()
    kw = df.groupby("unit").p_dis.first() * 1000
    per_unit = df.pivot_table(index="unit", columns="strategy", values="energy_rev", aggfunc="sum")
    if "actual_as_only" in per_unit:
        per_unit["actual_total"] = per_unit["actual"] + per_unit["actual_as_only"]
    annual = per_unit.div(days, axis=0).mul(365).div(kw, axis=0)      # $/kW-yr
    summary = pd.DataFrame({
        "$/kW-yr (median unit)": annual.median().round(1),
        "$/kW-yr (fleet-weighted)": (per_unit.sum() / (days * kw).sum() * 365).round(1),
        "capture vs perfect (%)": (100 * per_unit.sum() / per_unit["perfect_foresight"].sum()).round(1),
    })
    return summary.reindex([o for o in ORDER if o in summary.index])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", type=int, default=20, help="largest N batteries by capacity")
    ap.add_argument("--all", action="store_true", help="every active, node-linked storage unit")
    ap.add_argument("--start", default="2025-12-05")
    ap.add_argument("--end", default="2026-07-10")
    ap.add_argument("--deg", type=float, default=0.0, help="degradation cost, $/MWh throughput")
    ap.add_argument("--cycles", type=float, default=None, help="max full cycles per day")
    ap.add_argument("--tag", default="", help="suffix for output files")
    ap.add_argument("--lp", action="store_true",
                    help="use the LP relaxation instead of the MILP (to measure the negative-price exploit)")
    a = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    params = D.battery_params()
    if not a.all:
        params = params.head(a.units)
    as_px = None
    if D.as_prices_available():
        as_px = D.rt_as_prices(a.start, a.end)
        print(f"AS prices loaded (real-time MCPC): {list(as_px.columns)}")
    else:
        print("no AS prices on disk — reporting energy-only actuals")

    all_rows, all_iv, t0 = [], [], time.time()
    for i, row in params.iterrows():
        t1 = time.time()
        try:
            rows, ivs = run_unit(row, a.start, a.end, a.deg, a.cycles, as_px, milp=not a.lp)
        except Exception as e:                 # one bad unit must not sink the fleet
            print(f"[{i+1:>3}/{len(params)}] {row.unit:<16} FAILED: {type(e).__name__}: {e}", flush=True)
            continue
        all_rows += rows; all_iv += ivs
        ndays = len({r["day"] for r in rows})
        on = np.mean([r["on_share"] >= ON_THRESHOLD for r in rows if r["strategy"] == "perfect_foresight"]) if rows else 0
        print(f"[{i+1:>3}/{len(params)}] {row.unit:<16} {row.node:<16} {ndays:>3} days  "
              f"{100*on:3.0f}% fully-ON  {time.time()-t1:5.1f}s", flush=True)

    df = pd.DataFrame(all_rows)
    tag = f"_{a.tag}" if a.tag else ""
    df.to_parquet(OUT / f"unit_day{tag}.parquet", index=False)
    pd.concat(all_iv, ignore_index=True).to_parquet(OUT / f"pf_intervals{tag}.parquet", index=False)

    summary = summarise(df)
    summary.to_csv(OUT / f"summary{tag}.csv")
    on_days = df[df.on_share >= ON_THRESHOLD]
    summary_on = summarise(on_days)
    summary_on.to_csv(OUT / f"summary{tag}_on.csv")

    print(f"\n{df.unit.nunique()} units, {df.day.nunique()} days, {time.time()-t0:.0f}s")
    print(f"\n=== all unit-days ({df[df.strategy=='perfect_foresight'].shape[0]:,}) ===")
    print(summary.to_string())
    print(f"\n=== fully-ON unit-days only (on_share >= {ON_THRESHOLD}; "
          f"{on_days[on_days.strategy=='perfect_foresight'].shape[0]:,}) ===")
    print(summary_on.to_string())


if __name__ == "__main__":
    main()
