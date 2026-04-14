import dagster as dg
from pydantic import Field


class RawInputConfig(dg.Config):
    input_path: str = "data/raw/input.csv"
    separator: str = ","
    index_col: str | None = None


class ValidationConfig(dg.Config):
    required_columns: list[str] = Field(default_factory=list)
    drop_duplicate_rows: bool = True
    drop_fully_empty_rows: bool = True


class PlotConfig(dg.Config):
    max_columns: int = 12
