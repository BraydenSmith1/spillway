"""
download_sced.py — 60-day SCED disclosure files.
These carry HSL and Base Point: the raw material for measuring curtailment.
Published on a 60-day delay, so recent dates return nothing.
"""

import os
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv
from gridstatus.ercot_api.ercot_api import ErcotAPI

load_dotenv()
OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "sced_60day"
OUT.mkdir(parents=True, exist_ok=True)

api = ErcotAPI(
    username=os.getenv("ERCOT_USERNAME"),
    password=os.getenv("ERCOT_PASSWORD"),
    public_subscription_key=os.getenv("ERCOT_SUBSCRIPTION_KEY"),
)

end = pd.Timestamp.now(tz="US/Central").normalize() - pd.Timedelta(days=62)
start = pd.Timestamp("2023-08-01", tz="US/Central")

for day in pd.date_range(start, end, freq="D"):
    tag = day.strftime("%Y-%m-%d")
    out = OUT / f"gen_resource_{tag}.parquet"
    if out.exists():
        continue

    try:
        result = api.get_60_day_sced_disclosure(date=tag, process=True)
    except Exception as e:
        print(f"{tag}: failed — {e}")
        continue

    gen = result.get("sced_gen_resource")
    if gen is None or len(gen) == 0:
        print(f"{tag}: empty")
        continue

    gen.to_parquet(out, index=False)
    print(f"{tag}: {len(gen):,} rows")