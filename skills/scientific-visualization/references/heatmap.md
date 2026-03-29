# Heatmap

Publication-ready heatmap for differentially expressed genes, expression matrices, or correlation matrices. Use when showing patterns across multiple genes and samples/conditions simultaneously.

## When to Use

- To display expression patterns of differentially expressed genes across conditions
- To visualize correlation matrices (gene-gene, sample-sample)
- To show fold change values for a curated gene set
- To identify sample or gene clusters via hierarchical clustering
- Standard figure for multi-sample transcriptomics, proteomics, and metabolomics

## Input Data

Expected input: a DataFrame where rows are genes/features and columns are samples/conditions.

| Element | Type | Description |
|---------|------|-------------|
| Row index | str | Gene or feature identifiers |
| Columns | str | Sample or condition identifiers |
| Values | float | Expression levels (log2-normalized, z-scored, or fold change) |

Optional: a metadata DataFrame mapping sample columns to experimental groups.

Example expression matrix CSV:
```
gene,Sample_A1,Sample_A2,Sample_A3,Sample_B1,Sample_B2,Sample_B3
BRCA1,8.2,7.9,8.5,4.1,3.8,4.3
TP53,6.1,5.8,6.4,9.2,8.9,9.5
MYC,7.3,7.1,7.5,7.4,7.2,7.6
IL6,3.2,3.5,3.1,8.8,9.1,8.6
```

Example metadata CSV:
```
sample,group
Sample_A1,Control
Sample_A2,Control
Sample_A3,Control
Sample_B1,Treatment
Sample_B2,Treatment
Sample_B3,Treatment
```

## UltraPlot Implementation

```python
import numpy as np
import pandas as pd
import ultraplot as uplt
import matplotlib as mpl
from matplotlib.colors import Normalize, TwoSlopeNorm
from scipy.cluster.hierarchy import linkage, leaves_list
from scipy.spatial.distance import pdist


# Okabe-Ito palette for group annotations
OKABE_ITO = [
    "#E69F00", "#56B4E9", "#009E73", "#F0E442",
    "#0072B2", "#D55E00", "#CC79A7", "#000000",
]


def plot_heatmap(
    df,
    metadata=None,
    group_col=None,
    z_score=True,
    cluster_rows=True,
    cluster_cols=True,
    cmap="RdBu_r",
    vmin=None,
    vmax=None,
    show_values=False,
    value_fmt=".1f",
    row_fontsize=None,
    figsize=(4, 6),
    title="",
    save_path=None,
):
    """Plot a publication-ready clustered heatmap from an expression matrix.

    Optionally z-scores rows, performs hierarchical clustering, and adds
    sample group annotations from metadata.

    Parameters
    ----------
    df : pandas.DataFrame
        Expression matrix with genes as rows and samples as columns.
        Values should be numeric (log2-normalized counts, z-scores, or
        fold changes).
    metadata : pandas.DataFrame or None, optional
        Sample annotation table. Must contain a column matching `group_col`
        and an index or column matching the column names of `df`.
        If None, no group annotation bar is drawn, by default None.
    group_col : str or None, optional
        Column name in `metadata` identifying sample groups, by default None.
        Required if `metadata` is provided.
    z_score : bool, optional
        Whether to z-score each row (gene) across samples, by default True.
        Standard for gene expression data. Set to False for fold change or
        correlation matrices.
    cluster_rows : bool, optional
        Whether to hierarchically cluster rows, by default True.
    cluster_cols : bool, optional
        Whether to hierarchically cluster columns, by default True.
    cmap : str, optional
        Colormap name, by default "RdBu_r". Use diverging colormaps for
        z-scored or fold change data; sequential for raw expression.
    vmin : float or None, optional
        Minimum value for color scale. If None, auto-computed.
        For diverging data, auto-set to symmetric bounds, by default None.
    vmax : float or None, optional
        Maximum value for color scale. If None, auto-computed, by default None.
    show_values : bool, optional
        Whether to overlay numeric values in each cell. Only recommended
        for small matrices (fewer than 20x20), by default False.
    value_fmt : str, optional
        Format string for cell value annotations, by default ".1f".
    row_fontsize : float or None, optional
        Font size for row (gene) labels. If None, auto-scales based on
        gene count: 8 for <=20 genes, 6 for <=40, hidden for >50,
        by default None.
    figsize : tuple of float, optional
        Figure dimensions in inches (width, height), by default (4, 6).
    title : str, optional
        Plot title, by default "".
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.
        If None, saves to ./results/heatmap, by default None.

    Returns
    -------
    fig : ultraplot.Figure
        The figure object.
    ax : ultraplot.Axes
        The axes object.
    """
    # ── Prepare data ──────────────────────────────────────────────────
    mat = df.copy().astype(float)

    # Z-score rows if requested
    if z_score:
        row_means = mat.mean(axis=1)
        row_stds = mat.std(axis=1, ddof=1)
        # Avoid division by zero for constant rows
        row_stds = row_stds.replace(0, 1.0)
        mat = mat.sub(row_means, axis=0).div(row_stds, axis=0)

    # ── Hierarchical clustering ───────────────────────────────────────
    if cluster_rows and mat.shape[0] > 1:
        row_dist = pdist(mat.values, metric="euclidean")
        row_linkage = linkage(row_dist, method="ward")
        row_order = leaves_list(row_linkage)
        mat = mat.iloc[row_order, :]

    if cluster_cols and mat.shape[1] > 1:
        col_dist = pdist(mat.values.T, metric="euclidean")
        col_linkage = linkage(col_dist, method="ward")
        col_order = leaves_list(col_linkage)
        mat = mat.iloc[:, col_order]

    # ── Auto-scale color bounds ───────────────────────────────────────
    data_max = np.nanmax(np.abs(mat.values))
    is_diverging = cmap in ("RdBu_r", "RdBu", "coolwarm", "bwr", "seismic")

    if vmin is None and vmax is None and is_diverging:
        vmax = np.ceil(data_max * 10) / 10  # round up to 1 decimal
        vmin = -vmax
    elif vmin is None:
        vmin = np.nanmin(mat.values)
    if vmax is None:
        vmax = np.nanmax(mat.values)

    # ── Auto row fontsize ─────────────────────────────────────────────
    n_genes = mat.shape[0]
    if row_fontsize is None:
        if n_genes <= 20:
            row_fontsize = 8
        elif n_genes <= 40:
            row_fontsize = 6
        else:
            row_fontsize = 0  # hide labels

    # ── Metadata group colors ─────────────────────────────────────────
    group_colors = None
    group_label_map = None
    if metadata is not None and group_col is not None:
        # Align metadata to current column order
        if "sample" in metadata.columns:
            meta_aligned = metadata.set_index("sample").reindex(mat.columns)
        else:
            meta_aligned = metadata.reindex(mat.columns)

        groups = meta_aligned[group_col].values
        unique_groups = list(dict.fromkeys(groups))  # preserve order
        color_palette = {g: OKABE_ITO[i % len(OKABE_ITO)] for i, g in enumerate(unique_groups)}
        group_colors = [color_palette[g] for g in groups]
        group_label_map = color_palette

    # ── Plot ──────────────────────────────────────────────────────────
    mpl.rcParams["svg.fonttype"] = "none"

    fig, ax = uplt.subplot(figsize=figsize)

    # Render heatmap with pcolormesh
    im = ax.pcolormesh(
        mat.values,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
    )

    # ── Colorbar ──────────────────────────────────────────────────────
    cbar_label = "Z-score" if z_score else "Expression"
    fig.colorbar(im, loc="right", label=cbar_label, width=0.12)

    # ── Cell value annotations ────────────────────────────────────────
    if show_values and n_genes <= 50 and mat.shape[1] <= 20:
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                val = mat.values[i, j]
                text_color = "white" if abs(val - vmin) / (vmax - vmin) > 0.75 or abs(val - vmin) / (vmax - vmin) < 0.25 else "black"
                ax.text(
                    j + 0.5, i + 0.5,
                    f"{val:{value_fmt}}",
                    ha="center", va="center",
                    fontsize=6, color=text_color,
                )

    # ── Group annotation bar ──────────────────────────────────────────
    if group_colors is not None:
        for j, color in enumerate(group_colors):
            ax.fill_between(
                [j, j + 1], mat.shape[0], mat.shape[0] + 0.6,
                color=color, linewidth=0.3, edgecolor="white",
            )
        # Add legend for groups
        from matplotlib.patches import Patch
        legend_handles = [Patch(facecolor=c, label=g) for g, c in group_label_map.items()]
        ax.legend(
            handles=legend_handles,
            loc="upper right",
            bbox_to_anchor=(1.0, 1.15),
            fontsize=7,
            frameon=False,
            ncol=min(len(group_label_map), 4),
            handletextpad=0.3,
        )

    # ── Axis labels ───────────────────────────────────────────────────
    # X-axis: sample names
    ax.set_xticks(np.arange(mat.shape[1]) + 0.5)
    ax.set_xticklabels(mat.columns, rotation=45, ha="right", fontsize=8)

    # Y-axis: gene names
    if row_fontsize > 0:
        ax.set_yticks(np.arange(n_genes) + 0.5)
        ax.set_yticklabels(mat.index, fontsize=row_fontsize)
    else:
        ax.set_yticks([])

    ax.format(
        title=title,
        titlesize=9,
        titleweight="bold",
    )

    # ── Save ──────────────────────────────────────────────────────────
    if save_path is None:
        save_path = "./results/heatmap"
    fig.savefig(f"{save_path}.svg", dpi=300, bbox_inches="tight")
    fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax
```

## Colormap Recommendations

| Data type | Recommended cmap | Notes |
|-----------|-----------------|-------|
| Z-scored expression | `RdBu_r` | Diverging, centered at 0. Standard for DE heatmaps. |
| Fold change | `RdBu_r` or `coolwarm` | Diverging, symmetric around 0. |
| Raw / log2 expression | `viridis` or `magma` | Sequential. Set `z_score=False`. |
| Correlation matrix | `RdBu_r` | Diverging, set `vmin=-1, vmax=1`. |
| Binary (presence/absence) | `Greys` | Sequential, 0-1 range. |

## Customization Notes

- **`z_score=True`**: Default for gene expression. Standardizes each gene (row) to mean=0, sd=1 across samples. Set to `False` for fold change or correlation matrices where the original scale is meaningful.
- **`cluster_rows` / `cluster_cols`**: Uses Ward's method with Euclidean distance. Disable column clustering when sample order is meaningful (e.g., time series).
- **`row_fontsize`**: Auto-scales based on gene count. For >50 genes, labels are hidden. Override by setting explicitly (e.g., `row_fontsize=5` for dense heatmaps).
- **`show_values`**: Only practical for small matrices. Automatically disabled if the matrix exceeds 50 rows or 20 columns.
- **`metadata` + `group_col`**: Adds a colored annotation bar above the heatmap indicating sample groups. Colors are assigned from the Okabe-Ito palette.
- **Gene subsetting**: Filter the input DataFrame to your gene set of interest before passing. The function plots all rows it receives.
- **Symmetric color scale**: For diverging colormaps, the function auto-computes symmetric `vmin`/`vmax`. Override with explicit values if needed.
