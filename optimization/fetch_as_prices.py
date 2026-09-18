"""
fetch_as_prices.py — ancillary-service clearing prices, day-ahead and real-time.

Batteries earn from two things: moving energy through time (arbitrage) and
selling reserve capacity (ancillary services). A benchmark that only counts
the first will make every real battery look like it is leaving money on the
table when it is actually being paid for the second. These two datasets close
that gap.

    dam_as_prices   np4-188-cd  DAM MCPC — hourly clearing price per AS product
    rt_as_prices    np6-331-cd  Real-time clearing prices for capacity, 15-min
                                (exists because RTC+B co-optimises AS in SCED)

    python optimization/fetch_as_prices.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from download import download_monthly

for name, endpoint in [("dam_as_prices", "/np4-188-cd/dam_clear_price_for_cap"),
                       ("rt_as_prices",  "/np6-331-cd/rt_clear_price_cap")]:
    print(f"===== {name} =====", flush=True)
    download_monthly(name=name, endpoint=endpoint,
                     from_param="deliveryDateFrom", to_param="deliveryDateTo",
                     start="2025-09-01", end="2026-10-01")
