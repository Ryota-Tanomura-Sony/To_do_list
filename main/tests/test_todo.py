# tests/test_todo.py
import pandas as pd

from To_do import ensure_schema


def test_completed_string_false_becomes_false():
    df = pd.DataFrame([{"id": 1, "title": "x", "quadrant": "Do (緊急かつ重要)", "deadline": "", "tags": "", "completed": "False"}])
    out = ensure_schema(df)
    assert out.loc[0, "completed"] is False


def test_completed_string_true_becomes_true():
    df = pd.DataFrame([{"id": 1, "title": "x", "quadrant": "Do (緊急かつ重要)", "deadline": "", "tags": "", "completed": "True"}])
    out = ensure_schema(df)
    assert out.loc[0, "completed"] is True


def test_missing_columns_are_filled():
    df = pd.DataFrame([{"title": "x"}])
    out = ensure_schema(df)
    for col in ["id", "title", "quadrant", "deadline", "tags", "completed"]:
        assert col in out.columns