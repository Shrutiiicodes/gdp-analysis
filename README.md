# Forecasting India's GDP Growth

An end-to-end pipeline that assembles a quarterly macroeconomic panel for India, explores it,
forecasts real GDP growth, and decomposes what drives it — handling the February 2026 rebasing
of the National Accounts from base year 2011-12 to 2022-23.

## What the project does
1. Collects 12 public macro indicators and combines them into one quarterly master table.
2. Engineers features, prunes redundant ones (correlation + VIF), and tests stationarity.
3. Compares forecasting models under time-aware validation and identifies the top growth drivers.
4. Forecasts GDP growth for FY2026-27 Q1 and Q2 (SARIMA).
5. Decomposes realised growth into demand-side contributions.

## How to run (from the project root, `gdp-analysis/`)
```bash
# 1. preprocessing: regenerate the repo-rate interim files from the raw changelog
python src/make_repo_rate.py
#    (Other interim files — expenditure, GDP contributions, CPI, fiscal deficit — are
#     curated inputs already in data/interim/; see docs/data_provenance.md for sources.)

# 2. assemble the quarterly master table -> data/processed/composite_master_quarterly.csv
python src/build_composite.py

# 3. open the notebooks in order and Run All
#    notebooks/01_eda.ipynb           -> cleaning, EDA, feature selection
#    notebooks/02_forecasting.ipynb   -> models, accuracy, drivers, forecast, saved models
#    notebooks/03_contributions.ipynb -> demand-side decomposition
#    notebooks/04_scenarios.ipynb     -> scenario analysis
```
The notebooks auto-detect the project root (they walk up from the notebook's folder), so
no path editing is needed after cloning. To force a location, set the `GDP_PROJECT`
environment variable. Then use **Kernel -> Restart & Run All**.

Requirements: `pandas numpy scikit-learn statsmodels shap matplotlib seaborn openpyxl joblib`.

## Folder structure
```
gdp-analysis/
  data/raw/        # original downloaded files (gdp, cpi, iip, fx, crude, m3, repo)
  data/interim/    # cleaned intermediate CSVs (repo rates, cpi, expenditure, etc.)
  data/processed/  # composite_master_quarterly.csv  <- the analysis table
  src/
    utils.py            # shared helpers (fiscal-quarter logic, file finding)
    collapse_monthly.py # monthly/fortnightly -> quarterly collapse functions
    make_repo_rate.py   # raw repo changelog -> monthly + quarterly repo files
    build_composite.py  # assembles the master table from all sources
  notebooks/       # 01_eda, 02_forecasting, 03_contributions, 04_scenarios
  outputs/
    figures/       # all charts (PNG)
    forecasts/     # gdp_forecast_FY2026_27.csv
    models/        # saved SARIMAX + best ML model
  docs/            # data_dictionary.md, decisions.md
```

## Key results
- **Best accuracy:** a random-walk baseline (RMSE 0.97); regularized linear models match it to
  within ~0.1 RMSE, so the models' value is interpretability, not a large accuracy gain.
- **Top predictors of growth:** industrial production (IIP) and fixed investment (GFCF), by a
  consensus of Lasso, permutation importance and SHAP.
- **Largest accounting contributor:** private consumption (~3.6 pp average), then investment.
- **Forecast (SARIMA + COVID dummy):** FY2026-27 Q1 ~ 7.1%, Q2 ~ 6.1% (80% interval).
- **Base-year sensitivity:** the driver ranking shifts across the 2011-12 vs 2022-23 base
  (rank-correlation about -0.27 on the overlap) — reported as a caveat.

## Data sources
MoSPI (GDP, IIP), RBI (repo rate, CPI, M3, INR/USD reference rates), CGA / Union Budget
(fiscal deficit), and FRED (Brent crude). See `docs/data_dictionary.md` for per-variable detail
and `docs/decisions.md` for methodology choices.
```
```
