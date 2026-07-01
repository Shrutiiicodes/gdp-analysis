# Data provenance — interim files

Not every interim file is produced by a script. Some are curated once from a raw
source and then treated as a fixed input to `build_composite.py`. This table records
where each one comes from so the pipeline is auditable.

| Interim file | Raw source | Produced by | Type |
|---|---|---|---|
| `repo_rate_monthly_2011_2026.csv`, `repo_rate_quarterly_FY.csv` | `raw/repo/repo_rate_changelog.csv` | `src/make_repo_rate.py` | script-generated |
| `expenditure_components_quarterly_oldbase.csv` | `raw/gdp/Statement_Quarterly_Constant_28.11.2025.xlsx` (expenditure block, 2011-12 base) | curated once (manual clean) | curated input |
| `gdp_growth_contributions_quarterly.csv`, `gdp_growth_contributions_annual_FY.csv` | same old-base GDP statement (contributions-to-growth block) | curated once | curated input |
| `CPI_Combined_2012base_monthly_clean.csv` | `raw/cpi/RBIB Table No. 19 ... (Base 2010=100).xlsx` | curated once | curated input. NB: RBI table is *titled* "Base 2010=100" but the series is the official CPI-Combined **2012=100** (index ≈100 across 2012). Only the base-invariant YoY rate is used, so base choice doesn't affect results. |
| `fiscal_deficit_pct_gdp_quarterly.csv` | CGA monthly accounts / Union Budget (**no raw file in this repo**) | curated once, external | curated input |

Reproducibility note: `make_repo_rate.py` regenerates the repo files from raw. The
curated inputs above are committed as-is; `build_composite.py` consumes them directly.