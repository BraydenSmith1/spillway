"""
Reads ERCOT's API definition file and prints every endpoint
along with its date parameters. Saves a spreadsheet you can search.
"""

import json
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "data" / "ercot_api_spec.json"

spec = json.loads(SPEC.read_text())
rows = []

for path, methods in spec.get("paths", {}).items():
    get = methods.get("get")
    if not get:
        continue

    params = [p.get("name", "") for p in get.get("parameters", [])]
    # date-ish parameters are the ones we need for downloading history
    date_from = [p for p in params if p.lower().endswith("from")]
    date_to   = [p for p in params if p.lower().endswith("to")]

    rows.append({
        "endpoint": path,
        "summary": (get.get("summary") or "")[:90],
        "from_param": date_from[0] if date_from else "",
        "to_param": date_to[0] if date_to else "",
        "all_params": ", ".join(params),
    })

df = pd.DataFrame(rows).sort_values("endpoint")
out = ROOT / "data" / "ercot_endpoints.csv"
df.to_csv(out, index=False)

print(f"{len(df)} endpoints found. Saved to {out}\n")

# show the ones we care about
for term in ["spp_node", "lmp_node", "shadow", "load_forecast",
             "solar_power", "wind_power", "outage"]:
    hits = df[df["endpoint"].str.contains(term, case=False, na=False)]
    print(f"--- {term} ---")
    for _, r in hits.head(4).iterrows():
        print(f"  {r['endpoint']}")
        print(f"    from={r['from_param']!r}  to={r['to_param']!r}")
    print()