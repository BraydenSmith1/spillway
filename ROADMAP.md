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
- **Battery optimiser.** Pyomo MILP, benchmarked against real units' own
  dispatch, with day-ahead-informed and perfect-foresight bounds and AS
  revenue accounted for.
- **Capture-gap anatomy.** The ceiling-to-actual gap decomposed into
  commissioning, declared SOC window, reserves held (net of AS), and dispatch
  residual, per unit, with price-setting intervals flagged
  (`optimization/anatomy.py`).
- **Oversupply vs congestion, exactly.** System Lambda joined to every
  curtailed interval: 71% of solar and 84% of wind curtailment is congestion.
- **Registry.** `registry/storage.csv` and `registry/generation.csv`.
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
4. **Twenty manual crosswalk lookups, twice.** `crosswalk/aliases_todo.csv`
   ranks unplaced generation sites by curtailment and unplaced storage sites
   by capacity, interleaved. The top 20 of each lift placed coverage from ~45%
   to ~80% of curtailed MWh and from ~33% to well over half of storage MWh.
5. **Same-season RTC+B comparison.** Pull one more year of prices (cheap) so
   Feb–Jun 2025 can be compared with Feb–Jun 2026 without confounding the
   market redesign with the seasons.
6. **Constraint geography.** The oversupply-vs-congestion split is now exact
   (System Lambda, `analysis/curtailment_lambda_split.py`). What remains is
   naming the line: shadow-price `fromStation`/`toStation` map to physical
   lines, and joining them to plant coordinates would turn "which corridor"
   into "which line, on a map".

## Not planned

- A live forecast product. Ground-truth SCED data lags 60 days, so a live
  system can't be validated for two months after any change.
- Deep learning. Every problem here is tabular with clear features; trees
  and MILPs are the right tools.
