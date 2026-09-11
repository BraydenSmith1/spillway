"""
download.py — pulls a dataset month by month into separate Parquet files.

Safe to re-run, and safe to interrupt:
  * Completed months already on disk are skipped.
  * A month that was cut off mid-download resumes from the last saved chunk
    instead of starting the whole month over.
  * The current in-progress month is always re-fetched so it fills in.
"""

import sys, os, re, shutil
from pathlib import Path
import pandas as pd
sys.path.append(os.path.dirname(__file__))
from ercot import iter_pages, to_frame

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

# Pages held in memory before being written to a chunk file. 10 pages of
# 50,000 rows is ~500k rows — a few minutes of work, the most an interruption
# can cost. Keep CHUNK_PAGES * page_size around this size: too large and an
# interruption is expensive, too small and we write thousands of tiny files.
CHUNK_PAGES = 10

# ERCOT accepts pages far larger than the 5,000 this project started with —
# tested good to 200,000. Each request costs roughly the same regardless of
# size, so bigger pages mean proportionally fewer round trips: a month of
# nodal LMP drops from ~1,800 requests to under 200.
PAGE_SIZE = 50_000


def _is_timestamp_param(name):
    """True for SCEDTimestampFrom / postedDatetimeFrom style parameters."""
    n = name.lower()
    return "timestamp" in n or "datetime" in n


def _flush(part_dir, page, rows, cols):
    """Write buffered rows to a numbered chunk file."""
    if not rows:
        return
    part_dir.mkdir(parents=True, exist_ok=True)
    to_frame(rows, cols).to_parquet(part_dir / f"part_{page:06d}.parquet",
                                    index=False)


def _resume_point(part_dir):
    """Where to pick up: one past the highest page already saved."""
    if not part_dir.exists():
        return 1, 0
    parts = list(part_dir.glob("part_*.parquet"))
    if not parts:
        return 1, 0
    last = max(int(re.search(r"part_(\d+)", p.name).group(1)) for p in parts)
    return last + 1, len(parts)


def download_monthly(name, endpoint, from_param, to_param,
                     start="2025-09-01", end="2026-10-01", page_size=PAGE_SIZE,
                     log=print):
    out_dir = RAW / name
    out_dir.mkdir(parents=True, exist_ok=True)

    today = pd.Timestamp.now().normalize()
    months = pd.date_range(start, end, freq="MS")
    for i, m0 in enumerate(months[:-1]):
        m1 = months[i + 1]
        tag = m0.strftime("%Y-%m")
        out = out_dir / f"{name}_{tag}.parquet"

        # Chunk files are numbered by page, so chunks written at one page size
        # point at the wrong offsets if resumed at another. Making the size
        # part of the directory name means a size change starts clean instead
        # of silently stitching together mismatched data.
        part_dir = out_dir / f".partial_{tag}_s{page_size}"
        for old in out_dir.glob(f".partial_{tag}*"):
            if old != part_dir:
                log(f"  {tag}: discarding chunks from a different page size")
                shutil.rmtree(old, ignore_errors=True)

        # A month whose window extends past today is still in progress —
        # always re-fetch it, even if a (partial) file already exists,
        # so the last few days aren't permanently missed.
        in_progress = m1 > today

        # A month saved *while* it was still in progress holds only part of
        # the month. Without this marker the skip below would freeze that
        # partial file in place forever once the month settled.
        stale = out_dir / f".incomplete_{tag}"

        if out.exists() and not in_progress and not stale.exists():
            log(f"  skip {tag}")
            continue

        if stale.exists() and not in_progress:
            log(f"  {tag}: re-fetching (was saved mid-month, now settled)")

        # An in-progress month is still changing underneath us, so old
        # chunks may not line up with a fresh pass. Start it clean.
        if in_progress and part_dir.exists():
            shutil.rmtree(part_dir)

        start_page, n_parts = _resume_point(part_dir)
        if start_page > 1:
            log(f"  {tag}: resuming at page {start_page} "
                f"({n_parts} chunks already saved)")

        # ERCOT has two flavours of range parameter and they do NOT behave the
        # same way. A *Date* param ("deliveryDateTo") is inclusive of the whole
        # day. A *Timestamp* / *Datetime* param ("SCEDTimestampTo") reads a
        # bare date as midnight, so the last day of the range comes back empty
        # — silently losing one day in every month.
        last_day = m1 - pd.Timedelta(days=1)
        if _is_timestamp_param(from_param):
            lo = m0.strftime("%Y-%m-%dT00:00:00")
            hi = last_day.strftime("%Y-%m-%dT23:59:59")
        else:
            lo = m0.strftime("%Y-%m-%d")
            hi = last_day.strftime("%Y-%m-%d")

        params = {from_param: lo, to_param: hi, "size": page_size}

        buf, cols, last_page = [], None, start_page - 1
        try:
            for page, _total, batch, page_cols in iter_pages(
                    endpoint, params, start_page=start_page, log=log):
                cols = page_cols or cols
                buf.extend(batch)
                last_page = page
                if page % CHUNK_PAGES == 0:
                    _flush(part_dir, page, buf, cols)
                    buf = []
        except Exception as e:
            # Save what we have so the next run resumes instead of restarting.
            _flush(part_dir, last_page, buf, cols)
            log(f"  {tag}: interrupted at page {last_page} — "
                f"progress saved, will resume next run ({e})")
            continue

        _flush(part_dir, last_page, buf, cols)

        chunks = sorted(part_dir.glob("part_*.parquet")) if part_dir.exists() else []
        if not chunks:
            log(f"  {tag}: no data")
            continue

        df = pd.concat([pd.read_parquet(c) for c in chunks], ignore_index=True)
        df.to_parquet(out, index=False)
        shutil.rmtree(part_dir)

        # Leave a breadcrumb if this month isn't final yet, so a later run
        # knows to replace it rather than skipping it as complete.
        if in_progress:
            stale.touch()
        elif stale.exists():
            stale.unlink()

        note = " (in progress, will refresh next run)" if in_progress else ""
        log(f"  {tag}: {len(df):,} rows{note}")


if __name__ == "__main__":
    download_monthly(
        name="settlement_point_prices",
        endpoint="/np6-905-cd/spp_node_zone_hub",
        from_param="deliveryDateFrom",
        to_param="deliveryDateTo",
    )
