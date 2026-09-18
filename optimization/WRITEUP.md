# How much money are Texas batteries leaving on the table?

*A battery arbitrage optimiser, benchmarked against what 30 real ERCOT
batteries actually did.*

---

## The question

Every battery-arbitrage tutorial does the same thing: take a price series,
write a linear programme, report the revenue. It is a fine exercise and it
tells you nothing, because there is no answer key.

ERCOT publishes one. Sixty days after the fact, its SCED disclosure reports
every storage unit's dispatch instruction and state of charge at five-minute
resolution. Join that to the price at the unit's own node and you can ask a
much better question than "what would an optimiser earn?" — namely:

> **What did real batteries earn, what could they have earned, and what
> explains the gap?**

This write-up builds the optimiser, runs it at each real unit's own price
node, and compares five dispatch strategies against the unit's actual
behaviour over seven months (Dec 2025 – Jul 2026), which is every day of
storage telemetry ERCOT has published since batteries got their own
disclosure at the RTC+B market redesign.

---

## The data

All from ERCOT's public API, via the pipeline in `scripts/`:

| Dataset | Used for |
|---|---|
| `sced_esr` | each unit's physical limits, opening SOC every day, and what it actually did |
| `settlement_point_prices` | the real-time price at the unit's own node, 15-min — what every strategy settles at |
| `dam_settlement_point_prices` | day-ahead prices — what a real operator knows the night before |
| `rt_as_prices` (np6-331-cd) | real-time ancillary-service clearing prices, so the real unit's reserve revenue can be counted |
| `crosswalk/` | unit → price node |

Physical parameters are read from telemetry rather than a registry: the
largest observed `HSL` is the discharge limit, the most negative `LSL` the
charge limit, `Max SOC` the usable energy. Round-trip efficiency is **82%**,
measured from the fleet's own charge and discharge totals — not assumed.

Units are included if they have a node link and were active (|Base Point|
> 1 MW) on at least 120 of the 207 days. That leaves 129; the benchmark uses
the 30 largest by energy capacity.

---

## The model

A battery over one day of `n` settlement intervals, each `Δt = 0.25` h.

**Decide**, for every interval `t`:
- `c_t ≥ 0` — charging power, MW
- `d_t ≥ 0` — discharging power, MW
- `s_t` — state of charge at the end of the interval, MWh
- `y_t ∈ {0, 1}` — mode: 1 if discharging is permitted, 0 if charging is

**Maximise** revenue net of any degradation charge:

```
    Σ_t  Δt · p_t · (d_t − c_t)   −   c_deg · Δt · (c_t + d_t) / 2
```

**Subject to**

| | Constraint | Meaning |
|---|---|---|
| SOC balance | `s_t = s_{t−1} + η_c·Δt·c_t − Δt·d_t / η_d` | energy in, less losses, less energy out |
| SOC window | `S_min ≤ s_t ≤ S_max` | stay inside the usable range the operator declares |
| Power limits | `c_t ≤ P_chg`, `d_t ≤ P_dis` | the inverter's rating |
| One mode at a time | `c_t ≤ P_chg·(1 − y_t)`, `d_t ≤ P_dis·y_t` | can't charge and discharge together |
| End where you began | `s_n ≥ s_0` | no "free" energy from draining the battery |
| Cycle cap (optional) | `Σ_t Δt·d_t ≤ N_cyc · (S_max − S_min)` | warranty-style throughput limit |

Efficiency is split symmetrically: `η_c = η_d = √0.82 ≈ 0.906`.

Implemented in Pyomo (`optimization/model.py`), solved with HiGHS. Prices and
the opening SOC are *mutable parameters*, so one model per unit is built
once and re-solved every day — about 60 MILP solves per second.

### Why the binaries matter here and not in the textbook

The usual shortcut is to drop `y_t`. The argument: with round-trip efficiency
below 100%, charging and discharging at the same moment only wastes energy,
so an LP optimum would never choose it.

**That argument is correct when prices are non-negative, and wrong in ERCOT.**
About 7% of ERCOT settlement intervals clear *below zero* — the grid pays you
to consume. When the battery is already full during such an interval, the
LP relaxation finds a trick: charge and discharge simultaneously, so the
round-trip loss "burns" stored energy and makes room to absorb more paid
charging. It is a genuine arbitrage on paper and physically impossible for an
inverter.

`tests/test_model.py` demonstrates both halves: the LP exploiting negative
prices (up to 14 MW of simultaneous charge and discharge on synthetic days),
the MILP refusing to, and the two agreeing to the cent whenever prices are
non-negative. The `--lp` flag on the benchmark sizes the effect on real
prices — see Results.

---

## The five strategies

Every strategy is settled at the unit's **own real-time node price**. They
differ only in what they knew when they decided.

| Strategy | Knows | Represents |
|---|---|---|
| **Fixed schedule** | nothing | charge 10:00–15:00, discharge 18:00–21:00, every day. What anyone could write. |
| **Persistence** | yesterday's real-time prices | optimise on them, run it today. The laziest forecast. |
| **Day-ahead informed** | today's day-ahead prices | optimise on them, settle real-time. **What a real operator can actually do.** |
| **Perfect foresight** | today's real-time prices | optimise on them. The upper bound — unattainable, but the yardstick. |
| **Actual** | — | what the unit did, from telemetry. Energy revenue, plus ancillary-service revenue (awards × clearing price). |

Three gaps carry the story:

- **Perfect foresight − Day-ahead informed** = the value of a perfect
  real-time forecast, in dollars.
- **Actual ÷ Perfect foresight** = the *capture rate*, the industry's
  standard measure of operator performance.
- **Actual with AS − Actual energy-only** = how much of the "gap" was never
  a gap: capacity held for reserves is capacity that is being paid.

### Fairness

Each day the optimiser starts from the SOC the real battery actually had at
midnight, not from empty. Days with missing intervals (DST changes, ERCOT
publication gaps) are dropped rather than patched. Persistence needs a prior
day, so it skips the first day of each run.

---

## Results

<!-- RESULTS: filled from optimization/results/summary_full.csv once the
     full run completes. Keep the table shape below. -->

### Headline — 30 units, Dec 2025 – Jul 2026

<p align="center"><img src="results/fig_strategies.png" width="680"></p>

| Strategy | $/kW-yr (median unit) | $/kW-yr (fleet) | Capture vs perfect |
|---|---|---|---|
| Fixed schedule | 30.7 | 29.1 | 53% |
| Persistence | 11.5 | 11.7 | 21% |
| Day-ahead informed | 28.1 | 27.9 | 51% |
| Actual (energy only) | 18.6 | 19.0 | 35% |
| **Actual (energy + AS)** | **20.9** | **21.3** | **39%** |
| Perfect foresight | 53.3 | 54.5 | 100% |

*30 units · 199 days · 5,970 unit-days · every strategy settled at the unit's
own real-time node · each day opens at the unit's real SOC.*

- **Value of perfect foresight over day-ahead dispatch: $26.5/kW-yr** — 49% of
  the ceiling.
- **Ancillary services were 11% of what real units earned.** Real-time AS
  clearing prices averaged well under $1/MW-h across the window.
- **Capture across units: median 41%, IQR 33–46%, range 4–70%.**

### Sensitivities

| Variant | Perfect-foresight $/kW-yr | Change |
|---|---|---|
| Base (MILP) | | — |
| LP relaxation | | the negative-price exploit, in dollars |
| $10/MWh degradation cost | | |
| 1.5 cycles/day cap | | |

### Reading the results

**1. Real batteries captured about two-fifths of what was available.**
$21/kW-yr against a $54 ceiling. The best unit (SHAMROCK, 100 MW / 3.3 h)
captured 70%; two others cleared 60%. So 60–70% is achievable — the fleet
median of 41% is an operating outcome, not a physical limit.

**2. The dumb strategy beat the smart one.** Charging at noon and discharging
at dinner, every day, with no price information at all, earned $29/kW-yr —
*more* than optimising against the day-ahead price ($28). This held across
the full seven months, not just one lucky one. ERCOT's evening peak is so
reliable that a schedule tuned to the market's shape catches it; optimising
against day-ahead prices commits to day-ahead peaks that real-time doesn't
always honour (the average |DA − RT| gap is $11–13/MWh). The lesson is not
that optimisation fails — perfect foresight nearly doubles both — but that
**an optimiser fed the wrong price series can lose to a heuristic that
encodes the right shape.**

**3. Yesterday is a bad forecast.** Persistence captured 21%. Real-time
spikes don't repeat on schedule.

**4. The money is in a handful of days.** January and April each delivered
$85–87/kW-yr annualised under perfect foresight; June and July under $35.
Monthly capture rose from 29–30% in Dec–Jan to 44–52% by May–Jul — partly
operators settling in after the RTC+B redesign, partly fewer spikes to miss.

<p align="center"><img src="results/fig_monthly.png" width="680"></p>

**5. The worst days explain the capture gap.** On 21 January and 17 February
— the two biggest scarcity events of the winter — at least four of the thirty
units were *charging* when prices passed $3,000/MWh:

| Unit | Day | Actual | Perfect foresight |
|---|---|---|---|
| WZRD_ESS_ESR1 | 2026-01-21 | **−$121,165** | +$149,535 |
| EVLN_ESS_ESR1 | 2026-01-21 | −$108,260 | +$190,449 |
| TANZ_ESS_ESR1 | 2026-02-17 | −$94,479 | +$126,810 |
| TANZ_ESS_ESR2 | 2026-02-17 | −$93,991 | +$127,033 |

A $270,000 swing on one unit in one day. The two TANZ units share a site and
did it on the same day, which points at a site-level schedule or SOC target
rather than chance. WZRD is a 6.5-hour unit that used only 38% of its
capacity across the window and sold no reserves — almost certainly still
commissioning. **Unit-level capture rates are dominated by a few days**, and a
strategy's real test is what it does during a spike, not on an average day.

<p align="center"><img src="results/fig_example_day.png" width="720"></p>

**6. Ancillary services are no longer the story.** They added 11% to real
units' revenue. Real-time reserve prices averaged under $1/MW-h in this
window — consistent with the widely reported saturation of ERCOT's AS market
by storage. The "batteries live on reserves" era is not visible in this data.
Which makes the energy-arbitrage question — and the forecast quality it
depends on — the whole game.

---

## What this does not capture

Being explicit, because the gaps are where the next version lives:

1. **AS revenue is counted for the real unit but not optimised for.** The
   optimiser only trades energy. A co-optimising model that chooses between
   energy and reserves each interval is the obvious next step, and post-RTC
   it is the model ERCOT itself runs.
2. **Perfect foresight is a yardstick, not a strategy.** Nobody has it. The
   realistic ceiling is somewhere between day-ahead-informed and perfect, and
   the distance between them is exactly what a forecasting product is worth.
3. **Efficiency is a fleet average.** Individual units differ; a unit with
   88% round trip looks worse than it is against an 82% optimiser.
4. **Degradation is a flat throughput charge**, not a depth-of-discharge or
   temperature model.
5. **Unit limits are observed maxima.** A unit that never ran flat out
   appears smaller than its nameplate.
6. **Seven months, one market regime.** Every day here is post-RTC+B; there
   is no pre-RTC storage disclosure to compare against.

---

## Reproduce it

```bash
pip install -r requirements.txt
python optimization/fetch_as_prices.py          # ancillary-service prices (~2 min)
python -m optimization.benchmark --units 30     # ~10 min
python -m optimization.benchmark --units 30 --lp --tag lp
pytest                                          # 18 tests, no data needed
```

Results land in `optimization/results/`. Every number in this write-up comes
from `summary_*.csv`; per-unit-per-day detail is in `unit_day_*.parquet`.
