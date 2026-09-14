"""
01_resource_inventory.py — one row per ERCOT generation resource, from SCED.

Everything here comes from data we already hold. It is the spine the rest of
the crosswalk hangs off.

  fuel        Resource Type code (PVGR = solar, WIND, PWRSTR = storage, ...)
  qse / dme   the scheduling entity and decision-making entity codes ERCOT
              uses — the closest thing to "operator" in the raw data
  max_hsl_mw  highest available-power reading seen; a proxy for nameplate
"""

from pathlib import Path
import duckdb
duckdb.sql("SET TimeZone = 'America/Chicago'")  # ERCOT runs on Central; the Mac does not

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "crosswalk" / "staging"
OUT.mkdir(parents=True, exist_ok=True)

SCED = ROOT / "data/raw/sced_60day/gen_resource_202[56]-*.parquet"

df = duckdb.sql(f"""
    SELECT "Resource Name"                 AS resource,
           "Resource Type"                 AS fuel,
           MODE(QSE)                       AS qse,
           MODE(DME)                       AS dme,
           ROUND(MAX(HSL), 1)              AS max_hsl_mw,
           MIN("SCED Timestamp")::DATE     AS first_seen,
           MAX("SCED Timestamp")::DATE     AS last_seen,
           COUNT(*)                        AS intervals
    FROM read_parquet('{SCED}')
    WHERE "SCED Timestamp" >= '2025-08-01'
    GROUP BY 1, 2
""").df()

df.to_parquet(OUT / "resources.parquet", index=False)
print(f"{len(df):,} resources")
print(df.fuel.value_counts().head(8).to_string())
