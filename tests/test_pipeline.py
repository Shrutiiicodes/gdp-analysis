import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from utils import fy_quarter, order_key, find_project  # noqa: E402


def test_fy_quarter_and_order():
    assert fy_quarter(2012, 4) == "2012-13 Q1"
    assert fy_quarter(2013, 3) == "2012-13 Q4"
    assert order_key("2011-12 Q4") < order_key("2012-13 Q1")


def test_find_project_walks_up(monkeypatch):
    monkeypatch.delenv("GDP_PROJECT", raising=False)
    monkeypatch.chdir(ROOT / "notebooks")
    assert find_project() == ROOT


def test_find_project_env_var(monkeypatch, tmp_path):
    monkeypatch.setenv("GDP_PROJECT", str(ROOT))
    monkeypatch.chdir(tmp_path)
    assert find_project() == ROOT


def test_find_project_raises_outside_repo(monkeypatch, tmp_path):
    monkeypatch.delenv("GDP_PROJECT", raising=False)
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        find_project()


LEVEL_TO_YOY = [("GFCF", "GFCF_YoY"), ("Exports", "Exports_YoY"), ("Imports", "Imports_YoY"),
                ("M3_level", "M3_level_YoY"), ("M3_level", "M3_growth_YoY"),
                ("CrudeINR", "CrudeINR_YoY")]


def test_pct_change_does_not_forward_fill():
    # pandas < 3 padded NaN before differencing; the build relies on fill_method=None being honoured
    s = pd.Series([1.0, 2.0, 3.0, 4.0, float("nan")])
    assert s.pct_change(4, fill_method=None).isna().iloc[-1]


def test_master_has_no_yoy_where_level_missing():
    df = pd.read_csv(ROOT / "data" / "processed" / "composite_master_quarterly.csv")
    ks = df["FY_Quarter"].map(order_key)
    assert ks.iloc[0] == order_key("2011-12 Q1") and (ks.diff().dropna() == 1).all()   # contiguous spine
    for lvl, yoy in LEVEL_TO_YOY:
        no_level = df[lvl].isna()
        if lvl + "_new" in df.columns:                      # expenditure YoY may come from the new base
            no_level &= df[lvl + "_new"].isna()
        assert df.loc[no_level, yoy].isna().all(), f"{yoy} has values where {lvl} is NaN"


def test_master_contains_bank_credit_and_no_constant_label():
    df = pd.read_csv(ROOT / "data" / "processed" / "composite_master_quarterly.csv")
    assert "BankCredit_YoY" in df.columns
    assert "base_year_target" not in df.columns


def test_add_credit_missing_file_is_noop(tmp_path):
    from add_bank_credit import add_credit
    (tmp_path / "data" / "raw" / "credit").mkdir(parents=True)
    master = pd.DataFrame({"FY_Quarter": ["2011-12 Q1"]})
    out = add_credit(master, tmp_path)
    assert list(out.columns) == ["FY_Quarter"]


def test_fred_csv_to_raw_format():
    from fetch_brent import to_raw_format
    fred = "observation_date,MCOILBRENTEU\n1987-05-01,18.58\n2026-06-01,.\n2026-08-01,91.08\n"
    out = to_raw_format(fred)
    assert list(out.columns) == ["observation_date", "MCOILBRENTEU"]
    assert out["observation_date"].tolist() == ["01-05-1987", "01-08-2026"]   # DD-MM-YYYY, "." rows dropped
    assert out["MCOILBRENTEU"].tolist() == [18.58, 91.08]


def test_mospi_rows_to_wide():
    from fetch_mospi import tidy_to_wide
    rows = {
        "GDP":  [{"year": "2026-27", "quarter": "Q1", "constant_price": "8136153"},
                 {"year": "2025-26", "quarter": "Q4", "constant_price": "8880334"}],
        "GFCF": [{"year": "2026-27", "quarter": "Q1", "constant_price": "2795605"}],
    }
    out = tidy_to_wide(rows)
    assert out["FY_Quarter"].tolist() == ["2025-26 Q4", "2026-27 Q1"]        # chronological
    assert out.loc[1, "GDP"] == 8136153.0 and out.loc[1, "GFCF"] == 2795605.0
    assert pd.isna(out.loc[0, "GFCF"])


def test_master_new_base_comes_from_mospi_api_file():
    api = pd.read_csv(ROOT / "data" / "raw" / "gdp" / "mospi_quarterly_constant_2022-23.csv")
    df = pd.read_csv(ROOT / "data" / "processed" / "composite_master_quarterly.csv")
    last = api.iloc[-1]
    row = df.loc[df["FY_Quarter"] == last["FY_Quarter"]].iloc[0]
    assert row["GDP_level_new"] == last["GDP"]
    assert row["GDP_growth_source"] == "2022-23 base (spliced)"
