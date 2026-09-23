"""
price_setting.py — on which intervals was the unit's own offer the price?

The perfect-foresight ceiling treats the battery as a price-taker: it can
dispatch anything and the price does not move. That is false whenever the
unit's own offer curve is what SCED cleared against — the unit was the
marginal resource and any different dispatch would have produced a different
LMP. On those intervals the ceiling is not credible, and the anatomy flags
them rather than pretending otherwise.

Test, per 5-minute SCED run:
    offer = the unit's SCED1 energy offer curve, interpolated at its Base Point
            (discharge side for BP > 0, charge side for BP < 0)
    flagged if  status == ON  and  Proxy Extension != Yes  and  |BP| > 1 MW
                and  |LMP_5min - offer| < $1

Rolled up to 15-minute settlement intervals ("any flagged run in the
interval") and joined to the perfect-foresight dispatch, so the output is the
share of ceiling revenue earned on intervals where the ceiling assumption
does not hold.

    python -m optimization.price_setting --tag fleet
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from optimization import data as D

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "optimization" / "results"
DT = D.DT
TOL_PRICE = 1.0     # $/MWh
TOL_MW = 1.0        # MW — below this the unit is idle, not dispatched


def offer_at(bp: float, curve) -> tuple[float, bool]:
    """Offer price at Base Point, and whether BP sits at the end of that side
    of the curve (a capacity limit rather than an interior point)."""
    if curve is None or bp is None or not np.isfinite(bp) or abs(bp) <= TOL_MW:
        return np.nan, False
    try:
        pts = np.asarray([list(p) for p in curve], dtype=float)
    except (TypeError, ValueError):
        return np.nan, False
    if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) < 2:
        return np.nan, False
    side = pts[:, 0] >= 0 if bp > 0 else pts[:, 0] <= 0
    mw, pr = pts[side, 0], pts[side, 1]
    if len(mw) < 2:
        return np.nan, False
    order = np.argsort(mw, kind="stable")
    mw, pr = mw[order], pr[order]
    if bp < mw[0] - TOL_MW or bp > mw[-1] + TOL_MW:
        return np.nan, False
    at_limit = bool(abs(bp - mw[-1]) <= TOL_MW if bp > 0 else abs(bp - mw[0]) <= TOL_MW)
    return float(np.interp(bp, mw, pr)), at_limit


def flag_unit(unit: str, node: str, start: str, end: str) -> pd.DataFrame:
    ec = D.esr_curves(unit, start, end)
    lmp = D.lmp_5min(node, start, end)
    df = ec.join(lmp, how="inner")
    if df.empty:
        return df
    res = [offer_at(bp, c) for bp, c in zip(df.bp.to_numpy(), df.curve.to_numpy())]
    df["offer"] = [r[0] for r in res]
    df["at_limit"] = [r[1] for r in res]
    df["flag"] = ((df.status == "ON") & (df.proxy.astype(str).str.upper() != "YES")
                  & df.offer.notna() & ((df.lmp - df.offer).abs() < TOL_PRICE))
    df["flag_interior"] = df.flag & ~df.at_limit
    return df[["bp", "lmp", "offer", "at_limit", "flag", "flag_interior"]]


def rollup(unit: str, five: pd.DataFrame, iv: pd.DataFrame) -> pd.DataFrame:
    """15-minute intervals: any flagged run -> flagged interval; join PF dispatch."""
    five = five.copy()
    five["ts15"] = five.index.floor("15min")
    q = five.groupby("ts15").agg(flag=("flag", "any"), flag_interior=("flag_interior", "any"),
                                 n5=("flag", "size"), n5_flag=("flag", "sum"))
    j = iv[iv.unit == unit].set_index("ts").join(q, how="left")
    j[["flag", "flag_interior"]] = j[["flag", "flag_interior"]].fillna(False).astype(bool)
    j["pf_rev_abs"] = (DT * j.rt * j.pf_net).abs()
    j["pfwa_rev_abs"] = (DT * j.rt * j.pfwa_net).abs()
    j["day"] = j.index.normalize()
    g = j.groupby("day")
    out = pd.DataFrame({
        "intervals": g.size(),
        "flagged": g.flag.sum(),
        "flagged_interior": g.flag_interior.sum(),
        "pf_rev_abs": g.pf_rev_abs.sum(),
        "pf_rev_abs_flagged": j[j.flag].groupby("day").pf_rev_abs.sum(),
        "pfwa_rev_abs": g.pfwa_rev_abs.sum(),
        "pfwa_rev_abs_flagged": j[j.flag].groupby("day").pfwa_rev_abs.sum(),
    }).fillna(0.0)
    out.insert(0, "unit", unit)
    return out.reset_index()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="full")
    ap.add_argument("--start", default="2025-12-05")
    ap.add_argument("--end", default="2026-07-10")
    a = ap.parse_args()

    ud = pd.read_parquet(RES / f"unit_day_{a.tag}.parquet")
    iv = pd.read_parquet(RES / f"pf_intervals_{a.tag}.parquet")
    nodes = ud.drop_duplicates("unit").set_index("unit").node
    rows, t0 = [], time.time()
    for i, (unit, node) in enumerate(nodes.items(), 1):
        t1 = time.time()
        five = flag_unit(unit, node, a.start, a.end)
        if five.empty:
            print(f"[{i:>3}/{len(nodes)}] {unit:<16} no LMP/curve overlap", flush=True)
            continue
        r = rollup(unit, five, iv)
        rows.append(r)
        share = 100 * r.pf_rev_abs_flagged.sum() / max(r.pf_rev_abs.sum(), 1e-9)
        print(f"[{i:>3}/{len(nodes)}] {unit:<16} {len(five):>6} runs  "
              f"{100*five.flag.mean():4.1f}% runs flagged  "
              f"{share:4.1f}% of |PF rev| on flagged intervals  {time.time()-t1:4.1f}s", flush=True)
    out = pd.concat(rows, ignore_index=True)
    out.to_parquet(RES / f"price_setting_{a.tag}.parquet", index=False)
    fleet = 100 * out.pf_rev_abs_flagged.sum() / out.pf_rev_abs.sum()
    print(f"\n{out.unit.nunique()} units, {time.time()-t0:.0f}s   fleet: {fleet:.1f}% of |PF revenue| "
          f"on intervals where the unit's own offer set the LMP")


if __name__ == "__main__":
    main()
