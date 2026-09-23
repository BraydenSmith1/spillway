"""
curtailment_by_farm.py — how much energy did each solar farm throw away?

The first real measurement in this project: per-farm curtailment measured
from ERCOT's own dispatch data rather than assumed from published averages.

    python analysis/curtailment_by_farm.py

Method, in plain terms:
  HSL        = what the farm COULD have produced that interval
  Base Point = what ERCOT told it to produce
  the gap    = energy thrown away

Interval length comes from the data, not a constant — ERCOT ran SCED every
15 minutes before RTC+B and every 5 minutes after. See interval_hours.py.

Caveats, deliberately conservative:
  * only intervals where the unit reports status ON (it was actually running)
  * a 1 MW tolerance, so telemetry jitter isn't counted as curtailment
  * daylight only for solar (HSL > 0) — a panel at night isn't curtailed
  * this does NOT yet separate ERCOT-ordered curtailment from a generator
    choosing not to run at negative prices. See curtailment_vs_node_price.py.
"""

import sys
from pathlib import Path

import duckdb
import pandas as pd

duckdb.sql("SET TimeZone = 'America/Chicago'")  # ERCOT runs on Central

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from analysis.interval_hours import interval_hours_sql  # noqa: E402

FILES = [
    str(ROOT / "data/raw/sced_60day/gen_resource_2025-0[89]*.parquet"),
    str(ROOT / "data/raw/sced_60day/gen_resource_2025-1*.parquet"),
    str(ROOT / "data/raw/sced_60day/gen_resource_2026-*.parquet"),
]
IH = interval_hours_sql(FILES)

# The 1 MW tolerance belongs INSIDE the numerator, not in the WHERE clause.
# Filtering the rows first would leave only curtailed intervals in the
# denominator, which makes every farm look ~96% curtailed.
CURTAILED = """CASE WHEN HSL > "Base Point" + 1
                    THEN HSL - "Base Point" ELSE 0 END"""

BASE = f"""
    FROM read_parquet({FILES})
    WHERE "Resource Type" = 'PVGR'
      AND "Telemetered Resource Status" = 'ON'
      AND HSL > 0
"""

TOP_FARMS = f"""
WITH {IH},
daily AS (
    SELECT "Resource Name"      AS farm,
           "SCED Timestamp"::DATE AS day,
           SUM({CURTAILED})     AS curt_mw,
           SUM(HSL)             AS hsl_mw
    {BASE}
    GROUP BY 1, 2
)
SELECT farm,
       ROUND(SUM(curt_mw * hrs))                              AS wasted_mwh,
       ROUND(SUM(hsl_mw * hrs))                               AS potential_mwh,
       ROUND(100.0 * SUM(curt_mw * hrs) / NULLIF(SUM(hsl_mw * hrs), 0), 1)
                                                              AS pct_wasted
FROM daily JOIN interval_hours USING (day)
GROUP BY 1
HAVING SUM(hsl_mw * hrs) > 50000       -- real farms only, not tiny units
ORDER BY wasted_mwh DESC
LIMIT 5
"""


def monthly(farms):
    quoted = ", ".join(f"'{f}'" for f in farms)
    return f"""
    WITH {IH},
    daily AS (
        SELECT "Resource Name"        AS farm,
               "SCED Timestamp"::DATE AS day,
               SUM({CURTAILED})       AS curt_mw,
               SUM(HSL)               AS hsl_mw
        {BASE}
          AND "Resource Name" IN ({quoted})
        GROUP BY 1, 2
    )
    SELECT farm, strftime(day, '%Y-%m') AS month,
           ROUND(100.0 * SUM(curt_mw * hrs) / NULLIF(SUM(hsl_mw * hrs), 0), 1)
               AS pct_wasted
    FROM daily JOIN interval_hours USING (day)
    GROUP BY 1, 2 ORDER BY 1, 2
    """


def main():
    top = duckdb.sql(TOP_FARMS).df()

    print("\n" + "=" * 72)
    print("  TOP 5 SOLAR FARMS BY CURTAILMENT  (Aug 2025 - Jul 2026)")
    print("=" * 72 + "\n")
    out = top.copy()
    out["wasted_mwh"] = out["wasted_mwh"].map("{:,.0f}".format)
    out["potential_mwh"] = out["potential_mwh"].map("{:,.0f}".format)
    out["pct_wasted"] = out["pct_wasted"].map("{:.1f}%".format)
    print(out.to_string(index=False))

    farms = top["farm"].tolist()
    m = duckdb.sql(monthly(farms)).df()
    pivot = m.pivot(index="month", columns="farm", values="pct_wasted")

    print("\n" + "=" * 72)
    print("  PERCENT OF POTENTIAL OUTPUT THROWN AWAY, BY MONTH")
    print("=" * 72 + "\n")
    print(pivot.to_string(na_rep="  -"))

    total_wasted = top["wasted_mwh"].sum()
    avg_pct = 100.0 * top["wasted_mwh"].sum() / top["potential_mwh"].sum()
    print("\n" + "-" * 72)
    print(f"  These 5 farms alone threw away {total_wasted:,.0f} MWh in 12 months.")
    print(f"  Weighted average curtailment: {avg_pct:.1f}%")
    print("-" * 72 + "\n")


if __name__ == "__main__":
    main()
