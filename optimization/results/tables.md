## Headline

| Strategy | $/kW-yr (median unit) | $/kW-yr (fleet) | Capture vs perfect (%) |
|---|---|---|---|
| Fixed schedule | 30.7 | 29.1 | 53.4 |
| Persistence | 11.5 | 11.7 | 21.4 |
| Day-ahead informed | 28.1 | 27.9 | 51.3 |
| Actual (energy only) | 18.6 | 19.0 | 34.9 |
| Actual (energy + AS) | 20.9 | 21.3 | 39.1 |
| Perfect foresight | 53.3 | 54.5 | 100.0 |

Units: 30   Days: 2025-12-05 → 2026-07-08   Unit-days: 5,970

**Value of perfect foresight over day-ahead:** $26.5/kW-yr (49% of the ceiling).
**AS revenue as share of actual total:** 11%.

## Sensitivities (perfect-foresight, fleet $/kW-yr)

| Variant | Perfect foresight $/kW-yr | vs base |
|---|---|---|
| Base (MILP) | 54.5 | +0.0% |
| LP relaxation | 54.6 | +0.2% |
| $10/MWh degradation | 51.3 | -5.9% |
| 1.5 cycles/day cap | 52.6 | -3.5% |

## Per-unit capture rate (actual incl. AS ÷ perfect foresight)

Top 5:

| Unit | MW | hours | days | Perfect $/kW-yr | Actual $/kW-yr | Capture % | DA-informed capture % |
|---|---|---|---|---|---|---|---|
| SHAMROCK_ESR1 | 99.8 | 3.3 | 199.0 | 75.8 | 53.3 | 70.3 | 57.2 |
| BOCO_ESS_ESR1 | 150.3 | 2.5 | 199.0 | 63.6 | 40.7 | 64.0 | 55.1 |
| ANOL_ESS_ESR1 | 240.0 | 2.3 | 199.0 | 53.0 | 28.3 | 53.4 | 52.9 |
| BLVN_SLR_ESR1 | 180.0 | 2.0 | 199.0 | 50.2 | 25.4 | 50.7 | 50.5 |
| PINEFRST_ESR1 | 200.1 | 2.1 | 199.0 | 49.6 | 24.1 | 48.6 | 47.1 |

Bottom 5:

| Unit | MW | hours | days | Perfect $/kW-yr | Actual $/kW-yr | Capture % | DA-informed capture % |
|---|---|---|---|---|---|---|---|
| EVLN_ESS_ESR1 | 203.7 | 2.1 | 199.0 | 48.1 | 9.5 | 19.8 | 39.6 |
| TANZ_ESS_ESR1 | 128.9 | 2.3 | 199.0 | 52.6 | 10.0 | 19.0 | 51.4 |
| HEADCAMP_ESR1 | 163.4 | 2.3 | 199.0 | 65.7 | 12.5 | 19.0 | 48.7 |
| TANZ_ESS_ESR2 | 128.9 | 2.4 | 199.0 | 53.6 | 8.8 | 16.4 | 52.1 |
| WZRD_ESS_ESR1 | 150.4 | 6.5 | 199.0 | 79.7 | 3.0 | 3.8 | 64.5 |

Capture rate across units — median 41%, IQR 33–46%, range 4–70%.

## By month (fleet $/kW-yr, annualised)

| Month | Day-ahead informed | Actual (energy + AS) | Perfect foresight | capture % |
|---|---|---|---|---|
| 2025-12 | 25.4 | 12.8 | 44.4 | 28.8 |
| 2026-01 | 36.0 | 25.7 | 84.7 | 30.4 |
| 2026-02 | 23.3 | 14.4 | 41.3 | 34.9 |
| 2026-03 | 32.5 | 28.1 | 61.3 | 45.8 |
| 2026-04 | 46.9 | 41.5 | 86.8 | 47.9 |
| 2026-05 | 19.6 | 15.7 | 35.9 | 43.9 |
| 2026-06 | 15.3 | 12.6 | 32.4 | 38.8 |
| 2026-07 | 14.1 | 12.8 | 24.8 | 51.7 |

## Worst single days for a real battery (energy revenue)

| Unit | Day | Actual $ | Perfect-foresight $ |
|---|---|---|---|
| WZRD_ESS_ESR1 | 2026-01-21 | -121,165 | 149,535 |
| EVLN_ESS_ESR1 | 2026-01-21 | -108,260 | 190,449 |
| TANZ_ESS_ESR1 | 2026-02-17 | -94,479 | 126,810 |
| TANZ_ESS_ESR2 | 2026-02-17 | -93,991 | 127,033 |
| JAG_SLR_ESR1 | 2026-01-25 | -60,417 | 98,990 |

A large negative day usually means the unit charged into a price spike — a commissioning unit on a fixed test schedule, or a forced state-of-charge target.
