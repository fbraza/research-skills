"""
plot_results.py — Visualize Scaden deconvolution predictions.

Generates publication-quality figures from Scaden predictions:
- Stacked bar chart: cell type fractions per sample
- Fraction heatmap: samples × cell types
- Cell type boxplot: distribution of each cell type across samples
- Grouped comparison: fractions by condition (if metadata provided)

Parameters
----------
predictions_file : str
    Path to scaden_predictions.txt.
output_dir : str
    Directory to save plots.
metadata_file : str or None
    Optional TSV with sample metadata (must have sample names as index).
    Used for grouping samples by condition in comparison plots.
group_column : str
    Column in metadata to use for grouping (default: "condition").
top_n_celltypes : int
    Number of cell types to show (default: all).
figsize : tuple
    Figure size (width, height) in inches.
palette : str or list
    Color palette for cell types.

Returns
-------
dict with paths to all generated plot files.

Example
-------
    from scripts.plot_results import plot_deconvolution_results

    plots = plot_deconvolution_results(
        predictions_file="scaden_results/scaden_predictions.txt",
        output_dir="scaden_results/plots/",
        metadata_file="sample_metadata.tsv",
        group_column="condition"
    )
"""

import os
import sys
import warnings
warnings.filterwarnings("ignore")


def plot_deconvolution_results(
    predictions_file: str,
    output_dir: str = "plots/",
    metadata_file: str = None,
    group_column: str = "condition",
    top_n_celltypes: int = None,
    figsize: tuple = None,
    palette: str = "tab20"
) -> dict:
    """
    Generate all standard Scaden deconvolution visualizations.

    Parameters
    ----------
    predictions_file : str
        Path to scaden_predictions.txt.
    output_dir : str
        Output directory for plots.
    metadata_file : str or None
        Optional sample metadata TSV.
    group_column : str
        Metadata column for grouping.
    top_n_celltypes : int or None
        Limit to top N cell types by mean fraction.
    figsize : tuple or None
        Figure size override.
    palette : str
        Seaborn/matplotlib color palette.

    Returns
    -------
    dict mapping plot name to file path.
    """
    import pandas as pd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    sns.set_theme(style="ticks")
    os.makedirs(output_dir, exist_ok=True)

    # Load predictions
    preds = pd.read_csv(predictions_file, sep="\t", index_col=0)
    print(f"Loaded predictions: {preds.shape[0]} samples × {preds.shape[1]} cell types")

    # Optionally limit to top N cell types
    if top_n_celltypes and top_n_celltypes < preds.shape[1]:
        top_types = preds.mean().nlargest(top_n_celltypes).index
        preds = preds[top_types]
        print(f"  Showing top {top_n_celltypes} cell types by mean fraction")

    # Load metadata if provided
    metadata = None
    if metadata_file and os.path.exists(metadata_file):
        metadata = pd.read_csv(metadata_file, sep="\t", index_col=0)
        common = preds.index.intersection(metadata.index)
        preds = preds.loc[common]
        metadata = metadata.loc[common]
        print(f"  Metadata loaded: {len(common)} samples with metadata")

    # Generate color palette
    n_types = preds.shape[1]
    colors = sns.color_palette(palette, n_types)
    color_map = dict(zip(preds.columns, colors))

    plots = {}

    # ── 1. Stacked Bar Chart ──────────────────────────────────────────
    plots["stacked_bar"] = _plot_stacked_bar(preds, color_map, output_dir, figsize)

    # ── 2. Fraction Heatmap ───────────────────────────────────────────
    plots["heatmap"] = _plot_heatmap(preds, output_dir, figsize)

    # ── 3. Cell Type Boxplot ──────────────────────────────────────────
    plots["boxplot"] = _plot_boxplot(preds, color_map, output_dir, figsize)

    # ── 4. Grouped Comparison (if metadata available) ─────────────────
    if metadata is not None and group_column in metadata.columns:
        plots["grouped_comparison"] = _plot_grouped_comparison(
            preds, metadata, group_column, color_map, output_dir, figsize
        )

    print(f"\n✓ All visualizations saved to: {output_dir}")
    for name, path in plots.items():
        if path:
            print(f"  {name}: {os.path.basename(path)}")

    return plots


def _plot_stacked_bar(preds, color_map, output_dir, figsize=None):
    """Stacked bar chart of cell type fractions per sample."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n_samples = len(preds)
    width = max(10, n_samples * 0.3)
    fig, ax = plt.subplots(figsize=figsize or (width, 5))

    bottom = [0] * n_samples
    x = range(n_samples)

    for ct in preds.columns:
        ax.bar(x, preds[ct].values, bottom=bottom,
               label=ct, color=color_map[ct], width=0.8)
        bottom = [b + v for b, v in zip(bottom, preds[ct].values)]

    ax.set_xlabel("Sample", fontsize=12)
    ax.set_ylabel("Cell type fraction", fontsize=12)
    ax.set_title("Predicted Cell Type Composition", fontsize=14)
    ax.set_xticks(range(n_samples))
    ax.set_xticklabels(preds.index, rotation=90, fontsize=8)
    ax.set_ylim(0, 1.05)
    ax.legend(bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=9)
    plt.tight_layout()

    for ext in ["png", "svg"]:
        path = os.path.join(output_dir, f"stacked_bar.{ext}")
        plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  ✓ Stacked bar chart saved")
    return os.path.join(output_dir, "stacked_bar.png")


def _plot_heatmap(preds, output_dir, figsize=None):
    """Heatmap of cell type fractions (samples × cell types)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    n_samples, n_types = preds.shape
    height = max(6, n_samples * 0.2)
    width = max(6, n_types * 0.8)

    fig, ax = plt.subplots(figsize=figsize or (width, height))

    sns.heatmap(
        preds,
        cmap="YlOrRd",
        vmin=0, vmax=1,
        ax=ax,
        cbar_kws={"label": "Cell type fraction"},
        xticklabels=True,
        yticklabels=True if n_samples <= 50 else False
    )

    ax.set_title("Cell Type Fraction Heatmap", fontsize=14)
    ax.set_xlabel("Cell type", fontsize=12)
    ax.set_ylabel("Sample", fontsize=12)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.tight_layout()

    for ext in ["png", "svg"]:
        path = os.path.join(output_dir, f"fraction_heatmap.{ext}")
        plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  ✓ Fraction heatmap saved")
    return os.path.join(output_dir, "fraction_heatmap.png")


def _plot_boxplot(preds, color_map, output_dir, figsize=None):
    """Boxplot of cell type fraction distributions across samples."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    n_types = preds.shape[1]
    fig, ax = plt.subplots(figsize=figsize or (max(8, n_types * 1.2), 5))

    preds_long = preds.reset_index().melt(
        id_vars="index", var_name="Cell type", value_name="Fraction"
    )

    # Sort by median fraction
    order = preds.median().sort_values(ascending=False).index.tolist()

    import seaborn as sns
    sns.boxplot(
        data=preds_long,
        x="Cell type", y="Fraction",
        order=order,
        palette=color_map,
        ax=ax,
        width=0.6,
        fliersize=3
    )

    ax.set_xlabel("Cell type", fontsize=12)
    ax.set_ylabel("Predicted fraction", fontsize=12)
    ax.set_title("Cell Type Fraction Distribution", fontsize=14)
    ax.set_ylim(0, None)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    plt.tight_layout()

    for ext in ["png", "svg"]:
        path = os.path.join(output_dir, f"cell_type_boxplot.{ext}")
        plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  ✓ Cell type boxplot saved")
    return os.path.join(output_dir, "cell_type_boxplot.png")


def _plot_grouped_comparison(preds, metadata, group_column, color_map, output_dir, figsize=None):
    """Grouped bar chart comparing cell type fractions between conditions."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd

    groups = metadata[group_column].unique()
    n_types = preds.shape[1]

    fig, ax = plt.subplots(figsize=figsize or (max(10, n_types * 1.5), 5))

    # Compute mean ± SEM per group
    plot_data = []
    for group in groups:
        group_samples = metadata[metadata[group_column] == group].index
        group_preds = preds.loc[group_samples]
        for ct in preds.columns:
            plot_data.append({
                "Cell type": ct,
                "Group": group,
                "Mean fraction": group_preds[ct].mean(),
                "SEM": group_preds[ct].sem()
            })

    plot_df = pd.DataFrame(plot_data)

    # Sort cell types by overall mean
    order = preds.mean().sort_values(ascending=False).index.tolist()
    group_palette = sns.color_palette("Set2", len(groups))

    sns.barplot(
        data=plot_df,
        x="Cell type", y="Mean fraction",
        hue="Group",
        order=order,
        palette=group_palette,
        ax=ax,
        capsize=0.05,
        errwidth=1.5
    )

    ax.set_xlabel("Cell type", fontsize=12)
    ax.set_ylabel("Mean fraction ± SEM", fontsize=12)
    ax.set_title(f"Cell Type Fractions by {group_column.capitalize()}", fontsize=14)
    plt.xticks(rotation=45, ha="right", fontsize=9)
    ax.legend(title=group_column, bbox_to_anchor=(1.01, 1), loc="upper left")
    plt.tight_layout()

    for ext in ["png", "svg"]:
        path = os.path.join(output_dir, f"grouped_comparison.{ext}")
        plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()

    print(f"  ✓ Grouped comparison plot saved")
    return os.path.join(output_dir, "grouped_comparison.png")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Plot Scaden deconvolution results")
    parser.add_argument("predictions_file", help="Path to scaden_predictions.txt")
    parser.add_argument("--output_dir", default="plots/", help="Output directory")
    parser.add_argument("--metadata_file", default=None, help="Sample metadata TSV")
    parser.add_argument("--group_column", default="condition", help="Metadata grouping column")
    parser.add_argument("--top_n", type=int, default=None, help="Show top N cell types")
    args = parser.parse_args()

    plot_deconvolution_results(
        predictions_file=args.predictions_file,
        output_dir=args.output_dir,
        metadata_file=args.metadata_file,
        group_column=args.group_column,
        top_n_celltypes=args.top_n
    )
