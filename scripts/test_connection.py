import sys, os, json
sys.path.append(os.path.dirname(__file__))
from ercot import probe, fetch

ENDPOINT = "/np6-905-cd/spp_node_zone_hub"

# Step 1: look at the raw shape before trusting any parsing
raw = probe(ENDPOINT, {"deliveryDateFrom": "2026-06-01",
                       "deliveryDateTo": "2026-06-01"})
if raw:
    print("\ntop-level keys:", list(raw.keys()))
    print("\nfields block:", json.dumps(raw.get("fields"), indent=2)[:800])
    print("\nfirst data row:", raw.get("data", [[]])[0])

# Step 2: full download
df = fetch(ENDPOINT, {"deliveryDateFrom": "2026-06-01",
                      "deliveryDateTo": "2026-06-02"}, verbose=True)
print(f"\nGot {len(df):,} rows")
print(df.head(10))
print("\nColumns:", list(df.columns))