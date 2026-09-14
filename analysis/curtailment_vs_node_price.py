"""
curtailment_vs_node_price.py — was the spilled energy worth anything to its owner?

Joins each wind/solar unit's 5-minute curtailment to the price AT ITS OWN
NODE (via the crosswalk), Jan-Jun 2026. Two questions:

  1. What share of curtailed MWh happened while the generator's own node
     price was negative? At a negative price, producing costs money, so the
     spilled MWh had zero-or-less value to its owner.
  2. Using the node price as the value of each spilled MWh, what was the
     total "revenue" foregone — and how much of it was actually negative?

Row-level formula is the same as everywhere else: HSL - Base Point, ON, >1 MW.
"""
from pathlib import Path
import duckdb
duckdb.sql("SET TimeZone = 'America/Chicago'")  # ERCOT runs on Central; the Mac does not

ROOT = Path(__file__).resolve().parent.parent
CW = ROOT / "crosswalk/crosswalk.parquet"
SCED = ROOT / "data/raw/sced_60day/gen_resource_2026-0[1-6]-*.parquet"
SPP = ROOT / "data/raw/settlement_point_prices/settlement_point_prices_2026-0[1-6].parquet"

df = duckdb.sql(f"""
WITH cw AS (
    SELECT resource, fuel, settlement_point AS sp FROM '{CW}'
    WHERE fuel IN ('PVGR','WIND') AND settlement_point IS NOT NULL
),
sced AS (
    SELECT "Resource Name" AS resource,
           "SCED Timestamp"::DATE AS d,
           hour("SCED Timestamp") + 1 AS hr,
           (minute("SCED Timestamp") // 15) + 1 AS iv,
           CASE WHEN HSL > "Base Point" + 1 THEN (HSL - "Base Point") / 12.0 ELSE 0 END AS curt_mwh
    FROM read_parquet('{SCED}')
    WHERE "Telemetered Resource Status" = 'ON' AND HSL > 0
),
price AS (
    SELECT settlementPoint AS sp, deliveryDate::DATE AS d, deliveryHour AS hr,
           deliveryInterval AS iv, settlementPointPrice AS p
    FROM read_parquet('{SPP}')
)
SELECT cw.fuel, cw.resource,
       SUM(curt_mwh)                                       AS curt_mwh,
       SUM(curt_mwh) FILTER (WHERE p < 0)                  AS curt_mwh_neg,
       SUM(curt_mwh) FILTER (WHERE p >= 0 AND p < 15)      AS curt_mwh_0_15,
       SUM(curt_mwh) FILTER (WHERE p >= 15)                AS curt_mwh_15plus,
       SUM(curt_mwh * p)                                   AS value_at_node,
       SUM(curt_mwh * GREATEST(p, 0))                      AS value_if_floor0
FROM sced JOIN cw USING (resource)
JOIN price ON price.sp = cw.sp AND price.d = sced.d AND price.hr = sced.hr AND price.iv = sced.iv
GROUP BY 1, 2
""").df()

tot = df.groupby("fuel")[["curt_mwh","curt_mwh_neg","curt_mwh_0_15","curt_mwh_15plus","value_at_node","value_if_floor0"]].sum()
tot["pct_neg"] = 100*tot.curt_mwh_neg/tot.curt_mwh
tot["pct_under15"] = 100*(tot.curt_mwh_neg+tot.curt_mwh_0_15)/tot.curt_mwh
tot["avg_$/MWh_at_node"] = tot.value_at_node/tot.curt_mwh
print("=== Curtailed energy valued at the generator's OWN node price, Jan-Jun 2026 ===\n")
print(tot[["curt_mwh","pct_neg","pct_under15","avg_$/MWh_at_node","value_at_node","value_if_floor0"]].round(1).to_string())
print("\n  value_at_node    = sum(curtailed MWh x node price); negative means producing would have cost money")
print("  value_if_floor0  = same, but counting negative-price intervals as $0 (what a PTC-less owner forgoes)")

top = df[df.fuel=="PVGR"].sort_values("curt_mwh", ascending=False).head(10).copy()
top["pct_neg"] = (100*top.curt_mwh_neg/top.curt_mwh).round(0)
top["avg_$/MWh"] = (top.value_at_node/top.curt_mwh).round(2)
print("\n=== Top 10 curtailed solar units: share at negative own-node price ===")
print(top[["resource","curt_mwh","pct_neg","avg_$/MWh"]].round(0).to_string(index=False))
df.to_parquet(ROOT/"analysis/curtailment_vs_node_price.parquet", index=False)
