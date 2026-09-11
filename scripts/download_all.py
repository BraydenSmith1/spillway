"""
download_all.py — downloads several ERCOT datasets one after another.

Run a quick test first:   python -u scripts/download_all.py test
Then the real thing:      python -u scripts/download_all.py
"""

import sys, os, time, traceback
from pathlib import Path
from datetime import datetime
sys.path.append(os.path.dirname(__file__))
from download import download_monthly

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"; LOGS.mkdir(exist_ok=True)

# =====================================================================
#  FILL THIS IN using the output of list_endpoints.py
#  Leave a line commented out (#) to skip that dataset.
# =====================================================================
JOBS = [
    # --- fast datasets first: hourly/periodic, small compared to SCED data ---
    {
        "name":     "settlement_point_prices",
        "endpoint": "/np6-905-cd/spp_node_zone_hub",
        "from":     "deliveryDateFrom",
        "to":       "deliveryDateTo",
    },
    {
        "name":     "solar_production",
        "endpoint": "/np4-745-cd/spp_hrly_actual_fcast_geo",
        "from":     "deliveryDateFrom",
        "to":       "deliveryDateTo",
    },
    {
        "name":     "wind_production",
        "endpoint": "/np4-742-cd/wpp_hrly_actual_fcast_geo",
        "from":     "deliveryDateFrom",
        "to":       "deliveryDateTo",
    },
    {
        "name":     "resource_outages",
        "endpoint": "/np3-233-cd/hourly_res_outage_cap",
        "from":     "operatingDateFrom",
        "to":       "operatingDateTo",
    },
    {
        "name":     "7d_load_forecast_by_forecast",
        "endpoint": "/np3-560-cd/7d_load_fcast_by_fzn",
        "from":     "postedDatetimeFrom",
        "to":       "postedDatetimeTo",
    },
    {
        "name":     "7d_load_forecast_by_weather_zone",
        "endpoint": "/np3-561-cd/7d_load_fcast_by_wzn",
        "from":     "postedDatetimeFrom",
        "to":       "postedDatetimeTo",
    },
    # --- day-ahead market: hourly, so small. The DA/RT spread is what
    #     storage arbitrage and hedging actually trade on. ---
    {
        "name":     "dam_settlement_point_prices",
        "endpoint": "/np4-190-cd/dam_stlmnt_pnt_prices",
        "from":     "deliveryDateFrom",
        "to":       "deliveryDateTo",
    },
    {
        "name":     "dam_shadow_prices",
        "endpoint": "/np4-191-cd/dam_shadow_prices",
        "from":     "deliveryDateFrom",
        "to":       "deliveryDateTo",
    },
    # DAM Hourly LMPs: ~13.9M rows/month because it is priced per electrical
    # bus (~20k of them) rather than per settlement point, so it does not join
    # cleanly to the rest of this project and costs ~18 hours to pull. Enable
    # only if you need bus-level day-ahead detail.
    # {
    #     "name":     "dam_hourly_lmp",
    #     "endpoint": "/np4-183-cd/dam_hourly_lmp",
    #     "from":     "deliveryDateFrom",
    #     "to":       "deliveryDateTo",
    # },

    # --- slow datasets last: SCED 5-minute granularity, millions of rows/month ---
    {
        "name":     "lmp_resource_nodes",
        "endpoint": "/np6-788-cd/lmp_node_zone_hub",
        "from":     "SCEDTimestampFrom",
        "to":       "SCEDTimestampTo",
    },
    {
         "name":     "shadow_prices",
         "endpoint": "/np6-86-cd/shdw_prices_bnd_trns_const",
         "from":     "SCEDTimestampFrom",
         "to":       "SCEDTimestampTo",
    },
]
# =====================================================================

FULL_START = "2025-09-01"   # last 12 months (was 2023-08-01 / 3 years)
FULL_END   = "2026-10-01"
TEST_START = "2026-06-01"
TEST_END   = "2026-07-01"


def log(msg):
    stamp = datetime.now().strftime("%H:%M:%S")
    line = f"{stamp}  {msg}"
    print(line, flush=True)                      # flush = you see it now
    with open(LOGS / "download_all.log", "a") as f:
        f.write(line + "\n")


def run(test_mode):
    active = [j for j in JOBS if "FILL_ME_IN" not in j["endpoint"]]
    skipped = len(JOBS) - len(active)

    log(f"{'TEST' if test_mode else 'FULL'} run — "
        f"{len(active)} datasets ready, {skipped} not filled in yet")

    if not active:
        log("Nothing to do. Fill in the JOBS list first.")
        return

    start = TEST_START if test_mode else FULL_START
    end   = TEST_END   if test_mode else FULL_END
    began = time.time()

    for i, job in enumerate(active, 1):
        log(f"")
        log(f"===== [{i}/{len(active)}] {job['name']} =====")
        t0 = time.time()
        try:
            download_monthly(
                name=job["name"] + ("_TEST" if test_mode else ""),
                endpoint=job["endpoint"],
                from_param=job["from"],
                to_param=job["to"],
                start=start,
                end=end,
                log=log,
            )
            log(f"DONE {job['name']} in {(time.time()-t0)/60:.1f} min")
        except Exception:
            log(f"FAILED {job['name']}")
            log(traceback.format_exc())
            continue                              # keep going

    log(f"\nALL FINISHED in {(time.time()-began)/60:.1f} minutes")


if __name__ == "__main__":
    run(test_mode=(len(sys.argv) > 1 and sys.argv[1] == "test"))