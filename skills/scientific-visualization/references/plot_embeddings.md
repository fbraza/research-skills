# Embedding Plot

Publication-ready 2D embedding plots for UMAP, tSNE, PHATE, diffusion maps, and related dimensionality-reduction layouts. Use when visualizing cells, samples, or observations in a low-dimensional embedding colored by categorical annotations or continuous values.

## When to Use

- Plotting **UMAP**, **tSNE**, **PHATE**, or other 2D embeddings
- Coloring embeddings by **cell type**, **cluster**, **condition**, **batch**, or other categorical metadata
- Overlaying **gene expression**, **module scores**, or other continuous values on an embedding
- Creating final publication figures from a precomputed embedding

## Core Principle

`pubplot` keeps plotting separate from data extraction.

- **Plotting functions expect a pandas DataFrame**
- **AnnData / Seurat examples below are only for preparing that DataFrame**
- The plotting API is **embedding-agnostic**: the same functions work for UMAP, tSNE, PHATE, etc.

## Aesthetic Principles

These rules are derived from the reference images in `assets/` and are implemented by `pubplot/umap.py`.

### 1. Minimal L-shaped Axes

No full frame. No tick marks. No tick numbers. Use short axis stubs in the bottom-left corner labeled with the embedding type (e.g. `UMAP 1`, `UMAP 2`, `tSNE 1`, `PHATE 2`). Embedding coordinates are arbitrary, so numeric tick labels are usually meaningless.

### 2. Point Size Scales with Observation Count

| Total points | Point size (`s=`) |
|--------------|-------------------|
| > 50,000 | 0.20 |
| 20,001–50,000 | 0.5 |
| 10,001–20,000 | 1.0 |
| 5,001–10,000 | 2.0 |
| 2,001–5,000 | 4.0 |
| 501–2,000 | 16.0 |
| <= 500 | 32 |

This logic is built into `pubplot.umap._auto_point_size()` and used automatically when `point_size=None`.

### 3. Fully Opaque Categorical Points with Dark Edge Contours

Categorical embedding plots use:

- `alpha=1.0`
- one fill color per category
- a darkened edge color on every point
- slightly thinner outlines for very small points

This creates solid cluster masses in dense regions while preserving point boundaries at the edges.

### 4. Legend Only for Categorical Embeddings

Do not place text labels directly on the embedding. Use a legend instead.

### 5. Continuous Overlays Use `magma`

Feature plots should default to `magma`:

- low values: dark purple / black
- high values: orange / yellow

The colorbar sits above the panel and is labeled with `Min` / `Max`.

### 6. Clean White Background

No grid lines. No enclosing frame beyond the L-shaped axis stubs.

## Input Data

The plotting functions in `pubplot/umap.py` expect a **pandas DataFrame**.

### Categorical embedding input

Expected columns:
- one x-coordinate column
- one y-coordinate column
- one categorical annotation column

Example:

```text
UMAP1,UMAP2,cell_type
4.21,-1.02,CD8 T
4.19,-0.98,CD8 T
-2.10,3.41,B cell
```

Typical choices:
- coordinates: `UMAP1` / `UMAP2`, `tSNE1` / `tSNE2`, `PHATE1` / `PHATE2`
- categorical column: `cell_type`, `cluster`, `batch`, `condition`

### Continuous embedding input

Expected columns:
- one x-coordinate column
- one y-coordinate column
- one continuous value column

Example:

```text
UMAP1,UMAP2,GZMB
4.21,-1.02,2.31
4.19,-0.98,2.44
-2.10,3.41,0.02
```

Typical continuous values:
- gene expression
- module score
- QC metric
- pseudotime
- pathway score

## Data Extraction

These examples show how to prepare the DataFrame. They are **not** part of the plotting library itself.

### Python (AnnData)

General principle:
- embedding coordinates come from `adata.obsm[...]`
- categorical metadata comes from `adata.obs[...]`
- continuous overlays come from either `adata.obs[...]` or the expression matrix

#### Categorical embedding DataFrame

```python
import pandas as pd

embedding_df = pd.DataFrame(
    adata.obsm["X_umap"],
    columns=["UMAP1", "UMAP2"],
    index=adata.obs_names,
)
embedding_df["cell_type"] = adata.obs["cell_type"].astype(str).values
embedding_df["batch"] = adata.obs["batch"].astype(str).values
```

#### Continuous embedding DataFrame from expression

```python
import numpy as np
import pandas as pd

gene = "GZMB"
expr = adata[:, gene].X
expr = expr.A1 if hasattr(expr, "A1") else np.asarray(expr).ravel()

feature_df = pd.DataFrame(
    adata.obsm["X_umap"],
    columns=["UMAP1", "UMAP2"],
    index=adata.obs_names,
)
feature_df[gene] = expr
```

#### Continuous embedding DataFrame from `obs`

```python
score_df = pd.DataFrame(
    adata.obsm["X_umap"],
    columns=["UMAP1", "UMAP2"],
    index=adata.obs_names,
)
score_df["module_score"] = adata.obs["module_score"].astype(float).values
```

The same pattern applies to tSNE or other embeddings:

```python
tsne_df = pd.DataFrame(
    adata.obsm["X_tsne"],
    columns=["tSNE1", "tSNE2"],
    index=adata.obs_names,
)
tsne_df["cluster"] = adata.obs["leiden"].astype(str).values
```

### R (Seurat) → CSV → pandas

General principle:
- extract embedding coordinates from `Embeddings(...)`
- add metadata from the Seurat object
- write a CSV from R
- load that CSV in pandas
- pass the resulting DataFrame to `pubplot`

#### Categorical embedding export from Seurat

```r
library(Seurat)

obj <- readRDS("seurat_processed.rds")

umap_coords <- as.data.frame(Embeddings(obj, reduction = "umap"))
colnames(umap_coords) <- c("UMAP1", "UMAP2")
umap_coords$cell_type <- obj$cell_type
umap_coords$batch <- obj$batch
umap_coords$cluster <- obj$seurat_clusters

write.csv(umap_coords, "umap_data.csv", row.names = FALSE)
```

#### Continuous feature export from Seurat

```r
library(Seurat)

obj <- readRDS("seurat_processed.rds")

umap_coords <- as.data.frame(Embeddings(obj, reduction = "umap"))
colnames(umap_coords) <- c("UMAP1", "UMAP2")

expr <- GetAssayData(obj, assay = "RNA", layer = "data")["GZMB", ]
umap_coords$GZMB <- as.numeric(expr)

write.csv(umap_coords, "umap_feature_data.csv", row.names = FALSE)
```

#### Load in pandas

```python
import pandas as pd

umap_df = pd.read_csv("umap_data.csv")
feature_df = pd.read_csv("umap_feature_data.csv")
```

## `pubplot` Implementation

Source of truth: `pubplot/umap.py`

This module exposes two main plotting functions:

```python
from pubplot.umap import (
    plot_embedding_categorical,
    plot_embedding_continuous,
)
```

### `plot_embedding_categorical`

Use for metadata-like annotations such as:
- cell type
- cluster
- batch
- condition
- sample ID

API:

```python
plot_embedding_categorical(
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
    save_fmt="png",
)
```

Behavior implemented in `pubplot/umap.py`:
- auto point-size scaling from total observation count
- category-wise coloring using `PUBLICATION_PALETTE` by default
- darkened edge contours on all points
- shuffled plotting order to reduce category-order bias
- L-shaped axis stubs with `embedding_type` labels
- optional legend
- optional export to PNG / SVG

### `plot_embedding_continuous`

Use for continuous overlays such as:
- gene expression
- module scores
- QC metrics
- pseudotime
- pathway scores

API:

```python
plot_embedding_continuous(
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
)
```

Behavior implemented in `pubplot/umap.py`:
- auto point-size scaling from total observation count
- points sorted so high values are plotted on top
- no edge outlines for continuous overlays
- italic title when `title=""` (uses `value_col`)
- top colorbar with `Min` / `Max` tick labels
- L-shaped axis stubs with `embedding_type` labels

## Usage Examples

### Categorical embedding

```python
import pandas as pd
from pubplot.umap import plot_embedding_categorical

umap_df = pd.read_csv("umap_data.csv")

fig, ax = plot_embedding_categorical(
    umap_df,
    x_col="UMAP1",
    y_col="UMAP2",
    color_col="cell_type",
    embedding_type="UMAP",
    title="Cell type annotation",
    save_path="./results/umap_cell_type",
    save_fmt="both",
)
```

### Continuous feature plot

```python
import pandas as pd
from pubplot.umap import plot_embedding_continuous

feature_df = pd.read_csv("umap_feature_data.csv")

fig, ax = plot_embedding_continuous(
    feature_df,
    x_col="UMAP1",
    y_col="UMAP2",
    value_col="GZMB",
    embedding_type="UMAP",
    save_path="./results/umap_GZMB",
)
```

### Same API for tSNE

```python
fig, ax = plot_embedding_categorical(
    tsne_df,
    x_col="tSNE1",
    y_col="tSNE2",
    color_col="batch",
    embedding_type="tSNE",
    title="Batch structure",
    save_path="./results/tsne_batch",
    save_fmt="both",
)
```

## Colormap Options

| Data | Default | Notes |
|------|---------|-------|
| Categorical embeddings | `PUBLICATION_PALETTE` | Muted publication-style palette |
| Accessibility-critical categorical | `OKABE_ITO` | Use explicitly when needed |
| Gene expression / feature plot | `magma` | Default for continuous overlays |
| Generic continuous metric | `viridis` | Good alternative for scores / QC |

## Customization Notes

- **`embedding_type`** controls the axis-stub labels only. Use values like `"UMAP"`, `"tSNE"`, or `"PHATE"`.
- **`x_col` / `y_col`** can be named however you want; the function does not require specific column names.
- **`point_size=None`** is recommended unless a figure needs manual tuning.
- **`palette`** should be categorical and colorblind-friendly.
- **`show_legend=False`** is useful for very high-cardinality annotations.
- **Continuous overlays** should generally avoid edge outlines to reduce clutter.
- **Scatter points are rasterized** in the implementation to keep SVG size manageable while preserving vector text and axes.

## Caption Template

> **{embedding_type} visualization of {N} observations colored by {variable}.** Coordinates were extracted from a precomputed {embedding_type} embedding. [For continuous plots: color encodes {value description}.] Plot generated with `pubplot` using publication-style embedding defaults.
