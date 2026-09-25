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
    assert len(df) == 62 and not df["FY_Quarter"].duplicated().any()
    for lvl, yoy in LEVEL_TO_YOY:
        assert df.loc[df[lvl].isna(), yoy].isna().all(), f"{yoy} has values where {lvl} is NaN"


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
