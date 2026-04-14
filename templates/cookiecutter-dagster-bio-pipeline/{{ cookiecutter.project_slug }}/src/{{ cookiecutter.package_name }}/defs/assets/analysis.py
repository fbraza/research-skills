import dagster as dg
import pandas as pd

from {{ cookiecutter.package_name }}.lib.analysis import summarize_numeric_columns


@dg.asset(
    key_prefix="analysis",
    group_name="analysis",
    io_manager_key="dataframe_io",
    code_version="0.1.0",
    ins={"validated_table": dg.AssetIn(key=dg.AssetKey(["processed", "validated_table"]))},
)
def analysis_summary(
    context: dg.AssetExecutionContext,
    validated_table: pd.DataFrame,
) -> pd.DataFrame:
    """Create a starter analytical summary artifact."""
    context.log.info(f"Summarizing validated table with {len(validated_table)} rows")
    return summarize_numeric_columns(validated_table)
