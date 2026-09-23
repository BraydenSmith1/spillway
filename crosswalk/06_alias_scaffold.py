"""
06_alias_scaffold.py — list the sites automation could not place, worst first.

Some ERCOT stems are acronyms or SPV names that no string method will match to
EIA-860 ("REDBARN", "SPTX12B", "RIGGINS"). Those need a human: look the site
up, fill in the EIA plant code, and 04_match_eia.py will apply the override.

Writes crosswalk/aliases_todo.csv with two kinds of row, each ranked within
its kind so effort goes where the value is:

    generation   unplaced wind/solar sites, ranked by curtailed GWh
    storage      unplaced battery sites, ranked by energy capacity (MWh)

`priority` interleaves the two rankings (1 = top generation site, 2 = top
storage site, ...). Copy resolved rows into crosswalk/aliases.csv.
"""

from pathlib import Path
import sys

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

cw = pd.read_parquet(ROOT / "crosswalk/crosswalk.parquet")
cw["site"] = cw.resource.str.split("_").str[0].str.replace(r"\d+$", "", regex=True)
placed_sites = set(cw[cw.county.notna()].site)

# ---- generation: unplaced, ranked by curtailment ----------------------------
cu = pd.read_parquet(ROOT / "analysis/curtailment_by_unit.parquet")[["resource", "curt_mwh"]]
g = cw[cw.fuel.isin(["PVGR", "WIND"])].merge(cu, on="resource", how="left")
g = g[g.plant_code.isna()]
gen = g.groupby("site").agg(fuel=("fuel", "first"), units=("resource", "count"),
                            site_mw=("max_hsl_mw", "sum"), metric=("curt_mwh", lambda s: s.sum() / 1000),
                            settlement_points=("settlement_point", lambda s: "; ".join(sorted(set(s.dropna())))),
                            qse=("qse", "first"), dme=("dme", "first")).reset_index()
gen["kind"], gen["metric_name"] = "generation", "curtailed_gwh_12mo"

# ---- storage: unplaced ESR units, ranked by capacity ------------------------
con = duckdb.connect(); con.sql("SET TimeZone = 'America/Chicago'")
esr = con.sql(f"""
    SELECT "Resource Name" AS unit, ROUND(MAX("Max SOC"),1) AS soc_max_mwh, ROUND(MAX(HSL),1) AS p_dis_mw,
           MODE(QSE) AS qse, MODE(DME) AS dme
    FROM read_parquet('{ROOT}/data/raw/sced_esr/esr_*.parquet') GROUP BY 1
""").df()
esr["site"] = esr.unit.str.split("_").str[0].str.replace(r"\d+$", "", regex=True)
esr = esr[~esr.site.isin(placed_sites)]
sto = esr.groupby("site").agg(units=("unit", "count"), site_mw=("p_dis_mw", "sum"),
                              metric=("soc_max_mwh", "sum"), qse=("qse", "first"), dme=("dme", "first")).reset_index()
sto["fuel"], sto["kind"], sto["metric_name"] = "PWRSTR", "storage", "capacity_mwh"
sto["settlement_points"] = ""

# ---- combine, rank within kind, interleave ----------------------------------
todo = pd.concat([gen, sto], ignore_index=True)
todo = todo[todo.metric > 0]
todo["rank_in_kind"] = todo.groupby("kind").metric.rank(ascending=False, method="first").astype(int)
todo["priority"] = todo.rank_in_kind * 2 - (todo.kind == "generation").astype(int)
todo = todo.sort_values("priority")
todo["eia_plant_code"] = ""      # <- fill this in
todo["eia_plant_name"] = ""
todo = todo[["priority", "kind", "site", "fuel", "units", "site_mw", "metric_name", "metric",
             "settlement_points", "qse", "dme", "eia_plant_code", "eia_plant_name"]].round(1)
todo.to_csv(ROOT / "crosswalk/aliases_todo.csv", index=False)

print(f"{len(todo)} unplaced sites -> crosswalk/aliases_todo.csv "
      f"({int((todo.kind=='generation').sum())} generation, {int((todo.kind=='storage').sum())} storage)")
gt, st = todo[todo.kind == "generation"], todo[todo.kind == "storage"]
print(f"top 20 generation sites carry {gt.metric.head(20).sum()/gt.metric.sum():.0%} of unplaced curtailment; "
      f"top 20 storage sites carry {st.metric.head(20).sum()/st.metric.sum():.0%} of unplaced capacity\n")
print(todo.head(24)[["priority", "kind", "site", "units", "site_mw", "metric_name", "metric", "dme"]].to_string(index=False))
