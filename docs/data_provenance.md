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
| `CPI_Combined_2012base_monthly_clean.csv` | `raw/cpi/RBIB Table No. 19 ... (Base 2010=100).xlsx` | curated once | curated input. NB: RBI table is *titled* "Base 2010=100" but the series is the official CPI-Combined **2012=100** (index ≈100 across 2012). Only the base-invariant YoY rate is used, so base choice doesn't affect results. Jan–Mar 2026 inflation is the provisional 2024=100-base print (index not on the 2012 base); YoY is base-invariant so it is used as is. |
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

## Optional columns (appended by `build_composite.py` via `add_bank_credit.py`)

These files are **not** required for the main pipeline. They are added on request if the
corresponding raw files are present.

| Optional raw file | Description | Produced by |
|---|---|---|
| `raw/credit/bank_credit_outstanding.csv` | Scheduled commercial bank credit, quarter-end stock. Either provide a clean CSV with `Date` and `BankCredit` columns, or drop the raw RBI WSS Table-4 xlsx (`WSS_Table*.xlsx`) in the same folder — the script will parse and cache it automatically. | `src/build_composite.py` via `add_bank_credit.add_credit` |
| `raw/gst/gst_collections_monthly.csv` | Monthly GST collections. Clean CSV with `Date` and `GST` columns. | `src/build_composite.py` via `add_bank_credit.add_gst` |

---

## Reproducibility notes

- `make_repo_rate.py` and `gva_sectors.py` are fully script-generated from their raw inputs.
- **Brent is fetched automatically**: `src/fetch_brent.py` downloads FRED series
  `MCOILBRENTEU` (https://fred.stlouisfed.org/graph/fredgraph.csv?id=MCOILBRENTEU) and writes it in the
  repo's DD-MM-YYYY layout. `python run_all.py --fetch` runs it before the build; the monthly GitHub
  Actions job does the same and commits the result.
- **Every other raw file is a manual download.** MoSPI (IIP, GVA) and RBI (CPI, M3, FX,
  bank credit) publish Excel files whose URLs change per release and have no stable public API, so a data
  refresh is: download the new file, drop it into the matching `data/raw/<source>/` folder with the same
  name pattern the glob expects (see `build_composite.py`), then `python run_all.py`.
- The five **curated inputs** listed above are committed as-is; `build_composite.py` consumes them directly.
- The two **optional** credit/GST files are never committed to the repo; they extend the master CSV in-place when present.
- The **old-base** GDP statement (`*28.11.2025*.xlsx`) is read directly by `build_composite.py` via a glob pattern.
- The **new-base** (2022-23) quarterly series is `raw/gdp/mospi_quarterly_constant_2022-23.csv`, written by
  `src/fetch_mospi.py` from MoSPI's eSankhyiki JSON API (`https://api.mospi.gov.in/api/nas/getNASData`,
  base_year=2022-23, frequency_code=2, indicator codes 5/10/11/9/12/13/14/15/2; no authentication; the
  server needs legacy TLS renegotiation). It carries every back-revision MoSPI applies, so the master
  table follows the official series automatically. `python run_all.py --fetch` and the monthly CI job
  refresh it. The archived press-release xlsx (`*05.06.2026*.xlsx`) is kept only as the vintage snapshot
  used before the API switch; nothing reads it.