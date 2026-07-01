# Data Dictionary — `composite_master_quarterly.csv`

Quarterly panel, **FY2011-12 Q1 → FY2026-27 Q2** (62 rows × 44 columns). FY = Indian
fiscal year (Apr–Mar). Q1 = Apr–Jun, Q2 = Jul–Sep, Q3 = Oct–Dec, Q4 = Jan–Mar. Built by
`src/build_composite.py`. "Non-null" counts reflect structural gaps (YoY warm-up, the
forecast horizon, and the discontinued old-base tail) — see notes.

## Identifiers & target

| Column | Description | Unit | Source | Non-null |
|---|---|---|---|---|
| `FY_Quarter` | Fiscal-year quarter label, e.g. `2023-24 Q2` | — | constructed spine | 62 |
| `GDP_growth` | **Primary target.** Continuous YoY real GDP growth: old 2011-12 base spliced with new 2022-23 base for the quarters the old series no longer covers | % YoY | MoSPI (spliced) | 56 |
| `GDP_growth_source` | Which base each `GDP_growth` value came from (`2011-12 base` / `2022-23 base (spliced)` / `—`) | — | flag | 62 |
| `GDP_growth_old` | YoY real GDP growth, **2011-12 base** (discontinued after 2025-26 Q2) | % YoY | MoSPI Statement (28.11.2025) | 54 |
| `GDP_growth_new` | YoY real GDP growth, **2022-23 base** (computed from new-base levels) | % YoY | MoSPI Statement (05.06.2026) | 12 |
| `GDP_level_old` | Real GDP level, 2011-12 base | ₹ crore | MoSPI (28.11.2025) | 58 |
| `GDP_level_new` | Real GDP level, 2022-23 base | ₹ crore | MoSPI (05.06.2026) | 16 |
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
| `FiscalDeficit_pct_GDP` | Central fiscal deficit as % of GDP | % | CGA / derived | quarterly | 60 |
| `Repo_QtrAvg` | RBI repo rate, quarterly average | % | RBI | mean of months | 60 |
| `CPI_Inflation` | Combined CPI inflation (2012 base) | % YoY | RBI/MoSPI | mean of months | 57 |
| `IIP_growth` | Index of Industrial Production, headline growth | % YoY | MoSPI | mean of months | 56 |
| `INR_USD` | Rupee per US dollar, quarterly average | ₹/USD | RBI reference rates | mean of months | 61 |
| `INR_USD_vol` | Within-quarter std. dev. of the monthly INR/USD | ₹/USD | RBI | std of months | 61 |
| `Brent_USD` | Brent crude price, quarterly average | USD/bbl | FRED (MCOILBRENTEU) | mean of months | 61 |
| `M3_level` | Broad money supply (M3), quarter-end stock | ₹ crore | RBI Bulletin Table 7 | quarter-end | 61 |

## Engineered features

| Column | Description | Formula | Non-null |
|---|---|---|---|
| `GFCF_YoY` | Investment growth | `GFCF.pct_change(4)` | 54 |
| `Exports_YoY` | Export growth | `Exports.pct_change(4)` | 54 |
| `Imports_YoY` | Import growth | `Imports.pct_change(4)` | 54 |
| `M3_level_YoY` | Money-supply growth | `M3_level.pct_change(4)` | 57 |
| `M3_growth_YoY` | Alias of `M3_level_YoY` (kept for readability; drop one before modelling) | = `M3_level_YoY` | 57 |
| `RealRate` | Real policy rate | `Repo_QtrAvg − CPI_Inflation` | 57 |
| `RealM3_YoY` | Real money growth | `M3_level_YoY − CPI_Inflation` | 56 |
| `CrudeINR` | Oil price in rupees | `Brent_USD × INR_USD` | 61 |
| `CrudeINR_YoY` | Rupee oil-price growth | `CrudeINR.pct_change(4)` | 57 |
| `GDP_proxy_old` | Proxy GDP level for ratios (sum of big-4 components) | `PFCE+GFCE+GFCF+NetExports` | 58 |
| `InvestmentRate` | Investment share | `GFCF / GDP_proxy_old × 100` | 58 |
| `TradeOpenness` | Trade share | `(Exports+Imports) / GDP_proxy_old × 100` | 58 |
| `GDP_growth_lag1` | GDP growth, 1 quarter ago | `GDP_growth.shift(1)` | 56 |
| `GDP_growth_lag4` | GDP growth, 4 quarters ago (same quarter last year) | `GDP_growth.shift(4)` | 54 |

## Calendar, regime & provenance

| Column | Description | Unit | Non-null |
|---|---|---|---|
| `Quarter` | Quarter number 1–4 | — | 62 |
| `Q1`–`Q4` | One-hot seasonal dummies | 0/1 | 62 |
| `COVID` | 1 for the four FY2020-21 quarters, else 0 (structural-break / intervention dummy) | 0/1 | 62 |
| `base_year_target` | Which base the training target uses (label) | — | 62 |
| `has_new_base` | 1 if a new-base GDP figure exists for the quarter | 0/1 | 62 |

## Notes on missing values (all structural, not errors)
- **Head NaNs** (2011-12): YoY features need four prior quarters; some monthly series start in 2012.
- **`GDP_growth_old` ends at 2025-26 Q2**: the 2011-12 series was discontinued after the 27-Feb-2026 rebasing.
- **`GDP_*_new` start at 2022-23**: the new series doesn't exist before its base year.
- **`GDP_growth` is complete through 2025-26 Q4** via splicing; **FY2026-27 Q1/Q2** are the empty forecast horizon.
- **Leakage warning:** the `c_*` contribution columns (in `data/interim/gdp_growth_contributions_quarterly.csv`) sum to GDP growth and must **not** be used as model features — they belong to notebook 03 (decomposition) only.