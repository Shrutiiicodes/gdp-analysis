# Data provenance — interim files

Not every interim file is produced by a script. Some are curated once from a raw
source and then treated as a fixed input to `build_composite.py`. This table records
where each one comes from so the pipeline is auditable.

## Core interim files (required for `build_composite.py`)

| Interim file | Raw source | Produced by | Type |
|---|---|---|---|
| `repo_rate_monthly_2011_2026.csv`, `repo_rate_quarterly_FY.csv` | `raw/repo/repo_rate_changelog.csv` | `src/make_repo_rate.py` | script-generated |
| `expenditure_components_quarterly_oldbase.csv` | `raw/gdp/Statement_Quarterly_Constant_28.11.2025.xlsx` (expenditure block, 2011-12 base) | curated once (manual clean) | curated input |
| `gdp_growth_contributions_quarterly.csv`, `gdp_growth_contributions_annual_FY.csv` | same old-base GDP statement (contributions-to-growth block) | curated once | curated input |
| `CPI_Combined_2012base_monthly_clean.csv` | `raw/cpi/RBIB Table No. 19 ... (Base 2010=100).xlsx` | curated once | curated input. NB: RBI table is *titled* "Base 2010=100" but the series is the official CPI-Combined **2012=100** (index ≈100 across 2012). Only the base-invariant YoY rate is used, so base choice doesn't affect results. |
| `fiscal_deficit_pct_gdp_quarterly.csv` | CGA monthly accounts / Union Budget (**no raw file in this repo**) | curated once, external | curated input |

## GVA sectoral interim file (required for notebook 05 / `gva_sectors.py`)

| Interim file | Raw source | Produced by | Type |
|---|---|---|---|
| `gva_sectoral_quarterly.csv` | `raw/gva/gva_by_activity_quarterly.xlsx` (RBI DBIE export: "Quarterly Estimates of GVA at Basic Prices by Economic Activity, Constant Prices") | `src/gva_sectors.py` | script-generated |

**How to get the raw GVA file:**
1. Go to [https://data.rbi.org.in](https://data.rbi.org.in) → National Account Statistics.
2. Navigate to *"Quarterly Estimates of GVA at Basic Prices by Economic Activity"* → Constant Prices.
3. Export as Excel and save to `data/raw/gva/gva_by_activity_quarterly.xlsx`.
4. Run `python src/gva_sectors.py`.

## Optional interim files (appended by `add_bank_credit.py`)

These files are **not** required for the main pipeline. They are added on request if the
corresponding raw files are present.

| Optional raw file | Description | Produced by |
|---|---|---|
| `raw/credit/bank_credit_outstanding.csv` | Scheduled commercial bank credit, quarter-end stock. Either provide a clean CSV with `Date` and `BankCredit` columns, or drop the raw RBI WSS Table-4 xlsx (`WSS_Table*.xlsx`) in the same folder — the script will parse and cache it automatically. | `src/add_bank_credit.py` |
| `raw/gst/gst_collections_monthly.csv` | Monthly GST collections. Clean CSV with `Date` and `GST` columns. | `src/add_bank_credit.py` |

---

## Reproducibility notes

- `make_repo_rate.py` and `gva_sectors.py` are fully script-generated from their raw inputs.
- The five **curated inputs** listed above are committed as-is; `build_composite.py` consumes them directly.
- The two **optional** credit/GST files are never committed to the repo; they extend the master CSV in-place when present.
- The two raw GDP statement xlsx files (`*28.11.2025*.xlsx`, `*05.06.2026*.xlsx`) are read directly by `build_composite.py` using glob patterns, so small filename differences (dots vs underscores) are tolerated.