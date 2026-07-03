# Forecasting India's GDP Growth

An end-to-end pipeline that assembles a quarterly macroeconomic panel for India, explores it,
forecasts real GDP growth, decomposes what drives it, and breaks down production-side GVA
by sector — handling the February 2026 rebasing of the National Accounts from base year
2011-12 to 2022-23.

## What the project does
1. Collects 12+ public macro indicators and combines them into one quarterly master table.
2. Engineers features, prunes redundant ones (correlation + VIF), and tests stationarity.
3. Compares forecasting models under time-aware validation and identifies the top growth drivers.
4. Forecasts GDP growth for FY2026-27 Q1 and Q2 (SARIMAX with a deterministic COVID dummy).
5. Decomposes realised growth into demand-side expenditure contributions.
6. Runs a Granger-causality / predictive-causality screen on all candidate drivers.
7. Breaks down production-side GVA across Agriculture, Industry, and Services sectors.

## How to run (from the project root)

```bash
# 1. Regenerate the repo-rate interim files from the raw changelog
python src/make_repo_rate.py
#    (Other interim files — expenditure, GDP contributions, CPI, fiscal deficit — are
#     curated inputs already in data/interim/; see docs/data_provenance.md for sources.)

# 2. Assemble the quarterly master table -> data/processed/composite_master_quarterly.csv
python src/build_composite.py

# 3. [Optional] Append bank credit and/or GST collections to the master table
#    (requires data/raw/credit/bank_credit_outstanding.csv or a raw RBI WSS Table-4 xlsx)
python src/add_bank_credit.py

# 4. [Optional] Run the predictive-causality (Granger) driver screen standalone
python src/driver_screen.py

# 5. [Optional] Build the GVA sectoral view
#    (requires data/raw/gva/gva_by_activity_quarterly.xlsx from RBI DBIE)
python src/gva_sectors.py

# 6. Open the notebooks in order and Run All
#    notebooks/01_eda.ipynb           -> cleaning, EDA, feature selection
#    notebooks/02_forecasting.ipynb   -> models, accuracy, drivers, forecast, saved models
#    notebooks/03_contributions.ipynb -> demand-side decomposition
#    notebooks/04_scenarios.ipynb     -> scenario analysis
#    notebooks/05_gva_sectors.ipynb   -> production-side GVA sectoral breakdown
```

The notebooks auto-detect the project root (they walk up from the notebook's folder), so
no path editing is needed after cloning. To force a location, set the `GDP_PROJECT`
environment variable. Then use **Kernel → Restart & Run All**.

Requirements: see `requirements.txt`. Install with `pip install -r requirements.txt`.

## Folder structure

```
gdp-analysis/
  data/
    raw/
      gdp/       # MoSPI GDP statements (both 2011-12 and 2022-23 base)
      cpi/       # RBI CPI monthly data
      iip/       # MoSPI IIP monthly data
      fx/        # RBI monthly average exchange rates
      crude/     # FRED Brent crude prices (MCOILBRENTEU.csv)
      m3/        # RBI broad money supply (M3)
      repo/      # RBI repo rate changelog
      gva/       # RBI DBIE GVA by economic activity (for notebook 05)
      credit/    # [optional] RBI WSS Table-4 bank credit outstanding
    interim/     # cleaned intermediate CSVs
      repo_rate_monthly_2011_2026.csv
      repo_rate_quarterly_FY.csv
      expenditure_components_quarterly_oldbase.csv
      gdp_growth_contributions_quarterly.csv
      gdp_growth_contributions_annual_FY.csv
      CPI_Combined_2012base_monthly_clean.csv
      fiscal_deficit_pct_gdp_quarterly.csv
      gva_sectoral_quarterly.csv          <- produced by gva_sectors.py
    processed/
      composite_master_quarterly.csv      <- the main analysis table
      composite_master_quarterly.xlsx     <- same, Excel format
  src/
    utils.py            # shared helpers (fiscal-quarter logic, file finding)
    collapse_monthly.py # monthly/fortnightly -> quarterly collapse functions
    make_repo_rate.py   # raw repo changelog -> monthly + quarterly repo files
    build_composite.py  # assembles the master table from all sources
    add_bank_credit.py  # [optional] appends BankCredit_YoY and GST_YoY to master
    driver_screen.py    # Granger-causality / predictive-causality screen
    gva_sectors.py      # production-side GVA sectoral builder (Agriculture/Industry/Services)
  notebooks/
    01_eda.ipynb            # cleaning, EDA, feature selection
    02_forecasting.ipynb    # models, accuracy, drivers, forecast
    03_contributions.ipynb  # demand-side decomposition
    04_scenarios.ipynb      # scenario analysis
    05_gva_sectors.ipynb    # production-side GVA sectoral breakdown
  outputs/
    figures/       # all charts (PNG): 01_*, 02_*, 03_*, 04_*, 05a/05b/05c_*
    forecasts/     # gdp_forecast_FY2026_27.csv
    models/        # saved SARIMAX + best ML model (.pkl)
  docs/
    data_dictionary.md   # per-column documentation for composite_master_quarterly.csv
    data_provenance.md   # source and reproducibility notes for interim files
    decisions.md         # methodology choices and rationale
```

## Key results

- **Best accuracy:** a random-walk baseline (RMSE 0.97); regularized linear models match it
  to within ~0.1 RMSE, so the models' value is interpretability, not a large accuracy gain.
- **Top predictors of growth:** industrial production (IIP) and fixed investment (GFCF), by a
  consensus of Lasso, permutation importance and SHAP.
- **Granger-causality screen:** IIP and GFCF_YoY are also the strongest Granger-significant
  leading indicators (p < 0.05 over lags 1–4), reinforcing the driver story with predictive
  precedence — not just contemporaneous correlation.
- **Largest accounting contributor:** private consumption (~3.6 pp average), then investment.
- **Forecast (SARIMAX + COVID dummy):** FY2026-27 Q1 ~ 7.1%, Q2 ~ 6.1% (80% interval).
- **Production-side structure:** Services dominate GVA (~55% share); Industry and Agriculture
  are more volatile. Sectoral contributions are visualised in notebook 05.
- **Base-year sensitivity:** the driver ranking appears to shift across the 2011-12 vs
  2022-23 base (rank-correlation ~ -0.27), but this rests on only ~10 overlap quarters,
  so it's directional at best — reported as a caveat, not a precise estimate.

## Data sources

MoSPI (GDP, IIP, GVA), RBI (repo rate, CPI, M3, INR/USD reference rates, WSS bank credit),
CGA / Union Budget (fiscal deficit), and FRED (Brent crude). See `docs/data_dictionary.md`
for per-variable detail and `docs/decisions.md` for methodology choices.
