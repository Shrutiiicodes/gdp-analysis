"""
build_composite.py
Builds ONE quarterly master table from all the separate data files and writes it
to data/processed/composite_master_quarterly.{csv,xlsx}.

Pipeline:
    1) SPINE      - empty skeleton: every quarter 2011-12 Q1 .. 2025-26 Q4
    2) COLLAPSE   - squash monthly/fortnightly files to ONE number per quarter
    3) JOIN       - glue each file's column onto the spine on FY_Quarter
    4) BASE-YEAR  - attach BOTH GDP vintages (old 2011-12 base + new 2022-23 base)
    5) FEATURES   - derive economically-meaningful features (no dropping here;
                    feature selection / collinearity pruning happens in EDA)

WHY THE BASE-YEAR STAGE MATTERS
    On 27-Feb-2026 MoSPI rebased GDP from base 2011-12 -> 2022-23. We have BOTH
    series on disk, so we carry both targets through the panel:
       GDP_growth_old   (2011-12 base)  <- base-consistent source; covers most of the
                                            series (through 2025-26 Q2)
        GDP_growth_new   (2022-23 base)  <- new-base growth; supplies the post-rebasing
                                            tail AND drives the base-sensitivity story
    These are spliced into ONE continuous column, `GDP_growth`, which is the actual
    modelling / forecasting target downstream. Every row also carries a
    `base_year_target` label and a `GDP_growth_source` tag for provenance.

NOTE ON FILE PATHS
    Filenames are matched with glob patterns, so this works whether your GDP files
    are named ...05.06.2026.xlsx or ...05_06_2026.xlsx, etc. If a file moves, only
    the glob pattern needs touching.
"""

import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# Shared helpers live in utils.py / collapse_monthly.py (run as `python src/build_composite.py`
# so that src/ is on the import path).
try:
    from utils import MONTHS, fy_quarter, order_key, find_one
    from collapse_monthly import collapse_mean, collapse_qtr_end, collapse_agg
except ImportError:
    from .utils import MONTHS, fy_quarter, order_key, find_one
    from .collapse_monthly import collapse_mean, collapse_qtr_end, collapse_agg

DATA    = Path("data")
INTERIM = DATA / "interim"
RAW     = DATA / "raw"
OUT     = DATA / "processed"
OUT.mkdir(parents=True, exist_ok=True)

# 1) SPINE
spine_labels = [f"{y}-{str(y+1)[-2:]} Q{q}" for y in range(2011, 2026) for q in range(1, 5)]
spine_labels += ["2026-27 Q1", "2026-27 Q2"]   # forecast horizon (no data yet; target stays NaN)
spine = pd.DataFrame({"FY_Quarter": spine_labels})

# 2a) FILES ALREADY QUARTERLY (interim/) -- select the columns we want
gdp_old = pd.read_csv(INTERIM / "gdp_growth_contributions_quarterly.csv")[
    ["FY_Quarter", "GDP_growth_pct"]
].rename(columns={"GDP_growth_pct": "GDP_growth_old"})

exp  = pd.read_csv(INTERIM / "expenditure_components_quarterly_oldbase.csv")[
    ["FY_Quarter", "GFCE", "PFCE", "GFCF", "Exports", "Imports", "NetExports"]]
fisc = pd.read_csv(INTERIM / "fiscal_deficit_pct_gdp_quarterly.csv")[
    ["FY_Quarter", "FiscalDeficit_pct_GDP"]]
repo = pd.read_csv(INTERIM / "repo_rate_quarterly_FY.csv")[
    ["FY_Quarter", "Repo_QtrAvg"]]

cpi_file = find_one(INTERIM, "CPI_Combined_2012base_monthly_clean*.csv")
cpi = pd.read_csv(cpi_file)
cpi_q = (cpi.groupby("FY_Quarter", as_index=False)["CPI_Combined_Inflation_YoY_pct"]
            .mean().rename(columns={"CPI_Combined_Inflation_YoY_pct": "CPI_Inflation"}))

# 2b) COLLAPSE the raw monthly / fortnightly files

# --- IIP: headline growth, averaged over the quarter
iip = pd.read_excel(find_one(RAW / "iip", "iip_46.xlsx"))
iip["m"] = iip["month"].map(MONTHS)
iip["FY_Quarter"] = [fy_quarter(int(y), int(m)) for y, m in zip(iip["year"], iip["m"])]
iip["growth_rate"] = pd.to_numeric(iip["growth_rate"], errors="coerce")
iip_q = (iip.groupby("FY_Quarter", as_index=False)["growth_rate"]
            .mean().rename(columns={"growth_rate": "IIP_growth"}))

# --- FX: USD; keep BOTH the quarterly mean AND the within-quarter volatility
fx = pd.read_excel(find_one(RAW / "fx", "Monthly Average Exchange Rates*.xlsx"), skiprows=7)
fx_q = collapse_agg(fx, "Month", "USD", {"INR_USD": "mean", "INR_USD_vol": "std"})

# --- Crude (Brent): quarterly mean USD (dates are DD-MM-YYYY -> parse explicitly first)
cr = pd.read_csv(find_one(RAW / "crude", "MCOILBRENTEU.csv"))
cr["observation_date"] = pd.to_datetime(cr["observation_date"], format="%d-%m-%Y", errors="coerce")
cr_q = collapse_mean(cr, "observation_date", "MCOILBRENTEU", "Brent_USD")

# --- M3: STOCK -> quarter-END value (drop the FY book-closure artefact row first)
m3 = pd.read_excel(find_one(RAW / "m3", "*Sources of Money Stock*.xlsx"),
                   sheet_name="Report 1", skiprows=5)
m3 = m3.rename(columns={"M3 (1+2+3+4-5)": "M3"})[["Date", "M3"]].dropna()
m3["Date"] = pd.to_datetime(m3["Date"], errors="coerce")
m3 = m3.dropna()
m3 = m3[~((m3["Date"].dt.year == 2026) & (m3["Date"].dt.month == 3) & (m3["Date"].dt.day == 31))]
m3_q = collapse_qtr_end(m3, "Date", "M3", "M3_level")

# 2c) BASE-YEAR: parse BOTH GDP statement vintages straight from the raw files
def _statement_colmap(df, year_row, q_row):
    """Map column-index -> 'YYYY-YY Qn' using a ffilled year row + a quarter row.
       The wide MoSPI sheets stack several statements side by side and the year
       sequence restarts; we read only the FIRST (levels) block and stop the moment
       the chronological order goes backwards (i.e. a new block has begun)."""
    years = df.iloc[year_row].ffill()
    qs = df.iloc[q_row]
    out, last_key = {}, -1
    for c in range(1, df.shape[1]):
        y, q = years.iloc[c], qs.iloc[c]
        if pd.isna(y) or pd.isna(q):
            continue
        y, q = str(y).strip(), str(q).strip()
        if not q.startswith("Q"):
            continue
        key = order_key(f"{y} {q}")
        if out and key <= last_key:
            break  # sequence went backwards -> next statement block, stop
        out[c], last_key = f"{y} {q}", key
    return out


# --- OLD 2011-12 base: levels block is row 18 ("5. सकल देशीय उत्पाद"), cols 1..58
old_x = pd.read_excel(find_one(RAW / "gdp", "*28.11.2025*.xlsx*"), sheet_name=0, header=None)
old_map = _statement_colmap(old_x, year_row=3, q_row=4)
gdp_lvl_old = pd.DataFrame(
    {"FY_Quarter": list(old_map.values()),
     "GDP_level_old": [pd.to_numeric(old_x.iloc[18, c], errors="coerce") for c in old_map]}
)

# --- NEW 2022-23 base: GDP level row 17; we COMPUTE growth ourselves (base-consistent)
new_x = pd.read_excel(find_one(RAW / "gdp", "*05.06.2026*.xlsx*"), sheet_name=0, header=None)
new_map = _statement_colmap(new_x, year_row=1, q_row=3)
gdp_new = pd.DataFrame(
    {"FY_Quarter": list(new_map.values()),
     "GDP_level_new": [pd.to_numeric(new_x.iloc[17, c], errors="coerce") for c in new_map]}
).sort_values("FY_Quarter", key=lambda s: s.map(order_key))
gdp_new["GDP_growth_new"] = gdp_new["GDP_level_new"].pct_change(4) * 100


# 3) JOIN -- attach each piece to the spine
panel = spine.copy()
for piece in [gdp_old, exp, fisc, repo, cpi_q, iip_q, fx_q, cr_q, m3_q,
              gdp_lvl_old, gdp_new]:
    panel = panel.merge(piece, on="FY_Quarter", how="left", validate="one_to_one")

panel["_k"] = panel["FY_Quarter"].map(order_key)
panel = panel.sort_values("_k").drop(columns="_k").reset_index(drop=True)

# 5) FEATURES
# Provenance only: which base vintage does this row's GDP level/growth originate from?
# NOTE: the actual training target is the spliced `GDP_growth` built lower down — this
# label is not itself the target.
panel["base_year_target"] = "2011-12"
panel["has_new_base"] = panel["GDP_growth_new"].notna().astype(int)

# YoY of level series -> base-invariant, stationary-ish features
for col in ["GFCF", "Exports", "Imports", "M3_level"]:
    panel[col + "_YoY"] = panel[col].pct_change(4) * 100

# --- macro-meaningful engineered features ---------------------------------
panel["RealRate"]      = panel["Repo_QtrAvg"] - panel["CPI_Inflation"]      # real policy rate
panel["CrudeINR"]      = panel["Brent_USD"] * panel["INR_USD"]             # oil bill in rupees
panel["CrudeINR_YoY"]  = panel["CrudeINR"].pct_change(4) * 100
panel["M3_growth_YoY"] = panel["M3_level_YoY"]                             # alias, readability
panel["RealM3_YoY"]    = panel["M3_level_YoY"] - panel["CPI_Inflation"]    # real money growth

# GDP level proxy (old base) for ratio features.
# True GDP = PFCE+GFCE+GFCF+CIS+Valuables+NetExports+Discrepancies; we only carry
# the big four, so this is a *proxy* (documented as such). Ratios stay informative.
panel["GDP_proxy_old"]  = panel[["PFCE", "GFCE", "GFCF", "NetExports"]].sum(axis=1, min_count=4)
panel["InvestmentRate"] = panel["GFCF"] / panel["GDP_proxy_old"] * 100      # GFCF / GDP
panel["TradeOpenness"]  = (panel["Exports"] + panel["Imports"]) / panel["GDP_proxy_old"] * 100

# --- calendar / regime features -------------------------------------------
panel["Quarter"] = panel["FY_Quarter"].str[-1].astype(int)
for q in (1, 2, 3, 4):                                  # seasonal dummies
    panel[f"Q{q}"] = (panel["Quarter"] == q).astype(int)
panel["COVID"] = panel["FY_Quarter"].isin(                # structural-break flag
    ["2020-21 Q1", "2020-21 Q2", "2020-21 Q3", "2020-21 Q4"]).astype(int)

# base-revision size on the overlap (old vs new growth) -> useful later for the
# base-sensitivity study; it's just a derived column, EDA decides how to use it.
panel["BaseRevision_gap"] = panel["GDP_growth_new"] - panel["GDP_growth_old"]

# --- SPLICED CONTINUOUS TARGET ------------------------------------------------
# The 2011-12 series was DISCONTINUED after the 27-Feb-2026 rebasing, so old-base
# growth ends at 2025-26 Q2. We splice on the new 2022-23-base growth for the
# quarters the old series no longer covers, giving ONE continuous series through
# 2025-26 Q4 (this is the standard "back-series" splice MoSPI itself uses).
panel["GDP_growth"] = panel["GDP_growth_old"]
spliced = panel["GDP_growth"].isna() & panel["GDP_growth_new"].notna()
panel.loc[spliced, "GDP_growth"] = panel.loc[spliced, "GDP_growth_new"]
panel["GDP_growth_source"] = np.where(panel["GDP_growth_old"].notna(), "2011-12 base",
                              np.where(panel["GDP_growth_new"].notna() & panel["GDP_growth_old"].isna(),
                                       "2022-23 base (spliced)", "—"))
# autoregressive features on the CONTINUOUS target (legit: past values, no leakage)
panel["GDP_growth_lag1"] = panel["GDP_growth"].shift(1)
panel["GDP_growth_lag4"] = panel["GDP_growth"].shift(4)

# 6) SAVE + quick report
out_csv = OUT / "composite_master_quarterly.csv"
panel.to_csv(out_csv, index=False)
panel.to_excel(OUT / "composite_master_quarterly.xlsx", index=False)

print(f"Wrote {out_csv}  shape={panel.shape}")
print("\nContinuous target GDP_growth (old 2011-12 spliced with new 2022-23):")
tail = panel[["FY_Quarter", "GDP_growth_old", "GDP_growth_new", "GDP_growth",
              "GDP_growth_source"]].tail(8)
print(tail.to_string(index=False))
print(f"\nGDP_growth non-null: {panel['GDP_growth'].notna().sum()} of {len(panel)} rows")
print("\nMissing values per column (start/tail NaNs are expected):")
print(panel.isna().sum().to_string())
