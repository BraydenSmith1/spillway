"""
06_alias_scaffold.py — list the sites automation could not place, worst first.

Some ERCOT stems are acronyms or SPV names that no string method will match to
EIA-860 ("REDBARN", "SPTX12B", "RIGGINS"). Those need a human: look the site
up, fill in the EIA plant code, and 04_match_eia.py will apply the override.

Writes crosswalk/aliases_todo.csv ranked by curtailed MWh so effort goes where
the business value is. Copy rows into crosswalk/aliases.csv once resolved.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
cw = pd.read_parquet(ROOT / "crosswalk/crosswalk.parquet")
cu = pd.read_parquet(ROOT / "analysis/curtailment_by_unit.parquet")[["resource", "curt_mwh"]]
df = cw.merge(cu, on="resource", how="left")
df = df[df.fuel.isin(["PVGR", "WIND"]) & df.plant_code.isna()]
df["site"] = df.resource.str.split("_").str[0].str.replace(r"\d+$", "", regex=True)
todo = df.groupby("site").agg(fuel=("fuel", "first"), units=("resource", "count"),
    site_mw=("max_hsl_mw", "sum"), curt_gwh=("curt_mwh", lambda s: s.sum() / 1000),
    settlement_points=("settlement_point", lambda s: "; ".join(sorted(set(s.dropna())))),
    qse=("qse", "first"), dme=("dme", "first")).reset_index()
todo = todo.sort_values("curt_gwh", ascending=False).round(1)
todo["eia_plant_code"] = ""   # <- fill this in
todo["eia_plant_name"] = ""
todo.to_csv(ROOT / "crosswalk/aliases_todo.csv", index=False)
print(f"{len(todo)} unplaced sites written to crosswalk/aliases_todo.csv")
print(f"top 20 account for {todo.curt_gwh.head(20).sum()/todo.curt_gwh.sum():.0%} of unplaced curtailment\n")
print(todo.head(15)[["site","fuel","units","site_mw","curt_gwh","settlement_points","dme"]].to_string(index=False))
