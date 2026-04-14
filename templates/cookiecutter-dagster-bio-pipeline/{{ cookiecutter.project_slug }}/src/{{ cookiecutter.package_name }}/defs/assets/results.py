import dagster as dg
import pandas as pd
from matplotlib.figure import Figure

from {{ cookiecutter.package_name }}.defs.config import PlotConfig
from {{ cookiecutter.package_name }}.lib.analysis import build_missingness_figure


@dg.asset(
    key_prefix="results",
    group_name="deliverables",
    io_manager_key="dataframe_io",
    code_version="0.1.0",
    ins={"analysis_summary": dg.AssetIn(key=dg.AssetKey(["analysis", "analysis_summary"]))},
)
def summary_table(analysis_summary: pd.DataFrame) -> pd.DataFrame:
    """Expose the analysis summary as a deliverable table."""
    return analysis_summary


@dg.asset(
    key_prefix="results",
    group_name="deliverables",
    io_manager_key="figure_io",
    code_version="0.1.0",
    ins={"validated_table": dg.AssetIn(key=dg.AssetKey(["processed", "validated_table"]))},
)
def completeness_plot(config: PlotConfig, validated_table: pd.DataFrame) -> Figure:
    """Generate a starter figure artifact for the results layer."""
    return build_missingness_figure(validated_table, max_columns=config.max_columns)
