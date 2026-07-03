"""
driver_screen.py
----------------
Upgrades the driver story from "mere correlation" to a predictive-causality
screen, addressing the mentor review point:
    "Causal factor analysis vs. mere correlation."

For every candidate feature it reports, against the spliced GDP_growth target:
    * corr_t      contemporaneous correlation (same quarter)
    * bestLag     lag (in quarters) that maximises |correlation|
    * corr_lag    the correlation at that lag
    * stationary  ADF result on the feature (levels are differenced for Granger)
    * granger_p   min p-value of the SSR F-test over lags 1..MAXLAG

Interpretation:
    granger_p < 0.05  => the feature's HISTORY helps predict GDP growth beyond
                         GDP's own history ("Granger-causes" / predictive causality).
    High corr_t but high granger_p => COINCIDENT indicator (moves with GDP) that
                         does NOT lead it. This is the correlation-vs-causation nuance.

CAVEATS (state these in the report):
    ~56 quarters is a small sample; pairwise tests + best-of-lags inflate false
    positives (multiple comparisons). Granger = predictive precedence, NOT proof
    of a structural causal mechanism.

Run:  python src/driver_screen.py
"""

import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

from statsmodels.tsa.stattools import adfuller, grangercausalitytests


# --- project root auto-resolve (same pattern as the notebooks) ---------------
def find_project() -> Path:
    p = Path(os.environ.get("GDP_PROJECT", "")).expanduser()
    if (p / "data").is_dir():
        return p
    here = Path.cwd()
    for cand in (here, *here.parents):
        if (cand / "data" / "processed").is_dir():
            return cand
    return here


# Default feature set = the notebook-02 model features. Add "BankCredit_YoY",
# "GST_YoY" here once those series are merged into the composite master.
DEFAULT_FEATURES = [
    "IIP_growth", "GFCF_YoY", "Imports_YoY", "Exports_YoY", "InvestmentRate",
    "FiscalDeficit_pct_GDP", "CrudeINR_YoY", "Brent_USD", "TradeOpenness",
    "Repo_QtrAvg", "M3_level_YoY", "CPI_Inflation",
]

MAXLAG = 4


def _adf_p(s: pd.Series) -> float:
    s = s.dropna()
    try:
        return adfuller(s, autolag="AIC")[1]
    except Exception:
        return np.nan


def _best_lag_corr(x: pd.Series, y: pd.Series, maxlag: int = MAXLAG):
    best = (0, 0.0)
    for L in range(0, maxlag + 1):
        c = x.shift(L).corr(y)
        if pd.notna(c) and abs(c) > abs(best[1]):
            best = (L, c)
    return best


def _granger_min_p(x: pd.Series, y: pd.Series, maxlag: int = MAXLAG):
    d = pd.concat([y, x], axis=1).dropna()
    if len(d) < 20:
        return np.nan, np.nan
    xx = d.iloc[:, 1]
    if _adf_p(xx) > 0.10:          # non-stationary level -> difference it
        xx = xx.diff()
    dd = pd.concat([d.iloc[:, 0], xx], axis=1).dropna()
    dd.columns = ["y", "x"]
    best_lag, best_p = np.nan, 1.0
    for L in range(1, maxlag + 1):
        try:
            res = grangercausalitytests(dd, maxlag=[L], verbose=False)
            p = res[L][0]["ssr_ftest"][1]
            if p < best_p:
                best_lag, best_p = L, p
        except Exception:
            pass
    return best_lag, best_p


def run(features=None) -> pd.DataFrame:
    proj = find_project()
    df = pd.read_csv(proj / "data" / "processed" / "composite_master_quarterly.csv")
    u = df[df["GDP_growth"].notna()].reset_index(drop=True)
    y = u["GDP_growth"]

    feats = [f for f in (features or DEFAULT_FEATURES) if f in u.columns]
    rows = []
    for f in feats:
        x = u[f]
        L, c = _best_lag_corr(x, y)
        gl, gp = _granger_min_p(x, y)
        rows.append([
            f, round(x.corr(y), 2), L, round(c, 2),
            "yes" if _adf_p(x) < 0.10 else "no (diff)",
            gl, round(gp, 3) if pd.notna(gp) else np.nan,
        ])
    out = pd.DataFrame(
        rows,
        columns=["feature", "corr_t", "bestLag", "corr_lag",
                 "stationary", "granger_lag", "granger_p"],
    ).sort_values("granger_p").reset_index(drop=True)
    return out


if __name__ == "__main__":
    table = run()
    print(f"Predictive-causality screen (Granger F-test), lags 1..{MAXLAG}")
    print(table.to_string(index=False))
    sig = table.loc[table["granger_p"] < 0.05, "feature"].tolist()
    print("\nGranger-significant (p<0.05):", sig)
    print("Reading: high corr_t + high granger_p => coincident, not leading.")