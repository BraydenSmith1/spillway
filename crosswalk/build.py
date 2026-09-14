"""
build.py — rebuild the crosswalk end to end.

    python crosswalk/build.py

Runs the numbered steps in order and prints each one's summary. Takes a few
minutes; most of it is scanning SCED for the resource inventory.

  01  resource inventory from SCED        (fuel, QSE/DME, max HSL)
  02  resource -> settlement point         (naming conventions, tagged)
  02b validate those links against prices  (report only)
  03  EIA-860 prep                         (county, owner, coordinates, COD)
  04  resource -> EIA plant                (scored name + nameplate match)
  05  assemble crosswalk.csv / .parquet

Output columns carry a *_method field so you can filter by confidence.
"""

import subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STEPS = ["01_resource_inventory.py", "02_resource_to_settlement_point.py",
         "02b_validate_sp_links.py", "03_eia860_prep.py",
         "04_match_eia.py", "05_assemble.py"]

for step in STEPS:
    print(f"\n{'=' * 70}\n  {step}\n{'=' * 70}")
    r = subprocess.run([sys.executable, str(HERE / step)])
    if r.returncode:
        sys.exit(f"{step} failed")
