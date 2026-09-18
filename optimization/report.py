"""
report.py — turn benchmark output into the tables and figures in WRITEUP.md.

Reads optimization/results/summary_*.csv and unit_day_*.parquet, prints the
markdown tables, and saves figures next to them.

    python -m optimization.report
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "optimization" / "results"

LABEL = {"fixed_schedule": "Fixed schedule", "persistence": "Persistence",
         "dam_informed": "Day-ahead informed", "actual": "Actual (energy only)",
         "actual_as_only": "Actual (AS only)", "actual_total": "Actual (energy + AS)",
         "perfect_foresight": "Perfect foresight"}
ORDER = ["fixed_schedule", "persistence", "dam_informed", "actual", "actual_total", "perfect_foresight"]
COLOR = {"fixed_schedule": "#9e9e9e", "persistence": "#bdbdbd", "dam_informed": "#4c78a8",
         "actual": "#e45756", "actual_total": "#c0392b", "perfect_foresight": "#2ca02c"}


def summary(tag):
    p = RES / f"summary_{tag}.csv"
    return pd.read_csv(p, index_col=0) if p.exists() else None


def unit_day(tag="full"):
    return pd.read_parquet(RES / f"unit_day_{tag}.parquet")


def annualise(df):
    """$/kW-yr per (unit, strategy) from summed revenue."""
    days = df.groupby("unit").day.nunique()
    kw = df.groupby("unit").p_dis.first() * 1000
    rev = df.pivot_table(index="unit", columns="strategy", values="energy_rev", aggfunc="sum")
    if "actual_as_only" in rev:
        rev["actual_total"] = rev["actual"] + rev["actual_as_only"]
    return rev.div(days, axis=0).mul(365).div(kw, axis=0), rev, days, kw


def md(df, floatfmt="{:,.1f}"):
    """Minimal markdown table."""
    cols = list(df.columns)
    out = ["| " + " | ".join([df.index.name or ""] + cols) + " |", "|" + "---|" * (len(cols) + 1)]
    for idx, row in df.iterrows():
        cells = [str(idx)] + [floatfmt.format(v) if isinstance(v, (int, float, np.floating)) and not pd.isna(v)
                              else ("" if pd.isna(v) else str(v)) for v in row]
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def main(tag="full"):
    lines = []
    say = lambda s="": (print(s), lines.append(s))

    df = unit_day(tag)
    annual, rev, days, kw = annualise(df)
    pf_total = rev["perfect_foresight"].sum()

    # ---- headline ----------------------------------------------------------
    say("## Headline\n")
    head = pd.DataFrame({
        "$/kW-yr (median unit)": annual.median(),
        "$/kW-yr (fleet)": rev.sum() / (days * kw).sum() * 365,
        "Capture vs perfect (%)": 100 * rev.sum() / pf_total,
    }).reindex(ORDER).dropna(how="all")
    head.index = [LABEL[i] for i in head.index]; head.index.name = "Strategy"
    say(md(head))
    say(f"\nUnits: {df.unit.nunique()}   Days: {df.day.min().date()} → {df.day.max().date()}   "
        f"Unit-days: {len(df[df.strategy=='perfect_foresight']):,}")

    fleet = head["$/kW-yr (fleet)"]
    say(f"\n**Value of perfect foresight over day-ahead:** "
        f"${fleet['Perfect foresight'] - fleet['Day-ahead informed']:,.1f}/kW-yr "
        f"({100*(1 - fleet['Day-ahead informed']/fleet['Perfect foresight']):.0f}% of the ceiling).")
    if "Actual (energy + AS)" in fleet:
        say(f"**AS revenue as share of actual total:** "
            f"{100*(fleet['Actual (energy + AS)']-fleet['Actual (energy only)'])/fleet['Actual (energy + AS)']:.0f}%.")

    # ---- sensitivities -----------------------------------------------------
    say("\n## Sensitivities (perfect-foresight, fleet $/kW-yr)\n")
    base = summary(tag)
    rows = []
    for t, label in [(tag, "Base (MILP)"), ("lp", "LP relaxation"),
                     ("deg10", "$10/MWh degradation"), ("cyc15", "1.5 cycles/day cap")]:
        s = summary(t)
        if s is None or (t != tag and tag != "full"): continue
        v = s.loc["perfect_foresight", "$/kW-yr (fleet-weighted)"]
        b = base.loc["perfect_foresight", "$/kW-yr (fleet-weighted)"]
        rows.append({"Variant": label, "Perfect foresight $/kW-yr": v, "vs base": f"{100*(v/b-1):+.1f}%"})
    sens = pd.DataFrame(rows).set_index("Variant")
    say(md(sens))

    # ---- per-unit capture --------------------------------------------------
    say("\n## Per-unit capture rate (actual incl. AS ÷ perfect foresight)\n")
    meta = df.groupby("unit").agg(county=("county", "first"), p_dis=("p_dis", "first"),
                                  capacity=("capacity", "first"), days=("day", "nunique"))
    per = pd.DataFrame({
        "MW": meta.p_dis, "hours": (meta.capacity / meta.p_dis).round(1), "days": meta.days,
        "Perfect $/kW-yr": annual["perfect_foresight"],
        "Actual $/kW-yr": annual.get("actual_total", annual["actual"]),
        "Capture %": 100 * rev.get("actual_total", rev["actual"]) / rev["perfect_foresight"],
        "DA-informed capture %": 100 * rev["dam_informed"] / rev["perfect_foresight"],
    }).sort_values("Capture %", ascending=False)
    per.index.name = "Unit"
    say("Top 5:\n"); say(md(per.head(5)))
    say("\nBottom 5:\n"); say(md(per.tail(5)))
    say(f"\nCapture rate across units — median {per['Capture %'].median():.0f}%, "
        f"IQR {per['Capture %'].quantile(.25):.0f}–{per['Capture %'].quantile(.75):.0f}%, "
        f"range {per['Capture %'].min():.0f}–{per['Capture %'].max():.0f}%.")

    # ---- monthly -----------------------------------------------------------
    say("\n## By month (fleet $/kW-yr, annualised)\n")
    df["month"] = df.day.dt.to_period("M").astype(str)
    m = df.pivot_table(index="month", columns="strategy", values="energy_rev", aggfunc="sum")
    if "actual_as_only" in m: m["actual_total"] = m["actual"] + m["actual_as_only"]
    mdays = df.groupby("month").day.nunique()
    mkw = df.drop_duplicates(["month", "unit"]).groupby("month").p_dis.sum() * 1000
    monthly = m.div(mdays * mkw / 365, axis=0)
    monthly["capture %"] = 100 * m.get("actual_total", m["actual"]) / m["perfect_foresight"]
    show = monthly[[c for c in ["dam_informed", "actual_total", "perfect_foresight", "capture %"] if c in monthly]]
    show.columns = [LABEL.get(c, c) for c in show.columns]; show.index.name = "Month"
    say(md(show))

    # ---- worst single days ---------------------------------------------------
    say("\n## Worst single days for a real battery (energy revenue)\n")
    act = df[df.strategy == "actual"].copy()
    pf = df[df.strategy == "perfect_foresight"].set_index(["unit", "day"]).energy_rev
    act["perfect_that_day"] = act.set_index(["unit", "day"]).index.map(pf)
    worst = act.nsmallest(5, "energy_rev")[["unit", "day", "energy_rev", "perfect_that_day"]]
    worst["day"] = worst.day.dt.date.astype(str)
    worst.columns = ["Unit", "Day", "Actual $", "Perfect-foresight $"]
    say(md(worst.set_index("Unit"), floatfmt="{:,.0f}"))
    say("\nA large negative day usually means the unit charged into a price spike — "
        "a commissioning unit on a fixed test schedule, or a forced state-of-charge target.")

    (RES / "tables.md").write_text("\n".join(lines) + "\n")
    print(f"\ntables -> {RES/'tables.md'}")

    # ---- figures -----------------------------------------------------------
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    fig, ax = plt.subplots(figsize=(8, 4.2))
    order = [s for s in ORDER if LABEL[s] in fleet.index]
    vals = [fleet[LABEL[s]] for s in order]
    ax.barh([LABEL[s] for s in order], vals, color=[COLOR[s] for s in order])
    for i, (s, v) in enumerate(zip(order, vals)):
        ax.text(v + max(vals) * 0.01, i, f"${v:,.0f}  ({100*v/vals[-1]:.0f}%)", va="center")
    ax.set_xlabel("$/kW-year, fleet-weighted, settled at each unit's own node")
    ax.set_title(f"What {df.unit.nunique()} ERCOT batteries earned vs. what they could have")
    ax.set_xlim(0, max(vals) * 1.25); ax.invert_yaxis()
    fig.tight_layout(); fig.savefig(RES / "fig_strategies.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.hist(per["Capture %"], bins=15, color=COLOR["actual_total"], alpha=.85)
    ax.axvline(per["Capture %"].median(), color="k", ls="--", lw=1)
    ax.set_xlabel("Capture rate, % of perfect-foresight revenue (energy + AS)")
    ax.set_ylabel("units"); ax.set_title("Most batteries capture a third to a half of the ceiling")
    fig.tight_layout(); fig.savefig(RES / "fig_capture_hist.png", dpi=160); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.8))
    for s in ["perfect_foresight", "dam_informed", "actual_total"]:
        if s in monthly: ax.plot(monthly.index, monthly[s], marker="o", label=LABEL[s], color=COLOR[s])
    ax.set_ylabel("$/kW-yr (annualised)"); ax.set_title("Month by month")
    ax.legend(frameon=False); ax.tick_params(axis="x", rotation=45)
    fig.tight_layout(); fig.savefig(RES / "fig_monthly.png", dpi=160); plt.close(fig)

    # one illustrative day: the median-capture unit on its best perfect-foresight day
    try:
        from optimization import data as D
        from optimization.model import Battery
        from optimization.strategies import Optimiser
        u = per.index[len(per) // 2]
        best_day = (df[(df.unit == u) & (df.strategy == "perfect_foresight")]
                    .sort_values("energy_rev").day.iloc[-1])
        S, E = best_day.strftime("%Y-%m-%d"), (best_day + pd.DateOffset(days=1)).strftime("%Y-%m-%d")
        prm = D.battery_params(); r = prm[prm.unit == u].iloc[0]
        bat = Battery(u, float(r.p_chg), float(r.p_dis), float(r.soc_min), float(r.soc_max))
        rt = D.rt_prices(r.node, S, E); dam = D.dam_prices(r.node, S, E); act = D.actual_dispatch(u, S, E)
        g = pd.concat([rt.rename("rt"), dam.rename("dam"), act], axis=1, join="inner")
        soc0 = float(np.clip(g.soc_mwh.iloc[0], bat.soc_min, bat.soc_max))
        opt = Optimiser(bat, D.DT)
        pf = opt.run(g.rt.to_numpy(), soc0).net_mw; da = opt.run(g.dam.to_numpy(), soc0).net_mw
        fig, ax1 = plt.subplots(figsize=(9, 4))
        ax1.step(g.index, g.net_mw, where="post", color=COLOR["actual"], label="actual", lw=1.6)
        ax1.step(g.index, pf, where="post", color=COLOR["perfect_foresight"], label="perfect foresight", lw=1.2, alpha=.9)
        ax1.step(g.index, da, where="post", color=COLOR["dam_informed"], label="day-ahead informed", lw=1.2, alpha=.9)
        ax1.set_ylabel("net MW  (+ discharge / − charge)"); ax1.axhline(0, color="k", lw=.5)
        ax2 = ax1.twinx(); ax2.plot(g.index, g.rt, color="k", lw=.8, alpha=.5, label="RT price")
        ax2.set_ylabel("$/MWh")
        ax1.set_title(f"{u} @ {r.node}, {S}: what it did vs. what it could have done")
        h1, l1 = ax1.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, frameon=False, loc="upper left", fontsize=8)
        fig.tight_layout(); fig.savefig(RES / "fig_example_day.png", dpi=160); plt.close(fig)
        print(f"example day: {u} {S}")
    except Exception as e:                       # figures are a nice-to-have
        print(f"(example-day figure skipped: {e})")

    print("figures -> optimization/results/fig_*.png")


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "full")
