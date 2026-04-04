# Volcano Plot

Publication-ready volcano plot for differential expression results from DESeq2 or pyDESeq2. Use when visualizing genome-wide differential expression to highlight significantly up- and down-regulated genes simultaneously.

## When to Use

- After running DESeq2 or pyDESeq2 differential expression analysis
- To show the relationship between fold change magnitude and statistical significance
- To identify and label the most significant differentially expressed genes
- Standard figure in any bulk RNA-seq or proteomics DE publication

## Input Data

Expected input: a DataFrame from DESeq2/pyDESeq2 results with these columns:

| Column | Type | Description |
|--------|------|-------------|
| `gene` (or index) | str | Gene identifiers |
| `log2FoldChange` | float | Log2 fold change |
| `padj` | float | BH-adjusted p-value |
| `baseMean` (optional) | float | Mean normalized expression |

Example CSV:
```
gene,baseMean,log2FoldChange,lfcSE,stat,pvalue,padj
BRCA1,1523.4,2.31,0.45,5.13,2.9e-7,1.2e-5
TP53,892.1,-1.87,0.38,-4.92,8.6e-7,3.1e-5
MYC,2104.7,0.12,0.31,0.39,0.697,0.842
```

## UltraPlot Implementation

```python
import numpy as np
import pandas as pd
import ultraplot as uplt
import matplotlib as mpl
from adjustText import adjust_text


def plot_volcano(
    df,
    lfc_threshold=1.0,
    padj_threshold=0.05,
    top_n=10,
    gene_col="gene",
    lfc_col="log2FoldChange",
    padj_col="padj",
    marker_size=12,
    alpha_ns=0.4,
    alpha_sig=0.7,
    figsize=(3.5, 3.5),
    title="",
    save_path=None,
):
    """Plot a publication-ready volcano plot from DE results.

    Classifies genes as Up, Down, or Not Significant based on fold change
    and adjusted p-value thresholds. Labels the top N most significant genes.

    Parameters
    ----------
    df : pandas.DataFrame
        Differential expression results. Must contain columns for gene IDs,
        log2 fold change, and adjusted p-value.
    lfc_threshold : float, optional
        Absolute log2 fold change threshold for significance, by default 1.0.
    padj_threshold : float, optional
        Adjusted p-value threshold for significance, by default 0.05.
    top_n : int, optional
        Number of top significant genes to label, by default 10.
    gene_col : str, optional
        Column name for gene identifiers, by default "gene".
        If "index", uses the DataFrame index.
    lfc_col : str, optional
        Column name for log2 fold change values, by default "log2FoldChange".
    padj_col : str, optional
        Column name for adjusted p-values, by default "padj".
    marker_size : float, optional
        Size of scatter points, by default 12.
    alpha_ns : float, optional
        Transparency for non-significant points, by default 0.4.
    alpha_sig : float, optional
        Transparency for significant points, by default 0.7.
    figsize : tuple of float, optional
        Figure dimensions in inches (width, height), by default (3.5, 3.5).
    title : str, optional
        Plot title, by default "".
    save_path : str or None, optional
        Base path for saving (without extension). Saves both SVG and PNG.
        If None, saves to ./results/volcano_plot, by default None.

    Returns
    -------
    fig : ultraplot.Figure
        The figure object.
    ax : ultraplot.Axes
        The axes object.
    """
    # ── Prepare data ──────────────────────────────────────────────────
    plot_df = df.copy()

    if gene_col == "index":
        plot_df["_gene"] = plot_df.index
        gene_col = "_gene"

    # Drop rows with missing padj or LFC
    plot_df = plot_df.dropna(subset=[lfc_col, padj_col])

    # Compute -log10(padj), clamp padj floor to avoid inf
    padj_floor = plot_df[padj_col].replace(0, plot_df[padj_col][plot_df[padj_col] > 0].min() * 0.1)
    plot_df["neg_log10_padj"] = -np.log10(padj_floor)

    # ── Classify genes ────────────────────────────────────────────────
    conditions = [
        (plot_df[padj_col] <= padj_threshold) & (plot_df[lfc_col] >= lfc_threshold),
        (plot_df[padj_col] <= padj_threshold) & (plot_df[lfc_col] <= -lfc_threshold),
    ]
    choices = ["Up", "Down"]
    plot_df["category"] = np.select(conditions, choices, default="NS")

    n_up = (plot_df["category"] == "Up").sum()
    n_down = (plot_df["category"] == "Down").sum()
    n_ns = (plot_df["category"] == "NS").sum()

    # ── Color map ─────────────────────────────────────────────────────
    color_map = {
        "Up": "#D55E00",     # Okabe-Ito vermillion
        "Down": "#0072B2",   # Okabe-Ito blue
        "NS": "#BBBBBB",     # neutral grey
    }

    # ── Plot ──────────────────────────────────────────────────────────
    mpl.rcParams["svg.fonttype"] = "none"

    fig, ax = uplt.subplot(figsize=figsize)

    # Plot each category separately for legend control
    # NS first (behind), then significant categories on top
    for cat, label_suffix in [("NS", ""), ("Down", ""), ("Up", "")]:
        mask = plot_df["category"] == cat
        if not mask.any():
            continue
        count = mask.sum()
        alpha = alpha_ns if cat == "NS" else alpha_sig
        ax.scatter(
            plot_df.loc[mask, lfc_col],
            plot_df.loc[mask, "neg_log10_padj"],
            c=color_map[cat],
            s=marker_size,
            alpha=alpha,
            edgecolors="none",
            label=f"{cat} ({count})",
            zorder=2 if cat == "NS" else 3,
            rasterized=True,
        )

    # ── Threshold lines ───────────────────────────────────────────────
    neg_log10_threshold = -np.log10(padj_threshold)
    ax.axhline(neg_log10_threshold, color="grey", linestyle="--", linewidth=0.6, zorder=1)
    ax.axvline(lfc_threshold, color="grey", linestyle="--", linewidth=0.6, zorder=1)
    ax.axvline(-lfc_threshold, color="grey", linestyle="--", linewidth=0.6, zorder=1)

    # ── Label top genes ───────────────────────────────────────────────
    sig_df = plot_df[plot_df["category"].isin(["Up", "Down"])].copy()
    if len(sig_df) > 0 and top_n > 0:
        top_genes = sig_df.nsmallest(top_n, padj_col)
        texts = []
        for _, row in top_genes.iterrows():
            texts.append(
                ax.text(
                    row[lfc_col],
                    row["neg_log10_padj"],
                    row[gene_col],
                    fontsize=7,
                    fontstyle="italic",
                    ha="center",
                    va="bottom",
                )
            )
        adjust_text(
            texts,
            ax=ax,
            arrowprops=dict(arrowstyle="-", color="grey", lw=0.5),
            expand=(1.5, 1.5),
        )

    # ── Format axes ───────────────────────────────────────────────────
    ax.format(
        xlabel="log$_{2}$(Fold Change)",
        ylabel="$-$log$_{10}$(p$_{adj}$)",
        title=title,
        xlabelsize=9,
        ylabelsize=9,
        xticklabelsize=8,
        yticklabelsize=8,
        titlesize=9,
        titleweight="bold",
    )
    ax.legend(loc="upper right", fontsize=7, frameon=False, handletextpad=0.3)

    # ── Save ──────────────────────────────────────────────────────────
    if save_path is None:
        save_path = "./results/volcano_plot"
    fig.savefig(f"{save_path}.svg", dpi=300, bbox_inches="tight")
    fig.savefig(f"{save_path}.png", dpi=300, bbox_inches="tight")

    return fig, ax
```

## Colormap Recommendations

| Data encoding | Colormap | Notes |
|---------------|----------|-------|
| Categorical (Up / Down / NS) | Fixed 3-color: `#D55E00`, `#0072B2`, `#BBBBBB` | Okabe-Ito vermillion + blue; colorblind-safe |
| Continuous by baseMean (optional) | `viridis` | Sequential; avoid jet/rainbow |

## Customization Notes

- **`top_n`**: Controls how many gene labels appear. Set to 0 to disable labeling entirely. For dense plots, keep at 10-15 to avoid clutter.
- **`lfc_threshold`**: Draws vertical dashed lines. Use a biologically meaningful threshold (typically 1.0 = 2-fold change). Never use 0.
- **`padj_threshold`**: Draws the horizontal dashed line. Standard is 0.05. Use `padj`, never raw `pvalue`.
- **`marker_size`**: Reduce to 6-8 for datasets with >20,000 genes to avoid overplotting.
- **`alpha_ns` / `alpha_sig`**: Lower `alpha_ns` further (0.2-0.3) when NS points dominate and obscure significant genes.
- **`rasterized=True`**: Scatter points are rasterized to keep SVG file size manageable with large gene sets. Text and axes remain vector.
- **`adjustText`**: Requires the `adjustText` package (`pip install adjustText`). Prevents gene labels from overlapping.
- **Symmetric x-axis**: If needed, set `ax.format(xlim=(-max_lfc, max_lfc))` after calling the function for visual balance.
