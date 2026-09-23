"""
anatomy.py — the capture-gap anatomy: why did each battery fall short?

Takes the benchmark's unit-day table and decomposes the distance from the
perfect-foresight ceiling to what the unit actually earned into named,
additive pieces:

    ceiling              perfect foresight, all unit-days
    - commissioning      the whole gap on unit-days the unit was not fully ON
                         (on_share < 0.95: ONTEST / OUT / no telemetry)
    - declared window    ON days: ceiling minus the ceiling re-solved inside the
                         SOC window the operator declared that day
    - reserves, net      ON days: energy revenue foregone by holding the unit's
                         actual reserve awards, minus the AS revenue those
                         awards earned (can be negative = reserves paid off)
    - dispatch residual  ON days: what is left — decision quality
    = actual             energy + AS, all unit-days

Each piece is reported fleet-wide and per unit, in $/kW-yr on one common
denominator (so the bars add) and as a share of the ceiling.

Two things are reported alongside but NOT subtracted:
    price-setting        share of ceiling revenue on intervals where the unit's
                         own offer set the LMP — the price-taker ceiling is not
                         credible there (from price_setting.py)
    slack                MWh of reserve-energy slack the constrained re-solve
                         needed; non-zero means the real awards were not quite
                         feasible at 15-min resolution

And the residual is split by the fleet's 20 biggest perfect-foresight days
versus the other days.

    python -m optimization.anatomy --tag fleet
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "optimization" / "results"
ON_THRESHOLD = 0.95
TOP_DAYS = 20


def md(df, floatfmt="{:,.1f}"):
    cols = list(df.columns)
    out = ["| " + " | ".join([df.index.name or ""] + cols) + " |", "|" + "---|" * (len(cols) + 1)]
    for idx, row in df.iterrows():
        cells = [str(idx)] + [floatfmt.format(v) if isinstance(v, (int, float, np.floating)) and not pd.isna(v)
                              else ("" if pd.isna(v) else str(v)) for v in row]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def wide(ud: pd.DataFrame) -> pd.DataFrame:
    """One row per unit-day, one column per strategy revenue, plus tags."""
    w = ud.pivot_table(index=["unit", "day"], columns="strategy", values="energy_rev", aggfunc="sum")
    if "actual_as_only" not in w:
        w["actual_as_only"] = 0.0
    w["actual_total"] = w["actual"] + w["actual_as_only"]
    tags = ud.drop_duplicates(["unit", "day"]).set_index(["unit", "day"])[
        ["node", "county", "owner", "p_dis", "capacity", "on_share", "wmin", "wmax", "slack_mwh",
         "up_mean_mw", "dn_mean_mw"]]
    return w.join(tags)


def components(w: pd.DataFrame) -> pd.DataFrame:
    """Per unit-day, the additive pieces of ceiling - actual_total."""
    on = w.on_share >= ON_THRESHOLD
    c = pd.DataFrame(index=w.index)
    c["ceiling"] = w.perfect_foresight
    c["commissioning"] = np.where(on, 0.0, w.perfect_foresight - w.actual_total)
    c["window"] = np.where(on, w.perfect_foresight - w.pf_window, 0.0)
    c["reserves_energy"] = np.where(on, w.pf_window - w.pf_window_awards, 0.0)
    c["as_revenue"] = np.where(on, w.actual_as_only, 0.0)
    c["reserves_net"] = c.reserves_energy - c.as_revenue
    c["residual"] = np.where(on, w.pf_window_awards - w.actual, 0.0)
    c["actual_total"] = w.actual_total
    c["on"] = on
    # identity: ceiling - commissioning - window - reserves_net - residual == actual_total
    c["check"] = c.ceiling - c.commissioning - c.window - c.reserves_net - c.residual - c.actual_total
    return c.join(w[["p_dis", "capacity", "slack_mwh", "county", "owner"]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="full")
    a = ap.parse_args()
    ud = pd.read_parquet(RES / f"unit_day_{a.tag}.parquet")
    ps_path = RES / f"price_setting_{a.tag}.parquet"
    ps = pd.read_parquet(ps_path) if ps_path.exists() else None

    w = wide(ud)
    c = components(w)
    assert c.check.abs().max() < 1e-6, "waterfall identity broken"
    lines = []
    say = lambda s="": (print(s), lines.append(s))

    # ---- denominators: one for the whole fleet so bars add ---------------------
    unit_days = c.groupby(level="unit").size()
    kw = c.groupby(level="unit").p_dis.first() * 1000
    denom = float((unit_days * kw).sum()) / 365.0          # kW-years of exposure
    per_kwyr = lambda s: s.sum() / denom
    BARS = ["ceiling", "commissioning", "window", "reserves_net", "residual", "actual_total"]
    LABEL = {"ceiling": "Perfect-foresight ceiling", "commissioning": "− commissioning / not-ON unit-days",
             "window": "− declared SOC window", "reserves_net": "− reserves held, net of AS revenue",
             "residual": "− dispatch residual", "actual_total": "= Actual (energy + AS)"}

    # ---- 1. headline waterfall -------------------------------------------------
    say("# Capture-gap anatomy\n")
    say(f"*{c.index.get_level_values('unit').nunique()} units · "
        f"{c.index.get_level_values('day').min().date()} → {c.index.get_level_values('day').max().date()} · "
        f"{len(c):,} unit-days, {int(c.on.sum()):,} fully ON (on_share ≥ {ON_THRESHOLD})*\n")
    say("## 1. Fleet waterfall\n")
    fleet = pd.DataFrame({
        "$M": [c[b].sum() / 1e6 for b in BARS],
        "$/kW-yr": [per_kwyr(c[b]) for b in BARS],
        "% of ceiling": [100 * c[b].sum() / c.ceiling.sum() for b in BARS],
    }, index=[LABEL[b] for b in BARS]); fleet.index.name = "Step"
    say(md(fleet))
    cap_all = 100 * c.actual_total.sum() / c.ceiling.sum()
    on = c[c.on]
    cap_on = 100 * on.actual_total.sum() / on.ceiling.sum()
    say(f"\nCapture, all unit-days: **{cap_all:.1f}%**. Capture, fully-ON unit-days only: **{cap_on:.1f}%**. "
        f"The first bar of the waterfall is the difference.")
    say(f"\nOn fully-ON unit-days the remaining gap of {100-cap_on:.1f} points splits into: "
        f"declared window **{100*on.window.sum()/on.ceiling.sum():.1f}**, "
        f"reserves net **{100*on.reserves_net.sum()/on.ceiling.sum():.1f}** "
        f"(energy foregone {100*on.reserves_energy.sum()/on.ceiling.sum():.1f} minus AS earned "
        f"{100*on.as_revenue.sum()/on.ceiling.sum():.1f}), "
        f"dispatch residual **{100*on.residual.sum()/on.ceiling.sum():.1f}** points of the ON-day ceiling.")
    say(f"\nReserve-energy slack used by the constrained re-solve: {c.slack_mwh.sum():,.0f} MWh total "
        f"({100*(c.slack_mwh>0).mean():.1f}% of unit-days non-zero); AS revenue is priced at real-time MCPC only.")

    # ---- 2. hygiene ----------------------------------------------------------------
    say("\n## 2. Hygiene: what the status filter does\n")
    per_unit_on = c.groupby(level="unit").on.mean()
    hyg = pd.DataFrame({
        "unit-days": [len(c), int(c.on.sum())],
        "units": [c.index.get_level_values("unit").nunique(), int((per_unit_on > 0).sum())],
        "capture (fleet)": [cap_all, cap_on],
        "ceiling $/kW-yr": [c.ceiling.sum() / denom, on.ceiling.sum() / (float((on.groupby(level='unit').size() * kw.reindex(on.index.get_level_values('unit').unique())).sum()) / 365)],
    }, index=["all unit-days", f"on_share ≥ {ON_THRESHOLD}"]); hyg.index.name = "Set"
    say(md(hyg))
    low = per_unit_on[per_unit_on < 0.5].sort_values()
    if len(low):
        say(f"\nUnits fully ON on fewer than half their days ({len(low)}): " +
            ", ".join(f"{u} ({100*v:.0f}%)" for u, v in low.items()))

    # ---- 3. per-unit table -----------------------------------------------------------
    say("\n## 3. Per unit (fully-ON days; components as % of that unit's ON-day ceiling)\n")
    g = on.groupby(level="unit")
    pu = pd.DataFrame({
        "MW": g.p_dis.first(),
        "h": (g.capacity.first() / g.p_dis.first()).round(1),
        "ON days": g.size(),
        "all days": unit_days,
        "capture all %": 100 * c.groupby(level="unit").actual_total.sum() / c.groupby(level="unit").ceiling.sum(),
        "capture ON %": 100 * g.actual_total.sum() / g.ceiling.sum(),
        "window %": 100 * g.window.sum() / g.ceiling.sum(),
        "reserves net %": 100 * g.reserves_net.sum() / g.ceiling.sum(),
        "residual %": 100 * g.residual.sum() / g.ceiling.sum(),
        "slack MWh": g.slack_mwh.sum(),
    })
    if ps is not None:
        pg = ps.groupby("unit")
        pu["price-setting % of |PF$|"] = 100 * pg.pf_rev_abs_flagged.sum() / pg.pf_rev_abs.sum()
        pu["price-setting % intervals"] = 100 * pg.flagged.sum() / pg.intervals.sum()
    pu = pu.sort_values("capture ON %", ascending=False); pu.index.name = "Unit"
    say(md(pu.round(1)))
    pu.to_csv(RES / f"anatomy_units_{a.tag}.csv")

    # ---- 4. price-setting -----------------------------------------------------------
    say("\n## 4. Where the ceiling is not credible: price-setting intervals\n")
    if ps is not None:
        fleet_ps = 100 * ps.pf_rev_abs_flagged.sum() / ps.pf_rev_abs.sum()
        fleet_iv = 100 * ps.flagged.sum() / ps.intervals.sum()
        say(f"Fleet: **{fleet_ps:.1f}%** of |perfect-foresight revenue| was earned on 15-min intervals "
            f"containing at least one SCED run where the unit's own offer was within $1 of the LMP "
            f"({fleet_iv:.1f}% of intervals). On those intervals a different dispatch would have "
            f"moved the price, so the price-taker ceiling overstates what was available. This is "
            f"flagged, not subtracted.")
        hi = pu[pu["price-setting % of |PF$|"] > 50].index.tolist()
        if hi:
            say(f"\nUnits above 50%: {', '.join(hi)}.")
    else:
        say("price_setting.py has not been run for this tag.")

    # ---- 5. residual split: big days vs the rest ---------------------------------------
    say(f"\n## 5. Dispatch residual: the {TOP_DAYS} biggest days vs the rest\n")
    by_day = on.groupby(level="day").ceiling.sum().sort_values(ascending=False)
    top = set(by_day.index[:TOP_DAYS])
    on_top = on[on.index.get_level_values("day").isin(top)]
    on_rest = on[~on.index.get_level_values("day").isin(top)]
    split = pd.DataFrame({
        "unit-days": [len(on_top), len(on_rest)],
        "ceiling $M": [on_top.ceiling.sum() / 1e6, on_rest.ceiling.sum() / 1e6],
        "ceiling share %": [100 * on_top.ceiling.sum() / on.ceiling.sum(), 100 * on_rest.ceiling.sum() / on.ceiling.sum()],
        "residual $M": [on_top.residual.sum() / 1e6, on_rest.residual.sum() / 1e6],
        "residual share %": [100 * on_top.residual.sum() / on.residual.sum(), 100 * on_rest.residual.sum() / on.residual.sum()],
        "capture %": [100 * on_top.actual_total.sum() / on_top.ceiling.sum(), 100 * on_rest.actual_total.sum() / on_rest.ceiling.sum()],
    }, index=[f"top {TOP_DAYS} days", "other days"]); split.index.name = "Days"
    say(md(split))
    say("\nTop days: " + ", ".join(d.strftime("%Y-%m-%d") for d in sorted(top)))

    (RES / f"anatomy_{a.tag}.md").write_text("\n".join(lines) + "\n")
    print(f"\n-> {RES / f'anatomy_{a.tag}.md'}")

    # ---- figures ---------------------------------------------------------------------
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    vals = fleet["$/kW-yr"].to_numpy()
    fig, ax = plt.subplots(figsize=(9, 4.6))
    running = vals[0]; x = 0
    ax.bar(x, vals[0], color="#2ca02c"); ax.text(x, vals[0] + 0.8, f"${vals[0]:.1f}", ha="center")
    for i, b in enumerate(BARS[1:-1], start=1):
        v = vals[i]
        bottom = running - v if v >= 0 else running
        ax.bar(i, abs(v), bottom=bottom, color="#e45756" if v >= 0 else "#4c78a8")
        ax.text(i, running + 0.8, f"−${v:.1f}" if v >= 0 else f"+${-v:.1f}", ha="center")
        running -= v
    ax.bar(len(BARS) - 1, vals[-1], color="#c0392b")
    ax.text(len(BARS) - 1, vals[-1] + 0.8, f"${vals[-1]:.1f}", ha="center")
    ax.set_xticks(range(len(BARS)))
    ax.set_xticklabels(["Ceiling", "Commissioning", "Declared\nwindow", "Reserves\n(net of AS)", "Dispatch\nresidual", "Actual"])
    ax.set_ylabel("$/kW-year, fleet, one common denominator")
    ax.set_title(f"Where the gap went: {c.index.get_level_values('unit').nunique()} ERCOT batteries, "
                 f"capture {cap_all:.0f}% → {cap_on:.0f}% after hygiene")
    ax.set_ylim(0, vals[0] * 1.15)
    fig.tight_layout(); fig.savefig(RES / f"fig_waterfall_{a.tag}.png", dpi=160); plt.close(fig)

    # per-unit stacked composition (ON days), sorted by capture
    comp = pu[["capture ON %", "window %", "reserves net %", "residual %"]].sort_values("capture ON %")
    fig, ax = plt.subplots(figsize=(9, max(4, 0.22 * len(comp) + 1)))
    left = np.zeros(len(comp))
    for col, color, label in [("capture ON %", "#c0392b", "captured"), ("residual %", "#e45756", "dispatch residual"),
                              ("reserves net %", "#4c78a8", "reserves, net"), ("window %", "#9e9e9e", "declared window")]:
        v = comp[col].clip(lower=0).to_numpy()
        ax.barh(comp.index, v, left=left, color=color, label=label); left += v
    ax.set_xlabel("% of the unit's perfect-foresight ceiling (fully-ON days)")
    ax.set_xlim(0, 105); ax.legend(frameon=False, loc="lower right", fontsize=8)
    ax.set_title("Per-unit anatomy")
    fig.tight_layout(); fig.savefig(RES / f"fig_anatomy_units_{a.tag}.png", dpi=160); plt.close(fig)
    print(f"figures -> fig_waterfall_{a.tag}.png, fig_anatomy_units_{a.tag}.png")


if __name__ == "__main__":
    main()
