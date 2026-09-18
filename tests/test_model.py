"""
Tests for the battery arbitrage model. No data files needed — everything here
is synthetic, so it runs in CI.

Each test encodes something that was verified by hand during development,
including the one claim that turned out to be wrong (see test_lp_exploits_
negative_prices).
"""

import numpy as np
import pytest

from optimization.model import Battery, optimise
from optimization.strategies import Optimiser, fixed_schedule, revenue, simulate

DT = 0.25
BAT = Battery("TEST", p_chg=100, p_dis=100, soc_min=0, soc_max=200)   # 2-hour battery


def test_two_price_day_matches_analytic_answer():
    """12 hours at $10 then 12 hours at $100: fill up cheap, empty out dear.
    Revenue must equal the closed-form value to the dollar."""
    prices = np.array([10.0] * 48 + [100.0] * 48)
    d = optimise(BAT, prices, DT, soc0=0)
    expected = BAT.capacity * BAT.eta_d * 100 - (BAT.capacity / BAT.eta_c) * 10
    assert d.solve_status == "optimal"
    assert revenue(d.net_mw, prices, DT) == pytest.approx(expected, rel=1e-6)
    assert d.soc_mwh[-1] == pytest.approx(0.0, abs=1e-6)        # ends where it started


def test_flat_prices_do_nothing():
    prices = np.full(96, 30.0)
    d = optimise(BAT, prices, DT, soc0=0)
    assert d.charge_mw.sum() == pytest.approx(0.0, abs=1e-6)
    assert d.discharge_mw.sum() == pytest.approx(0.0, abs=1e-6)


def test_soc_stays_in_window():
    rng = np.random.default_rng(1)
    for _ in range(10):
        prices = rng.normal(30, 40, 96)
        d = optimise(BAT, prices, DT, soc0=100, mode_binaries=True)
        assert d.soc_mwh.min() >= BAT.soc_min - 1e-6
        assert d.soc_mwh.max() <= BAT.soc_max + 1e-6
        assert d.charge_mw.max() <= BAT.p_chg + 1e-6
        assert d.discharge_mw.max() <= BAT.p_dis + 1e-6


def test_milp_never_charges_and_discharges_at_once():
    rng = np.random.default_rng(2)
    for _ in range(20):
        prices = rng.normal(30, 40, 96)
        prices[rng.random(96) < 0.15] *= -1                      # ERCOT-style negatives
        d = optimise(BAT, prices, DT, soc0=100, mode_binaries=True)
        assert np.max(np.minimum(d.charge_mw, d.discharge_mw)) < 1e-6


def test_lp_exploits_negative_prices():
    """The claim 'an LP never charges and discharges at once because efficiency
    makes it wasteful' is TRUE for non-negative prices and FALSE otherwise.
    With a full battery and a negative price, the LP burns energy through the
    round-trip loss to make room for more paid charging. An inverter can't do
    that, which is why the benchmark uses the MILP."""
    rng = np.random.default_rng(0)
    exploited = False
    for _ in range(30):
        prices = rng.normal(30, 40, 96)
        prices[rng.random(96) < 0.15] *= -1
        d = optimise(BAT, prices, DT, soc0=100, mode_binaries=False)
        if np.max(np.minimum(d.charge_mw, d.discharge_mw)) > 1.0:
            exploited = True
            break
    assert exploited, "expected the LP relaxation to exploit negative prices on at least one day"


def test_lp_is_exact_when_prices_are_non_negative():
    rng = np.random.default_rng(3)
    for _ in range(10):
        prices = np.abs(rng.normal(30, 40, 96))
        lp = optimise(BAT, prices, DT, soc0=100, mode_binaries=False)
        milp = optimise(BAT, prices, DT, soc0=100, mode_binaries=True)
        assert lp.objective == pytest.approx(milp.objective, abs=0.05)


def test_cycle_cap_binds():
    prices = np.array([10.0, 100.0] * 48)                         # arbitrage every half hour
    unlimited = optimise(BAT, prices, DT, soc0=0)
    capped = optimise(Battery("C", 100, 100, 0, 200, cycles_max=1.0), prices, DT, soc0=0)
    assert unlimited.discharge_mw.sum() * DT > capped.discharge_mw.sum() * DT
    assert capped.discharge_mw.sum() * DT <= 200 + 1e-6


def test_degradation_cost_reduces_throughput():
    rng = np.random.default_rng(4)
    prices = rng.normal(30, 15, 96)
    free = optimise(BAT, prices, DT, soc0=100)
    costly = optimise(Battery("D", 100, 100, 0, 200, c_deg=20.0), prices, DT, soc0=100)
    assert costly.discharge_mw.sum() <= free.discharge_mw.sum() + 1e-6


def test_optimiser_reuses_model_across_days():
    opt = Optimiser(BAT, DT)
    a = opt.run(np.array([10.0] * 48 + [100.0] * 48), soc0=0)
    b = opt.run(np.array([100.0] * 48 + [10.0] * 48), soc0=200)
    assert len(opt._models) == 1                                  # one model, two solves
    assert a.discharge_mw[:48].sum() == pytest.approx(0.0, abs=1e-6)   # day A: no early discharge
    assert b.discharge_mw[:48].sum() > 0                          # day B: discharge early


def test_simulate_respects_physics():
    want = np.full(96, -1000.0)                                   # ask for the impossible
    d = simulate(BAT, want, DT, soc0=0)
    assert d.charge_mw.max() <= BAT.p_chg + 1e-9
    assert d.soc_mwh.max() <= BAT.soc_max + 1e-9


def test_fixed_schedule_charges_then_discharges():
    hours = np.repeat(np.arange(24), 4)
    d = fixed_schedule(BAT, hours, DT, soc0=0)
    assert d.charge_mw[(hours >= 10) & (hours <= 14)].sum() > 0
    assert d.discharge_mw[(hours >= 18) & (hours <= 20)].sum() > 0
    assert d.discharge_mw[hours < 18].sum() == 0
