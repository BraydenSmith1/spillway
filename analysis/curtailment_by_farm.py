"""
curtailment_by_farm.py — how much energy did each solar farm throw away?

The first real measurement in this project. Replaces the 12% curtailment
assumption in the master brief (§4.1) with a number from ERCOT's own data.

    python analysis/curtailment_by_farm.py

Method, in plain terms:
  HSL        = what the farm COULD have produced that interval
  Base Point = what ERCOT told it to produce
  the gap    = energy thrown away

Rows are 5-minute intervals, so MW / 12 = MWh.

Caveats, deliberately conservative:
  * only intervals where the unit reports status ON (it was actually running)
  * a 1 MW tolerance, so telemetry jitter isn't counted as curtailment
  * daylight only for solar (HSL > 0) — a panel at night isn't curtailed
  * this does NOT yet separate ERCOT-ordered curtailment from a generator
    choosing not to run at negative prices. That split is the next step.
"""

from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
FILES = [
    str(ROOT / "data/raw/sced_60day/gen_resource_2025-0[89]*.parquet"),
    str(ROOT / "data/raw/sced_60day/gen_resource_2025-1*.parquet"),
    str(ROOT / "data/raw/sced_60day/gen_resource_2026-*.parquet"),
]

BASE = f"""
    FROM read_parquet({FILES})
    WHERE "Resource Type" = 'PVGR'
      AND "Telemetered Resource Status" = 'ON'
      AND HSL > 0
"""

# The 1 MW tolerance belongs INSIDE the numerator, not in the WHERE clause.
# Filtering the rows first would leave only curtailed intervals in the
# denominator, which makes every farm look ~96% curtailed.
CURTAILED = """CASE WHEN HSL > "Base Point" + 1
                    THEN HSL - "Base Point" ELSE 0 END"""

TOP_FARMS = f"""
SELECT
    "Resource Name"                                AS farm,
    ROUND(SUM({CURTAILED}) / 12.0)                 AS wasted_mwh,
    ROUND(SUM(HSL) / 12.0)                         AS potential_mwh,
    ROUND(100.0 * SUM({CURTAILED})
          / NULLIF(SUM(HSL), 0), 1)                AS pct_wasted
    {BASE}
GROUP BY 1
HAVING SUM(HSL) / 12.0 > 50000          -- real farms only, not tiny units
ORDER BY wasted_mwh DESC
LIMIT 5
"""


def monthly(farms):
    quoted = ", ".join(f"'{f}'" for f in farms)
    return f"""
    SELECT
        "Resource Name"                                     AS farm,
        strftime("SCED Timestamp", '%Y-%m')                 AS month,
        ROUND(100.0 * SUM({CURTAILED})
              / NULLIF(SUM(HSL), 0), 1)                     AS pct_wasted
        {BASE}
          AND "Resource Name" IN ({quoted})
    GROUP BY 1, 2
    ORDER BY 1, 2
    """


def main():
    top = duckdb.sql(TOP_FARMS).df()

    print("\n" + "=" * 72)
    print("  TOP 5 SOLAR FARMS BY CURTAILMENT  (Aug 2025 - Jul 2026)")
    print("=" * 72)
    print()
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
    print("=" * 72)
    print()
    print(pivot.to_string(na_rep="  -"))

    total_wasted = top["wasted_mwh"].sum()
    avg_pct = 100.0 * top["wasted_mwh"].sum() / top["potential_mwh"].sum()
    print("\n" + "-" * 72)
    print(f"  These 5 farms alone threw away {total_wasted:,.0f} MWh in 12 months.")
    print(f"  Weighted average curtailment: {avg_pct:.1f}%")
    print(f"  The master brief (SS4.1) assumes 12%.")
    print("-" * 72 + "\n")


if __name__ == "__main__":
    main()
