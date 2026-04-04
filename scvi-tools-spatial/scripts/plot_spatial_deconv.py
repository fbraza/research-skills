"""
Visualization for Spatial Deconvolution Results

This module provides publication-quality plots for spatial deconvolution
outputs: cell type proportion maps, dominant cell type maps, proportion
validation against marker gene expression, deconvolution summaries, and
training history curves.

Supports output from Cell2location, DestVI, Tangram, RCTD, and scVIVA.

All plots are saved as PNG (300 DPI) and SVG. Never uses rainbow/jet
colormaps. SVG export failure is handled gracefully.

Functions:
  - plot_cell_type_proportions(): Multi-panel spatial heatmaps per cell type
  - plot_dominant_cell_type(): Spatial map of highest-proportion cell type
  - plot_proportion_validation(): Marker expression vs estimated proportions
  - plot_deconvolution_summary(): Stacked bar + violin summary of proportions
  - plot_training_history_spatial(): Training loss curves for spatial models

Helper:
  - _save_figure(): Save PNG (300 DPI) + SVG with graceful SVG fallback

Requirements:
  - scanpy >= 1.9: pip install scanpy
  - matplotlib >= 3.7: pip install matplotlib
  - seaborn >= 0.12: pip install seaborn
  - numpy, pandas (standard dependencies)
"""

import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
import seaborn as sns
from scipy import sparse


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
        Base filename without extension (e.g., "spatial_proportions").
    output_dir : str
        Directory to write files into. Created if it does not exist.

    Notes
    -----
    SVG export failure is handled gracefully — a warning is printed and
    the PNG is still written. The figure is closed after saving to free memory.
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


def _get_proportions_matrix(
    adata_sp: sc.AnnData,
    proportions_key: str,
) -> pd.DataFrame:
    """
    Retrieve cell type proportions as a DataFrame from adata_sp.

    Proportions may be stored in adata_sp.obsm[proportions_key] (ndarray
    or DataFrame) or as per-type columns in adata_sp.obs if obsm lookup fails.

    Parameters
    ----------
    adata_sp : AnnData
        Spatial AnnData with stored deconvolution results.
    proportions_key : str
        Key in adata_sp.obsm containing cell type proportions.

    Returns
    -------
    pd.DataFrame
        Shape (n_spots, n_cell_types). Index matches adata_sp.obs_names.

    Raises
    ------
    KeyError
        If proportions_key is not found in adata_sp.obsm.
    """
    if proportions_key not in adata_sp.obsm:
        raise KeyError(
            f"Proportions key '{proportions_key}' not found in adata_sp.obsm. "
            f"Available obsm keys: {list(adata_sp.obsm.keys())}\n"
            "Run a deconvolution model first (Cell2location, DestVI, RCTD, etc.)."
        )

    raw = adata_sp.obsm[proportions_key]

    if isinstance(raw, pd.DataFrame):
        df = raw.copy()
        df.index = adata_sp.obs_names
    else:
        arr = np.asarray(raw)
        # Infer column names
        n_types = arr.shape[1]
        col_names = [f"cell_type_{i}" for i in range(n_types)]
        df = pd.DataFrame(arr, index=adata_sp.obs_names, columns=col_names)

    return df


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def plot_cell_type_proportions(
    adata_sp: sc.AnnData,
    proportions_key: str = "cell_type_proportions",
    cell_types: Optional[List[str]] = None,
    n_cols: int = 3,
    output_dir: str = "results",
) -> None:
    """
    Plot spatial proportion heatmaps for each cell type.

    Creates a multi-panel figure with one spatial heatmap per cell type.
    Spot colour encodes the estimated proportion of that cell type, using
    the viridis colormap. Each panel is independently scaled [0, max].

    Parameters
    ----------
    adata_sp : AnnData
        Spatial AnnData with proportions stored in obsm[proportions_key].
        Must contain adata_sp.obsm['spatial'] with (x, y) coordinates.
    proportions_key : str, optional
        Key in adata_sp.obsm containing the (n_spots, n_types) proportions
        matrix. (default: "cell_type_proportions")
    cell_types : list of str, optional
        Cell types to plot. If None, all columns from the proportions matrix
        are used. (default: None — plot all types)
    n_cols : int, optional
        Number of columns in the multi-panel grid (default: 3).
    output_dir : str, optional
        Directory to save figures (default: "results").

    Returns
    -------
    None
        Saves spatial_proportions.png and spatial_proportions.svg.

    Raises
    ------
    KeyError
        If proportions_key is not found in adata_sp.obsm or if spatial
        coordinates are missing.
    ValueError
        If any specified cell_type is not found in the proportions matrix.

    Notes
    -----
    Uses viridis colormap throughout. Rainbow/jet colormaps are never used.
    Panels without sufficient content are hidden.

    Examples
    --------
    >>> plot_cell_type_proportions(adata_sp)
    >>> plot_cell_type_proportions(
    ...     adata_sp,
    ...     cell_types=["Macrophage", "T_cell", "Epithelial"],
    ...     n_cols=3,
    ...     output_dir="results/deconv",
    ... )
    """
    print("=" * 60)
    print("Cell Type Proportion Spatial Maps")
    print("=" * 60)

    if "spatial" not in adata_sp.obsm:
        raise KeyError(
            "Spatial coordinates not found in adata_sp.obsm['spatial']. "
            "Cannot produce spatial plots."
        )

    prop_df = _get_proportions_matrix(adata_sp, proportions_key)

    if cell_types is None:
        cell_types = list(prop_df.columns)
        print(f"\n  Using all {len(cell_types)} cell types from proportions matrix.")
    else:
        missing = [ct for ct in cell_types if ct not in prop_df.columns]
        if missing:
            raise ValueError(
                f"Cell types not found in proportions matrix: {missing}. "
                f"Available: {list(prop_df.columns)}"
            )

    n_types = len(cell_types)
    n_rows = int(np.ceil(n_types / n_cols))
    print(f"  Cell types:  {n_types}")
    print(f"  Grid:        {n_rows} rows x {n_cols} cols")

    spatial_coords = np.asarray(adata_sp.obsm["spatial"])
    x_coords = spatial_coords[:, 0]
    y_coords = spatial_coords[:, 1]

    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(4.5 * n_cols, 4.0 * n_rows),
        constrained_layout=True,
    )
    axes_flat = np.array(axes).ravel()

    for idx, ct in enumerate(cell_types):
        ax = axes_flat[idx]
        proportions = prop_df[ct].values

        sc_plot = ax.scatter(
            x_coords, y_coords,
            c=proportions,
            cmap="viridis",
            s=5,
            linewidths=0,
            vmin=0,
            vmax=max(proportions.max(), 1e-6),
            rasterized=True,
        )
        plt.colorbar(sc_plot, ax=ax, fraction=0.046, pad=0.04, label="Proportion")
        ax.set_title(ct, fontsize=9, fontweight="bold")
        ax.set_xlabel("X", fontsize=7)
        ax.set_ylabel("Y", fontsize=7)
        ax.tick_params(labelsize=6)
        ax.set_aspect("equal")

    # Hide unused axes
    for idx in range(n_types, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    fig.suptitle("Cell Type Proportions (Spatial)", fontsize=12, fontweight="bold", y=1.01)

    _save_figure(fig, "spatial_proportions", output_dir)


def plot_dominant_cell_type(
    adata_sp: sc.AnnData,
    dominant_key: str = "dominant_cell_type",
    output_dir: str = "results",
) -> None:
    """
    Plot a spatial map coloured by the highest-proportion cell type per spot.

    Each spot is coloured according to the cell type with the highest estimated
    proportion. Uses the tab20 categorical colormap.

    Parameters
    ----------
    adata_sp : AnnData
        Spatial AnnData. Must contain adata_sp.obs[dominant_key] with
        categorical cell type assignments (one label per spot).
        Must also contain adata_sp.obsm['spatial'].
    dominant_key : str, optional
        Column in adata_sp.obs containing the dominant cell type label per spot.
        (default: "dominant_cell_type")
    output_dir : str, optional
        Directory to save figures (default: "results").

    Returns
    -------
    None
        Saves dominant_cell_type.png and dominant_cell_type.svg.

    Raises
    ------
    KeyError
        If dominant_key is not found in adata_sp.obs, or if spatial
        coordinates are missing from adata_sp.obsm.

    Notes
    -----
    If dominant_key is absent but adata_sp.obsm contains a proportions matrix,
    consider first computing the dominant type with:
        prop_df = adata_sp.obsm['cell_type_proportions']
        adata_sp.obs['dominant_cell_type'] = prop_df.idxmax(axis=1)

    Examples
    --------
    >>> # Pre-compute dominant cell type
    >>> prop_df = pd.DataFrame(adata_sp.obsm['cell_type_proportions'])
    >>> adata_sp.obs['dominant_cell_type'] = prop_df.idxmax(axis=1)
    >>> plot_dominant_cell_type(adata_sp, output_dir="results/deconv")
    """
    print("=" * 60)
    print("Dominant Cell Type Spatial Map")
    print("=" * 60)

    if "spatial" not in adata_sp.obsm:
        raise KeyError(
            "Spatial coordinates not found in adata_sp.obsm['spatial']. "
            "Cannot produce spatial plots."
        )

    if dominant_key not in adata_sp.obs.columns:
        raise KeyError(
            f"Dominant cell type key '{dominant_key}' not found in adata_sp.obs. "
            f"Available obs columns: {list(adata_sp.obs.columns[:15])}\n"
            "Compute dominant type first:\n"
            "  prop_df = pd.DataFrame(adata_sp.obsm['cell_type_proportions'])\n"
            "  adata_sp.obs['dominant_cell_type'] = prop_df.idxmax(axis=1)"
        )

    labels = adata_sp.obs[dominant_key].astype(str)
    unique_types = sorted(labels.unique())
    n_types = len(unique_types)
    print(f"\n  Unique cell types: {n_types}")
    for ct in unique_types:
        n = int((labels == ct).sum())
        pct = n / len(labels) * 100
        print(f"    {ct}: {n:,} spots ({pct:.1f}%)")

    # Build colormap from tab20
    cmap = plt.get_cmap("tab20")
    colors = [cmap(i % 20) for i in range(n_types)]
    type_to_color = dict(zip(unique_types, colors))

    spatial_coords = np.asarray(adata_sp.obsm["spatial"])
    x_coords = spatial_coords[:, 0]
    y_coords = spatial_coords[:, 1]
    spot_colors = [type_to_color[lb] for lb in labels]

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.scatter(
        x_coords, y_coords,
        c=spot_colors,
        s=5,
        linewidths=0,
        rasterized=True,
    )
    ax.set_aspect("equal")
    ax.set_title("Dominant Cell Type per Spot", fontsize=12, fontweight="bold")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")

    # Legend
    legend_handles = [
        plt.Line2D(
            [0], [0],
            marker="o", color="w",
            markerfacecolor=type_to_color[ct],
            markersize=8,
            label=ct,
        )
        for ct in unique_types
    ]
    ax.legend(
        handles=legend_handles,
        loc="upper right",
        bbox_to_anchor=(1.28, 1.0),
        frameon=False,
        fontsize=8,
        title="Cell type",
        title_fontsize=9,
    )

    _save_figure(fig, "dominant_cell_type", output_dir)


def plot_proportion_validation(
    adata_sp: sc.AnnData,
    marker_genes_dict: Dict[str, List[str]],
    proportions_key: str = "cell_type_proportions",
    output_dir: str = "results",
) -> None:
    """
    Validate estimated proportions against marker gene expression.

    For each cell type, plots mean marker gene expression per spot against
    the estimated proportion for that type. Pearson correlation coefficient
    and p-value are displayed on each panel.

    Parameters
    ----------
    adata_sp : AnnData
        Spatial AnnData with:
        - Cell type proportions in obsm[proportions_key]
        - Gene expression in layers['counts'] or X
    marker_genes_dict : dict of {str: list of str}
        Mapping from cell type name to a list of marker gene names.
        Example: {"Macrophage": ["CD68", "CSF1R"], "T_cell": ["CD3D", "CD3E"]}
        Cell types not found in the proportions matrix are skipped with a warning.
        Marker genes not found in adata_sp.var_names are skipped with a warning.
    proportions_key : str, optional
        Key in adata_sp.obsm containing cell type proportions.
        (default: "cell_type_proportions")
    output_dir : str, optional
        Directory to save figures (default: "results").

    Returns
    -------
    None
        Saves proportion_validation.png and proportion_validation.svg.

    Raises
    ------
    KeyError
        If proportions_key is not found in adata_sp.obsm.
    ValueError
        If marker_genes_dict is empty or none of its cell types match the
        proportions matrix.

    Notes
    -----
    Mean marker expression is computed across all available marker genes
    for each cell type after log1p normalisation of raw counts. Pearson
    correlation is computed with scipy.stats.pearsonr.

    Examples
    --------
    >>> markers = {
    ...     "Macrophage": ["CD68", "CSF1R", "MRC1"],
    ...     "T_cell": ["CD3D", "CD3E", "CD8A"],
    ...     "Epithelial": ["EPCAM", "KRT8"],
    ... }
    >>> plot_proportion_validation(adata_sp, markers, output_dir="results/deconv")
    """
    from scipy.stats import pearsonr

    print("=" * 60)
    print("Proportion Validation Against Marker Genes")
    print("=" * 60)

    if not marker_genes_dict:
        raise ValueError("marker_genes_dict is empty. Provide at least one cell type.")

    prop_df = _get_proportions_matrix(adata_sp, proportions_key)

    # Retrieve expression matrix
    if "counts" in adata_sp.layers:
        expr_raw = adata_sp.layers["counts"]
        expr_source = "layers['counts']"
    else:
        expr_raw = adata_sp.X
        expr_source = "X"
    print(f"\n  Expression source: adata.{expr_source}")

    if sparse.issparse(expr_raw):
        expr_dense = np.asarray(expr_raw.todense(), dtype=np.float32)
    else:
        expr_dense = np.asarray(expr_raw, dtype=np.float32)

    # log1p transform for visualisation
    expr_log = np.log1p(expr_dense)
    gene_index = {g: i for i, g in enumerate(adata_sp.var_names)}

    # Filter to cell types present in proportions matrix
    valid_types = []
    for ct in marker_genes_dict:
        if ct not in prop_df.columns:
            warnings.warn(
                f"Cell type '{ct}' not found in proportions matrix columns. "
                "Skipping this cell type.",
                UserWarning,
                stacklevel=2,
            )
        else:
            valid_types.append(ct)

    if not valid_types:
        raise ValueError(
            "None of the provided cell types match the proportions matrix. "
            f"Proportions columns: {list(prop_df.columns)}"
        )

    n_types = len(valid_types)
    n_cols = min(3, n_types)
    n_rows = int(np.ceil(n_types / n_cols))
    print(f"  Valid cell types: {n_types}")
    print(f"  Grid: {n_rows} rows x {n_cols} cols")

    fig, axes = plt.subplots(
        n_rows, n_cols,
        figsize=(5.0 * n_cols, 4.5 * n_rows),
        constrained_layout=True,
    )
    axes_flat = np.array(axes).ravel()

    for idx, ct in enumerate(valid_types):
        ax = axes_flat[idx]
        markers = marker_genes_dict[ct]

        # Find available markers
        avail_markers = [g for g in markers if g in gene_index]
        missing_markers = [g for g in markers if g not in gene_index]
        if missing_markers:
            warnings.warn(
                f"Marker genes not found in adata_sp.var_names for '{ct}': "
                f"{missing_markers}. These will be skipped.",
                UserWarning,
                stacklevel=2,
            )

        proportions = prop_df[ct].values

        if not avail_markers:
            ax.text(
                0.5, 0.5,
                f"No marker genes found\nfor {ct}",
                ha="center", va="center",
                transform=ax.transAxes,
                fontsize=9,
            )
            ax.set_title(ct, fontsize=9, fontweight="bold")
            continue

        # Mean log expression across available markers
        marker_cols = [gene_index[g] for g in avail_markers]
        mean_expr = expr_log[:, marker_cols].mean(axis=1)

        # Pearson correlation
        if len(mean_expr) > 2 and np.std(mean_expr) > 0 and np.std(proportions) > 0:
            r, pval = pearsonr(mean_expr, proportions)
            corr_label = f"r = {r:.3f}\np = {pval:.2e}"
        else:
            corr_label = "r = N/A"

        ax.scatter(
            mean_expr, proportions,
            s=6,
            alpha=0.5,
            color="#2E86AB",
            linewidths=0,
            rasterized=True,
        )

        # Trend line
        if np.std(mean_expr) > 0:
            z = np.polyfit(mean_expr, proportions, 1)
            p = np.poly1d(z)
            x_line = np.linspace(mean_expr.min(), mean_expr.max(), 100)
            ax.plot(x_line, p(x_line), color="#E84855", linewidth=1.5, linestyle="--")

        ax.set_xlabel(f"Mean log1p({', '.join(avail_markers[:3])}{'...' if len(avail_markers) > 3 else ''})", fontsize=8)
        ax.set_ylabel("Estimated proportion", fontsize=8)
        ax.set_title(ct, fontsize=9, fontweight="bold")
        ax.text(
            0.05, 0.95,
            corr_label,
            transform=ax.transAxes,
            fontsize=8,
            va="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightyellow", alpha=0.8),
        )
        ax.tick_params(labelsize=7)

    # Hide unused axes
    for idx in range(n_types, len(axes_flat)):
        axes_flat[idx].set_visible(False)

    fig.suptitle("Proportion Validation: Marker Expression vs Estimated Proportion",
                 fontsize=11, fontweight="bold")

    _save_figure(fig, "proportion_validation", output_dir)


def plot_deconvolution_summary(
    adata_sp: sc.AnnData,
    proportions_key: str = "cell_type_proportions",
    output_dir: str = "results",
) -> None:
    """
    Plot a summary of deconvolution results across all spots.

    Creates a two-panel figure:
    - Panel 1: Stacked bar chart of mean cell type proportions (sorted
      descending by mean proportion).
    - Panel 2: Violin plot of proportion distributions per cell type.

    Parameters
    ----------
    adata_sp : AnnData
        Spatial AnnData with proportions stored in obsm[proportions_key].
    proportions_key : str, optional
        Key in adata_sp.obsm containing the proportions matrix.
        (default: "cell_type_proportions")
    output_dir : str, optional
        Directory to save figures (default: "results").

    Returns
    -------
    None
        Saves deconvolution_summary.png and deconvolution_summary.svg.

    Raises
    ------
    KeyError
        If proportions_key is not found in adata_sp.obsm.

    Notes
    -----
    Uses the tab20 colormap for consistent colours across panels.
    Cell types are sorted by mean proportion (descending) in both panels.

    Examples
    --------
    >>> plot_deconvolution_summary(adata_sp, output_dir="results/deconv")
    """
    print("=" * 60)
    print("Deconvolution Summary")
    print("=" * 60)

    prop_df = _get_proportions_matrix(adata_sp, proportions_key)

    mean_props = prop_df.mean(axis=0).sort_values(ascending=False)
    cell_types_sorted = list(mean_props.index)
    n_types = len(cell_types_sorted)
    print(f"\n  Cell types: {n_types}")
    print(f"  Spots:      {len(prop_df):,}")

    cmap = plt.get_cmap("tab20")
    colors = [cmap(i % 20) for i in range(n_types)]
    type_to_color = dict(zip(cell_types_sorted, colors))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)

    # --- Panel 1: Stacked bar (mean proportions) ---
    cumulative = 0.0
    for ct in cell_types_sorted:
        val = float(mean_props[ct])
        ax1.barh(
            0, val,
            left=cumulative,
            color=type_to_color[ct],
            edgecolor="white",
            linewidth=0.5,
            label=ct,
            height=0.6,
        )
        if val > 0.03:
            ax1.text(
                cumulative + val / 2, 0,
                f"{val:.2f}",
                ha="center", va="center",
                fontsize=7, color="white", fontweight="bold",
            )
        cumulative += val

    ax1.set_xlim(0, 1)
    ax1.set_yticks([])
    ax1.set_xlabel("Mean proportion", fontsize=10)
    ax1.set_title("Mean Cell Type Proportions\n(across all spots)", fontsize=10, fontweight="bold")
    ax1.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.35),
        ncol=min(4, n_types),
        frameon=False,
        fontsize=8,
    )

    # --- Panel 2: Violin plot ---
    prop_long = prop_df[cell_types_sorted].melt(
        var_name="Cell type", value_name="Proportion"
    )
    order = cell_types_sorted

    sns.violinplot(
        data=prop_long,
        x="Cell type",
        y="Proportion",
        order=order,
        palette={ct: type_to_color[ct] for ct in cell_types_sorted},
        inner="box",
        cut=0,
        linewidth=0.8,
        ax=ax2,
    )
    ax2.set_xticklabels(
        [ct for ct in order],
        rotation=45,
        ha="right",
        fontsize=8,
    )
    ax2.set_xlabel("Cell type", fontsize=10)
    ax2.set_ylabel("Proportion", fontsize=10)
    ax2.set_title("Proportion Distribution per Cell Type", fontsize=10, fontweight="bold")
    ax2.yaxis.grid(True, linewidth=0.5, alpha=0.5)
    ax2.set_axisbelow(True)

    fig.suptitle("Deconvolution Summary", fontsize=12, fontweight="bold")

    _save_figure(fig, "deconvolution_summary", output_dir)


def plot_training_history_spatial(
    model: Any,
    model_name: str = "",
    output_dir: str = "results",
) -> None:
    """
    Plot training loss curves for a spatial deconvolution model.

    Adapts to different model types:
    - Cell2location: looks for model.history['elbo_train'] and
      model.history['elbo_validation'] (or similar keys).
    - scvi-tools models (DestVI, scVIVA): model.history['elbo_train'].
    - Tangram: no training history — prints a message and exits cleanly.

    Parameters
    ----------
    model : trained model object
        Any trained spatial model with a .history attribute
        (Cell2location, DestVI, scVIVA) or without (Tangram).
    model_name : str, optional
        Short name for labelling the figure title and output filename.
        Example: "Cell2location", "DestVI", "scVIVA". (default: "")
    output_dir : str, optional
        Directory to save figures (default: "results").

    Returns
    -------
    None
        Saves {model_name}_training.png and {model_name}_training.svg,
        or spatial_model_training.png/.svg if model_name is empty.
        Does nothing (prints message) if no training history is available.

    Notes
    -----
    Key name resolution is attempted in order:
      1. 'elbo_train' (scvi-tools standard)
      2. 'train_elbo' (Cell2location variant)
      3. 'loss_train' / 'loss'
      Validation keys: 'elbo_validation', 'validation_elbo', 'loss_validation'

    Examples
    --------
    >>> plot_training_history_spatial(model, model_name="Cell2location",
    ...                               output_dir="results/deconv")
    >>> plot_training_history_spatial(model, model_name="DestVI",
    ...                               output_dir="results/deconv")
    """
    print("=" * 60)
    label = model_name if model_name else "Spatial Model"
    print(f"Training History: {label}")
    print("=" * 60)

    # --- Check for history attribute ---
    if not hasattr(model, "history") or model.history is None:
        print(
            f"\n  No training history available for {label}. "
            "This is expected for Tangram (non-gradient optimization) "
            "and some RCTD configurations. Skipping plot."
        )
        return

    history = model.history

    # Tangram-specific: check known Tangram attributes
    model_class = type(model).__name__
    if "Tangram" in model_class:
        print(
            f"\n  {label} is a Tangram model. Tangram does not expose "
            "gradient-based training history. Skipping plot."
        )
        return

    if not history:
        print(f"\n  model.history is present but empty for {label}. Skipping plot.")
        return

    # --- Key resolution ---
    TRAIN_KEY_CANDIDATES = [
        "elbo_train",
        "train_elbo",
        "loss_train",
        "loss",
        "training_loss",
    ]
    VAL_KEY_CANDIDATES = [
        "elbo_validation",
        "validation_elbo",
        "loss_validation",
        "val_loss",
        "validation_loss",
    ]

    train_key: Optional[str] = None
    val_key: Optional[str] = None

    for k in TRAIN_KEY_CANDIDATES:
        if k in history:
            train_key = k
            break

    for k in VAL_KEY_CANDIDATES:
        if k in history:
            val_key = k
            break

    if train_key is None:
        available = list(history.keys())
        print(
            f"\n  No recognized training loss key found in model.history.\n"
            f"  Available keys: {available}\n"
            "  Skipping plot."
        )
        return

    print(f"\n  Training key:   {train_key}")
    print(f"  Validation key: {val_key if val_key else 'not found'}")

    # --- Extract loss values ---
    def _to_array(val: Any) -> np.ndarray:
        if isinstance(val, pd.DataFrame):
            return val.values.ravel()
        if isinstance(val, pd.Series):
            return val.values.ravel()
        return np.asarray(val).ravel()

    train_loss = _to_array(history[train_key])
    val_loss = _to_array(history[val_key]) if val_key else None

    n_epochs = len(train_loss)
    print(f"  Epochs recorded: {n_epochs}")
    print(f"  Final train loss: {train_loss[-1]:.4f}")
    if val_loss is not None:
        print(f"  Final val loss:   {val_loss[-1]:.4f}")

    # --- Plot ---
    has_val = val_loss is not None and len(val_loss) > 0

    fig, axes = plt.subplots(
        1, 2 if has_val else 1,
        figsize=(12 if has_val else 7, 4),
        constrained_layout=True,
    )
    if not has_val:
        axes = [axes]

    title_prefix = f"{model_name} " if model_name else ""

    # Full curve
    ax = axes[0]
    epochs = np.arange(1, n_epochs + 1)
    ax.plot(epochs, train_loss, color="#2E86AB", linewidth=1.5, label="Train ELBO")
    if has_val:
        val_epochs = np.arange(1, len(val_loss) + 1)
        ax.plot(val_epochs, val_loss, color="#E84855", linewidth=1.5, linestyle="--", label="Validation ELBO")
        ax.legend(fontsize=9, frameon=False)
    ax.set_xlabel("Epoch", fontsize=10)
    ax.set_ylabel("ELBO", fontsize=10)
    ax.set_title(f"{title_prefix}Training Curve (Full)", fontsize=10, fontweight="bold")
    ax.yaxis.grid(True, linewidth=0.5, alpha=0.5)
    ax.set_axisbelow(True)

    # Fine convergence view (last 20%)
    if has_val:
        ax2 = axes[1]
        cutoff = max(1, int(0.8 * n_epochs))
        ax2.plot(epochs[cutoff:], train_loss[cutoff:], color="#2E86AB", linewidth=1.5, label="Train ELBO")
        val_cutoff = max(1, int(0.8 * len(val_loss)))
        val_ep2 = np.arange(val_cutoff + 1, len(val_loss) + 1)
        ax2.plot(val_ep2, val_loss[val_cutoff:], color="#E84855", linewidth=1.5,
                 linestyle="--", label="Validation ELBO")
        ax2.legend(fontsize=9, frameon=False)
        ax2.set_xlabel("Epoch", fontsize=10)
        ax2.set_ylabel("ELBO", fontsize=10)
        ax2.set_title(f"{title_prefix}Training Curve (Final 20%)", fontsize=10, fontweight="bold")
        ax2.yaxis.grid(True, linewidth=0.5, alpha=0.5)
        ax2.set_axisbelow(True)

    fig.suptitle(f"{title_prefix}Training History", fontsize=12, fontweight="bold")

    fname = f"{model_name.lower().replace(' ', '_')}_training" if model_name else "spatial_model_training"
    _save_figure(fig, fname, output_dir)


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("plot_spatial_deconv.py — Example Usage")
    print("=" * 60)
    print()
    print("Visualize deconvolution results from Cell2location, DestVI, or RCTD:")
    print()
    print("  import scanpy as sc")
    print("  from plot_spatial_deconv import (")
    print("      plot_cell_type_proportions,")
    print("      plot_dominant_cell_type,")
    print("      plot_proportion_validation,")
    print("      plot_deconvolution_summary,")
    print("      plot_training_history_spatial,")
    print("  )")
    print()
    print("  adata_sp = sc.read_h5ad('results/adata_deconvolved.h5ad')")
    print()
    print("  # 1. Spatial proportion maps (one panel per cell type)")
    print("  plot_cell_type_proportions(adata_sp, output_dir='results/figures')")
    print()
    print("  # 2. Dominant cell type map")
    print("  import pandas as pd")
    print("  prop_df = pd.DataFrame(adata_sp.obsm['cell_type_proportions'])")
    print("  adata_sp.obs['dominant_cell_type'] = prop_df.idxmax(axis=1)")
    print("  plot_dominant_cell_type(adata_sp, output_dir='results/figures')")
    print()
    print("  # 3. Validate proportions against marker genes")
    print("  markers = {")
    print("      'Macrophage': ['CD68', 'CSF1R', 'MRC1'],")
    print("      'T_cell': ['CD3D', 'CD3E', 'CD8A'],")
    print("  }")
    print("  plot_proportion_validation(adata_sp, markers, output_dir='results/figures')")
    print()
    print("  # 4. Overall deconvolution summary")
    print("  plot_deconvolution_summary(adata_sp, output_dir='results/figures')")
    print()
    print("  # 5. Training history (skips automatically for Tangram)")
    print("  plot_training_history_spatial(model, model_name='Cell2location',")
    print("                                output_dir='results/figures')")
