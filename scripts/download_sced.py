"""
download_sced.py — 60-day SCED disclosure files.

Each archive ERCOT publishes is a ~47 MB zip holding several reports. Two of
them matter here:

  * sced_gen_resource — generators: HSL, Base Point, telemetered output.
    HSL minus Base Point is curtailment.
  * sced_esr          — energy storage: charge/discharge, ancillary service
    awards, and State of Charge. Batteries appear in no other dataset in
    this project.

Published on a 60-day delay, so recent dates return nothing. Safe to re-run:
a day is skipped only when every file it would produce already exists.
"""

import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from gridstatus.ercot_api.ercot_api import ErcotAPI

load_dotenv()
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
GEN_OUT = RAW / "sced_60day"
ESR_OUT = RAW / "sced_esr"
for d in (GEN_OUT, ESR_OUT):
    d.mkdir(parents=True, exist_ok=True)

api = ErcotAPI(
    username=os.getenv("ERCOT_USERNAME"),
    password=os.getenv("ERCOT_PASSWORD"),
    public_subscription_key=os.getenv("ERCOT_SUBSCRIPTION_KEY"),
)

end = pd.Timestamp.now(tz="US/Central").normalize() - pd.DateOffset(days=62)
start = pd.Timestamp("2023-08-01", tz="US/Central")

# Storage capture starts at RTC+B go-live (2025-12-05), because that is when
# the report begins to exist. Checked directly: delivery 2025-11-15 returns 0
# ESR rows, 2025-12-10 returns 90,770. Batteries got their own SCED disclosure
# when real-time co-optimization went live. Reaching back further just
# re-downloads ~47 MB archives to find no storage report in them.
ESR_START = pd.Timestamp("2025-12-01", tz="US/Central")

for day in pd.date_range(start, end, freq="D"):
    tag = day.strftime("%Y-%m-%d")
    gen_file = GEN_OUT / f"gen_resource_{tag}.parquet"
    esr_file = ESR_OUT / f"esr_{tag}.parquet"

    need_gen = not gen_file.exists()
    need_esr = day >= ESR_START and not esr_file.exists()
    if not (need_gen or need_esr):
        continue

    try:
        result = api.get_60_day_sced_disclosure(date=tag, process=True)
    except Exception as e:
        print(f"{tag}: failed — {e}", flush=True)
        continue

    wrote = []

    if need_gen:
        gen = result.get("sced_gen_resource")
        if gen is None or len(gen) == 0:
            print(f"{tag}: gen empty", flush=True)
        else:
            gen.to_parquet(gen_file, index=False)
            wrote.append(f"gen {len(gen):,}")

    if need_esr:
        esr = result.get("sced_esr")
        # ESR is listed as "when available" — older archives, especially before
        # RTC+B went live in Dec 2025, may not carry a storage report at all.
        if esr is None or len(esr) == 0:
            print(f"{tag}: no esr report", flush=True)
        else:
            esr.to_parquet(esr_file, index=False)
            wrote.append(f"esr {len(esr):,}")

    if wrote:
        print(f"{tag}: {' | '.join(wrote)} rows", flush=True)
