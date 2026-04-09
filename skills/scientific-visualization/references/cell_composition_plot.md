# Cell Composition Plot

Publication-ready horizontal stacked bar plots for showing sample-wise cell-type composition in single-cell datasets.

## When to Use

- Comparing the proportion of cell subtypes across patients, samples, conditions, or batches
- Summarizing compositional shifts in scRNA-seq or spatial single-cell datasets
- Showing patient-specific or condition-specific abundance structure
- Visualizing a moderate number of discrete subtypes in a compact, publication-style stacked format

## Input Data

Expected input: a DataFrame where rows are samples and columns are cell subtypes, with values representing percentages or proportions.

| Column / Index | Type | Description |
|----------------|------|-------------|
| sample index | str | Sample or patient identifier |
| subtype columns | float | Percentage/proportion of each subtype in the sample |

Example CSV:
```csv
sample,CD4 T cells,CD8 T cells,NK cells,B cells,CD14+ Monocytes,FCGR3A+ Monocytes,Dendritic cells,Megakaryocytes
Patient01,32.5,10.4,8.2,12.0,22.1,9.7,3.8,1.3
Patient02,28.1,14.2,10.6,16.5,18.3,8.9,2.4,1.0
Patient03,35.4,9.7,7.5,10.2,24.0,8.0,4.0,1.2
```

Alternatively, start from cell-level metadata and compute the table from counts.

## Data Extraction

### Python (AnnData / scanpy)

```python
import pandas as pd

# Example: sample-wise cell-type composition
comp = (
    adata.obs.groupby(["sample_id", "cell_type"], observed=False)
    .size()
    .rename("n")
    .reset_index()
)
comp["pct"] = 100 * comp["n"] / comp.groupby("sample_id")["n"].transform("sum")

composition_df = (
    comp.pivot(index="sample_id", columns="cell_type", values="pct")
    .fillna(0)
)
```

### Python (pseudo-samples for testing)

```python
import numpy as np

rng = np.random.default_rng(42)
adata.obs["pseudo_patient"] = rng.choice(["P1", "P2", "P3", "P4"], size=adata.n_obs)

comp = (
    adata.obs.groupby(["pseudo_patient", "cell_type"], observed=False)
    .size()
    .rename("n")
    .reset_index()
)
comp["pct"] = 100 * comp["n"] / comp.groupby("pseudo_patient")["n"].transform("sum")
composition_df = comp.pivot(index="pseudo_patient", columns="cell_type", values="pct").fillna(0)
```

### R (Seurat) — export to CSV

```r
library(dplyr)
library(tidyr)

meta <- obj@meta.data
comp <- meta %>%
  count(sample_id, celltype, name = "n") %>%
  group_by(sample_id) %>%
  mutate(pct = 100 * n / sum(n)) %>%
  ungroup()

composition_df <- comp %>%
  select(sample_id, celltype, pct) %>%
  pivot_wider(names_from = celltype, values_from = pct, values_fill = 0)

write.csv(composition_df, "cell_composition.csv", row.names = FALSE)
```

## Python Implementation

```python
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

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
    "#203161", "#40569A", "#64B024", "#BDD2CB", "#931419",
    "#C04736", "#EBA5AB", "#BEACAE", "#5C6C6B", "#F09F2E",
    "#D83746", "#DA5E28", "#DDDDDB", "#97767A", "#C24935",
]

# Exact reference-inspired palette for <=8 subtypes (panel J)
CELL_COMPOSITION_PALETTE_8 = [
    "#203161",  # dark navy
    "#40569A",  # mid blue
    "#64B024",  # bright green
    "#2E5111",  # deep olive green
    "#BDD2CB",  # pale sage
    "#E2DBA4",  # pale sand
    "#C04736",  # brick rust
    "#931419",  # deep crimson
]

# Exact reference-inspired palette for 9-13 subtypes (panel K)
CELL_COMPOSITION_PALETTE_13 = [
    "#5C6C6B",  # dark grey-green
    "#BDD2CB",  # pale sage
    "#DDDDDB",  # pale grey
    "#97767A",  # muted mauve-brown
    "#BEACAE",  # light taupe-mauve
    "#DA5E28",  # burnt orange
    "#F09F2E",  # warm orange
    "#EBA5AB",  # pale rose
    "#E46571",  # coral pink
    "#D83746",  # red-pink
    "#C24935",  # brick red
    "#C44E52",  # muted red
    "#90141A",  # oxblood
]


def get_cell_composition_palette(n_subtypes):
    """Return the exact reference-inspired palette by subtype count.

    <=8 categories uses the panel-J palette.
    9-13 categories uses the panel-K palette.
    >13 categories raises an error because the plot becomes unreadable.
    """
    if n_subtypes <= 8:
        return CELL_COMPOSITION_PALETTE_8[:n_subtypes]
    if n_subtypes <= 13:
        return CELL_COMPOSITION_PALETTE_13[:n_subtypes]
    raise ValueError(
        "Cell composition plot supports at most 13 subtypes. "
        "This plot will not be readable with more categories; please subset your data."
    )


def build_color_map(groups):
    palette = get_cell_composition_palette(len(groups))
    return {group: color for group, color in zip(groups, palette)}


def plot_cell_composition(
    composition_df,
    color_map=None,
    figsize=(4.3, 3.0),
    title_top="Patient-Specific",
    title_bottom="Cell Subtypes",
    xlabel="Proportion [%]",
    bar_height=0.94,
    legend_title=None,
    save_path=None,
):
    """Plot publication-style cell composition bars.

    Horizontal stacked bars with compact spacing, legend on the right,
    no enclosing frame, and only the bottom x-axis line visible.

    Parameters
    ----------
    composition_df : pandas.DataFrame
        Rows are samples; columns are subtype percentages.
    color_map : dict or None, optional
        Mapping from subtype to color. If None, uses the automatic
        reference-inspired palette selected by subtype count.
    figsize : tuple of float, optional
        Figure size in inches. Default (4.3, 3.0).
    title_top : str, optional
        First title line. Default 'Patient-Specific'.
    title_bottom : str, optional
        Bold second title line. Default 'Cell Subtypes'.
    xlabel : str, optional
        X-axis label. Default 'Proportion [%]'.
    bar_height : float, optional
        Height of each horizontal stacked bar. Default 0.94.
    legend_title : str or None, optional
        Optional legend title. Default None.
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.

    Returns
    -------
    tuple of (Figure, Axes)
        The matplotlib Figure and Axes objects.
    """
    groups = list(composition_df.columns)
    if color_map is None:
        color_map = build_color_map(groups)
    colors = [color_map[g] for g in groups]
    samples = list(composition_df.index)

    fig, ax = plt.subplots(figsize=figsize)

    y = np.arange(len(samples))
    left = np.zeros(len(samples))
    for group, color in zip(groups, colors):
        vals = composition_df[group].to_numpy()
        ax.barh(
            y,
            vals,
            left=left,
            height=bar_height,
            color=color,
            edgecolor="black",
            linewidth=0.7,
            label=group,
        )
        left += vals

    ax.set_xlim(0, 100)
    ax.set_yticks(y)
    ax.set_yticklabels(samples, fontsize=8)
    ax.set_xticks(np.arange(0, 101, 10))
    ax.set_xlabel(xlabel, fontsize=8, labelpad=2)
    ax.invert_yaxis()

    # Minimal axis styling: keep only the bottom x-axis line
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_visible(True)
    ax.spines["bottom"].set_linewidth(0.8)
    ax.spines["bottom"].set_color("black")
    ax.tick_params(axis="x", length=3, width=0.8, pad=1, labelsize=7)
    ax.tick_params(axis="y", length=0, pad=2)
    ax.grid(False)

    ax.text(
        0.5, 1.14, title_top,
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontsize=11, fontweight="normal",
    )
    ax.text(
        0.5, 1.05, title_bottom,
        transform=ax.transAxes,
        ha="center", va="bottom",
        fontsize=10, fontweight="bold",
    )

    handles = [
        Patch(facecolor=color_map[g], edgecolor="black", linewidth=0.6, label=g)
        for g in groups
    ]
    ax.legend(
        handles=handles,
        title=legend_title,
        frameon=False,
        fontsize=8,
        title_fontsize=8,
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        handlelength=0.9,
        handleheight=0.9,
        handletextpad=0.3,
        borderaxespad=0.0,
        labelspacing=0.25,
    )

    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
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
| `<=8` subtypes | `CELL_COMPOSITION_PALETTE_8` | Exact palette logic from panel J of the reference figure |
| `9-13` subtypes | `CELL_COMPOSITION_PALETTE_13` | Exact palette logic from panel K of the reference figure |
| `>13` subtypes | Not allowed | Raise an error; advise subsetting because the plot becomes unreadable |

## Customization Notes

- **Subtype count limit**: This plot style should not be used for more than 13 subtypes. Subset first.
- **Color logic**: Do not improvise colors for this plot type. Use the dedicated reference-inspired palettes.
- **No rectangular frame**: Unlike violin or ridge plots, this figure keeps only the bottom x-axis line.
- **Legend placement**: Put the legend on the right side, vertically centered.
- **Bar outlines**: Keep thin black borders between stacked segments for readability.
- **Compact spacing**: Bars should be tightly packed, similar to the reference figure.
- **Title layout**: Use two centered lines, with the second line bold.
- **X-axis ticks**: Use 0-100 with 10% increments by default.
- **Best use case**: Patient-specific or sample-specific cell-type composition summaries.
