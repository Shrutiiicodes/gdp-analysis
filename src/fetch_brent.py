"""
fetch_brent.py
--------------
The one source with a stable machine-readable endpoint: FRED's monthly Brent
series (MCOILBRENTEU). Downloads the CSV and rewrites it in the DD-MM-YYYY
layout that data/raw/crude/MCOILBRENTEU.csv already uses, so build_composite.py
needs no change. Every other raw file is a manual download (see README).

Run:  python src/fetch_brent.py
"""

import io
import urllib.request

import pandas as pd

try:
    from utils import find_project
except ImportError:
    from .utils import find_project

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MCOILBRENTEU"


def to_raw_format(csv_text: str) -> pd.DataFrame:
    """FRED CSV text (ISO dates, '.' for missing) -> the repo's raw layout."""
    df = pd.read_csv(io.StringIO(csv_text), na_values=["."]).dropna()
    df["observation_date"] = pd.to_datetime(df["observation_date"]).dt.strftime("%d-%m-%Y")
    df["MCOILBRENTEU"] = df["MCOILBRENTEU"].astype(float)
    return df.reset_index(drop=True)


def main():
    out = find_project() / "data" / "raw" / "crude" / "MCOILBRENTEU.csv"
    with urllib.request.urlopen(URL, timeout=30) as r:
        text = r.read().decode("utf-8")
    df = to_raw_format(text)
    df.to_csv(out, index=False)
    print(f"Wrote {out}  ({len(df)} months, last = {df['observation_date'].iloc[-1]})")


if __name__ == "__main__":
    main()
