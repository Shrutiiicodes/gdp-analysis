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
  answers *what drives GDP* (backtested); SARIMA answers *what's next quarter* (forecast).
- **"Top driver" is a consensus**, not one method: Lasso + permutation + SHAP averaged.

## Forecasting FY2026-27
- **SARIMA, not regression.** Future quarters have no exogenous data (CPI/IIP/etc. don't
  exist yet), so the forecast uses the series' own history.
- **COVID as a known exogenous dummy.** The 2020-21 swings distorted the first SARIMA fit
  (implausible 2.5% point); a COVID dummy (1 in FY21, 0 elsewhere *and* in the future)
  stabilized it (AIC ≈306→282) to a sensible ~7%/~6% with an 80% interval.

## Known limitations
- Spliced target has a small discontinuity at the 2025-26 Q2/Q3 base join.
- `GDP_proxy_old` (ratios' denominator) omits CIS/Valuables/Discrepancies — documented proxy.
- Base-sensitivity uses only ~10 overlap quarters → directional.
- Re-estimate once MoSPI releases the full 2022-23 back-series (expected Dec 2026).