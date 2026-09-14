"""
02b_validate_sp_links.py — does each resource→node link behave like a real one?

A generator's own node price should sag when the generator is curtailed:
that is what congestion looks like from the price side. So for every link we
compare the node's average price during curtailed intervals against the rest.
Exact-stem links set the baseline; if the fuzzy links show the same signature,
they are probably right. Any link where prices are HIGHER during curtailment
is suspect.

March 2026 is used because curtailment peaked then.
"""

from pathlib import Path
import duckdb
duckdb.sql("SET TimeZone = 'America/Chicago'")  # ERCOT runs on Central; the Mac does not

ROOT = Path(__file__).resolve().parent.parent
STG = ROOT / "crosswalk" / "staging"
SCED = ROOT / "data/raw/sced_60day/gen_resource_2026-03-*.parquet"
SPP = ROOT / "data/raw/settlement_point_prices/settlement_point_prices_2026-03.parquet"

df = duckdb.sql(f"""
WITH links AS (
    SELECT resource, sp, method FROM '{STG}/resource_sp.parquet'
    WHERE sp IS NOT NULL AND fuel IN ('PVGR', 'WIND')
),
sced AS (
    SELECT "Resource Name" AS resource,
           -- bucket the 5-min SCED stamp into the 15-min settlement interval
           "SCED Timestamp"::DATE                              AS d,
           hour("SCED Timestamp") + 1                          AS hr,
           (minute("SCED Timestamp") // 15) + 1                AS iv,
           CASE WHEN HSL > "Base Point" + 1 THEN 1 ELSE 0 END  AS curtailed
    FROM read_parquet('{SCED}')
    WHERE "Telemetered Resource Status" = 'ON' AND HSL > 5
),
price AS (
    SELECT settlementPoint AS sp, deliveryDate::DATE AS d,
           deliveryHour AS hr, deliveryInterval AS iv,
           settlementPointPrice AS p
    FROM read_parquet('{SPP}')
)
SELECT l.resource, l.sp, l.method,
       COUNT(*)                                          AS n,
       ROUND(AVG(p) FILTER (WHERE curtailed = 1), 1)     AS price_when_curtailed,
       ROUND(AVG(p) FILTER (WHERE curtailed = 0), 1)     AS price_otherwise
FROM links l
JOIN sced  s USING (resource)
JOIN price p ON p.sp = l.sp AND p.d = s.d AND p.hr = s.hr AND p.iv = s.iv
GROUP BY 1, 2, 3
HAVING COUNT(*) FILTER (WHERE curtailed = 1) >= 50
""").df()

df["gap"] = df.price_when_curtailed - df.price_otherwise
df["looks_right"] = df.gap < 0

print("Signature by link method (negative gap = price sags when curtailed):")
print(df.groupby("method").agg(
    links=("resource", "count"),
    median_gap=("gap", "median"),
    pct_looks_right=("looks_right", lambda s: round(100 * s.mean())),
).to_string())

bad = df[~df.looks_right].sort_values("gap", ascending=False)
print(f"\n{len(bad)} suspect links (price higher when curtailed):")
print(bad.head(12).to_string(index=False))

df.to_parquet(STG / "sp_link_validation.parquet", index=False)
