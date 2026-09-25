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


def test_master_has_no_yoy_where_level_missing():
    df = pd.read_csv(ROOT / "data" / "processed" / "composite_master_quarterly.csv")
    assert len(df) == 62 and not df["FY_Quarter"].duplicated().any()
    for lvl, yoy in LEVEL_TO_YOY:
        assert df.loc[df[lvl].isna(), yoy].isna().all(), f"{yoy} has values where {lvl} is NaN"
