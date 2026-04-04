"""
Diagnostic Plots for scvi-tools Models

This module provides publication-quality diagnostic visualizations for all
scvi-tools model types: scVI, scANVI, LDVAE, CellAssign, and veloVI.

All plots are saved as PNG (300 DPI) and SVG. Never uses rainbow/jet colormaps.

Functions:
  - plot_training_history(): ELBO loss curves — full and fine-convergence view
  - plot_latent_umap(): UMAP projections of the learned latent space
  - plot_batch_mixing(): Side-by-side UMAP for batch vs cell type
  - plot_scanvi_confidence(): Histogram of scANVI max prediction probabilities
  - plot_ldvae_loadings(): Heatmap of LDVAE gene factor loadings
  - plot_cellassign_probabilities(): CellAssign probability heatmap + proportions
  - plot_velovi_diagnostics(): veloVI latent time, velocity coherence, and permutation scores

Requirements:
  - scanpy >= 1.9: pip install scanpy
  - matplotlib >= 3.7: pip install matplotlib
  - seaborn >= 0.12: pip install seaborn
  - scvi-tools >= 1.1 (optional, required only for plot_training_history)
"""

import warnings
from pathlib import Path
from typing import Any, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
import seaborn as sns


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _save_figure(fig: plt.Figure, name: str, output_dir: str) -> None:
    """
    Save a matplotlib figure as PNG (300 DPI) and SVG.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to save.
    name : str
        Base filename without extension (e.g., "training_history").
    output_dir : str
        Directory to write files into. Created if it does not exist.

    Notes
    -----
    SVG export failure is handled gracefully — a warning is printed and
    the PNG is still written. The figure is closed after saving.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    png_path = out / f"{name}.png"
    svg_path = out / f"{name}.svg"

    fig.savefig(png_path, dpi=300, bbox_inches="tight")

    try:
        fig.savefig(svg_path, format="svg", bbox_inches="tight")
    except Exception as exc:
        warnings.warn(f"SVG export failed for '{name}': {exc}. PNG was saved.")

    plt.close(fig)
    print(f"  ✓ {name} saved  ({png_path})")


def _ensure_umap(adata: sc.AnnData, rep_key: str = "X_scVI") -> None:
    """
    Compute neighbors and UMAP if not already present in adata.

    The neighbor graph is built from rep_key. UMAP is stored in
    adata.obsm['X_umap'] by scanpy.

    Parameters
    ----------
    adata : AnnData
        Annotated data matrix.
    rep_key : str, optional
        Key in adata.obsm to use as the representation (default: "X_scVI").

    Raises
    ------
    KeyError
        If rep_key is not found in adata.obsm.
    """
    if rep_key not in adata.obsm:
        raise KeyError(
            f"Representation '{rep_key}' not found in adata.obsm. "
            f"Available keys: {list(adata.obsm.keys())}"
        )

    # Neighbors
    neighbors_computed = (
        "neighbors" in adata.uns
        and adata.uns.get("neighbors", {}).get("params", {}).get("use_rep") == rep_key
    )
    if not neighbors_computed:
        print(f"  Computing neighbors using '{rep_key}'...")
        sc.pp.neighbors(adata, use_rep=rep_key)

    # UMAP
    if "X_umap" not in adata.obsm:
        print("  Computing UMAP...")
        sc.tl.umap(adata)


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def plot_training_history(
    model: Any,
    output_dir: str = "results",
) -> None:
    """
    Plot ELBO training and validation loss curves.

    Produces a two-panel figure:
    - Left panel: full training history.
    - Right panel: final 50% of epochs (fine-convergence view).

    Parameters
    ----------
    model : scvi-tools model
        A trained scvi-tools model with a ``history`` attribute
        (e.g., scvi.model.SCVI, scvi.model.SCANVI).
    output_dir : str, optional
        Directory to write output files (default: "results").

    Notes
    -----
    Saves ``training_history.png`` and ``training_history.svg``.

    Examples
    --------
    >>> model.train(max_epochs=400)
    >>> plot_training_history(model, output_dir="results/scvi")
    """
    print("=" * 60)
    print("Plotting Training History")
    print("=" * 60)

    history = model.history
    train_loss = history.get("elbo_train")
    val_loss = history.get("elbo_validation", None)

    if train_loss is None:
        raise ValueError(
            "Model history does not contain 'elbo_train'. "
            "Ensure the model was trained before calling this function."
        )

    train_vals = train_loss.values.ravel()
    train_epochs = train_loss.index.tolist()
    n_epochs = len(train_vals)

    has_val = val_loss is not None and len(val_loss) > 0
    if has_val:
        val_vals = val_loss.values.ravel()
        val_epochs = val_loss.index.tolist()

    # Midpoint for fine-convergence panel
    mid = n_epochs // 2

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("scvi-tools Training History (ELBO)", fontsize=14, fontweight="bold")

    for ax_idx, (ax, title, slc_epoch, slc_start) in enumerate(
        [
            (axes[0], "Full training", train_epochs, 0),
            (axes[1], f"Final 50% (epoch {train_epochs[mid]}+)", train_epochs[mid:], mid),
        ]
    ):
        ax.plot(
            slc_epoch,
            train_vals[slc_start:],
            label="Train ELBO",
            linewidth=1.8,
            color="#2166ac",
        )
        if has_val:
            # Validation may be recorded less frequently — filter to range
            if ax_idx == 1:
                cutoff = train_epochs[mid]
                v_filtered = [
                    (e, v) for e, v in zip(val_epochs, val_vals) if e >= cutoff
                ]
            else:
                v_filtered = list(zip(val_epochs, val_vals))

            if v_filtered:
                ve, vv = zip(*v_filtered)
                ax.plot(
                    list(ve),
                    list(vv),
                    label="Validation ELBO",
                    linewidth=1.8,
                    color="#d6604d",
                    linestyle="--",
                )

        ax.set_xlabel("Epoch", fontsize=11)
        ax.set_ylabel("ELBO Loss", fontsize=11)
        ax.set_title(title, fontsize=12)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3, linestyle=":")

    fig.tight_layout()

    print(f"\n  Epochs trained: {n_epochs}")
    print(f"  Final train ELBO: {train_vals[-1]:.3f}")
    if has_val:
        print(f"  Final validation ELBO: {val_vals[-1]:.3f}")

    _save_figure(fig, "training_history", output_dir)


def plot_latent_umap(
    adata: sc.AnnData,
    color_keys: List[str],
    rep_key: str = "X_scVI",
    output_dir: str = "results",
) -> None:
    """
    Plot UMAP projections of the scvi-tools latent space.

    Computes neighbors and UMAP from rep_key if not already present.
    Renders one panel per key in color_keys.

    Parameters
    ----------
    adata : AnnData
        Annotated data matrix.
    color_keys : list of str
        Keys in adata.obs (or gene names) to colour the UMAP by.
        One subplot per key.
    rep_key : str, optional
        Key in adata.obsm for the latent representation (default: "X_scVI").
    output_dir : str, optional
        Directory to write output files (default: "results").

    Notes
    -----
    Saves ``latent_umap.png`` and ``latent_umap.svg``.

    Examples
    --------
    >>> plot_latent_umap(
    ...     adata,
    ...     color_keys=["batch", "cell_type", "n_genes_by_counts"],
    ...     rep_key="X_scVI",
    ...     output_dir="results/scvi",
    ... )
    """
    print("=" * 60)
    print("Plotting Latent UMAP")
    print("=" * 60)

    _ensure_umap(adata, rep_key=rep_key)

    n_panels = len(color_keys)
    n_cols = min(n_panels, 3)
    n_rows = int(np.ceil(n_panels / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4.5 * n_rows))
    axes_flat = np.array(axes).ravel() if n_panels > 1 else [axes]

    umap_coords = adata.obsm["X_umap"]

    for i, key in enumerate(color_keys):
        ax = axes_flat[i]

        if key in adata.obs.columns:
            values = adata.obs[key]
        elif key in adata.var_names:
            gene_idx = adata.var_names.get_loc(key)
            import scipy.sparse as sp
            X = adata.X
            values_arr = (
                np.asarray(X[:, gene_idx].todense()).ravel()
                if sp.issparse(X)
                else np.asarray(X[:, gene_idx]).ravel()
            )
            values = pd.Series(values_arr, index=adata.obs_names, name=key)
        else:
            warnings.warn(f"Key '{key}' not found in adata.obs or adata.var_names; skipping.")
            ax.set_visible(False)
            continue

        if pd.api.types.is_categorical_dtype(values) or pd.api.types.is_object_dtype(values):
            categories = values.astype("category").cat.categories.tolist()
            n_cats = len(categories)
            palette = (
                sns.color_palette("tab20", n_cats)
                if n_cats <= 20
                else sns.color_palette("tab20", 20)
            )
            cat_to_color = {c: palette[j % len(palette)] for j, c in enumerate(categories)}
            colors = [cat_to_color[v] for v in values]
            scatter = ax.scatter(
                umap_coords[:, 0],
                umap_coords[:, 1],
                c=colors,
                s=3,
                alpha=0.6,
                linewidths=0,
                rasterized=True,
            )
            # Legend
            handles = [
                plt.Line2D(
                    [0], [0],
                    marker="o",
                    color="w",
                    markerfacecolor=cat_to_color[c],
                    markersize=6,
                    label=str(c),
                )
                for c in categories[:20]
            ]
            ax.legend(
                handles=handles,
                fontsize=6,
                loc="upper right",
                framealpha=0.5,
                markerscale=1.2,
            )
        else:
            numeric_vals = pd.to_numeric(values, errors="coerce")
            sc_plot = ax.scatter(
                umap_coords[:, 0],
                umap_coords[:, 1],
                c=numeric_vals,
                s=3,
                alpha=0.6,
                cmap="viridis",
                linewidths=0,
                rasterized=True,
            )
            plt.colorbar(sc_plot, ax=ax, shrink=0.7, pad=0.02)

        ax.set_title(key, fontsize=11)
        ax.set_xlabel("UMAP 1", fontsize=9)
        ax.set_ylabel("UMAP 2", fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])

    # Hide unused axes
    for j in range(n_panels, len(axes_flat)):
        axes_flat[j].set_visible(False)

    fig.suptitle(f"Latent UMAP ({rep_key})", fontsize=13, fontweight="bold", y=1.01)
    fig.tight_layout()

    _save_figure(fig, "latent_umap", output_dir)


def plot_batch_mixing(
    adata: sc.AnnData,
    batch_key: str,
    rep_key: str = "X_scVI",
    output_dir: str = "results",
) -> None:
    """
    Side-by-side UMAP coloured by batch and by cell type (if available).

    Helps assess whether the latent space has achieved batch mixing while
    preserving biological variation.

    Parameters
    ----------
    adata : AnnData
        Annotated data matrix.
    batch_key : str
        Column in adata.obs containing batch labels.
    rep_key : str, optional
        Key in adata.obsm for the latent representation (default: "X_scVI").
    output_dir : str, optional
        Directory to write output files (default: "results").

    Notes
    -----
    Saves ``batch_mixing.png`` and ``batch_mixing.svg``.
    Cell type panel is shown only when a suitable column is detected in
    adata.obs (checked by name: "cell_type", "celltype", "leiden", "louvain",
    "scanvi_predictions", "cluster").

    Examples
    --------
    >>> plot_batch_mixing(adata, batch_key="sample", rep_key="X_scVI")
    """
    print("=" * 60)
    print("Plotting Batch Mixing")
    print("=" * 60)

    if batch_key not in adata.obs.columns:
        raise ValueError(
            f"Batch key '{batch_key}' not found in adata.obs. "
            f"Available columns: {list(adata.obs.columns.tolist())}"
        )

    _ensure_umap(adata, rep_key=rep_key)

    # Detect cell type column
    candidate_celltype_keys = [
        "cell_type", "celltype", "cell_types", "leiden", "louvain",
        "scanvi_predictions", "cluster", "clusters", "annotation",
    ]
    celltype_key: Optional[str] = None
    for candidate in candidate_celltype_keys:
        if candidate in adata.obs.columns:
            celltype_key = candidate
            break

    n_panels = 2 if celltype_key is not None else 1
    fig, axes = plt.subplots(1, n_panels, figsize=(7 * n_panels, 6))
    if n_panels == 1:
        axes = [axes]

    umap_coords = adata.obsm["X_umap"]

    def _draw_categorical_umap(ax: plt.Axes, key: str, title: str) -> None:
        """Render one categorical UMAP panel."""
        values = adata.obs[key].astype("category")
        categories = values.cat.categories.tolist()
        n_cats = len(categories)
        palette = sns.color_palette("tab20", min(n_cats, 20))
        cat_to_color = {c: palette[j % len(palette)] for j, c in enumerate(categories)}
        colors = [cat_to_color[v] for v in values]
        ax.scatter(
            umap_coords[:, 0],
            umap_coords[:, 1],
            c=colors,
            s=3,
            alpha=0.6,
            linewidths=0,
            rasterized=True,
        )
        handles = [
            plt.Line2D(
                [0], [0],
                marker="o",
                color="w",
                markerfacecolor=cat_to_color[c],
                markersize=7,
                label=str(c),
            )
            for c in categories[:20]
        ]
        ax.legend(
            handles=handles,
            fontsize=7,
            loc="upper right",
            framealpha=0.5,
        )
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xlabel("UMAP 1", fontsize=9)
        ax.set_ylabel("UMAP 2", fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])

    _draw_categorical_umap(axes[0], batch_key, f"Batch ({batch_key})")

    if celltype_key is not None:
        _draw_categorical_umap(axes[1], celltype_key, f"Cell type ({celltype_key})")

    fig.suptitle(f"Batch Mixing Assessment ({rep_key})", fontsize=13, fontweight="bold")
    fig.tight_layout()

    n_batches = adata.obs[batch_key].nunique()
    print(f"\n  Batches shown: {n_batches} ({batch_key})")
    if celltype_key is not None:
        print(f"  Cell type column: {celltype_key}")
    else:
        print("  No cell type column detected; showing batch panel only.")

    _save_figure(fig, "batch_mixing", output_dir)


def plot_scanvi_confidence(
    adata: sc.AnnData,
    predictions_key: str = "scanvi_predictions",
    output_dir: str = "results",
) -> None:
    """
    Histogram of scANVI maximum prediction probabilities.

    Visualises the classifier confidence distribution across all cells.
    A vertical dashed line marks the 0.8 threshold. The fraction of cells
    above and below this threshold is printed to stdout.

    Parameters
    ----------
    adata : AnnData
        Annotated data matrix containing scANVI prediction probabilities.
    predictions_key : str, optional
        Key in adata.obs or adata.obsm holding prediction labels or
        probability matrix. If a probability matrix is stored in obsm under
        ``predictions_key + "_probabilities"`` or ``"scanvi_probabilities"``,
        it is used; otherwise the function looks for a ``predictions_key`` in
        obs and attempts to extract ``"scanvi_probabilities"`` from obsm.
        (default: "scanvi_predictions")
    output_dir : str, optional
        Directory to write output files (default: "results").

    Notes
    -----
    Saves ``scanvi_confidence.png`` and ``scanvi_confidence.svg``.

    Examples
    --------
    >>> plot_scanvi_confidence(adata, predictions_key="scanvi_predictions")
    """
    print("=" * 60)
    print("Plotting scANVI Prediction Confidence")
    print("=" * 60)

    THRESHOLD = 0.8

    # Locate probability matrix
    prob_matrix: Optional[np.ndarray] = None
    prob_candidates = [
        predictions_key + "_probabilities",
        "scanvi_probabilities",
        predictions_key,
    ]
    for candidate in prob_candidates:
        if candidate in adata.obsm:
            prob_matrix = np.asarray(adata.obsm[candidate])
            print(f"  Probability matrix found in adata.obsm['{candidate}']")
            break

    if prob_matrix is None:
        raise KeyError(
            "No scANVI probability matrix found. Expected one of: "
            + ", ".join(f"adata.obsm['{k}']" for k in prob_candidates)
            + ". Run scANVI and store soft predictions before plotting."
        )

    max_probs = prob_matrix.max(axis=1)

    n_total = len(max_probs)
    n_above = int((max_probs >= THRESHOLD).sum())
    n_below = n_total - n_above
    pct_above = 100.0 * n_above / n_total
    pct_below = 100.0 * n_below / n_total

    print(f"\n  Total cells: {n_total:,}")
    print(f"  Above threshold ({THRESHOLD}): {n_above:,} ({pct_above:.1f}%)")
    print(f"  Below threshold ({THRESHOLD}): {n_below:,} ({pct_below:.1f}%)")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(
        max_probs,
        bins=50,
        color="#4393c3",
        edgecolor="white",
        linewidth=0.4,
        alpha=0.85,
    )
    ax.axvline(
        THRESHOLD,
        color="#d73027",
        linewidth=2.0,
        linestyle="--",
        label=f"Threshold = {THRESHOLD}  ({pct_above:.1f}% above)",
    )
    ax.set_xlabel("Max Prediction Probability", fontsize=12)
    ax.set_ylabel("Cell Count", fontsize=12)
    ax.set_title("scANVI Classifier Confidence", fontsize=13, fontweight="bold")
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, linestyle=":")
    fig.tight_layout()

    _save_figure(fig, "scanvi_confidence", output_dir)


def plot_ldvae_loadings(
    loadings_df: pd.DataFrame,
    n_top: int = 20,
    output_dir: str = "results",
) -> None:
    """
    Heatmap of LDVAE gene factor loadings.

    Selects the top n_top genes by maximum absolute loading across all
    factors and plots a clustered heatmap with hierarchical column ordering.

    Parameters
    ----------
    loadings_df : pandas.DataFrame
        DataFrame of shape (n_genes, n_factors) where rows are genes and
        columns are latent factors. Typically obtained from
        ``model.get_loadings()``.
    n_top : int, optional
        Number of top genes to display (ranked by max absolute loading
        across factors, default: 20).
    output_dir : str, optional
        Directory to write output files (default: "results").

    Notes
    -----
    Saves ``ldvae_loadings.png`` and ``ldvae_loadings.svg``.
    Columns (factors) are reordered by hierarchical clustering.

    Examples
    --------
    >>> loadings = model.get_loadings()  # returns a DataFrame
    >>> plot_ldvae_loadings(loadings, n_top=20, output_dir="results/ldvae")
    """
    print("=" * 60)
    print("Plotting LDVAE Factor Loadings")
    print("=" * 60)

    if not isinstance(loadings_df, pd.DataFrame):
        raise TypeError(
            f"loadings_df must be a pandas DataFrame, got {type(loadings_df).__name__}."
        )

    n_genes_total, n_factors = loadings_df.shape
    print(f"\n  Genes: {n_genes_total}")
    print(f"  Factors: {n_factors}")

    # Select top genes by max absolute loading
    max_abs = loadings_df.abs().max(axis=1)
    top_genes = max_abs.nlargest(n_top).index.tolist()
    sub_df = loadings_df.loc[top_genes]

    print(f"  Showing top {len(top_genes)} genes by max |loading|")

    # Determine figure height proportional to gene count
    fig_height = max(6, len(top_genes) * 0.35 + 2)
    fig_width = max(8, n_factors * 0.6 + 3)

    # Clustermap handles its own figure creation
    g = sns.clustermap(
        sub_df,
        col_cluster=True,
        row_cluster=True,
        cmap="RdBu_r",
        center=0,
        figsize=(fig_width, fig_height),
        yticklabels=True,
        xticklabels=True,
        linewidths=0,
        cbar_kws={"label": "Loading"},
    )
    g.ax_heatmap.set_xlabel("Factor", fontsize=11)
    g.ax_heatmap.set_ylabel("Gene", fontsize=11)
    g.ax_heatmap.set_title(
        f"LDVAE Loadings — Top {len(top_genes)} Genes",
        fontsize=12,
        fontweight="bold",
        pad=12,
    )
    g.ax_heatmap.tick_params(axis="y", labelsize=8)
    g.ax_heatmap.tick_params(axis="x", labelsize=8)

    fig = g.fig
    fig.tight_layout()

    _save_figure(fig, "ldvae_loadings", output_dir)


def plot_cellassign_probabilities(
    adata: sc.AnnData,
    prob_key: str = "cellassign_probabilities",
    output_dir: str = "results",
) -> None:
    """
    CellAssign probability heatmap and cell type proportion bar chart.

    Panel 1: Heatmap of cell x cell-type assignment probabilities.
    If more than 1000 cells are present the heatmap uses a random subsample.

    Panel 2: Bar chart of predicted cell type proportions.

    Parameters
    ----------
    adata : AnnData
        Annotated data matrix.
    prob_key : str, optional
        Key in adata.obsm containing the CellAssign probability matrix
        (shape: n_cells x n_types, default: "cellassign_probabilities").
    output_dir : str, optional
        Directory to write output files (default: "results").

    Notes
    -----
    Saves ``cellassign_results.png`` and ``cellassign_results.svg``.

    Examples
    --------
    >>> plot_cellassign_probabilities(
    ...     adata,
    ...     prob_key="cellassign_probabilities",
    ...     output_dir="results/cellassign",
    ... )
    """
    print("=" * 60)
    print("Plotting CellAssign Probabilities")
    print("=" * 60)

    if prob_key not in adata.obsm:
        raise KeyError(
            f"Probability key '{prob_key}' not found in adata.obsm. "
            f"Available keys: {list(adata.obsm.keys())}"
        )

    prob_matrix = np.asarray(adata.obsm[prob_key])
    n_cells, n_types = prob_matrix.shape

    # Infer cell type names from columns if stored as DataFrame; otherwise generic
    if isinstance(adata.obsm[prob_key], pd.DataFrame):
        cell_type_names = list(adata.obsm[prob_key].columns)
    else:
        cell_type_names = [f"Type_{i}" for i in range(n_types)]

    print(f"\n  Cells: {n_cells:,}")
    print(f"  Cell types: {n_types}")

    # Predicted assignments (argmax)
    pred_indices = prob_matrix.argmax(axis=1)
    pred_labels = [cell_type_names[i] for i in pred_indices]
    proportions = pd.Series(pred_labels).value_counts(normalize=True).sort_values(ascending=False)

    print("\n  Cell type proportions (predicted):")
    for ct, prop in proportions.items():
        print(f"    {ct}: {prop:.1%}")

    # Subsample for heatmap
    HEATMAP_MAX = 1000
    if n_cells > HEATMAP_MAX:
        rng = np.random.default_rng(42)
        sample_idx = rng.choice(n_cells, size=HEATMAP_MAX, replace=False)
        sample_idx = np.sort(sample_idx)
        prob_plot = prob_matrix[sample_idx]
        heatmap_title = f"Assignment Probabilities (subsample n={HEATMAP_MAX})"
    else:
        prob_plot = prob_matrix
        heatmap_title = "Assignment Probabilities"

    # Sort cells by predicted type for cleaner display
    sort_order = np.argsort(prob_plot.argmax(axis=1))
    prob_plot = prob_plot[sort_order]

    fig, axes = plt.subplots(1, 2, figsize=(7 * 2, 6))

    # Panel 1: heatmap
    sns.heatmap(
        prob_plot,
        ax=axes[0],
        cmap="viridis",
        xticklabels=cell_type_names,
        yticklabels=False,
        cbar_kws={"label": "Probability", "shrink": 0.7},
        vmin=0,
        vmax=1,
    )
    axes[0].set_title(heatmap_title, fontsize=11, fontweight="bold")
    axes[0].set_xlabel("Cell Type", fontsize=10)
    axes[0].set_ylabel("Cells", fontsize=10)
    axes[0].tick_params(axis="x", labelsize=8, rotation=45)

    # Panel 2: proportions bar chart
    palette = sns.color_palette("tab20", len(proportions))
    axes[1].barh(
        proportions.index[::-1],
        proportions.values[::-1],
        color=palette[::-1],
        edgecolor="white",
        linewidth=0.5,
    )
    axes[1].set_xlabel("Proportion", fontsize=10)
    axes[1].set_title("Predicted Cell Type Proportions", fontsize=11, fontweight="bold")
    axes[1].tick_params(axis="y", labelsize=9)
    axes[1].grid(True, axis="x", alpha=0.3, linestyle=":")

    fig.suptitle("CellAssign Results", fontsize=13, fontweight="bold")
    fig.tight_layout()

    _save_figure(fig, "cellassign_results", output_dir)


def plot_velovi_diagnostics(
    adata: sc.AnnData,
    output_dir: str = "results",
) -> None:
    """
    Three-panel diagnostic figure for veloVI RNA velocity results.

    Panel a: UMAP coloured by latent time (adata.obs['latent_time']).
    Panel b: Histogram of velocity coherence scores
             (adata.obs['velocity_coherence'] or computed via
             scvelo if available).
    Panel c: Scatter of permutation-based gene velocity scores
             (adata.var['fit_likelihood'] or
              adata.var['velocity_genes'], if present).

    Parameters
    ----------
    adata : AnnData
        Annotated data matrix with veloVI outputs stored in standard keys.
    output_dir : str, optional
        Directory to write output files (default: "results").

    Notes
    -----
    Saves ``velovi_diagnostics.png`` and ``velovi_diagnostics.svg``.

    Expected keys (all optional — panels degrade gracefully if missing):
    - adata.obs['latent_time']: latent pseudotime from veloVI
    - adata.obs['velocity_coherence']: per-cell coherence score
    - adata.var['fit_likelihood']: per-gene velocity likelihood
    - adata.var['velocity_genes']: boolean mask of velocity genes

    Examples
    --------
    >>> plot_velovi_diagnostics(adata, output_dir="results/velovi")
    """
    print("=" * 60)
    print("Plotting veloVI Diagnostics")
    print("=" * 60)

    # Detect latent time rep key for UMAP
    rep_key = "X_umap"
    if rep_key not in adata.obsm:
        # Try to compute from a known latent rep
        for candidate_rep in ["X_scVI", "X_velovi", "X_scanvi", "X_pca"]:
            if candidate_rep in adata.obsm:
                _ensure_umap(adata, rep_key=candidate_rep)
                break
        else:
            if "neighbors" in adata.uns:
                sc.tl.umap(adata)
            else:
                raise KeyError(
                    "No UMAP coordinates (adata.obsm['X_umap']) and no known latent "
                    "representation found. Run _ensure_umap() manually before plotting."
                )

    umap_coords = adata.obsm["X_umap"]

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle("veloVI Diagnostics", fontsize=14, fontweight="bold")

    # ---- Panel a: latent time UMAP ----
    ax_a = axes[0]
    latent_time_key = "latent_time"
    if latent_time_key in adata.obs.columns:
        latent_time = adata.obs[latent_time_key].values
        sc_a = ax_a.scatter(
            umap_coords[:, 0],
            umap_coords[:, 1],
            c=latent_time,
            s=3,
            alpha=0.7,
            cmap="viridis",
            linewidths=0,
            rasterized=True,
        )
        plt.colorbar(sc_a, ax=ax_a, shrink=0.75, label="Latent Time")
        ax_a.set_title("Latent Time", fontsize=11, fontweight="bold")
        print(f"\n  Latent time range: {latent_time.min():.3f} — {latent_time.max():.3f}")
    else:
        ax_a.text(
            0.5, 0.5,
            "adata.obs['latent_time']\nnot found",
            ha="center", va="center",
            transform=ax_a.transAxes,
            fontsize=10, color="gray",
        )
        ax_a.set_title("Latent Time (missing)", fontsize=11)
        warnings.warn(
            "adata.obs['latent_time'] not found. "
            "Run veloVI and store latent time before plotting."
        )

    ax_a.set_xlabel("UMAP 1", fontsize=9)
    ax_a.set_ylabel("UMAP 2", fontsize=9)
    ax_a.set_xticks([])
    ax_a.set_yticks([])

    # ---- Panel b: velocity coherence histogram ----
    ax_b = axes[1]
    coherence_candidates = ["velocity_coherence", "coherence", "velocity_confidence"]
    coherence_key: Optional[str] = None
    for candidate in coherence_candidates:
        if candidate in adata.obs.columns:
            coherence_key = candidate
            break

    if coherence_key is not None:
        coherence = adata.obs[coherence_key].values
        ax_b.hist(
            coherence,
            bins=50,
            color="#4393c3",
            edgecolor="white",
            linewidth=0.4,
            alpha=0.85,
        )
        median_coh = float(np.nanmedian(coherence))
        ax_b.axvline(
            median_coh,
            color="#d73027",
            linewidth=1.8,
            linestyle="--",
            label=f"Median = {median_coh:.3f}",
        )
        ax_b.set_xlabel("Velocity Coherence", fontsize=10)
        ax_b.set_ylabel("Cell Count", fontsize=10)
        ax_b.set_title("Velocity Coherence Scores", fontsize=11, fontweight="bold")
        ax_b.legend(fontsize=9)
        ax_b.grid(True, alpha=0.3, linestyle=":")
        print(f"  Velocity coherence median: {median_coh:.3f}  (key: '{coherence_key}')")
    else:
        ax_b.text(
            0.5, 0.5,
            "Velocity coherence\nnot found in adata.obs",
            ha="center", va="center",
            transform=ax_b.transAxes,
            fontsize=10, color="gray",
        )
        ax_b.set_title("Velocity Coherence (missing)", fontsize=11)
        warnings.warn(
            "No velocity coherence key found in adata.obs. "
            f"Checked: {coherence_candidates}."
        )

    # ---- Panel c: per-gene permutation / likelihood scores ----
    ax_c = axes[2]
    gene_score_candidates = ["fit_likelihood", "velocity_score", "velocity_genes_score"]
    gene_score_key: Optional[str] = None
    for candidate in gene_score_candidates:
        if candidate in adata.var.columns:
            gene_score_key = candidate
            break

    if gene_score_key is not None:
        gene_scores = adata.var[gene_score_key].values
        valid_mask = np.isfinite(gene_scores)
        gene_ranks = np.arange(valid_mask.sum())

        # Colour velocity genes differently if the boolean column exists
        is_velocity_gene = adata.var.get("velocity_genes", pd.Series(True, index=adata.var_names))
        is_vg = is_velocity_gene.values[valid_mask].astype(bool)

        ax_c.scatter(
            gene_ranks[~is_vg],
            np.sort(gene_scores[valid_mask])[~is_vg],
            s=4,
            alpha=0.5,
            color="#aaaaaa",
            label="Non-velocity genes",
            linewidths=0,
            rasterized=True,
        )
        ax_c.scatter(
            gene_ranks[is_vg],
            np.sort(gene_scores[valid_mask])[is_vg],
            s=5,
            alpha=0.7,
            color="#2166ac",
            label="Velocity genes",
            linewidths=0,
            rasterized=True,
        )
        ax_c.set_xlabel("Gene Rank", fontsize=10)
        ax_c.set_ylabel(gene_score_key, fontsize=10)
        ax_c.set_title(f"Per-Gene Scores ({gene_score_key})", fontsize=11, fontweight="bold")
        ax_c.legend(fontsize=9)
        ax_c.grid(True, alpha=0.3, linestyle=":")
        n_vg = int(is_vg.sum())
        print(f"  Velocity genes (highlighted): {n_vg}  (key: '{gene_score_key}')")
    else:
        ax_c.text(
            0.5, 0.5,
            "Per-gene permutation scores\nnot found in adata.var",
            ha="center", va="center",
            transform=ax_c.transAxes,
            fontsize=10, color="gray",
        )
        ax_c.set_title("Permutation Scores (missing)", fontsize=11)
        warnings.warn(
            "No per-gene score key found in adata.var. "
            f"Checked: {gene_score_candidates}."
        )

    fig.tight_layout()

    _save_figure(fig, "velovi_diagnostics", output_dir)


# ---------------------------------------------------------------------------
# __main__ block
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("scvi-tools Diagnostic Plots")
    print("=" * 60)
    print()
    print("Available functions:")
    print()
    print("  from plot_scvi_diagnostics import (")
    print("      plot_training_history,")
    print("      plot_latent_umap,")
    print("      plot_batch_mixing,")
    print("      plot_scanvi_confidence,")
    print("      plot_ldvae_loadings,")
    print("      plot_cellassign_probabilities,")
    print("      plot_velovi_diagnostics,")
    print("  )")
    print()
    print("Example — scVI workflow:")
    print()
    print("  # After training a scVI model:")
    print("  plot_training_history(model, output_dir='results/scvi')")
    print("  plot_latent_umap(adata, ['batch', 'cell_type'], rep_key='X_scVI')")
    print("  plot_batch_mixing(adata, batch_key='sample', rep_key='X_scVI')")
    print()
    print("Example — scANVI confidence:")
    print()
    print("  # Store soft predictions before plotting:")
    print("  soft_preds = model.predict(soft=True)  # shape: (n_cells, n_types)")
    print("  adata.obsm['scanvi_predictions_probabilities'] = soft_preds")
    print("  plot_scanvi_confidence(adata, predictions_key='scanvi_predictions')")
    print()
    print("Example — LDVAE loadings:")
    print()
    print("  loadings = model.get_loadings()  # returns DataFrame")
    print("  plot_ldvae_loadings(loadings, n_top=20, output_dir='results/ldvae')")
    print()
    print("Example — CellAssign:")
    print()
    print("  adata.obsm['cellassign_probabilities'] = model.predict()  # n_cells x n_types")
    print("  plot_cellassign_probabilities(adata)")
    print()
    print("Example — veloVI:")
    print()
    print("  adata.obs['latent_time'] = model.get_latent_time()")
    print("  plot_velovi_diagnostics(adata, output_dir='results/velovi')")
