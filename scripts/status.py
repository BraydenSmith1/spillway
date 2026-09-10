"""Tells you exactly what's been downloaded and what's missing."""

from pathlib import Path
import pandas as pd

OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "sced_60day"
files = sorted(OUT.glob("gen_resource_*.parquet"))

print(f"Files on disk:  {len(files)}")
print(f"Total size:     {sum(f.stat().st_size for f in files)/1e6:,.0f} MB")

tiny = [f for f in files if f.stat().st_size < 10_000]
print(f"Suspiciously small files: {len(tiny)}")

dates = sorted(pd.to_datetime(
    [f.stem.replace("gen_resource_", "") for f in files]))
print(f"Date range:     {dates[0]:%Y-%m-%d} to {dates[-1]:%Y-%m-%d}")

start = pd.Timestamp("2023-08-01")
end = pd.Timestamp.now().normalize() - pd.Timedelta(days=62)
expected = pd.date_range(start, end, freq="D")
missing = [d for d in expected if d not in set(dates)]

print(f"\nExpected days:  {len(expected)}")
print(f"Missing days:   {len(missing)}  ({len(missing)/len(expected)*100:.0f}%)")
if missing:
    print(f"First few gaps: {[f'{d:%Y-%m-%d}' for d in missing[:8]]}")