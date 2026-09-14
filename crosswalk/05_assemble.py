"""
05_assemble.py — combine the staging tables into the crosswalk.

Output: crosswalk/crosswalk.csv (and .parquet), one row per ERCOT resource.
Every external attribute carries a method column saying how it was linked,
so any analysis can choose its own confidence threshold:

  sp_method    exact | lcpN | none          (resource -> settlement point)
  eia_method   eia_node | name_prefix | name_fuzzy | NaN   (resource -> EIA)

Run the numbered scripts in order first, or just `python crosswalk/build.py`.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STG = ROOT / "crosswalk" / "staging"

res = pd.read_parquet(STG / "resources.parquet")
sp = pd.read_parquet(STG / "resource_sp.parquet")[["resource", "sp", "sp_type", "method"]] \
       .rename(columns={"sp": "settlement_point", "method": "sp_method"})
eia = pd.read_parquet(STG / "resource_eia.parquet")[[
    "resource", "plant_code", "plant_name", "county", "latitude", "longitude",
    "operating_year", "utility", "owner", "nameplate_mw", "eia_method", "eia_score",
    "sp", "sp_from_eia",
]].rename(columns={"nameplate_mw": "plant_nameplate_mw", "sp": "sp_eia"})

cw = res.merge(sp, on="resource", how="left").merge(eia, on="resource", how="left")
# Where naming failed but EIA reports the node (GALLOWAY -> GALO_RN1), use it.
use_eia = cw.settlement_point.isna() & cw.sp_eia.notna()
cw.loc[use_eia, "settlement_point"] = cw.loc[use_eia, "sp_eia"]
cw.loc[use_eia, "sp_method"] = "eia_node"
cw = cw.drop(columns=["sp_eia", "sp_from_eia"])
cw = cw[[
    "resource", "fuel", "settlement_point", "sp_type", "sp_method",
    "qse", "dme", "max_hsl_mw", "first_seen", "last_seen",
    "plant_name", "plant_code", "county", "latitude", "longitude",
    "operating_year", "utility", "owner", "plant_nameplate_mw",
    "eia_method", "eia_score",
]].sort_values(["fuel", "resource"])

cw.to_csv(ROOT / "crosswalk" / "crosswalk.csv", index=False)
cw.to_parquet(ROOT / "crosswalk" / "crosswalk.parquet", index=False)

print(f"{len(cw):,} resources written to crosswalk/crosswalk.csv\n")
for fuel in ("PVGR", "WIND", "PWRSTR"):
    f = cw[cw.fuel == fuel]
    print(f"{fuel:7} {len(f):4}   node {f.settlement_point.notna().mean():4.0%}   "
          f"county {f.county.notna().mean():4.0%}   owner {f.owner.notna().mean():4.0%}")

print("\nTop counties by linked solar capacity (max HSL, MW):")
solar = cw[(cw.fuel == "PVGR") & cw.county.notna()]
print(solar.groupby("county").max_hsl_mw.sum().sort_values(ascending=False).head(8).round(0).to_string())
