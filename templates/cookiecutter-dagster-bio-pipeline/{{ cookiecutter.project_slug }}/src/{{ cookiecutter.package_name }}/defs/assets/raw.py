from pathlib import Path

import dagster as dg
import pandas as pd

from {{ cookiecutter.package_name }}.defs.config import RawInputConfig


@dg.asset(
    key_prefix="raw",
    group_name="ingestion",
    io_manager_key="dataframe_io",
    code_version="0.1.0",
)
def input_table(context: dg.AssetExecutionContext, config: RawInputConfig) -> pd.DataFrame:
    """Load a canonical raw tabular input into the pipeline."""
    input_path = Path(config.input_path)
    if not input_path.exists():
        raise FileNotFoundError(
            f"Expected a raw input file at {input_path}. "
            "Place an immutable source file in data/raw/ "
            "or update RawInputConfig.input_path."
        )

    context.log.info(f"Loading raw input from {input_path}")
    return pd.read_csv(input_path, sep=config.separator, index_col=config.index_col)
