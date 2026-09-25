"""
run_all.py -- the whole pipeline in one command (from anywhere inside the repo):

    python run_all.py            # rebuild interim + master table, GVA view, notebooks 01-05, tests
    python run_all.py --fetch    # same, but first refresh Brent (FRED) and the new-base GDP series (MoSPI API)

Stops at the first failing step and exits non-zero, so CI can gate on it.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable

STEPS = [
    ("repo rate",      [PY, "src/make_repo_rate.py"]),
    ("master table",   [PY, "src/build_composite.py"]),
    ("GVA sectors",    [PY, "src/gva_sectors.py"]),
    *[(f"notebook {nb.name}", [PY, "-m", "jupyter", "nbconvert", "--to", "notebook",
                                "--execute", "--inplace", str(nb)])
      for nb in sorted((ROOT / "notebooks").glob("0*.ipynb"))],
    ("tests",          [PY, "-m", "pytest", "tests", "-q"]),
]
if "--fetch" in sys.argv:
    STEPS.insert(0, ("fetch GDP (MoSPI API)", [PY, "src/fetch_mospi.py"]))
    STEPS.insert(0, ("fetch Brent (FRED)", [PY, "src/fetch_brent.py"]))

for name, cmd in STEPS:
    print(f"\n=== {name} ===", flush=True)
    if subprocess.run(cmd, cwd=ROOT).returncode:
        sys.exit(f"FAILED at step: {name}")
print("\nAll steps passed.")
