# Registry

Two flat CSVs, one row per ERCOT unit, built from public data by
`python crosswalk/07_registry.py`. Every external attribute carries a method
column recording how the link was made, so you can filter by confidence.

| File | Rows | What |
|---|---|---|
| `storage.csv` | every storage unit in ERCOT's 60-day ESR disclosure (Dec 2025 →) | physical limits from telemetry, price node, owner/county where resolved, activity, and the benchmark's capture-gap anatomy where the unit was benchmarked |
| `generation.csv` | every wind and solar unit in the 60-day SCED disclosure | price node, plant/county/owner/coordinates/COD from EIA-860 where resolved, twelve months of measured curtailment, and the oversupply-vs-congestion split |

## `storage.csv`

| Column | Meaning | Source |
|---|---|---|
| `unit` | ERCOT resource name (`_ESR1` form, post-RTC+B) | ESR disclosure |
| `node` | settlement point the unit is priced at | name-stem match to price data (`optimization/data.py:_esr_nodes`) |
| `p_dis_mw`, `p_chg_mw` | max discharge / charge observed (HSL, −LSL) | telemetry maxima |
| `soc_max_mwh`, `soc_min_mwh` | usable energy window declared | telemetry maxima / minima |
| `duration_h` | `soc_max / p_dis` | derived |
| `county`, `owner` | physical plant | EIA-860 via site-stem match to the crosswalk (≈45% resolved) |
| `qse`, `dme` | scheduling / decision-making entity codes | ESR disclosure (most-common value) |
| `first_seen`, `last_seen`, `days_seen` | presence in the disclosure | ESR disclosure |
| `active_days` | days with \|Base Point\| > 1 MW | ESR disclosure |
| `on_share` | share of 5-min rows with status ON over the whole window | ESR disclosure |
| `benchmarked` | included in the capture-gap anatomy | `optimization/` |
| `capture_all_pct` | actual (energy + AS at RT MCPC) ÷ perfect-foresight ceiling, all unit-days | `optimization/anatomy.py` |
| `capture_on_pct` | same, fully-ON unit-days only (on_share ≥ 0.95 that day) | |
| `gap_window_pct`, `gap_reserves_net_pct`, `gap_dispatch_pct` | the anatomy's components as % of the unit's ON-day ceiling | |

## `generation.csv`

| Column | Meaning | Source |
|---|---|---|
| `resource`, `fuel` | ERCOT unit name and type (`PVGR` solar, `WIND`) | SCED disclosure |
| `settlement_point`, `sp_method` | price node and how it was linked (`exact` / `lcpN` / `eia_node` / `none`) | crosswalk step 02 |
| `qse`, `dme`, `max_hsl_mw`, `first_seen`, `last_seen` | | SCED disclosure |
| `plant_name`, `county`, `latitude`, `longitude`, `owner`, `utility`, `plant_nameplate_mw`, `operating_year` | physical plant | EIA-860 (2025), crosswalk step 04 |
| `eia_method`, `eia_score` | how the EIA link was made and its evidence score | crosswalk step 04 |
| `curtailed_gwh_12mo`, `curtailment_pct_12mo` | `HSL − Base Point` summed Aug 2025 – Jul 2026, status ON, interval length derived per day | `analysis/curtailment_by_county_owner.py` |
| `congestion_pct`, `oversupply_pct` | share of curtailed MWh with System Lambda > 0 and own-node LMP < 0 (congestion) vs Lambda ≤ 0 (oversupply), Sep 2025 – Jul 2026 | `analysis/curtailment_lambda_split.py` |

## Caveats

- Node links for storage are by name stem and were not individually validated
  the way generation links were (see `crosswalk/README.md`); treat a
  storage `node` as probable, not certain.
- EIA-860 is annual; plants commissioned after its snapshot are absent, and
  ERCOT stems that are acronyms or SPV names do not match by name. The
  unresolved ones, ranked by curtailment and by capacity, are in
  `crosswalk/aliases_todo.csv` — resolving the top twenty of each kind is the
  single highest-value hour of manual work in the project.
- All benchmark columns are price-taking ceilings settled at the unit's own
  node. AS revenue is priced at real-time MCPC only (day-ahead awards at DAM
  MCPC would be higher); see `optimization/WRITEUP.md`.
- SCED data lags 60 days. Nothing here is current.
