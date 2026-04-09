# UMAP / tSNE / Embedding Plot

Publication-ready dimensionality reduction scatter plots (UMAP, tSNE, PHATE, etc.) for single-cell data, colored by cluster, cell type, or gene expression.

## Aesthetic Principles

These rules are extracted from the user's reference figures (`assets/umap_*.png`) and apply to **all** dimensionality reduction plots.

### 1. Minimal L-shaped Axes (No Full Frame)

No full box frame. No tick marks. No tick numbers. Use short perpendicular axis stubs in the bottom-left corner — two lines forming an L, labeled "UMAP 1" / "UMAP 2" (or tSNE, PHATE, etc.). Embedding coordinates are arbitrary so numerical ticks are meaningless.

### 2. Point Size Scales with Cell Count

| Total cells | Point size (`s=`) | Visual goal |
|-------------|-------------------|-------------|
| > 50,000 | 2 | Dense, solid cluster masses |
| 20,000–50,000 | 5 | Individual points barely distinguishable |
| 10,000–20,000 | 10 | Points visible, clusters clearly separated |
| 5,000–10,000 | 18 | Each point visible |
| 2,000–5,000 | 30 | Large dots, clear separation |
| 500–2,000 | 50 | Every cell individually readable |
| < 500 | 70 | Very large dots |

The function auto-computes point size from cell count if not explicitly provided.

### 3. Fully Opaque Points with Dark Edge Contours

- **No transparency** — `alpha=1.0` on every point. Clusters appear as solid colored masses.
- **Dark edge on every point** — `edgecolors` set to a darkened version of the fill color (factor 0.4), `linewidths=0.4` for large points, `0.2` for small points. This gives each dot a visible contour. Where dots overlap in dense regions, the edges naturally blend into the mass; at boundaries and isolated points, individual circles are clearly defined.

### 4. Legend Only — No Centroid Labels

Use a simple legend to the right of the plot. Do not place text labels on the plot itself — keep the visualization clean. The legend uses small colored dots matching the cluster colors.

### 5. Custom Publication Palette

The default palette uses muted, earthy, saturated-but-not-neon tones inspired by Nature/Cell paper aesthetics.

```python
PUBLICATION_PALETTE = [
    "#3A5BA0",  # muted navy blue
    "#D4753C",  # burnt orange
    "#5A8F5A",  # forest green
    "#C44E52",  # brick red
    "#7B5EA7",  # dusty purple
    "#E8A838",  # warm gold
    "#46878F",  # teal
    "#B07AA1",  # mauve
    "#2E86C1",  # steel blue
    "#8C6D31",  # olive/khaki
    "#4E9A9A",  # sage teal
    "#D98880",  # dusty rose
    "#6B8E23",  # olive drab
    "#9B59B6",  # muted violet
    "#1ABC9C",  # muted aquamarine
    "#86714D",  # warm brown
    "#8EC9EB",  # light sky blue
    "#6E2F84",  # deep plum
    "#F5A623",  # bright amber / saffron
    "#7BC657",  # fresh leaf green
    "#708090",  # slate grey
    "#8B4513",  # saddle brown
    "#C5A9D8",  # soft lavender
    "#D35400",  # pumpkin
    "#B8860B",  # dark goldenrod
    "#E2DBA4",  # pale sand
    "#C0D0CB",  # pale sage
    "#E46571",  # coral pink
    "#90141A",  # oxblood
    "#2E5111",  # deep olive green
]

# Fallback for accessibility-critical contexts
OKABE_ITO = [
    "#E69F00", "#56B4E9", "#009E73", "#F0E442",
    "#0072B2", "#D55E00", "#CC79A7", "#000000",
]
```

### 6. Feature Plot Colormap: Magma

For gene expression overlays, use `magma` (dark → orange → bright yellow). Low/no expression cells are dark purple-black, high expression pops in warm yellow. The colorbar is placed above the plot with "Min" / "Max" labels. Gene name in *italics* as the plot title. No edge contours on feature plot points (`edgecolors="none"`).

### 7. Clean Background

White background, no grid lines, no spines except the L-shaped stubs.

---

## Input Data

Expected input: a CSV or DataFrame with columns:
- `UMAP1` / `UMAP2` (or `tSNE1` / `tSNE2`) — embedding coordinates
- `cell_type` or `cluster` — categorical annotation for coloring
- Optional: continuous values (gene expression) for feature plots

## Data Extraction

### Python (AnnData / scanpy)

```python
import pandas as pd
import scanpy as sc

adata = sc.read_h5ad("adata_processed.h5ad")

# UMAP coordinates + metadata
umap_df = pd.DataFrame(
    adata.obsm["X_umap"],
    columns=["UMAP1", "UMAP2"],
    index=adata.obs_names,
)
umap_df["cell_type"] = adata.obs["cell_type"].values
umap_df["cluster"] = adata.obs["leiden"].values

# For feature plots (gene expression overlay)
gene = "CD3D"
umap_df[gene] = adata[:, gene].X.toarray().flatten()

# tSNE (if computed)
tsne_df = pd.DataFrame(
    adata.obsm["X_tsne"],
    columns=["tSNE1", "tSNE2"],
    index=adata.obs_names,
)
```

### R (Seurat) — export to CSV

```r
library(Seurat)
obj <- readRDS("seurat_processed.rds")

# UMAP
umap_coords <- as.data.frame(Embeddings(obj, reduction = "umap"))
colnames(umap_coords) <- c("UMAP1", "UMAP2")
umap_coords$cell_type <- obj$cell_type
umap_coords$cluster <- obj$seurat_clusters
write.csv(umap_coords, "umap_data.csv", row.names = FALSE)

# For feature plot
gene_expr <- GetAssayData(obj, assay = "RNA", layer = "data")["CD3D", ]
umap_coords$CD3D <- as.numeric(gene_expr)
write.csv(umap_coords, "umap_feature_data.csv", row.names = FALSE)
```

## UltraPlot Implementation

```python
import numpy as np
import pandas as pd
import matplotlib as mpl
import matplotlib.colors as mcolors
import ultraplot as uplt

# ── Palettes ─────────────────────────────────────────────────────────

PUBLICATION_PALETTE = [
    "#3A5BA0", "#D4753C", "#5A8F5A", "#C44E52", "#7B5EA7",
    "#E8A838", "#46878F", "#B07AA1", "#2E86C1", "#8C6D31",
    "#4E9A9A", "#D98880", "#6B8E23", "#9B59B6", "#1ABC9C",
    "#86714D", "#8EC9EB", "#6E2F84", "#F5A623", "#7BC657",
    "#708090", "#8B4513", "#C5A9D8", "#D35400", "#B8860B",
    "#E2DBA4", "#C0D0CB", "#E46571", "#90141A", "#2E5111",
]

OKABE_ITO = [
    "#E69F00", "#56B4E9", "#009E73", "#F0E442",
    "#0072B2", "#D55E00", "#CC79A7", "#000000",
]


# ── Helpers ──────────────────────────────────────────────────────────

def _auto_point_size(n_cells):
    """Compute point size based on total cell count.

    Sizes ensure dots overlap in dense regions (solid mass effect)
    while remaining individually visible at boundaries.

    Parameters
    ----------
    n_cells : int
        Total number of cells/points to plot.

    Returns
    -------
    float
        Recommended marker size (matplotlib `s` parameter).
    """
    if n_cells > 50_000:
        return 2.0
    elif n_cells > 20_000:
        return 5.0
    elif n_cells > 10_000:
        return 10.0
    elif n_cells > 5_000:
        return 18.0
    elif n_cells > 2_000:
        return 30.0
    elif n_cells > 500:
        return 50.0
    else:
        return 70.0


def _darken_color(hex_color, factor=0.6):
    """Darken a hex color by a factor for edge coloring.

    Parameters
    ----------
    hex_color : str
        Hex color string (e.g., '#D4753C').
    factor : float, optional
        Darkening factor (0 = black, 1 = unchanged). Default 0.6.

    Returns
    -------
    str
        Darkened hex color string.
    """
    rgb = mcolors.to_rgb(hex_color)
    return mcolors.to_hex(tuple(c * factor for c in rgb))


def _draw_axis_stubs(ax, embedding_type="UMAP", stub_length_frac=0.12):
    """Draw minimal L-shaped axis stubs in the bottom-left corner.

    Removes all spines, ticks, and tick labels. Draws two short line
    segments (an L shape) to indicate axis directions, with labels.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axes to modify.
    embedding_type : str, optional
        Label prefix for axes (e.g., 'UMAP', 'tSNE', 'PHATE').
        Default 'UMAP'.
    stub_length_frac : float, optional
        Length of each stub as a fraction of the axis range.
        Default 0.12.
    """
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel("")
    ax.set_ylabel("")

    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    x_range = xlim[1] - xlim[0]
    y_range = ylim[1] - ylim[0]

    pad_x = 0.03 * x_range
    pad_y = 0.03 * y_range
    origin_x = xlim[0] + pad_x
    origin_y = ylim[0] + pad_y
    stub_x = stub_length_frac * x_range
    stub_y = stub_length_frac * y_range

    ax.annotate(
        "", xy=(origin_x + stub_x, origin_y), xytext=(origin_x, origin_y),
        arrowprops=dict(arrowstyle="-", color="black", lw=1.2),
        annotation_clip=False,
    )
    ax.annotate(
        "", xy=(origin_x, origin_y + stub_y), xytext=(origin_x, origin_y),
        arrowprops=dict(arrowstyle="-", color="black", lw=1.2),
        annotation_clip=False,
    )

    ax.text(
        origin_x + stub_x / 2, origin_y - 0.03 * y_range,
        f"{embedding_type} 1", ha="center", va="top", fontsize=8,
    )
    ax.text(
        origin_x - 0.03 * x_range, origin_y + stub_y / 2,
        f"{embedding_type} 2", ha="right", va="center", fontsize=8,
        rotation=90,
    )


# ── Main Functions ───────────────────────────────────────────────────

def plot_embedding_categorical(
    df,
    x_col,
    y_col,
    color_col,
    embedding_type="UMAP",
    figsize=(4, 3.5),
    title="",
    palette=None,
    point_size=None,
    show_legend=True,
    save_path=None,
):
    """Plot a categorical-colored embedding (UMAP, tSNE, PHATE, etc.).

    Scatter plot of 2D embedding coordinates colored by a categorical
    variable. Points are fully opaque with darkened edge contours.
    Uses the publication palette and auto-scales point size based on
    cell count. Axes are rendered as minimal L-shaped stubs.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with embedding coordinates and a categorical column.
    x_col : str
        Column name for the x-axis coordinate (e.g., 'UMAP1').
    y_col : str
        Column name for the y-axis coordinate (e.g., 'UMAP2').
    color_col : str
        Column name for the categorical variable used for coloring.
    embedding_type : str, optional
        Label prefix for axes: 'UMAP', 'tSNE', 'PHATE', etc.
        Default 'UMAP'.
    figsize : tuple of float, optional
        Figure size in inches (width, height). Default (4, 3.5).
    title : str, optional
        Figure title. Default ''.
    palette : list of str or None, optional
        List of hex color strings. If None, uses PUBLICATION_PALETTE.
    point_size : float or None, optional
        Marker size. If None, auto-computed from cell count.
    show_legend : bool, optional
        Whether to show a legend. Default True.
    save_path : str or None, optional
        Base path for saving (without extension). Saves SVG and PNG.
        Default None.

    Returns
    -------
    tuple of (Figure, Axes)
        The ultraplot Figure and Axes objects.
    """
    mpl.rcParams["svg.fonttype"] = "none"

    if palette is None:
        palette = PUBLICATION_PALETTE

    n_cells = len(df)
    if point_size is None:
        point_size = _auto_point_size(n_cells)

    categories = df[color_col].astype("category").cat.categories
    color_map = {cat: palette[i % len(palette)] for i, cat in enumerate(categories)}

    fig, ax = uplt.subplot(figsize=figsize)

    # Shuffle to avoid plotting order bias
    df_shuffled = df.sample(frac=1, random_state=42)

    # All points: fully opaque, dark edge contours on every dot
    for cat in categories:
        mask = df_shuffled[color_col] == cat
        if not mask.any():
            continue
        fill_color = color_map[cat]
        edge_color = _darken_color(fill_color, 0.4)
        ax.scatter(
            df_shuffled.loc[mask, x_col],
            df_shuffled.loc[mask, y_col],
            c=fill_color,
            s=point_size,
            alpha=1.0,
            edgecolors=edge_color,
            linewidths=0.4 if point_size >= 15 else 0.2,
            label=str(cat),
            zorder=2,
            rasterized=True,
        )

    ax.format(title=title, titlesize=9, titleweight="bold")
    _draw_axis_stubs(ax, embedding_type=embedding_type)

    if show_legend:
        ax.legend(
            loc="right", ncols=1, fontsize=6, markersize=5,
            frameon=False, handletextpad=0.4, columnspacing=1.0,
        )

    if save_path is not None:
        fig.savefig(f"{save_path}.svg", bbox_inches="tight")
        fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax


def plot_embedding_continuous(
    df,
    x_col,
    y_col,
    value_col,
    embedding_type="UMAP",
    figsize=(3.5, 3.5),
    title="",
    cmap="magma",
    point_size=None,
    cbar_label="norm. Expression",
    save_path=None,
):
    """Plot a continuous-colored embedding (feature plot / gene expression).

    Scatter plot of 2D embedding colored by a continuous variable.
    Points are fully opaque with no edge contours. Sorted so high
    values plot on top. Uses magma colormap by default. Gene names
    are displayed in italics as the plot title.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with embedding coordinates and a continuous column.
    x_col : str
        Column name for the x-axis coordinate (e.g., 'UMAP1').
    y_col : str
        Column name for the y-axis coordinate (e.g., 'UMAP2').
    value_col : str
        Column name for the continuous variable (e.g., gene name).
    embedding_type : str, optional
        Label prefix for axes. Default 'UMAP'.
    figsize : tuple of float, optional
        Figure size in inches (width, height). Default (3.5, 3.5).
    title : str, optional
        Figure title. If empty, uses value_col in italics. Default ''.
    cmap : str, optional
        Colormap name. Default 'magma'.
    point_size : float or None, optional
        Marker size. If None, auto-computed from cell count.
    cbar_label : str, optional
        Label for the colorbar. Default 'norm. Expression'.
    save_path : str or None, optional
        Base path for saving (without extension). Saves SVG and PNG.
        Default None.

    Returns
    -------
    tuple of (Figure, Axes)
        The ultraplot Figure and Axes objects.
    """
    mpl.rcParams["svg.fonttype"] = "none"

    n_cells = len(df)
    if point_size is None:
        point_size = _auto_point_size(n_cells)

    # Sort so high-expression cells plot on top
    df_sorted = df.sort_values(value_col, ascending=True)

    fig, ax = uplt.subplot(figsize=figsize)

    scatter = ax.scatter(
        df_sorted[x_col],
        df_sorted[y_col],
        c=df_sorted[value_col],
        cmap=cmap,
        s=point_size,
        alpha=1.0,
        edgecolors="none",
        rasterized=True,
        zorder=2,
    )

    display_title = title if title else f"$\\it{{{value_col}}}$"
    ax.format(title=display_title, titlesize=9, titleweight="normal")

    _draw_axis_stubs(ax, embedding_type=embedding_type)

    cbar = fig.colorbar(scatter, loc="top", width=0.08, length=0.5)
    cbar.set_label(cbar_label, fontsize=7)
    cbar.set_ticks([df_sorted[value_col].min(), df_sorted[value_col].max()])
    cbar.set_ticklabels(["Min", "Max"])
    cbar.ax.tick_params(labelsize=7)

    if save_path is not None:
        fig.savefig(f"{save_path}.svg", bbox_inches="tight")
        fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax
```

## Usage Examples

### Categorical embedding (cell type)

```python
import pandas as pd

umap_df = pd.read_csv("umap_data.csv")
fig, ax = plot_embedding_categorical(
    umap_df,
    x_col="UMAP1",
    y_col="UMAP2",
    color_col="cell_type",
    embedding_type="UMAP",
    title="Cell Type Annotation",
    save_path="./results/umap_cell_type",
)
```

### Feature plot (gene expression)

```python
umap_df = pd.read_csv("umap_feature_data.csv")
fig, ax = plot_embedding_continuous(
    umap_df,
    x_col="UMAP1",
    y_col="UMAP2",
    value_col="GZMB",
    embedding_type="UMAP",
    save_path="./results/umap_GZMB_expression",
)
```

## Colormap Options

| Data | Cmap | Notes |
|------|------|-------|
| Cell types (default) | `PUBLICATION_PALETTE` | Muted earthy tones, up to 20 categories |
| Cell types (accessibility) | `OKABE_ITO` | Colorblind-safe fallback, up to 8 categories |
| Gene expression | `magma` | Dark → orange → yellow; low expression is dark |
| Gene expression (alt) | `inferno` | Similar to magma, slightly more yellow at top |
| Score / continuous metric | `viridis` | Perceptually uniform, good for generic scores |

## Customization Notes

- **`point_size=None`**: Auto-sizing is the default. Override only when the auto result doesn't look right for your specific dataset geometry.
- **`palette`**: Pass `OKABE_ITO` explicitly when accessibility is the primary concern.
- **Edge contours**: Every point has a darkened edge (`factor=0.4`). `linewidths` auto-adjusts — `0.4` for large points (s >= 15), `0.2` for small points. In dense regions, overlapping dots naturally hide interior edges while boundary dots remain individually defined.
- **Feature plot sorting**: Points are sorted ascending so high-expression cells always render on top.
- **Rasterization**: Scatter points are rasterized (`rasterized=True`) to keep SVG file sizes manageable. Text and axis elements remain vector for Illustrator editing.
- **No centroid labels**: Keep the plot clean. Use the legend for cluster identification.

## Caption Template

> **{embedding_type} visualization of {N} cells colored by {variable}.** Embedding computed with n_neighbors={X}, min_dist={Y}, using {N_PCs} principal components. [For tSNE: perplexity={Z}.] Clusters identified by Leiden algorithm at resolution {R}. n = {total cells} cells from {N} samples.
