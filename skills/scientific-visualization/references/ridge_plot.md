# Ridge Plot

Publication-ready ridge plots for showing the distribution of expression, concentration, score, or QC metrics across groups.

## When to Use

- Comparing the full distribution of one continuous feature across multiple groups
- Showing how a gene, score, concentration, or QC metric shifts between conditions or cell subsets
- Displaying many related group distributions in a compact stacked layout
- Replacing boxplots/violins when the visual goal is smooth distribution shape rather than summary statistics

## Input Data

Expected input: a DataFrame in long format with these columns:

| Column | Type | Description |
|--------|------|-------------|
| `group` | str | Categorical grouping variable (e.g., `Healthy`, `Severe`, `CD8 T cells`) |
| `value` | float | Continuous feature to visualize (expression, score, concentration, QC metric) |

Example CSV:
```csv
group,value
Healthy,0.42
Healthy,0.55
Healthy,0.61
Moderate,1.20
Moderate,1.44
Severe,1.85
```

## Data Extraction

### Python (AnnData / scanpy)

```python
import numpy as np
import pandas as pd

# Gene expression
feature = "CCL5"
values = adata[:, feature].X
values = values.A1 if hasattr(values, "A1") else np.asarray(values).ravel()

ridge_df = pd.DataFrame(
    {
        "group": adata.obs["cell_type"].astype(str).values,
        "value": values,
    }
)
```

### Python (AnnData obs-level score / QC metric)

```python
import numpy as np
import pandas as pd

ridge_df = pd.DataFrame(
    {
        "group": adata.obs["cell_type"].astype(str).values,
        "value": adata.obs["pct_counts_mt"].astype(float).values,
    }
)

# Example for total counts on a more compact scale
ridge_df["value"] = np.log1p(adata.obs["total_counts"].astype(float).values)
```

### R (Seurat) — export to CSV

```r
library(Seurat)
obj <- readRDS("seurat_processed.rds")

# Gene expression
ridge_df <- data.frame(
  group = obj$celltype,
  value = FetchData(obj, vars = "CCL5")[, 1]
)
write.csv(ridge_df, "ridge_data.csv", row.names = FALSE)

# QC metric / score
ridge_qc_df <- data.frame(
  group = obj$celltype,
  value = log1p(obj$nCount_RNA)
)
write.csv(ridge_qc_df, "ridge_qc_data.csv", row.names = FALSE)
```

## Python Implementation

```python
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde
from matplotlib.ticker import MultipleLocator, NullLocator

mpl.rcParams["svg.fonttype"] = "none"
mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
        "font.size": 8,
        "axes.labelsize": 9,
        "axes.titlesize": 10,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
    }
)

PUBLICATION_PALETTE = [
    "#3A5BA0", "#D4753C", "#5A8F5A", "#C44E52", "#7B5EA7",
    "#E8A838", "#46878F", "#B07AA1", "#2E86C1", "#8C6D31",
    "#4E9A9A", "#D98880", "#6B8E23", "#9B59B6", "#1ABC9C",
    "#86714D", "#8EC9EB", "#6E2F84", "#F5A623", "#7BC657",
    "#708090", "#8B4513", "#C5A9D8", "#D35400", "#B8860B",
    "#E2DBA4", "#C0D0CB", "#E46571", "#90141A", "#2E5111",
]

RIDGE_REFERENCE_COLORS = [
    "#8EC9EB",  # light sky blue
    "#C5A9D8",  # soft lavender
    "#8E72A9",  # medium purple
    "#6E2F84",  # deep plum
    "#F5A623",  # orange
    "#D4C33F",  # mustard yellow
    "#86C95A",  # fresh green
    "#1C9A46",  # deep green
]


def _feature_fontsize(feature_name):
    n = len(feature_name)
    if n <= 8:
        return 18
    if n <= 14:
        return 15
    if n <= 22:
        return 12
    return 10


def _major_tick_step(xlim):
    span = xlim[1] - xlim[0]
    if span <= 4:
        return 1
    if span <= 8:
        return 2
    if span <= 20:
        return 5
    return 10


def plot_ridge(
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
):
    """Plot a publication-style ridge plot.

    Stacked kernel density curves are drawn on separate baselines, with
    group labels inside the panel and the feature name centered above the
    frame.

    Parameters
    ----------
    df : pandas.DataFrame
        Long-format table containing the data.
    group_col : str
        Column name for the grouping variable.
    value_col : str
        Column name for the continuous feature.
    feature_name : str
        Name of the feature shown above the plot.
    groups_to_plot : list of str or None, optional
        Groups to include and their order. If None, all groups are used.
    colors : list of str or None, optional
        Fill/baseline colors for each group. If None, uses the ridge
        reference colors.
    figsize : tuple of float, optional
        Figure size in inches. Default (4.2, 4.8).
    xlim : tuple of float or None, optional
        X-axis limits. If None, computed from the data.
    bw_method : float or str, optional
        KDE bandwidth passed to scipy.stats.gaussian_kde. Default 0.25.
    fill_alpha : float, optional
        Fill opacity. Default 1.0.
    baseline_lw : float, optional
        Line width of each group baseline. Default 1.8.
    frame_lw : float, optional
        Line width of the rectangular frame. Default 2.0.
    feature_loc : tuple of float, optional
        Position of the feature label in axes coordinates. Default
        (0.5, 1.02), centered above the frame.
    group_label_fontsize : float, optional
        Font size for the group labels inside the plot. Default 15.
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.

    Returns
    -------
    tuple of (Figure, Axes)
        The matplotlib Figure and Axes objects.
    """
    groups = groups_to_plot or df[group_col].dropna().unique().tolist()
    data_by_group = [df.loc[df[group_col] == group, value_col].dropna().to_numpy() for group in groups]
    groups = [g for g, arr in zip(groups, data_by_group) if len(arr) > 1]
    data_by_group = [arr for arr in data_by_group if len(arr) > 1]

    if not groups:
        raise ValueError("No groups with enough values to draw densities.")

    if colors is None:
        colors = RIDGE_REFERENCE_COLORS[: len(groups)]
    if len(colors) < len(groups):
        colors = [colors[i % len(colors)] for i in range(len(groups))]

    all_values = np.concatenate(data_by_group)
    if xlim is None:
        x_min = min(0, float(np.floor(all_values.min() * 10) / 10))
        x_max = float(np.ceil(all_values.max() * 10) / 10)
        xlim = (x_min, x_max)

    x_grid = np.linspace(xlim[0], xlim[1], 400)
    y_positions = np.arange(len(groups))[::-1]

    fig, ax = plt.subplots(figsize=figsize)

    max_height = 0
    for y0, group, values, color in zip(y_positions, groups, data_by_group, colors):
        kde = gaussian_kde(values, bw_method=bw_method)
        density = kde(x_grid)
        density = density / density.max() * 0.82
        max_height = max(max_height, density.max())

        ax.fill_between(x_grid, y0, y0 + density, color=color, alpha=fill_alpha, linewidth=0)
        ax.plot(x_grid, y0 + density, color=color, linewidth=1.4)
        ax.hlines(y0, xlim[0], xlim[1], color=color, linewidth=baseline_lw)

        ax.text(
            xlim[1] - 0.01 * (xlim[1] - xlim[0]),
            y0 + density.max() * 0.38,
            group,
            ha="right",
            va="center",
            fontsize=group_label_fontsize,
            color="#1F1B20",
        )

    ax.text(
        feature_loc[0],
        feature_loc[1],
        feature_name,
        transform=ax.transAxes,
        ha="center",
        va="bottom",
        fontsize=_feature_fontsize(feature_name),
        fontweight="bold",
        clip_on=False,
    )

    ax.set_xlim(xlim)
    ax.set_ylim(-0.05, y_positions.max() + max_height + 0.12)
    ax.set_yticks([])
    ax.set_ylabel("")
    ax.set_xlabel("")

    ax.xaxis.set_major_locator(MultipleLocator(_major_tick_step(xlim)))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_minor_locator(NullLocator())
    ax.tick_params(axis="x", width=1.6, length=10, labelsize=28, pad=12)
    ax.tick_params(axis="y", length=0)

    for spine in ax.spines.values():
        spine.set_visible(True)
        spine.set_linewidth(frame_lw)
        spine.set_color("black")

    ax.grid(False)
    ax.set_facecolor("white")
    fig.patch.set_facecolor("white")

    fig.tight_layout(pad=0.6)

    if save_path is not None:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path.with_suffix(".png"), dpi=300, bbox_inches="tight")
        fig.savefig(save_path.with_suffix(".svg"), dpi=300, bbox_inches="tight")

    return fig, ax
```

## Colormap Recommendations

| Data encoding | Colormap | Notes |
|---------------|----------|-------|
| Ridge groups (reference style) | `RIDGE_REFERENCE_COLORS` | Closely matches the provided ridge plot example |
| General categorical groups | `PUBLICATION_PALETTE` | Use when more flexibility or more categories are needed |
| Ordered groups / progression | Same-hue light → dark progression | Best when group order has biological meaning |
| Highlight one group | One accent + muted others | Use when one condition is the main message |

## Customization Notes

- **Rectangular frame**: Keep all four spines visible. This is part of the intended style.
- **Feature title placement**: Center the feature name above the frame, not inside the plotting area.
- **Group labels**: Place labels inside the panel on the right side. This avoids the need for a legend.
- **Axis style**: Use only the x-axis. Hide all y-axis ticks and labels.
- **Minimal x-axis ticks**: Use sparse integer major ticks only. Never show dense intermediate ticks.
- **Bandwidth (`bw_method`)**: Lower values preserve local peaks; higher values smooth noisy distributions.
- **Best use case**: Ridge plots work best for 4-10 groups. Too many groups can become cramped.
- **Expression vs QC**: The same function can be used for genes, pathway scores, module scores, concentrations, or QC metrics.
- **Scale choice**: For highly skewed variables like total counts, use `log1p` before plotting.
