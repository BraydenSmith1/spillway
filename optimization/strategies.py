"""
strategies.py — the dispatch policies being benchmarked.

Each takes a battery and a day's worth of price data and returns a Dispatch.
Revenue is always evaluated against the REAL-TIME price the battery would
actually have settled at — the strategies differ only in what they knew when
they decided.

    fixed_schedule      charge midday, discharge evening, every day, no prices
    persistence         optimise on yesterday's prices, run it today
    dam_informed        optimise on today's day-ahead prices, settle real-time
    perfect_foresight   optimise on today's real-time prices — the upper bound
    actual              what the battery really did, from SCED telemetry

The gap between dam_informed and perfect_foresight is the value of a perfect
real-time forecast. The gap between actual and perfect_foresight is the
industry "capture rate". Neither is a criticism of the operator: they are
also selling ancillary services, which energy-only revenue ignores — see
benchmark.py for how that is handled.
"""

from __future__ import annotations

import numpy as np

from optimization.model import Battery, Dispatch, build, set_params, solve


def revenue(net_mw: np.ndarray, rt_price: np.ndarray, dt: float) -> float:
    """$ earned settling a net export profile at real-time prices."""
    return float(np.sum(dt * rt_price * net_mw))


def simulate(battery: Battery, desired_net_mw: np.ndarray, dt: float, soc0: float) -> Dispatch:
    """Run a requested profile through the battery's physics.

    Clips to power limits and the SOC window, applies efficiency. Used for
    heuristic strategies that don't come out of the optimiser and so may ask
    for something the battery can't do.
    """
    n = len(desired_net_mw)
    c = np.zeros(n); d = np.zeros(n); s = np.zeros(n)
    soc = soc0
    for t, want in enumerate(desired_net_mw):
        if want < 0:                                        # charge
            mw = min(-want, battery.p_chg, (battery.soc_max - soc) / (battery.eta_c * dt))
            c[t] = max(mw, 0.0)
            soc += battery.eta_c * dt * c[t]
        elif want > 0:                                      # discharge
            mw = min(want, battery.p_dis, (soc - battery.soc_min) * battery.eta_d / dt)
            d[t] = max(mw, 0.0)
            soc -= dt * d[t] / battery.eta_d
        s[t] = soc
    return Dispatch(c, d, s, objective=float("nan"), solve_status="simulated")


def fixed_schedule(battery: Battery, hours: np.ndarray, dt: float, soc0: float,
                   charge_hours=(10, 11, 12, 13, 14), discharge_hours=(18, 19, 20)) -> Dispatch:
    """The strategy anyone could write: charge when the sun is up, discharge
    at dinner time. Spreads the day's energy evenly across each window."""
    n = len(hours)
    want = np.zeros(n)
    chg_slots = np.isin(hours, charge_hours); dis_slots = np.isin(hours, discharge_hours)
    if chg_slots.any():
        want[chg_slots] = -battery.capacity / (chg_slots.sum() * dt * battery.eta_c)
    if dis_slots.any():
        want[dis_slots] = battery.capacity * battery.eta_d / (dis_slots.sum() * dt)
    return simulate(battery, want, dt, soc0)


class Optimiser:
    """Holds one Pyomo model per (battery, horizon length) and re-solves with
    new prices, which is ~10x faster than rebuilding each day."""

    def __init__(self, battery: Battery, dt: float, milp: bool = True):
        self.battery, self.dt, self.milp, self._models = battery, dt, milp, {}

    def run(self, prices: np.ndarray, soc0: float, smin: float | None = None,
            smax: float | None = None, awards: dict | None = None) -> Dispatch:
        """Solve one day. smin/smax narrow the SOC window; awards impose the
        unit's reserve position. Both reset to defaults when omitted."""
        n = len(prices)
        if n not in self._models:
            self._models[n] = build(self.battery, prices, self.dt, soc0, mode_binaries=self.milp)
        set_params(self._models[n], prices=prices, soc0=soc0, smin=smin, smax=smax, awards=awards)
        return solve(self._models[n])


def persistence(opt: Optimiser, yesterday_rt: np.ndarray, soc0: float) -> Dispatch:
    return opt.run(yesterday_rt, soc0)


def dam_informed(opt: Optimiser, today_dam: np.ndarray, soc0: float) -> Dispatch:
    return opt.run(today_dam, soc0)


def perfect_foresight(opt: Optimiser, today_rt: np.ndarray, soc0: float) -> Dispatch:
    return opt.run(today_rt, soc0)
