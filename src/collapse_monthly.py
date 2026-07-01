"""
collapse_monthly.py
-------------------
Reusable functions for squashing a monthly or fortnightly series down to ONE
value per fiscal quarter. `build_composite.py` imports these so the collapse
logic lives in one tested place.

Two collapse rules cover every series we use:
    * FLOWS / RATES  (repo, CPI, IIP, FX, crude)  -> quarterly MEAN
    * STOCKS         (M3)                          -> quarter-END value

Can also be run as a quick CLI for ad-hoc collapsing:
    python src/collapse_monthly.py <file.csv> <date_col> <value_col> [mean|qend]
"""

import pandas as pd

try:
    from utils import fy_quarter, order_key      # when run as a script (src/ on path)
except ImportError:
    from .utils import fy_quarter, order_key      # when imported as a package


def add_fy_quarter(df, date_col):
    """Return a copy of df with a clean datetime `date_col` and an FY_Quarter column."""
    out = df.copy()
    out[date_col] = pd.to_datetime(out[date_col], errors="coerce")
    out = out.dropna(subset=[date_col])
    out["FY_Quarter"] = [fy_quarter(d.year, d.month) for d in out[date_col]]
    return out


def collapse_mean(df, date_col, value_col, out_name=None):
    """Quarterly MEAN of a flow/rate series -> DataFrame[FY_Quarter, out_name]."""
    out_name = out_name or value_col
    d = add_fy_quarter(df, date_col)
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
    return (d.groupby("FY_Quarter", as_index=False)[value_col]
              .mean().rename(columns={value_col: out_name}))


def collapse_qtr_end(df, date_col, value_col, out_name=None):
    """Quarter-END value of a stock series (last observation in each quarter)."""
    out_name = out_name or value_col
    d = add_fy_quarter(df, date_col)
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
    d = d.dropna(subset=[value_col]).sort_values(date_col)
    return (d.groupby("FY_Quarter", as_index=False).last()[["FY_Quarter", value_col]]
              .rename(columns={value_col: out_name}))


def collapse_agg(df, date_col, value_col, aggs):
    """General collapse: `aggs` is a dict {out_name: pandas_agg}, e.g.
       {'INR_USD': 'mean', 'INR_USD_vol': 'std'} -> one column per agg."""
    d = add_fy_quarter(df, date_col)
    d[value_col] = pd.to_numeric(d[value_col], errors="coerce")
    g = d.groupby("FY_Quarter")[value_col].agg(list(aggs.values()))
    g.columns = list(aggs.keys())
    return g.reset_index()


if __name__ == "__main__":
    import sys
    path, dcol, vcol = sys.argv[1], sys.argv[2], sys.argv[3]
    how = sys.argv[4] if len(sys.argv) > 4 else "mean"
    frame = pd.read_csv(path)
    res = collapse_qtr_end(frame, dcol, vcol) if how == "qend" else collapse_mean(frame, dcol, vcol)
    res = res.sort_values("FY_Quarter", key=lambda s: s.map(order_key))
    print(res.to_string(index=False))
