# Capture-gap anatomy: why 129 ERCOT batteries fell short of the ceiling

*Dec 2025 – Jul 2026 · every active, node-linked storage unit in the ESR
disclosure · 25,671 unit-days, 22,193 of them fully ON · each strategy settled
at the unit's own real-time node · each day opens at the unit's real SOC.*

<p align="center"><img src="fig_waterfall.png" width="720"></p>

## What the waterfall says

The perfect-foresight ceiling for the fleet is **$48.7/kW-yr**. Real units
earned **$18.9** — a capture rate of **38.9%**. The gap of $29.8 decomposes,
additively and on one common denominator, into:

| Piece | $/kW-yr | % of ceiling | What it is |
|---|---|---|---|
| Commissioning / not-ON | −5.7 | 11.7 | the whole gap on unit-days the unit was not fully ON (ONTEST, OUT, no telemetry) |
| Declared SOC window | −2.3 | 4.7 | the ceiling re-solved inside the Min/Max SOC the operator declared that day |
| Reserves, net of AS | −8.6 | 17.6 | energy revenue foregone by holding the unit's actual reserve awards, minus the AS revenue those awards earned |
| Dispatch residual | −13.2 | 27.1 | what is left: decision quality |

**1. Twelve percent of the ceiling sat on days the unit wasn't trading.**
Filter to fully-ON unit-days (≥ 95% of 5-minute rows with status ON) and
fleet capture moves from 38.9% to **42.5%**; on the 30 largest units, which
the earlier write-up reported at 39%, it moves to **44.9%**. This is the
hygiene step any published benchmark applies, and this repo's headline did not
until now. Five units were fully ON on fewer than half their days (TORT 2%,
WZRD 24%, the TANZ pair 46–47%, QUEEN_BA 47%).

**2. The declared window is small for the fleet and the whole story for a
few.** Fleet-wide it costs 5.5 points of the ON-day ceiling. But NWF declares
a window worth 63% of its ceiling, WZRD 49%, EUNICE 40%, HEADCAMP and GKS
22% — units telling ERCOT they will use a fraction of the capacity the
telemetry says they have. That is the operator's own conservatism, priced.

**3. Reserves cost more energy than they earned — at real-time prices.**
Holding the unit's actual awards (Reg/RRS backed by 0.5 h of stored energy,
ECRS 1 h, NonSpin 4 h, plus headroom from net output) cost **25.8 points** of
ON-day energy revenue and earned back **5.3 points** at real-time MCPC — net
**20.5**. Not one of the 129 units had reserves pay for themselves at
real-time prices. Two caveats bound this number rather than dissolve it:

- AS revenue is priced at real-time MCPC only. Day-ahead awards are paid at
  DAM MCPC, which runs 2–4× higher, so the AS side is a lower bound. The DAM
  ESR disclosure (not yet downloaded) would fix it.
- Imposing real-time awards as hard prior obligations on a perfect-foresight
  re-solve is the strictest reading: real-time awards are outputs of the
  same SCED solve as the dispatch, not commitments made in advance. So 20.5
  is an upper bound on the energy cost of the reserve position. The
  constrained re-solve needed 44,650 MWh of slack across 6.6% of unit-days;
  excluding every unit-day with any slack, the figure is 19.1 points, so the
  result is not a slack artifact.

**4. The dispatch residual is the largest piece — and it is spread thin.**
31.5 points of the ON-day ceiling. It is *not* concentrated on the big days:
the fleet's 20 biggest perfect-foresight days carry 39.7% of the ceiling and
39.9% of the residual, and capture on those days (44.1%) was *higher* than on
the other 179 (41.5%). "The money is made on a dozen days" is true of the
ceiling; it is not where the operators fell short.

**5. On a quarter of the ceiling, the ceiling is fiction.** 24.5% of
|perfect-foresight revenue| falls on intervals where the unit's own offer
curve was within $1 of the 5-minute LMP — the unit was the marginal resource,
and a different dispatch would have moved the price. Three units (RRANCHES ×2,
CARN) are above 50%. This is flagged, not subtracted, because the correct
correction needs a supply-stack re-clearing this data cannot support.

**6. The earlier "worst days" story was wrong.** The 09-17 write-up led with
Jan 21 and Feb 17 as "the winter's two biggest scarcity events" during which
four units charged into $3,000 prices. The hub averaged $23–60 those days.
They were nodal spikes on violated 138 kV constraints (`138_NAL_HAS_1`,
`BLASCOFE_RC_1`, both at the $3,500 cap), and the two Jan 21 units were
commissioning (EVLN 100% ONTEST, WZRD 86%). The TANZ pair on Feb 17 was
mostly ON and did charge ~400 MWh each into the spike — a real event, but a
local-constraint one. The true worst fully-ON days are different and more
interesting: **JAG_SLR on Jan 25 (−$60k against +$99k possible), ANOL on
Feb 1 (−$59k), BLACKSPR on May 18 (−$56k against +$151k), EBNY on Jan 26
(−$56k against +$161k)**. Jan 24–27 is Winter Storm Fern.

## What is new here, and what is not

Capture rates in the 40–60% range, AS saturation, revenue concentrated in a
few days: all reported by Modo, the IMM and the literature. What this adds
is the decomposition — a named, additive account of *why* each specific unit
fell short, built from columns the public disclosure carries (status,
declared SOC window, awards, offer curves) that published benchmarks do not
use. The honest one-line summary: **after hygiene, roughly half the remaining
gap is the reserve position and half is dispatch, with declared limits a
small third piece and a quarter of the ceiling not credible at all.**

## Reproduce

```bash
python -m optimization.benchmark --all --tag fleet     # ~4.5 h, 129 units
python -m optimization.price_setting --tag fleet       # ~4 min
python -m optimization.anatomy --tag fleet             # seconds
```

---

# Tables (generated by `anatomy.py`)

*129 units · 2025-12-05 → 2026-07-08 · 25,671 unit-days, 22,193 fully ON (on_share ≥ 0.95)*

## 1. Fleet waterfall

| Step | $M | $/kW-yr | % of ceiling |
|---|---|---|---|
| Perfect-foresight ceiling | 358.9 | 48.7 | 100.0 |
| − commissioning / not-ON unit-days | 42.1 | 5.7 | 11.7 |
| − declared SOC window | 16.9 | 2.3 | 4.7 |
| − reserves held, net of AS revenue | 63.1 | 8.6 | 17.6 |
| − dispatch residual | 97.3 | 13.2 | 27.1 |
| = Actual (energy + AS) | 139.5 | 18.9 | 38.9 |

Capture, all unit-days: **38.9%**. Capture, fully-ON unit-days only: **42.5%**. The first bar of the waterfall is the difference.

On fully-ON unit-days the remaining gap of 57.5 points splits into: declared window **5.5**, reserves net **20.5** (energy foregone 25.8 minus AS earned 5.3), dispatch residual **31.5** points of the ON-day ceiling.

Reserve-energy slack used by the constrained re-solve: 44,650 MWh total (6.6% of unit-days non-zero); AS revenue is priced at real-time MCPC only.

## 2. Hygiene: what the status filter does

| Set | unit-days | units | capture (fleet) | ceiling $/kW-yr |
|---|---|---|---|---|
| all unit-days | 25,671.0 | 129.0 | 38.9 | 48.7 |
| on_share ≥ 0.95 | 22,193.0 | 129.0 | 42.5 | 48.5 |

Units fully ON on fewer than half their days (5): TORT_ESS_ESR1 (2%), WZRD_ESS_ESR1 (24%), TANZ_ESS_ESR2 (46%), QUEEN_BA_ESR1 (47%), TANZ_ESS_ESR1 (47%)

## 3. Per unit (fully-ON days; components as % of that unit's ON-day ceiling)

| Unit | MW | h | ON days | all days | capture all % | capture ON % | window % | reserves net % | residual % | slack MWh | price-setting % of |PF$| | price-setting % intervals |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| RRC_WIND_ESR2 | 75.2 | 3.0 | 167.0 | 199.0 | 67.8 | 73.0 | 0.0 | 0.0 | 27.0 | 0.0 | 10.0 | 9.4 |
| SHAMROCK_ESR1 | 99.8 | 3.3 | 191.0 | 199.0 | 70.3 | 70.4 | 5.5 | 0.1 | 23.9 | 0.0 | 19.4 | 24.5 |
| RRC_WIND_ESR1 | 75.3 | 3.0 | 170.0 | 199.0 | 64.0 | 68.2 | 2.2 | 0.0 | 29.5 | 0.0 | 10.0 | 9.6 |
| BOCO_ESS_ESR1 | 150.3 | 2.5 | 184.0 | 199.0 | 64.0 | 66.2 | 3.4 | 32.1 | -1.7 | 290.5 | 23.9 | 18.3 |
| LMO_ESR1 | 100.7 | 2.4 | 193.0 | 199.0 | 64.1 | 63.7 | 1.0 | 23.8 | 11.5 | 1,035.5 | 22.1 | 28.1 |
| TDWLPR_1_ESR2 | 102.0 | 2.3 | 162.0 | 199.0 | 45.0 | 58.4 | 1.6 | 38.3 | 1.7 | 2.8 | 26.6 | 22.2 |
| RVRVLYS_ESR1 | 52.0 | 2.2 | 190.0 | 199.0 | 58.5 | 58.3 | 0.7 | 25.0 | 16.0 | 605.6 | 25.1 | 34.7 |
| TDWLPR_1_ESR1 | 101.9 | 2.3 | 160.0 | 199.0 | 43.9 | 57.7 | 3.1 | 38.1 | 1.1 | 1.8 | 26.4 | 21.9 |
| BKSL_ESS_ESR1 | 100.0 | 2.3 | 181.0 | 199.0 | 54.9 | 56.3 | 9.4 | 24.7 | 9.5 | 163.6 | 8.2 | 9.2 |
| ANOL_ESS_ESR1 | 240.0 | 2.3 | 188.0 | 199.0 | 53.4 | 54.8 | 5.7 | 26.2 | 13.3 | 202.8 | 12.3 | 11.7 |
| HMNG_ESS_ESR1 | 100.1 | 2.5 | 197.0 | 199.0 | 54.3 | 54.5 | 1.6 | 35.7 | 8.3 | 4.2 | 29.5 | 25.0 |
| RADN_SLR_ESR2 | 81.9 | 2.1 | 157.0 | 199.0 | 48.6 | 54.1 | 4.9 | 2.3 | 38.7 | 890.8 | 9.2 | 12.2 |
| JADE_SLR_ESR1 | 79.4 | 2.0 | 183.0 | 199.0 | 52.6 | 53.4 | 2.6 | 22.3 | 21.7 | 778.0 | 10.2 | 13.5 |
| HOUSEMTN_ESR1 | 60.0 | 2.2 | 185.0 | 199.0 | 49.5 | 53.2 | 3.2 | 25.0 | 18.6 | 17.3 | 45.3 | 49.6 |
| ANDMDSLR_ESR2 | 79.4 | 2.0 | 184.0 | 199.0 | 48.6 | 52.8 | 4.5 | 31.1 | 11.6 | 1,528.9 | 10.7 | 15.2 |
| JADE_SLR_ESR2 | 81.9 | 2.1 | 181.0 | 199.0 | 51.5 | 52.6 | 3.9 | 22.0 | 21.5 | 802.3 | 8.7 | 11.4 |
| RVRVLYS_ESR2 | 52.0 | 2.2 | 192.0 | 199.0 | 52.6 | 52.1 | 1.7 | 25.4 | 20.8 | 567.6 | 23.9 | 31.9 |
| BCNV_ESS_ESR1 | 150.0 | 2.1 | 130.0 | 199.0 | 33.4 | 52.1 | 4.8 | 30.9 | 12.2 | 0.0 | 18.8 | 15.0 |
| ZIER_SLR_ESR1 | 40.4 | 2.0 | 190.0 | 199.0 | 51.2 | 51.7 | 1.5 | 30.3 | 16.5 | 7.8 | 14.4 | 17.3 |
| PAD1_ESS_ESR1 | 50.0 | 2.4 | 183.0 | 199.0 | 48.3 | 51.5 | 0.2 | 14.8 | 33.5 | 0.0 | 36.3 | 26.2 |
| ANDMDSLR_ESR1 | 81.9 | 2.0 | 185.0 | 199.0 | 49.3 | 51.0 | 4.3 | 30.2 | 14.5 | 804.4 | 12.6 | 14.5 |
| MADERO_ESR2 | 100.6 | 2.7 | 195.0 | 199.0 | 50.3 | 50.5 | 1.7 | 22.7 | 25.1 | 1,005.9 | 45.4 | 50.6 |
| BLVN_SLR_ESR1 | 180.0 | 2.0 | 182.0 | 199.0 | 50.7 | 50.5 | 0.1 | 30.9 | 18.5 | 213.7 | 12.3 | 10.5 |
| CLO_ESR2 | 100.2 | 2.0 | 190.0 | 199.0 | 49.0 | 50.3 | 0.5 | 36.5 | 12.7 | 23.7 | 33.1 | 27.7 |
| RADN_SLR_ESR1 | 79.0 | 2.0 | 162.0 | 199.0 | 48.0 | 50.2 | 5.4 | 2.5 | 41.9 | 229.8 | 10.4 | 12.3 |
| CLO_ESR1 | 100.2 | 2.1 | 189.0 | 199.0 | 48.5 | 49.7 | 0.8 | 36.8 | 12.7 | 18.2 | 33.0 | 27.8 |
| PINEFRST_ESR1 | 200.1 | 2.1 | 181.0 | 199.0 | 48.6 | 49.1 | 2.8 | 0.5 | 47.5 | 0.0 | 39.8 | 29.9 |
| JAG_SLR_ESR1 | 150.0 | 2.0 | 152.0 | 199.0 | 40.8 | 48.8 | 0.4 | 15.4 | 35.4 | 117.2 | 25.4 | 23.1 |
| CACH_ESS_ESR1 | 200.0 | 2.4 | 190.0 | 199.0 | 47.7 | 48.6 | 0.7 | 21.8 | 28.9 | 98.5 | 48.0 | 47.6 |
| DSWL_ESS_ESR1 | 150.0 | 2.3 | 193.0 | 199.0 | 48.6 | 48.2 | 5.2 | 8.2 | 38.4 | 560.4 | 12.8 | 13.6 |
| CORALSLR_ESR2 | 53.3 | 1.2 | 193.0 | 199.0 | 48.2 | 48.2 | 1.1 | 25.7 | 25.0 | 52.8 | 16.1 | 10.8 |
| CORALSLR_ESR1 | 49.5 | 1.2 | 192.0 | 199.0 | 47.5 | 47.9 | 2.7 | 22.7 | 26.7 | 48.5 | 18.1 | 14.3 |
| MADERO_ESR1 | 100.7 | 2.6 | 196.0 | 199.0 | 46.9 | 47.6 | 3.2 | 23.4 | 25.8 | 15.3 | 45.7 | 51.6 |
| CNLY_ESS_ESR1 | 125.1 | 2.0 | 186.0 | 199.0 | 47.4 | 47.6 | 1.6 | 35.1 | 15.8 | 10,738.2 | 22.2 | 20.1 |
| DAN_ESR1 | 75.6 | 1.6 | 170.0 | 199.0 | 44.9 | 47.6 | 6.4 | 8.0 | 38.0 | 536.0 | 18.5 | 9.2 |
| GIGA_ESS_ESR1 | 125.2 | 2.0 | 191.0 | 199.0 | 45.0 | 47.2 | 4.7 | 37.3 | 10.7 | 5,494.4 | 14.2 | 13.5 |
| DGFS_ESR_ESR1 | 75.4 | 1.2 | 188.0 | 199.0 | 45.8 | 47.0 | 6.3 | 27.3 | 19.4 | 331.1 | 4.4 | 6.5 |
| ANEM_ESS_ESR1 | 201.8 | 2.4 | 181.0 | 199.0 | 43.6 | 46.7 | 3.0 | 15.9 | 34.4 | 1,071.4 | 40.2 | 35.9 |
| JAG_SLR_ESR2 | 150.7 | 2.3 | 175.0 | 199.0 | 39.0 | 46.6 | 3.3 | 1.4 | 48.7 | 0.0 | 1.6 | 2.5 |
| EBNY_ESS_ESR1 | 202.0 | 2.4 | 178.0 | 199.0 | 43.9 | 46.4 | 2.8 | 13.2 | 37.6 | 470.9 | 49.9 | 43.4 |
| FLOWERII_ESR1 | 100.3 | 2.0 | 192.0 | 199.0 | 46.4 | 46.4 | 1.9 | 21.0 | 30.7 | 8.5 | 7.1 | 9.6 |
| ESTONIAN_ESR1 | 101.6 | 1.8 | 177.0 | 199.0 | 44.7 | 46.3 | 4.5 | 32.2 | 17.0 | 24.9 | 36.3 | 26.4 |
| SWOOSEII_ESR1 | 101.1 | 2.0 | 187.0 | 199.0 | 44.6 | 46.0 | 3.1 | 32.3 | 18.5 | 1.9 | 26.0 | 23.7 |
| AVIL_ESS_ESR1 | 160.0 | 2.4 | 192.0 | 199.0 | 46.4 | 46.0 | 0.8 | 19.4 | 33.8 | 23.9 | 14.4 | 10.6 |
| DAN_ESR2 | 72.8 | 1.5 | 172.0 | 199.0 | 43.7 | 45.8 | 7.0 | 7.6 | 39.6 | 331.2 | 19.3 | 9.8 |
| JAR_ESR2 | 157.8 | 1.8 | 191.0 | 199.0 | 44.7 | 45.5 | 0.1 | 35.8 | 18.6 | 511.8 | 10.5 | 10.3 |
| RRANCHES_ESR1 | 151.9 | 2.4 | 178.0 | 199.0 | 43.3 | 45.3 | 2.7 | 15.4 | 36.6 | 43.9 | 52.3 | 44.6 |
| MYR_ESR2 | 73.8 | 1.6 | 182.0 | 199.0 | 44.2 | 45.1 | 8.1 | 6.4 | 40.4 | 238.3 | 19.9 | 10.0 |
| MYR_ESR1 | 76.2 | 1.6 | 183.0 | 199.0 | 43.8 | 45.0 | 7.4 | 6.9 | 40.7 | 191.9 | 17.1 | 10.4 |
| JAR_ESR1 | 147.8 | 1.8 | 189.0 | 199.0 | 43.9 | 44.9 | 0.3 | 35.3 | 19.5 | 435.0 | 12.6 | 11.9 |
| CROSSETT_ESR1 | 100.9 | 1.0 | 194.0 | 199.0 | 44.5 | 44.9 | 2.5 | 24.4 | 28.3 | 118.3 | 6.7 | 7.5 |
| SMTH_ESS_ESR1 | 125.2 | 2.0 | 171.0 | 199.0 | 41.5 | 44.5 | 2.0 | 15.3 | 38.2 | 218.2 | 13.0 | 13.1 |
| BYRDR_ES_ESR1 | 50.0 | 1.2 | 187.0 | 199.0 | 40.4 | 44.3 | 5.3 | 30.9 | 19.5 | 40.1 | 7.4 | 7.8 |
| BR_ARROW_ESR1 | 48.3 | 2.1 | 196.0 | 199.0 | 43.8 | 43.9 | 6.1 | 10.9 | 39.1 | 0.0 | 13.0 | 9.8 |
| CROSSETT_ESR2 | 100.0 | 1.0 | 196.0 | 199.0 | 44.1 | 43.8 | 2.2 | 24.1 | 29.9 | 114.6 | 11.7 | 11.8 |
| CTW_ESR1 | 150.1 | 1.5 | 141.0 | 199.0 | 36.1 | 43.6 | 9.2 | 8.0 | 39.2 | 239.3 | 18.5 | 9.2 |
| PHO_ESR2 | 151.3 | 1.7 | 178.0 | 199.0 | 42.6 | 43.1 | 3.8 | 32.5 | 20.6 | 12.2 | 33.4 | 30.4 |
| BR_ARROW_ESR2 | 51.7 | 2.1 | 196.0 | 199.0 | 43.1 | 42.9 | 4.4 | 0.1 | 52.6 | 0.0 | 19.4 | 19.7 |
| RPUBRDS_ESR1 | 50.0 | 1.2 | 190.0 | 199.0 | 42.5 | 42.8 | 7.6 | 26.2 | 23.5 | 51.5 | 13.6 | 15.1 |
| CARN_ESS_ESR1 | 150.0 | 2.4 | 193.0 | 199.0 | 40.7 | 42.6 | 1.3 | 15.5 | 40.5 | 81.2 | 50.4 | 47.5 |
| WAL_ESR1 | 200.3 | 2.0 | 191.0 | 199.0 | 42.8 | 42.6 | 7.2 | 28.9 | 21.3 | 2,697.5 | 15.2 | 15.0 |
| TBWF_ESS_ESR1 | 152.0 | 2.4 | 189.0 | 199.0 | 41.3 | 42.1 | 2.4 | 19.3 | 36.3 | 945.5 | 38.7 | 35.9 |
| PHO_ESR1 | 152.0 | 1.7 | 179.0 | 199.0 | 40.1 | 41.8 | 2.3 | 33.0 | 22.9 | 34.9 | 33.7 | 28.7 |
| RRANCHES_ESR2 | 151.4 | 2.4 | 175.0 | 199.0 | 40.5 | 41.7 | 2.8 | 14.3 | 41.2 | 17.9 | 51.2 | 43.4 |
| TSECA_ES_ESR1 | 100.3 | 2.5 | 162.0 | 199.0 | 32.2 | 41.1 | 6.6 | 13.4 | 38.9 | 364.3 | 33.9 | 32.8 |
| LUCKYBLU_ESR1 | 102.0 | 2.2 | 175.0 | 199.0 | 38.6 | 40.9 | 10.0 | 7.4 | 41.7 | 2.7 | 11.3 | 4.7 |
| MUSTNGCK_ESR1 | 71.0 | 1.7 | 181.0 | 199.0 | 36.6 | 40.8 | 4.4 | 30.6 | 24.1 | 13.9 | 29.7 | 24.0 |
| BLACKSPR_ESR1 | 120.0 | 2.4 | 181.0 | 199.0 | 39.1 | 40.8 | 3.6 | 5.9 | 49.8 | 0.0 | 34.8 | 27.5 |
| LON_ESR1 | 176.0 | 2.3 | 190.0 | 199.0 | 40.3 | 40.6 | 8.8 | 25.7 | 25.0 | 87.3 | 32.8 | 33.0 |
| WIG_ESS_ESR1 | 120.1 | 1.6 | 193.0 | 199.0 | 40.2 | 40.4 | 0.1 | 36.8 | 22.6 | 293.0 | 18.0 | 13.9 |
| BLUEJAY_ESR1 | 51.9 | 1.7 | 183.0 | 199.0 | 39.1 | 40.3 | 0.6 | 34.4 | 24.7 | 0.0 | 21.7 | 19.7 |
| CORAZON_ESR1 | 200.4 | 1.3 | 163.0 | 199.0 | 39.4 | 40.2 | 8.0 | 30.7 | 21.1 | 253.7 | 15.1 | 13.6 |
| MIDP_SLR_ESR1 | 52.9 | 2.6 | 101.0 | 199.0 | 24.7 | 40.2 | 21.1 | 0.0 | 38.7 | 0.0 | 0.4 | 0.7 |
| ALP_BESS_ESR1 | 100.8 | 1.7 | 193.0 | 199.0 | 38.7 | 39.8 | 3.5 | 32.4 | 24.4 | 35.3 | 14.4 | 11.8 |
| ADL_ESR1 | 60.0 | 1.1 | 104.0 | 199.0 | 29.1 | 39.7 | 13.6 | 27.7 | 19.1 | 4.5 | 4.5 | 4.6 |
| WFTANK_ESR1 | 152.0 | 1.3 | 184.0 | 199.0 | 38.5 | 39.3 | 10.3 | 35.3 | 15.1 | 310.0 | 19.8 | 18.6 |
| SPTX12B_ESR1 | 25.0 | 0.9 | 178.0 | 199.0 | 36.4 | 39.1 | 6.0 | 14.5 | 40.4 | 0.2 | 27.3 | 21.9 |
| CHIL_SLR_ESR1 | 151.6 | 2.2 | 157.0 | 199.0 | 36.1 | 38.9 | 3.1 | 17.9 | 40.0 | 114.2 | 40.0 | 38.6 |
| AZURE_ESR1 | 78.0 | 1.6 | 162.0 | 199.0 | 32.1 | 38.4 | 5.6 | 32.0 | 24.0 | 13.7 | 15.1 | 13.5 |
| ANG_SLR_ESR1 | 100.0 | 2.4 | 167.0 | 199.0 | 32.3 | 38.2 | 17.1 | 17.3 | 27.4 | 0.0 | 29.8 | 23.2 |
| HLY_ESR2 | 102.2 | 1.6 | 191.0 | 199.0 | 37.7 | 38.2 | 0.0 | 38.0 | 23.8 | 110.6 | 15.2 | 12.8 |
| ANTL_ESS_ESR1 | 70.0 | 2.4 | 189.0 | 199.0 | 37.8 | 38.0 | 1.3 | 21.0 | 39.7 | 62.3 | 48.1 | 46.8 |
| NCO_ESR1 | 51.0 | 1.2 | 192.0 | 199.0 | 37.4 | 37.8 | 6.2 | 27.7 | 28.3 | 83.5 | 16.5 | 17.6 |
| SEVNF_ES_ESR1 | 100.3 | 2.5 | 163.0 | 199.0 | 29.5 | 36.7 | 7.2 | 15.6 | 40.4 | 194.6 | 34.9 | 35.2 |
| HLY_ESR1 | 104.2 | 1.7 | 191.0 | 199.0 | 36.1 | 36.5 | 0.0 | 36.4 | 27.0 | 126.2 | 15.8 | 13.8 |
| FTDUNCAN_ESR1 | 100.1 | 2.3 | 196.0 | 199.0 | 36.5 | 36.4 | 6.3 | 37.6 | 19.6 | 23.1 | 31.8 | 32.3 |
| CARTWHL_ESR1 | 150.3 | 2.3 | 166.0 | 199.0 | 33.8 | 36.4 | 12.0 | 0.0 | 51.6 | 0.0 | 16.6 | 12.4 |
| LILY_ESR1 | 50.7 | 1.4 | 178.0 | 199.0 | 34.4 | 35.5 | 1.6 | 34.4 | 28.5 | 17.3 | 17.5 | 12.3 |
| PLATINUM_ESR2 | 153.0 | 2.4 | 131.0 | 199.0 | 30.8 | 35.4 | 10.3 | 10.0 | 44.3 | 89.8 | 21.0 | 22.7 |
| PLATINUM_ESR1 | 148.5 | 2.4 | 130.0 | 199.0 | 31.9 | 35.2 | 10.3 | 9.9 | 44.7 | 78.4 | 24.0 | 22.6 |
| LOWR_ESS_ESR1 | 61.0 | 2.1 | 179.0 | 199.0 | 31.9 | 34.6 | 7.3 | 4.8 | 53.3 | 0.0 | 34.4 | 28.7 |
| ELZA_SLR_ESR1 | 100.0 | 1.7 | 164.0 | 199.0 | 32.9 | 34.4 | 5.3 | 33.5 | 26.8 | 0.0 | 28.2 | 23.5 |
| ROSELAND_ESR1 | 50.5 | 1.7 | 183.0 | 199.0 | 35.9 | 34.3 | 3.8 | 35.4 | 26.5 | 0.2 | 22.8 | 18.8 |
| HEADCAMP_ESR1 | 163.4 | 2.3 | 116.0 | 199.0 | 19.0 | 33.6 | 21.9 | 0.0 | 44.5 | 0.0 | 18.3 | 17.0 |
| QUEEN_BA_ESR1 | 50.0 | 1.7 | 94.0 | 199.0 | 15.3 | 32.4 | 20.1 | 17.4 | 30.1 | 0.0 | 9.8 | 9.1 |
| SHEEPCRK_ESR1 | 136.9 | 1.3 | 178.0 | 199.0 | 31.6 | 31.4 | 2.3 | 21.1 | 45.3 | 65.8 | 37.3 | 35.0 |
| DKNS_ESS_ESR1 | 50.0 | 1.1 | 169.0 | 199.0 | 32.5 | 31.0 | 6.2 | 19.7 | 43.1 | 247.7 | 32.0 | 31.7 |
| NOBLESLR_ESR2 | 63.0 | 1.0 | 182.0 | 199.0 | 29.8 | 30.6 | 3.3 | 16.5 | 49.6 | 0.0 | 21.8 | 13.9 |
| DKNS_ESS_ESR2 | 50.0 | 1.1 | 171.0 | 199.0 | 31.3 | 30.2 | 6.5 | 17.8 | 45.5 | 191.0 | 37.1 | 34.0 |
| DKNS_ESS_ESR3 | 50.0 | 1.1 | 170.0 | 199.0 | 31.0 | 30.0 | 6.6 | 18.7 | 44.7 | 217.7 | 34.5 | 35.2 |
| STAM_SLR_ESR1 | 72.0 | 1.8 | 180.0 | 199.0 | 29.2 | 29.9 | 3.1 | 36.4 | 30.6 | 0.0 | 28.3 | 22.9 |
| PALE_ESS_ESR1 | 200.2 | 1.1 | 177.0 | 199.0 | 28.1 | 29.1 | 7.6 | 24.0 | 39.3 | 1,003.5 | 37.4 | 35.7 |
| FIVEWSLR_ESR1 | 220.0 | 1.3 | 175.0 | 199.0 | 28.9 | 29.0 | 9.8 | 20.5 | 40.6 | 387.8 | 34.5 | 34.8 |
| DKNS_ESS_ESR4 | 50.0 | 1.1 | 170.0 | 199.0 | 30.1 | 28.9 | 7.2 | 19.1 | 44.9 | 216.4 | 33.6 | 34.0 |
| CROSSTRL_ESR1 | 58.0 | 2.3 | 194.0 | 199.0 | 28.2 | 28.7 | 9.4 | 9.6 | 52.3 | 0.0 | 47.7 | 45.3 |
| HYDR_ESS_ESR1 | 201.5 | 1.1 | 180.0 | 199.0 | 28.7 | 28.6 | 7.0 | 20.0 | 44.4 | 222.6 | 35.5 | 34.0 |
| TANZ_ESS_ESR1 | 128.9 | 2.3 | 94.0 | 199.0 | 19.0 | 28.5 | 8.3 | 20.0 | 43.2 | 64.5 | 28.3 | 27.7 |
| TANZ_ESS_ESR2 | 128.9 | 2.4 | 91.0 | 199.0 | 16.4 | 28.0 | 9.9 | 22.1 | 39.9 | 101.1 | 27.2 | 26.2 |
| ANCHOR_ESR2 | 36.3 | 1.7 | 161.0 | 199.0 | 25.7 | 27.9 | 10.0 | 34.1 | 28.0 | 9.2 | 22.2 | 16.9 |
| STRG_SLR_ESR1 | 101.9 | 2.1 | 173.0 | 199.0 | 25.5 | 27.4 | 17.8 | 0.0 | 54.8 | 0.0 | 8.0 | 5.8 |
| EVLN_ESS_ESR1 | 203.7 | 2.1 | 138.0 | 199.0 | 19.8 | 27.2 | 18.8 | 0.0 | 54.0 | 0.0 | 11.6 | 8.2 |
| PAVO_ESS_ESR1 | 87.5 | 1.1 | 162.0 | 199.0 | 24.9 | 27.1 | 14.2 | 17.8 | 40.9 | 151.2 | 33.1 | 30.5 |
| PAVO_ESS_ESR2 | 89.0 | 1.1 | 161.0 | 199.0 | 25.8 | 27.1 | 8.1 | 21.4 | 43.3 | 1,107.2 | 33.7 | 31.1 |
| NOBLESLR_ESR1 | 63.1 | 1.0 | 191.0 | 199.0 | 26.5 | 26.8 | 10.5 | 16.6 | 46.2 | 0.0 | 21.3 | 15.0 |
| GKS_BESS_ESR1 | 100.0 | 2.3 | 171.0 | 199.0 | 23.9 | 26.5 | 21.9 | 16.7 | 34.8 | 0.0 | 4.7 | 4.4 |
| BEXAR_ES_ESR1 | 101.9 | 1.0 | 161.0 | 199.0 | 31.9 | 26.1 | 0.1 | 8.5 | 65.3 | 0.0 | 32.0 | 25.0 |
| SUNVASLR_ESR2 | 46.9 | 1.1 | 172.0 | 199.0 | 25.1 | 25.8 | 7.5 | 17.5 | 49.3 | 29.9 | 14.3 | 11.2 |
| GAMBIT_ESR1 | 100.0 | 1.6 | 184.0 | 199.0 | 25.4 | 25.7 | 2.0 | 11.7 | 60.6 | 182.1 | 33.1 | 29.9 |
| RBN_ESR1 | 101.3 | 1.3 | 185.0 | 199.0 | 24.3 | 25.5 | 5.3 | 15.9 | 53.2 | 34.6 | 35.2 | 32.3 |
| SUNVASLR_ESR1 | 53.3 | 1.1 | 171.0 | 199.0 | 24.7 | 25.5 | 8.3 | 16.1 | 50.1 | 71.4 | 10.8 | 10.6 |
| FENCESLR_ESR1 | 71.0 | 1.8 | 180.0 | 199.0 | 25.7 | 25.2 | 8.2 | 30.1 | 36.5 | 35.7 | 24.5 | 21.3 |
| WZRD_ESS_ESR1 | 150.4 | 6.5 | 48.0 | 199.0 | 3.8 | 23.4 | 48.5 | 13.3 | 14.8 | 0.0 | 3.7 | 3.0 |
| ANCHOR_ESR1 | 35.2 | 1.7 | 157.0 | 199.0 | 17.8 | 19.1 | 11.2 | 32.7 | 37.0 | 1.2 | 17.8 | 15.8 |
| BATCAVE_ESR1 | 100.5 | 1.1 | 169.0 | 199.0 | 17.4 | 18.1 | 4.4 | 21.5 | 55.9 | 184.4 | 12.2 | 12.3 |
| LBRA_ESS_ESR1 | 200.3 | 1.1 | 168.0 | 199.0 | 15.9 | 16.5 | 6.6 | 22.0 | 54.9 | 214.9 | 26.7 | 30.9 |
| NF_BRP_ESR1 | 101.6 | 1.1 | 168.0 | 199.0 | 13.4 | 15.5 | 5.0 | 22.0 | 57.5 | 75.7 | 8.3 | 10.5 |
| EUNICE_ESR1 | 28.4 | 1.6 | 165.0 | 199.0 | 14.1 | 14.6 | 40.0 | 14.2 | 31.2 | 0.0 | 1.0 | 2.1 |
| TORT_ESS_ESR1 | 52.0 | 0.9 | 4.0 | 199.0 | 19.6 | 13.7 | 11.0 | 51.7 | 23.6 | 9.0 | 33.3 | 29.4 |
| NWF_ESR1 | 29.2 | 0.3 | 180.0 | 199.0 | 8.8 | 4.9 | 63.3 | 13.4 | 18.3 | 0.0 | 11.9 | 8.6 |

## 4. Where the ceiling is not credible: price-setting intervals

Fleet: **24.5%** of |perfect-foresight revenue| was earned on 15-min intervals containing at least one SCED run where the unit's own offer was within $1 of the LMP (21.1% of intervals). On those intervals a different dispatch would have moved the price, so the price-taker ceiling overstates what was available. This is flagged, not subtracted.

Units above 50%: RRANCHES_ESR1, CARN_ESS_ESR1, RRANCHES_ESR2.

## 5. Dispatch residual: the 20 biggest days vs the rest

| Days | unit-days | ceiling $M | ceiling share % | residual $M | residual share % | capture % |
|---|---|---|---|---|---|---|
| top 20 days | 2,275.0 | 122.6 | 39.7 | 38.8 | 39.9 | 44.1 |
| other days | 19,918.0 | 186.0 | 60.3 | 58.4 | 60.1 | 41.5 |

Top days: 2025-12-14, 2026-01-20, 2026-01-24, 2026-01-25, 2026-01-26, 2026-01-27, 2026-01-28, 2026-01-31, 2026-02-01, 2026-03-16, 2026-03-23, 2026-03-24, 2026-04-09, 2026-04-11, 2026-04-20, 2026-04-24, 2026-04-27, 2026-04-28, 2026-05-26, 2026-06-06
