# GDP Project Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the pipeline reproducible end-to-end (scripts → master table → notebooks 01–05 → outputs) on the current venv, remove the fabricated feature values in the committed master table, and bring README/docs in line with what the code actually produces.

**Architecture:** Keep the existing layout (`src/` scripts, five notebooks, committed data/outputs). Fixes are surgical: one shared project-root resolver in `src/utils.py`, `fill_method=None` on every `pct_change`, bank credit folded into `build_composite.py` so the build is one idempotent step, the missing SHAP cell restored in notebook 02, orphan files removed, docs corrected, one small pytest file as the regression guard.

**Tech Stack:** Python 3.12.4 in `./venv` (pandas 3.0.3, numpy 2.4.6, statsmodels 0.14.6, scikit-learn 1.9.0, shap 0.52.0), Jupyter via `nbconvert`, pytest. Windows/PowerShell; run every command from the project root `C:\Users\asus\Projects\GDP`.

**Spec:** The **Findings** section below (this audit). There is no separate spec document.

## Global Constraints

- Interpreter is always `venv\Scripts\python` (never the system Python).
- No new runtime dependencies beyond `pytest` and `nbconvert` (dev/tooling only).
- `data/processed/composite_master_quarterly.csv` must be produced by a single `python src/build_composite.py` run; nothing else may rewrite it.
- Spine stays FY2011-12 Q1 → FY2026-27 Q2 (62 rows). Column names used by notebooks (`GDP_growth`, `FEATURES` list in notebook 02) must not change; `base_year_target` is the only column removed.
- Notebooks must run top-to-bottom via `jupyter nbconvert --execute` from the project root with no hardcoded absolute paths.
- Commit after every task. Regenerated CSVs/figures/pickles are committed (the repo intentionally tracks outputs).

## Findings (what is wrong, with evidence)

Severity: **P0** = results wrong or pipeline cannot run; **P1** = reproducibility/hygiene; **P2** = docs/narrative.

| # | Sev | Finding | Evidence |
|---|---|---|---|
| F1 | P0 | Committed master table has **fabricated YoY values** in the tail rows: `GFCF_YoY`, `Exports_YoY`, `Imports_YoY` for 2025-26 Q3 → 2026-27 Q2 and `M3_level_YoY`, `M3_growth_YoY`, `CrudeINR_YoY` for 2026-27 Q2 are non-null although the underlying level is NaN. Cause: the CSV was built with pandas < 3, where `pct_change` forward-filled NaN by default; `warnings.filterwarnings("ignore")` hid the FutureWarning. The venv now has pandas 3.0.3, so a rebuild gives different numbers (54 non-null vs 58). Downstream: notebook 04's scenario baseline vector is `df[FEATURES].ffill().iloc[-1]`, i.e. the 2026-27 Q2 row, so the published **Baseline scenario used GFCF_YoY = 0.0, Exports_YoY = 0.0, CrudeINR_YoY = 76.2**; the Granger screen for GFCF/Exports/Imports used 56 pairs instead of 54. ML training is unaffected (those rows drop because `InvestmentRate` is NaN). | Rebuilt in scratch and diffed: only those cells differ. `src/build_composite.py:163,142,168`, `src/add_bank_credit.py:29`, `src/gva_sectors.py:199` |
| F2 | P0 | **Notebook 02 cannot Run All.** Cells 16 and 17 use `sv`, `HAS_SHAP`, `shap_imp`, which no cell defines (the SHAP cell was deleted; cell 16 has execution count 16, out of sequence). `outputs/figures/02c_shap_summary.png` has no producer. | `notebooks/02_forecasting.ipynb` cells 16–17 |
| F3 | P0 | **Notebook 01 hardcodes** `os.chdir(r"C:\Users\asus\Projects\GDP")`; notebook 02 has the same path as a fallback. README claims the notebooks auto-detect the root. | `notebooks/01_eda.ipynb` cell 2; `02_forecasting.ipynb` cell 2 |
| F4 | P0 | **Build is not idempotent.** `add_bank_credit.py` rewrites the master CSV in place, so the committed file has 45 columns (`BankCredit_YoY`) while `build_composite.py` produces 44. Notebook 03 passes `"BankCredit_YoY"` to the driver screen and would silently drop it after a fresh build. The uncommitted data-dictionary edit (44 → 45 columns) papers over this. | `src/add_bank_credit.py:84-99`, `git diff docs/data_dictionary.md` |
| F5 | P1 | `requirements.txt` is unpinned and lacks `ipykernel`/`nbconvert`. The pandas 2 → 3 drift is exactly what caused F1. | `requirements.txt` |
| F6 | P1 | The project-root resolver is copy-pasted in `add_bank_credit.py`, `driver_screen.py`, `gva_sectors.py` and three notebooks, while `build_composite.py` and `make_repo_rate.py` use bare `Path("data")` and only work from the project root. | `src/*.py` |
| F7 | P1 | `warnings.filterwarnings("ignore")` at module level in every script and notebook. | all of `src/`, all notebooks |
| F8 | P1 | Orphan/stray files: `data/raw/gva/gva_sectoral_quarterly.csv` (an old copy of an *output* sitting in `raw/`, differs from the interim one; `gva_sectors.py` even has a guard against it), `outputs/forecasts/gdp_forecast_old_base.csv` (nothing writes it; stale forecast of quarters now known), `outputs/figures/02c_shap_summary.png` (no producer until F2 is fixed), untracked `project_metrics_gdp_analysis.md` (personal resume notes; also wrong: attributes RMSE 0.97 to SARIMAX when it is the naive baseline). | `git status`, grep for writers |
| F9 | P1 | No tests, no smoke check. A broken notebook (F2) and a wrong CSV (F1) were committed as "DONE. FINAL." | repo |
| F10 | P2 | **README contradicts the code.** README: "IIP and GFCF_YoY are the strongest Granger-significant leading indicators (p < 0.05)". Actual screen: significant are IIP (0.005), CPI (0.022), Brent (0.023); GFCF_YoY p = 0.41 and notebook 03's own takeaway says GFCF "does not lead growth". README "Top predictors: IIP and GFCF", but notebook 02 deliberately excludes GDP components from the consensus and reports IIP, fiscal deficit, crude. README quotes holdout RMSE only; the expanding-window CV RMSE for Ridge is 3.3 and the naive baseline is not in the CV comparison. | `README.md` Key results; `notebooks/02` cells 12, 17; `notebooks/03` cell 15 |
| F11 | P2 | `base_year_target` is the constant `"2011-12"` on all 62 rows, including the two spliced 2022-23 rows; the dictionary calls it "which base the training target uses". Redundant with `GDP_growth_source`. | `src/build_composite.py:158` |
| F12 | P2 | Notebook 01 figures are numbered `02_small_multiples`, `03a_corr_heatmap`, `04_lead_lag`, `06_base_year_overlay`, colliding with notebooks 02–04's numbering; the README diff removed "01_*" instead of fixing it. Notebook 01 uses `GDP_growth_old` as target while everything else uses the spliced `GDP_growth`. | `notebooks/01_eda.ipynb` |
| F13 | P2 | Doc gaps: CPI Jan–Mar 2026 YoY comes from the 2024=100 series (index NaN) but provenance says 2012=100 only; fiscal deficit is an annual figure broadcast to four quarters (2025-26 is a Budget Estimate) but the dictionary says "quarterly"; `BankCredit_YoY` for 2026-27 Q1 is a partial quarter (data ends 31 May 2026). | `data/interim/*.csv`, `docs/*.md` |
| F14 | P2 | Line endings: git warns "LF will be replaced by CRLF" on every touch; `core.autocrlf=true` with no `.gitattributes`. | `git diff` output |

## Review Focus

1. **pandas changes `pct_change` semantics again.** Expected: YoY columns are NaN wherever the level is NaN. Pinned by `test_master_has_no_yoy_where_level_missing` (Task 3).
2. **Notebook launched from `notebooks/` or from a Jupyter server whose cwd is elsewhere.** Expected: root still found by walking up. Pinned by `test_find_project_walks_up` (Task 2).
3. **`GDP_PROJECT` unset and cwd outside the repo.** Expected: a clear `FileNotFoundError`, not silently writing into cwd. Pinned by `test_find_project_raises_outside_repo` (Task 2).
4. **Bank credit raw file absent (fresh clone by someone without it).** Expected: build still succeeds, column simply absent. Pinned by `test_add_credit_missing_file_is_noop` (Task 4).
5. **Raw M3 file gains a new FY book-closure artefact row (e.g. 2027-03-31).** Expected: it is dropped like the 2026 one. Not pinned; the hardcoded date filter at `build_composite.py:101` is left as is and flagged with a `ponytail:` comment in Task 3.

---

### Task 1: Pin the environment

**Files:**
- Modify: `requirements.txt`

**Interfaces:**
- Produces: a `requirements.txt` that reproduces the venv used for all later tasks.

- [ ] **Step 1: Capture the versions actually installed**

Run:
```powershell
venv\Scripts\python -m pip show openpyxl | Select-String "^Version"
```
Note the openpyxl version printed (all other versions are already known and listed below).

- [ ] **Step 2: Rewrite `requirements.txt`**

```
pandas==3.0.3
numpy==2.4.6
statsmodels==0.14.6
scikit-learn==1.9.0
scipy==1.18.0
matplotlib==3.11.0
seaborn==0.13.2
shap==0.52.0
joblib==1.5.3
openpyxl==<version from Step 1>
# notebooks / tooling
ipykernel==7.3.0
nbconvert
pytest
```

- [ ] **Step 3: Install the two new tools and verify the pins are satisfiable**

Run:
```powershell
venv\Scripts\python -m pip install -r requirements.txt
venv\Scripts\python -m pip check
```
Expected: `No broken requirements found.`

- [ ] **Step 4: Commit**

```powershell
git add requirements.txt
git commit -m "chore: pin requirements to the working venv; add nbconvert and pytest"
```

---

### Task 2: One project-root resolver in `utils.py`

**Files:**
- Modify: `src/utils.py`
- Modify: `src/add_bank_credit.py:15-23`, `src/driver_screen.py:42-50`, `src/gva_sectors.py:80-88`
- Modify: `src/build_composite.py:48-52`, `src/make_repo_rate.py:26-29`
- Create: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `utils.find_project() -> pathlib.Path` — returns the project root (dir containing `data/processed`), honouring `GDP_PROJECT`; raises `FileNotFoundError` if not found. All scripts import it as `from utils import find_project` (with the existing `except ImportError: from .utils import ...` fallback).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_pipeline.py`:
```python
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from utils import fy_quarter, order_key, find_project  # noqa: E402


def test_fy_quarter_and_order():
    assert fy_quarter(2012, 4) == "2012-13 Q1"
    assert fy_quarter(2013, 3) == "2012-13 Q4"
    assert order_key("2011-12 Q4") < order_key("2012-13 Q1")


def test_find_project_walks_up(monkeypatch):
    monkeypatch.delenv("GDP_PROJECT", raising=False)
    monkeypatch.chdir(ROOT / "notebooks")
    assert find_project() == ROOT


def test_find_project_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("GDP_PROJECT", str(ROOT))
    monkeypatch.chdir(tmp_path)
    assert find_project() == ROOT


def test_find_project_raises_outside_repo(monkeypatch, tmp_path):
    monkeypatch.delenv("GDP_PROJECT", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        find_project()
```

- [ ] **Step 2: Run to verify they fail**

Run: `venv\Scripts\python -m pytest tests/test_pipeline.py -v`
Expected: `ImportError: cannot import name 'find_project'`.

- [ ] **Step 3: Add `find_project` to `src/utils.py`**

Append to `src/utils.py` (add `import os` next to the existing `from pathlib import Path`):
```python
def find_project():
    """Project root = the directory containing data/processed.
       Order: $GDP_PROJECT, then walk up from the current working directory."""
    env = os.environ.get("GDP_PROJECT")
    if env and (Path(env).expanduser() / "data").is_dir():
        return Path(env).expanduser().resolve()
    for cand in (Path.cwd(), *Path.cwd().parents):
        if (cand / "data" / "processed").is_dir():
            return cand
    raise FileNotFoundError("Project root not found: run from inside the repo or set GDP_PROJECT")
```

- [ ] **Step 4: Replace the three copies and the two bare `Path("data")`**

In `src/add_bank_credit.py`, `src/driver_screen.py`, `src/gva_sectors.py`: delete the local `_project()` / `find_project()` function, add `find_project` to the `from utils import ...` line (both branches of the try/except), and replace every call `_project()` with `find_project()`. In `driver_screen.py` the import block currently has no `utils` import; add:
```python
try:
    from utils import find_project
except ImportError:
    from .utils import find_project
```

In `src/build_composite.py` replace line 48 `DATA    = Path("data")` with:
```python
DATA    = find_project() / "data"
```
and add `find_project` to both `from utils import ...` lines. In `src/make_repo_rate.py` replace line 26 `DATA = Path("data")` with `DATA = find_project() / "data"` and add `find_project` to both `from utils import ...` lines; delete the `if not src.exists(): ... rglob` fallback (lines 35–39) — the resolver makes it dead.

- [ ] **Step 5: Run tests and the two builders from a subdirectory to prove the resolver works**

Run:
```powershell
venv\Scripts\python -m pytest tests/test_pipeline.py -v
cd src; ..\venv\Scripts\python make_repo_rate.py; ..\venv\Scripts\python driver_screen.py; cd ..
git status --short data/interim
```
Expected: 4 passed; both scripts print their tables; `git status` shows no change to the interim repo-rate CSVs (byte-identical rebuild).

- [ ] **Step 6: Commit**

```powershell
git add src tests
git commit -m "refactor: single find_project() resolver in utils; scripts run from any cwd"
```

---

### Task 3: Kill the forward-fill artefact in every YoY (F1, F7)

**Files:**
- Modify: `src/build_composite.py:142,163,168` and remove line 37 (`warnings.filterwarnings("ignore")`)
- Modify: `src/add_bank_credit.py:29`
- Modify: `src/gva_sectors.py:199` and remove line 41
- Modify: `src/driver_screen.py` remove line 36
- Modify: `tests/test_pipeline.py`

**Interfaces:**
- Produces: a master CSV where every `*_YoY` is NaN wherever its level is NaN.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pipeline.py`:
```python
import pandas as pd  # put with the other imports at the top

LEVEL_TO_YOY = [("GFCF", "GFCF_YoY"), ("Exports", "Exports_YoY"), ("Imports", "Imports_YoY"),
                ("M3_level", "M3_level_YoY"), ("M3_level", "M3_growth_YoY"),
                ("CrudeINR", "CrudeINR_YoY")]


def test_master_has_no_yoy_where_level_missing():
    df = pd.read_csv(ROOT / "data" / "processed" / "composite_master_quarterly.csv")
    assert len(df) == 62 and not df["FY_Quarter"].duplicated().any()
    for lvl, yoy in LEVEL_TO_YOY:
        assert df.loc[df[lvl].isna(), yoy].isna().all(), f"{yoy} has values where {lvl} is NaN"
```

- [ ] **Step 2: Run to verify it fails against the committed CSV**

Run: `venv\Scripts\python -m pytest tests/test_pipeline.py::test_master_has_no_yoy_where_level_missing -v`
Expected: FAIL with `GFCF_YoY has values where GFCF is NaN`.

- [ ] **Step 3: Make every `pct_change` explicit**

`src/build_composite.py`:
```python
# line 142
gdp_new["GDP_growth_new"] = gdp_new["GDP_level_new"].pct_change(4, fill_method=None) * 100
# line 163
    panel[col + "_YoY"] = panel[col].pct_change(4, fill_method=None) * 100
# line 168
panel["CrudeINR_YoY"]  = panel["CrudeINR"].pct_change(4, fill_method=None) * 100
```
`src/add_bank_credit.py` line 29:
```python
    d[out_col] = d[level_col].pct_change(4, fill_method=None) * 100
```
`src/gva_sectors.py` line 199:
```python
        gva[f"{s}_YoY"] = gva[s].pct_change(4, fill_method=None) * 100
```
Delete the module-level `warnings.filterwarnings("ignore")` (and the now-unused `import warnings`) from `build_composite.py`, `driver_screen.py`, `gva_sectors.py`. Add above the M3 filter at `build_composite.py:101`:
```python
# ponytail: hardcoded 2026-03-31 book-closure row; generalise to "any 31-Mar row ~2x its neighbours" if a new vintage adds another
```

- [ ] **Step 4: Rebuild and run the test**

Run:
```powershell
venv\Scripts\python src/build_composite.py
venv\Scripts\python -m pytest tests/test_pipeline.py -v
```
Expected: build prints `shape=(62, 44)` and no warnings; 5 passed. (`BankCredit_YoY` is gone for now — Task 4 brings it back inside the build.)

- [ ] **Step 5: Commit (code only; the CSV is committed after Task 4 so the data changes land once)**

```powershell
git add src tests
git commit -m "fix: pct_change(fill_method=None) everywhere; stop blanket-ignoring warnings"
```

---

### Task 4: Make the build one idempotent step (F4, F11)

**Files:**
- Modify: `src/build_composite.py` (after line 203, before `# 6) SAVE`; line 158)
- Modify: `src/add_bank_credit.py` (delete `main()` and the `__main__` block, lines 84–112)
- Modify: `data/processed/feature_manifest.csv` (remove the `base_year_target` row)
- Modify: `tests/test_pipeline.py`
- Modify: `README.md` "How to run" (remove step 3), folder tree comment for `add_bank_credit.py`

**Interfaces:**
- Consumes: `add_bank_credit.add_credit(master: DataFrame, proj: Path) -> DataFrame` and `add_gst(...)` (unchanged signatures).
- Produces: `composite_master_quarterly.csv` with 44 columns (45 minus `base_year_target` plus `BankCredit_YoY`), written only by `build_composite.py`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pipeline.py`:
```python
def test_master_contains_bank_credit_and_no_constant_label():
    df = pd.read_csv(ROOT / "data" / "processed" / "composite_master_quarterly.csv")
    assert "BankCredit_YoY" in df.columns
    assert "base_year_target" not in df.columns


def test_add_credit_missing_file_is_noop(tmp_path):
    from add_bank_credit import add_credit
    (tmp_path / "data" / "raw" / "credit").mkdir(parents=True)
    master = pd.DataFrame({"FY_Quarter": ["2011-12 Q1"]})
    out = add_credit(master, tmp_path)
    assert list(out.columns) == ["FY_Quarter"]
```

- [ ] **Step 2: Run to verify they fail**

Run: `venv\Scripts\python -m pytest tests/test_pipeline.py -v`
Expected: `test_master_contains_bank_credit_and_no_constant_label` FAILS (`BankCredit_YoY` missing after the Task 3 rebuild); `test_add_credit_missing_file_is_noop` PASSES already (it pins existing behaviour).

- [ ] **Step 3: Fold the optional proxies into the build and drop the constant label**

In `src/build_composite.py`:
- Delete line 158 `panel["base_year_target"] = "2011-12"` and its two comment lines above it (keep `has_new_base`).
- Insert after line 203 (`panel["GDP_growth_lag4"] = ...`):
```python
# --- OPTIONAL PROXIES (skipped with a message if the raw files are absent) ----
try:
    from add_bank_credit import add_credit, add_gst
except ImportError:
    from .add_bank_credit import add_credit, add_gst
panel = add_credit(panel, DATA.parent)
panel = add_gst(panel, DATA.parent)
```
In `src/add_bank_credit.py`: delete `main()` and the `if __name__ == "__main__":` block (lines 84–112) and the now-unused `import numpy as np`. Add a module docstring at the top:
```python
"""
add_bank_credit.py
------------------
Optional proxies appended to the master table BY build_composite.py (not run directly):
    BankCredit_YoY  from data/raw/credit/bank_credit_outstanding.csv (Date, BankCredit)
                    or a raw RBI WSS Table-4 export named WSS_Table*.xlsx in the same folder
    GST_YoY         from data/raw/gst/gst_collections_monthly.csv (Date, GST)
If a file is missing the column is simply not added.
"""
```
In `data/processed/feature_manifest.csv` delete the line `base_year_target,dropped,provenance label,0`.

- [ ] **Step 4: Rebuild, run tests, run the driver screen**

Run:
```powershell
venv\Scripts\python src/build_composite.py
venv\Scripts\python -m pytest tests/test_pipeline.py -v
venv\Scripts\python src/driver_screen.py
```
Expected: build prints `shape=(62, 44)`; 7 passed; driver screen lists `IIP_growth`, `CPI_Inflation`, `Brent_USD` as Granger-significant.

- [ ] **Step 5: Update README run steps**

In `README.md` "How to run": delete step 3 (`add_bank_credit.py`) and renumber; change the folder-tree comment to `add_bank_credit.py  # optional BankCredit_YoY / GST_YoY, called by build_composite.py`. In step 2's comment add: `(also appends BankCredit_YoY if data/raw/credit/bank_credit_outstanding.csv is present)`.

- [ ] **Step 6: Commit code + regenerated data**

```powershell
git add src tests README.md data/processed
git commit -m "fix: build_composite is the single writer of the master table; drop constant base_year_target"
```

---

### Task 5: Restore notebook 02 so it runs top-to-bottom (F2, F10-CV)

**Files:**
- Modify: `notebooks/02_forecasting.ipynb` (cell 2 path fallback, cell 12 CV loop, new cell before cell 16)

**Interfaces:**
- Produces: variables `sv` (ndarray, n_rows × n_features), `shap_imp` (Series indexed by `FEATURES`), `HAS_SHAP = True`, consumed by existing cells 16–17; `outputs/figures/02c_shap_summary.png` regenerated.

- [ ] **Step 1: Verify the failure**

Run: `venv\Scripts\jupyter nbconvert --to notebook --execute --inplace notebooks/02_forecasting.ipynb`
Expected: fails with `NameError: name 'sv' is not defined`.

- [ ] **Step 2: Remove the hardcoded fallback in cell 2**

Replace the `CANDIDATES` list with:
```python
CANDIDATES = [
    os.environ.get("GDP_PROJECT", ""),                       # 1) env var, if set
    *[str(p) for p in [Path.cwd(), *Path.cwd().parents]],    # 2) walk up from cwd
]
```

- [ ] **Step 3: Put the naive baseline into the expanding-window CV (cell 12)**

Replace cell 12 with:
```python
cv_rmse = {}
for name, mdl in models.items():
    errs = []
    for tr_idx, te_idx in tscv.split(X):
        mdl.fit(X.iloc[tr_idx], y.iloc[tr_idx])
        errs.append(rmse(y.iloc[te_idx], mdl.predict(X.iloc[te_idx])))
    cv_rmse[name] = np.mean(errs)
# same folds for the random-walk baseline, so the comparison is like-for-like
cv_rmse["Naive (t-1)"] = np.mean([rmse(y.iloc[te], y.shift(1).iloc[te]) for _, te in tscv.split(X)])
cv = pd.Series(cv_rmse, name="CV_RMSE").sort_values()
print(cv.round(3).to_string())
```

- [ ] **Step 4: Insert the SHAP cell as a new code cell immediately before current cell 16**

```python
# (c) SHAP on the best model (refit on full data). Permutation explainer = model-agnostic.
import shap
best_model = models[BEST].fit(X, y)
explainer = shap.Explainer(best_model.predict, X, seed=0)
sv = explainer(X).values                                   # rows x features
shap_imp = pd.Series(np.abs(sv).mean(0), index=FEATURES).sort_values(ascending=False)
HAS_SHAP = True
shap.summary_plot(sv, X, feature_names=FEATURES, show=False)
plt.gcf().savefig(FIGS/"02c_shap_summary.png", dpi=150, bbox_inches="tight"); plt.show()
print("mean |SHAP|:"); print(shap_imp.round(3).to_string())
```

- [ ] **Step 5: Execute the notebook in place and check outputs**

Run:
```powershell
venv\Scripts\jupyter nbconvert --to notebook --execute --inplace notebooks/02_forecasting.ipynb
git status --short outputs
```
Expected: exit 0; `02c_shap_summary.png`, `02c_shap_bar.png`, `gdp_forecast_FY2026_27.csv`, and both model files show as modified. Open the executed notebook and confirm cell 12 output now includes `Naive (t-1)` and cell 17 says `avg rank across 3 methods`.

- [ ] **Step 6: Commit**

```powershell
git add notebooks/02_forecasting.ipynb outputs
git commit -m "fix(nb02): restore SHAP cell, add naive baseline to CV, drop hardcoded path"
```

---

### Task 6: Notebook 01 portable and consistent (F3, F12)

**Files:**
- Modify: `notebooks/01_eda.ipynb` cells 2, 3, 7, 9, 14, 18
- Modify: `README.md` folder tree (`figures/` line)
- Rename: `outputs/figures/02_small_multiples.png → 01a_small_multiples.png`, `03a_corr_heatmap.png → 01b_corr_heatmap.png`, `04_lead_lag.png → 01c_lead_lag.png`, `06_base_year_overlay.png → 01d_base_year_overlay.png`

**Interfaces:**
- Produces: figures `01a`–`01d`; notebook 01 analyses the spliced `GDP_growth` target used by notebooks 02–04.

- [ ] **Step 1: Replace the `os.chdir` in cell 2**

Replace
```python
# --- the whole path problem, solved in one line ---
os.chdir(r"C:\Users\asus\Projects\GDP")
PROJECT = Path.cwd()
```
with
```python
# Project root: $GDP_PROJECT, else walk up from cwd (same rule as src/utils.find_project).
PROJECT = Path(os.environ.get("GDP_PROJECT", "")).expanduser()
if not (PROJECT / "data" / "processed").is_dir():
    PROJECT = next(c for c in (Path.cwd(), *Path.cwd().parents) if (c / "data" / "processed").is_dir())
```

- [ ] **Step 2: Switch the EDA target to the spliced series (cell 3)**

Replace `TARGET = "GDP_growth_old"` with `TARGET = "GDP_growth"` and `ID_COLS = ["FY_Quarter", "base_year_target"]` with `ID_COLS = ["FY_Quarter", "GDP_growth_source"]`. In cell 9 delete the two dead entries `"GDP_growth_old_lag1", "GDP_growth_old_lag4",` from `cand`.

- [ ] **Step 3: Renumber the saved figures**

Cell 7: `FIGS / "01a_small_multiples.png"`. Cell 9: `FIGS / "01b_corr_heatmap.png"`. Cell 14: `FIGS / "01c_lead_lag.png"`. Cell 18: `FIGS / "01d_base_year_overlay.png"`. Then:
```powershell
git rm outputs/figures/02_small_multiples.png outputs/figures/03a_corr_heatmap.png outputs/figures/04_lead_lag.png outputs/figures/06_base_year_overlay.png
```
README folder tree: `figures/       # all charts (PNG): 01a-d_* (EDA), 02a-e_*, 03b-e_*, 04a/b_*, 05a-c_*`.

- [ ] **Step 4: Execute from a different cwd to prove portability**

Run:
```powershell
cd notebooks; ..\venv\Scripts\jupyter nbconvert --to notebook --execute --inplace 01_eda.ipynb; cd ..
Get-ChildItem outputs\figures\01*
```
Expected: exit 0; four `01a`–`01d` PNGs present; the stationarity table's first row is now `GDP_growth`.

- [ ] **Step 5: Commit**

```powershell
git add notebooks/01_eda.ipynb outputs/figures README.md
git commit -m "fix(nb01): no hardcoded path, spliced target, 01a-d figure names"
```

---

### Task 7: Remove orphan and stray files (F8, F14)

**Files:**
- Delete: `data/raw/gva/gva_sectoral_quarterly.csv`, `outputs/forecasts/gdp_forecast_old_base.csv`
- Move out of repo: `project_metrics_gdp_analysis.md` (untracked; personal notes)
- Create: `.gitattributes`

- [ ] **Step 1: Confirm nothing reads the two files**

Run:
```powershell
git grep -n "gdp_forecast_old_base"; git grep -n "raw/gva/gva_sectoral"
```
Expected: no hits in `src/`, `notebooks/`, `docs/` (the only match, if any, is this plan).

- [ ] **Step 2: Delete and move**

```powershell
git rm data/raw/gva/gva_sectoral_quarterly.csv outputs/forecasts/gdp_forecast_old_base.csv
Move-Item project_metrics_gdp_analysis.md ..\GDP_resume_metrics.md
```
(The moved file also needs a correction before it is used anywhere: RMSE 0.97 is the naive random-walk baseline, not the SARIMAX model; the Granger-significant set is IIP, CPI, Brent — see F10.)

- [ ] **Step 3: Normalise line endings**

Create `.gitattributes`:
```
* text=auto
*.ipynb text eol=lf
*.png binary
*.xlsx binary
*.pkl binary
*.joblib binary
```
Run `git add --renormalize .` and check `git status` — expect only line-ending-only diffs, if any.

- [ ] **Step 4: Verify the GVA builder still runs and picks the right input**

Run: `venv\Scripts\python src/gva_sectors.py`
Expected: prints `reading: gva_by_activity_quarterly.xlsx` and saves 05a/05b/05c; `git status` shows `data/interim/gva_sectoral_quarterly.csv` unchanged (byte-identical).

- [ ] **Step 5: Commit**

```powershell
git add -A
git commit -m "chore: remove orphan outputs, add .gitattributes"
```

---

### Task 8: Regenerate every downstream output on the corrected table (F1 downstream)

**Files:**
- Modify (by execution): `notebooks/03_contributions.ipynb`, `notebooks/04_scenarios.ipynb`, `notebooks/05_gva_sectors.ipynb`, `outputs/figures/03*,04*,05*`, `outputs/forecasts/gdp_scenarios_FY2026_27.csv`

- [ ] **Step 1: Run the three remaining notebooks in order**

```powershell
venv\Scripts\jupyter nbconvert --to notebook --execute --inplace notebooks/03_contributions.ipynb
venv\Scripts\jupyter nbconvert --to notebook --execute --inplace notebooks/04_scenarios.ipynb
venv\Scripts\jupyter nbconvert --to notebook --execute --inplace notebooks/05_gva_sectors.ipynb
```
Expected: all exit 0.

- [ ] **Step 2: Check the scenario baseline is no longer built from fabricated values**

Open `notebooks/04_scenarios.ipynb` cell 4 output. Expected: `GFCF_YoY` and `Exports_YoY` baseline values are the last real observations (2025-26 Q2: ≈7.33 and ≈5.59), not `0.00`; `CrudeINR_YoY` baseline ≈ −10, not 76.2. Note the new Optimistic/Baseline/Pessimistic numbers from `outputs/forecasts/gdp_scenarios_FY2026_27.csv` for Task 9.

- [ ] **Step 3: Run the full test file one more time and commit**

```powershell
venv\Scripts\python -m pytest tests -v
git add notebooks outputs
git commit -m "chore: regenerate notebooks 03-05 and outputs on the corrected master table"
```

---

### Task 9: Docs tell the truth (F10, F11, F13)

**Files:**
- Modify: `README.md` "Key results", "How to run" (add the test/smoke commands)
- Modify: `docs/data_dictionary.md`
- Modify: `docs/data_provenance.md`
- Modify: `docs/decisions.md`

- [ ] **Step 1: README key results**

Replace the "Granger-causality screen" bullet with:
```
- **Granger-causality screen:** IIP growth is both coincident (r ≈ 0.93) and leading
  (p ≈ 0.005). CPI inflation and Brent are the other Granger-significant series (p < 0.05
  at lag 2). GFCF_YoY is strongly coincident (r ≈ 0.83) but does **not** lead growth
  (p ≈ 0.41): it moves with GDP rather than ahead of it.
```
Replace the "Top predictors" bullet with:
```
- **Top predictors of growth:** industrial production (IIP) by a consensus of Lasso,
  permutation importance and SHAP; among external drivers it is followed by the fiscal
  deficit and rupee crude. GFCF ranks high too but is a component of GDP, so it is reported
  separately from the external drivers.
```
Replace the "Best accuracy" bullet with:
```
- **Best accuracy:** on the 8-quarter holdout a random-walk baseline (RMSE 0.97) is not
  beaten; Ridge is within 0.06. Under 5-fold expanding-window CV all models are far worse
  (Ridge ≈ 3.3, naive shown alongside), so the models' value is interpretability, not accuracy.
```
Update the scenario numbers anywhere they appear (README does not quote them today; `docs/decisions.md` does not either — only `project_metrics` did). Add to "How to run":
```bash
# Regression checks (data invariants + path resolver)
venv\Scripts\python -m pytest tests -v
# Execute every notebook headlessly, in order
venv\Scripts\jupyter nbconvert --to notebook --execute --inplace notebooks/0*.ipynb
```

- [ ] **Step 2: Data dictionary**

- Header: `62 rows × 44 columns` and add: `Produced only by src/build_composite.py (which also appends BankCredit_YoY / GST_YoY when their raw files exist).`
- Delete the `base_year_target` row.
- `FiscalDeficit_pct_GDP`: description → `Central fiscal deficit as % of GDP, **annual** figure broadcast to the four quarters of the FY; FY2025-26 is the Budget Estimate`; collapse rule → `annual → 4 quarters`.
- `CPI_Inflation`: add `Jan–Mar 2026 YoY taken from the 2024=100 series (index level not carried)`.
- Non-null counts: `GFCF_YoY`, `Exports_YoY`, `Imports_YoY` → 54; `M3_level_YoY`, `M3_growth_YoY`, `CrudeINR_YoY` → 57 (read them off `df.notna().sum()` after Task 8 and copy exactly).
- Optional columns section: rename to `Optional columns (appended by build_composite.py when raw files exist)` and add to `BankCredit_YoY`: `the latest quarter may be partial (raw data ends 31 May 2026 → 2026-27 Q1 uses the May fortnight)`.

- [ ] **Step 3: Provenance and decisions**

`docs/data_provenance.md`: in the CPI row add `Jan–Mar 2026 inflation is the provisional 2024=100-base print (index not on the 2012 base); YoY is base-invariant so it is used as is.` In the optional-files table: `Produced by` → `src/build_composite.py via add_bank_credit.add_credit`.

`docs/decisions.md`, "Data construction": add
```
- **YoY never forward-fills.** Every `pct_change(4)` passes `fill_method=None`. pandas < 3 padded
  NaN levels before differencing, which fabricated YoY values for quarters with no level data
  (caught 2026-09; the tail of the previously committed table was affected). `tests/test_pipeline.py`
  pins the invariant.
```
"Known limitations": replace the base-sensitivity bullet's `~10` with the real overlap count printed by notebook 02 cell 22.

- [ ] **Step 4: Commit**

```powershell
git add README.md docs
git commit -m "docs: align README/dictionary/provenance/decisions with the corrected pipeline"
```

---

## Self-review

- **Coverage:** F1→T3+T8, F2→T5, F3→T1/T6/T5, F4→T4, F5→T1, F6→T2, F7→T3, F8→T7, F9→T2–T4 tests, F10→T5+T9, F11→T4+T9, F12→T6, F13→T9, F14→T7. No finding without a task.
- **Names:** `find_project` (T2) used in T2 scripts and mirrored inline in notebooks (T5/T6) because notebooks cannot import `utils` before knowing the root. `add_credit`/`add_gst` signatures unchanged (T4). `sv`/`shap_imp`/`HAS_SHAP` (T5) match the names the existing cells 16–17 already use.
- **Order matters:** T3 and T4 both rebuild the CSV; data is committed once, in T4. T8 must follow T4–T7 because notebooks 03/04 read the table and notebook 05 regenerates the GVA interim CSV that T7 checks.
