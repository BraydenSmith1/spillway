"""
curtailment_lambda_split.py — oversupply or congestion? Exactly, per curtailed MWh.

ERCOT's nodal price is  LMP = System Lambda + congestion component  — there is
no marginal-loss term. System Lambda is the energy price for the grid as a
whole; the congestion component is what this node adds or subtracts because
of full lines between it and everyone else. Both are public. So for every
curtailed 5-minute interval at a unit's own node, one subtraction settles the
question the brief's §1 asks:

    lambda <= 0              system-wide OVERSUPPLY: Texas as a whole had more
                             power than it wanted; the node was not special
    lambda > 0, LMP < 0      CONGESTION: the grid wanted power, this node was
                             stuck behind a full line (LMP - lambda < 0)
    lambda > 0, LMP >= 0     OTHER: curtailed at a positive price — local
                             limits, ramping, or operator choice

This replaces the "lift" heuristic in FINDINGS §3, which could only say which
constraint's binding intervals *coincided* with a unit's curtailment. It does
not need shift factors: shift factors apportion congestion across named
lines; the dollar split between oversupply and congestion needs only lambda.

Window: Sep 2025 - Jul 2026, where SCED disclosure, nodal LMP and lambda all
exist. Interval length is derived per day (15-min SCED disclosure before
RTC+B, 5-min after) — see analysis/interval_hours.py.

    python analysis/curtailment_lambda_split.py
"""

from pathlib import Path
import sys

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.interval_hours import interval_hours_sql  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "analysis"
START, END = "2025-09-01", "2026-07-11"
SCED = [str(RAW / f"sced_60day/gen_resource_{g}") for g in
        ("2025-09*.parquet", "2025-1*.parquet", "2026-*.parquet")]
LMP = str(RAW / "lmp_resource_nodes/lmp_resource_nodes_202[56]-*.parquet")
LAMBDA = str(RAW / "sced_system_lambda/*.parquet")
CW = str(ROOT / "crosswalk/crosswalk.parquet")
CURT = 'CASE WHEN HSL > "Base Point" + 1 THEN HSL - "Base Point" ELSE 0 END'

con = duckdb.connect()
con.sql("SET TimeZone = 'America/Chicago'")
con.sql(f"SET temp_directory = '{ROOT}/.duckdb_tmp'")

print("building curtailed-interval table ...", flush=True)
con.sql(f"""
CREATE TABLE curt AS
WITH {interval_hours_sql(SCED)},
cw AS (SELECT resource, settlement_point AS node FROM '{CW}'
       WHERE fuel IN ('PVGR','WIND') AND settlement_point IS NOT NULL),
s AS (
    SELECT "Resource Name" AS resource, "Resource Type" AS fuel,
           date_trunc('minute', ("SCED Timestamp" AT TIME ZONE 'America/Chicago')) AS ts,
           "SCED Timestamp"::DATE AS day,
           {CURT} AS curt_mw
    FROM read_parquet({SCED})
    WHERE "Resource Type" IN ('PVGR','WIND') AND "Telemetered Resource Status" = 'ON'
      AND HSL > 0 AND HSL > "Base Point" + 1
      AND "SCED Timestamp" >= TIMESTAMPTZ '{START} 00:00:00 America/Chicago'
      AND "SCED Timestamp" <  TIMESTAMPTZ '{END} 00:00:00 America/Chicago'
)
SELECT s.resource, s.fuel, cw.node, s.ts, s.day, s.curt_mw, s.curt_mw * ih.hrs AS curt_mwh
FROM s JOIN cw USING (resource) JOIN interval_hours ih USING (day)
""")
n = con.sql("SELECT COUNT(*) FROM curt").fetchone()[0]
print(f"  {n:,} curtailed unit-intervals", flush=True)

print("joining nodal LMP and System Lambda ...", flush=True)
con.sql(f"""
CREATE TABLE lmp AS
SELECT date_trunc('minute', CAST(SCEDTimestamp AS TIMESTAMP)) AS ts, settlementPoint AS node, LMP AS lmp
FROM read_parquet('{LMP}')
WHERE NOT repeatHourFlag AND settlementPoint IN (SELECT DISTINCT node FROM curt)
  AND SCEDTimestamp >= '{START}' AND SCEDTimestamp < '{END}'
""")
con.sql(f"""
CREATE TABLE lam AS
SELECT date_trunc('minute', CAST(SCEDTimestamp AS TIMESTAMP)) AS ts,
       COALESCE(cappedSystemLambda, uncappedSystemLambda) AS lam
FROM read_parquet('{LAMBDA}')
WHERE NOT repeatedHourFlag AND SCEDTimestamp >= '{START}' AND SCEDTimestamp < '{END}'
""")
con.sql("""
CREATE TABLE split AS
SELECT c.*, l.lmp, m.lam, l.lmp - m.lam AS congestion_component,
       CASE WHEN m.lam <= 0 THEN 'oversupply'
            WHEN l.lmp < 0  THEN 'congestion'
            ELSE 'other' END AS cause
FROM curt c
JOIN lmp l ON l.node = c.node AND l.ts = c.ts
JOIN lam m ON m.ts = c.ts
""")
matched = con.sql("SELECT COUNT(*) FROM split").fetchone()[0]
print(f"  {matched:,} matched to both LMP and lambda ({100*matched/n:.1f}%)", flush=True)

# ---- outputs ---------------------------------------------------------------
lines = []
say = lambda s="": (print(s), lines.append(s))

say("## Oversupply vs congestion: fleet, Sep 2025 – Jul 2026\n")
fleet = con.sql("""
SELECT fuel, cause,
       ROUND(SUM(curt_mwh)/1e3) AS curt_gwh,
       ROUND(100.0*SUM(curt_mwh)/SUM(SUM(curt_mwh)) OVER (PARTITION BY fuel),1) AS pct_of_fuel,
       ROUND(SUM(curt_mwh*lmp)/1e6, 2) AS value_at_node_musd,
       ROUND(SUM(curt_mwh*lam)/1e6, 2) AS value_at_lambda_musd
FROM split GROUP BY 1,2 ORDER BY 1, 3 DESC
""").df()
say(fleet.to_markdown(index=False))

say("\n## By month (solar + wind), share of curtailed MWh by cause\n")
monthly = con.sql("""
SELECT strftime(day,'%Y-%m') AS month,
       ROUND(SUM(curt_mwh)/1e3) AS curt_gwh,
       ROUND(100.0*SUM(CASE WHEN cause='oversupply' THEN curt_mwh END)/SUM(curt_mwh),1) AS oversupply_pct,
       ROUND(100.0*SUM(CASE WHEN cause='congestion' THEN curt_mwh END)/SUM(curt_mwh),1) AS congestion_pct,
       ROUND(100.0*SUM(CASE WHEN cause='other' THEN curt_mwh END)/SUM(curt_mwh),1) AS other_pct,
       ROUND(AVG(lam),2) AS avg_lambda_when_curtailed
FROM split GROUP BY 1 ORDER BY 1
""").df()
say(monthly.to_markdown(index=False))

site = con.sql("""
SELECT resource, fuel, node,
       ROUND(SUM(curt_mwh)/1e3,1) AS curt_gwh,
       ROUND(100.0*SUM(CASE WHEN cause='oversupply' THEN curt_mwh END)/SUM(curt_mwh),1) AS oversupply_pct,
       ROUND(100.0*SUM(CASE WHEN cause='congestion' THEN curt_mwh END)/SUM(curt_mwh),1) AS congestion_pct,
       ROUND(100.0*SUM(CASE WHEN cause='other' THEN curt_mwh END)/SUM(curt_mwh),1) AS other_pct,
       ROUND(SUM(curt_mwh*congestion_component)/NULLIF(SUM(curt_mwh),0),2) AS avg_congestion_usd_mwh,
       ROUND(SUM(curt_mwh*lam)/NULLIF(SUM(curt_mwh),0),2) AS avg_lambda_usd_mwh
FROM split GROUP BY 1,2,3
""").df()
cw = pd.read_parquet(ROOT / "crosswalk/crosswalk.parquet")[["resource", "county", "owner"]]
site = site.merge(cw, on="resource", how="left")
top_solar = site[site.fuel == "PVGR"].sort_values("curt_gwh", ascending=False).head(50)
top_wind = site[site.fuel == "WIND"].sort_values("curt_gwh", ascending=False).head(20)

for label, t in [("Top 50 solar sites", top_solar), ("Top 20 wind sites", top_wind)]:
    say(f"\n## {label}\n")
    say(t[["resource", "node", "county", "owner", "curt_gwh", "oversupply_pct", "congestion_pct",
           "other_pct", "avg_congestion_usd_mwh", "avg_lambda_usd_mwh"]].to_markdown(index=False))

say("\n## Site x month (top sites), % congestion\n")
sm = con.sql("""
SELECT resource, strftime(day,'%Y-%m') AS month,
       ROUND(SUM(curt_mwh)/1e3,1) AS curt_gwh,
       ROUND(100.0*SUM(CASE WHEN cause='congestion' THEN curt_mwh END)/SUM(curt_mwh),0) AS congestion_pct
FROM split GROUP BY 1,2
""").df()
keep = pd.concat([top_solar.head(12), top_wind.head(6)]).resource.tolist()
piv = sm[sm.resource.isin(keep)].pivot(index="resource", columns="month", values="congestion_pct")
say(piv.reindex(keep).to_markdown())

(OUT / "lambda_split_tables.md").write_text("\n".join(lines) + "\n")
site.to_parquet(OUT / "curtailment_lambda_split.parquet", index=False)
sm.to_parquet(OUT / "curtailment_lambda_split_monthly.parquet", index=False)
print(f"\n-> {OUT/'lambda_split_tables.md'}, curtailment_lambda_split*.parquet")
