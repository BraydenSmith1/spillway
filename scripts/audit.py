"""
audit.py — what's actually on disk, and where the holes are.

Prints one block per dataset: size, row count, the date range it really
covers, and any missing days inside that range.

    python scripts/audit.py
"""

from pathlib import Path
from datetime import date
import pandas as pd
import pyarrow.parquet as pq

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

# The column that best answers "which day does this row describe".
# Forecast datasets use postedDatetime: their deliveryDate runs up to 7 days
# into the future, which would overstate what we actually hold.
DATE_COL = {
    "settlement_point_prices":           "deliveryDate",
    "lmp_resource_nodes":                "SCEDTimestamp",
    "shadow_prices":                     "SCEDTimestamp",
    "solar_production":                  "deliveryDate",
    "wind_production":                   "deliveryDate",
    "resource_outages":                  "operatingDate",
    "7d_load_forecast_by_forecast":      "postedDatetime",
    "7d_load_forecast_by_weather_zone":  "postedDatetime",
}

# The window the project is trying to cover.
WINDOW_START = pd.Timestamp("2025-09-01")


def human(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:,.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024


def gaps(days, lo, hi):
    """Missing calendar days between lo and hi."""
    have = set(days)
    return [d.date() for d in pd.date_range(lo, hi) if d.date() not in have]


def summarize_gaps(missing, limit=6):
    """Collapse a list of dates into readable runs."""
    if not missing:
        return "none"
    runs, start, prev = [], missing[0], missing[0]
    for d in missing[1:]:
        if (d - prev).days == 1:
            prev = d
            continue
        runs.append((start, prev))
        start = prev = d
    runs.append((start, prev))
    out = [f"{a}" if a == b else f"{a}..{b}" for a, b in runs[:limit]]
    if len(runs) > limit:
        out.append(f"(+{len(runs)-limit} more runs)")
    return ", ".join(out)


def audit_sced(files):
    """sced_60day is one file per day — read dates from filenames, not content."""
    days = sorted(date.fromisoformat(f.stem.replace("gen_resource_", ""))
                  for f in files)
    rows = sum(pq.ParquetFile(f).metadata.num_rows for f in files)
    return days, rows


def audit_generic(files, col):
    days, rows = set(), 0
    for f in files:
        pf = pq.ParquetFile(f)
        rows += pf.metadata.num_rows
        if col not in pf.schema.names:
            continue
        s = pd.to_datetime(pq.read_table(f, columns=[col])[col].to_pandas(),
                           errors="coerce")
        days.update(s.dt.date.dropna().unique())
    return sorted(days), rows


def main():
    today = pd.Timestamp.now().normalize().date()
    datasets = sorted(d for d in RAW.iterdir() if d.is_dir())

    print(f"AUDIT  ({today})   target window: {WINDOW_START.date()} -> {today}")
    print("=" * 74)

    for d in datasets:
        files = sorted(d.glob("*.parquet"))
        if not files:
            print(f"\n{d.name}\n  NO DATA")
            continue

        size = sum(f.stat().st_size for f in files)
        col = DATE_COL.get(d.name)

        if d.name == "sced_60day":
            days, rows = audit_sced(files)
            col = "filename"
        elif col:
            days, rows = audit_generic(files, col)
        else:
            days, rows = [], sum(pq.ParquetFile(f).metadata.num_rows for f in files)

        print(f"\n{d.name}")
        print(f"  files {len(files):>5}   {human(size):>9}   {rows:>14,} rows"
              f"   (dates from {col})")

        if not days:
            print("  no usable date column")
            continue

        print(f"  covers        {days[0]} -> {days[-1]}  ({len(days)} days)")

        # Holes inside what we hold
        internal = gaps(days, days[0], days[-1])
        print(f"  internal gaps {summarize_gaps(internal)}")

        # Shortfall against the target window
        want_lo = max(WINDOW_START.date(), days[0])
        missing_before = (days[0] - WINDOW_START.date()).days
        if missing_before > 0:
            print(f"  ** starts {missing_before} days late "
                  f"(window begins {WINDOW_START.date()}) **")
        behind = (today - days[-1]).days
        if behind > 1:
            print(f"  ** ends {behind} days short of today **")


if __name__ == "__main__":
    main()
