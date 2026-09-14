"""
02_resource_to_settlement_point.py — link each generator to its price node.

ERCOT's official mapping (NP4-160-SG) sits behind an MIS login, so this is
derived from naming conventions and tagged with how confident each link is.

  exact    the part before the first "_" is identical           (~80%)
  lcpN     longest common prefix of N characters, best candidate (~10%)
  none     no plausible settlement point found

Validate before trusting a fuzzy row: when the resource is curtailed to zero,
its node price should be low or negative.
"""

from pathlib import Path
import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
STG = ROOT / "crosswalk" / "staging"
SPP = ROOT / "data/raw/settlement_point_prices/settlement_point_prices_2026-0[4-9].parquet"

# Resource-node style points only; hubs and load zones are not generators.
sp = duckdb.sql(f"""
    SELECT DISTINCT settlementPoint AS sp, settlementPointType AS sp_type
    FROM read_parquet('{SPP}')
    WHERE settlementPointType IN ('RN', 'PCCRN', 'LCCRN', 'PUN')
""").df()
sp["stem"] = sp.sp.str.split("_").str[0]

res = duckdb.sql(f"SELECT resource, fuel FROM '{STG}/resources.parquet'").df()
res["stem"] = res.resource.str.split("_").str[0]

# --- pass 1: exact stem -------------------------------------------------
exact = res.merge(sp, on="stem", how="inner")
# A stem can map to several points (e.g. _RN and _ALL). Prefer _ALL, then _RN.
exact["rank"] = exact.sp.str.contains("_ALL").map({True: 0, False: 1}) \
              + exact.sp.str.endswith("_RN").map({True: 0, False: 0.5})
exact = exact.sort_values(["resource", "rank"]).drop_duplicates("resource")
exact["method"] = "exact"

# --- pass 2: longest common prefix for the rest ---------------------------
def lcp(a, b):
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n

rest = res[~res.resource.isin(exact.resource)].copy()
rows = []
storage_words = ("ESS", "BESS", "_ES_", "BATT", "STOR")
for _, r in rest.iterrows():
    cands = sp.copy()
    cands["lcp"] = cands.stem.map(lambda s: lcp(r.stem, s))
    cands = cands[cands.lcp >= 4]
    # A wind/solar resource does not sit at a battery node.
    if r.fuel in ("PVGR", "WIND"):
        cands = cands[~cands.sp.str.contains("|".join(storage_words))]
    if cands.empty:
        rows.append({**r.to_dict(), "sp": None, "sp_type": None,
                     "method": "none"})
        continue
    cands["rank"] = -cands.lcp \
                  + cands.sp.str.contains("_ALL").map({True: 0, False: 0.5})
    best = cands.sort_values("rank").iloc[0]
    rows.append({**r.to_dict(), "sp": best.sp, "sp_type": best.sp_type,
                 "method": f"lcp{best.lcp}"})

fuzzy = pd.DataFrame(rows)
out = pd.concat([exact[["resource", "fuel", "sp", "sp_type", "method"]],
                 fuzzy[["resource", "fuel", "sp", "sp_type", "method"]]])
out = out.sort_values("resource").reset_index(drop=True)
out.to_parquet(STG / "resource_sp.parquet", index=False)

print(f"{len(out):,} resources")
print(out.method.value_counts().to_string())
ws = out[out.fuel.isin(["PVGR", "WIND"])]
print(f"\nwind+solar: {ws.sp.notna().sum()} of {len(ws)} linked "
      f"({100*ws.sp.notna().mean():.0f}%)")
