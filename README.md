# Spillway

**Open, reproducible analysis of nodal electricity prices in ERCOT (the Texas grid).**

> ⚠️ **TODO — the most important line in this README.** Replace this with the one
> specific question this project answers, and the headline number you found. E.g.
> *"Battery storage at West Texas resource nodes would have earned 40% more than
> at the North Hub in 2026 — here's the node-by-node breakdown."*

---

## Why this exists

ERCOT publishes an enormous amount of market data for free, but it arrives as raw,
paginated API responses with cryptic location codes and no context. Most usable
nodal analysis lives behind commercial platforms that cost thousands of dollars per
seat. This project builds an open, reproducible pipeline from ERCOT's public API to
a queryable database, and uses it to answer a specific question about the Texas market.

## The data

All data comes from the [ERCOT Public API](https://apiexplorer.ercot.com/) and covers
**the entire ERCOT interconnection** — roughly 90% of Texas load, operating as a single
grid largely isolated from the rest of the US.

| Dataset | What it is | Granularity |
|---|---|---|
| `settlement_point_prices` | Real-time price at every pricing location | 15 min × ~1,115 points |
| `lmp_resource_nodes` | Locational marginal price at generator nodes | 5 min (SCED) |
| `shadow_prices` | Cost of each binding transmission constraint | 5 min (SCED) |
| `sced_60day` | Per-generator dispatch: output, limits, fuel type | 5 min, 60-day lag |
| `solar_production` | Solar output, actual vs. forecast, by region | hourly |
| `wind_production` | Wind output, actual vs. forecast, by region | hourly |
| `resource_outages` | Generation capacity offline | hourly |
| `7d_load_forecast_*` | Demand forecasts by zone / weather zone | hourly, 7-day horizon |

**Scale:** ~7 GB of Parquet and growing. Prices in a single month range from
**-$251/MWh to $10,152/MWh**, and **5.1% of all price intervals are negative** —
the grid periodically paying generators to stop.

**Coverage:** last 12 months (rolling). Older history can be pulled by widening
`FULL_START` in `scripts/download_all.py`.

### Known data quality issues

- `sced_60day` is missing **54 of 1,075 expected days (~5%)**, mostly scattered gaps
  in Dec 2025 and Mar 2026. <!-- TODO: document how you handle these -->
- The 60-day SCED disclosure is published with a deliberate 60-day lag, so the most
  recent two months of generator-level data are never available.
- ERCOT did not publish some datasets before late 2023.

## Setup

```bash
# 1. Clone and create a virtual environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Add your ERCOT credentials
cp .env.example .env    # then edit .env with your real values

# 3. Start the database
docker compose up -d

# 4. Create the tables
psql -h localhost -p 5433 -U spillway -d spillway -f sql/01_schema.sql

# 5. Download the data (long-running; auto-restarts if interrupted)
./scripts/run_download.sh &
tail -f logs/download_all.out    # watch progress
```

## Project structure

```
spillway/
├── scripts/            # pipeline code
│   ├── ercot.py            # API client: auth + pagination
│   ├── download.py         # pulls one dataset, month by month
│   ├── download_all.py     # runs all 8 datasets in sequence
│   ├── run_download.sh     # keeps the download alive (caffeinate + auto-restart)
│   ├── db.py               # database connection
│   └── status.py           # what's downloaded, what's missing
├── sql/01_schema.sql   # TimescaleDB table definitions
├── ingest/             # TODO: Parquet -> database
├── crosswalk/          # TODO: node codes -> real power plants
├── notebooks/          # exploration (numbered: 01_, 02_, ...)
├── analysis/           # TODO: the actual analysis
├── reports/figures/    # charts used in this README
└── data/               # NOT in git — regenerate with scripts/download_all.py
    ├── raw/                # immutable API output
    ├── clean/              # processed
    └── warehouse/
```

## Status

- [x] ERCOT API client with auth, pagination, retry/backoff
- [x] Download pipeline (resumable, auto-restarting)
- [x] `settlement_point_prices` — complete
- [x] `sced_60day` — 95% complete (1,021 days, 7 GB)
- [x] All datasets downloaded (~9.2 GB, ~470M rows)
- [ ] Ingest Parquet into TimescaleDB
- [x] Crosswalk: settlement point → physical asset (`crosswalk/`, 91% node / 42% owner coverage)
- [x] First analysis: curtailment valued at own-node price (`analysis/FINDINGS.md`)
- [ ] Findings written up

## Findings

<!-- TODO: 3-5 charts and what they show. This section is what people actually read. -->


