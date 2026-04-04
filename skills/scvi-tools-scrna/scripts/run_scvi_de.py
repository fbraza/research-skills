"""
Bayesian Differential Expression Analysis with scvi-tools

This module implements Bayesian DE testing using scvi-tools' probabilistic
framework. Unlike traditional methods (Wilcoxon, t-test), scvi-tools DE
operates on the learned generative model, enabling batch-corrected comparisons
with proper zero-inflation handling and uncertainty quantification.

Statistical framework:
  - "change" mode: composite null |β| ≤ δ (recommended — avoids trivially
    small effects; requires a biologically meaningful minimum effect size)
  - "vanilla" mode: point null β = 0 (more sensitive but detects tiny effects)
  - FDR control via posterior expected False Discovery Proportion (FDP)
  - Bayes factor: log-odds ratio of DE vs. not-DE; higher = stronger evidence

For methodology details see references/differential-expression.md

Functions:
  - run_bayesian_de(): Run DE between two groups (or one-vs-rest)
  - filter_de_results(): Split significant results into up/downregulated sets
  - plot_volcano(): Volcano plot with labeled top genes
  - summarize_de(): Print and return a summary statistics dict

Requirements:
  - scvi-tools >= 1.1: pip install scvi-tools
  - matplotlib: pip install matplotlib
  - adjustText (optional, for non-overlapping labels): pip install adjustText
"""

import warnings
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

try:
    import matplotlib.pyplot as plt
    import matplotlib as mpl
except ImportError:
    raise ImportError(
        "matplotlib is required for this module.\n"
        "Install with: pip install matplotlib"
    )

try:
    import scvi  # noqa: F401 — presence validated here
except ImportError:
    raise ImportError(
        "scvi-tools is required for this module.\n"
        "Install with: pip install scvi-tools"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_bayesian_de(
    model: Any,
    adata: Any,
    groupby: str,
    group1: str,
    group2: Optional[str] = None,
    mode: str = "change",
    delta: float = 0.25,
    fdr_target: float = 0.05,
    n_samples: int = 5000,
    batch_correction: bool = True,
) -> pd.DataFrame:
    """
    Run Bayesian differential expression between two groups using scvi-tools.

    Uses the model's learned generative distribution to sample posterior
    estimates of log fold-change between cell groups, then applies FDP-based
    FDR control.  When ``group2`` is None the comparison is one-vs-rest
    (group1 against all other cells).

    Parameters
    ----------
    model : scvi-tools model
        A trained scvi-tools model (e.g. ``scvi.model.SCVI``).
    adata : AnnData
        AnnData object used to train the model.
    groupby : str
        Column in ``adata.obs`` that defines the groups.
    group1 : str
        Primary group (appears in numerator of the LFC: log μ_group1 − log μ_ref).
    group2 : str, optional
        Reference group.  If None, compares group1 to all remaining cells
        (one-vs-rest).
    mode : {"change", "vanilla"}, optional
        Hypothesis testing mode (default: "change").
        - "change": composite null |β| ≤ δ — recommended for biology.
        - "vanilla": point null β = 0 — more sensitive, may find tiny effects.
    delta : float, optional
        Minimum absolute LFC for "change" mode (default: 0.25).
        Ignored when mode="vanilla".
    fdr_target : float, optional
        Target FDR / FDP threshold (default: 0.05).
    n_samples : int, optional
        Posterior samples drawn per cell (default: 5000).
        Increase for precision; reduce for speed.
    batch_correction : bool, optional
        Marginalise over batch when sampling (default: True).
        Set False only for within-batch comparisons.

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by gene name with columns including:
        lfc_mean, lfc_std, lfc_median, bayes_factor,
        is_de_fdr_0.05, mean1, mean2,
        non_zeros_proportion1, non_zeros_proportion2.

    Raises
    ------
    ValueError
        If ``groupby`` is not a column of ``adata.obs``, or if ``group1`` /
        ``group2`` are not present in that column.

    Notes
    -----
    LFC sign convention: positive lfc_mean means higher expression in group1.

    Examples
    --------
    >>> de = run_bayesian_de(model, adata, groupby="cell_type",
    ...                      group1="Macrophage", group2="Monocyte")
    >>> de = run_bayesian_de(model, adata, groupby="condition",
    ...                      group1="treated")  # one-vs-rest
    """
    # ------------------------------------------------------------------
    # Input validation
    # ------------------------------------------------------------------
    if groupby not in adata.obs.columns:
        raise ValueError(
            f"groupby column '{groupby}' not found in adata.obs. "
            f"Available columns: {list(adata.obs.columns)}"
        )

    available_groups = adata.obs[groupby].astype(str).unique().tolist()

    if group1 not in available_groups:
        raise ValueError(
            f"group1 '{group1}' not found in adata.obs['{groupby}']. "
            f"Available values: {sorted(available_groups)}"
        )

    if group2 is not None and group2 not in available_groups:
        raise ValueError(
            f"group2 '{group2}' not found in adata.obs['{groupby}']. "
            f"Available values: {sorted(available_groups)}"
        )

    # ------------------------------------------------------------------
    # Summary header
    # ------------------------------------------------------------------
    comparison_label = (
        f"{group1} vs. {group2}" if group2 is not None else f"{group1} vs. rest"
    )
    print("=" * 60)
    print("Bayesian Differential Expression (scvi-tools)")
    print("=" * 60)
    print(f"\n  Comparison : {comparison_label}")
    print(f"  groupby    : {groupby}")
    print(f"  mode       : {mode}" + (f"  (delta={delta})" if mode == "change" else ""))
    print(f"  fdr_target : {fdr_target}")
    print(f"  n_samples  : {n_samples:,}")
    print(f"  batch_corr : {batch_correction}")
    if group2 is None:
        print(f"\n  [NOTE] group2 is None — performing one-vs-rest comparison.")
        print(f"         group1 is compared against all other cells in '{groupby}'.")

    # ------------------------------------------------------------------
    # Run DE
    # ------------------------------------------------------------------
    print(f"\n  Running differential_expression()...")

    de_results: pd.DataFrame = model.differential_expression(
        groupby=groupby,
        group1=group1,
        group2=group2,
        mode=mode,
        delta=delta,
        fdr_target=fdr_target,
        n_samples=n_samples,
        batch_correction=batch_correction,
    )

    # ------------------------------------------------------------------
    # Print summary
    # ------------------------------------------------------------------
    fdr_col = "is_de_fdr_0.05"
    n_total = len(de_results)
    n_sig = int(de_results[fdr_col].sum()) if fdr_col in de_results.columns else 0
    n_up = int((de_results[fdr_col] & (de_results["lfc_mean"] > 0)).sum()) \
        if fdr_col in de_results.columns else 0
    n_down = int((de_results[fdr_col] & (de_results["lfc_mean"] < 0)).sum()) \
        if fdr_col in de_results.columns else 0

    print(f"\n  Results:")
    print(f"    Total genes tested : {n_total:,}")
    print(f"    Significant (FDR {fdr_target:.2f}): {n_sig:,}")
    print(f"    Upregulated        : {n_up:,}  (lfc_mean > 0)")
    print(f"    Downregulated      : {n_down:,}  (lfc_mean < 0)")
    print(f"\n  ✓ Differential expression complete")

    return de_results


def filter_de_results(
    de_results: pd.DataFrame,
    fdr_col: str = "is_de_fdr_0.05",
    lfc_threshold: float = 0.25,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Filter DE results to significant genes and split by direction.

    Genes are considered significant when ``fdr_col`` is True.  Within
    significant genes, upregulated is defined as lfc_mean > lfc_threshold
    and downregulated as lfc_mean < -lfc_threshold.  Both subsets are sorted
    by |lfc_mean| descending so the strongest effects appear first.

    Parameters
    ----------
    de_results : pd.DataFrame
        Output DataFrame from :func:`run_bayesian_de`.
    fdr_col : str, optional
        Boolean column indicating significance (default: "is_de_fdr_0.05").
    lfc_threshold : float, optional
        Minimum |lfc_mean| for directional classification (default: 0.25).
        Significant genes with |lfc_mean| ≤ lfc_threshold are excluded from
        both returned DataFrames (ambiguous direction).

    Returns
    -------
    tuple of (pd.DataFrame, pd.DataFrame)
        (upregulated, downregulated), each sorted by |lfc_mean| descending.

    Raises
    ------
    KeyError
        If ``fdr_col`` or "lfc_mean" are absent from ``de_results``.

    Examples
    --------
    >>> up, down = filter_de_results(de_results, lfc_threshold=0.5)
    >>> print(f"Up: {len(up)}, Down: {len(down)}")
    """
    for col in (fdr_col, "lfc_mean"):
        if col not in de_results.columns:
            raise KeyError(
                f"Required column '{col}' not found in de_results. "
                f"Available columns: {list(de_results.columns)}"
            )

    sig = de_results[de_results[fdr_col].astype(bool)].copy()

    upregulated = sig[sig["lfc_mean"] > lfc_threshold].copy()
    downregulated = sig[sig["lfc_mean"] < -lfc_threshold].copy()

    upregulated = upregulated.reindex(
        upregulated["lfc_mean"].abs().sort_values(ascending=False).index
    )
    downregulated = downregulated.reindex(
        downregulated["lfc_mean"].abs().sort_values(ascending=False).index
    )

    n_up = len(upregulated)
    n_down = len(downregulated)
    n_ambiguous = len(sig) - n_up - n_down

    print(f"\n  Filtered DE results (lfc_threshold={lfc_threshold}):")
    print(f"    Upregulated   : {n_up:,}")
    print(f"    Downregulated : {n_down:,}")
    if n_ambiguous > 0:
        print(
            f"    Ambiguous (|lfc| ≤ {lfc_threshold}): {n_ambiguous:,} "
            f"(excluded from both sets)"
        )
    print(f"\n  ✓ Filtering complete")

    return upregulated, downregulated


def plot_volcano(
    de_results: pd.DataFrame,
    output_dir: str = "results",
    title: Optional[str] = None,
    lfc_threshold: float = 0.25,
) -> None:
    """
    Volcano plot of Bayesian DE results.

    x-axis: lfc_mean (log fold-change, group1 relative to reference).
    y-axis: -log10(1 / (bayes_factor + 1))  —  a monotone transformation of
            the Bayes factor that places strong evidence at the top of the plot.

    Point colours:
      - Red:  significant (is_de_fdr_0.05 == True) and lfc_mean > lfc_threshold
      - Blue: significant and lfc_mean < -lfc_threshold
      - Grey: non-significant or |lfc_mean| ≤ lfc_threshold

    Top 5 upregulated and top 5 downregulated genes (by |lfc_mean|) are
    labelled.  If adjustText is installed labels are repositioned to reduce
    overlap; otherwise they are placed at the data point without adjustment.

    Saves PNG (300 DPI) and SVG to ``output_dir``.

    Parameters
    ----------
    de_results : pd.DataFrame
        Output DataFrame from :func:`run_bayesian_de`.
    output_dir : str, optional
        Directory for saved figures (default: "results").
    title : str, optional
        Plot title.  If None, defaults to "Volcano Plot".
    lfc_threshold : float, optional
        Vertical dashed lines drawn at ±lfc_threshold (default: 0.25).

    Returns
    -------
    None

    Examples
    --------
    >>> plot_volcano(de_results, output_dir="results/de", title="Macro vs Mono")
    """
    required_cols = {"lfc_mean", "bayes_factor", "is_de_fdr_0.05"}
    missing = required_cols - set(de_results.columns)
    if missing:
        raise KeyError(
            f"Columns missing from de_results: {missing}. "
            f"Available: {list(de_results.columns)}"
        )

    # ------------------------------------------------------------------
    # Derived quantities
    # ------------------------------------------------------------------
    lfc = de_results["lfc_mean"].values
    # Guard against zero bayes_factor: add 1 in denominator is already present
    y_score = -np.log10(1.0 / (de_results["bayes_factor"].values + 1.0))
    sig_mask = de_results["is_de_fdr_0.05"].astype(bool).values

    up_mask = sig_mask & (lfc > lfc_threshold)
    down_mask = sig_mask & (lfc < -lfc_threshold)
    grey_mask = ~(up_mask | down_mask)

    # ------------------------------------------------------------------
    # Build figure
    # ------------------------------------------------------------------
    mpl.rcParams.update({"font.size": 11})
    fig, ax = plt.subplots(figsize=(9, 6))

    scatter_kw = dict(s=14, linewidths=0, alpha=0.6)
    ax.scatter(lfc[grey_mask], y_score[grey_mask], color="#AAAAAA", **scatter_kw,
               label="Not significant", zorder=2)
    ax.scatter(lfc[down_mask], y_score[down_mask], color="#3A7ABF", **scatter_kw,
               label=f"Down (FDR ≤ 0.05, lfc < −{lfc_threshold})", zorder=3)
    ax.scatter(lfc[up_mask], y_score[up_mask], color="#D93025", **scatter_kw,
               label=f"Up (FDR ≤ 0.05, lfc > {lfc_threshold})", zorder=3)

    # Threshold lines
    ax.axvline(x=lfc_threshold, color="#888888", linestyle="--", linewidth=0.9)
    ax.axvline(x=-lfc_threshold, color="#888888", linestyle="--", linewidth=0.9)

    ax.set_xlabel("Mean log fold-change (group1 / reference)", fontsize=12)
    ax.set_ylabel(r"$-\log_{10}(1\,/\,(\mathrm{Bayes\,factor} + 1))$", fontsize=12)
    ax.set_title(title if title is not None else "Volcano Plot", fontsize=14)
    ax.legend(fontsize=9, loc="upper left", framealpha=0.8)
    ax.grid(True, alpha=0.25, linewidth=0.5)

    # ------------------------------------------------------------------
    # Label top 5 up + top 5 down genes
    # ------------------------------------------------------------------
    gene_names = de_results.index.tolist()

    up_indices = np.where(up_mask)[0]
    down_indices = np.where(down_mask)[0]

    top_up_idx = up_indices[np.argsort(lfc[up_indices])[::-1][:5]] if len(up_indices) else []
    top_down_idx = down_indices[np.argsort(lfc[down_indices])[:5]] if len(down_indices) else []
    label_indices = list(top_up_idx) + list(top_down_idx)

    texts = []
    for idx in label_indices:
        texts.append(
            ax.text(
                lfc[idx],
                y_score[idx],
                gene_names[idx],
                fontsize=8,
                ha="left",
                va="bottom",
            )
        )

    if texts:
        try:
            from adjustText import adjust_text
            adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle="-", color="grey", lw=0.6))
        except ImportError:
            warnings.warn(
                "adjustText not installed — gene labels may overlap. "
                "Install with: pip install adjustText",
                stacklevel=2,
            )

    fig.tight_layout()

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    safe_title = (title or "volcano").replace(" ", "_").replace("/", "-")
    png_path = out_path / f"{safe_title}.png"
    svg_path = out_path / f"{safe_title}.svg"

    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(fig)

    print(f"\n  ✓ Volcano plot saved:")
    print(f"      {png_path}")
    print(f"      {svg_path}")


def summarize_de(
    de_results: pd.DataFrame,
    fdr_col: str = "is_de_fdr_0.05",
) -> dict:
    """
    Compute and print a concise summary of DE results.

    Parameters
    ----------
    de_results : pd.DataFrame
        Output DataFrame from :func:`run_bayesian_de`.
    fdr_col : str, optional
        Boolean significance column (default: "is_de_fdr_0.05").

    Returns
    -------
    dict
        Keys:
        - total_tested (int): all genes in the results table
        - total_de (int): genes where fdr_col is True
        - n_up (int): significant genes with lfc_mean > 0
        - n_down (int): significant genes with lfc_mean < 0
        - median_lfc_up (float): median lfc_mean among upregulated genes
        - median_lfc_down (float): median lfc_mean among downregulated genes
        - top5_up (list[str]): top-5 upregulated gene names by lfc_mean
        - top5_down (list[str]): top-5 downregulated gene names by |lfc_mean|

    Raises
    ------
    KeyError
        If ``fdr_col`` or "lfc_mean" are absent from ``de_results``.

    Examples
    --------
    >>> stats = summarize_de(de_results)
    >>> print(stats["top5_up"])
    """
    for col in (fdr_col, "lfc_mean"):
        if col not in de_results.columns:
            raise KeyError(
                f"Required column '{col}' not found in de_results. "
                f"Available columns: {list(de_results.columns)}"
            )

    sig = de_results[de_results[fdr_col].astype(bool)]
    up = sig[sig["lfc_mean"] > 0].sort_values("lfc_mean", ascending=False)
    down = sig[sig["lfc_mean"] < 0].sort_values("lfc_mean")

    total_tested = len(de_results)
    total_de = len(sig)
    n_up = len(up)
    n_down = len(down)
    median_lfc_up = float(up["lfc_mean"].median()) if n_up > 0 else float("nan")
    median_lfc_down = float(down["lfc_mean"].median()) if n_down > 0 else float("nan")
    top5_up = up.head(5).index.tolist()
    top5_down = down.head(5).index.tolist()

    summary = {
        "total_tested": total_tested,
        "total_de": total_de,
        "n_up": n_up,
        "n_down": n_down,
        "median_lfc_up": median_lfc_up,
        "median_lfc_down": median_lfc_down,
        "top5_up": top5_up,
        "top5_down": top5_down,
    }

    pct_de = 100.0 * total_de / total_tested if total_tested > 0 else 0.0

    print("\n" + "=" * 60)
    print("DE Results Summary")
    print("=" * 60)
    print(f"  Total genes tested : {total_tested:,}")
    print(f"  Significant (FDR)  : {total_de:,}  ({pct_de:.1f}%)")
    print(f"  Upregulated        : {n_up:,}  (median LFC = {median_lfc_up:+.3f})")
    print(f"  Downregulated      : {n_down:,}  (median LFC = {median_lfc_down:+.3f})")
    if top5_up:
        print(f"\n  Top 5 upregulated  : {', '.join(top5_up)}")
    if top5_down:
        print(f"  Top 5 downregulated: {', '.join(top5_down)}")
    print("=" * 60)

    return summary


# ---------------------------------------------------------------------------
# CLI entry-point (illustrative usage)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("scvi-tools Bayesian DE — run_scvi_de.py")
    print("=" * 60)
    print()
    print("Example workflow (two-group comparison):")
    print()
    print("  import scvi")
    print("  import scanpy as sc")
    print("  from run_scvi_de import (")
    print("      run_bayesian_de,")
    print("      filter_de_results,")
    print("      plot_volcano,")
    print("      summarize_de,")
    print("  )")
    print()
    print("  # Load trained model and matching AnnData")
    print("  model = scvi.model.SCVI.load('results/scvi_model', adata=adata)")
    print()
    print("  # 1. Run Bayesian DE (change mode, recommended)")
    print("  de = run_bayesian_de(")
    print("      model, adata,")
    print("      groupby='cell_type',")
    print("      group1='Macrophage',")
    print("      group2='Monocyte',")
    print("      mode='change',")
    print("      delta=0.25,")
    print("      fdr_target=0.05,")
    print("  )")
    print()
    print("  # 2. Filter to significant genes")
    print("  up, down = filter_de_results(de, lfc_threshold=0.25)")
    print()
    print("  # 3. Volcano plot")
    print("  plot_volcano(de, output_dir='results/de', title='Macro_vs_Mono')")
    print()
    print("  # 4. Summary statistics")
    print("  stats = summarize_de(de)")
    print()
    print("  # 5. Save tables")
    print("  de.to_csv('results/de/de_results.csv')")
    print("  up.to_csv('results/de/upregulated.csv')")
    print("  down.to_csv('results/de/downregulated.csv')")
    print()
    print("One-vs-rest comparison (omit group2):")
    print()
    print("  de_ovr = run_bayesian_de(")
    print("      model, adata,")
    print("      groupby='cell_type',")
    print("      group1='Macrophage',  # group2=None")
    print("  )")
