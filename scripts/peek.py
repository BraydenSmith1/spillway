"""
peek.py — look inside a Parquet file without writing any code.

Parquet is compressed and columnar, so you can't open it in Excel or read it
in a text editor. This prints what's inside.

    python scripts/peek.py sced_60day              # newest file in that folder
    python scripts/peek.py settlement_point_prices
    python scripts/peek.py data/raw/sced_esr/esr_2026-05-14.parquet

    python scripts/peek.py sced_60day --rows 30    # show more rows
    python scripts/peek.py sced_60day --cols       # just list the columns
    python scripts/peek.py sced_60day --csv        # export a sample to open in Excel

Only the rows it needs are read, so this is fast even on a 7 GB dataset.
"""

import sys
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
SAMPLE_DIR = ROOT / "data" / "samples"


def resolve(target):
    """Accept a dataset name or a path; return an actual .parquet file."""
    p = Path(target)
    if p.is_file():
        return p
    folder = p if p.is_dir() else RAW / target
    if not folder.is_dir():
        sys.exit(f"No such file or dataset: {target}\n"
                 f"Available: {', '.join(sorted(d.name for d in RAW.iterdir() if d.is_dir()))}")
    files = sorted(folder.glob("*.parquet"))
    if not files:
        sys.exit(f"{folder} has no .parquet files yet.")
    return files[-1]          # newest by name


def head_rows(path, n):
    """Read only the first n rows, not the whole file."""
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=n):
        return batch.to_pandas()
    return pd.DataFrame()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        sys.exit(__doc__)

    n = 10
    if "--rows" in sys.argv:
        n = int(sys.argv[sys.argv.index("--rows") + 1])

    path = resolve(args[0])
    pf = pq.ParquetFile(path)
    total = pf.metadata.num_rows
    size = path.stat().st_size / 1e6

    print(f"\n{path.relative_to(ROOT)}")
    print(f"{total:,} rows x {len(pf.schema_arrow.names)} columns   ({size:,.1f} MB on disk)")

    if "--cols" in flags:
        print("\ncolumns:")
        for name, typ in zip(pf.schema_arrow.names, pf.schema_arrow.types):
            print(f"   {name:<42} {typ}")
        return

    df = head_rows(path, max(n, 1000) if "--csv" in flags else n)

    if "--csv" in flags:
        SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
        out = SAMPLE_DIR / f"{path.stem}_sample.csv"
        df.head(1000).to_csv(out, index=False)
        print(f"\nWrote {min(len(df),1000):,} rows to {out.relative_to(ROOT)}")
        print("Open that in Excel or Numbers.")
        return

    pd.set_option("display.max_columns", 12)
    pd.set_option("display.width", 200)
    print(f"\nfirst {min(n, len(df))} rows:")
    print(df.head(n).to_string())

    if len(pf.schema_arrow.names) > 12:
        print(f"\n(showing 12 of {len(pf.schema_arrow.names)} columns — "
              f"use --cols to list them all)")


if __name__ == "__main__":
    main()
