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

**One command** (rebuilds interim files, the master table, the GVA view, executes notebooks 01-05,
runs the tests; stops at the first failure):

```bash
python run_all.py
```

Add `--fetch` to refresh Brent from FRED first. That is the only source with a stable
machine-readable endpoint; every other raw file under `data/raw/` is a manual download from
MoSPI / RBI (see `docs/data_provenance.md`), so a data refresh is: drop the new files in, then
`python run_all.py`. GitHub Actions (`.github/workflows/pipeline.yml`) runs the same command on
every push and, on the 1st of each month, with `--fetch`, committing regenerated outputs.

The individual steps, if you need just one:

```bash
# 1. Regenerate the repo-rate interim files from the raw changelog
python src/make_repo_rate.py
#    (Other interim files — expenditure, GDP contributions, CPI, fiscal deficit — are
#     curated inputs already in data/interim/; see docs/data_provenance.md for sources.)

# 2. Assemble the quarterly master table -> data/processed/composite_master_quarterly.csv
#    (also appends BankCredit_YoY if data/raw/credit/bank_credit_outstanding.csv is present)
python src/build_composite.py

# 3. [Optional] Run the predictive-causality (Granger) driver screen standalone
python src/driver_screen.py

# 4. [Optional] Build the GVA sectoral view
#    (requires data/raw/gva/gva_by_activity_quarterly.xlsx from RBI DBIE)
python src/gva_sectors.py

# 5. Open the notebooks in order and Run All
#    notebooks/01_eda.ipynb           -> cleaning, EDA, feature selection
#    notebooks/02_forecasting.ipynb   -> models, accuracy, drivers, forecast, saved models
#    notebooks/03_contributions.ipynb -> demand-side decomposition
#    notebooks/04_scenarios.ipynb     -> scenario analysis
#    notebooks/05_gva_sectors.ipynb   -> production-side GVA sectoral breakdown

# Regression checks (data invariants + path resolver)
python -m pytest tests -v
# Or execute every notebook headlessly, in order
jupyter nbconvert --to notebook --execute --inplace notebooks/0*.ipynb
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
      feature_manifest.csv               <- per-column role labels (feature/dropped/target)
  src/
    utils.py            # shared helpers (fiscal-quarter logic, file finding)
    collapse_monthly.py # monthly/fortnightly -> quarterly collapse functions
    make_repo_rate.py   # raw repo changelog -> monthly + quarterly repo files
    build_composite.py  # assembles the master table from all sources
    add_bank_credit.py  # optional BankCredit_YoY / GST_YoY, called by build_composite.py
    driver_screen.py    # Granger-causality / predictive-causality screen
    gva_sectors.py      # production-side GVA sectoral builder (Agriculture/Industry/Services)
  notebooks/
    01_eda.ipynb            # cleaning, EDA, feature selection
    02_forecasting.ipynb    # models, accuracy, drivers, forecast
    03_contributions.ipynb  # demand-side decomposition
    04_scenarios.ipynb      # scenario analysis
    05_gva_sectors.ipynb    # production-side GVA sectoral breakdown
  outputs/
    figures/       # all charts (PNG): 01a-d_* (EDA), 02a-e_*, 03b-e_*, 04a/b_*, 05a-c_*
    forecasts/     # gdp_forecast_FY2026_27.csv
    models/        # saved SARIMAX (.pkl) + best ML model (.joblib)
  docs/
    data_dictionary.md   # per-column documentation for composite_master_quarterly.csv
    data_provenance.md   # source and reproducibility notes for interim files
    decisions.md         # methodology choices and rationale
```

## Key results

- **Best accuracy:** on the 8-quarter holdout the random-walk baseline (RMSE 0.97) is not
  beaten; Ridge is within 0.06. Under 5-fold expanding-window CV every model is far worse in
  absolute terms (Ridge ≈ 3.3) but Ridge does beat the same-fold naive baseline (≈ 4.4). The
  models' value is interpretability plus a modest, fold-robust edge, not a large accuracy gain.
- **Top predictors of growth:** industrial production (IIP) by a consensus of Lasso,
  permutation importance and SHAP; among external drivers it is followed by the fiscal
  deficit and rupee crude. GFCF ranks high too but is a component of GDP, so it is reported
  separately from the external drivers.
- **Granger-causality screen:** IIP growth is both coincident (r ≈ 0.93) and leading
  (p ≈ 0.005). CPI inflation and Brent are the other Granger-significant series (p < 0.05
  at lag 2). GFCF_YoY is strongly coincident (r ≈ 0.85) but does **not** lead growth
  (p ≈ 0.41): it moves with GDP rather than ahead of it.
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
