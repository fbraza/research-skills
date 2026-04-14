import dagster as dg
import pandas as pd

from {{ cookiecutter.package_name }}.defs.assets.analysis import analysis_summary
from {{ cookiecutter.package_name }}.defs.assets.processed import validated_table
from {{ cookiecutter.package_name }}.defs.assets.raw import input_table


@dg.asset_check(asset=input_table, description="Raw input table should not be empty.")
def check_input_table_not_empty(input_table: pd.DataFrame) -> dg.AssetCheckResult:
    passed = not input_table.empty
    return dg.AssetCheckResult(
        passed=passed,
        metadata={"rows": len(input_table), "columns": len(input_table.columns)},
    )


@dg.asset_check(
    asset=validated_table,
    description="Validated table should not contain fully empty rows.",
)
def check_validated_table(validated_table: pd.DataFrame) -> dg.AssetCheckResult:
    has_all_empty_row = bool(validated_table.isna().all(axis=1).any())
    return dg.AssetCheckResult(
        passed=not has_all_empty_row,
        metadata={"rows": len(validated_table), "columns": len(validated_table.columns)},
    )


@dg.asset_check(
    asset=analysis_summary,
    description="Analysis summary should contain at least one row.",
)
def check_analysis_summary(analysis_summary: pd.DataFrame) -> dg.AssetCheckResult:
    required_columns = {"column", "dtype"}
    passed = (not analysis_summary.empty) and required_columns.issubset(analysis_summary.columns)
    return dg.AssetCheckResult(
        passed=passed,
        metadata={"rows": len(analysis_summary), "columns": len(analysis_summary.columns)},
    )
