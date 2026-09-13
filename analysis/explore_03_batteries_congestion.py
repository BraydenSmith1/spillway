import duckdb
D = "/Users/braydensmith/spillway/data/raw"
RT = f"'{D}/settlement_point_prices/settlement_point_prices_202[56]-*.parquet'"
ESR = f"'{D}/sced_esr/*.parquet'"
SHDW = f"'{D}/shadow_prices/*.parquet'"

print("### L. Are those $0.00 nodes real? (ERKA_SLR_RN, March 2026)")
print(duckdb.sql(f"""
SELECT settlementPoint sp, COUNT(*) n,
       COUNT(*) FILTER (WHERE settlementPointPrice=0) n_zero,
       ROUND(MIN(settlementPointPrice),2) mn, ROUND(MAX(settlementPointPrice),2) mx
FROM read_parquet({RT})
WHERE settlementPoint IN ('ERKA_SLR_RN','CST2_SLR_RN','AGUAYO_UNIT1','HB_WEST')
  AND deliveryDate >= '2026-03-01' AND deliveryDate < '2026-04-01'
GROUP BY 1 ORDER BY 1
"""))

print("### M. Batteries: fleet size and behaviour (ESR, Dec2025-Jul2026)")
print(duckdb.sql(f"""
SELECT strftime("SCED Timestamp",'%Y-%m') AS month,
       COUNT(DISTINCT "Resource Name") AS units,
       ROUND(SUM(CASE WHEN "Base Point">0 THEN "Base Point" ELSE 0 END)/12.0) AS discharge_mwh,
       ROUND(SUM(CASE WHEN "Base Point"<0 THEN -"Base Point" ELSE 0 END)/12.0) AS charge_mwh,
       ROUND(AVG(SOC),1) AS avg_soc_mwh,
       ROUND(MAX("Max SOC"),1) AS biggest_unit_mwh
FROM read_parquet({ESR})
GROUP BY 1 ORDER BY 1
"""))

print("### N. Battery charge/discharge by hour (Mar 2026)")
print(duckdb.sql(f"""
SELECT hour("SCED Timestamp") AS hr,
       ROUND(SUM(CASE WHEN "Base Point"<0 THEN -"Base Point" ELSE 0 END)/12.0) AS charge_mwh,
       ROUND(SUM(CASE WHEN "Base Point">0 THEN "Base Point" ELSE 0 END)/12.0) AS discharge_mwh
FROM read_parquet({ESR})
WHERE "SCED Timestamp" >= '2026-03-01' AND "SCED Timestamp" < '2026-04-01'
GROUP BY 1 ORDER BY 1
"""))

print("### O. Which transmission constraints bind most? (shadow prices)")
print(duckdb.sql(f"""
SELECT constraintName, COUNT(*) AS intervals_binding,
       ROUND(AVG(shadowPrice),2) AS avg_shadow_price,
       ROUND(MAX(shadowPrice),2) AS max_shadow_price
FROM read_parquet({SHDW})
WHERE "SCEDTimestamp" >= '2025-08-01'
GROUP BY 1 ORDER BY intervals_binding DESC LIMIT 12
"""))
