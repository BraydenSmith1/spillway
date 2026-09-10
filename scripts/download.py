"""
download.py — pulls a dataset month by month into separate Parquet files.
Safe to re-run: skips completed months already on disk. The current
in-progress month is always re-fetched so it eventually gets filled in.
"""

import sys, os
from pathlib import Path
import pandas as pd
sys.path.append(os.path.dirname(__file__))
from ercot import fetch

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"


def download_monthly(name, endpoint, from_param, to_param,
                     start="2023-08-01", end="2026-08-01", page_size=5000,
                     log=print):
    out_dir = RAW / name
    out_dir.mkdir(parents=True, exist_ok=True)

    today = pd.Timestamp.now().normalize()
    months = pd.date_range(start, end, freq="MS")
    for i, m0 in enumerate(months[:-1]):
        m1 = months[i + 1]
        tag = m0.strftime("%Y-%m")
        out = out_dir / f"{name}_{tag}.parquet"

        # A month whose window extends past today is still in progress —
        # always re-fetch it, even if a (partial) file already exists,
        # so the last few days aren't permanently missed.
        in_progress = m1 > today
        if out.exists() and not in_progress:
            log(f"  skip {tag}")
            continue

        try:
            df = fetch(endpoint, {
                from_param: m0.strftime("%Y-%m-%d"),
                to_param: (m1 - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                "size": page_size,
            })
        except Exception as e:
            log(f"  {tag}: FAILED — {e}")
            continue

        if df.empty:
            log(f"  {tag}: no data")
            continue

        df.to_parquet(out, index=False)
        note = " (in progress, will refresh next run)" if in_progress else ""
        log(f"  {tag}: {len(df):,} rows{note}")


if __name__ == "__main__":
    download_monthly(
        name="settlement_point_prices",
        endpoint="/np6-905-cd/spp_node_zone_hub",
        from_param="deliveryDateFrom",
        to_param="deliveryDateTo",
    )