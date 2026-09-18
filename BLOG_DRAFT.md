# I benchmarked a battery optimiser against 30 real Texas batteries. The dumb strategy won.

*Draft. ~800 words. Numbers from `optimization/results/`; long-form version
with the full formulation in `optimization/WRITEUP.md`.*

---

Every battery-arbitrage tutorial ends the same way: you write a linear
programme, feed it a year of prices, and report how much money it made. It's
a satisfying exercise and it proves nothing, because there's no answer key.
The optimiser is only ever compared to itself.

ERCOT publishes an answer key. Sixty days after the fact, its SCED disclosure
reports what every grid-scale battery in Texas actually did — dispatch
instruction and state of charge, every five minutes. So instead of asking
"what would an optimiser earn?", I could ask something better: **what did
real batteries earn, what could they have earned, and what explains the gap?**

## The setup

I pulled seven months of ERCOT data through its public API — real-time
prices at every node, day-ahead prices, ancillary-service clearing prices,
and the storage disclosure — and built a Pyomo MILP that dispatches a battery
against a day of prices. Then I ran it for the 30 largest active batteries,
every day from December 2025 to July 2026, **at each unit's own price node**,
opening each day at the state of charge the real unit actually had.

Five strategies, all settled at the same real-time price:

- **Fixed schedule** — charge 10:00–15:00, discharge 18:00–21:00, every day,
  no price information whatsoever.
- **Persistence** — optimise on yesterday's prices, run that today.
- **Day-ahead informed** — optimise on today's day-ahead prices, settle in
  real time. This is what an operator can actually do.
- **Perfect foresight** — optimise on today's real-time prices. Unattainable,
  but it's the ceiling everything is measured against.
- **Actual** — what the battery did, plus what it earned selling reserves.

## The result

| Strategy | $/kW-year | Capture |
|---|---|---|
| Fixed schedule | $29 | 53% |
| Persistence | $12 | 21% |
| Day-ahead informed | $28 | 51% |
| **Actual (energy + reserves)** | **$21** | **39%** |
| Perfect foresight | $54 | 100% |

Real batteries captured about **two-fifths** of what was on the table. The
best unit captured 70%. So 40% isn't physics — it's operations.

And the row I keep coming back to: **charging at noon and discharging at
dinner, with no price data at all, beat optimising against the day-ahead
market.** Over seven months, not one lucky week. ERCOT's evening peak is so
regular that a schedule shaped like the market catches it, while an optimiser
fed day-ahead prices commits to peaks that real time doesn't always deliver —
the two series differ by $11–13/MWh on an average interval. The lesson isn't
that optimisation fails; perfect foresight nearly doubles both. It's that
**a model fed the wrong signal loses to a heuristic that encodes the right
shape.**

## Where the money went

A handful of days. January and April each delivered $85–87/kW-yr annualised
under perfect foresight; June and July under $35. And on the two biggest
scarcity events of the winter — 21 January and 17 February — at least four of
the thirty batteries were *charging* when prices passed $3,000/MWh. One lost
$121,000 in a day against a possible +$150,000: a $270,000 swing on a single
unit. Two units at the same site did it on the same day, which looks like a
site-level schedule rather than bad luck.

Capture rate, it turns out, is decided on about a dozen days a year.

## The modelling detail that surprised me

Textbook battery models often skip the binary variable that stops a battery
charging and discharging at once. The argument: efficiency losses make it
wasteful, so the LP never chooses it. **That's true when prices are
positive and false in ERCOT**, where 7% of intervals clear *below zero*. With
a full battery and a negative price, the LP relaxation charges and discharges
simultaneously on purpose — burning stored energy through the round-trip loss
to make room for more paid charging. It's a real arbitrage on paper and
physically impossible. On real prices the relaxation over-claimed at 29 of the 30 units — by $50,000 on
the worst one — yet only 0.2% fleet-wide. Small today; it scales with every
gigawatt of solar that pushes prices below zero more often. I kept the binaries.

Two other sensitivities: a $10/MWh degradation charge <<DEG_DELTA>>, and a
1.5-cycle-per-day cap <<CYC_DELTA>>. The perfect-foresight strategy loves
shallow micro-cycles on small price ripples; a real operator with a warranty
does not.

## What I got wrong along the way

Two measurement errors, both mine, both caught by checking a claim rather
than by anything visibly breaking. DuckDB was reading ERCOT's Central-time
timestamps in my laptop's Mountain time, shifting every hour-of-day result by
an hour. And ERCOT changed SCED's cadence from 15-minute to 5-minute intervals
at its December market redesign — I'd hardcoded 5 minutes throughout, which
understated three months of energy threefold. Both are now derived from the
data and have regression tests. I'd rather say that here than have someone
find it.

## What's next

The optimiser only trades energy; real units also sell reserves, and post-RTC
ERCOT co-optimises the two. Adding reserve products as decision variables is
the obvious next model — it's the one ERCOT itself runs.

Code, data pipeline, tests, and the full formulation:
**[github.com/<you>/spillway]**.
