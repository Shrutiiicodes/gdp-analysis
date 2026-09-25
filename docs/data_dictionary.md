# Data Dictionary — `composite_master_quarterly.csv`

Quarterly panel, **FY2011-12 Q1 → two quarters past the latest MoSPI print** (currently FY2026-27 Q3;
63 rows × 49 columns). FY = Indian
fiscal year (Apr–Mar). Q1 = Apr–Jun, Q2 = Jul–Sep, Q3 = Oct–Dec, Q4 = Jan–Mar. Produced only by
`src/build_composite.py` (which also appends `BankCredit_YoY` / `GST_YoY` when their raw files exist). "Non-null" counts reflect structural gaps (YoY warm-up, the
forecast horizon, and the discontinued old-base tail) — see notes.

## Identifiers & target

| Column | Description | Unit | Source | Non-null |
|---|---|---|---|---|
| `FY_Quarter` | Fiscal-year quarter label, e.g. `2023-24 Q2` | — | constructed spine | 62 |
| `GDP_growth` | **Primary target.** Continuous YoY real GDP growth: old 2011-12 base spliced with new 2022-23 base for the quarters the old series no longer covers | % YoY | MoSPI (spliced) | 57 |
| `GDP_growth_source` | Which base each `GDP_growth` value came from (`2011-12 base` / `2022-23 base (spliced)` / `—`) | — | flag | 63 |
| `GDP_growth_old` | YoY real GDP growth, **2011-12 base** (discontinued after 2025-26 Q2) | % YoY | MoSPI Statement (28.11.2025) | 54 |
| `GDP_growth_new` | YoY real GDP growth, **2022-23 base** (computed from new-base levels) | % YoY | MoSPI eSankhyiki API via `src/fetch_mospi.py` | 13 |
| `GDP_level_old` | Real GDP level, 2011-12 base | ₹ crore | MoSPI (28.11.2025) | 58 |
| `GDP_level_new` | Real GDP level, 2022-23 base (includes MoSPI's back-revisions) | ₹ crore | MoSPI eSankhyiki API | 17 |
| `PFCE_new`, `GFCE_new`, `GFCF_new`, `Exports_new`, `Imports_new` | Expenditure levels, 2022-23 base; used only to extend the YoY / ratio features past the discontinued old base | ₹ crore | MoSPI eSankhyiki API | 17 |
| `BaseRevision_gap` | `GDP_growth_new − GDP_growth_old` on overlapping quarters (size of the rebasing revision) | pp | derived | 10 |

## Expenditure components (levels, 2011-12 base, constant prices)

| Column | Description | Unit | Source | Non-null |
|---|---|---|---|---|
| `PFCE` | Private Final Consumption Expenditure | ₹ crore | MoSPI expenditure (old base) | 58 |
| `GFCE` | Government Final Consumption Expenditure | ₹ crore | MoSPI | 58 |
| `GFCF` | Gross Fixed Capital Formation (investment) | ₹ crore | MoSPI | 58 |
| `Exports` | Exports of goods & services | ₹ crore | MoSPI | 58 |
| `Imports` | Imports of goods & services | ₹ crore | MoSPI | 58 |
| `NetExports` | `Exports − Imports` | ₹ crore | derived | 58 |

## Macro indicators

| Column | Description | Unit | Source | Collapse rule | Non-null |
|---|---|---|---|---|---|
| `FiscalDeficit_pct_GDP` | Central fiscal deficit as % of GDP, **annual** figure broadcast to the four quarters of the FY; FY2025-26 is the Budget Estimate | % | CGA / Union Budget | annual → 4 quarters | 60 |
| `Repo_QtrAvg` | RBI repo rate, quarterly average (complete quarters only) | % | RBI | mean of months | 61 |
| `CPI_Inflation` | Combined CPI inflation (2012 base; Jan–Mar 2026 YoY taken from the 2024=100 series, index level not carried) | % YoY | RBI/MoSPI | mean of months | 57 |
| `IIP_growth` | Index of Industrial Production, headline growth | % YoY | MoSPI | mean of months | 56 |
| `INR_USD` | Rupee per US dollar, quarterly average | ₹/USD | RBI reference rates | mean of months | 61 |
| `INR_USD_vol` | Within-quarter std. dev. of the monthly INR/USD | ₹/USD | RBI | std of months | 61 |
| `Brent_USD` | Brent crude price, quarterly average | USD/bbl | FRED (MCOILBRENTEU) | mean of months | 62 |
| `M3_level` | Broad money supply (M3), quarter-end stock | ₹ crore | RBI Bulletin Table 7 | quarter-end | 61 |

## Engineered features

| Column | Description | Formula | Non-null |
|---|---|---|---|
| `GFCF_YoY` | Investment growth; old base through 2025-26 Q2, new base (`GFCF_new`) after | `GFCF.pct_change(4, fill_method=None)` | 57 |
| `Exports_YoY` | Export growth; old base then new base, as above | `Exports.pct_change(4, fill_method=None)` | 57 |
| `Imports_YoY` | Import growth; old base then new base, as above | `Imports.pct_change(4, fill_method=None)` | 57 |
| `M3_level_YoY` | Money-supply growth | `M3_level.pct_change(4, fill_method=None)` | 57 |
| `M3_growth_YoY` | Alias of `M3_level_YoY` (kept for readability; drop one before modelling) | = `M3_level_YoY` | 57 |
| `RealRate` | Real policy rate | `Repo_QtrAvg − CPI_Inflation` | 57 |
| `RealM3_YoY` | Real money growth | `M3_level_YoY − CPI_Inflation` | 56 |
| `CrudeINR` | Oil price in rupees | `Brent_USD × INR_USD` | 61 |
| `CrudeINR_YoY` | Rupee oil-price growth | `CrudeINR.pct_change(4, fill_method=None)` | 57 |
| `GDP_proxy_old` | Proxy GDP level for ratios (sum of big-4 components) | `PFCE+GFCE+GFCF+NetExports` | 58 |
| `InvestmentRate` | Investment share; new-base levels used after 2025-26 Q2 | `GFCF / GDP_proxy × 100` | 61 |
| `TradeOpenness` | Trade share; new-base levels used after 2025-26 Q2 | `(Exports+Imports) / GDP_proxy × 100` | 61 |
| `GDP_growth_lag1` | GDP growth, 1 quarter ago | `GDP_growth.shift(1)` | 57 |
| `GDP_growth_lag4` | GDP growth, 4 quarters ago (same quarter last year) | `GDP_growth.shift(4)` | 55 |

## Optional columns (appended by `build_composite.py` when raw files exist)

`build_composite.py` calls `add_bank_credit.add_credit` / `add_gst`; each column is present only if its
raw file exists. In this repo the bank-credit file is committed, so `BankCredit_YoY` is part of the table.

| Column | Description | Unit | Source | Non-null |
|---|---|---|---|---|
| `BankCredit_YoY` | Scheduled commercial bank credit, YoY growth (quarter-end stock). The latest quarter may be partial: raw data ends 31 May 2026, so 2026-27 Q1 uses the May fortnight | % YoY | RBI WSS Table 4 | 61 |
| `GST_YoY` | GST collection, YoY growth (quarterly sum of monthly collections) | % YoY | GSTN / CGA | varies |

## Calendar, regime & provenance

| Column | Description | Unit | Non-null |
|---|---|---|---|
| `Quarter` | Quarter number 1–4 | — | 63 |
| `Q1`–`Q4` | One-hot seasonal dummies | 0/1 | 63 |
| `COVID` | 1 for the four FY2020-21 quarters, else 0 (structural-break / intervention dummy) | 0/1 | 63 |
| `has_new_base` | 1 if a new-base GDP figure exists for the quarter | 0/1 | 63 |

---

# Data Dictionary — `gva_sectoral_quarterly.csv`

Tidy quarterly GVA table produced by `src/gva_sectors.py` from the RBI DBIE raw export.
Stored at `data/interim/gva_sectoral_quarterly.csv`.

| Column | Description | Unit | Source |
|---|---|---|---|
| `FY_Quarter` | Fiscal-year quarter label | — | derived |
| `Agriculture` | GVA at constant prices — Agriculture, Forestry & Fishing | ₹ crore | MoSPI via RBI DBIE |
| `Industry` | GVA — Mining + Manufacturing + Utilities + Construction | ₹ crore | MoSPI via RBI DBIE |
| `Services` | GVA — Trade/Transport/Comm + Financial/RE + Public Admin + Other | ₹ crore | MoSPI via RBI DBIE |
| `GVA_total` | Sum of the three headline sectors | ₹ crore | derived |
| `Agriculture_YoY` | Agriculture GVA, YoY growth | % YoY | derived |
| `Industry_YoY` | Industry GVA, YoY growth | % YoY | derived |
| `Services_YoY` | Services GVA, YoY growth | % YoY | derived |
| `GVA_total_YoY` | Total GVA, YoY growth | % YoY | derived |
| `Agriculture_contrib` | Agriculture contribution to aggregate GVA growth | pp | derived |
| `Industry_contrib` | Industry contribution to aggregate GVA growth | pp | derived |
| `Services_contrib` | Services contribution to aggregate GVA growth | pp | derived |

---

## Notes on missing values (all structural, not errors)
- **Head NaNs** (2011-12): YoY features need four prior quarters; some monthly series start in 2012.
- **`GDP_growth_old` ends at 2025-26 Q2**: the 2011-12 series was discontinued after the 27-Feb-2026 rebasing.
- **`GDP_*_new` and `*_new` levels start at 2022-23**: the new series doesn't exist before its base year (MoSPI's full back-series is expected Dec 2026).
- **`GDP_growth` runs through the latest MoSPI quarter** via splicing; the last two spine rows are the empty forecast horizon (the spine is rebuilt from the API file, so it moves forward on each release).
- **Leakage warning:** the `c_*` contribution columns (in `data/interim/gdp_growth_contributions_quarterly.csv`) sum to GDP growth and must **not** be used as model features — they belong to notebook 03 (decomposition) only.
- **`BankCredit_YoY` / `GST_YoY`** are only present if their raw files existed when `build_composite.py` ran.