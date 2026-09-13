import duckdb

SCED = "'/Users/braydensmith/spillway/data/raw/sced_60day/gen_resource_202[56]-*.parquet'"
CURT = """CASE WHEN HSL > "Base Point" + 1 THEN HSL - "Base Point" ELSE 0 END"""
WIN = """"SCED Timestamp" >= '2025-08-01' AND "SCED Timestamp" < '2026-07-11'"""

print("### A. ERCOT-wide curtailment by fuel, Aug2025-Jul2026")
print(duckdb.sql(f"""
SELECT "Resource Type" AS fuel,
       COUNT(DISTINCT "Resource Name")        AS units,
       ROUND(SUM(HSL)/12.0/1e6, 2)            AS potential_twh,
       ROUND(SUM({CURT})/12.0/1e6, 3)         AS curtailed_twh,
       ROUND(100.0*SUM({CURT})/NULLIF(SUM(HSL),0), 2) AS pct
FROM read_parquet({SCED})
WHERE {WIN} AND "Telemetered Resource Status"='ON' AND HSL>0
GROUP BY 1 HAVING SUM(HSL)>0 ORDER BY curtailed_twh DESC LIMIT 10
"""))

print("### B. Renewable curtailment by month")
print(duckdb.sql(f"""
SELECT strftime("SCED Timestamp",'%Y-%m') AS month,
       ROUND(SUM(CASE WHEN "Resource Type"='WIND' THEN {CURT} ELSE 0 END)/12.0) AS wind_mwh,
       ROUND(SUM(CASE WHEN "Resource Type"='PVGR' THEN {CURT} ELSE 0 END)/12.0) AS solar_mwh,
       ROUND(100.0*SUM(CASE WHEN "Resource Type"='PVGR' THEN {CURT} ELSE 0 END)
             /NULLIF(SUM(CASE WHEN "Resource Type"='PVGR' THEN HSL ELSE 0 END),0),1) AS solar_pct,
       ROUND(100.0*SUM(CASE WHEN "Resource Type"='WIND' THEN {CURT} ELSE 0 END)
             /NULLIF(SUM(CASE WHEN "Resource Type"='WIND' THEN HSL ELSE 0 END),0),1) AS wind_pct
FROM read_parquet({SCED})
WHERE {WIN} AND "Telemetered Resource Status"='ON' AND HSL>0
  AND "Resource Type" IN ('WIND','PVGR')
GROUP BY 1 ORDER BY 1
"""))

print("### C. Curtailment by hour of day (solar vs wind)")
print(duckdb.sql(f"""
SELECT hour("SCED Timestamp") AS hr,
       ROUND(100.0*SUM(CASE WHEN "Resource Type"='PVGR' THEN {CURT} ELSE 0 END)
             /NULLIF(SUM(CASE WHEN "Resource Type"='PVGR' THEN HSL ELSE 0 END),0),1) AS solar_pct,
       ROUND(100.0*SUM(CASE WHEN "Resource Type"='WIND' THEN {CURT} ELSE 0 END)
             /NULLIF(SUM(CASE WHEN "Resource Type"='WIND' THEN HSL ELSE 0 END),0),1) AS wind_pct
FROM read_parquet({SCED})
WHERE {WIN} AND "Telemetered Resource Status"='ON' AND HSL>0
  AND "Resource Type" IN ('WIND','PVGR')
GROUP BY 1 ORDER BY 1
"""))

print("### D. How concentrated is curtailment? (solar units ranked)")
print(duckdb.sql(f"""
WITH per AS (
  SELECT "Resource Name" AS farm, SUM({CURT})/12.0 AS mwh
  FROM read_parquet({SCED})
  WHERE {WIN} AND "Telemetered Resource Status"='ON' AND HSL>0 AND "Resource Type"='PVGR'
  GROUP BY 1
), r AS (SELECT farm, mwh, ROW_NUMBER() OVER (ORDER BY mwh DESC) rn, SUM(mwh) OVER () tot FROM per)
SELECT
  COUNT(*) FILTER (WHERE rn<=10)  AS top10_units,
  ROUND(100.0*SUM(mwh) FILTER (WHERE rn<=10)/MAX(tot),1) AS top10_pct_of_all,
  ROUND(100.0*SUM(mwh) FILTER (WHERE rn<=50)/MAX(tot),1) AS top50_pct_of_all,
  COUNT(*) AS total_solar_units
FROM r
"""))
