from collections.abc import Sequence

import pandas as pd


def validate_table(
    df: pd.DataFrame,
    required_columns: Sequence[str] = (),
    *,
    drop_duplicate_rows: bool = True,
    drop_fully_empty_rows: bool = True,
) -> pd.DataFrame:
    """Validate a generic tabular input before downstream processing."""
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    output = df.copy()

    if drop_fully_empty_rows:
        output = output.dropna(how="all")

    if drop_duplicate_rows:
        output = output.drop_duplicates()

    if output.empty:
        raise ValueError("Validation removed all rows from the table")

    return output
