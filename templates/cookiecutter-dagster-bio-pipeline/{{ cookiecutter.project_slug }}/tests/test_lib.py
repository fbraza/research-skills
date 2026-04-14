import pandas as pd

from {{ cookiecutter.package_name }}.lib.analysis import summarize_numeric_columns
from {{ cookiecutter.package_name }}.lib.qc import validate_table


def test_validate_table_removes_duplicate_rows() -> None:
    df = pd.DataFrame({"sample": ["a", "a"], "value": [1, 1]})

    validated = validate_table(df, required_columns=["sample", "value"])

    assert len(validated) == 1


def test_summarize_numeric_columns_returns_expected_columns() -> None:
    df = pd.DataFrame({"value": [1.0, 2.0, 3.0], "group": ["x", "y", "z"]})

    summary = summarize_numeric_columns(df)

    assert {"column", "dtype"}.issubset(summary.columns)
    assert "value" in set(summary["column"])
