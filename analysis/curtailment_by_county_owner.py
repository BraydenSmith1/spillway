"""
curtailment_by_county_owner.py — where and whose, using the crosswalk.

Rolls twelve months of solar/wind curtailment up to county and owner via
crosswalk/crosswalk.parquet, and reports how much of the curtailment sits
at units the crosswalk could actually place. The EIA link covers ~40% of
units, so the coverage line is the honest caveat on the rollups.
"""
from pathlib import Path
import duckdb, pandas as pd
duckdb.sql("SET TimeZone = 'America/Chicago'")

ROOT = Path(__file__).resolve().parent.parent
SCED = [str(ROOT / f"data/raw/sced_60day/gen_resource_{g}") for g in
        ("2025-0[89]*.parquet", "2025-1*.parquet", "2026-*.parquet")]
CURT = 'CASE WHEN HSL > "Base Point" + 1 THEN HSL - "Base Point" ELSE 0 END'

per = duckdb.sql(f"""
SELECT "Resource Name" AS resource,
       SUM({CURT}) / 12.0 AS curt_mwh, SUM(HSL) / 12.0 AS pot_mwh
FROM read_parquet({SCED})
WHERE "Resource Type" IN ('PVGR','WIND') AND "Telemetered Resource Status" = 'ON' AND HSL > 0
GROUP BY 1
""").df()
cw = pd.read_parquet(ROOT / "crosswalk/crosswalk.parquet")
df = per.merge(cw, on="resource", how="left")

placed = df.county.notna()
print(f"units: {len(df)}   placed in a county: {placed.sum()} ({placed.mean():.0%})")
print(f"curtailed MWh placed: {df.curt_mwh[placed].sum()/df.curt_mwh.sum():.0%} of all")
top50 = df.sort_values("curt_mwh", ascending=False).head(50)
print(f"of the 50 most-curtailed units: {top50.county.notna().sum()} have county/owner")

def roll(key, n=10):
    g = df[df[key].notna()].groupby(key).agg(units=("resource","count"),
        curt_gwh=("curt_mwh", lambda s: s.sum()/1000), pot_gwh=("pot_mwh", lambda s: s.sum()/1000))
    g["pct"] = 100*g.curt_gwh/g.pot_gwh
    return g.sort_values("curt_gwh", ascending=False).head(n).round(1)

print("\n=== Curtailment by county (linked units only), Aug 2025 - Jul 2026 ===")
print(roll("county").to_string())
print("\n=== Curtailment by owner (linked units only) ===")
print(roll("owner", 12).to_string())

print("\n=== Top 12 solar units with everything the crosswalk knows ===")
s = df[df.fuel=="PVGR"].sort_values("curt_mwh", ascending=False).head(12)
s = s.assign(curt_gwh=(s.curt_mwh/1000).round(1), pct=(100*s.curt_mwh/s.pot_mwh).round(0))
print(s[["resource","settlement_point","curt_gwh","pct","county","owner","plant_nameplate_mw","operating_year"]].to_string(index=False))
df.to_parquet(ROOT / "analysis/curtailment_by_unit.parquet", index=False)
