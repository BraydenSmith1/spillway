import duckdb
D = "/Users/braydensmith/spillway/data/raw"
RT = f"'{D}/settlement_point_prices/settlement_point_prices_202[56]-*.parquet'"
SCED = f"'{D}/sced_60day/gen_resource_202[56]-*.parquet'"
WIND = f"'{D}/wind_production/*.parquet'"
CURT = """CASE WHEN HSL > "Base Point" + 1 THEN HSL - "Base Point" ELSE 0 END"""

print("### P. RTC+B (2025-12-05) before/after, hub prices")
print(duckdb.sql(f"""
SELECT CASE WHEN deliveryDate < '2025-12-05' THEN 'before RTC' ELSE 'after RTC' END AS era,
       COUNT(*) AS intervals,
       ROUND(AVG(settlementPointPrice),2) AS mean_price,
       ROUND(STDDEV(settlementPointPrice),2) AS volatility,
       ROUND(100.0*COUNT(*) FILTER (WHERE settlementPointPrice<0)/COUNT(*),2) AS pct_negative,
       ROUND(100.0*COUNT(*) FILTER (WHERE settlementPointPrice>200)/COUNT(*),3) AS pct_over_200
FROM read_parquet({RT})
WHERE settlementPoint LIKE 'HB_%'
  AND deliveryDate >= '2025-08-01' AND deliveryDate < '2026-07-11'
GROUP BY 1 ORDER BY 1 DESC
"""))

print("### Q. Is curtailment happening at negative prices? (solar, hourly join)")
print(duckdb.sql(f"""
WITH c AS (
  SELECT date_trunc('hour', "SCED Timestamp") h,
         SUM({CURT})/12.0 AS curt_mwh
  FROM read_parquet({SCED})
  WHERE "Resource Type"='PVGR' AND "Telemetered Resource Status"='ON' AND HSL>0
    AND "SCED Timestamp" >= '2026-01-01' AND "SCED Timestamp" < '2026-07-01'
  GROUP BY 1
), p AS (
  SELECT CAST(deliveryDate AS DATE) + INTERVAL (deliveryHour-1) HOUR AS h,
         AVG(settlementPointPrice) AS hub_price
  FROM read_parquet({RT})
  WHERE settlementPoint='HB_WEST'
    AND deliveryDate >= '2026-01-01' AND deliveryDate < '2026-07-01'
  GROUP BY 1
)
SELECT CASE WHEN hub_price < 0 THEN 'price < $0'
            WHEN hub_price < 15 THEN '$0-15'
            WHEN hub_price < 40 THEN '$15-40'
            ELSE 'over $40' END AS price_band,
       COUNT(*) AS hours,
       ROUND(SUM(curt_mwh)) AS curtailed_mwh,
       ROUND(100.0*SUM(curt_mwh)/SUM(SUM(curt_mwh)) OVER (),1) AS pct_of_curtailment
FROM c JOIN p USING (h)
GROUP BY 1 ORDER BY 3 DESC
"""))

print("### R. How accurate is ERCOT's own wind forecast? (system-wide, hourly)")
print(duckdb.sql(f"""
SELECT strftime(CAST(deliveryDate AS DATE),'%Y-%m') AS month,
       COUNT(*) AS hours,
       ROUND(AVG(ABS(genSystemWide - STWPFSystemWide)),1) AS mae_mw,
       ROUND(AVG(genSystemWide),1) AS avg_actual_mw,
       ROUND(100.0*AVG(ABS(genSystemWide - STWPFSystemWide))/NULLIF(AVG(genSystemWide),0),1) AS mae_pct
FROM read_parquet({WIND})
WHERE genSystemWide IS NOT NULL AND STWPFSystemWide IS NOT NULL
  AND deliveryDate >= '2025-09-01' AND deliveryDate < '2026-07-01'
GROUP BY 1 ORDER BY 1
"""))
