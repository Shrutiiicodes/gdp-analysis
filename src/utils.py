"""
utils.py
--------
Small shared helpers used across the pipeline (build_composite.py,
collapse_monthly.py, make_repo_rate.py). Keeping them in one place means the
fiscal-quarter logic is defined exactly once.
"""

from pathlib import Path

# Month name -> month number (used when a source labels months as text)
MONTHS = {"January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
          "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12}


def fy_quarter(year, month):
    """Calendar (year, month) -> Indian fiscal-quarter label, e.g. (2012, 5) -> '2012-13 Q1'.
       Fiscal year runs Apr->Mar. Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar(next yr)."""
    year, month = int(year), int(month)
    if month >= 4:
        fy, q = year, (month - 4) // 3 + 1
    else:
        fy, q = year - 1, 4
    return f"{fy}-{str(fy + 1)[-2:]} Q{q}"


def order_key(fq):
    """Chronological sort key so '2011-12 Q1' < '2011-12 Q2' < ... < '2026-27 Q2'."""
    return int(fq[:4]) * 4 + int(fq[-1])


def fq_to_date(label):
    """FY-quarter label -> the quarter-END Timestamp, e.g. '2011-12 Q1' -> 2011-06-30.
       Handy for plotting on a real time axis."""
    import pandas as pd
    fy, q = int(label[:4]), int(label[-1])
    end_month = {1: 6, 2: 9, 3: 12, 4: 3}[q]
    year = fy if q <= 3 else fy + 1
    return pd.Timestamp(year=year, month=end_month, day=1) + pd.offsets.MonthEnd(0)


def find_one(folder, pattern):
    """Return the single file matching `pattern` (glob) inside `folder`, else raise.
       Lets the pipeline tolerate small filename differences (dots vs underscores, etc.)."""
    hits = sorted(Path(folder).glob(pattern))
    if not hits:
        raise FileNotFoundError(f"No file matching {pattern!r} in {folder}")
    return hits[0]
