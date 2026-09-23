"""
07_registry.py — the crosswalk as a downloadable registry.

Two flat CSVs anyone can open, one row per unit, with everything this project
knows about it and a method column saying how each link was made:

    registry/storage.csv      every ERCOT storage unit in the ESR disclosure
    registry/generation.csv   every wind and solar unit in the SCED disclosure

Storage rows carry the benchmark's capture rates where the unit was
benchmarked; generation rows carry twelve months of measured curtailment.

    python crosswalk/07_registry.py
"""

from pathlib import Path
import sys

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from optimization import data as D  # noqa: E402

REG = ROOT / "registry"
REG.mkdir(exist_ok=True)
RES = ROOT / "optimization" / "results"

con = duckdb.connect()
con.sql("SET TimeZone = 'America/Chicago'")

# ---- storage -----------------------------------------------------------------
esr = con.sql(f"""
    SELECT "Resource Name" AS unit,
           MIN("SCED Timestamp")::DATE AS first_seen,
           MAX("SCED Timestamp")::DATE AS last_seen,
           COUNT(DISTINCT "SCED Timestamp"::DATE) AS days_seen,
           COUNT(DISTINCT CASE WHEN ABS("Base Point") > 1 THEN "SCED Timestamp"::DATE END) AS active_days,
           ROUND(AVG(CASE WHEN "Telemetered Resource Status" = 'ON' THEN 1.0 ELSE 0.0 END), 3) AS on_share,
           MODE(QSE) AS qse, MODE(DME) AS dme
    FROM read_parquet('{ROOT}/data/raw/sced_esr/esr_*.parquet')
    GROUP BY 1
""").df()
params = D.battery_params(min_power_mw=0.0, min_active_days=0)
storage = esr.merge(params, on="unit", how="left")
storage["duration_h"] = (storage.soc_max / storage.p_dis).round(2)
storage["benchmarked"] = False
for tag in ("fleet", "full"):
    p = RES / f"anatomy_units_{tag}.csv"
    if p.exists():
        an = pd.read_csv(p, index_col=0)
        storage = storage.merge(
            an[["capture all %", "capture ON %", "window %", "reserves net %", "residual %"]]
              .rename(columns={"capture all %": "capture_all_pct", "capture ON %": "capture_on_pct",
                               "window %": "gap_window_pct", "reserves net %": "gap_reserves_net_pct",
                               "residual %": "gap_dispatch_pct"}),
            left_on="unit", right_index=True, how="left")
        storage["benchmarked"] = storage.capture_all_pct.notna()
        break
cols = ["unit", "node", "p_dis", "p_chg", "soc_max", "soc_min", "duration_h", "county", "owner",
        "qse", "dme", "first_seen", "last_seen", "days_seen", "active_days", "on_share", "benchmarked",
        "capture_all_pct", "capture_on_pct", "gap_window_pct", "gap_reserves_net_pct", "gap_dispatch_pct"]
storage = storage.reindex(columns=[c for c in cols if c in storage.columns])
storage = storage.rename(columns={"p_dis": "p_dis_mw", "p_chg": "p_chg_mw", "soc_max": "soc_max_mwh", "soc_min": "soc_min_mwh"})
storage = storage.sort_values("soc_max_mwh", ascending=False)
storage.to_csv(REG / "storage.csv", index=False)

# ---- generation --------------------------------------------------------------
cw = pd.read_parquet(ROOT / "crosswalk/crosswalk.parquet")
gen = cw[cw.fuel.isin(["PVGR", "WIND"])].copy()
cu = ROOT / "analysis/curtailment_by_unit.parquet"
if cu.exists():
    c = pd.read_parquet(cu)[["resource", "curt_mwh", "pot_mwh"]]
    c["curtailed_gwh_12mo"] = (c.curt_mwh / 1000).round(2)
    c["curtailment_pct_12mo"] = (100 * c.curt_mwh / c.pot_mwh).round(1)
    gen = gen.merge(c[["resource", "curtailed_gwh_12mo", "curtailment_pct_12mo"]], on="resource", how="left")
ls = ROOT / "analysis/curtailment_lambda_split.parquet"
if ls.exists():
    s = pd.read_parquet(ls)[["resource", "congestion_pct", "oversupply_pct"]]
    gen = gen.merge(s, on="resource", how="left")
gcols = ["resource", "fuel", "settlement_point", "sp_method", "qse", "dme", "max_hsl_mw", "first_seen",
         "last_seen", "plant_name", "county", "latitude", "longitude", "owner", "utility",
         "plant_nameplate_mw", "operating_year", "eia_method", "eia_score",
         "curtailed_gwh_12mo", "curtailment_pct_12mo", "congestion_pct", "oversupply_pct"]
gen = gen.reindex(columns=[c for c in gcols if c in gen.columns]).sort_values("curtailed_gwh_12mo", ascending=False)
gen.to_csv(REG / "generation.csv", index=False)

print(f"registry/storage.csv     {len(storage):4} units   node {storage.node.notna().mean():4.0%}   "
      f"owner {storage.owner.notna().mean():4.0%}   benchmarked {int(storage.benchmarked.sum())}")
print(f"registry/generation.csv  {len(gen):4} units   node {gen.settlement_point.notna().mean():4.0%}   "
      f"owner {gen.owner.notna().mean():4.0%}")
