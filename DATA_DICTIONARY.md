# Data Dictionary

*Every variable in `data/raw/`, 2026-09-17. 12 datasets, 228 columns.*

Schemas pulled directly from the Parquet files. Definitions of ERCOT's
acronyms are my reading of the data plus standard market usage — **the ones
marked ⚠️ are worth confirming against the ERCOT Nodal Protocols before you
quote them to anyone.**

Quick look at any of these: `python scripts/peek.py <dataset> --cols`

---

## The four generator dispatch variables that matter most

These live in `sced_60day` and `sced_esr` and carry most of the project's
value. Everything about curtailment comes from the relationship between them.

| Variable | Meaning |
|---|---|
| **`HSL`** | High Sustained Limit — what the unit **could** produce right now. For wind/solar this is live available power, so it moves with the weather. |
| **`Base Point`** | What ERCOT **instructed** the unit to produce this interval. The dispatch order. |
| **`Telemetered Net Output`** | What the unit **actually** produced. Proves the instruction was followed. |
| **`LSL`** | Low Sustained Limit — minimum stable output. Non-zero for thermal units that can't turn down past a point. |

**`HSL − Base Point` = curtailment.** `Telemetered Net Output` tracking
`Base Point` is what confirms the gap is a dispatch decision rather than a
data artifact.

---

## 1. `sced_60day` — generator dispatch, per SCED run (43 cols)

*Per generator, every SCED run. Published on a 60-day delay. 165.7M rows.*
*Cadence: **15-minute** through 2025-12-04, **5-minute** after — see trap 3.*

**Identity**
| Column | Meaning |
|---|---|
| `SCED Timestamp` | when SCED ran (timezone-aware, US/Central) |
| `Resource Name` | ERCOT's unit code, e.g. `GALLOWAY_SOLAR1` |
| `Resource Type` | fuel code — `PVGR` solar, `WIND`, `PWRSTR` storage (pre-RTC only), `CCGT90`/`SCGT90`/`SCLE90`/`CCLE90` gas, `CLLIG` coal/lignite, `NUC`, `HYDRO`, `DSL` diesel, `GSREH`/`GSNONR`/`GSSUP` gas steam |
| `QSE` | Qualified Scheduling Entity — who schedules it into the market |
| `DME` | Decision Making Entity — who actually operates it |
| `Telemetered Resource Status` | `ON`, `OFF`, `OUT`, `ONTEST`, `ONOS`, `OFFQS`, `EMR`, `STARTUP`, `ONSC`. **Filter to `ON`** — an offline unit isn't curtailed. |

**Dispatch limits**
| Column | Meaning | Populated |
|---|---|---|
| `HSL` / `LSL` | high / low **sustained** limit — physical capability | always |
| `HDL` / `LDL` | high / low **dispatch** limit — the band SCED may dispatch within | always |
| `Base Point` | the instruction issued | always |
| `Output Schedule` | the unit's own self-schedule | always |
| `Telemetered Net Output` | metered actual | always |
| `Ramp Rate Up` / `Down` | MW/min the unit can move | always |
| `HASL` / `LASL` | high / low **ancillary service** limit — capability net of AS obligations | **pre-RTC only** |

Checked against the data rather than assumed: `LDL ≤ Base Point ≤ HDL` holds
on **100%** of ON rows — that is the hard dispatch band. `LSL ≤ LDL` holds 99%
of the time, and `HDL ≤ HSL` only **65%** — so HDL is *not* simply a tightened
HSL, and the six limits are not a clean nested hierarchy. Don't assume one.

> **⚠️ Schema change at RTC+B.** `HASL`, `LASL` and the whole
> `AS Responsibility for *` family are populated through **2025-12-04** and
> are **entirely NULL from 2025-12-10 onward**. The `AS Awards *` family is
> the reverse — empty before, populated after. This is real: before RTC,
> ancillary services were procured ahead and a unit carried a *responsibility*
> that shrank its dispatch range; after RTC they are co-optimised in real time
> and the unit receives an *award* each run. Any model touching these columns
> will silently get NULLs across the boundary.

**Ancillary services** — three families of column, same six products

*Products:* `RegUp` / `RegDown` (regulation), `RRS` (Responsive Reserve,
split into `RRSPFR` primary frequency response, `RRSFFR` fast frequency
response, `RRSUFR` under-frequency relay), `NonSpin` (non-spinning reserve),
`ECRS` (ERCOT Contingency Reserve Service).

| Family | Meaning |
|---|---|
| `AS Capability <product>` | how much the unit *could* provide |
| `AS Responsibility for <product>` | how much it is *obligated* to hold |
| `AS Awards <product>` | how much it was *awarded* |

**Offers and costs**
| Column | Meaning |
|---|---|
| `SCED1 Offer Curve`, `SCED2 Offer Curve`, `SCED TPO Offer Curve` | the unit's price/quantity bid curves, as nested `[[MW, $], …]` lists |
| `Start Up Cold/Hot/Inter Offer` | startup cost offers by thermal state |
| `Min Gen Cost` | minimum generation cost offer |

---

## 2. `sced_esr` — storage dispatch, 5-minute (40 cols)

*Batteries only. Starts 2025-12-05, the RTC+B go-live. 19.5M rows.*

Same shape as `sced_60day`, minus the `AS Responsibility` family, plus the
three columns that make it uniquely valuable:

| Column | Meaning |
|---|---|
| **`SOC`** | State of Charge — energy currently stored, MWh |
| **`Min SOC`** / **`Max SOC`** | the usable window the operator declares |
| `Bid Type` | e.g. `3PT` — offer curve structure ⚠️ |
| `Proxy Extension` | whether ERCOT extended the offer curve on the unit's behalf ⚠️ |

For storage, **`Base Point` sign is the direction**: negative = charging,
positive = discharging. That's how the charge/discharge profiles in
`FINDINGS.md` §6 are derived. `Max SOC − Min SOC` gives usable capacity;
the largest unit in the fleet is ~950–983 MWh.

---

## 3. `settlement_point_prices` — real-time prices, 15-minute (7 cols)

*Every pricing location. 97.5M rows, no gaps since 2023-12-11.*

| Column | Meaning |
|---|---|
| `deliveryDate`, `deliveryHour` (1–24), `deliveryInterval` (1–4) | the 15-minute interval |
| `settlementPoint` | location code |
| `settlementPointType` | `RN` resource node (816), `PCCRN`/`LCCRN` combined-cycle variants (228), `PUN` private use network (52), `LZ`/`LZEW`/`LZ_DC`/`LZ_DCEW` load zones, `HU` hub, `AH`/`SH` hub averages |
| `settlementPointPrice` | $/MWh |
| `DSTFlag` | daylight-saving repeated-hour marker |

`HB_`-prefixed points are hubs (trading benchmarks), `LZ_` are load zones
(where demand settles), everything else is a resource node (where a generator
settles). A generator's revenue is set at **its own node**, which is why the
crosswalk matters.

---

## 4. `lmp_resource_nodes` — nodal LMP, 5-minute (4 cols)

| Column | Meaning |
|---|---|
| `SCEDTimestamp`, `repeatHourFlag`, `settlementPoint`, `LMP` | locational marginal price, $/MWh |

Finer time resolution than settlement point prices, same locations. 170.6M
rows — the largest dataset by row count.

---

## 5. `dam_settlement_point_prices` — day-ahead prices, hourly (5 cols)

Same as real-time but cleared a day ahead, and `hourEnding` is a **string**
(`"01:00"`–`"24:00"`) rather than an integer — a join trap. The DA/RT spread
is what storage arbitrage and hedging trade on.

---

## 6. `shadow_prices` — real-time congestion, 5-minute (15 cols)

*Which transmission constraints were binding, and what they cost. 1.1M rows.*

| Column | Meaning |
|---|---|
| `constraintName`, `constraintID` | the binding element |
| `contingencyName` | the outage scenario it's evaluated against (N-1) |
| **`shadowPrice`** | $/MWh value of relieving it by 1 MW — the cost of the congestion |
| `maxShadowPrice` | cap applied (several constraints hit exactly $3,500) |
| `limit` / `value` / `violatedMW` | the constraint's MW limit, actual flow, and overage |
| `fromStation`, `toStation`, `fromStationkV`, `toStationkV` | the physical line and its voltage |
| `CCTStatus` | Competitive Constraint Test status — whether the constraint is deemed competitive, which affects mitigation ⚠️ |

`fromStation`/`toStation` are how you'd eventually place a constraint
geographically — the missing link between congestion and a map.

`dam_shadow_prices` is the same idea day-ahead, with `constraintLimit`,
`constraintValue`, `violationAmount` and a `deliveryTime` column instead.

---

## 7. `wind_production` / `solar_production` — hourly, by region

*Actual **and** forecast, which makes forecast error a free feature.*

Four measures, repeated for system-wide and each region:

| Prefix | Meaning |
|---|---|
| `gen…` | **actual** generation, MW |
| `COPHSL…` | Current Operating Plan HSL — capability the resources themselves declared ⚠️ |
| `STWPF…` / `STPPF…` | Short-Term **Wind** / **PhotoVoltaic** Power Forecast — ERCOT's point forecast ⚠️ |
| `WGRPP…` / `PVGRPP…` | Wind / PV Generation Resource Production **Potential** — a different confidence level, believed ~80th percentile ⚠️ |

**Regions** — wind: `SystemWide`, `Panhandle`, `Coastal`, `South`, `West`,
`North`. Solar: `SystemWide`, `CenterWest`, `NorthWest`, `FarWest`, `FarEast`,
`SouthEast`, `CenterEast`.

`gen − STWPF` is ERCOT's own forecast error; measured at 4–11% MAE system-wide
(`FINDINGS.md` §8). That's the benchmark any forecast product must beat.

⚠️ The exact percentile behind `WGRPP`/`PVGRPP` should be confirmed in the
protocols before being described publicly.

---

## 8. `resource_outages` — capacity offline, hourly (15 cols)

| Column | Meaning |
|---|---|
| `postedDatetime` | when the snapshot was published |
| `operatingDate`, `hourEnding` | the hour it describes |
| `totalResourceMWZone<Zone>` | total capacity on outage |
| `totalIRRMWZone<Zone>` | of which is **Intermittent Renewable Resources** |
| `totalNewEquipResourceMWZone<Zone>` | new equipment outages ⚠️ |

Zones: `South`, `North`, `West`, `Houston`. Note this is **zonal, not nodal** —
it won't tell you a specific plant is down.

---

## 9. `7d_load_forecast_by_forecast` / `_by_weather_zone` — demand, hourly

| Column | Meaning |
|---|---|
| `postedDatetime` | when the forecast was made — **use this for coverage**, since `deliveryDate` runs up to 7 days ahead |
| `deliveryDate`, `hourEnding` | the hour being forecast |
| zone columns | forecast MW per zone |
| `systemTotal` | ERCOT-wide forecast MW |

*Forecast zones:* `north`, `south`, `west`, `houston`.
*Weather zones:* `coast`, `east`, `farWest`, `north`, `northCentral`,
`southCentral`, `southern`, `west`.

Because `postedDatetime` and `deliveryDate` are both present, you can measure
**forecast error as a function of lead time** — a useful feature, and a
self-contained analysis in its own right. Only covers 2026-03-26 onward;
ERCOT retains ~6 months.

---

## Derived: `crosswalk/crosswalk.csv` (21 cols)

Not from ERCOT — built by `crosswalk/build.py`. Links a `Resource Name` to
its `settlement_point` and, where resolvable, to the physical plant:
`county`, `latitude`, `longitude`, `owner`, `utility`, `operating_year`,
`plant_nameplate_mw`. The `sp_method` and `eia_method` columns record how each
link was made so you can filter by confidence. See `crosswalk/README.md`.

---

## Joining these together — the traps

1. **Timezones.** `sced_60day` and `sced_esr` stamps are timezone-aware
   US/Central. Everything else is naive strings. Pin your session:
   `duckdb.sql("SET TimeZone = 'America/Chicago'")`. Getting this wrong
   shifted an entire analysis by an hour for two days.
2. **Two hour conventions.** Real-time prices use integer `deliveryHour`
   (1–24) plus `deliveryInterval` (1–4). Day-ahead uses a **string**
   `hourEnding` (`"01:00"`). SCED uses a raw timestamp.
3. **⚠️ SCED cadence changed at RTC+B.** 96 runs/day (**15-minute**) through
   2025-12-04; ~290 runs/day (**5-minute**) from 2025-12-10. **Never hardcode
   `MW / 12`** across a window spanning the boundary — it understates pre-RTC
   energy threefold. Derive hours per row from the data:
   `24.0 / COUNT(DISTINCT "SCED Timestamp")` per day. Helper:
   `analysis/interval_hours.py`. Percentages survive the error (the factor
   cancels); every MWh, GWh and TWh figure does not.
4. **Three time resolutions.** Nodal LMP is 5-minute; settlement point prices
   are 15-minute; everything else hourly. Aggregate fine to coarse, never
   interpolate coarse to fine.
5. **`postedDatetime` ≠ `deliveryDate`** in forecast and outage datasets. One
   is when it was said, the other what it was about.
6. **Resource names ≠ settlement point names.** `GALLOWAY_SOLAR1` settles at
   `GALO_RN1`. That is the entire reason the crosswalk exists.
7. **`Resource Type` moves.** Storage is `PWRSTR` inside `sced_60day` through
   Dec 2025, then relocates to `sced_esr` at RTC+B.
