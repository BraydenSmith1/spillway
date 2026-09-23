"""
fetch_lambda.py — ERCOT System Lambda, real-time (per SCED run) and day-ahead.

LMP = System Lambda + congestion component (ERCOT has no marginal-loss term).
So lambda is the exact reference for splitting a negative nodal price into
"the whole grid was oversupplied" (lambda <= 0) versus "this node was stuck
behind a full line" (lambda > 0, LMP < 0). One row per SCED run — tiny.

    python scripts/fetch_lambda.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from download import download_monthly

for name, endpoint, f, t in [
    ("sced_system_lambda", "/np6-322-cd/sced_system_lambda", "SCEDTimestampFrom", "SCEDTimestampTo"),
    ("dam_system_lambda",  "/np4-523-cd/dam_system_lambda",  "deliveryDateFrom",  "deliveryDateTo"),
]:
    print(f"===== {name} =====", flush=True)
    download_monthly(name=name, endpoint=endpoint, from_param=f, to_param=t,
                     start="2025-08-01", end="2026-10-01")
