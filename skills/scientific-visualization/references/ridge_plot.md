# Ridge Plot

Publication-ready ridge plots for comparing the distribution of one continuous feature across multiple groups. Use when you want stacked density curves with in-panel group labels and a compact publication-style layout.

## When to Use

- Comparing the full distribution of one continuous variable across groups
- Showing how gene expression, pathway scores, concentrations, or QC metrics shift between conditions
- Displaying multiple related distributions in a compact stacked layout
- Replacing boxplots or violins when the main visual message is the density shape

## Core Principle

`pubplot` keeps plotting separate from data extraction.

- **Plotting functions expect a pandas DataFrame**
- **AnnData / Seurat examples below are only for preparing that DataFrame**
- The plotting API operates on long-format grouped data, independent of source object type

## Input Data

The plotting function in `pubplot/ridge.py` expects a **long-format pandas DataFrame**.

Required inputs:
- one categorical grouping column
- one numeric value column
- one explicit `feature_name` string used as the title above the frame

Example:

```text
group,value
Healthy,0.42
Healthy,0.55
Healthy,0.61
Moderate,1.20
Moderate,1.44
Severe,1.85
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
- the result should be a long-format DataFrame with at least a group column and a value column

#### Gene expression by metadata group

```python
import numpy as np
import pandas as pd

gene = "CCL5"
values = adata[:, gene].X
values = values.A1 if hasattr(values, "A1") else np.asarray(values).ravel()

ridge_df = pd.DataFrame(
    {
        "group": adata.obs["cell_type"].astype(str).values,
        "value": values,
    }
)
```

#### Score or QC metric from `obs`

```python
import numpy as np
import pandas as pd

ridge_df = pd.DataFrame(
    {
        "group": adata.obs["condition"].astype(str).values,
        "value": adata.obs["module_score"].astype(float).values,
    }
)

# Example: log-transform a highly skewed metric before plotting
ridge_df["value"] = np.log1p(adata.obs["total_counts"].astype(float).values)
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

ridge_df <- data.frame(
  group = obj$celltype,
  value = FetchData(obj, vars = "CCL5")[, 1]
)

write.csv(ridge_df, "ridge_data.csv", row.names = FALSE)
```

#### QC metric or score export from Seurat

```r
library(Seurat)

obj <- readRDS("seurat_processed.rds")

ridge_df <- data.frame(
  group = obj$condition,
  value = log1p(obj$nCount_RNA)
)

write.csv(ridge_df, "ridge_qc_data.csv", row.names = FALSE)
```

#### Load in pandas

```python
import pandas as pd

ridge_df = pd.read_csv("ridge_data.csv")
```

## `pubplot` Implementation

Source of truth: `pubplot/ridge.py`

This module exposes one main plotting function:

```python
from pubplot.ridge import plot_ridge
```

API:

```python
plot_ridge(
    df,
    group_col,
    value_col,
    feature_name,
    groups_to_plot=None,
    colors=None,
    figsize=(4.2, 4.8),
    xlim=None,
    bw_method=0.25,
    fill_alpha=1.0,
    baseline_lw=1.8,
    frame_lw=2.0,
    feature_loc=(0.5, 1.02),
    group_label_fontsize=15,
    save_path=None,
    save_fmt="png",
)
```

## Behavior Implemented in `pubplot/ridge.py`

### Group filtering and ordering

- If `groups_to_plot` is provided, it determines which groups are plotted and in what order
- Otherwise, groups are taken from `df[group_col]` in first-appearance order after dropping missing values
- Groups with fewer than 2 non-missing values are removed automatically
- If no valid groups remain, the function raises:

```python
ValueError("No groups with enough values to draw densities.")
```

### KDE behavior

- Density curves are computed with `scipy.stats.gaussian_kde`
- `bw_method=0.25` by default
- If a group's values have near-zero variance, the code adds tiny Gaussian noise before KDE so the density can still be estimated
- Each density is scaled to a maximum height of `0.82` within its ridge band

### Color logic

- If `colors=None`, the function uses `RIDGE_REFERENCE_COLORS`
- If fewer colors are supplied than groups, colors are recycled
- The same color is used for:
  - ridge fill
  - density outline
  - horizontal baseline

### X-axis limits and ticks

- If `xlim=None`, limits are computed from the data
- The lower bound is rounded down to one decimal place and clipped at zero with:

```python
x_min = min(0, floor(min_value * 10) / 10)
```

- The upper bound is rounded up to one decimal place
- Major tick spacing is chosen automatically from the x-range:
  - span `<= 4` → step `1`
  - span `<= 8` → step `2`
  - span `<= 20` → step `5`
  - otherwise → step `10`
- Minor ticks are disabled

### Layout and labels

- Group labels are placed **inside the panel on the right**
- The `feature_name` is drawn above the frame using `feature_loc`
- Feature title font size is auto-scaled by name length via `_feature_fontsize(...)`
- The y-axis is hidden completely
- The plot uses a full rectangular frame

### Saving behavior

- If `save_path=None`, nothing is written to disk
- If `save_path` is provided, parent directories are created automatically
- `save_fmt="png"` saves PNG only
- `save_fmt="svg"` saves SVG only
- `save_fmt="both"` saves both PNG and SVG

## Aesthetic Notes

These rules reflect the actual implementation in `pubplot/ridge.py`.

- Compact stacked ridges with no legend
- In-panel group labels on the right
- Feature title centered above the frame
- Full rectangular border
- White background, no grid
- Heavy x-axis tick styling for the publication look

## Usage Examples

### Basic ridge plot

```python
import pandas as pd
from pubplot.ridge import plot_ridge

ridge_df = pd.read_csv("ridge_data.csv")

fig, ax = plot_ridge(
    ridge_df,
    group_col="group",
    value_col="value",
    feature_name="CCL5",
    save_path="./results/ridge_CCL5",
    save_fmt="both",
)
```

### Subset and order groups

```python
fig, ax = plot_ridge(
    ridge_df,
    group_col="group",
    value_col="value",
    feature_name="CCL5",
    groups_to_plot=["Healthy", "Moderate", "Severe"],
    save_path="./results/ridge_subset",
    save_fmt="both",
)
```

### Custom x-range and bandwidth

```python
fig, ax = plot_ridge(
    ridge_df,
    group_col="group",
    value_col="value",
    feature_name="Module score",
    xlim=(0, 5),
    bw_method=0.4,
    save_path="./results/ridge_score",
    save_fmt="both",
)
```

### Custom colors

```python
fig, ax = plot_ridge(
    ridge_df,
    group_col="group",
    value_col="value",
    feature_name="QC metric",
    colors=["#8EC9EB", "#C5A9D8", "#6E2F84"],
    save_path="./results/ridge_custom_colors",
    save_fmt="both",
)
```

## Colormap Recommendations

| Data encoding | Colors | Notes |
|---------------|--------|-------|
| Ridge groups (default) | `RIDGE_REFERENCE_COLORS` | Matches the intended reference style |
| More flexible categorical styling | `PUBLICATION_PALETTE` | Use when custom grouping requires different tones |
| Ordered progression | same-hue light → dark | Useful when groups have biological order |
| Highlight one group | one accent + muted others | Useful when one condition is the main message |

## Customization Notes

- **`feature_name`** is mandatory and functions as the visual title above the frame
- **`groups_to_plot`** is the main filtering and ordering parameter
- **`bw_method`** controls smoothness; smaller values preserve local structure, larger values smooth more aggressively
- **`xlim`** should be set manually when you need strict cross-figure comparability
- **Ridge plots work best when each group has enough observations to support density estimation**
- **For highly skewed variables, transform first** (for example with `log1p`) before plotting
- **No legend is needed** because the group labels are drawn directly in the panel

## Caption Template

> **Ridge plot of {feature_name} across {grouping}.** Each ridge shows the kernel density estimate of the distribution within one group. Group labels are shown inside the panel. Plot generated with `pubplot` using publication-style ridge defaults.
