# Roadmap

What's done, what's next, and roughly why. For the analysis so far see
`analysis/FINDINGS.md`; for the optimiser see `optimization/WRITEUP.md`.

## Done

- **Pipeline.** ERCOT public API → Parquet, 12 datasets, ~9 GB. Resumable,
  chunked, watchdogged; works around two ERCOT API quirks and one bug in the
  latest `gridstatus` release. `scripts/audit.py` reports coverage.
- **Crosswalk.** Resource → price node (91% of wind/solar, validated against
  price behaviour) → plant, county, owner via EIA-860 (42%).
- **Curtailment measured.** System-wide 5–6%; the worst sites 22–31%; 96% of
  it at a negative own-node price. Concentrated: 50 sites ≈ 70%.
- **Battery optimiser.** Pyomo MILP, benchmarked against 30 real units' own
  dispatch, with day-ahead-informed and perfect-foresight bounds and AS
  revenue accounted for.
- **Tests + CI.** 18 tests on synthetic data, including one for each
  data-quality trap that produced a wrong answer along the way.

## Next

1. **Energy + AS co-optimisation.** The optimiser currently trades only
   energy; the real unit's reserve revenue is *counted* but not *chosen*.
   Add reserve products as decision variables with capacity coupling. This
   is the model ERCOT itself runs post-RTC+B and the single biggest
   improvement available.
2. **Rolling-horizon dispatch.** Replace the daily "decide at midnight"
   structure with a receding horizon that re-plans every interval as
   real-time prices arrive. Closer to how an operator actually runs, and
   it bounds what a good short-term forecast is worth.
3. **A curtailment forecast, honestly scored.** LightGBM quantile regression
   for P10/P50/P90 curtailment 24–48h ahead at a node, split in time,
   scored per node against persistence and seasonal-naive baselines.
4. **Twenty manual crosswalk lookups.** `crosswalk/aliases_todo.csv` ranks
   the unplaced sites by curtailment; resolving the top 20 lifts placed
   coverage from ~45% to ~80% of curtailed MWh.
5. **Same-season RTC+B comparison.** Pull one more year of prices (cheap) so
   Feb–Jun 2025 can be compared with Feb–Jun 2026 without confounding the
   market redesign with the seasons.
6. **Constraint geography.** Shadow-price `fromStation`/`toStation` map to
   physical lines; joining them to plant coordinates would turn "which
   constraint" into "which line, on a map".

## Not planned

- A live forecast product. Ground-truth SCED data lags 60 days, so a live
  system can't be validated for two months after any change.
- Deep learning. Every problem here is tabular with clear features; trees
  and MILPs are the right tools.
