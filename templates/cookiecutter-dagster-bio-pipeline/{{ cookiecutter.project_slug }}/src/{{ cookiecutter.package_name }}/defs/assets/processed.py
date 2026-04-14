import dagster as dg
import pandas as pd

from {{ cookiecutter.package_name }}.defs.config import ValidationConfig
from {{ cookiecutter.package_name }}.lib.qc import validate_table


@dg.asset(
    key_prefix="processed",
    group_name="preparation",
    io_manager_key="dataframe_io",
    code_version="0.1.0",
    ins={"input_table": dg.AssetIn(key=dg.AssetKey(["raw", "input_table"]))},
)
def validated_table(
    context: dg.AssetExecutionContext,
    config: ValidationConfig,
    input_table: pd.DataFrame,
) -> pd.DataFrame:
    """Apply a minimal validation and cleanup step before analysis."""
    context.log.info(f"Validating input table with {len(input_table)} rows")
    return validate_table(
        input_table,
        config.required_columns,
        drop_duplicate_rows=config.drop_duplicate_rows,
        drop_fully_empty_rows=config.drop_fully_empty_rows,
    )
