"""
fetch_mospi.py
--------------
Pulls three official MoSPI series from the eSankhyiki JSON API (no authentication;
the server still uses legacy TLS renegotiation, hence the ssl option) and writes
them as tidy raw CSVs that build_composite.py reads directly:

    data/raw/gdp/mospi_quarterly_constant_2022-23.csv
        FY_Quarter, GDP, PFCE, GFCE, GFCF, CIS, Valuables, Exports, Imports, NetTaxes
        (2022-23 base, constant prices, Rs crore, incl. every MoSPI back-revision)
    data/raw/iip/mospi_iip_general_monthly.csv
        year, month, growth_rate, base_year      (General index YoY %, 2011-12 base
        where published, 2022-23 base after it ends)
    data/raw/cpi/mospi_cpi_combined_monthly.csv
        Date (YYYY-MM), index, inflation, base_year   (All-India Combined General;
        2010 base for 2012-2013, 2012 base 2014-2025, 2024 base from 2026)

Splice rule for series that change base: keep the OLDER base for every month it
covers, take the newer base only for months after it ends. YoY rates are close to
base-invariant, so the join is clean. A fetch writes a file only when it fully
succeeds; run_all.py treats a failed fetch as a warning and builds from the
committed file.

Endpoints discovered from https://esankhyiki.mospi.gov.in/macroindicators.
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

API = "https://api.mospi.gov.in/api/"
_ctx = ssl.create_default_context()
_ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT   # api.mospi.gov.in needs legacy renegotiation

NAS_BASE = "2022-23"
NAS_INDICATORS = {5: "GDP", 10: "PFCE", 11: "GFCE", 9: "GFCF", 12: "CIS", 13: "Valuables",
                  14: "Exports", 15: "Imports", 2: "NetTaxes"}
IIP_BASES = ["2011-12", "2022-23"]                    # older first
CPI_BASES = [("2010", "year=2012"), ("2010", "year=2013"),   # oldest first; 2010 base ignores code filters and
             #                                            the 2012 base has no YoY for 2013 (its index starts then)
             ("2012", "sector_code=3&group_code=0"),
             ("2024", "state_code=1&sector_code=3&division_code=0")]


def _get(path: str) -> dict:
    with urllib.request.urlopen(API + path, timeout=60, context=_ctx) as r:
        return json.loads(r.read().decode("utf-8"))


def _fetch_all(path: str, limit: int = 100) -> list:
    """Page through an eSankhyiki data endpoint (max 100 rows per page)."""
    rows, page = [], 1
    while True:
        d = _get(f"{path}&page={page}&limit={limit}")
        rows += d.get("data", [])
        meta = d.get("meta_data") or {}
        if page >= int(meta.get("totalPages") or 1):
            return rows
        page += 1


# --- national accounts -------------------------------------------------------------
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


def fetch_nas() -> pd.DataFrame:
    return tidy_to_wide({
        name: _fetch_all(f"nas/getNASData?base_year={NAS_BASE}&series=Current&frequency_code=2"
                         f"&indicator_code={code}&account_code=1")
        for code, name in NAS_INDICATORS.items()})


# --- base splicing (shared by IIP and CPI) -----------------------------------------
def splice_bases(frames: list) -> pd.DataFrame:
    """[(base_year, frame with a datetime column 'm'), ...] oldest first -> one frame that
    keeps each month from the OLDEST base that covers it, tagged with base_year."""
    out = None
    for base, f in frames:
        f = f.copy()
        f["base_year"] = base
        if out is None:
            out = f
        else:
            out = pd.concat([out, f[f["m"] > out["m"].max()]])
    return out.sort_values("m").reset_index(drop=True)


def _month_col(f: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(f["year"].astype(str) + " " + f["month"], format="%Y %B")


# --- IIP --------------------------------------------------------------------------
def fetch_iip() -> pd.DataFrame:
    frames = []
    for base in IIP_BASES:
        rows = [r for r in _fetch_all(f"iip/getIIPData?base_year={base}&frequency=Monthly")
                if r.get("type") == "General"]
        f = pd.DataFrame(rows)
        f["m"] = _month_col(f)
        f["growth_rate"] = pd.to_numeric(f["growth_rate"], errors="coerce")
        frames.append((base, f[["m", "growth_rate"]].dropna().drop_duplicates("m")))
    s = splice_bases(frames)
    s["year"], s["month"] = s["m"].dt.year, s["m"].dt.strftime("%B")
    return s[["year", "month", "growth_rate", "base_year"]]


# --- CPI --------------------------------------------------------------------------
def fetch_cpi() -> pd.DataFrame:
    frames = []
    for base, codes in CPI_BASES:
        rows = _fetch_all(f"cpi/getCPIData?base_year={base}&level=Group&series=Current&{codes}")
        f = pd.DataFrame(rows)
        headline = f.get("division", pd.Series("", index=f.index)).eq("CPI (General)") | f.get("group", pd.Series("", index=f.index)).eq("General")
        f = f[(f["state"] == "All India") & (f["sector"] == "Combined") & headline]
        f["m"] = _month_col(f)
        f["index"] = pd.to_numeric(f["index"], errors="coerce")
        f["inflation"] = pd.to_numeric(f["inflation"], errors="coerce")
        f = f.dropna(subset=["inflation"]).drop_duplicates("m")
        frames.append((base, f[["m", "index", "inflation"]]))
    s = splice_bases(frames)
    s["Date"] = s["m"].dt.strftime("%Y-%m")
    return s[["Date", "index", "inflation", "base_year"]]


def main():
    root = find_project() / "data" / "raw"
    jobs = [
        (root / "gdp" / f"mospi_quarterly_constant_{NAS_BASE}.csv", fetch_nas),
        (root / "iip" / "mospi_iip_general_monthly.csv", fetch_iip),
        (root / "cpi" / "mospi_cpi_combined_monthly.csv", fetch_cpi),
    ]
    failed = 0
    for out, fn in jobs:
        try:
            df = fn()
            df.to_csv(out, index=False)
            print(f"Wrote {out}  ({len(df)} rows, last = {df.iloc[-1, 0]})")
        except Exception as e:                      # keep the committed file, report, carry on
            failed += 1
            print(f"!! {out.name}: fetch failed ({type(e).__name__}: {str(e)[:120]}); committed file kept")
    raise SystemExit(1 if failed == len(jobs) else 0)


if __name__ == "__main__":
    main()
