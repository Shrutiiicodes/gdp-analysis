"""
gva_sectors.py
--------------
Builds the production-side (GVA) sectoral view that the mentor review asked for:
    "break down GVA across Agriculture, Industry (Manufacturing, Mining,
     Utilities, Construction) and Services (Trade, Financials, Real Estate)."

INPUT (download once -- the sandbox can't reach RBI DBIE / MoSPI):
    RBI DBIE  ->  https://data.rbi.org.in
    Path      :  National Account Statistics -> "Quarterly Estimates of GVA at
                 Basic Prices by Economic Activity" -> AT CONSTANT PRICES (Rs crore).
                 (Levels, not growth rates -- levels let us derive BOTH sector
                  growth AND each sector's contribution to aggregate GVA growth.)
    Export    :  Excel/CSV, all available quarters.
    Save as   :  data/raw/gva/gva_by_activity_quarterly.(xlsx|csv)

    The eight sub-sectors are folded into three headline sectors:
        Agriculture = Agriculture, Forestry & Fishing
        Industry    = Mining + Manufacturing + Utilities + Construction
        Services    = Trade/Transport/Comm + Financial/Real Estate + Public Admin

OUTPUT (outputs/figures/ + a tidy CSV in data/interim/):
    05a_gva_sector_growth.png       sector YoY growth, quarterly (line)
    05b_gva_contributions.png       contribution to aggregate GVA growth (stacked)
    05c_gva_shares_annual.png       sector shares of GVA over FY (stacked area)
    gva_sectoral_quarterly.csv      tidy table for the report / appendix

Run:  python src/gva_sectors.py
"""

import os
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings("ignore")

try:
    from utils import fy_quarter, order_key
except ImportError:
    from .utils import fy_quarter, order_key

sns.set_theme(style="whitegrid", context="notebook")
plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 150,
                     "savefig.bbox": "tight", "axes.titleweight": "bold"})

# --- map raw sub-sector names (fuzzy) to the three headline sectors -----------
SUBSECTOR_TO_HEAD = [
    ("agri",            "Agriculture"),
    ("forest",          "Agriculture"),
    ("fish",            "Agriculture"),
    ("mining",          "Industry"),
    ("quarry",          "Industry"),
    ("manufactur",      "Industry"),
    ("electric",        "Industry"),
    ("utility",         "Industry"),
    ("gas",             "Industry"),
    ("water",           "Industry"),
    ("construction",    "Industry"),
    ("trade",           "Services"),
    ("hotel",           "Services"),
    ("transport",       "Services"),
    ("communication",   "Services"),
    ("broadcast",       "Services"),
    ("financial",       "Services"),
    ("real estate",     "Services"),
    ("professional",    "Services"),
    ("public admin",    "Services"),
    ("defence",         "Services"),
    ("other services",  "Services"),
]
HEAD_ORDER = ["Agriculture", "Industry", "Services"]


def _project() -> Path:
    p = Path(os.environ.get("GDP_PROJECT", "")).expanduser()
    if (p / "data").is_dir():
        return p
    here = Path.cwd()
    for cand in (here, *here.parents):
        if (cand / "data" / "processed").is_dir():
            return cand
    return here


def _head_of(colname: str):
    c = str(colname).lower()
    for key, head in SUBSECTOR_TO_HEAD:
        if key in c:
            return head
    return None


def _norm_quarter(label) -> str:
    """Accept 'Q1:2012-13', '2012-13 Q1', 'Q1 2012-13', 'Jun 2012' -> FY-quarter label."""
    s = str(label).strip()
    m = re.search(r"(20\d\d)[-/](\d\d).*?Q\s*([1-4])", s) or \
        re.search(r"Q\s*([1-4]).*?(20\d\d)[-/](\d\d)", s)
    if m:
        g = m.groups()
        if g[0].startswith("20"):   # year first
            return f"{g[0]}-{g[1]} Q{g[2]}"
        return f"{g[1]}-{g[2]} Q{g[0]}"
    # fall back: try a parseable date
    try:
        d = pd.to_datetime(s, errors="raise")
        return fy_quarter(d.year, d.month)
    except Exception:
        return s


def load_gva(proj: Path) -> pd.DataFrame:
    """Return a quarterly frame indexed by FY_Quarter with one column per
    headline sector (constant-price GVA levels, Rs crore)."""
    folder = proj / "data" / "raw" / "gva"
    # Only the RAW DBIE export (xlsx/xls). Never a processed .csv, and never our
    # own tidy output, so a stray file can't be picked up by mistake.
    cands = sorted(p for p in folder.glob("*.xls*")
                   if "sectoral" not in p.name.lower())
    preferred = [p for p in cands if p.name == "gva_by_activity_quarterly.xlsx"]
    hits = preferred or cands
    if not hits:
        raise FileNotFoundError(
            f"No raw DBIE .xlsx in {folder}. Save the DBIE 'Quarterly Estimates "
            f"of GVA at Basic Prices (Constant Prices)' export there as "
            f"gva_by_activity_quarterly.xlsx (not a .csv).")
    f = hits[0]
    print(f"reading: {f.name}")
    raw = pd.read_excel(f, header=None)

    # guard: reject an already-folded file (has our output columns, not sub-sectors)
    flat = raw.astype(str).values.ravel()
    if any("_YoY" in str(v) or "_contrib" in str(v) for v in flat):
        raise ValueError(
            f"{f.name} looks like a PROCESSED file (contains _YoY/_contrib "
            f"columns), not the raw DBIE export. Point me at the raw download.")

    # find the header row = the row whose cells map to the most sub-sectors
    score = raw.apply(lambda r: sum(_head_of(v) is not None for v in r), axis=1)
    hdr = int(score.idxmax())
    data = raw.iloc[hdr:].reset_index(drop=True)
    data.columns = data.iloc[0]
    data = data.iloc[1:].reset_index(drop=True)

    # Locate the FY_Quarter labels. Two common layouts:
    #   (a) one combined column: '2012-13 Q1'
    #   (b) split columns: a sparse/merged YEAR col ('2011-12', blank on Q2-Q4)
    #       plus a separate QUARTER col ('Q1'..'Q4').  <-- the RBI DBIE export
    def _is_year(s):   return s.astype(str).str.contains(r"20\d\d-\d\d", na=False)
    def _is_qtr(s):    return s.astype(str).str.strip().str.fullmatch(r"Q[1-4]").fillna(False)

    qtr_cols  = [c for c in data.columns if _is_qtr(data[c]).mean()  > 0.5]
    year_cols = [c for c in data.columns if _is_year(data[c]).mean() > 0.15]

    if qtr_cols and year_cols:                      # layout (b): combine them
        yr = data[year_cols[0]].astype(str).str.extract(r"(20\d\d-\d\d)")[0].ffill()
        qt = data[qtr_cols[0]].astype(str).str.extract(r"(Q[1-4])")[0]
        data["FY_Quarter"] = (yr.str.strip() + " " + qt.str.strip())
    else:                                           # layout (a): single label col
        data["FY_Quarter"] = data[data.columns[0]].map(_norm_quarter)

    data = data[data["FY_Quarter"].str.contains(r"20\d\d-\d\d Q[1-4]", na=False)]

    # collapse sub-sector columns into the three heads
    out = pd.DataFrame({"FY_Quarter": data["FY_Quarter"]})
    empty = []
    for head in HEAD_ORDER:
        cols = [c for c in data.columns if _head_of(c) == head]
        print(f"  {head:12s} <- {len(cols)} column(s): {[str(c)[:35] for c in cols]}")
        if not cols:
            empty.append(head)
        vals = data[cols].apply(pd.to_numeric, errors="coerce").sum(axis=1)
        out[head] = vals
    if empty:
        print("\n!! No columns matched for:", empty)
        print("!! Columns the parser actually sees in your file:")
        for c in data.columns:
            print("     -", repr(c))
        print("!! -> the header text differs from the DBIE default; tell me the "
              "names above and I'll widen the matcher.\n")
    out["GVA_total"] = out[HEAD_ORDER].sum(axis=1)
    out = (out.groupby("FY_Quarter", as_index=False).last()
              .sort_values("FY_Quarter", key=lambda s: s.map(order_key))
              .reset_index(drop=True))
    return out


def build(proj: Path):
    gva = load_gva(proj)
    figs = proj / "outputs" / "figures"; figs.mkdir(parents=True, exist_ok=True)

    # --- sector YoY growth + contribution to aggregate GVA growth -------------
    for s in HEAD_ORDER + ["GVA_total"]:
        gva[f"{s}_YoY"] = gva[s].pct_change(4) * 100
    # contribution_s = (level_s(t) - level_s(t-4)) / total(t-4) * 100
    for s in HEAD_ORDER:
        gva[f"{s}_contrib"] = (gva[s] - gva[s].shift(4)) / gva["GVA_total"].shift(4) * 100

    tidy = gva.dropna(subset=["GVA_total_YoY"]).copy()
    palette = {"Agriculture": "#4C9F70", "Industry": "#C1666B", "Services": "#4D7EA8"}

    # (a) sector growth lines
    fig, ax = plt.subplots(figsize=(13, 5))
    for s in HEAD_ORDER:
        ax.plot(tidy["FY_Quarter"], tidy[f"{s}_YoY"], label=s, color=palette[s], lw=1.8)
    ax.plot(tidy["FY_Quarter"], tidy["GVA_total_YoY"], "k--", lw=1.3, label="Total GVA")
    ax.axhline(0, color="k", lw=.6); ax.set_ylabel("YoY growth (%)"); ax.set_xlabel("")
    ax.set_xticks(range(0, len(tidy), 2)); ax.set_xticklabels(tidy["FY_Quarter"][::2], rotation=90, fontsize=7)
    ax.legend(frameon=False, ncol=4, fontsize=9); ax.set_title("Sectoral GVA growth (Agriculture / Industry / Services)")
    fig.savefig(figs / "05a_gva_sector_growth.png"); plt.close(fig)

    # (b) contribution to aggregate GVA growth (stacked, mirrors notebook 03)
    fig, ax = plt.subplots(figsize=(14, 6))
    tidy.set_index("FY_Quarter")[[f"{s}_contrib" for s in HEAD_ORDER]].plot(
        kind="bar", stacked=True, ax=ax, width=.85,
        color=[palette[s] for s in HEAD_ORDER])
    ax.plot(range(len(tidy)), tidy["GVA_total_YoY"].values, "k-o", ms=3, lw=1.3, label="Total GVA growth")
    ax.axhline(0, color="k", lw=.6); ax.set_ylabel("contribution to GVA growth (pp)"); ax.set_xlabel("")
    ax.set_xticklabels(tidy["FY_Quarter"], rotation=90, fontsize=7)
    ax.legend([s for s in HEAD_ORDER] + ["Total GVA growth"], frameon=False, ncol=4, fontsize=8)
    ax.set_title("Sectoral contribution to quarterly GVA growth")
    fig.savefig(figs / "05b_gva_contributions.png"); plt.close(fig)

    # (c) annual sector shares (structural backdrop)
    gva["FY"] = gva["FY_Quarter"].str[:7]
    ann = gva.groupby("FY")[HEAD_ORDER].sum()
    shares = ann.div(ann.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.stackplot(range(len(shares)), *[shares[s] for s in HEAD_ORDER],
                 labels=HEAD_ORDER, colors=[palette[s] for s in HEAD_ORDER], alpha=.9)
    ax.set_xticks(range(len(shares))); ax.set_xticklabels(shares.index, rotation=90, fontsize=7)
    ax.set_ylabel("share of GVA (%)"); ax.set_xlabel(""); ax.set_ylim(0, 100)
    ax.legend(frameon=False, ncol=3, loc="lower center"); ax.set_title("Sector shares of GVA over time")
    fig.savefig(figs / "05c_gva_shares_annual.png"); plt.close(fig)

    tidy_path = proj / "data" / "interim" / "gva_sectoral_quarterly.csv"
    tidy.to_csv(tidy_path, index=False)
    print("saved figures 05a/05b/05c and", tidy_path.name)
    print("\nLatest sector growth (YoY %):")
    print(tidy[["FY_Quarter", "Agriculture_YoY", "Industry_YoY",
                "Services_YoY", "GVA_total_YoY"]].tail(6).round(2).to_string(index=False))
    return tidy


if __name__ == "__main__":
    build(_project())