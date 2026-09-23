# Curtailment in ERCOT — what the data says

*Window: Aug 2025 – Jul 2026 · every number computed with DuckDB over
`data/raw/` · regenerate with the scripts listed at the bottom.*

The battery work lives in [`../optimization/WRITEUP.md`](../optimization/WRITEUP.md).
This file covers the other half of the project: how much renewable energy
ERCOT throws away, where, and what it was worth to the people who owned it.

Column definitions and the join traps are in
[`../DATA_DICTIONARY.md`](../DATA_DICTIONARY.md).

---

## How curtailment is measured

```
curtailment = HSL − Base Point          (when HSL > Base Point + 1 MW)
```

`HSL` = what the unit could produce; `Base Point` = what ERCOT instructed;
unit status `ON`; `HSL > 0`.

**Interval length is derived per day, never hardcoded.** ERCOT ran SCED every
15 minutes through 2025-12-04 and every 5 minutes from 2025-12-10, so
MW → MWh uses `24 / (SCED runs that day)`. See `interval_hours.py`.

**Only meaningful for intermittent resources.** For gas, coal or storage,
`HSL − Base Point` is just "not at maximum" — normal dispatch, not curtailment.

*Source: `sced_60day`. Row-level audit trail: `show_your_work.py`.*

---

## 1. How much

| Fuel | Units | Potential (TWh) | Curtailed (TWh) | % |
|---|---|---|---|---|
| WIND | 382 | 112.63 | 5.59 | **4.97%** |
| PVGR (solar) | 289 | 71.94 | 4.58 | **6.37%** |

**System-wide is 5–6%. The worst farms are 22–31%.** Both are true; quote the
right one.

Curtailment is **concentrated**: of 298 solar units, the top 10 carry 22.8% of
all solar curtailment and the top 50 carry **69.5%**. The five most-curtailed
solar units spilled 566,957 MWh over twelve months — a weighted 25.4% of their
potential.

Seasonality is strong: near zero in Aug–Sep, peaking Feb–Mar (44–56% at the
worst farms), falling back through summer. By hour (Central, daylight only for
solar), solar curtailment climbs from ~1% at 07:00 to a plateau of 7–8% from
11:00–16:00; wind peaks at 10.6% at 15:00.

---

## 2. What it was worth — at each unit's own node

Jan–Jun 2026, every wind/solar unit the crosswalk could place at a price node
(91% of them), each curtailed interval joined to the price **at that unit's own
settlement point**:

| | Curtailed MWh | at price < $0 | Avg $/MWh at node | Value at node | If negatives floored at $0 |
|---|---|---|---|---|---|
| **Solar** | 3,183,146 | **96.5%** | −$8.60 | −$27.4 M | $1.10 M |
| **Wind** | 3,488,654 | **95.7%** | −$11.50 | −$40.1 M | $0.84 M |

Three terawatt-hours of solar were spilled in six months. Valued at what the
market was paying at that place and moment, producing it would have *cost* the
owners $27 million. Even counting every negative-price interval as worth $0 —
the most generous framing for a PTC-less owner — the foregone revenue was
**$1.1 million, about $0.35 per MWh.**

This holds at the unit level, not just on average. Every one of the ten
most-curtailed solar units shows 94–100% of its curtailment at a negative
own-node price:

| Unit | Curtailed MWh | % at negative price | Avg $/MWh |
|---|---|---|---|
| GALLOWAY_SOLAR1 | 105,899 | 97% | −$7 |
| SPTX12B_UNIT1 | 87,664 | 96% | −$3 |
| REDBARN_UNIT_1 | 86,346 | 98% | −$4 |
| RIGGINS_UNIT1 | 79,712 | 95% | −$3 |
| WAYMARK_UNIT1 | 77,426 | 94% | −$3 |
| JADE_SLR_UNIT2 | 66,412 | 100% | −$11 |

**What it does not settle:** at a negative price you cannot tell from this data
whether ERCOT ordered the unit off or the unit chose to stop. For the economics
it barely matters — the energy is worthless either way.

*Source: `curtailment_vs_node_price.py`. Earlier versions of this table used a
hub proxy and read 78%; own-node and correctly time-aligned, it is 96%.*

---

## 3. Congestion or oversupply — exactly

ERCOT's nodal price is **LMP = System Lambda + congestion component** (there is
no marginal-loss term). Lambda is the energy price for the grid as a whole; the
congestion component is what a full line adds or subtracts at this node. Both
are public, so every curtailed interval classifies by one subtraction:

| Lambda | Own-node LMP | Reading |
|---|---|---|
| ≤ 0 | — | **oversupply** — Texas as a whole had more power than it wanted |
| > 0 | < 0 | **congestion** — the grid wanted power; this node was stuck behind a full line |
| > 0 | ≥ 0 | other — curtailed at a positive price (local limits, ramping, operator choice) |

Sep 2025 – Jul 2026, 1.47 M curtailed unit-intervals, 100% matched to both a
5-minute LMP and a lambda: **71% of solar and 84% of wind curtailment is
congestion** — the grid still wanted the power. Oversupply is concentrated in
Jan–Feb 2026, when the system price itself collapsed.

The distinction matters because congestion has a cure on a schedule
(transmission build-out) and oversupply does not.

Naming *which* line is harder. Shadow prices identify every binding constraint
per SCED run, and 99%+ of curtailment coincides with *some* constraint binding
— which is not discriminating, because with hundreds of constraints one nearly
always is. Ranking by lift (how much more often a constraint binds during a
given unit's curtailment than by chance) identifies corridors, not lines;
pinning a specific line needs shift factors ERCOT doesn't publish.

*Source: `curtailment_lambda_split.py`, `congestion_attribution.py`.*

---

## 4. Where, and whose

Via the crosswalk, for the 42% of wind/solar units it can place — which hold
**45% of all curtailed MWh** and 25 of the 50 most-curtailed units:

| County | Units | Curtailed GWh | % of potential |
|---|---|---|---|
| Borden | 11 | 473.0 | 13.5% |
| Nolan | 15 | 351.7 | 12.4% |
| Pecos | 8 | 339.1 | 17.7% |
| Roberts | 2 | 267.7 | **28.0%** |
| Scurry | 19 | 253.2 | 4.9% |
| Concho | 12 | 250.8 | 8.9% |
| Andrews | 5 | 234.2 | 14.6% |
| Childress | 4 | 210.5 | **19.2%** |
| Clay | 1 | 185.8 | **31.2%** |

Full county and owner tables: `curtailment_by_county_owner.py`. The unplaced
units, ranked by curtailment, are in `../crosswalk/aliases_todo.csv`.

---

## 5. Prices

35.9 million real-time intervals, all settlement points:

| Mean | Median | Min | Max | Negative | > $100 | > $1,000 |
|---|---|---|---|---|---|---|
| $32.00 | $24.84 | −$251 | $13,036 | **6.85%** | 3.02% | 0.031% |

Negative prices by month track curtailment exactly: 0.76% in Aug 2025,
**15.0% in Feb 2026**, back to 2% by July.

**Day-ahead vs real-time**, all seven hubs: DAM cleared **$2–3/MWh above RT**
consistently, with an average *absolute* gap of **$11–13**. Direction is small,
magnitude large — which is why day-ahead-informed dispatch underperforms in the
battery benchmark. HB_PAN (Panhandle) is the cheapest hub at $22.61 RT.

---

## 6. Batteries

Fleet of 313→335 units (Dec 2025 – Jul 2026), charging **720–860 GWh/month**,
implied round-trip efficiency **80–85%** — a sanity check that the data and the
arithmetic are sound, and the source of the 82% used in the optimiser.

Behaviour, March 2026 (Central):

| Hour | Charging MWh | Discharging MWh |
|---|---|---|
| 07 | 3,289 | **72,202** |
| 09 | **65,642** | 8,948 |
| 12–15 | ~53,000 | ~5,500 |
| **19** | 2,703 | **137,884** |
| 20 | 3,005 | 108,798 |

Charge through the solar glut, discharge into the 7–8 pm peak. The fleet is
already absorbing ~700 GWh/month of exactly the midday energy that would
otherwise be curtailed.

---

## 7. Congestion, system-wide

| Constraint | Intervals binding | Avg shadow price | Max |
|---|---|---|---|
| NELRIO | 32,590 | $11.60 | $978 |
| 6437__F | 21,503 | **$131.25** | $3,500 |
| HARGRO_TWINBU1_1 | 15,069 | **$292.08** | $3,500 |

Frequency and severity are different things; several constraints hit the
$3,500 cap.

---

## 8. RTC+B before and after — suggestive only

| | Before (Aug–Dec 25) | After (Dec 25–Jul 26) |
|---|---|---|
| Mean price | $33.52 | $28.93 |
| Volatility (σ) | 27.1 | **49.4** |
| % negative | 2.85% | **8.83%** |

Direction matches ERCOT's predictions for real-time co-optimisation, but the
two windows are different seasons and negative prices are strongly seasonal.
**Not causal.** A same-season test needs one more year of prices, which is
cheap to fetch.

Separately: ERCOT's own wind forecast misses by **4–11% MAE**, worst in March.
That is the benchmark any forecast product has to beat.

---

## Reproducing this

```bash
python analysis/explore_01_curtailment.py       # §1
python analysis/curtailment_vs_node_price.py    # §2
python analysis/curtailment_lambda_split.py     # §3
python analysis/congestion_attribution.py       # §3 (constraint lift)
python analysis/curtailment_by_county_owner.py  # §4
python analysis/explore_02_prices.py            # §5
python analysis/explore_03_batteries_congestion.py  # §6, §7
python analysis/explore_04_rtc_and_forecast.py  # §8
python analysis/show_your_work.py               # trace any number to raw rows
```

Every DuckDB session is pinned to Central time. The traps that produced wrong
answers along the way — and that are now regression-tested in
`tests/test_traps.py` — are documented in
[`../DATA_DICTIONARY.md`](../DATA_DICTIONARY.md).
