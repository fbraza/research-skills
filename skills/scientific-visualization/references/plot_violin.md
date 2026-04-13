# Violin Plot

Publication-ready violin plots for comparing the distribution of a continuous variable across categorical groups. Use when you want to show distribution shape together with optional individual points.

## When to Use

- Comparing a continuous measurement across multiple groups
- Showing distribution shape rather than only summary statistics
- Overlaying individual observations as jittered points
- Creating final publication figures from long-format tabular data

## Core Principle

`pubplot` keeps plotting separate from data extraction.

- **Plotting functions expect a pandas DataFrame**
- **AnnData / Seurat examples below are only for preparing that DataFrame**
- The plotting API operates on long-format grouped data, independent of source object type

## Input Data

The plotting function in `pubplot/violin.py` expects a **long-format pandas DataFrame**.

Required columns:
- one categorical grouping column
- one numeric value column

Example:

```text
group,value
Control,5.2
Control,4.8
Control,5.5
Treatment,8.1
Treatment,7.6
Treatment,8.3
```

Typical grouping columns:
- `cell_type`
- `condition`
- `cluster`
- `batch`
- `sample_group`

Typical value columns:
- gene expression
- module score
- pathway score
- QC metric
- concentration / abundance / intensity

## Data Extraction

These examples show how to prepare the DataFrame. They are **not** part of the plotting library itself.

### Python (AnnData)

General principle:
- group labels usually come from `adata.obs[...]`
- values come from either `adata.obs[...]` or the expression matrix
- the result should be a two-column or multi-column long-format DataFrame

#### Gene expression by metadata group

```python
import numpy as np
import pandas as pd

gene = "CCL5"
values = adata[:, gene].X
values = values.A1 if hasattr(values, "A1") else np.asarray(values).ravel()

violin_df = pd.DataFrame(
    {
        "group": adata.obs["cell_type"].astype(str).values,
        "value": values,
    }
)
```

#### Score or QC metric from `obs`

```python
import pandas as pd

violin_df = pd.DataFrame(
    {
        "group": adata.obs["condition"].astype(str).values,
        "value": adata.obs["module_score"].astype(float).values,
    }
)
```

### R (Seurat) → CSV → pandas

General principle:
- extract the grouping variable from Seurat metadata
- extract the continuous value from metadata or expression matrix
- write a CSV in R
- load the CSV in pandas
- pass the DataFrame to `pubplot`

#### Gene expression export from Seurat

```r
library(Seurat)

obj <- readRDS("seurat_processed.rds")

violin_df <- data.frame(
  group = obj$cell_type,
  value = FetchData(obj, vars = "CCL5")[, 1]
)

write.csv(violin_df, "violin_data.csv", row.names = FALSE)
```

#### Metadata score export from Seurat

```r
library(Seurat)

obj <- readRDS("seurat_processed.rds")

violin_df <- data.frame(
  group = obj$condition,
  value = obj$module_score
)

write.csv(violin_df, "violin_score_data.csv", row.names = FALSE)
```

#### Load in pandas

```python
import pandas as pd

violin_df = pd.read_csv("violin_data.csv")
```

## `pubplot` Implementation

Source of truth: `pubplot/violin.py`

This module exposes one main plotting function:

```python
from pubplot.violin import plot_violinplot
```

API:

```python
plot_violinplot(
    df,
    group_col,
    value_col,
    figsize=(3.5, 3),
    title="",
    ylabel="",
    palette=None,
    show_points=True,
    point_size=0.5,
    alpha=1.0,
    jitter_width=0.15,
    orient="v",
    groups_to_plot=None,
    order=None,
    uniform_color=None,
    point_color="black",
    legend_loc="upper left",
    legend_bbox_to_anchor=None,
    save_path=None,
    save_fmt="png",
)
```

## Behavior Implemented in `pubplot/violin.py`

### Group-selection logic

- If `groups_to_plot` is provided, only those groups are kept
- If `order` is provided, it determines the displayed order of the retained groups
- If no valid groups remain, the function raises a `ValueError`

### Color logic

- If `palette=None`, the function uses `PUBLICATION_PALETTE`
- **8 groups or fewer**:
  - one color per group
  - legend shown
  - category axis labels hidden
- **More than 8 groups**:
  - all violins use `uniform_color` if provided, otherwise `PUBLICATION_PALETTE[0]`
  - no legend
  - group labels shown on the categorical axis

### Point overlay

If `show_points=True`, the function overlays jittered points using:
- `point_color` for all points
- `point_size` passed directly to `ax.scatter(..., s=point_size)`
- `alpha` for point opacity
- `jitter_width` for horizontal or vertical jitter depending on orientation

### Axes and frame

- The plot uses a **closed rectangular frame** with all four spines visible
- Grid lines are disabled
- Tick styling is minimal and outward-facing
- For vertical orientation, `ylabel` is used as the y-axis label
- For horizontal orientation, `ylabel` is used as the x-axis label

### Saving behavior

- If `save_path=None`, output defaults to `./results/violinplot`
- `save_fmt="png"` saves PNG only
- `save_fmt="svg"` saves SVG only
- `save_fmt="both"` saves both PNG and SVG

## Aesthetic Notes

These rules reflect the actual implementation in `pubplot/violin.py`.

- Publication palette by default
- Black violin outlines
- Optional black jittered points
- Full rectangular frame
- Sparse numeric ticks only
- Legend used only for smaller group counts

## Usage Examples

### Basic violin plot

```python
import pandas as pd
from pubplot.violin import plot_violinplot

violin_df = pd.read_csv("violin_data.csv")

fig, ax = plot_violinplot(
    violin_df,
    group_col="group",
    value_col="value",
    title="CCL5",
    ylabel="Expression level",
    save_path="./results/violin_CCL5",
    save_fmt="both",
)
```

### Subset and order groups

```python
fig, ax = plot_violinplot(
    violin_df,
    group_col="group",
    value_col="value",
    groups_to_plot=["CD8 T", "NK", "Mono"],
    order=["Mono", "CD8 T", "NK"],
    ylabel="Expression level",
    save_path="./results/violin_subset",
    save_fmt="both",
)
```

### Many-group case with uniform violin color

```python
fig, ax = plot_violinplot(
    violin_df,
    group_col="group",
    value_col="value",
    uniform_color="#3A5BA0",
    point_color="black",
    ylabel="Score",
    save_path="./results/violin_many_groups",
    save_fmt="both",
)
```

### Horizontal orientation

```python
fig, ax = plot_violinplot(
    violin_df,
    group_col="group",
    value_col="value",
    orient="h",
    ylabel="Expression level",
    save_path="./results/violin_horizontal",
    save_fmt="both",
)
```

## Customization Notes

- **`groups_to_plot`** is the main filtering parameter
- **`order`** lets you reorder groups after filtering
- **`orient="h"`** is useful when group labels are long
- **`point_size`** in this implementation is passed directly to `scatter(s=...)`, so small numbers produce very small dots
- **`show_points=True`** is generally recommended when sample size is modest
- **Violin plots require enough observations to show meaningful density**; for very small groups, interpretation should be cautious

## Caption Template

> **Violin plot of {value} across {grouping}.** Each violin summarizes the distribution within one group; black points indicate individual observations when shown. Plot generated with `pubplot` using publication-style violin defaults.
