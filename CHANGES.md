# What changed, in plain terms

*2026-09-17. Written for the project owner, not for GitHub visitors — delete
or fold into the README before publishing if you like.*

## The big one: `optimization/` is new

A battery arbitrage model and a benchmark that tests it against real
batteries.

| File | What it does |
|---|---|
| `model.py` | The Pyomo model. Given a day of prices and a battery's limits, decides when to charge and discharge. Solved with HiGHS (free, installed). |
| `strategies.py` | Five ways to run the battery — from "ignore prices, charge at noon" to "know the future". |
| `data.py` | Loads prices, battery limits, actual dispatch and AS awards from `data/raw/`, all at 15-min resolution in Central time. |
| `benchmark.py` | Runs every strategy on every unit every day and reports $/kW-year and capture rates. |
| `fetch_as_prices.py` | Downloads the two ancillary-service price datasets (see below). |
| `WRITEUP.md` | The formulation, the constraints, the results, the caveats — your blog post's skeleton. |
| `results/` | Output of each benchmark run. |

**One finding you should understand before you present this**, because
someone will ask: the model uses binary variables to stop the battery
charging and discharging at once. Most tutorials skip them and argue the
LP never does it anyway because efficiency makes it wasteful. **That's true
only when prices are positive.** ERCOT prices go negative 7% of the time,
and when they do, the LP cheats: it burns stored energy to make room for
more paid charging. So the binaries stay. `tests/test_model.py` proves both
halves. This is the kind of detail that separates "ran a tutorial" from
"understood the problem."

## Two new datasets

- `data/raw/dam_as_prices/` — day-ahead ancillary-service clearing prices
  (`np4-188-cd`)
- `data/raw/rt_as_prices/` — real-time ancillary-service clearing prices
  (`np6-331-cd`), which only exist because RTC+B co-optimises reserves

Why: a battery that held capacity for reserves instead of arbitraging
wasn't being lazy, it was being paid. Without these you'd conclude real
batteries capture ~28% of possible revenue; with them the picture is fairer.

## Repo cleanup for publishing

- **`spillway-master-brief.md` has been removed from git history entirely**
  (`git filter-repo`). It's still on your disk and now gitignored. It was
  committed on 09-11 by an over-broad `git add` — my mistake. A copy is at
  `../spillway-master-brief.backup.md`. Since the repo was never pushed,
  nothing leaked.
- `LICENSE` — MIT.
- `pyproject.toml` — makes it a proper Python project; `pytest` finds tests.
- `tests/` — 18 tests. Model tests use synthetic prices; trap tests build
  tiny Parquet files. **None need the 9 GB of data**, so they run in CI.
- `.github/workflows/tests.yml` — GitHub Actions runs the tests on every push.
- `ROADMAP.md` replaces `TODO.md`. The old one referenced sections of the
  business brief that a public reader can't see.
- Hardcoded `/Users/braydensmith/...` paths removed from four scripts (and a
  test now fails if they come back).
- `requirements.txt` pinned to the versions actually installed.

## Earlier this week (already committed)

- **Two measurement errors found and fixed.** Timezone (Mountain vs Central,
  09-14) and SCED cadence (15-min vs 5-min at RTC+B, 09-17). Both are
  documented in `FINDINGS.md` §9 and have regression tests.
- `DATA_DICTIONARY.md` — all 228 columns explained.
- `crosswalk/` — resource → node → plant/county/owner.

## The result, in one table

30 real batteries, 199 days, each settled at its own node:

| Strategy | $/kW-yr | Capture |
|---|---|---|
| Fixed schedule (noon charge, dinner discharge, no prices) | $29 | 53% |
| Day-ahead informed (what an operator can actually do) | $28 | 51% |
| **What the batteries actually did** (energy + reserves) | **$21** | **39%** |
| Perfect foresight (the ceiling) | $54 | 100% |

Three things to be able to say out loud: (1) real units captured ~40% of the
ceiling and the best captured 70%, so 40% is an operating outcome, not
physics; (2) the dumb fixed schedule *beat* day-ahead optimisation because
ERCOT's evening peak is that regular and day-ahead prices are that unreliable
a guide to real-time; (3) four units lost $60–121k each in single days by
charging into the winter's two biggest spikes. Full narrative in
`optimization/WRITEUP.md` §"Reading the results".

## What you need to do

1. **Read `optimization/WRITEUP.md` end to end.** It's the blog post. Make
   sure you can explain every constraint and the negative-price finding
   without looking.
2. **Run it yourself once:** `python -m optimization.benchmark --units 5
   --start 2026-01-01 --end 2026-02-01`. Thirteen seconds. Watch the numbers
   come out.
3. **Decide what stays public.** `CHANGES.md` (this file) and
   `analysis/curtailment_by_unit.parquet` are fine either way. The brief is
   already excluded.
4. **Rewrite the README's opening** with the headline result once you've
   read the write-up — it should be *your* sentence, not mine.
5. **Create the GitHub repo, then:** `git remote add origin <url> && git push
   -u origin main`. CI will run the tests on the first push.
6. **Fill 20 rows of `crosswalk/aliases_todo.csv`** when you have an hour.
   Biggest remaining data improvement per unit of effort.

## What's next (the interesting part)

See `ROADMAP.md`. If you do one thing: **energy + AS co-optimisation**. The
optimiser currently ignores the revenue stream that post-RTC batteries
actually live on. Adding reserve products as decision variables is a real
extension of the MILP, it's the model ERCOT itself runs, and it's what would
make a Modo analyst sit up.
