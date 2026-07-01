"""
make_repo_rate.py
-----------------
Turns the RAW repo-rate changelog (event-based: a row each time RBI changed the
rate) into the two interim files the composite needs:
    data/interim/repo_rate_monthly_2011_2026.csv   (month-end + day-weighted month avg)
    data/interim/repo_rate_quarterly_FY.csv        (quarter avg + quarter-end)

Run from the project root:
    python src/make_repo_rate.py

Why this exists: the repo rate is a step function that changes on arbitrary dates.
To use it at monthly/quarterly frequency we expand it to a daily series, then
average. The day-weighted monthly average correctly handles months where the rate
changed mid-month.
"""

from pathlib import Path
import pandas as pd

try:
    from utils import order_key, fy_quarter
except ImportError:
    from .utils import order_key, fy_quarter

DATA = Path("data")
RAW = DATA / "raw" / "repo"
INTERIM = DATA / "interim"
INTERIM.mkdir(parents=True, exist_ok=True)


def build():
    # 1) read the changelog (EffectiveDate, Repo_Rate_pct)
    src = RAW / "repo_rate_changelog.csv"
    if not src.exists():                       # tolerate alt location
        hits = list(Path("data").rglob("repo_rate_changelog.csv"))
        if not hits:
            raise FileNotFoundError("repo_rate_changelog.csv not found under data/")
        src = hits[0]
    log = pd.read_csv(src)
    log["EffectiveDate"] = pd.to_datetime(log["EffectiveDate"], format="%d-%m-%Y", errors="coerce")
    log = log.dropna().sort_values("EffectiveDate").reset_index(drop=True)

    # 2) expand to a DAILY step series from first change to end-2025-26 (Mar 2026)
    start = log["EffectiveDate"].iloc[0]
    end = pd.Timestamp("2026-03-31")
    days = pd.DataFrame({"date": pd.date_range(start, end, freq="D")})
    days = days.merge(log.rename(columns={"EffectiveDate": "date"}), on="date", how="left")
    days["Repo_Rate_pct"] = days["Repo_Rate_pct"].ffill()   # carry each rate until the next change

    # 3) MONTHLY: month-end value + day-weighted month average
    days["ym"] = days["date"].dt.to_period("M")
    monthly = days.groupby("ym").agg(
        Repo_MonthEnd=("Repo_Rate_pct", "last"),
        Repo_MonthAvg=("Repo_Rate_pct", "mean")).reset_index()
    monthly["Date"] = monthly["ym"].astype(str)
    monthly["FY_Quarter"] = [fy_quarter(p.year, p.month) for p in monthly["ym"]]
    monthly = monthly[["Date", "FY_Quarter", "Repo_MonthEnd", "Repo_MonthAvg"]]
    monthly = monthly[monthly["Date"] >= "2011-01"]          # match the published window
    monthly.to_csv(INTERIM / "repo_rate_monthly_2011_2026.csv", index=False)

    # 4) QUARTERLY: avg of monthly averages + quarter-end value
    monthly["_k"] = monthly["FY_Quarter"].map(order_key)
    monthly = monthly.sort_values(["_k", "Date"])
    quarterly = monthly.groupby("FY_Quarter", as_index=False).agg(
        Repo_QtrAvg=("Repo_MonthAvg", "mean"),
        Repo_QtrEnd=("Repo_MonthEnd", "last"))
    quarterly = quarterly.sort_values("FY_Quarter", key=lambda s: s.map(order_key))
    quarterly.to_csv(INTERIM / "repo_rate_quarterly_FY.csv", index=False)

    print(f"Wrote {INTERIM/'repo_rate_monthly_2011_2026.csv'}  ({len(monthly)} months)")
    print(f"Wrote {INTERIM/'repo_rate_quarterly_FY.csv'}  ({len(quarterly)} quarters)")
    print(quarterly.head(4).to_string(index=False))


if __name__ == "__main__":
    build()
