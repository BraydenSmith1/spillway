"""
03_eia860_prep.py — one row per ERCOT generator from EIA Form 860.

EIA-860 is the federal census of every generator in the US. For each one it
records the plant, county, coordinates, technology, nameplate, first year of
operation, the operating utility and — where reported — the owners. This is
where county / owner / COD come from.

Source: https://www.eia.gov/electricity/data/eia860/  (2025 final release)
The zip is cached under data/external/ so the build is repeatable offline.
"""

from pathlib import Path
import zipfile, urllib.request
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STG = ROOT / "crosswalk" / "staging"
EXT = ROOT / "data" / "external" / "eia860"
URL = "https://www.eia.gov/electricity/data/eia860/xls/eia8602025.zip"

EXT.mkdir(parents=True, exist_ok=True)
zpath = EXT / "eia8602025.zip"
if not zpath.exists():
    urllib.request.urlretrieve(URL, zpath)
with zipfile.ZipFile(zpath) as z:
    z.extractall(EXT)

xl = lambda name: pd.read_excel(EXT / name, sheet_name=0, header=1)

gen = xl("3_1_Generator_Y2025.xlsx")
plant = xl("2___Plant_Y2025.xlsx")
own = xl("4___Owner_Y2025.xlsx")

gen = gen[gen["State"] == "TX"].drop(columns=["County"], errors="ignore")
# The plant table is the authoritative source for location.
plant = plant[["Plant Code", "County", "Latitude", "Longitude",
               "Balancing Authority Code"]]
g = gen.merge(plant, on="Plant Code", how="left")
g = g[g["Balancing Authority Code"] == "ERCO"]

# Largest owner per generator; fall back to the operating utility.
# Excel hands back mixed types in these columns, so normalise before use.
own["Percent Owned"] = pd.to_numeric(own["Percent Owned"], errors="coerce")
for frame in (g, own):
    frame["Generator ID"] = frame["Generator ID"].astype(str)
own = own.sort_values("Percent Owned", ascending=False) \
         .drop_duplicates(["Plant Code", "Generator ID"])
g = g.merge(own[["Plant Code", "Generator ID", "Owner Name", "Percent Owned"]],
            on=["Plant Code", "Generator ID"], how="left")
g["owner"] = g["Owner Name"].fillna(g["Utility Name"])

tech_map = {
    "Solar Photovoltaic": "PVGR",
    "Onshore Wind Turbine": "WIND",
    "Batteries": "PWRSTR",
    "Natural Gas Fired Combined Cycle": "CCGT",
    "Natural Gas Fired Combustion Turbine": "SCGT",
    "Natural Gas Steam Turbine": "GS",
    "Conventional Steam Coal": "CLLIG",
    "Nuclear": "NUC",
    "Conventional Hydroelectric": "HYDRO",
}
out = pd.DataFrame({
    "plant_code":   g["Plant Code"],
    "plant_name":   g["Plant Name"],
    "generator_id": g["Generator ID"].astype(str),
    "technology":   g["Technology"],
    "fuel":         g["Technology"].map(tech_map),
    "nameplate_mw": g["Nameplate Capacity (MW)"],
    "county":       g["County"],
    "latitude":     g["Latitude"],
    "longitude":    g["Longitude"],
    "operating_year": g["Operating Year"],
    "utility":      g["Utility Name"],
    "owner":        g["owner"],
    "owner_pct":    g["Percent Owned"],
    "eia_lmp_node": g["RTO/ISO LMP Node Designation"],
    "status":       g["Status"],
})
out.to_parquet(STG / "eia_generators.parquet", index=False)

print(f"{len(out):,} ERCOT generators in EIA-860")
print(out.fuel.value_counts(dropna=False).head(8).to_string())
print(f"\ncounty populated: {out.county.notna().mean():.0%}   "
      f"owner populated: {out.owner.notna().mean():.0%}   "
      f"lmp node populated: {out.eia_lmp_node.notna().mean():.0%}")
