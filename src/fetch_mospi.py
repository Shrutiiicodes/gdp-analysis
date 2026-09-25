"""
fetch_mospi.py
--------------
Pulls the official 2022-23-base QUARTERLY national accounts (constant prices,
Rs crore) from MoSPI's eSankhyiki JSON API and writes one tidy wide CSV:

    data/raw/gdp/mospi_quarterly_constant_2022-23.csv
    FY_Quarter, GDP, PFCE, GFCE, GFCF, CIS, Valuables, Exports, Imports, NetTaxes

This is the same data the MoSPI press-note statements print, including every
back-revision MoSPI applies to earlier quarters, so build_composite.py reads it
instead of parsing the wide press-release xlsx.

Endpoint discovered from https://esankhyiki.mospi.gov.in/macroindicators?product=nas
(no authentication). The server still uses legacy TLS renegotiation, hence the
ssl option below.

Run:  python src/fetch_mospi.py
"""

import json
import ssl
import urllib.request

import pandas as pd

try:
    from utils import find_project, order_key
except ImportError:
    from .utils import find_project, order_key

API = "https://api.mospi.gov.in/api/nas/getNASData"
BASE_YEAR = "2022-23"
INDICATORS = {  # eSankhyiki quarter_indicator codes -> our column names
    5: "GDP", 10: "PFCE", 11: "GFCE", 9: "GFCF", 12: "CIS", 13: "Valuables",
    14: "Exports", 15: "Imports", 2: "NetTaxes",
}
OUT_NAME = f"mospi_quarterly_constant_{BASE_YEAR}.csv"

_ctx = ssl.create_default_context()
_ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT   # api.mospi.gov.in needs legacy renegotiation


def fetch_indicator(code: int, limit: int = 100) -> list:
    """All quarterly rows for one indicator (the API pages at <= 100 rows)."""
    rows, page = [], 1
    while True:
        url = (f"{API}?base_year={BASE_YEAR}&series=Current&frequency_code=2"
               f"&indicator_code={code}&account_code=1&page={page}&limit={limit}")
        with urllib.request.urlopen(url, timeout=60, context=_ctx) as r:
            d = json.loads(r.read().decode("utf-8"))
        rows += d["data"]
        if page >= d["meta_data"]["totalPages"]:
            return rows
        page += 1


def tidy_to_wide(rows_by_name: dict) -> pd.DataFrame:
    """{name: [api rows]} -> chronological wide frame, one column per name (constant prices)."""
    frames = []
    for name, rows in rows_by_name.items():
        f = pd.DataFrame(rows)
        f["FY_Quarter"] = f["year"] + " " + f["quarter"]
        f[name] = pd.to_numeric(f["constant_price"], errors="coerce")
        frames.append(f[["FY_Quarter", name]].drop_duplicates("FY_Quarter").set_index("FY_Quarter"))
    wide = pd.concat(frames, axis=1).reset_index()
    return wide.sort_values("FY_Quarter", key=lambda s: s.map(order_key)).reset_index(drop=True)


def main():
    out = find_project() / "data" / "raw" / "gdp" / OUT_NAME
    wide = tidy_to_wide({name: fetch_indicator(code) for code, name in INDICATORS.items()})
    wide.to_csv(out, index=False)
    print(f"Wrote {out}  ({len(wide)} quarters, {wide['FY_Quarter'].iloc[0]} -> {wide['FY_Quarter'].iloc[-1]})")


if __name__ == "__main__":
    main()
