# PCA Plot

Publication-ready PCA scatter plot with variance explained on the axes. Use when visualizing the first two principal components colored by a categorical annotation, with optional point labels.

## When to Use

- Showing sample structure in the first two principal components
- Coloring PCA coordinates by condition, tissue, batch, or another categorical variable
- Displaying variance explained on the PC1 / PC2 axes
- Adding sample labels when the number of points is small enough to keep the plot readable

## Core Principle

`pubplot` keeps plotting separate from data extraction.

- **Plotting functions expect a pandas DataFrame**
- **AnnData / Seurat examples below are only for preparing that DataFrame**
- The plotting API operates on tabular PCA coordinates and metadata, independent of source object type

## Input Data

The plotting function in `pubplot/pca.py` expects a **pandas DataFrame**.

Required inputs:
- one column for PC1 coordinates
- one column for PC2 coordinates
- one categorical column for coloring

Optional inputs:
- one label column for sample or point labels
- one variance-ratio vector (`var_ratio`) supplied separately

Example:

```text
PC1,PC2,condition,sample_id
-4.12,1.44,Control,S1
-3.88,1.62,Control,S2
2.31,-0.88,Treatment,S3
```

Typical categorical columns:
- `condition`
- `tissue`
- `batch`
- `sample_group`

## Data Extraction

These examples show how to prepare the plotting DataFrame. They are **not** part of the plotting library itself.

### Python (AnnData)

General principle:
- PCA coordinates come from `adata.obsm["X_pca"]`
- sample metadata comes from `adata.obs[...]`
- explained variance comes from `adata.uns["pca"]["variance_ratio"]`

#### PCA coordinates + metadata

```python
import pandas as pd

pca_df = pd.DataFrame(
    adata.obsm["X_pca"][:, :2],
    columns=["PC1", "PC2"],
    index=adata.obs_names,
)
pca_df["condition"] = adata.obs["condition"].astype(str).values
pca_df["sample_id"] = adata.obs_names.astype(str)

var_ratio = adata.uns["pca"]["variance_ratio"]
```

### Python (scikit-learn / custom matrix)

```python
from sklearn.decomposition import PCA
import pandas as pd

pca = PCA(n_components=2)
coords = pca.fit_transform(data_matrix)

pca_df = pd.DataFrame(coords, columns=["PC1", "PC2"])
pca_df["condition"] = metadata["condition"].astype(str).values

var_ratio = pca.explained_variance_ratio_
```

### R (Seurat) → CSV → pandas

General principle:
- extract PCA coordinates from Seurat embeddings
- add metadata columns in R
- export coordinates to CSV
- export variance explained separately if needed
- load both in pandas

#### Export from Seurat

```r
library(Seurat)

obj <- readRDS("seurat_processed.rds")

pca_coords <- as.data.frame(Embeddings(obj, "pca")[, 1:2])
colnames(pca_coords) <- c("PC1", "PC2")
pca_coords$condition <- obj$condition
pca_coords$sample_id <- colnames(obj)
write.csv(pca_coords, "pca_data.csv", row.names = FALSE)

var_explained <- Stdev(obj, "pca")^2
var_ratio <- var_explained / sum(var_explained)
write.csv(
  data.frame(PC = seq_along(var_ratio), variance_ratio = var_ratio),
  "pca_variance.csv",
  row.names = FALSE
)
```

#### Load in pandas

```python
import pandas as pd

pca_df = pd.read_csv("pca_data.csv")
var_df = pd.read_csv("pca_variance.csv")
var_ratio = var_df["variance_ratio"].values
```

## `pubplot` Implementation

Source of truth: `pubplot/pca.py`

This module exposes one main plotting function:

```python
from pubplot.pca import plot_pca
```

API:

```python
plot_pca(
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
    save_path=None,
    save_fmt="png",
)
```

## Behavior Implemented in `pubplot/pca.py`

### Color logic

- If `palette=None`, the function uses `PUBLICATION_PALETTE`
- Categories are taken from `df[color_col].astype("category").cat.categories`
- Colors are assigned in category order and recycled if needed

### Axis labels

- If `var_ratio` is provided, axis labels are formatted as:

```python
PC1 ({var_ratio[0] * 100:.1f}% variance)
PC2 ({var_ratio[1] * 100:.1f}% variance)
```

- If `var_ratio=None`, axes are labeled simply `PC1` and `PC2`

### Scatter styling

- Each category is plotted separately
- `point_size` is passed directly to `ax.scatter(..., s=point_size)`
- Points are fully opaque (`alpha=1.0`)
- Points have black outlines with `linewidths=0.3`

### Label behavior

- If `label_col` is provided, the function adds text labels for every row in `df`
- Labels are adjusted with `adjustText.adjust_text(...)` to reduce overlap
- Connecting arrows are drawn in grey when labels are moved

### Legend behavior

- A legend is always drawn
- The legend uses:
  - `loc="best"`
  - `fontsize=7`
  - `frameon=True`
  - `framealpha=0.8`

### Saving behavior

- If `save_path=None`, nothing is written to disk
- `save_fmt="png"` saves PNG only
- `save_fmt="svg"` saves SVG only
- `save_fmt="both"` saves both PNG and SVG

## Aesthetic Notes

These rules reflect the actual implementation in `pubplot/pca.py`.

- Publication palette by default
- Black point outlines for separation
- Variance explained shown on axes when available
- Optional point labels with overlap adjustment
- Standard framed PCA legend

## Usage Examples

### Basic PCA plot

```python
import pandas as pd
from pubplot.pca import plot_pca

pca_df = pd.read_csv("pca_data.csv")
var_df = pd.read_csv("pca_variance.csv")
var_ratio = var_df["variance_ratio"].values

fig, ax = plot_pca(
    pca_df,
    color_col="condition",
    var_ratio=var_ratio,
    title="PCA — Treatment vs Control",
    save_path="./results/pca_condition",
    save_fmt="both",
)
```

### PCA with sample labels

```python
fig, ax = plot_pca(
    pca_df,
    color_col="tissue",
    var_ratio=var_ratio,
    label_col="sample_id",
    point_size=50,
    title="PCA — Tissue origin",
    save_path="./results/pca_tissue_labeled",
    save_fmt="both",
)
```

### Custom PC column names

```python
fig, ax = plot_pca(
    df=pca_df,
    color_col="batch",
    var_ratio=var_ratio,
    pc1_col="PC1",
    pc2_col="PC2",
    title="PCA — Batch structure",
    save_path="./results/pca_batch",
    save_fmt="both",
)
```

## Customization Notes

- **`var_ratio`** should contain at least the first two explained-variance values when provided
- **`label_col`** is best used for smaller datasets; labeling many points will still become crowded even with `adjustText`
- **`point_size`** is passed directly to matplotlib scatter, so increase it explicitly when plotting very few samples
- **`palette`** should remain categorical and colorblind-friendly
- **The function does not draw confidence ellipses**; the reference should not assume ellipse support unless the code is changed

## Caption Template

> **PCA of {N} samples colored by {grouping}.** PC1 and PC2 explain {X}% and {Y}% of the total variance, respectively. [If labels are shown: Sample identifiers are annotated directly on the plot.] Plot generated with `pubplot` using publication-style PCA defaults.
