"""
04_match_eia.py — attach county, owner, coordinates and COD to ERCOT resources.

ERCOT names units ("GALLOWAY_SOLAR1", "ASCK_UNIT1"); EIA names plants
("Galloway 1 Solar Farm", "Ash Creek Solar"). Matching is done at the site
level and scored on two kinds of evidence, because ERCOT stems are often
acronyms that no string metric alone will catch:

  name   prefix / subsequence / similarity of the stem vs. the cleaned name
  size   agreement between summed max-HSL and EIA nameplate, same fuel

A site is linked when the combined score clears a threshold. The method
column records which evidence carried it, and eia_score the total.

  eia_node   EIA reports the plant's ERCOT node and it matches ours
  name       name evidence dominant
  name+mw    both, the usual case
  mw         nameplate nearly exact and name weakly similar (acronyms)
"""

from pathlib import Path
from difflib import SequenceMatcher
import re
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STG = ROOT / "crosswalk" / "staging"

res = pd.read_parquet(STG / "resources.parquet")
sp = pd.read_parquet(STG / "resource_sp.parquet")[["resource", "sp"]]
eia = pd.read_parquet(STG / "eia_generators.parquet")

FUELS = {"PVGR", "WIND", "PWRSTR"}
res = res[res.fuel.isin(FUELS)].merge(sp, on="resource", how="left")
res["stem"] = res.resource.str.split("_").str[0]
# AMADEUS1 / AMADEUS2 are one plant to EIA; group on the stem sans digits.
res["site"] = res.stem.str.replace(r"\d+$", "", regex=True)
eia = eia[eia.fuel.isin(FUELS) & (eia.status == "OP")]

STOP = {"SOLAR", "WIND", "LLC", "LP", "INC", "FARM", "ENERGY", "PROJECT",
        "POWER", "PARTNERS", "HOLDINGS", "PHASE", "I", "II", "III", "IV",
        "STORAGE", "BESS", "BATTERY", "CENTER", "GENERATION", "PORTFOLIO",
        "THE", "OF", "AND", "GRID", "RANCH", "CREEK", "HILL", "COUNTY"}

def clean(name):
    toks = re.sub(r"[^A-Z0-9 ]", " ", str(name).upper()).split()
    return "".join(t for t in toks if t not in STOP)

def node_stem(n):
    """ANEM_ESS_RN, ANEM_ES_RN, GALO_RN1, PAVLOV_BESS -> ANEM, GALO, PAVLOV"""
    return re.split(r"[_\-]", str(n).upper().strip())[0]

def is_subsequence(a, b):
    it = iter(b)
    return all(ch in it for ch in a)

# --- ERCOT sites -----------------------------------------------------------
site = res.groupby("site").agg(
    fuel=("fuel", "first"),
    site_mw=("max_hsl_mw", "sum"),
    sps=("sp", lambda s: set(s.dropna())),
).reset_index()
site["sp_stems"] = site.sps.map(lambda s: {node_stem(x) for x in s})

# --- EIA plants ------------------------------------------------------------
plant = eia.groupby("plant_code").agg(
    plant_name=("plant_name", "first"),
    fuel=("fuel", "first"),
    nameplate_mw=("nameplate_mw", "sum"),
    county=("county", "first"),
    latitude=("latitude", "first"),
    longitude=("longitude", "first"),
    operating_year=("operating_year", "min"),
    utility=("utility", "first"),
    owner=("owner", lambda s: s.mode().iat[0] if s.notna().any() else None),
    eia_nodes=("eia_lmp_node", lambda s: {str(x).upper().strip() for x in s.dropna()}),
).reset_index()
plant["key"] = plant.plant_name.map(clean)
plant["node_stems"] = plant.eia_nodes.map(
    lambda ns: {node_stem(n) for n in ns if n not in ("ERCOT", "NAN") and "BUS" not in n})

def score(s, p):
    stem, key = s.site, p.key
    name = 0
    if len(stem) >= 4 and key.startswith(stem):
        name = 3
    elif len(stem) >= 4 and is_subsequence(stem, key):
        name = 2
    else:
        r = SequenceMatcher(None, stem, key[:len(stem) + 3]).ratio()
        name = 2 if r >= 0.85 else (1 if r >= 0.6 else 0)
    if p.nameplate_mw <= 0 or s.site_mw <= 0:
        size = 0
    else:
        d = abs(p.nameplate_mw - s.site_mw) / p.nameplate_mw
        size = 3 if d <= 0.05 else (2 if d <= 0.15 else (1 if d <= 0.6 else -3))
    return name, size

links = []
for _, s in site.iterrows():
    cands = plant[plant.fuel == s.fuel]
    if cands.empty:
        continue
    # pass A: EIA's own node points at one of our settlement points
    hit = cands[cands.node_stems.map(lambda ns: bool(ns & s.sp_stems))]
    if len(hit) == 1:
        links.append((s.site, hit.iloc[0].plant_code, "eia_node", 6.0))
        continue
    # pass B: scored evidence
    best = None
    for _, p in cands.iterrows():
        name, size = score(s, p)
        total = name + size
        if best is None or total > best[0]:
            best = (total, name, size, p.plant_code)
    total, name, size, code = best
    if total >= 4 and name >= 1:
        method = "name" if size <= 1 else ("mw" if name == 1 else "name+mw")
        links.append((s.site, code, method, float(total)))

lk = pd.DataFrame(links, columns=["site", "plant_code", "eia_method", "eia_score"])

# Hand-resolved sites win over everything above. See 06_alias_scaffold.py.
alias_path = ROOT / "crosswalk" / "aliases.csv"
if alias_path.exists():
    al = pd.read_csv(alias_path).dropna(subset=["eia_plant_code"])
    al = al[al.eia_plant_code.astype(str).str.strip() != ""]
    if len(al):
        al = pd.DataFrame({"site": al.site, "plant_code": al.eia_plant_code.astype(int),
                           "eia_method": "alias", "eia_score": 9.0})
        lk = pd.concat([al, lk[~lk.site.isin(al.site)]], ignore_index=True)
        print(f"applied {len(al)} manual aliases")
out = res.merge(lk, on="site", how="left") \
         .merge(plant.drop(columns=["key", "eia_nodes", "node_stems", "fuel"]),
                on="plant_code", how="left")

# EIA can supply a settlement point where naming failed us (GALLOWAY -> GALO_RN1).
import duckdb
all_sps = set(duckdb.sql(f"""
    SELECT DISTINCT settlementPoint FROM read_parquet('{ROOT}/data/raw/settlement_point_prices/settlement_point_prices_2026-0[4-9].parquet')
""").df().settlementPoint)  # every node the market prices, not just ones we already linked
fill = out.sp.isna() & out.plant_code.notna()
node_of = plant.set_index("plant_code").eia_nodes
out.loc[fill, "sp"] = out.loc[fill, "plant_code"].map(
    lambda c: next((n for n in node_of.get(c, set()) if n in all_sps), None))
out["sp_from_eia"] = fill & out.sp.notna()

out.to_parquet(STG / "resource_eia.parquet", index=False)

ws = out[out.fuel.isin(["PVGR", "WIND"])]
print(f"wind+solar resources: {len(ws)}   linked to EIA: {ws.plant_code.notna().sum()} "
      f"({100*ws.plant_code.notna().mean():.0f}%)")
print(out.eia_method.value_counts(dropna=False).to_string())
print(f"\nsettlement points recovered from EIA's node field: {int(out.sp_from_eia.sum())}")
