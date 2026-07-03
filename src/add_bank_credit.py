import os
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from utils import order_key
    from collapse_monthly import collapse_qtr_end, add_fy_quarter
except ImportError:
    from .utils import order_key
    from .collapse_monthly import collapse_qtr_end, add_fy_quarter


def _project() -> Path:
    p = Path(os.environ.get("GDP_PROJECT", "")).expanduser()
    if (p / "data").is_dir():
        return p
    here = Path.cwd()
    for cand in (here, *here.parents):
        if (cand / "data" / "processed").is_dir():
            return cand
    return here


def _yoy(df_q: pd.DataFrame, level_col: str, out_col: str) -> pd.DataFrame:
    """4-quarter YoY % change on a quarterly-ordered frame."""
    d = df_q.sort_values("FY_Quarter", key=lambda s: s.map(order_key)).copy()
    d[out_col] = d[level_col].pct_change(4) * 100
    return d[["FY_Quarter", out_col]]


def parse_rbi_wss_table4(xlsx_path) -> pd.DataFrame:
    """Extract a clean (Date, BankCredit) frame from the raw RBI WSS Table 4
    export ('Scheduled Commercial Banks - Business in India').

    That file has a multi-row banner: the header sits on row index 5, data
    begins on row index 6, the fortnight date is column 1, and '7 Bank Credit*'
    is column 24. This isolates just those two columns.
    """
    raw = pd.read_excel(xlsx_path, header=None)
    out = pd.DataFrame({
        "Date": pd.to_datetime(raw.iloc[6:, 1], errors="coerce"),
        "BankCredit": pd.to_numeric(raw.iloc[6:, 24], errors="coerce"),
    }).dropna().sort_values("Date")
    return out


def add_credit(master: pd.DataFrame, proj: Path,
               path="data/raw/credit/bank_credit_outstanding.csv",
               date_col="Date", value_col="BankCredit") -> pd.DataFrame:
    f = proj / path
    # Prefer a cleaned CSV; fall back to a raw RBI WSS Table-4 xlsx if present.
    if not f.exists():
        rbi = list((proj / "data" / "raw" / "credit").glob("WSS_Table*.xlsx"))
        if rbi:
            print(f"[info] parsing raw RBI WSS export: {rbi[0].name}")
            parse_rbi_wss_table4(rbi[0]).to_csv(f, index=False)
        else:
            print(f"[skip] bank credit file not found at {f}\n"
                  f"       download per the recipe in this file's docstring.")
            return master
    raw = pd.read_csv(f)
    q = collapse_qtr_end(raw, date_col, value_col, out_name="BankCredit_level")
    yoy = _yoy(q, "BankCredit_level", "BankCredit_YoY")
    return master.merge(yoy, on="FY_Quarter", how="left")


def add_gst(master: pd.DataFrame, proj: Path,
            path="data/raw/gst/gst_collections_monthly.csv",
            date_col="Date", value_col="GST") -> pd.DataFrame:
    f = proj / path
    if not f.exists():
        print(f"[skip] GST file not found at {f} (optional).")
        return master
    raw = add_fy_quarter(pd.read_csv(f), date_col)
    raw[value_col] = pd.to_numeric(raw[value_col], errors="coerce")
    q = (raw.groupby("FY_Quarter", as_index=False)[value_col].sum()   # FLOW -> SUM
            .rename(columns={value_col: "GST_level"}))
    yoy = _yoy(q, "GST_level", "GST_YoY")
    return master.merge(yoy, on="FY_Quarter", how="left")


def main():
    proj = _project()
    mpath = proj / "data" / "processed" / "composite_master_quarterly.csv"
    master = pd.read_csv(mpath)

    before = set(master.columns)
    master = add_credit(master, proj)
    master = add_gst(master, proj)
    added = [c for c in master.columns if c not in before]

    if not added:
        print("\nNothing added. Download the raw file(s) first (see docstring).")
        return

    master.to_csv(mpath, index=False)
    print(f"\nMerged {added} and rewrote {mpath.name}.")

    # Re-run the driver screen including the new proxy/proxies.
    try:
        from driver_screen import run, DEFAULT_FEATURES
    except ImportError:
        from .driver_screen import run, DEFAULT_FEATURES
    table = run(DEFAULT_FEATURES + added)
    print("\nDriver screen WITH new banking proxies:")
    print(table.to_string(index=False))


if __name__ == "__main__":
    main()