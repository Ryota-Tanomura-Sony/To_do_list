# tests/test_todo.py
import datetime as dt

import pandas as pd

from To_do import ensure_schema, month_grid_dates, shift_month


def test_completed_string_false_becomes_false():
    df = pd.DataFrame([{"id": 1, "title": "x", "quadrant": "Do (緊急かつ重要)", "deadline": "", "tags": "", "completed": "False"}])
    out = ensure_schema(df)
    assert bool(out.loc[0, "completed"]) is False


def test_completed_string_true_becomes_true():
    df = pd.DataFrame([{"id": 1, "title": "x", "quadrant": "Do (緊急かつ重要)", "deadline": "", "tags": "", "completed": "True"}])
    out = ensure_schema(df)
    assert bool(out.loc[0, "completed"]) is True


def test_missing_columns_are_filled():
    df = pd.DataFrame([{"title": "x"}])
    out = ensure_schema(df)
    for col in ["id", "title", "quadrant", "deadline", "tags", "completed"]:
        assert col in out.columns


def test_shift_month_crosses_year_boundary():
    assert shift_month(dt.date(2026, 1, 1), -1) == dt.date(2025, 12, 1)


def test_month_grid_dates_builds_monday_start_calendar():
    weeks = month_grid_dates(dt.date(2026, 5, 15))
    assert weeks[0][0] == dt.date(2026, 4, 27)
    assert weeks[-1][-1] == dt.date(2026, 5, 31)
