# Decisions Log

A record of the choices made in this project and why, so they can be defended
and revisited. Newest decisions at the bottom of each section.

## Data construction
- **One quarterly spine, left-joined.** Every source is collapsed to one value per fiscal
  quarter and joined onto a fixed FY2011-12 Q1 → FY2026-27 Q2 spine with
  `validate="one_to_one"`, so nothing is silently duplicated or dropped.
- **Collapse rules by series type.** Flows/rates (repo, CPI, IIP, FX, Brent) → quarterly
  *mean*; M3 is a *stock* → quarter-*end* value. A single FY-book-closure M3 outlier
  (2026-03-31, ~2× neighbours) is dropped as an artefact.
- **YoY never forward-fills.** Every `pct_change(4)` passes `fill_method=None`. pandas < 3 padded
  NaN levels before differencing, which fabricated YoY values for quarters with no level data
  (caught 2026-09; the tail of the previously committed table was affected). `tests/test_pipeline.py`
  pins the invariant.
- **YoY/growth forms are the modelling features**, not levels — levels are base-specific and
  non-stationary (confirmed by ADF/KPSS in notebook 01).

## Base-year revision (the central issue)
- **Two GDP vintages are carried, not one.** Old 2011-12 base (`*_old`) and new 2022-23 base
  (`*_new`), because MoSPI rebased on 27-Feb-2026.
- **IIP and CPI come from the same MoSPI API.** `fetch_mospi.py` splices bases with one rule — keep the
  older base for every month it covers, take the newer base only after it ends — because YoY rates are
  close to base-invariant. The previously committed IIP file and curated CPI file were reproduced exactly
  (IIP) and to 0.01 pp from 2014 (CPI); the 2012-13 CPI quarters now come from the official 2010 base
  (up to 0.8 pp different) and Apr-May 2020 are unpublished.
- **RBI's DBIE portal is not automated.** It sits behind a session-token gateway (SAP/CIMS) rather than a
  plain HTTP API; scraping it would break on every portal change. M3, FX and bank credit stay manual.
- **New base comes from MoSPI's JSON API, not a press-release spreadsheet.** `src/fetch_mospi.py`
  pulls the 2022-23-base quarterly GDP and expenditure levels (with every back-revision) from
  eSankhyiki; the spine's forecast horizon is derived from the latest quarter in that file, so
  each MoSPI release moves the forecast forward without editing code.
- **Expenditure features are spliced like the target.** `GFCF_YoY`, `Exports_YoY`, `Imports_YoY`,
  `InvestmentRate` and `TradeOpenness` use the old base where it exists and new-base levels after
  2025-26 Q2, so the regression features keep pace with the GDP target.
- **Splicing.** The old quarterly series was discontinued after 2025-26 Q2, so the primary
  target `GDP_growth` uses old-base growth through Q2 and new-base growth for Q3/Q4. Growth
  rates are spliced (not levels), since growth is far more base-comparable than the absolute
  level. A `GDP_growth_source` flag records the provenance. This mirrors MoSPI's own
  back-series method.
- **Base sensitivity is reported, not hidden.** Driver importance is compared across both
  bases on the overlap; the low rank-correlation is flagged as a genuine (if directional,
  n≈10) finding.

## Feature selection
- **Done in EDA (notebook 01), not in the builder.** `build_composite.py` produces the full
  panel; keep/drop decisions live with the evidence (correlation, VIF).
- **Dropped:** redundant levels where a YoY twin exists (`GFCF`, `Exports`, `Imports`,
  `M3_level`, `CrudeINR`); exact aliases (`M3_growth_YoY`); the linear combo `NetExports`;
  and one of each composite-vs-parent perfect pair (`RealRate`/`RealM3_YoY` vs their parents).
  Post-pruning worst VIF fell from ∞ to ~15; residual moderate collinearity is left to
  regularization rather than over-pruning ~55 rows.
- **Leakage excluded.** The `c_*` contribution columns are an accounting identity summing to
  the target; used only in the descriptive decomposition (notebook 03), never as predictors.

## Modelling
- **Small-sample discipline.** ~55 quarterly rows → prefer simple, regularized, interpretable
  models; time-aware validation (fixed holdout + expanding-window CV), never random k-fold.
- **Baselines are mandatory.** naive(t-1) and seasonal-naive; the random walk is the bar.
- **Explanation vs forecasting are separated.** Regression/ML on contemporaneous features
  answers *what drives GDP* (backtested); SARIMAX answers *what's next quarter* (forecast).
- **"Top driver" is a consensus**, not one method: Lasso + permutation + SHAP averaged.

## Predictive-causality screen (`src/driver_screen.py`)
- **Granger F-test added as a fourth pillar.** The mentor review flagged "causal factor
  analysis vs. mere correlation." `driver_screen.py` runs an ADF-then-Granger pipeline over
  lags 1–4 for every candidate feature, reporting `corr_t` (contemporaneous), `bestLag`/`corr_lag`
  (peak lagged correlation), and `granger_p` (minimum SSR F-test p-value).
- **Interpretation is explicit.** High `corr_t` + high `granger_p` = coincident indicator
  (moves *with* GDP, doesn't *lead* it). This distinction is stated in the script header and
  reported in the notebook.
- **Caveats stated, not hidden.** ~56 quarters is small; best-of-lags + multiple features
  inflate false positives. Granger = predictive precedence, not proof of a structural causal
  mechanism. These caveats are documented in the driver_screen.py docstring.
- **Non-stationary features are first-differenced** before the Granger test (ADF p > 0.10
  threshold), so the test is always run on a stationary input.
- **Optional extension:** `build_composite.py` calls `add_bank_credit.add_credit`/`add_gst`, so
  `BankCredit_YoY` (and `GST_YoY` when its file exists) are part of the master table; notebook 03
  screens them alongside the core features.

## Forecasting FY2026-27
- **SARIMAX, not regression.** Future quarters have no *unknown* exogenous data (CPI/IIP/etc.
  don't exist yet), so the forecast uses the series' own history plus a deterministic COVID
  dummy (known 0 ahead) — technically SARIMAX, not pure SARIMA.
- **COVID as a known exogenous dummy.** The 2020-21 swings distorted the first SARIMAX fit
  (implausible 2.5% point); a COVID dummy (1 in FY21, 0 elsewhere *and* in the future)
  stabilized it (AIC ≈306→282) to a sensible ~7%/~6% with an 80% interval.

## GVA sectoral view (`src/gva_sectors.py`, notebook 05)
- **Production-side added as a complement to the demand-side story.** Notebook 03 decomposes
  GDP growth into expenditure contributions (PFCE, GFCE, GFCF, NetExports). Notebook 05 adds
  the supply-side breakdown: Agriculture, Industry (Mining + Manufacturing + Utilities +
  Construction), and Services — the three-sector grouping standard in Indian NAS commentary.
- **Source: RBI DBIE raw export, not a derived file.** The script reads the raw DBIE xlsx
  directly; a fuzzy keyword matcher maps sub-sector column names to the three headline sectors,
  making it robust to minor label changes across DBIE vintages.
- **Two output types.** Growth rates (`*_YoY`) answer *how fast each sector grew*;
  contributions (`*_contrib`) answer *how much each sector contributed to aggregate GVA growth*
  — the same accounting logic as the demand-side decomposition in notebook 03.
- **Annual shares** (figure 05c) provide the structural backdrop: Services dominates (~55%),
  and the share trend is relevant for interpreting why GDP growth has become increasingly
  Services-led.
- **Not merged into the composite master.** GVA sectoral data lives in its own interim CSV
  (`gva_sectoral_quarterly.csv`) rather than being appended to `composite_master_quarterly.csv`,
  because the GVA sub-sector columns would introduce leakage risk (they are components of, and
  co-determined with, GDP growth) and the raw data source is optional (requires a separate DBIE
  download).

## Automation (`run_all.py`, `.github/workflows/pipeline.yml`)
- **One entry point.** `run_all.py` runs interim builders, the master table, the GVA view, the five
  notebooks headlessly (`nbconvert --execute --inplace`) and the tests, stopping at the first failure.
  Notebook outputs, figures, forecasts and models are regenerated from scratch, so committed outputs are
  always the product of the committed code and data.
- **CI on every push** runs `run_all.py` on a clean Ubuntu runner with the pinned `requirements.txt`. A
  notebook that cannot Run All, or a dependency drift that changes results, fails the build. This is the
  guard against the two failures found in the 2026-09 audit (a deleted SHAP cell; pandas 2→3 changing
  `pct_change` and silently fabricating YoY values).
- **Monthly scheduled run with `--fetch`** refreshes Brent from FRED and commits regenerated outputs as
  `github-actions[bot]`. Only Brent is automated because it is the only source with a stable endpoint;
  MoSPI/RBI releases are quarterly manual drops into `data/raw/`.
- **Not automated on purpose:** scraping MoSPI/RBI portals. Their URLs change every release; a scraper
  would break more often than the quarterly manual step it replaces.

## Known limitations
- Spliced target has a small discontinuity at the 2025-26 Q2/Q3 base join.
- `GDP_proxy_old` (ratios' denominator) omits CIS/Valuables/Discrepancies — documented proxy.
- Base-sensitivity uses only 10 overlap quarters → directional (rank-corr moved from -0.27 to 0.08
  when MoSPI back-revised the new series in Aug 2026, which is itself evidence of how fragile it is).
- GVA sectoral contributions use the **2011-12 base** DBIE export (2011-12 Q1 → 2025-26 Q2); the
  new-base GVA by industry is available from the same MoSPI API from 2022-23 only, so the sectoral
  view stays on the long old-base series until MoSPI publishes the full back-series.
- Re-estimate once MoSPI releases the full 2022-23 back-series (expected Dec 2026).
- GitHub disables scheduled workflows on public repos after 60 days without repository activity; if the
  monthly job stops, re-enable it from the Actions tab (any push also re-enables it).