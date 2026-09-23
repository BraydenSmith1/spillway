"""
model.py — battery energy arbitrage as a Pyomo optimisation.

The decision: at every settlement interval, how much to charge and how much to
discharge, given a price series, so that revenue over the horizon is maximised
while the battery stays within its physical limits.

Formulation
-----------
Sets
    T = {0 .. n-1}                 settlement intervals, each dt hours long

Parameters (mutable — one model per unit is re-solved every day)
    p[t]        price at interval t, $/MWh
    S_0         opening state of charge, MWh
    S_lo, S_hi  the SOC window in force today, MWh (defaults to the physical
                envelope; the anatomy narrows it to the operator's declared
                Min/Max SOC)
    up[t]       MW of upward reserve held (RegUp + RRS + ECRS + NonSpin)
    dn[t]       MW of RegDown held
    E_req[t]    MWh that must remain above S_lo to back the upward reserves
    E_dn[t]     MWh of headroom that must remain below S_hi for RegDown
    (all award parameters default to zero)

Fixed
    P_chg, P_dis   max charging / discharging power, MW
    eta_c, eta_d   charge / discharge efficiency (round trip = eta_c * eta_d)
    c_deg          degradation cost per MWh of throughput, $/MWh (0 to ignore)
    cycles_max     optional cap on daily throughput, in full cycles

Variables
    c[t] >= 0   charge power, MW
    d[t] >= 0   discharge power, MW
    s[t]        state of charge at END of interval t, MWh
    y[t]        binary: 1 = discharging mode, 0 = charging mode
    slo[t], shi[t] >= 0   slack on the reserve-energy constraints (penalised)

Objective   maximise  sum_t dt * p[t] * (d[t] - c[t])
                      - c_deg * dt * (c[t] + d[t]) / 2
                      - PENALTY * sum_t (slo[t] + shi[t])

Constraints
    s[t] = s[t-1] + eta_c*dt*c[t] - dt*d[t]/eta_d           SOC balance
    S_lo <= s[t] <= S_hi                                    SOC window
    c[t] <= P_chg ,  d[t] <= P_dis                          power limits
    (d[t]-c[t]) + up[t] <= P_dis ,  (c[t]-d[t]) + dn[t] <= P_chg   reserve headroom
                                                            (from net output)
    s[t] + slo[t] >= S_lo + E_req[t]                        energy behind reserves
    s[t] - shi[t] <= S_hi - E_dn[t]                         room for RegDown
    c[t] <= P_chg*(1-y[t]) ,  d[t] <= P_dis*y[t]            one mode at a time
    s[n-1] >= S_0                                           end where you started
    sum_t dt*d[t] <= cycles_max * (S_hi - S_lo)             optional cycle cap

The reserve-energy durations (Reg/RRS 0.5 h, ECRS 1 h, NonSpin 4 h) are applied
by the caller when it builds E_req from awards; the model only sees MWh. The
slacks exist because awards are 15-minute means of 5-minute SCED values and
the opening SOC is the real unit's, so a literally infeasible combination can
occur for an interval or two; the penalty is set above any realised ERCOT price
so slack is never used to make money. Slack consumed is reported on Dispatch.

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

# Above the highest settlement price observed in the data ($13,036/MWh), so
# reserve slack is only ever used when the constraints are literally
# infeasible, never as a source of revenue.
SLACK_PENALTY = 25_000.0


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
    slack_mwh: float = 0.0        # reserve-energy slack consumed (0 unless infeasible)

    @property
    def net_mw(self) -> np.ndarray:
        """Positive = discharging (export), negative = charging."""
        return self.discharge_mw - self.charge_mw


def build(battery: Battery, prices: np.ndarray, dt: float, soc0: float | None = None,
          mode_binaries: bool = False) -> pyo.ConcreteModel:
    n = len(prices)
    soc0 = battery.soc_min if soc0 is None else soc0

    m = pyo.ConcreteModel(name=f"arbitrage[{battery.name}]")
    m._battery = battery
    m.T = pyo.RangeSet(0, n - 1)
    m.dt = dt

    # --- mutable parameters: everything that changes day to day ------------
    m.p = pyo.Param(m.T, initialize=dict(enumerate(map(float, prices))), mutable=True)
    m.soc0 = pyo.Param(initialize=float(soc0), mutable=True)
    m.smin = pyo.Param(initialize=float(battery.soc_min), mutable=True)
    m.smax = pyo.Param(initialize=float(battery.soc_max), mutable=True)
    m.up = pyo.Param(m.T, initialize=0.0, mutable=True)
    m.dn = pyo.Param(m.T, initialize=0.0, mutable=True)
    m.ereq = pyo.Param(m.T, initialize=0.0, mutable=True)
    m.edn = pyo.Param(m.T, initialize=0.0, mutable=True)

    # --- variables ----------------------------------------------------------
    m.c = pyo.Var(m.T, bounds=(0, battery.p_chg))
    m.d = pyo.Var(m.T, bounds=(0, battery.p_dis))
    m.s = pyo.Var(m.T, bounds=(battery.soc_min, battery.soc_max))   # physical envelope
    m.slo = pyo.Var(m.T, bounds=(0, None))
    m.shi = pyo.Var(m.T, bounds=(0, None))

    # --- constraints --------------------------------------------------------
    def soc_balance(m, t):
        prev = m.soc0 if t == 0 else m.s[t - 1]
        return m.s[t] == prev + battery.eta_c * dt * m.c[t] - dt * m.d[t] / battery.eta_d
    m.soc_balance = pyo.Constraint(m.T, rule=soc_balance)

    m.window_lo = pyo.Constraint(m.T, rule=lambda m, t: m.s[t] >= m.smin)
    m.window_hi = pyo.Constraint(m.T, rule=lambda m, t: m.s[t] <= m.smax)

    # Reserves are measured from the unit's net operating point: a battery
    # charging at -100 MW can offer 200 MW of upward reserve by swinging to
    # +100. So headroom is on net output, not on the discharge variable alone.
    m.cap_up = pyo.Constraint(m.T, rule=lambda m, t: m.d[t] - m.c[t] + m.up[t] <= battery.p_dis)
    m.cap_dn = pyo.Constraint(m.T, rule=lambda m, t: m.c[t] - m.d[t] + m.dn[t] <= battery.p_chg)
    m.res_lo = pyo.Constraint(m.T, rule=lambda m, t: m.s[t] + m.slo[t] >= m.smin + m.ereq[t])
    m.res_hi = pyo.Constraint(m.T, rule=lambda m, t: m.s[t] - m.shi[t] <= m.smax - m.edn[t])

    m.end_state = pyo.Constraint(expr=m.s[n - 1] >= m.soc0)

    if battery.cycles_max is not None:
        m.cycle_cap = pyo.Constraint(
            expr=sum(dt * m.d[t] for t in m.T) <= battery.cycles_max * (m.smax - m.smin))

    if mode_binaries:
        m.y = pyo.Var(m.T, within=pyo.Binary)      # 1 = discharging mode
        m.chg_mode = pyo.Constraint(m.T, rule=lambda m, t: m.c[t] <= battery.p_chg * (1 - m.y[t]))
        m.dis_mode = pyo.Constraint(m.T, rule=lambda m, t: m.d[t] <= battery.p_dis * m.y[t])

    m.revenue = pyo.Objective(
        expr=sum(dt * (m.p[t] * m.d[t] - m.p[t] * m.c[t])
                 - battery.c_deg * dt * (m.c[t] + m.d[t]) / 2 for t in m.T)
             - SLACK_PENALTY * sum(m.slo[t] + m.shi[t] for t in m.T),
        sense=pyo.maximize)
    return m


def set_params(m: pyo.ConcreteModel, prices=None, soc0=None, smin=None, smax=None,
               awards: dict | None = None) -> None:
    """Update the mutable parameters in place.

    smin/smax default back to the physical envelope and awards back to zero
    when not given, so a re-solve never inherits the previous day's window or
    reserve position by accident.
    """
    bat = m._battery
    if prices is not None:
        for t, v in enumerate(prices):
            m.p[t] = float(v)
    lo = float(bat.soc_min if smin is None else smin)
    hi = float(bat.soc_max if smax is None else smax)
    m.smin, m.smax = lo, hi
    # The opening SOC must sit inside today's window or the first interval is
    # infeasible (the battery cannot jump 50 MWh in 15 minutes). Clip it.
    if soc0 is not None:
        m.soc0 = float(min(max(float(soc0), lo), hi))
    elif not (lo <= pyo.value(m.soc0) <= hi):
        m.soc0 = float(min(max(pyo.value(m.soc0), lo), hi))
    n = len(m.T)
    if awards is None:
        for t in m.T:
            m.up[t] = 0.0; m.dn[t] = 0.0; m.ereq[t] = 0.0; m.edn[t] = 0.0
    else:
        up, dn = awards["up"], awards["dn"]
        ereq, edn = awards["ereq"], awards["edn"]
        assert len(up) == n
        for t in m.T:
            m.up[t] = float(up[t]); m.dn[t] = float(dn[t])
            m.ereq[t] = float(ereq[t]); m.edn[t] = float(edn[t])


def set_prices(m: pyo.ConcreteModel, prices: np.ndarray, soc0: float | None = None) -> None:
    """Backward-compatible alias: prices (and opening SOC) only; window and
    awards are reset to their defaults."""
    set_params(m, prices=prices, soc0=soc0)


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
    T = list(m.T)
    try:
        res = solver().solve(m)
    except RuntimeError as e:                  # APPSI raises when there is no feasible point
        if "feasible solution was not found" not in str(e):
            raise
        nan = np.full(len(T), np.nan)
        return Dispatch(nan, nan, nan, objective=float("nan"), solve_status="infeasible")
    # Pyomo's legacy and APPSI result objects keep this in different places.
    status = str(getattr(getattr(res, "solver", res), "termination_condition", "unknown"))
    slack = float(sum(pyo.value(m.slo[t]) + pyo.value(m.shi[t]) for t in T))
    return Dispatch(
        charge_mw=np.array([pyo.value(m.c[t]) for t in T]),
        discharge_mw=np.array([pyo.value(m.d[t]) for t in T]),
        soc_mwh=np.array([pyo.value(m.s[t]) for t in T]),
        objective=float(pyo.value(m.revenue)),
        solve_status=status,
        slack_mwh=slack,
    )


def optimise(battery: Battery, prices: np.ndarray, dt: float, soc0: float | None = None,
             mode_binaries: bool = False, smin: float | None = None, smax: float | None = None,
             awards: dict | None = None) -> Dispatch:
    """One-shot convenience: build, set, solve, return the dispatch."""
    m = build(battery, prices, dt, soc0, mode_binaries)
    set_params(m, smin=smin, smax=smax, awards=awards)
    return solve(m)
