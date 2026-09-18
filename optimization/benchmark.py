"""
benchmark.py — how much did real ERCOT batteries earn, versus what they could have?

For each storage unit with a settlement-point link, every day in the window:

    fixed_schedule     charge 10:00-15:00, discharge 18:00-21:00, ignore prices
    persistence        optimise on yesterday's real-time prices, run today
    dam_informed       optimise on today's day-ahead prices, settle real-time
    perfect_foresight  optimise on today's real-time prices (upper bound)
    actual             the unit's real dispatch from SCED telemetry

Every strategy is settled at the unit's own real-time node price. Each day
opens at the SOC the real battery actually had, so the comparison is fair.

If ancillary-service prices are on disk, the real battery's AS revenue
(awards x clearing price) is added as `actual_total`, because a battery
that held capacity for reserves instead of arbitraging wasn't being lazy —
it was being paid for something the energy-only optimiser can't see.

    python -m optimization.benchmark --units 20 --start 2025-12-05 --end 2026-07-10
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


def run_unit(row, start, end, deg, cycles, as_prices=None, milp=True):
    bat = Battery(row.unit, p_chg=float(row.p_chg), p_dis=float(row.p_dis),
                  soc_min=float(row.soc_min), soc_max=float(row.soc_max),
                  c_deg=deg, cycles_max=cycles)
    rt = D.rt_prices(row.node, start, end)
    dam = D.dam_prices(row.node, start, end)
    act = D.actual_dispatch(row.unit, start, end)
    aw = D.as_awards(row.unit, start, end) if as_prices is not None else None

    frame = pd.concat([rt.rename("rt"), dam.rename("dam"), act], axis=1, join="inner")
    if aw is not None:
        frame = frame.join(aw, how="left").fillna({c: 0.0 for c in aw.columns})
        frame = frame.join(as_prices, how="left", rsuffix="_px").fillna(0.0)
    frame["day"] = frame.index.date
    opt = Optimiser(bat, DT, milp=milp)
    rows, yesterday_rt = [], None

    for day, g in frame.groupby("day"):
        if len(g) != N:                       # DST days, gaps: skip rather than fudge
            yesterday_rt = None
            continue
        rtp, damp = g.rt.to_numpy(), g.dam.to_numpy()
        hours = g.index.hour.to_numpy()
        soc0 = float(np.clip(g.soc_mwh.iloc[0] if not np.isnan(g.soc_mwh.iloc[0]) else bat.soc_min,
                             bat.soc_min, bat.soc_max))

        results = {
            "fixed_schedule": fixed_schedule(bat, hours, DT, soc0).net_mw,
            "dam_informed": dam_informed(opt, damp, soc0).net_mw,
            "perfect_foresight": perfect_foresight(opt, rtp, soc0).net_mw,
            "actual": g.net_mw.to_numpy(),
        }
        if yesterday_rt is not None:
            results["persistence"] = persistence(opt, yesterday_rt, soc0).net_mw

        base = dict(unit=row.unit, node=row.node, county=row.county, owner=row.owner,
                    day=pd.Timestamp(day), p_dis=bat.p_dis, capacity=bat.capacity)
        for strat, net in results.items():
            rows.append({**base, "strategy": strat,
                         "energy_rev": revenue(net, rtp, DT),
                         "cycles": float(np.sum(np.clip(net, 0, None)) * DT / bat.capacity)})

        if aw is not None:
            as_rev = 0.0
            for prod in aw.columns:
                px = f"{prod}_px" if f"{prod}_px" in g.columns else prod
                if px in g.columns and prod in g.columns:
                    as_rev += float(np.sum(DT * g[prod].to_numpy() * g[px].to_numpy()))
            rows.append({**base, "strategy": "actual_as_only", "energy_rev": as_rev, "cycles": 0.0})
        yesterday_rt = rtp
    return rows


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
    order = ["fixed_schedule", "persistence", "dam_informed", "actual", "actual_as_only",
             "actual_total", "perfect_foresight"]
    return summary.reindex([o for o in order if o in summary.index])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", type=int, default=20, help="largest N batteries by capacity")
    ap.add_argument("--start", default="2025-12-05")
    ap.add_argument("--end", default="2026-07-10")
    ap.add_argument("--deg", type=float, default=0.0, help="degradation cost, $/MWh throughput")
    ap.add_argument("--cycles", type=float, default=None, help="max full cycles per day")
    ap.add_argument("--tag", default="", help="suffix for output files")
    ap.add_argument("--lp", action="store_true",
                    help="use the LP relaxation instead of the MILP (to measure the negative-price exploit)")
    a = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    params = D.battery_params().head(a.units)
    as_px = None
    if D.as_prices_available():
        as_px = D.rt_as_prices(a.start, a.end)
        print(f"AS prices loaded: {list(as_px.columns)}")
    else:
        print("no AS prices on disk — reporting energy-only actuals")

    all_rows, t0 = [], time.time()
    for i, row in params.iterrows():
        t1 = time.time()
        rows = run_unit(row, a.start, a.end, a.deg, a.cycles, as_px, milp=not a.lp)
        all_rows += rows
        ndays = len({r["day"] for r in rows})
        print(f"[{i+1:>2}/{len(params)}] {row.unit:<16} {row.node:<16} {ndays:>3} days  "
              f"{time.time()-t1:5.1f}s", flush=True)

    df = pd.DataFrame(all_rows)
    tag = f"_{a.tag}" if a.tag else ""
    df.to_parquet(OUT / f"unit_day{tag}.parquet", index=False)
    summary = summarise(df)
    summary.to_csv(OUT / f"summary{tag}.csv")
    print(f"\n{len(params)} units, {df.day.nunique()} days, {time.time()-t0:.0f}s\n")
    print(summary.to_string())


if __name__ == "__main__":
    main()
