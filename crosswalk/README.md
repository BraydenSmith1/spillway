# Crosswalk

**What it is:** one row per ERCOT generation resource, linking the name ERCOT
uses in dispatch data to the node it is priced at, and from there to the
physical plant — county, coordinates, owner, nameplate, first year of operation.

**Why it exists:** without it, curtailment data is about `BATCAVE_RN` and price
data is about `GALO_RN1`, and neither is about a company you can call.

```
python crosswalk/build.py          # rebuild everything, ~3 minutes
crosswalk/crosswalk.csv            # the result (also .parquet)
```

## Coverage (as built 2026-09-14)

| | Units | Price node | County / owner |
|---|---|---|---|
| Solar (PVGR) | 317 | **93%** | 33% |
| Wind | 399 | **89%** | 47% |
| Storage (PWRSTR) | 308 | 86% | 45% |

Read the two columns differently. The **node link is strong**: every link was
tested against price behaviour (a unit's node price should sag while it is
curtailed) and 100% of both exact and fuzzy links show that signature, with a
median sag of $25–60/MWh. The **plant link is partial**: ERCOT stems are often
acronyms or SPV names (`REDBARN`, `SPTX12B`, `RIGGINS`) that no string method
can match to EIA-860. Those sites need a human — see *Extending it* below.

Of the 50 most-curtailed units, 22 are placed. Of all curtailed MWh, 45% is.

## How each column is derived

| Column | Source | Method field |
|---|---|---|
| `fuel`, `qse`, `dme`, `max_hsl_mw` | our own SCED data | — |
| `settlement_point` | name stem match to price data; EIA's node field where naming failed | `sp_method`: `exact` / `lcpN` / `eia_node` / `none` |
| `county`, `latitude`, `longitude`, `owner`, `utility`, `operating_year`, `plant_nameplate_mw` | EIA Form 860 (2025), ERCOT balancing area only | `eia_method`: `eia_node` / `name+mw` / `mw` / `name` / `alias` |

`eia_score` is the evidence total behind the EIA link (max 9). Filter on it if
a downstream use needs high confidence.

## Steps

| Step | Does |
|---|---|
| `01_resource_inventory.py` | one row per resource from SCED |
| `02_resource_to_settlement_point.py` | link resource to node by name |
| `02b_validate_sp_links.py` | test those links against price behaviour |
| `03_eia860_prep.py` | download & clean EIA-860 for ERCOT |
| `04_match_eia.py` | score name similarity + nameplate agreement |
| `05_assemble.py` | combine into `crosswalk.csv` |
| `06_alias_scaffold.py` | list what automation missed, worst first |

## Extending it

`crosswalk/aliases_todo.csv` lists every unplaced site ranked by curtailed
MWh, with its price node, QSE and DME codes to help identification. To resolve
one: find the plant in EIA-860 (`crosswalk/staging/eia_generators.parquet`),
put its `plant_code` in the `eia_plant_code` column, copy the row into
`crosswalk/aliases.csv`, and rebuild. Aliases override every automated match.

The top 20 unplaced sites carry most of the unplaced curtailment, so twenty
lookups would move plant coverage on the sites that matter from ~45% to
roughly 80%.

## Known limitations

- ERCOT's official mapping (NP4-160-SG) sits behind an MIS login and was not
  used. If you obtain it, replace step 02.
- EIA-860 is annual; plants commissioned after its snapshot are absent.
- EIA's own node field is inconsistently formatted (`_ES_` vs `_ESS_`, bare
  `ERCOT`), so it is used as a hint, not a key.
- A stem can group units that EIA splits into separate plants (or vice versa);
  the nameplate check catches most of these but not all.
