"""
show_your_work.py — trace one curtailment number from raw rows to the headline.

Every figure in curtailment_by_farm.py comes from the same arithmetic applied
to millions of rows. This walks that arithmetic for ONE farm on ONE day so you
can see it, check it by hand, and trust (or reject) the result.

    python analysis/show_your_work.py

Change FARM and DAY below and re-run to inspect anything you like.
"""

from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parent.parent
FARM = "GALLOWAY_SOLAR1"
DAY = "2026-03-15"
MONTH_GLOB = str(ROOT / "data/raw/sced_60day/gen_resource_2026-03-*.parquet")
DAY_FILE = str(ROOT / f"data/raw/sced_60day/gen_resource_{DAY}.parquet")

line = lambda t: print("\n" + "=" * 78 + f"\n  {t}\n" + "=" * 78)


# ── STEP 1 ────────────────────────────────────────────────────────────────
# The rawest thing there is: actual rows from the file, nothing computed.
line(f"STEP 1 — Raw 5-minute rows: {FARM} on {DAY}, midday")
print("""
  HSL        = what the farm COULD produce right now (its available power)
  Base Point = what ERCOT INSTRUCTED it to produce
  Telem Net  = what it ACTUALLY produced (proves it followed the instruction)
""")
print(duckdb.sql(f"""
    SELECT
        strftime("SCED Timestamp", '%H:%M:%S')  AS time,
        ROUND(HSL, 1)                           AS hsl_mw,
        ROUND("Base Point", 1)                  AS basepoint_mw,
        ROUND("Telemetered Net Output", 1)      AS actual_mw,
        "Telemetered Resource Status"           AS status
    FROM read_parquet('{DAY_FILE}')
    WHERE "Resource Name" = '{FARM}'
      AND hour("SCED Timestamp") = 13
    ORDER BY 1
    LIMIT 12
""").df().to_string(index=False))

# ── STEP 2 ────────────────────────────────────────────────────────────────
line("STEP 2 — The arithmetic, one row at a time")
print("""
  gap_mw  = HSL - Base Point        (power being thrown away)
  mwh     = gap_mw / 12             (each row covers 5 minutes = 1/12 hour)
""")
print(duckdb.sql(f"""
    SELECT
        strftime("SCED Timestamp", '%H:%M:%S')          AS time,
        ROUND(HSL, 1)                                   AS hsl_mw,
        ROUND("Base Point", 1)                          AS basepoint_mw,
        ROUND(HSL - "Base Point", 1)                    AS gap_mw,
        ROUND((HSL - "Base Point") / 12.0, 2)           AS wasted_mwh
    FROM read_parquet('{DAY_FILE}')
    WHERE "Resource Name" = '{FARM}'
      AND hour("SCED Timestamp") = 13
    ORDER BY 1
    LIMIT 12
""").df().to_string(index=False))

# ── STEP 3 ────────────────────────────────────────────────────────────────
line(f"STEP 3 — Add up that single hour")
print(duckdb.sql(f"""
    SELECT
        COUNT(*)                                        AS intervals,
        ROUND(SUM(HSL) / 12.0, 1)                       AS could_have_made_mwh,
        ROUND(SUM("Base Point") / 12.0, 1)              AS told_to_make_mwh,
        ROUND(SUM(HSL - "Base Point") / 12.0, 1)        AS wasted_mwh
    FROM read_parquet('{DAY_FILE}')
    WHERE "Resource Name" = '{FARM}'
      AND hour("SCED Timestamp") = 13
""").df().to_string(index=False))

# ── STEP 4 ────────────────────────────────────────────────────────────────
line(f"STEP 4 — The whole day, hour by hour (daylight only)")
print(duckdb.sql(f"""
    SELECT
        hour("SCED Timestamp")                          AS hour,
        ROUND(SUM(HSL) / 12.0, 1)                       AS could_have_mwh,
        ROUND(SUM("Base Point") / 12.0, 1)              AS produced_mwh,
        ROUND(SUM(HSL - "Base Point") / 12.0, 1)        AS wasted_mwh,
        ROUND(100.0 * SUM(HSL - "Base Point")
              / NULLIF(SUM(HSL), 0), 1)                 AS pct_wasted
    FROM read_parquet('{DAY_FILE}')
    WHERE "Resource Name" = '{FARM}'
      AND "Telemetered Resource Status" = 'ON'
      AND HSL > 0
    GROUP BY 1 ORDER BY 1
""").df().to_string(index=False))

# ── STEP 5 ────────────────────────────────────────────────────────────────
line(f"STEP 5 — The whole month = the number in the report")
print(duckdb.sql(f"""
    SELECT
        ROUND(SUM(HSL) / 12.0)                          AS could_have_mwh,
        ROUND(SUM(CASE WHEN HSL > "Base Point" + 1
                       THEN HSL - "Base Point" ELSE 0 END) / 12.0)
                                                        AS wasted_mwh,
        ROUND(100.0 * SUM(CASE WHEN HSL > "Base Point" + 1
                               THEN HSL - "Base Point" ELSE 0 END)
              / NULLIF(SUM(HSL), 0), 1)                 AS pct_wasted
    FROM read_parquet('{MONTH_GLOB}')
    WHERE "Resource Name" = '{FARM}'
      AND "Telemetered Resource Status" = 'ON'
      AND HSL > 0
""").df().to_string(index=False))
print(f"\n  ^ this pct_wasted is the 2026-03 cell for {FARM}")
print("    in the monthly table from curtailment_by_farm.py.\n")
