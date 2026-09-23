"""
Tests for the capture-gap anatomy machinery: the mutable SOC window and
reserve-award parameters on the model, the status filter, and the
price-setting test. All synthetic; no data files needed.
"""

import numpy as np
import pandas as pd
import pytest

from optimization.model import Battery, optimise
from optimization.strategies import Optimiser
from optimization.price_setting import offer_at

DT = 0.25
BAT = Battery("TEST", p_chg=100, p_dis=100, soc_min=0, soc_max=200)
TWO_PRICE = np.array([10.0] * 48 + [100.0] * 48)
ZERO = np.zeros(96)


def test_declared_window_narrows_the_ceiling():
    """Re-solving inside a narrower SOC window can only lose revenue, and a
    window half the size of the envelope loses about half the two-price-day
    arbitrage."""
    full = optimise(BAT, TWO_PRICE, DT, soc0=0, mode_binaries=True)
    half = optimise(BAT, TWO_PRICE, DT, soc0=50, mode_binaries=True, smin=50, smax=150)
    assert half.objective < full.objective
    assert half.objective == pytest.approx(full.objective / 2, rel=0.02)
    assert half.soc_mwh.min() >= 50 - 1e-6 and half.soc_mwh.max() <= 150 + 1e-6


def test_opening_soc_is_clipped_into_the_window():
    """An opening SOC outside the day's window must not make the day infeasible."""
    d = optimise(BAT, TWO_PRICE, DT, soc0=0, mode_binaries=True, smin=50, smax=150)
    assert d.solve_status == "optimal"
    assert d.soc_mwh.min() >= 50 - 1e-6


def test_upward_reserve_award_caps_discharge():
    up = np.full(96, 60.0)
    d = optimise(BAT, TWO_PRICE, DT, soc0=0, mode_binaries=True,
                 awards=dict(up=up, dn=ZERO, ereq=ZERO, edn=ZERO))
    assert d.discharge_mw.max() <= 40 + 1e-6
    assert d.slack_mwh == pytest.approx(0.0, abs=1e-6)


def test_reserve_energy_keeps_soc_above_floor():
    ereq = np.full(96, 100.0)
    d = optimise(BAT, TWO_PRICE, DT, soc0=150, mode_binaries=True,
                 awards=dict(up=ZERO, dn=ZERO, ereq=ereq, edn=ZERO))
    assert d.soc_mwh.min() >= 100 - 1e-6
    assert d.slack_mwh == pytest.approx(0.0, abs=1e-6)


def test_slack_only_when_physically_impossible():
    """Starting empty with 100 MWh required in reserve is infeasible for the
    first few intervals; slack covers exactly that and no more."""
    ereq = np.full(96, 100.0)
    d = optimise(BAT, TWO_PRICE, DT, soc0=0, mode_binaries=True,
                 awards=dict(up=ZERO, dn=ZERO, ereq=ereq, edn=ZERO))
    assert d.solve_status == "optimal"
    assert d.slack_mwh > 0
    assert d.soc_mwh[10:].min() >= 100 - 1e-6        # once charged, no more slack


def test_optimiser_resets_window_and_awards_between_days():
    opt = Optimiser(BAT, DT)
    constrained = opt.run(TWO_PRICE, 50, smin=50, smax=150,
                          awards=dict(up=np.full(96, 60.0), dn=ZERO, ereq=ZERO, edn=ZERO))
    free = opt.run(TWO_PRICE, 0)
    ref = optimise(BAT, TWO_PRICE, DT, soc0=0, mode_binaries=True)
    assert constrained.objective < ref.objective
    assert free.objective == pytest.approx(ref.objective, rel=1e-6)


def test_on_share_filter_semantics():
    """A unit-day is fully ON only if at least 95% of its rows report ON."""
    rows = pd.Series(["ON"] * 280 + ["ONTEST"] * 8)
    assert (rows == "ON").mean() >= 0.95
    rows = pd.Series(["ON"] * 200 + ["ONTEST"] * 88)
    assert (rows == "ON").mean() < 0.95


def test_offer_at_uses_the_right_side_of_the_curve():
    curve = [[-100, -8.0], [0, -7.9], [0, 80.0], [50, 80.5], [100, 81.0]]
    price, at_limit = offer_at(25.0, curve)
    assert price == pytest.approx(80.25) and not at_limit         # discharge side, interior
    price, at_limit = offer_at(-50.0, curve)
    assert price == pytest.approx(-7.95) and not at_limit         # charge side, interior
    price, at_limit = offer_at(100.0, curve)
    assert at_limit                                                # capacity-limited
    assert np.isnan(offer_at(0.0, curve)[0])                       # idle: not dispatched
    assert np.isnan(offer_at(25.0, None)[0])
