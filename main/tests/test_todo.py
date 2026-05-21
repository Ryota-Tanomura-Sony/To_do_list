# tests/test_todo.py
import datetime as dt
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from To_do import ensure_schema, get_month_grid, _normalize_tags, _parse_bool


def test_completed_string_false_becomes_false():
    df = pd.DataFrame([{"id": 1, "title": "x", "quadrant": "Do (緊急かつ重要)", "deadline": "", "tags": "", "completed": "False"}])
    out = ensure_schema(df)
    assert out.loc[0, "completed"] == False  # noqa: E712


def test_completed_string_true_becomes_true():
    df = pd.DataFrame([{"id": 1, "title": "x", "quadrant": "Do (緊急かつ重要)", "deadline": "", "tags": "", "completed": "True"}])
    out = ensure_schema(df)
    assert out.loc[0, "completed"] == True  # noqa: E712


def test_missing_columns_are_filled():
    df = pd.DataFrame([{"title": "x"}])
    out = ensure_schema(df)
    for col in ["id", "title", "quadrant", "deadline", "tags", "completed"]:
        assert col in out.columns


def test_get_month_grid_returns_6_weeks():
    grid = get_month_grid(2026, 5)
    assert len(grid) == 6
    for week in grid:
        assert len(week) == 7


def test_get_month_grid_contains_target_month():
    grid = get_month_grid(2026, 5)
    all_dates = [d for week in grid for d in week]
    may_dates = [d for d in all_dates if d.month == 5]
    assert len(may_dates) >= 28  # 5月は31日だが前後月の日もある


def test_get_month_grid_starts_on_monday():
    grid = get_month_grid(2026, 1)
    first_day = grid[0][0]
    assert first_day.weekday() == 0  # 月曜


def test_normalize_tags_basic():
    assert _normalize_tags("A,B,C") == ["A", "B", "C"]
    assert _normalize_tags("") == []
    assert _normalize_tags("A,A,B") == ["A", "B"]


def test_parse_bool_variants():
    assert _parse_bool("true") is True
    assert _parse_bool("False") is False
    assert _parse_bool(1) is True
    assert _parse_bool(0) is False
    assert _parse_bool(None) is False