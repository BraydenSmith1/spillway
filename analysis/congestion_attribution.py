"""
congestion_attribution.py — congestion or oversupply? and which line?

Curtailment has two causes: a transmission line is full (congestion) or the
region simply has too much power (oversupply). Only the first is tied to a
place, so only the first can be attributed to specific grid infrastructure.

Shadow prices tell us which constraints were binding at every SCED run. This
joins them to each unit's curtailed intervals on the exact SCED timestamp:

  * share of curtailed MWh during which ANY constraint was binding
  * for each unit, the constraint whose binding intervals overlap its
    curtailment far more than chance ("lift") — a proxy for causation, since
    we do not have shift factors

Jan-Jun 2026, wind and solar with a settlement-point link.
"""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
CW = ROOT / "crosswalk/crosswalk.parquet"
SCED = ROOT / "data/raw/sced_60day/gen_resource_2026-0[1-6]-*.parquet"
SH = ROOT / "data/raw/shadow_prices/shadow_prices_2026-0[1-6].parquet"

con = duckdb.connect()
con.sql("SET TimeZone = 'America/Chicago'")
# SCED stamps are tz-aware; shadow-price stamps are naive Central strings.
# Bring both to naive Central minutes so the join is exact.
con.sql(f"""
CREATE TABLE curt AS
SELECT "Resource Name" AS resource, "Resource Type" AS fuel,
       date_trunc('minute', ("SCED Timestamp" AT TIME ZONE 'America/Chicago')) AS ts,
       (HSL - "Base Point") / 12.0 AS curt_mwh
FROM read_parquet('{SCED}')
WHERE "Telemetered Resource Status" = 'ON' AND HSL > 0 AND HSL > "Base Point" + 1
  AND "Resource Type" IN ('PVGR','WIND')
  AND "Resource Name" IN (SELECT resource FROM '{CW}' WHERE settlement_point IS NOT NULL)
""")
con.sql(f"""
CREATE TABLE bind AS
SELECT DISTINCT date_trunc('minute', CAST(SCEDTimestamp AS TIMESTAMP)) AS ts, constraintName AS cname
FROM read_parquet('{SH}') WHERE shadowPrice > 0
""")
con.sql("CREATE TABLE any_bind AS SELECT DISTINCT ts FROM bind")

print("=== Share of curtailed MWh while at least one constraint was binding ===")
print(con.sql("""
SELECT fuel,
       ROUND(SUM(curt_mwh)) AS curt_mwh,
       ROUND(100.0 * SUM(curt_mwh) FILTER (WHERE ab.ts IS NOT NULL) / SUM(curt_mwh), 1) AS pct_with_binding
FROM curt LEFT JOIN any_bind ab USING (ts) GROUP BY 1
""").df().to_string(index=False))

print("\n=== For the top curtailed solar units: most-implicated constraint (by lift) ===")
print(con.sql("""
WITH base AS (SELECT cname, COUNT(*) AS n_bind FROM bind GROUP BY 1),
     nts AS (SELECT COUNT(DISTINCT ts) AS n FROM any_bind),
     per AS (
       SELECT c.resource, b.cname,
              SUM(c.curt_mwh) AS mwh_with,
              COUNT(DISTINCT c.ts) AS n_overlap
       FROM curt c JOIN bind b USING (ts) GROUP BY 1,2),
     tot AS (SELECT resource, SUM(curt_mwh) AS mwh, COUNT(DISTINCT ts) AS n_curt FROM curt GROUP BY 1),
     scored AS (
       SELECT p.resource, p.cname,
              ROUND(100.0 * p.mwh_with / t.mwh, 0) AS pct_of_curt,
              ROUND((1.0*p.n_overlap/t.n_curt) / (1.0*base.n_bind/(SELECT n FROM nts)), 1) AS lift,
              t.mwh
       FROM per p JOIN tot t USING (resource) JOIN base USING (cname)
       WHERE p.n_overlap >= 200)
SELECT resource, cname AS constraint, pct_of_curt, lift
FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY resource ORDER BY lift DESC, pct_of_curt DESC) rn FROM scored)
WHERE rn = 1 AND resource IN (SELECT resource FROM tot ORDER BY mwh DESC LIMIT 12)
ORDER BY lift DESC
""").df().to_string(index=False))
