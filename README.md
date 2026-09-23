# Spillway

**How much money are Texas batteries leaving on the table — and why?** An
ERCOT data pipeline, a Pyomo battery optimiser benchmarked against what **129
real batteries** actually did, and the gap between them decomposed into named
pieces.

<p align="center"><img src="optimization/results/fig_waterfall.png" width="720"></p>

## The headline

Every active, node-linked storage unit in ERCOT, Dec 2025 – Jul 2026, settled
at its own price node, opening each day at its real state of charge. On
fully-ON unit-days, with commissioning and outage days excluded:

| Strategy | $/kW-year | Capture vs. perfect foresight |
|---|---|---|
| Fixed schedule (charge at noon, discharge at dinner) | $25 | 52% |
| Day-ahead informed — *what a real operator can do* | $23 | 47% |
| **Actual — what the batteries did (energy + reserves)** | **$21** | **42%** |
| Perfect foresight — *the ceiling* | $49 | 100% |

Including commissioning days, capture is 39%. **Where the gap went**,
fleet-wide: 12% of the ceiling sat on days the unit wasn't fully operational,
5% in the SOC window operators declared, 18% in reserves held, and 27% in
dispatch. On a further quarter of the ceiling the unit's own offer set the
price, where a price-taking ceiling isn't credible at all.

**Read this as energy-arbitrage capture, not total revenue capture.** Reserve
revenue here is priced at real-time MCPC only; ERCOT procures most ancillary
services day-ahead at higher prices, and those awards need a disclosure this
project hasn't pulled yet. Counting the full day-ahead stack would raise
"actual" and narrow the gap. Method, results and the rest of the caveats:
**[`optimization/WRITEUP.md`](optimization/WRITEUP.md)**.

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
   when prices are non-negative. ERCOT prices go negative 7% of the time, and
   the LP relaxation then burns stored energy through the round-trip loss to
   absorb more paid charging — an arbitrage no inverter can perform. The
   benchmark uses the MILP; `tests/test_model.py` demonstrates both
   behaviours.

## The other half: curtailment

The same pipeline measures how much renewable energy ERCOT throws away. Full
analysis in [`analysis/FINDINGS.md`](analysis/FINDINGS.md):

- **Curtailment is 5–6% system-wide and 22–31% at the worst sites.** The 50
  most-curtailed solar units account for 70% of all solar curtailment.
- **96% of curtailed energy is spilled at a negative own-node price.** Valued
  at the node, 3.2 TWh of curtailed solar over six months was worth −$27 M to
  its owners.
- **It's congestion, not glut.** Joining ERCOT's System Lambda to every
  curtailed interval: 71% of solar and 84% of wind curtailment happened while
  the grid as a whole still wanted the power.
- **Batteries charge ~700 GWh/month straight through the midday surplus**,
  with an implied fleet round-trip efficiency of 82%.

## What's in the repo

```
scripts/            ERCOT API client, resumable downloaders, coverage audit
crosswalk/          resource → price node → plant / county / owner (EIA-860)
registry/           the crosswalk as CSVs: storage.csv, generation.csv
analysis/           curtailment, prices, congestion; FINDINGS.md
optimization/       Pyomo MILP, strategies, benchmark, anatomy; WRITEUP.md
tests/              27 tests, all synthetic — no download needed
DATA_DICTIONARY.md  every column of every dataset, and the join traps
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

python -m optimization.benchmark --units 30     # ~15 min (--all: fleet, ~4.5 h)
python -m optimization.report                    # tables + figures
python -m optimization.price_setting --tag fleet # offer-curve price-setting flags
python -m optimization.anatomy --tag fleet       # the waterfall
pytest                                           # 27 tests, ~3 s
```

Everything downstream of the API is deterministic; every number in the
write-up regenerates from `optimization/results/`.

## Things to know before trusting a number

Documented in full in [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md) and encoded
as regression tests in `tests/test_traps.py`:

- SCED ran every **15 minutes before RTC+B (2025-12-05) and every 5 after**.
  Interval length is derived from the data, never hardcoded — assuming 5
  minutes throughout understates pre-RTC energy threefold.
- SCED timestamps are **Central**; every DuckDB session is pinned to it.
- `HSL − Base Point` is curtailment **only for wind and solar**.
- A battery reporting `ONTEST` is commissioning, not trading. Benchmarks that
  don't filter on `Telemetered Resource Status` blend test schedules into
  operating results — this one did until 2026-09-23.
- Reserve revenue is real-time MCPC only; day-ahead awards would raise it.
- ~14 SCED days are permanently unpublished by ERCOT; load forecasts only
  exist from 2026-03; the ESR storage disclosure begins at RTC+B go-live.
- `gridstatus` 0.36.0 silently drops every SCED day after 2026-06-25
  (`Unknown curve type found`), and ERCOT's timestamp-typed range parameters
  drop the last day of every month. Both worked around in `scripts/`.

## What's next

Energy and ancillary services **co-optimised** in one model — choosing between
them each interval, the way ERCOT itself does post-RTC+B — priced against the
full day-ahead and real-time award stack. That closes the measurement gap in
the headline above and turns the benchmark into a revenue model.

## License

MIT.
