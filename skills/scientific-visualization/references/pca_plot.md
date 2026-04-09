# PCA Plot

Publication-ready PCA scatter plot with variance explained on axes.

## Input Data

Expected input: a CSV or DataFrame with columns:
- `PC1`, `PC2` — first two principal components
- A categorical column for coloring (e.g., `condition`, `tissue`, `batch`)
- Optional: `sample_id` for labeling points

Variance explained should be provided separately (list/array of floats).

## Data Extraction

### Python (AnnData)

```python
import pandas as pd

pca_df = pd.DataFrame(
    adata.obsm["X_pca"][:, :2],
    columns=["PC1", "PC2"],
    index=adata.obs_names,
)
pca_df["condition"] = adata.obs["condition"].values
var_ratio = adata.uns["pca"]["variance_ratio"]  # array of floats
```

### Python (sklearn / custom matrix)

```python
from sklearn.decomposition import PCA
import pandas as pd

pca = PCA(n_components=2)
coords = pca.fit_transform(data_matrix)
pca_df = pd.DataFrame(coords, columns=["PC1", "PC2"])
pca_df["condition"] = metadata["condition"].values
var_ratio = pca.explained_variance_ratio_
```

### R (Seurat) — export to CSV

```r
library(Seurat)
obj <- readRDS("seurat_processed.rds")

pca_coords <- as.data.frame(Embeddings(obj, "pca")[, 1:2])
colnames(pca_coords) <- c("PC1", "PC2")
pca_coords$condition <- obj$condition
pca_coords$sample_id <- colnames(obj)
write.csv(pca_coords, "pca_data.csv", row.names = FALSE)

# Variance explained
var_explained <- Stdev(obj, "pca")^2
var_ratio <- var_explained / sum(var_explained)
write.csv(
    data.frame(PC = seq_along(var_ratio), variance_ratio = var_ratio),
    "pca_variance.csv",
    row.names = FALSE,
)
```

### R (prcomp) — export to CSV

```r
pca_result <- prcomp(t(count_matrix), scale. = TRUE)
pca_coords <- as.data.frame(pca_result$x[, 1:2])
colnames(pca_coords) <- c("PC1", "PC2")
pca_coords$condition <- metadata$condition
write.csv(pca_coords, "pca_data.csv", row.names = FALSE)

var_ratio <- pca_result$sdev^2 / sum(pca_result$sdev^2)
write.csv(
    data.frame(PC = seq_along(var_ratio), variance_ratio = var_ratio),
    "pca_variance.csv",
    row.names = FALSE,
)
```

## UltraPlot Implementation

```python
import numpy as np
import pandas as pd
import matplotlib as mpl
import ultraplot as uplt

# Publication palette (muted earthy tones — default)
PUBLICATION_PALETTE = [
    "#3A5BA0", "#D4753C", "#5A8F5A", "#C44E52", "#7B5EA7",
    "#E8A838", "#46878F", "#B07AA1", "#2E86C1", "#8C6D31",
    "#4E9A9A", "#D98880", "#6B8E23", "#9B59B6", "#1ABC9C",
    "#86714D", "#8EC9EB", "#6E2F84", "#F5A623", "#7BC657",
    "#708090", "#8B4513", "#C5A9D8", "#D35400", "#B8860B",
    "#E2DBA4", "#C0D0CB", "#E46571", "#90141A", "#2E5111",
]

# Okabe-Ito (colorblind-safe fallback)
OKABE_ITO = [
    "#E69F00", "#56B4E9", "#009E73", "#F0E442",
    "#0072B2", "#D55E00", "#CC79A7", "#000000",
]


def plot_pca(
    df,
    color_col,
    var_ratio=None,
    pc1_col="PC1",
    pc2_col="PC2",
    label_col=None,
    figsize=(3.5, 3.5),
    title="",
    palette=None,
    point_size=30,
    alpha=0.8,
    show_ellipses=False,
    save_path=None,
):
    """Plot a publication-ready PCA scatter plot.

    Scatter plot of PC1 vs PC2 colored by a categorical variable.
    Optionally displays variance explained on axes, sample labels,
    and 95% confidence ellipses per group.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with PC coordinates and a categorical column.
    color_col : str
        Column name for the categorical variable used for coloring.
    var_ratio : array-like of float or None, optional
        Variance explained ratio per PC (e.g., [0.35, 0.18, ...]).
        If provided, the first two values are shown on axis labels.
        Default None.
    pc1_col : str, optional
        Column name for PC1. Default 'PC1'.
    pc2_col : str, optional
        Column name for PC2. Default 'PC2'.
    label_col : str or None, optional
        Column name for point labels (e.g., sample IDs). If provided,
        labels are placed with adjustText to avoid overlaps.
        Default None.
    figsize : tuple of float, optional
        Figure size in inches (width, height). Default (3.5, 3.5).
    title : str, optional
        Figure title. Default ''.
    palette : list of str or None, optional
        List of hex color strings. If None, uses Okabe-Ito palette.
    point_size : float, optional
        Marker size for scatter points. Default 30.
    alpha : float, optional
        Marker transparency. Default 0.8.
    show_ellipses : bool, optional
        If True, draw 95% confidence ellipses per group. Default False.
    save_path : str or None, optional
        Base path for saving (without extension). If provided, saves
        both SVG and PNG to this path. Default None.

    Returns
    -------
    tuple of (Figure, Axes)
        The ultraplot Figure and Axes objects.
    """
    mpl.rcParams["svg.fonttype"] = "none"

    if palette is None:
        palette = PUBLICATION_PALETTE

    categories = df[color_col].astype("category").cat.categories
    color_map = {cat: palette[i % len(palette)] for i, cat in enumerate(categories)}

    # Build axis labels with variance explained
    if var_ratio is not None:
        xlabel = f"PC1 ({var_ratio[0] * 100:.1f}% variance)"
        ylabel = f"PC2 ({var_ratio[1] * 100:.1f}% variance)"
    else:
        xlabel = "PC1"
        ylabel = "PC2"

    fig, ax = uplt.subplot(figsize=figsize)

    for cat in categories:
        mask = df[color_col] == cat
        subset = df.loc[mask]
        ax.scatter(
            subset[pc1_col],
            subset[pc2_col],
            c=color_map[cat],
            s=point_size,
            alpha=alpha,
            label=str(cat),
            edgecolors="white",
            linewidths=0.3,
            zorder=3,
        )

        # 95% confidence ellipse
        if show_ellipses and mask.sum() >= 3:
            _draw_confidence_ellipse(
                ax,
                subset[pc1_col].values,
                subset[pc2_col].values,
                color=color_map[cat],
            )

    # Add sample labels with adjustText
    if label_col is not None:
        try:
            from adjustText import adjust_text
        except ImportError:
            from adjustText import adjust_text

        texts = []
        for _, row in df.iterrows():
            texts.append(
                ax.text(
                    row[pc1_col],
                    row[pc2_col],
                    str(row[label_col]),
                    fontsize=6,
                    ha="center",
                    va="center",
                )
            )
        adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", color="grey", lw=0.5))

    ax.format(
        xlabel=xlabel,
        ylabel=ylabel,
        title=title,
    )

    ax.legend(
        loc="best",
        ncols=1,
        fontsize=7,
        frameon=True,
        framealpha=0.8,
    )

    if save_path is not None:
        fig.savefig(f"{save_path}.svg", bbox_inches="tight")
        fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax


def _draw_confidence_ellipse(ax, x, y, color, n_std=1.96, alpha=0.15):
    """Draw a 95% confidence ellipse for a 2D point cloud.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes object to draw on.
    x : array-like of float
        X-coordinates.
    y : array-like of float
        Y-coordinates.
    color : str
        Fill and edge color for the ellipse.
    n_std : float, optional
        Number of standard deviations for the ellipse radius.
        Default 1.96 (95% confidence).
    alpha : float, optional
        Fill transparency. Default 0.15.

    Returns
    -------
    None
        Draws directly on the provided Axes.
    """
    from matplotlib.patches import Ellipse
    import numpy as np

    cov = np.cov(x, y)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    order = eigenvalues.argsort()[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]

    angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
    width = 2 * n_std * np.sqrt(eigenvalues[0])
    height = 2 * n_std * np.sqrt(eigenvalues[1])

    ellipse = Ellipse(
        xy=(np.mean(x), np.mean(y)),
        width=width,
        height=height,
        angle=angle,
        facecolor=color,
        edgecolor=color,
        alpha=alpha,
        linewidth=1,
        linestyle="--",
        zorder=1,
    )
    ax.add_patch(ellipse)
```

## Usage Examples

### Basic PCA plot

```python
import pandas as pd

pca_df = pd.read_csv("pca_data.csv")
var_df = pd.read_csv("pca_variance.csv")
var_ratio = var_df["variance_ratio"].values

fig, ax = plot_pca(
    pca_df,
    color_col="condition",
    var_ratio=var_ratio,
    title="PCA — Treatment vs Control",
    save_path="./results/pca_condition",
)
```

### PCA with sample labels and confidence ellipses

```python
fig, ax = plot_pca(
    pca_df,
    color_col="tissue",
    var_ratio=var_ratio,
    label_col="sample_id",
    show_ellipses=True,
    point_size=50,
    title="PCA — Tissue Origin",
    save_path="./results/pca_tissue_labeled",
)
```

## Caption Template

> **PCA of [N] samples colored by [condition/tissue/batch].** PC1 and PC2 explain [X]% and [Y]% of total variance, respectively. [If ellipses: Ellipses represent 95% confidence intervals per group.] Data normalized by [method] prior to PCA. n = [N] samples across [K] groups.
