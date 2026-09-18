import duckdb
D = "data/raw"
RT = f"'{D}/settlement_point_prices/settlement_point_prices_202[56]-*.parquet'"
DAM = f"'{D}/dam_settlement_point_prices/*.parquet'"

print("### G. Real-time price distribution, Aug2025-Jul2026 (all settlement points)")
print(duckdb.sql(f"""
SELECT COUNT(*) AS intervals,
       ROUND(AVG(settlementPointPrice),2)  AS mean,
       ROUND(MEDIAN(settlementPointPrice),2) AS median,
       ROUND(MIN(settlementPointPrice),2)  AS min,
       ROUND(MAX(settlementPointPrice),2)  AS max,
       ROUND(100.0*COUNT(*) FILTER (WHERE settlementPointPrice<0)/COUNT(*),2) AS pct_negative,
       ROUND(100.0*COUNT(*) FILTER (WHERE settlementPointPrice>100)/COUNT(*),3) AS pct_over_100,
       ROUND(100.0*COUNT(*) FILTER (WHERE settlementPointPrice>1000)/COUNT(*),4) AS pct_over_1000
FROM read_parquet({RT})
WHERE deliveryDate >= '2025-08-01' AND deliveryDate < '2026-07-11'
"""))

print("### H. Negative prices by month")
print(duckdb.sql(f"""
SELECT strftime(CAST(deliveryDate AS DATE),'%Y-%m') AS month,
       ROUND(100.0*COUNT(*) FILTER (WHERE settlementPointPrice<0)/COUNT(*),2) AS pct_negative,
       ROUND(AVG(settlementPointPrice),2) AS avg_price
FROM read_parquet({RT})
WHERE deliveryDate >= '2025-08-01' AND deliveryDate < '2026-07-11'
GROUP BY 1 ORDER BY 1
"""))

print("### I. Day-ahead vs real-time, hub prices")
print(duckdb.sql(f"""
WITH d AS (
  SELECT CAST(deliveryDate AS DATE) dt, deliveryHour hr, settlementPoint sp,
         AVG(settlementPointPrice) dam
  FROM read_parquet({DAM}) WHERE settlementPoint LIKE 'HB_%' GROUP BY 1,2,3
), r AS (
  SELECT CAST(deliveryDate AS DATE) dt, deliveryHour hr, settlementPoint sp,
         AVG(settlementPointPrice) rt
  FROM read_parquet({RT}) WHERE settlementPoint LIKE 'HB_%' GROUP BY 1,2,3
)
SELECT d.sp AS hub, COUNT(*) AS hours,
       ROUND(AVG(dam),2) AS avg_dam, ROUND(AVG(rt),2) AS avg_rt,
       ROUND(AVG(rt-dam),2) AS avg_rt_minus_dam,
       ROUND(AVG(ABS(rt-dam)),2) AS avg_abs_gap
FROM d JOIN r USING (dt,hr,sp)
WHERE d.dt >= '2025-08-01'
GROUP BY 1 ORDER BY 1
"""))

print("### J. Daily price spread at a hub (battery arbitrage opportunity)")
print(duckdb.sql(f"""
WITH h AS (
  SELECT CAST(deliveryDate AS DATE) dt, deliveryHour hr,
         AVG(settlementPointPrice) p
  FROM read_parquet({RT}) WHERE settlementPoint='HB_WEST'
    AND deliveryDate >= '2025-08-01' AND deliveryDate < '2026-07-11'
  GROUP BY 1,2
)
SELECT strftime(dt,'%Y-%m') AS month,
       ROUND(AVG(mx-mn),2) AS avg_daily_spread,
       ROUND(MAX(mx-mn),2) AS max_daily_spread
FROM (SELECT dt, MAX(p) mx, MIN(p) mn FROM h GROUP BY dt)
GROUP BY 1 ORDER BY 1
"""))
