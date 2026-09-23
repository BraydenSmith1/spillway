# ERCOT Data — Findings

*Revised 2026-09-23 · Window: Aug 2025 – Jul 2026 · All numbers from `data/raw/`*

Everything below was computed with DuckDB over the project's Parquet files.
Each finding names its source and logic, so any number can be re-derived or
challenged. **Exploratory results, not validated conclusions** — caveats are
inline.

**What changed on 09-23.** §3 is rewritten. ERCOT's System Lambda (the
grid-wide energy price, `np6-322-cd`) was downloaded and joined to every
curtailed interval, so the oversupply-vs-congestion question is now answered
exactly rather than by the shadow-price lift heuristic: 71% of solar and 84%
of wind curtailment is congestion. The earlier claim that this split "needs
shift factors ERCOT does not publish" was wrong and is corrected — shift
factors are needed to name lines, not to separate congestion from glut.

**What changed on 09-17.** A second measurement error, larger than the first.
ERCOT ran SCED every **15 minutes before RTC+B and every 5 minutes after**
(96 vs ~290 runs/day). Every energy figure had assumed 5 minutes throughout,
which understated pre-RTC MWh threefold and, because the low-curtailment
autumn months were underweighted, *overstated* pooled percentages. Absolute
energy and pooled-percentage figures below are corrected; interval length is
now derived per day (`analysis/interval_hours.py`) rather than hardcoded.
**§2, §3 and §6 were unaffected** — they cover Jan–Jun 2026 or Dec 2025
onward, entirely post-RTC, where MW/12 was correct.

**What changed on 09-14.** Two things. (1) The crosswalk now
exists, so curtailment can be joined to each unit's *own* node price, to the
constraints that were binding, and to county and owner. (2) A timezone error
was found and fixed: DuckDB was evaluating SCED timestamps in Mountain time,
one hour off ERCOT's Central clock. Monthly totals were unaffected;
hour-of-day tables were mislabeled by an hour, and the SCED-to-price joins
were misaligned by one interval, which *understated* the price relationship.
Corrected figures below; the old ones are noted where they moved.

---

## 0. How curtailment is measured

```
curtailment = HSL − Base Point          (when HSL > Base Point + 1 MW)
```

`HSL` = what the unit could produce; `Base Point` = what ERCOT instructed;
unit status `ON`; `HSL > 0`.

**Interval length is derived per day, never hardcoded.** ERCOT ran SCED every
15 minutes through 2025-12-04 and every 5 minutes from 2025-12-10, so
MW → MWh uses `24 / (SCED runs that day)`. See `analysis/interval_hours.py`.

**Only meaningful for intermittent resources.** For gas, coal or storage,
`HSL − Base Point` is just "not at maximum" — normal dispatch, not curtailment.

*Source: `sced_60day`. Row-level audit trail: `analysis/show_your_work.py`.*

---

## 1. ERCOT-wide curtailment

| Fuel | Units | Potential (TWh) | Curtailed (TWh) | % |
|---|---|---|---|---|
| WIND | 382 | 112.63 | 5.59 | **4.97%** |
| PVGR (solar) | 289 | 71.94 | 4.58 | **6.37%** |

*(Duration-aware. The 09-14 version read 5.5% and 7.2% on 4.94/3.98 TWh,
inflated by the SCED cadence error.)*

**System-wide is 5–6%. The worst farms are 22–31%.** Both are true; quote the
right one. The brief's 12% (§4.1) is roughly **double** the system average and
well below the tail Spillway targets.

Concentration — of 298 solar units, the top 10 carry **22.8%** of all solar
curtailment and the top 50 carry **69.5%**. Fifty sites ≈ 70% of the resource.

Seasonality — near zero in Aug–Sep, peaking Feb–Mar (44–56% at the worst
farms), falling back through summer. The five most-curtailed solar units threw
away **566,957 MWh** over twelve months, a weighted **25.4%** of potential.

By hour (corrected to Central; daylight only for solar): solar curtailment
climbs from ~1% at 07:00 to a plateau of **7–8% from 11:00–16:00**; wind peaks
at **10.6% at 15:00**. Nighttime solar percentages in the raw table are
artifacts of tiny denominators and should be ignored (see §9).

---

## 2. ⭐ Curtailed energy valued at the generator's own node

This is the central result. Jan–Jun 2026, every wind/solar unit the crosswalk
could place at a price node (91% of them), each curtailed 5-minute interval
joined to the price **at that unit's own settlement point**:

| | Curtailed MWh | at price < $0 | at price < $15 | Avg $/MWh at node | Value at node | Value if negatives floored at $0 |
|---|---|---|---|---|---|---|
| **Solar** | 3,183,146 | **96.5%** | 99.4% | **−$8.60** | **−$27.4 M** | $1.10 M |
| **Wind** | 3,488,654 | **95.7%** | 99.4% | **−$11.50** | **−$40.1 M** | $0.84 M |

Read the last two columns carefully. Three terawatt-hours of solar were
spilled in six months. Valued at what the market was paying at that place and
moment, producing it would have *cost* the owners $27 million. Even counting
every negative-price interval as worth $0 — the most generous framing for a
PTC-less owner — the foregone revenue was **$1.1 million, or about $0.35 per
MWh.**

**The spilled energy is worth nothing to the people spilling it.** That is the
premise of the entire business, and it holds at the unit level, not just on
average. Every one of the ten most-curtailed solar units shows 94–100% of its
curtailment at a negative own-node price:

| Unit | Curtailed MWh | % at negative price | Avg $/MWh |
|---|---|---|---|
| GALLOWAY_SOLAR1 | 105,899 | 97% | −$7 |
| SPTX12B_UNIT1 | 87,664 | 96% | −$3 |
| REDBARN_UNIT_1 | 86,346 | 98% | −$4 |
| RIGGINS_UNIT1 | 79,712 | 95% | −$3 |
| WAYMARK_UNIT1 | 77,426 | 94% | −$3 |
| JADE_SLR_UNIT2 | 66,412 | 100% | −$11 |
| PROSPERO_UNIT1/2 | ~65,000 each | 99% | −$4 |

*(The 09-12 version reported 78% using the West hub as a proxy, with the
timezone misalignment. Own-node, correctly aligned: 96%.)*

**What it does not settle:** at a negative price you cannot tell from this
data whether ERCOT ordered the unit off or the unit chose to stop. For the
economics it barely matters — the energy is worthless either way — but for the
contract language ("verified curtailment hours", §4.2) it does. §3 is the
partial answer.

*Source: `analysis/curtailment_vs_node_price.py`.*

---

## 3. Congestion or oversupply — exactly, per curtailed MWh

ERCOT's nodal price is **LMP = System Lambda + congestion component** — there
is no marginal-loss term. Lambda is the energy price for the grid as a whole;
the congestion component is what a full line adds or subtracts at this node.
Both are public. So every curtailed 5-minute interval, joined to the unit's
own node, classifies by one subtraction:

| Lambda | Own-node LMP | Reading |
|---|---|---|
| ≤ 0 | — | **oversupply** — Texas as a whole had more power than it wanted |
| > 0 | < 0 | **congestion** — the grid wanted power; this node was stuck behind a full line |
| > 0 | ≥ 0 | other — curtailed at a positive price (local limits, ramping, operator choice) |

Sep 2025 – Jul 2026, 1.47 M curtailed unit-intervals at node-linked units,
100% matched to both a 5-minute LMP and a lambda:

| | Curtailed GWh | Congestion | Oversupply | Other |
|---|---|---|---|---|
| **Solar** | 4,233 | **70.7%** | 26.1% | 3.2% |
| **Wind** | 5,119 | **84.0%** | 10.8% | 5.1% |

**Curtailment in ERCOT is overwhelmingly congestion, not glut.** Seven in ten
curtailed solar MWh and more than eight in ten wind MWh were spilled while the
grid as a whole still wanted the power. The oversupply share lives in two
months:

| Month | GWh | Oversupply | Congestion | Avg λ when curtailed |
|---|---|---|---|---|
| 2025-10 | 711 | 19% | 77% | $20 |
| 2025-12 | 790 | 9% | 86% | $22 |
| **2026-01** | 981 | **47%** | 49% | $15 |
| **2026-02** | 1,259 | **44%** | 53% | **$4** |
| 2026-03 | 1,621 | 12% | 85% | $15 |
| 2026-04 | 1,380 | **0.4%** | **96%** | $28 |
| 2026-06 | 881 | 0% | 95% | $23 |

January–February 2026 — the negative-price peak in §5 — is the only period in
which System Lambda itself collapsed (averaging $4 in February) and
curtailment was a genuine Texas-wide surplus. By April, 96% of curtailment was
congestion with lambda at $28: the state wanted the power and could not move
it.

**The dollar view.** Curtailed solar under congestion was worth **−$37 M** at
its own nodes and **+$56 M** at the system price. The congestion component
averaged **−$31/MWh** on curtailed solar and **−$36/MWh** on curtailed wind.
That ~$93 M on solar alone is the price of being on the wrong side of a wire.

**Per site.** The top sites are 70–94% congestion. A Permian cluster — CMPD,
ASCK, MERCURY, FILESSLR — sits at 90–94% with congestion components of −$58
to −$63/MWh: the most stranded energy in Texas. Wind is more uniformly
congested than solar.

| Site | Fuel | Curtailed GWh | Congestion | Congestion $/MWh | Owner |
|---|---|---|---|---|---|
| GALLOWAY_SOLAR1 | solar | 127 | 74% | −17 | 225DD 8me LLC |
| REDBARN_UNIT_1 | solar | 115 | 77% | −18 | — |
| SPTX12B_UNIT1 | solar | 109 | 80% | −17 | RWE Clean Energy |
| CMPD_SLR_SOLAR2 | solar | 103 | **94%** | **−60** | — |
| MISAE_UNIT1 | solar | 95 | 81% | −22 | Childress Solar Park LLC |
| ASCK_SLR_SOLAR2 | solar | 87 | **94%** | **−63** | — |
| HRFDWIND_JRDWIND2 | wind | 191 | 88% | −29 | — |
| SHANNONW_UNIT_1 | wind | 186 | 85% | −24 | 1370 Shannon LLC |
| MIAM1_G2 | wind | 134 | 91% | −26 | Invenergy |
| PENA_UNIT1 | wind | 110 | 93% | −35 | — |

Full per-site (top 50 solar, top 20 wind) and site × month tables:
`analysis/lambda_split_tables.md`; per-unit values are in `registry/generation.csv`.

**What this means for a contract.** The two kinds of curtailment have
opposite trajectories. Congestion has a cure with a schedule — ERCOT's
transmission plan, and the Permian-basin build-out in particular — so a site
that is 94% congestion-curtailed today may be far less so once the line is
built. Oversupply has no cure and grows with every gigawatt of solar, but it
is contested by every battery on the system. A multi-year exclusive on a
congestion site is a bet on the transmission schedule; on an oversupply site,
a bet against the battery build-out.

**Which line?** Shadow prices still answer that. The binding intervals of
`225T558_1` coincide with curtailment far above chance at four of the top
twelve solar sites, and `PNHNDL` with 19% of HRFDWIND's — those are the
corridors. Apportioning congestion *across named lines* needs shift factors,
which ERCOT does not publish. The split between oversupply and congestion does
not: it needs only System Lambda, which is public. The earlier statement here
that "apportioning between them needs shift factors" was wrong.

*Source: `analysis/curtailment_lambda_split.py` (primary);
`analysis/congestion_attribution.py` (corridor hint). Lambda from
`np6-322-cd`, fetched by `scripts/fetch_lambda.py`.*

---

## 4. Where, and whose

Via the crosswalk, for the 42% of wind/solar units it can place (which hold
**45% of all curtailed MWh** and 25 of the 50 most-curtailed units):

**By county, Aug 2025 – Jul 2026**

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

Pecos County — the brief's §4.1 archetype — is real: eight placed units,
339 GWh spilled, 17.7%.

**By owner**

| Owner | Units | Curtailed GWh | % of potential |
|---|---|---|---|
| Invenergy Services LLC | 12 | **599.4** | 17.4% |
| RWE Clean Energy | 29 | 495.3 | 6.0% |
| Starwood Energy Group Global | 2 | 290.1 | **26.7%** |
| Intersect USA, LLC | 6 | 256.4 | 12.4% |
| 225DD 8me LLC *(Galloway)* | 2 | 196.8 | 23.2% |
| Childress Solar Park LLC | 2 | 188.8 | **35.2%** |
| 1370 Shannon LLC | 1 | 185.8 | **31.2%** |
| Concho Bluff LLC | 2 | 144.8 | 28.1% |
| Onward Energy | 5 | 116.5 | 5.0% |

This is the §6.3 screening filter in numbers. RWE is second by volume but
loses only 6% — well-sited, and a large portfolio owner unlikely to sign a
site-level deal. Childress Solar Park loses **35%** of everything it could
make, at two units, held by a single-asset LLC. **That is the shape of a
first call.**

**Galloway, fully resolved:** node `GALO_RN1`, Concho County, owned by
225DD 8me LLC, 250 MW nameplate, operating since 2021, **127.0 GWh curtailed
over twelve months (22%)**, 97% of it at a negative price.

*Source: `analysis/curtailment_by_county_owner.py`, `crosswalk/crosswalk.csv`.
Coverage caveat: rollups cover placed units only; `REDBARN`, `SPTX12B`,
`WAYMARK`, `RIGGINS` remain unplaced — see `crosswalk/README.md`.*

---

## 5. Prices

35.9 million real-time intervals, all settlement points:

| Mean | Median | Min | Max | Negative | > $100 | > $1,000 |
|---|---|---|---|---|---|---|
| $32.00 | $24.84 | −$251 | $13,036 | **6.85%** | 3.02% | 0.031% |

Negative prices by month track curtailment exactly: 0.76% in Aug 2025,
**15.0% in Feb 2026** (average price $20.10), back to 2% by July.

**Day-ahead vs real-time**, all seven hubs: DAM cleared **$2–3/MWh above RT**
consistently, with an average absolute gap of **$11–13**. Direction is small,
magnitude large. HB_PAN (Panhandle) is the cheapest hub at $22.61 RT.

---

## 6. Batteries

Fleet of 313→335 units (Dec 2025–Jul 2026), charging **720–860 GWh/month**,
implied round-trip efficiency **80–85%** — a sanity check that the data and
arithmetic are sound.

Behaviour, March 2026, corrected to Central:

| Hour | Charging MWh | Discharging MWh |
|---|---|---|
| 07 | 3,289 | **72,202** |
| 09 | **65,642** | 8,948 |
| 12–15 | ~53,000 | ~5,500 |
| **19** | 2,703 | **137,884** |
| 20 | 3,005 | 108,798 |

Charge through the solar glut, discharge into the 7–8 pm peak. **Batteries
are already absorbing ~700 GWh/month of exactly the midday energy Spillway
targets.** §15's cannibalization risk is present tense.

*(09-12 version had these an hour early.)*

---

## 7. Congestion, system-wide

| Constraint | Intervals binding | Avg shadow price | Max |
|---|---|---|---|
| NELRIO | 32,590 | $11.60 | $978 |
| 6437__F | 21,503 | **$131.25** | $3,500 |
| HARGRO_TWINBU1_1 | 15,069 | **$292.08** | $3,500 |

Frequency and severity are different things; several hit the $3,500 cap.

---

## 8. RTC+B before/after — suggestive only

| | Before (Aug–Dec 25) | After (Dec 25–Jul 26) |
|---|---|---|
| Mean price | $33.52 | $28.93 |
| Volatility (σ) | 27.1 | **49.4** |
| % negative | 2.85% | **8.83%** |

Direction matches ERCOT's predictions, but the windows are different seasons
and negative prices are strongly seasonal. **Not causal.** A same-season test
needs one more year of prices (cheap to fetch).

ERCOT's own wind forecast misses by **4–11%** (MAE), worst in March — the
benchmark any forecast product must beat.

---

## 9. Data-quality traps found

Each produced a plausible-looking wrong answer first.

1. **Timezone.** DuckDB defaulted to the Mac's zone (Mountain); SCED stamps are
   Central. Hour tables shifted; joins misaligned. Fixed by pinning every
   session to `America/Chicago`. *This is the DST/timezone trap the TODO
   warned about, and it was in the analysis for two days before it was caught.*
2. **Denominator.** Filtering to curtailed intervals before computing a share
   reported 96% curtailment everywhere. The tolerance belongs in the numerator.
3. **Small denominators.** Solar "15.9% curtailed at 23:00" — over 401 MWh vs
   5.9 million at midday. Some units report large HSL at night (co-located
   storage or telemetry). Restrict solar to daylight.
4. **Phantom nodes.** Several nodes averaging exactly $0.00 for a month had
   **one row** each. Check `COUNT(*)` before trusting an average.
5. **"Any constraint binding"** is true 99% of the time and therefore says
   nothing. Use lift.
6. **Fuel-type misapplication.** `HSL − Base Point` on gas/coal/storage is not
   curtailment. Storage also *moves*: `PWRSTR` in `sced_60day` through Dec
   2025, then the separate ESR file after RTC+B.
7. **SCED cadence changed at RTC+B** — 15-minute intervals before
   2025-12-05, 5-minute after. Hardcoding `MW / 12` understated pre-RTC energy
   threefold and skewed every pooled percentage across the boundary. Derive
   interval length from the data (`analysis/interval_hours.py`). *Caught on
   09-17, three days after the numbers were first published. The tell was
   an unrelated check: HASL and LASL turned out to be NULL after December,
   which led to counting SCED runs per day.*
8. **EIA's node field** is a hint, not a key (`_ES_` vs `_ESS_`, literal
   "ERCOT"). A first version of the matcher also only accepted nodes it had
   *already* linked, silently dropping Galloway's.

---

## 10. What this means for Spillway

**Strengthened, now at unit level rather than in aggregate:**
- Spilled energy is worth **nothing** to its owner — 96% of it occurs at a
  negative own-node price, and the total foregone revenue across 3 TWh was
  ~$1 M. A $12/MWh offer competes against a loss.
- Curtailment is **concentrated** (50 sites ≈ 70%) and **placeable**: the
  crosswalk now gives county and owner for sites carrying 45% of it, with a
  ranked list of what remains.
- **Curtailment is congestion, not glut**: 71% of solar and 84% of wind
  curtailed MWh occurred while the grid as a whole still wanted power. That is
  the kind a site contract can be underwritten against — with the caveat that
  congestion has a cure on a schedule (transmission) and oversupply does not.

**Complicated:**
- System-wide curtailment is 5–6%. Say "the worst-hit sites lose a fifth to a
  third," not "ERCOT wastes 30%." The brief's 12% assumption is about double
  the system-wide reality.
- Batteries are already taking ~700 GWh/month of this resource.
- Strong seasonality: a load sized on annual figures idles in August.
- The oversupply/congestion split is exact (System Lambda), but naming *which
  line* at a site still needs shift factors ERCOT doesn't publish; the
  shadow-price lift only identifies corridors.

**Next, in order:** twenty manual lookups in `crosswalk/aliases_todo.csv`
(moves placed coverage from ~45% to ~80% of curtailed MWh); a same-season RTC
comparison; then a forecast baseline.

---

## Reproducing this

`analysis/explore_0*.py` regenerate §1, §5–8. `curtailment_vs_node_price.py`,
`curtailment_lambda_split.py`, `congestion_attribution.py`,
`curtailment_by_county_owner.py` regenerate
§2–4. `python crosswalk/build.py` rebuilds the crosswalk. `python
scripts/audit.py` reports coverage. Every DuckDB session is pinned to
Central time.
