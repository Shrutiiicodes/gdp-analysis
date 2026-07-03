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
- **YoY/growth forms are the modelling features**, not levels — levels are base-specific and
  non-stationary (confirmed by ADF/KPSS in notebook 01).

## Base-year revision (the central issue)
- **Two GDP vintages are carried, not one.** Old 2011-12 base (`*_old`) and new 2022-23 base
  (`*_new`), because MoSPI rebased on 27-Feb-2026.
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
- **Optional extension:** `add_bank_credit.py` appends `BankCredit_YoY` (and optionally
  `GST_YoY`) to the master CSV, and then calls `driver_screen.run()` automatically so the
  new proxies are screened alongside the core features.

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

## Known limitations
- Spliced target has a small discontinuity at the 2025-26 Q2/Q3 base join.
- `GDP_proxy_old` (ratios' denominator) omits CIS/Valuables/Discrepancies — documented proxy.
- Base-sensitivity uses only ~10 overlap quarters → directional.
- GVA sectoral contributions use the **2022-23 base** DBIE export; the old-base breakdown is
  not separately tracked (consistent with the GVA series available on DBIE at time of writing).
- Re-estimate once MoSPI releases the full 2022-23 back-series (expected Dec 2026).