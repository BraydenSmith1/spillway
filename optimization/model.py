"""
model.py — battery energy arbitrage as a Pyomo optimisation.

The decision: at every settlement interval, how much to charge and how much to
discharge, given a price series, so that revenue over the horizon is maximised
while the battery stays within its physical limits.

Formulation
-----------
Sets
    T = {0 .. n-1}                 settlement intervals, each dt hours long

Parameters
    p[t]        price at interval t, $/MWh          (mutable — re-solve cheaply)
    P_chg       max charging power, MW
    P_dis       max discharging power, MW
    S_min, S_max  state-of-charge window, MWh
    S_0         opening state of charge, MWh
    eta_c, eta_d  charge / discharge efficiency (round trip = eta_c * eta_d)
    c_deg       degradation cost per MWh of throughput, $/MWh   (0 to ignore)
    cycles_max  optional cap on daily throughput, in full cycles

Variables
    c[t] >= 0   charge power, MW
    d[t] >= 0   discharge power, MW
    s[t]        state of charge at END of interval t, MWh

Objective   maximise  sum_t dt * ( p[t]*d[t] - p[t]*c[t] ) - c_deg * dt * (c[t] + d[t]) / 2

Constraints
    s[t] = s[t-1] + eta_c*dt*c[t] - dt*d[t]/eta_d          SOC balance
    S_min <= s[t] <= S_max                                  SOC window
    c[t] <= P_chg ,  d[t] <= P_dis                          power limits
    s[n-1] >= S_0                                           end where you started
    sum_t dt*d[t] <= cycles_max * (S_max - S_min)           optional cycle cap

LP or MILP? It depends on the sign of the price.
------------------------------------------------
A battery cannot charge and discharge at once. The textbook fix is a binary
"mode" variable per interval. A common shortcut drops it, arguing that with
round-trip efficiency below 1, simultaneous operation only wastes energy, so
the LP optimum never chooses it.

That argument is true when prices are non-negative — and false in ERCOT.
When the price is NEGATIVE and the battery is full, the LP relaxation charges
and discharges together on purpose: the round-trip loss "burns" stored energy,
freeing capacity to absorb more paid charging. That is a real arbitrage on
paper and impossible for an inverter. About 7% of ERCOT intervals clear below
zero, so the shortcut is not safe here. `mode_binaries=True` (the default in
the benchmark) adds the binaries; tests/test_model.py demonstrates the LP
exploiting negative prices and the MILP refusing to.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pyomo.environ as pyo


@dataclass(frozen=True)
class Battery:
    """Physical parameters, all in MW / MWh / hours."""
    name: str
    p_chg: float
    p_dis: float
    soc_min: float
    soc_max: float
    eta_c: float = 0.906          # sqrt(0.82): fleet round-trip measured from ESR data
    eta_d: float = 0.906
    c_deg: float = 0.0            # $/MWh throughput
    cycles_max: float | None = None

    @property
    def capacity(self) -> float:
        return self.soc_max - self.soc_min

    @property
    def duration_h(self) -> float:
        return self.capacity / self.p_dis if self.p_dis else float("nan")


@dataclass
class Dispatch:
    charge_mw: np.ndarray
    discharge_mw: np.ndarray
    soc_mwh: np.ndarray
    objective: float
    solve_status: str

    @property
    def net_mw(self) -> np.ndarray:
        """Positive = discharging (export), negative = charging."""
        return self.discharge_mw - self.charge_mw


def build(battery: Battery, prices: np.ndarray, dt: float, soc0: float | None = None,
          mode_binaries: bool = False) -> pyo.ConcreteModel:
    n = len(prices)
    soc0 = battery.soc_min if soc0 is None else soc0

    m = pyo.ConcreteModel(name=f"arbitrage[{battery.name}]")
    m.T = pyo.RangeSet(0, n - 1)
    m.dt = dt
    m.p = pyo.Param(m.T, initialize=dict(enumerate(map(float, prices))), mutable=True)
    m.soc0 = pyo.Param(initialize=float(soc0), mutable=True)

    m.c = pyo.Var(m.T, bounds=(0, battery.p_chg))
    m.d = pyo.Var(m.T, bounds=(0, battery.p_dis))
    m.s = pyo.Var(m.T, bounds=(battery.soc_min, battery.soc_max))

    def soc_balance(m, t):
        prev = m.soc0 if t == 0 else m.s[t - 1]
        return m.s[t] == prev + battery.eta_c * dt * m.c[t] - dt * m.d[t] / battery.eta_d
    m.soc_balance = pyo.Constraint(m.T, rule=soc_balance)

    m.end_state = pyo.Constraint(expr=m.s[n - 1] >= m.soc0)

    if battery.cycles_max is not None:
        m.cycle_cap = pyo.Constraint(
            expr=sum(dt * m.d[t] for t in m.T) <= battery.cycles_max * battery.capacity)

    if mode_binaries:
        m.y = pyo.Var(m.T, within=pyo.Binary)      # 1 = discharging mode
        m.chg_mode = pyo.Constraint(m.T, rule=lambda m, t: m.c[t] <= battery.p_chg * (1 - m.y[t]))
        m.dis_mode = pyo.Constraint(m.T, rule=lambda m, t: m.d[t] <= battery.p_dis * m.y[t])

    m.revenue = pyo.Objective(
        expr=sum(dt * (m.p[t] * m.d[t] - m.p[t] * m.c[t])
                 - battery.c_deg * dt * (m.c[t] + m.d[t]) / 2 for t in m.T),
        sense=pyo.maximize)
    return m


def set_prices(m: pyo.ConcreteModel, prices: np.ndarray, soc0: float | None = None) -> None:
    """Update the mutable parameters in place — avoids rebuilding per day."""
    for t, v in enumerate(prices):
        m.p[t] = float(v)
    if soc0 is not None:
        m.soc0 = float(soc0)


_solver = None


def solver():
    global _solver
    if _solver is None:
        _solver = pyo.SolverFactory("appsi_highs")
        # HiGHS's default MIP gap (1e-4) shows up as a few dollars of noise on
        # an $80k day. Tighten it so LP-vs-MILP comparisons mean something.
        _solver.config.mip_gap = 1e-6
    return _solver


def solve(m: pyo.ConcreteModel) -> Dispatch:
    res = solver().solve(m)
    # Pyomo's legacy and APPSI result objects keep this in different places.
    status = str(getattr(getattr(res, "solver", res), "termination_condition", "unknown"))
    T = list(m.T)
    return Dispatch(
        charge_mw=np.array([pyo.value(m.c[t]) for t in T]),
        discharge_mw=np.array([pyo.value(m.d[t]) for t in T]),
        soc_mwh=np.array([pyo.value(m.s[t]) for t in T]),
        objective=float(pyo.value(m.revenue)),
        solve_status=status,
    )


def optimise(battery: Battery, prices: np.ndarray, dt: float, soc0: float | None = None,
             mode_binaries: bool = False) -> Dispatch:
    """One-shot convenience: build, solve, return the dispatch."""
    return solve(build(battery, prices, dt, soc0, mode_binaries))
