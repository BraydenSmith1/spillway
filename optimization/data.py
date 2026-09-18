"""
data.py — everything the optimiser and benchmark need, loaded from data/raw.

All timestamps are naive Central, at 15-minute settlement resolution, because
that is the resolution ERCOT settles real-time energy at. SCED's 5-minute
storage telemetry is averaged up to 15 minutes to match.

    battery_params()        physical limits per storage unit, from ESR telemetry
    rt_prices(node, ...)    real-time settlement point prices, 15-min
    dam_prices(node, ...)   day-ahead prices, hourly, repeated to 15-min
    actual_dispatch(unit)   what the battery really did (Base Point), 15-min
    as_prices(...)          ancillary-service clearing prices, if downloaded
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import duckdb
import pandas as pd

from optimization.model import Battery

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DT = 0.25  # hours per settlement interval

con = duckdb.connect()
con.sql("SET TimeZone = 'America/Chicago'")   # ERCOT's clock, not the Mac's


STORAGE_WORDS = ("ESS", "_ES_", "BESS", "STOR", "BATT", "ESR")


def _esr_nodes(units) -> pd.Series:
    """Map storage unit names to settlement points by name stem.

    Storage units were renamed when they moved to the ESR disclosure at RTC+B
    ("FERD_ESS_BES1" -> "FERD_ESS_ESR1"), so the crosswalk built from the
    generator file doesn't match them directly. The site stem does. Where a
    site has both a solar node and a storage node, prefer the storage one.
    """
    sp = con.sql(f"""
        SELECT DISTINCT settlementPoint AS sp
        FROM read_parquet('{RAW}/settlement_point_prices/settlement_point_prices_2026-0[4-9].parquet')
        WHERE settlementPointType IN ('RN', 'PCCRN', 'LCCRN', 'PUN')
    """).df().sp
    by_stem = {}
    for node in sp:
        by_stem.setdefault(node.split("_")[0], []).append(node)

    def rank(node):
        return (0 if any(w in node for w in STORAGE_WORDS) else 1,
                0 if node.endswith("_RN") else 1, len(node))

    out = {}
    for u in units:
        cands = by_stem.get(u.split("_")[0], [])
        out[u] = sorted(cands, key=rank)[0] if cands else None
    return pd.Series(out, name="node")


def battery_params(month_glob: str = "esr_*.parquet", min_power_mw: float = 20.0,
                   min_active_days: int = 120) -> pd.DataFrame:
    """One row per storage unit with a settlement-point link.

    Limits come from telemetry rather than a registry: HSL is the observed
    maximum discharge, LSL (negative) the maximum charge, Max SOC the usable
    energy. Taking the extremes over a few months gives the nameplate-ish
    envelope without one bad reading dominating.
    """
    df = con.sql(f"""
        SELECT "Resource Name"          AS unit,
               ROUND(MAX(HSL), 1)       AS p_dis,
               ROUND(-MIN(LSL), 1)      AS p_chg,
               ROUND(MAX("Max SOC"), 1) AS soc_max,
               ROUND(MIN("Min SOC"), 1) AS soc_min,
               -- days the unit actually moved energy; screens out units still commissioning
               COUNT(DISTINCT CASE WHEN ABS("Base Point") > 1 THEN "SCED Timestamp"::DATE END) AS active_days,
               COUNT(DISTINCT "SCED Timestamp"::DATE) AS days_seen
        FROM read_parquet('{RAW}/sced_esr/esr_*.parquet')
        GROUP BY 1
        HAVING MAX(HSL) >= {min_power_mw} AND MAX("Max SOC") > 0
    """).df()
    df = df[df.active_days >= min_active_days]
    df["node"] = df.unit.map(_esr_nodes(df.unit))
    df = df[df.node.notna()]

    # County / owner from the crosswalk, matched on site stem (any fuel).
    cw = pd.read_parquet(ROOT / "crosswalk/crosswalk.parquet")
    cw["stem"] = cw.resource.str.split("_").str[0]
    site = cw.dropna(subset=["county"]).drop_duplicates("stem").set_index("stem")[["county", "owner"]]
    df["stem"] = df.unit.str.split("_").str[0]
    df = df.join(site, on="stem").drop(columns="stem")
    return df.sort_values("soc_max", ascending=False).reset_index(drop=True)


def to_battery(row, **overrides) -> Battery:
    kw = dict(name=row.unit, p_chg=float(row.p_chg), p_dis=float(row.p_dis),
              soc_min=float(row.soc_min), soc_max=float(row.soc_max))
    kw.update(overrides)
    return Battery(**kw)


@lru_cache(maxsize=None)
def rt_prices(node: str, start: str, end: str) -> pd.Series:
    """Real-time price at a settlement point, 15-min, indexed by interval start."""
    s = con.sql(f"""
        SELECT CAST(deliveryDate AS DATE)
               + INTERVAL ((deliveryHour - 1) * 60 + (deliveryInterval - 1) * 15) MINUTE AS ts,
               settlementPointPrice AS price
        FROM read_parquet('{RAW}/settlement_point_prices/settlement_point_prices_202[56]-*.parquet')
        WHERE settlementPoint = '{node}' AND NOT DSTFlag
          AND deliveryDate >= '{start}' AND deliveryDate < '{end}'
        ORDER BY ts
    """).df().set_index("ts").price
    return s[~s.index.duplicated()]


@lru_cache(maxsize=None)
def dam_prices(node: str, start: str, end: str) -> pd.Series:
    """Day-ahead price at a settlement point, hourly, repeated to 15-min."""
    s = con.sql(f"""
        SELECT CAST(deliveryDate AS DATE)
               + INTERVAL ((CAST(SPLIT_PART(hourEnding, ':', 1) AS INT) - 1) * 60) MINUTE AS ts,
               settlementPointPrice AS price
        FROM read_parquet('{RAW}/dam_settlement_point_prices/*.parquet')
        WHERE settlementPoint = '{node}' AND NOT DSTFlag
          AND deliveryDate >= '{start}' AND deliveryDate < '{end}'
        ORDER BY ts
    """).df().set_index("ts").price
    s = s[~s.index.duplicated()]
    return s.resample("15min").ffill()


@lru_cache(maxsize=None)
def actual_dispatch(unit: str, start: str, end: str) -> pd.DataFrame:
    """What the battery actually did: mean Base Point (MW, +discharge/-charge)
    and end-of-interval SOC, at 15-min."""
    return con.sql(f"""
        SELECT date_trunc('minute', ("SCED Timestamp" AT TIME ZONE 'America/Chicago'))
                 - INTERVAL (minute("SCED Timestamp" AT TIME ZONE 'America/Chicago') % 15) MINUTE AS ts,
               AVG("Base Point") AS net_mw,
               LAST(SOC ORDER BY "SCED Timestamp") AS soc_mwh
        FROM read_parquet('{RAW}/sced_esr/esr_*.parquet')
        WHERE "Resource Name" = '{unit}'
          AND "SCED Timestamp" >= TIMESTAMPTZ '{start} 00:00:00 America/Chicago'
          AND "SCED Timestamp" <  TIMESTAMPTZ '{end} 00:00:00 America/Chicago'
        GROUP BY 1 ORDER BY 1
    """).df().set_index("ts")


def as_awards(unit: str, start: str, end: str) -> pd.DataFrame:
    """Ancillary-service MW awarded to the unit, 15-min mean, per product."""
    return con.sql(f"""
        SELECT date_trunc('minute', ("SCED Timestamp" AT TIME ZONE 'America/Chicago'))
                 - INTERVAL (minute("SCED Timestamp" AT TIME ZONE 'America/Chicago') % 15) MINUTE AS ts,
               AVG(COALESCE("AS Awards RegUp", 0))   AS regup,
               AVG(COALESCE("AS Awards RegDown", 0)) AS regdn,
               AVG(COALESCE("AS Awards RRSPFR", 0) + COALESCE("AS Awards RRSFFR", 0)
                   + COALESCE("AS Awards RRSUFR", 0)) AS rrs,
               AVG(COALESCE("AS Awards ECRS", 0))    AS ecrs,
               AVG(COALESCE("AS Awards NonSpin", 0)) AS nonspin
        FROM read_parquet('{RAW}/sced_esr/esr_*.parquet')
        WHERE "Resource Name" = '{unit}'
          AND "SCED Timestamp" >= TIMESTAMPTZ '{start} 00:00:00 America/Chicago'
          AND "SCED Timestamp" <  TIMESTAMPTZ '{end} 00:00:00 America/Chicago'
        GROUP BY 1 ORDER BY 1
    """).df().set_index("ts")


def as_prices_available() -> bool:
    return any((RAW / "rt_as_prices").glob("*.parquet"))


def _norm(product: str) -> str:
    """ERCOT's product labels vary in case and spelling; map to our keys."""
    p = str(product).upper().replace(" ", "").replace("-", "")
    if p.startswith("REGUP"): return "regup"
    if p.startswith("REGD"):  return "regdn"
    if p.startswith("RRS"):   return "rrs"
    if p.startswith("ECRS"):  return "ecrs"
    if p.startswith("NSPIN") or p.startswith("NONSPIN"): return "nonspin"
    return p.lower()


@lru_cache(maxsize=None)
def rt_as_prices(start: str, end: str) -> pd.DataFrame:
    """Real-time AS clearing prices ($/MW per hour), 15-min, one column per
    product. The file is long-format (one row per product per interval)."""
    df = con.sql(f"""
        SELECT CAST(deliveryDate AS DATE)
               + INTERVAL ((deliveryHour - 1) * 60 + (deliveryInt - 1) * 15) MINUTE AS ts,
               ASType AS product, MCPC AS price
        FROM read_parquet('{RAW}/rt_as_prices/*.parquet')
        WHERE deliveryDate >= '{start}' AND deliveryDate < '{end}' AND NOT repeatHourFlag
    """).df()
    df["product"] = df["product"].map(_norm)
    wide = df.pivot_table(index="ts", columns="product", values="price", aggfunc="sum").sort_index()
    return wide.fillna(0.0)


@lru_cache(maxsize=None)
def dam_as_prices(start: str, end: str) -> pd.DataFrame:
    """Day-ahead AS clearing prices (MCPC, $/MW per hour), hourly repeated to 15-min."""
    df = con.sql(f"""
        SELECT CAST(deliveryDate AS DATE)
               + INTERVAL ((CAST(SPLIT_PART(hourEnding, ':', 1) AS INT) - 1) * 60) MINUTE AS ts,
               ancillaryType AS product, MCPC AS price
        FROM read_parquet('{RAW}/dam_as_prices/*.parquet')
        WHERE deliveryDate >= '{start}' AND deliveryDate < '{end}' AND NOT DSTFlag
    """).df()
    df["product"] = df["product"].map(_norm)
    wide = df.pivot_table(index="ts", columns="product", values="price", aggfunc="sum").sort_index()
    return wide.resample("15min").ffill().fillna(0.0)
