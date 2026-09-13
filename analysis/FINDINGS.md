# ERCOT Data — Exploratory Findings

*2026-09-12 · Window: Aug 2025 – Jul 2026 · All numbers from `data/raw/`*

Everything below was computed with DuckDB over the project's Parquet files.
Each finding lists the source dataset and the logic used, so any number can be
re-derived or challenged. **These are exploratory results, not validated
conclusions** — caveats are stated inline rather than buried at the end.

---

## 0. How curtailment is measured (read this first)

Every curtailment number here is:

```
curtailment = HSL − Base Point          (when HSL > Base Point + 1 MW)
```

- `HSL` — what the unit **could** produce that interval
- `Base Point` — what ERCOT **instructed** it to produce
- 5-minute rows, so MW ÷ 12 = MWh
- 1 MW tolerance so telemetry jitter isn't counted
- Filtered to `Telemetered Resource Status = 'ON'` and `HSL > 0`

**This formula only means "curtailment" for intermittent resources.** For a gas
plant, `HSL − Base Point` just means "not running flat out," which is normal
economic dispatch. Applying it to dispatchable fuels produces nonsense — see §1.

*Source: `data/raw/sced_60day/*.parquet`. Traceable row-by-row via
`analysis/show_your_work.py`.*

---

## 1. ERCOT-wide curtailment by fuel

| Fuel | Units | Potential (TWh) | "Curtailed" (TWh) | % |
|---|---|---|---|---|
| WIND | 392 | 90.47 | 4.94 | **5.5%** |
| PVGR (solar) | 298 | 55.08 | 3.98 | **7.2%** |
| CCGT90 (gas) | 199 | 110.69 | 14.06 | 12.7% ⚠️ |
| CLLIG (coal) | 22 | 49.43 | 11.44 | 23.2% ⚠️ |
| PWRSTR (storage) | 236 | 8.71 | 8.20 | 94.1% ⚠️ |

⚠️ **The gas, coal and storage rows are not curtailment.** A coal plant at 77%
of max is doing exactly what the market asked. A battery's `HSL` is its maximum
discharge, and it spends most of its time not discharging — hence the absurd
94%. **Only the WIND and PVGR rows are meaningful.**

> **Correction to something I said earlier:** I previously told you there were
> no batteries in `sced_60day`. That was wrong. Storage appears as resource
> type `PWRSTR` — **but only through Dec 2025**. From Jan 2026 the count drops
> to exactly zero, because RTC+B moved storage into its own ESR disclosure.
> You therefore have continuous battery coverage across the redesign: `PWRSTR`
> in `sced_60day` before, `sced_esr` after.

### ERCOT-wide is 5–7%. Your top farms are 26–37%.

This distinction matters enormously and I blurred it earlier. **System-wide
renewable curtailment is 5.5% (wind) and 7.2% (solar)** — *below* the 12% in
§4.1 of the brief. The 30% figure I quoted was the average of the five
**worst-affected** farms.

Both are true. Spillway targets the worst nodes, so the tail is the relevant
number — but **"ERCOT curtails 30%" is not a defensible claim** and would be
challenged immediately by anyone who knows the market. The defensible version:

> *"System-wide solar curtailment is ~7%, but it is highly concentrated: the
> ten worst-affected solar farms lose 26–37% of their potential output."*

### Concentration — the genuinely good news

Of 298 solar units:
- Top **10** units = **22.7%** of all solar curtailment
- Top **50** units = **69.7%** of all solar curtailment

**A portfolio of ~50 sites captures 70% of the entire ERCOT solar curtailment
opportunity.** That is a strong argument for the §4.9 portfolio model and a
direct answer to "how many contracts before this is a real business."

---

## 2. ⭐ Curtailment happens almost entirely at negative prices

Joining hourly solar curtailment to the HB_WEST hub price, Jan–Jun 2026:

| Hub price | Hours | Curtailed MWh | Share of all curtailment |
|---|---|---|---|
| **below $0** | 821 | 2,674,478 | **78.1%** |
| $0–15 | 825 | 598,023 | 17.5% |
| $15–40 | 1,788 | 124,306 | 3.6% |
| over $40 | 699 | 26,225 | 0.8% |

**95.6% of solar curtailment occurs when power is worth under $15/MWh, and 78%
when the price is outright negative.**

This is the single most important result here, and it cuts both ways:

**For the thesis.** The energy really is worthless at the moment it is spilled.
A generator facing a negative price is *paying* to produce. An offer of
$12/MWh (§4.2) isn't competing against $0 — it's competing against a loss.
That is a far stronger pitch than the brief assumes.

**Against the thesis.** At negative prices you cannot tell from this data
whether ERCOT *ordered* the farm off or the farm *chose* to stop. §1
distinguishes congestion from oversupply; this join does not. Resolving it
needs the shadow-price attribution in §6 below. Until then, "verified
curtailment hours" (§4.2) is not yet a defined quantity.

*Source: `sced_60day` joined to `settlement_point_prices` on the hour.*
*Caveat: uses HB_WEST as a single reference price. Node-level prices require
the crosswalk, which does not exist yet.*

---

## 3. Prices

Across 35.9 million real-time intervals (all settlement points, Aug 25 – Jul 26):

| Metric | Value |
|---|---|
| Mean | **$32.00** |
| Median | **$24.84** |
| Minimum | **−$251.00** |
| Maximum | **$13,036.40** |
| Negative | **6.85%** of intervals |
| Over $100 | 3.02% |
| Over $1,000 | 0.031% |

Mean well above median is the signature of a market where rare spikes carry a
large share of total value. The top 0.03% of intervals clear above $1,000.

### Negative prices by month

| Month | % negative | Avg price |
|---|---|---|
| 2025-08 | 0.76% | $36.96 |
| 2025-10 | 4.26% | $33.66 |
| 2025-12 | 5.84% | $34.96 |
| **2026-02** | **15.00%** | **$20.10** |
| 2026-03 | 13.98% | $23.32 |
| 2026-06 | 5.11% | $29.73 |

February 2026: **one interval in seven cleared below zero.** The seasonal shape
matches curtailment almost exactly — both peak in Feb–Mar and collapse in
August, when Texas summer demand absorbs everything available.

**Implication for load sizing (§4.3):** an annual average badly misrepresents
the resource. A load sized on the yearly figure sits idle through August and is
undersized through March. The interruptibility ladder in §3.1 matters more than
the brief implies.

---

## 4. Day-ahead vs real-time

| Hub | Avg DAM | Avg RT | RT − DAM | Avg absolute gap |
|---|---|---|---|---|
| HB_NORTH | $33.90 | $31.35 | −$2.55 | $12.27 |
| HB_WEST | $32.69 | $29.86 | −$2.83 | $13.36 |
| HB_HOUSTON | $34.48 | $31.70 | −$2.78 | $11.05 |
| HB_PAN | $25.94 | $22.61 | −$3.32 | $13.38 |
| HB_SOUTH | $34.52 | $32.45 | −$2.07 | $11.66 |

Two observations:

1. **Day-ahead cleared systematically above real-time — by $2–3/MWh at every
   hub.** Selling forward beat selling into real-time over this window. That is
   a hedging result, and it is consistent across all seven hubs, which makes it
   unlikely to be noise.
2. **The average absolute gap is $11–13/MWh** — four to five times the average
   bias. Direction is small; magnitude is large. That gap is the volatility
   batteries and traders monetise.

**HB_PAN (Panhandle) is the cheapest hub in ERCOT** at $22.61 real-time, ~$9
below the others — a wind-heavy, congested corner. Worth a look as a Spillway
target region.

---

## 5. Batteries

### Fleet

| Month | Units | Charged (MWh) | Discharged (MWh) | Implied round-trip |
|---|---|---|---|---|
| 2026-01 | 318 | 785,660 | 667,674 | 85.0% |
| 2026-03 | 325 | 719,281 | 600,409 | 83.5% |
| 2026-05 | 325 | 857,944 | 704,407 | 82.1% |
| 2026-06 | 335 | 823,415 | 654,368 | 79.5% |

Round-trip efficiency of 80–85% is exactly what you'd expect from lithium-ion
including auxiliary load — **a useful sanity check that the data and the
arithmetic are both sound.**

The fleet grew from 313 to 335 units in seven months, and the largest single
unit has ~950–983 MWh of usable capacity.

### Behaviour (March 2026, MWh by hour)

| Hour | Charging | Discharging |
|---|---|---|
| 06 | 3,289 | **72,202** |
| 09 | **79,668** | 3,878 |
| 14 | 53,887 | 5,351 |
| **18** | 2,703 | **137,884** |
| 19 | 3,005 | 108,798 |

Textbook arbitrage: charge hard through the midday solar glut, discharge into
the evening peak, with a smaller morning discharge around 06:00.

**This is the §15 cannibalization risk, quantified.** Batteries are already
absorbing the midday surplus — the exact hours and the exact energy Spillway
wants to buy. They are a direct competitor for the resource, not a hypothetical
one. The counter-argument in §9.5 (contract them, or sell them the forecast)
now has a number behind it: **~720,000 MWh/month of charging demand** already
competing for curtailed energy.

*Source: `data/raw/sced_esr/*.parquet`, Base Point sign convention — negative =
charging, positive = discharging.*

---

## 6. Congestion

Most frequently binding transmission constraints:

| Constraint | Intervals binding | Avg shadow price | Max |
|---|---|---|---|
| NELRIO | 32,590 | $11.60 | $978.58 |
| NE_LOB | 28,930 | $7.64 | $93.35 |
| WESTEX | 23,259 | $6.04 | $129.85 |
| 6437__F | 21,503 | **$131.25** | **$3,500.00** |
| HARGRO_TWINBU1_1 | 15,069 | **$292.08** | $3,500.00 |
| 587__A | 14,974 | $286.36 | $3,114.31 |
| LPLMK_LPLNE_1 | 14,836 | $219.71 | $3,500.00 |

**Frequency and severity are different things.** NELRIO binds most often but
costs $11.60 on average. HARGRO_TWINBU1_1 binds half as often at **25× the
cost**. Several hit exactly $3,500 — a system cap, not a market outcome.

For Spillway this is the §2.2 persistence test in raw form: a constraint
binding 20,000+ intervals across a year is structural, and structural
congestion is what a 5–10 year exclusive can be underwritten against.

*Source: `data/raw/shadow_prices/*.parquet`. **Not yet joined to specific
farms** — that needs the crosswalk.*

---

## 7. RTC+B before and after — suggestive, not conclusive

Hub prices either side of 2025-12-05:

| | Before RTC | After RTC | Change |
|---|---|---|---|
| Mean price | $33.52 | $28.93 | −14% |
| **Volatility (σ)** | **27.12** | **49.39** | **+82%** |
| % negative | 2.85% | 8.83% | **3.1×** |
| % over $200 | 0.318% | 0.925% | 2.9× |

Every direction matches what ERCOT predicted: lower average cost, higher
volatility.

**⚠️ Do not quote this as causal.** "Before" is Aug–Dec 2025; "after" is
Dec 2025–Jul 2026. The two windows are *different seasons*, and §3 above shows
negative prices are strongly seasonal, peaking in Feb–Mar regardless. A large
part of this gap is almost certainly spring, not market design.

A defensible version needs same-season comparison — Feb–Jun 2025 vs Feb–Jun
2026 — which requires extending the price download back another year. That is
cheap: prices are the fastest dataset to pull.

---

## 8. ERCOT's own wind forecast accuracy

System-wide short-term wind power forecast (`STWPF`) vs actual:

| Month | MAE (MW) | Avg actual (MW) | MAE % |
|---|---|---|---|
| 2025-09 | 412 | 9,401 | 4.4% |
| 2025-12 | 1,185 | 13,834 | 8.6% |
| 2026-03 | 1,987 | 17,957 | **11.1%** |
| 2026-05 | 894 | 13,041 | 6.9% |

ERCOT's own forecast misses by **4–11%**, worst in March — the same month
curtailment and negative prices peak. Error scales with output.

**Relevance to Layer 1 (§3.1):** this is the incumbent benchmark. A forecast
product must beat or usefully complement it. Note that ERCOT forecasts
*production*; Spillway would forecast *curtailment*, which is a different and
arguably harder target — but this sets the accuracy bar customers will expect.

---

## 9. Data-quality traps found along the way

Recording these because each one produced a plausible-looking wrong answer:

1. **The denominator trap.** Filtering to curtailed intervals *before*
   computing a percentage reported every farm at ~96% curtailment. The
   tolerance has to sit inside the numerator. Caught only because the summary
   and monthly tables disagreed.
2. **Small denominators.** Solar shows "15.9% curtailment" at 22:00 — computed
   over 401 MWh, versus 5.9 million MWh at midday. Meaningless. Some solar
   units report `HSL` up to 200 MW at night (likely co-located storage or
   telemetry error). **Filter solar to daylight hours.**
3. **Phantom nodes.** `ERKA_SLR_RN` and `CST2_SLR_RN` appeared to average
   exactly $0.00 for March 2026. They have **one row each** for the entire
   month. Always check `COUNT(*)` before trusting an average.
4. **Fuel-type misapplication.** `HSL − Base Point` on gas, coal or storage
   produces meaningless "curtailment." Restrict to WIND and PVGR.
5. **Resource types move.** `PWRSTR` vanishes from `sced_60day` in Jan 2026 —
   not a gap, a relocation to the ESR file at RTC+B.

---

## 10. What this means for Spillway

**Strengthened:**
- Curtailment is **highly concentrated** — 50 sites ≈ 70% of the solar
  opportunity, making a portfolio strategy tractable.
- Spilled energy is genuinely near-worthless: **78% of curtailment occurs at
  negative prices**. The $12/MWh offer beats a loss, not a zero.
- Worst-affected farms lose 26–37% of output — 2–3× the §4.1 assumption of 12%
  and far more spill per site than the 41 GWh modelled.

**Weakened or complicated:**
- **System-wide curtailment is 5–7%, not 12%.** The brief's assumption is
  aggressive at ERCOT level and only conservative at the tail. Be precise about
  which you're quoting.
- **Batteries are already taking this resource**, charging ~720 GWh/month
  concentrated in exactly the midday hours Spillway targets. §15's
  cannibalization risk is present tense, not future.
- **Strong seasonality** — near-zero curtailment in August, peak in Feb–Mar.
  The §4.3 flat-utilisation model doesn't match the resource shape.

**Still unanswerable without the crosswalk:**
- Which physical farm sits at which price node
- Whether a given curtailment event was ordered or economic
- Whether congestion at a specific site is structural or episodic

That last group is the binding constraint on everything now. **The crosswalk is
no longer a nice-to-have; it is what stands between these findings and a
site-specific pitch.**

---

## Reproducing this

All figures come from DuckDB queries over `data/raw/`. The curtailment
methodology is in `analysis/curtailment_by_farm.py`; the row-level audit trail
is `analysis/show_your_work.py`. Coverage and gaps: `python scripts/audit.py`.
