# ERCOT Data — Findings

*Revised 2026-09-14 · Window: Aug 2025 – Jul 2026 · All numbers from `data/raw/`*

Everything below was computed with DuckDB over the project's Parquet files.
Each finding names its source and logic, so any number can be re-derived or
challenged. **Exploratory results, not validated conclusions** — caveats are
inline.

**What changed since the 09-12 version.** Two things. (1) The crosswalk now
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
5-minute rows so MW ÷ 12 = MWh; unit status `ON`; `HSL > 0`.

**Only meaningful for intermittent resources.** For gas, coal or storage,
`HSL − Base Point` is just "not at maximum" — normal dispatch, not curtailment.

*Source: `sced_60day`. Row-level audit trail: `analysis/show_your_work.py`.*

---

## 1. ERCOT-wide curtailment

| Fuel | Units | Potential (TWh) | Curtailed (TWh) | % |
|---|---|---|---|---|
| WIND | 392 | 90.47 | 4.94 | **5.5%** |
| PVGR (solar) | 298 | 55.08 | 3.98 | **7.2%** |

**System-wide is 5–7%. The worst farms are 26–37%.** Both are true; quote the
right one. The brief's 12% (§4.1) is *above* the system average and *below*
the tail Spillway targets.

Concentration — of 298 solar units, the top 10 carry **22.7%** of all solar
curtailment and the top 50 carry **69.7%**. Fifty sites ≈ 70% of the resource.

Seasonality — near zero in Aug–Sep, peaking Feb–Mar (solar 12–13% system-wide,
44–56% at the worst farms), falling back through summer.

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

## 3. Congestion or oversupply — and which line?

Shadow prices identify every transmission constraint binding at each SCED run.
Joined to curtailment on the exact timestamp:

**99.2% of solar and 99.7% of wind curtailment occurred while at least one
constraint was binding somewhere in ERCOT.** That sounds decisive and is not:
with hundreds of constraints, one is nearly always binding. "Any constraint" is
not discriminating.

What *is* informative is which constraint's binding intervals coincide with a
given unit's curtailment far more than chance ("lift"):

| Unit | Most-implicated constraint | Lift | Share of unit's curtailment |
|---|---|---|---|
| REDBARN_UNIT_1 | 656T656_1 | 5.7× | 3% |
| SPTX12B_UNIT1 | **225T558_1** | 5.0× | 4% |
| SRWE1_SRWE2, SRWE1_UNIT1, MWEC_G1 | **225T558_1** | 3.3–4.0× | 2% |
| SHANNONW_UNIT_1, MIAM1_G1/G2 | HCKSW_MR2L | 3.8–4.5× | 11–12% |
| PENA_UNIT1 | FORMOS_JOSLIN1_1 | 4.0× | 3% |
| HRFDWIND_JRDWIND1/2 | PNHNDL | 2.8× | **19%** |

Two readings. First, **constraint `225T558_1` is implicated at four of the top
twelve sites** — a shared corridor, which is exactly the "structural
congestion" §2.2 of the TODO says a long-term contract can be underwritten
against. Second, the share column is small: no single line explains most of
any unit's curtailment. The honest interpretation is that these sites sit
behind *several* recurring constraints at once, with system-wide oversupply
underneath. Apportioning between them properly needs shift factors, which
ERCOT does not publish here.

*Source: `analysis/congestion_attribution.py`.*

---

## 4. Where, and whose

Via the crosswalk, for the 42% of wind/solar units it can place (which hold
**45% of all curtailed MWh** and 22 of the 50 most-curtailed units):

**By county, Aug 2025 – Jul 2026**

| County | Units | Curtailed GWh | % of potential |
|---|---|---|---|
| Borden | 11 | 421.9 | 15.3% |
| Pecos | 8 | 309.1 | 21.3% |
| Roberts | 2 | 241.2 | **31.9%** |
| Concho | 12 | 231.1 | 10.4% |
| Andrews | 5 | 223.9 | 18.3% |
| Childress | 4 | 175.6 | 20.0% |
| Clay | 1 | 165.2 | **34.0%** |
| Dickens | 1 | 121.0 | 32.3% |

Pecos County — the brief's §4.1 archetype — is real: eight placed units,
309 GWh spilled, 21%.

**By owner**

| Owner | Units | Curtailed GWh | % of potential |
|---|---|---|---|
| Invenergy Services LLC | 12 | **546.1** | 19.8% |
| Starwood Energy Group Global | 2 | 250.5 | 28.6% |
| 225DD 8me LLC *(Galloway)* | 2 | 183.8 | 29.1% |
| West Texas Solar Project II LLC | 4 | 170.4 | 21.5% |
| Childress Solar Park LLC | 2 | 168.3 | **40.5%** |
| Prospero Energy Project (Longroad) | 4 | 165.9 | 15.9% |
| 1370 Shannon LLC | 1 | 165.2 | 34.0% |
| RWE Clean Energy | 23 | 97.0 | 1.9% |

The last row is the §6.3 screening filter in numbers: RWE has more units than
anyone but loses under 2% — well-sited, and a large portfolio owner unlikely to
sign a site-level deal. Childress Solar Park loses 40% of everything it could
make, at two units, held by a single-asset LLC. **That is the shape of a first
call.**

**Galloway, fully resolved:** node `GALO_RN1`, Concho County, owned by
225DD 8me LLC, 250 MW nameplate, operating since 2021, **118.6 GWh curtailed
over twelve months (28%)**, 97% of it at a negative price.

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
7. **EIA's node field** is a hint, not a key (`_ES_` vs `_ESS_`, literal
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
- Shared corridors exist (`225T558_1`), which is what a multi-year exclusive
  is underwritten against.

**Complicated:**
- System-wide curtailment is 5–7%. Say "the worst-hit sites lose a quarter to
  a third," not "ERCOT wastes 30%."
- Batteries are already taking ~700 GWh/month of this resource.
- Strong seasonality: a load sized on annual figures idles in August.
- No single constraint explains most of a site's curtailment; proper
  attribution needs shift factors ERCOT doesn't publish.

**Next, in order:** twenty manual lookups in `crosswalk/aliases_todo.csv`
(moves placed coverage from ~45% to ~80% of curtailed MWh); a same-season RTC
comparison; then a forecast baseline.

---

## Reproducing this

`analysis/explore_0*.py` regenerate §1, §5–8. `curtailment_vs_node_price.py`,
`congestion_attribution.py`, `curtailment_by_county_owner.py` regenerate
§2–4. `python crosswalk/build.py` rebuilds the crosswalk. `python
scripts/audit.py` reports coverage. Every DuckDB session is pinned to
Central time.
