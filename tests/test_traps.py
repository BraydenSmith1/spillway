"""
Regression tests for the data-quality traps found during the project.

Each one produced a plausible-looking wrong answer before it was caught. The
tests build tiny synthetic Parquet files so they run without the 9 GB dataset.
See "Joining these together — the traps" in DATA_DICTIONARY.md for each one.
"""

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from analysis.interval_hours import interval_hours_sql


@pytest.fixture
def sced_files(tmp_path):
    """Two synthetic SCED days: one at 15-min cadence (pre-RTC), one at 5-min."""
    def day(date, minutes, hsl, bp):
        ts = pd.date_range(f"{date} 00:00", f"{date} 23:59", freq=f"{minutes}min", tz="US/Central")
        return pd.DataFrame({"SCED Timestamp": ts, "Resource Name": "FARM_1",
                             "Resource Type": "PVGR", "Telemetered Resource Status": "ON",
                             "HSL": hsl, "Base Point": bp})
    pre = day("2025-11-15", 15, 100.0, 50.0)     # 96 rows, half curtailed
    post = day("2026-03-15", 5, 100.0, 50.0)     # 288 rows, half curtailed
    pre.to_parquet(tmp_path / "gen_resource_2025-11-15.parquet")
    post.to_parquet(tmp_path / "gen_resource_2026-03-15.parquet")
    return str(tmp_path / "gen_resource_*.parquet")


def test_interval_hours_is_derived_not_hardcoded(sced_files):
    """Trap 7: SCED ran every 15 minutes before RTC+B and every 5 after.
    Dividing by 12 everywhere understated pre-RTC energy threefold."""
    con = duckdb.connect()
    con.sql("SET TimeZone = 'America/Chicago'")
    hrs = con.sql(f"WITH {interval_hours_sql(sced_files)} SELECT * FROM interval_hours ORDER BY day").df()
    assert hrs.hrs.tolist() == pytest.approx([0.25, 5 / 60], rel=1e-6)


def test_energy_is_the_same_regardless_of_cadence(sced_files):
    """Same physical day (100 MW available, 50 MW dispatched, all day) must
    yield the same MWh whether SCED sampled it 96 or 288 times."""
    con = duckdb.connect()
    con.sql("SET TimeZone = 'America/Chicago'")
    mwh = con.sql(f"""
        WITH {interval_hours_sql(sced_files)},
        daily AS (SELECT "SCED Timestamp"::DATE AS day, SUM(HSL - "Base Point") AS curt_mw
                  FROM read_parquet('{sced_files}') GROUP BY 1)
        SELECT day, curt_mw * hrs AS curt_mwh FROM daily JOIN interval_hours USING (day) ORDER BY day
    """).df()
    assert mwh.curt_mwh.tolist() == pytest.approx([1200.0, 1200.0], rel=1e-6)   # 50 MW x 24 h


def test_curtailment_tolerance_lives_in_the_numerator():
    """Trap 2: filtering to curtailed rows BEFORE computing the percentage
    left only curtailed intervals in the denominator and reported ~96%
    curtailment for every farm."""
    df = pd.DataFrame({"HSL": [100.0] * 10, "Base Point": [100.0] * 5 + [50.0] * 5})
    curt = np.where(df.HSL > df["Base Point"] + 1, df.HSL - df["Base Point"], 0)
    right = 100 * curt.sum() / df.HSL.sum()                          # 25%
    wrong = 100 * curt[curt > 0].sum() / df.HSL[curt > 0].sum()      # 50%
    assert right == pytest.approx(25.0)
    assert wrong == pytest.approx(50.0)
    assert right != wrong


def test_duckdb_session_is_pinned_to_central():
    """Trap 1: DuckDB defaults to the machine's zone. SCED stamps are Central.
    Every analysis module must pin the session."""
    from optimization import data as D
    assert D.con.sql("SELECT current_setting('TimeZone')").fetchone()[0] == "America/Chicago"


def test_dam_hour_ending_is_a_string():
    """Day-ahead prices carry hourEnding as '01:00'..'24:00'; real-time carries
    an integer deliveryHour. Joining them naively is a silent zero-row join."""
    s = pd.Series(["01:00", "13:00", "24:00"])
    hours = s.str.split(":").str[0].astype(int)
    assert hours.tolist() == [1, 13, 24]


def test_battery_base_point_sign_convention():
    """Storage Base Point: negative = charging, positive = discharging.
    Verified against telemetered output on real data (mean -11 MW when
    negative, +12 MW when positive)."""
    from optimization.model import Dispatch
    d = Dispatch(charge_mw=np.array([10.0, 0.0]), discharge_mw=np.array([0.0, 20.0]),
                 soc_mwh=np.zeros(2), objective=0.0, solve_status="test")
    assert d.net_mw.tolist() == [-10.0, 20.0]


def test_repo_has_no_hardcoded_home_paths():
    """The explore scripts once carried absolute /Users/... paths; the repo must
    run on any machine."""
    root = Path(__file__).resolve().parent.parent
    needle = "/Users/" + "braydensmith"          # built at runtime so this file doesn't match itself
    offenders = [p for p in root.rglob("*.py")
                 if ".venv" not in p.parts and p != Path(__file__) and needle in p.read_text()]
    assert offenders == []


def test_lambda_classification_signs():
    """§3: LMP = System Lambda + congestion. lambda <= 0 is system-wide
    oversupply regardless of the node; lambda > 0 with a negative own-node
    LMP is congestion; a positive LMP under positive lambda is 'other'.
    Mirrors the CASE in analysis/curtailment_lambda_split.py."""
    con = duckdb.connect()
    rows = con.sql("""
        SELECT lmp, lam,
               CASE WHEN lam <= 0 THEN 'oversupply'
                    WHEN lmp < 0  THEN 'congestion'
                    ELSE 'other' END AS cause,
               lmp - lam AS congestion_component
        FROM (VALUES (-30.0, -5.0), (-30.0, 20.0), (10.0, 20.0), (-0.01, 0.0), (5.0, 0.0))
             t(lmp, lam)
        ORDER BY lmp, lam
    """).df()
    got = dict(zip(zip(rows.lmp, rows.lam), rows.cause))
    assert got[(-30.0, -5.0)] == "oversupply"        # grid itself negative
    assert got[(-30.0, 20.0)] == "congestion"        # grid wanted power, node did not
    assert got[(10.0, 20.0)] == "other"              # curtailed at a positive price
    assert got[(-0.01, 0.0)] == "oversupply"         # lambda exactly 0 counts as oversupply
    assert got[(5.0, 0.0)] == "oversupply"
    comp = rows.set_index(["lmp", "lam"]).congestion_component
    assert comp[(-30.0, 20.0)] == pytest.approx(-50.0)   # the price of the wire
