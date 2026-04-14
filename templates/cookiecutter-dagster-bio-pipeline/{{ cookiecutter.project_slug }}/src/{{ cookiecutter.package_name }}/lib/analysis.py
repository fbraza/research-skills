import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure


def summarize_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Create a generic numeric summary table for downstream inspection."""
    numeric = df.select_dtypes(include="number")

    if numeric.empty:
        return pd.DataFrame(
            {
                "column": df.columns.astype(str),
                "dtype": df.dtypes.astype(str).values,
            }
        )

    summary = (
        numeric.agg(["count", "mean", "std", "min", "max"])
        .T.reset_index()
        .rename(columns={"index": "column"})
    )
    summary["dtype"] = numeric.dtypes.astype(str).values
    return summary[["column", "dtype", "count", "mean", "std", "min", "max"]]


def build_missingness_figure(df: pd.DataFrame, max_columns: int = 12) -> Figure:
    """Plot column-wise missingness for a manageable subset of columns."""
    subset = df.iloc[:, :max_columns]

    fig, ax = plt.subplots(figsize=(max(6, 0.6 * max(1, subset.shape[1])), 4))

    if subset.empty:
        ax.text(0.5, 0.5, "No columns available", ha="center", va="center")
        ax.set_axis_off()
        fig.tight_layout()
        return fig

    missing_pct = subset.isna().mean().mul(100).sort_values(ascending=False)
    ax.bar(missing_pct.index.astype(str), missing_pct.values, color="#4477AA")
    ax.set_ylabel("Missing values (%)")
    ax.set_xlabel("Column")
    ax.set_title("Column-wise missingness")
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    return fig
