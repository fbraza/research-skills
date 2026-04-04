# Enrichment Dot Plot

Publication-ready dot plot for GSEA or ORA enrichment results (e.g., from clusterProfiler, fgsea, gseapy).

## Input Data

Expected input: a CSV or DataFrame with columns:
- `Description` or `pathway` — pathway/term name
- `p.adjust` or `padj` — adjusted p-value
- `Count` or `size` — number of genes in the overlap
- `GeneRatio` or `NES` — gene ratio (for ORA) or normalized enrichment score (for GSEA)
- Optional: `category` — pathway database (GO:BP, KEGG, Reactome, etc.)

Example:
```
Description,GeneRatio,p.adjust,Count
Immune response,0.15,1.2e-8,45
Cell cycle regulation,0.12,3.4e-6,38
Apoptotic process,0.09,8.7e-5,28
Cytokine signaling,0.08,1.1e-4,22
```

## Data Extraction

### Python (gseapy)

```python
import pandas as pd
import gseapy as gp

# ORA results
enr = gp.enrichr(gene_list=deg_genes, gene_sets="GO_Biological_Process_2023")
enr_df = enr.results[["Term", "Overlap", "Adjusted P-value", "Genes"]].copy()
enr_df.columns = ["Description", "GeneRatio", "p.adjust", "Genes"]
enr_df["Count"] = enr_df["Genes"].str.split(";").str.len()

# GSEA results
gsea = gp.prerank(rnk=rank_df, gene_sets="KEGG_2021_Human")
gsea_df = gsea.res2d[["Term", "NES", "FDR q-val", "Lead_genes"]].copy()
gsea_df.columns = ["Description", "NES", "p.adjust", "Lead_genes"]
gsea_df["Count"] = gsea_df["Lead_genes"].str.split(";").str.len()
```

### R (clusterProfiler) — export to CSV

```r
library(clusterProfiler)

# ORA
ego <- enrichGO(gene = deg_genes, OrgDb = org.Hs.eg.db, ont = "BP")
write.csv(as.data.frame(ego), "enrichment_ora.csv", row.names = FALSE)

# GSEA
gsea_res <- gseGO(geneList = ranked_genes, OrgDb = org.Hs.eg.db, ont = "BP")
write.csv(as.data.frame(gsea_res), "enrichment_gsea.csv", row.names = FALSE)
```

### R (fgsea) — export to CSV

```r
library(fgsea)

fgsea_res <- fgsea(pathways = gene_sets, stats = ranked_genes)
fgsea_df <- as.data.frame(fgsea_res)
fgsea_df$leadingEdge <- sapply(fgsea_df$leadingEdge, paste, collapse = ";")
write.csv(fgsea_df, "enrichment_fgsea.csv", row.names = FALSE)
```

## UltraPlot Implementation

```python
import numpy as np
import pandas as pd
import matplotlib as mpl
import ultraplot as uplt

# Typography defaults
mpl.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica"],
    "font.size": 8,
    "axes.labelsize": 9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "axes.titlesize": 9,
})


def plot_enrichment_dotplot(
    df,
    pathway_col="Description",
    padj_col="p.adjust",
    count_col="Count",
    ratio_col="GeneRatio",
    top_n=20,
    figsize=(4, 5),
    title="",
    cmap="viridis_r",
    max_label_len=50,
    size_range=(20, 200),
    sort_by="padj",
    save_path=None,
):
    """Plot a publication-ready enrichment dot plot.

    Dot plot showing enriched pathways with dot size proportional to
    gene count and dot color encoding -log10(padj). Suitable for both
    ORA (x-axis = GeneRatio) and GSEA (x-axis = NES) results.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with enrichment results.
    pathway_col : str, optional
        Column name for pathway/term names. Default 'Description'.
    padj_col : str, optional
        Column name for adjusted p-values. Default 'p.adjust'.
    count_col : str, optional
        Column name for gene counts in overlap. Default 'Count'.
    ratio_col : str, optional
        Column name for gene ratio (ORA) or NES (GSEA). Default
        'GeneRatio'.
    top_n : int, optional
        Maximum number of top pathways to display. Default 20.
    figsize : tuple of float, optional
        Figure size in inches (width, height). Default (4, 5).
    title : str, optional
        Figure title. Default ''.
    cmap : str, optional
        Matplotlib colormap name. Default 'viridis_r' (dark = more
        significant).
    max_label_len : int, optional
        Maximum character length for pathway labels before truncation.
        Default 50.
    size_range : tuple of float, optional
        Min and max dot sizes in points^2. Default (20, 200).
    sort_by : str, optional
        Sort pathways by 'padj' (most significant on top) or 'ratio'
        (highest gene ratio on top). Default 'padj'.
    save_path : str or None, optional
        Base path for saving (without extension). If provided, saves
        both SVG and PNG to this path. Default None.

    Returns
    -------
    tuple of (Figure, Axes)
        The ultraplot Figure and Axes objects.
    """
    plot_df = df.copy()

    # Ensure numeric types
    plot_df[padj_col] = pd.to_numeric(plot_df[padj_col], errors="coerce")
    plot_df[count_col] = pd.to_numeric(plot_df[count_col], errors="coerce")
    plot_df[ratio_col] = pd.to_numeric(plot_df[ratio_col], errors="coerce")

    # Handle string GeneRatio like "10/200" from clusterProfiler
    if plot_df[ratio_col].isna().all():
        raw = df[ratio_col].astype(str)
        if raw.str.contains("/").any():
            parts = raw.str.split("/", expand=True).astype(float)
            plot_df[ratio_col] = parts[0] / parts[1]

    # Select top N pathways by significance
    plot_df = plot_df.dropna(subset=[padj_col, ratio_col, count_col])
    plot_df = plot_df.nsmallest(top_n, padj_col)

    # Sort for display
    if sort_by == "padj":
        plot_df = plot_df.sort_values(padj_col, ascending=False)
    else:
        plot_df = plot_df.sort_values(ratio_col, ascending=True)

    # Compute -log10(padj)
    plot_df["neg_log10_padj"] = -np.log10(plot_df[padj_col].clip(lower=1e-300))

    # Truncate long pathway names
    plot_df["label"] = plot_df[pathway_col].apply(
        lambda s: s[:max_label_len] + "..." if len(str(s)) > max_label_len else str(s)
    )

    # Scale dot sizes to size_range
    count_min = plot_df[count_col].min()
    count_max = plot_df[count_col].max()
    if count_max > count_min:
        plot_df["dot_size"] = (
            (plot_df[count_col] - count_min) / (count_max - count_min)
            * (size_range[1] - size_range[0])
            + size_range[0]
        )
    else:
        plot_df["dot_size"] = np.mean(size_range)

    # Plot
    fig, ax = uplt.subplot(figsize=figsize)

    scatter = ax.scatter(
        plot_df[ratio_col],
        np.arange(len(plot_df)),
        s=plot_df["dot_size"],
        c=plot_df["neg_log10_padj"],
        cmap=cmap,
        edgecolors="black",
        linewidths=0.3,
        zorder=3,
    )

    # Y-axis: pathway names
    ax.set_yticks(np.arange(len(plot_df)))
    ax.set_yticklabels(plot_df["label"].values, fontsize=7)

    # Determine x-axis label based on data type
    is_gsea = (plot_df[ratio_col] < 0).any()
    x_label = "NES" if is_gsea else "Gene Ratio"

    ax.format(
        xlabel=x_label,
        ylabel="",
        title=title,
    )

    # Colorbar for -log10(padj)
    fig.colorbar(scatter, label="$-\\log_{10}$(padj)", loc="right", width=0.1)

    # Size legend for Count
    _add_size_legend(
        ax,
        count_col=count_col,
        count_min=count_min,
        count_max=count_max,
        size_range=size_range,
    )

    if save_path is not None:
        mpl.rcParams["svg.fonttype"] = "none"
        fig.savefig(f"{save_path}.svg", bbox_inches="tight")
        fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax


def _add_size_legend(ax, count_col, count_min, count_max, size_range):
    """Add a size legend showing gene count to dot size mapping.

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        Axes object to add the legend to.
    count_col : str
        Label for the count variable.
    count_min : float
        Minimum gene count in the data.
    count_max : float
        Maximum gene count in the data.
    size_range : tuple of float
        Min and max dot sizes in points^2.

    Returns
    -------
    None
        Adds legend directly to the Axes.
    """
    import matplotlib.lines as mlines

    if count_max <= count_min:
        return

    # Pick 3 representative sizes
    counts = np.linspace(count_min, count_max, 3).astype(int)
    sizes = (
        (counts - count_min) / (count_max - count_min)
        * (size_range[1] - size_range[0])
        + size_range[0]
    )

    handles = [
        mlines.Line2D(
            [], [],
            marker="o",
            color="grey",
            markersize=np.sqrt(s),
            linestyle="None",
            markeredgecolor="black",
            markeredgewidth=0.3,
            label=str(c),
        )
        for c, s in zip(counts, sizes)
    ]

    size_legend = ax.legend(
        handles=handles,
        title=count_col,
        loc="lower right",
        fontsize=6,
        title_fontsize=7,
        frameon=True,
        framealpha=0.8,
    )
    ax.add_artist(size_legend)
```

## Usage Examples

### ORA dot plot

```python
import pandas as pd

enr_df = pd.read_csv("enrichment_ora.csv")
fig, ax = plot_enrichment_dotplot(
    enr_df,
    pathway_col="Description",
    padj_col="p.adjust",
    count_col="Count",
    ratio_col="GeneRatio",
    top_n=15,
    title="GO Biological Process (ORA)",
    save_path="./results/enrichment_ora_dotplot",
)
```

### GSEA dot plot (NES on x-axis)

```python
gsea_df = pd.read_csv("enrichment_gsea.csv")
fig, ax = plot_enrichment_dotplot(
    gsea_df,
    pathway_col="Description",
    padj_col="p.adjust",
    count_col="setSize",
    ratio_col="NES",
    top_n=20,
    cmap="RdBu_r",
    title="KEGG Pathways (GSEA)",
    save_path="./results/enrichment_gsea_dotplot",
)
```

## Colormap Options

| Metric | Cmap | Notes |
|--------|------|-------|
| -log10(padj) | `viridis_r` | Dark = more significant |
| -log10(padj) alt | `magma_r` | Alternative sequential |
| NES (GSEA) | `RdBu_r` | Diverging for positive/negative enrichment |

## Customization Quick Reference

| Parameter | Default | Description |
|-----------|---------|-------------|
| `top_n` | 20 | Maximum pathways to show |
| `max_label_len` | 50 | Truncate pathway names beyond this length |
| `size_range` | (20, 200) | Min/max dot sizes (points^2) |
| `sort_by` | `padj` | Sort by `padj` or `ratio` |
| `cmap` | `viridis_r` | Colormap for -log10(padj) |

## Caption Template

> **Enrichment dot plot of top [N] [GO:BP / KEGG / Reactome] pathways from [ORA / GSEA] analysis.** Dot size represents gene count in the overlap; color encodes -log10(adjusted p-value). [For GSEA: x-axis shows normalized enrichment score (NES).] Background gene set: [description]. Significance threshold: padj <= 0.05. Analysis performed with [clusterProfiler / fgsea / gseapy] v[X.X].
