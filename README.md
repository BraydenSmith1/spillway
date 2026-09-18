# Spillway

**How much money are Texas batteries leaving on the table?** An ERCOT data
pipeline, a nodal curtailment analysis, and a Pyomo battery-arbitrage
optimiser benchmarked against what 30 real batteries actually did.

<p align="center"><img src="optimization/results/fig_strategies.png" width="720"></p>

## The headline

Over 199 days (Dec 2025 – Jul 2026), settled at each unit's own price node:

| Strategy | $/kW-year | Capture vs. perfect foresight |
|---|---|---|
| Fixed schedule (charge at noon, discharge at dinner) | $29 | 53% |
| Day-ahead informed — *what a real operator can do* | $28 | 51% |
| **Actual — what the batteries did (energy + reserves)** | **$21** | **39%** |
| Perfect foresight — *the ceiling* | $54 | 100% |

A perfect real-time forecast is worth **$27/kW-year** over dispatching on
day-ahead prices — that gap is what a forecasting product sells. Full write-up,
formulation, and caveats: **[`optimization/WRITEUP.md`](optimization/WRITEUP.md)**.

## Why this isn't the usual battery tutorial

Everyone optimises a battery against a price series. Three things here are
different:

1. **There's an answer key.** ERCOT's 60-day SCED disclosure reports every
   storage unit's dispatch and state of charge at 5-minute resolution. The
   optimiser is scored against real behaviour, not against itself.
2. **It runs at each unit's own node**, via a resource→settlement-point
   crosswalk validated against price behaviour — not a hub proxy.
3. **The LP shortcut is wrong in ERCOT.** Dropping the charge/discharge mode
   binaries ("efficiency makes simultaneous operation wasteful") holds only
   when prices are non-negative. ERCOT prices go negative 7% of the time,
   and the LP relaxation then "burns" stored energy to absorb more paid
   charging. The benchmark uses the MILP; `tests/test_model.py` demonstrates
   both behaviours.

## What else came out of the data

From 9.2 GB / 470 M rows of ERCOT public API data, analysed in
[`analysis/FINDINGS.md`](analysis/FINDINGS.md):

- **Renewable curtailment is 5–6% system-wide and 22–31% at the worst
  sites.** The 50 most-curtailed solar units account for 70% of all solar
  curtailment.
- **96% of curtailed energy is spilled at a negative own-node price.**
  Valued at the node, 3.2 TWh of curtailed solar over six months was worth
  −$27 M to its owners.
- **Batteries charge ~700 GWh/month straight through the midday surplus**,
  with an implied fleet round-trip efficiency of 82%.
- **`gridstatus` 0.36.0 silently drops every SCED day after 2026-06-25**
  (`Unknown curve type found`), and ERCOT's timestamp-typed range parameters
  drop the last day of every month. Both worked around in `scripts/`.

## What's in the repo

```
scripts/          ERCOT API client, resumable downloaders, coverage audit
crosswalk/        resource → price node → plant / county / owner (EIA-860)
analysis/         curtailment, prices, congestion, batteries; FINDINGS.md
optimization/     Pyomo MILP, five strategies, benchmark, report; WRITEUP.md
tests/            18 tests, all on synthetic data — no download needed
DATA_DICTIONARY.md  every column of every dataset, acronyms explained
```

## Reproduce it

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # add your free ERCOT API credentials

python scripts/download_all.py       # ~1 day for the full window; resumable
./scripts/run_sced.sh                # 60-day disclosures (generators + storage)
python optimization/fetch_as_prices.py
python crosswalk/build.py            # ~3 min
python scripts/audit.py              # what's on disk, where the gaps are

python -m optimization.benchmark --units 30     # ~10 min
python -m optimization.report                    # tables + figures
pytest                                           # 18 tests, ~3 s
```

Everything downstream of the API is deterministic; the numbers in the
write-up regenerate from `optimization/results/`.

## Things to know before trusting a number

Documented in full in [`analysis/FINDINGS.md` §9](analysis/FINDINGS.md) and
encoded as regression tests:

- SCED ran every **15 minutes before RTC+B (2025-12-05) and every 5 after**.
  Interval length is derived from the data, never hardcoded.
- SCED timestamps are **Central**; every DuckDB session is pinned to it.
- `HSL − Base Point` is curtailment **only for wind and solar**.
- ~14 SCED days are permanently unpublished by ERCOT; load forecasts only
  exist from 2026-03; the ESR storage disclosure begins at RTC+B go-live.

## Roadmap

[`ROADMAP.md`](ROADMAP.md). The next real step is energy + ancillary-service
co-optimisation — the model ERCOT itself runs post-RTC+B.

## License

MIT.
