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

| Strategy | $/kW-yr (median unit) | $/kW-yr (fleet) | Capture vs perfect |
|---|---|---|---|
| Fixed schedule | | | |
| Persistence | | | |
| Day-ahead informed | | | |
| Actual (energy only) | | | |
| Actual (with AS) | | | |
| Perfect foresight | | | 100% |

### Sensitivities

| Variant | Perfect-foresight $/kW-yr | Change |
|---|---|---|
| Base (MILP) | | — |
| LP relaxation | | the negative-price exploit, in dollars |
| $10/MWh degradation cost | | |
| 1.5 cycles/day cap | | |

### Reading the results

*(written once the numbers are in)*

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
