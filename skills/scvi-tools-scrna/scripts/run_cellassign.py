"""
Marker-Based Cell Type Assignment with CellAssign

This module implements marker-based probabilistic cell type assignment using
CellAssign (Zhang et al. 2019, Nature Methods). CellAssign uses a user-supplied
binary marker gene matrix as prior knowledge to assign each cell to a predefined
type or an "other" category via an EM-based generative model.

For methodology details see: https://doi.org/10.1038/s41592-019-0535-3

Functions:
  - create_marker_matrix(): Build a binary gene x cell-type DataFrame from a dict
  - validate_marker_matrix(): Cross-reference marker genes against adata.var_names
  - train_cellassign(): Set up and train the CellAssign model, write predictions
  - get_assignment_probabilities(): Retrieve per-cell soft assignment probabilities
  - summarize_assignments(): Summarise cell counts, proportions, and mean confidence

Requirements:
  - scvi-tools >= 1.1: pip install scvi-tools
  - torch: pip install torch
  - GPU recommended for training (10-20x faster)

Notes
-----
CellAssign is accessed as scvi.external.CellAssign (not scvi.model).
It expects raw integer counts in adata.layers['counts'] and a size_factor
column in adata.obs for proper normalisation.
"""

import warnings
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import scanpy as sc

try:
    import scvi
except ImportError:
    raise ImportError(
        "scvi-tools is required for CellAssign.\n"
        "Install with: pip install scvi-tools"
    )

from setup_scvi import detect_accelerator


# ---------------------------------------------------------------------------
# 1. create_marker_matrix
# ---------------------------------------------------------------------------

def create_marker_matrix(marker_dict: Dict[str, List[str]]) -> pd.DataFrame:
    """
    Build a binary gene x cell-type marker matrix from a dictionary.

    Parameters
    ----------
    marker_dict : dict
        Mapping of cell type name -> list of marker gene symbols.
        Example::

            {
                "T cells":   ["CD3D", "CD3E", "CD4"],
                "B cells":   ["CD19", "MS4A1"],
                "Monocytes": ["CD14", "LYZ", "CST3"],
            }

    Returns
    -------
    pd.DataFrame
        Binary DataFrame with genes as the index and cell types as columns.
        Entry is 1 where a gene is a marker for a given type, 0 otherwise.

    Notes
    -----
    - All genes across every cell type are collected as the row index.
    - Duplicate gene names within a single cell type are silently deduplicated.

    Examples
    --------
    >>> marker_mat = create_marker_matrix({"T cells": ["CD3D", "CD4"]})
    >>> marker_mat.shape
    (2, 1)
    """
    print("=" * 60)
    print("Building Marker Matrix")
    print("=" * 60)

    if not marker_dict:
        raise ValueError("marker_dict is empty. Provide at least one cell type.")

    n_types = len(marker_dict)

    # Collect all unique genes across all cell types (preserve insertion order)
    all_genes: List[str] = []
    seen: set = set()
    for genes in marker_dict.values():
        for g in genes:
            if g not in seen:
                all_genes.append(g)
                seen.add(g)

    n_genes = len(all_genes)

    # Build binary DataFrame
    mat = pd.DataFrame(0, index=all_genes, columns=list(marker_dict.keys()))
    for cell_type, genes in marker_dict.items():
        unique_genes = list(dict.fromkeys(genes))  # deduplicate, keep order
        mat.loc[unique_genes, cell_type] = 1

    # Print summary
    print(f"\n  Cell types : {n_types}")
    print(f"  Total genes: {n_genes}")
    print(f"\n  Markers per cell type:")
    for cell_type in mat.columns:
        n_markers = int(mat[cell_type].sum())
        print(f"    {cell_type}: {n_markers} markers")

    print(f"\n  ✓ Marker matrix created  ({n_genes} genes x {n_types} cell types)")
    return mat


# ---------------------------------------------------------------------------
# 2. validate_marker_matrix
# ---------------------------------------------------------------------------

def validate_marker_matrix(
    marker_mat: pd.DataFrame,
    adata: sc.AnnData,
) -> pd.DataFrame:
    """
    Validate a marker matrix against an AnnData object and filter to
    genes that are actually present in adata.var_names.

    Parameters
    ----------
    marker_mat : pd.DataFrame
        Binary gene x cell-type marker matrix (genes as index, types as columns).
        See :func:`create_marker_matrix`.
    adata : AnnData
        AnnData object whose var_names define the measurable gene universe.

    Returns
    -------
    pd.DataFrame
        Filtered marker matrix containing only genes present in adata.var_names.

    Raises
    ------
    ValueError
        If any cell type retains fewer than 2 marker genes after filtering, or
        if marker_mat has zero rows after filtering.

    Notes
    -----
    - If the matrix appears transposed (columns look like genes rather than
      cell types), a warning is issued and the matrix is transposed automatically.
    - Missing marker genes are printed by name so they can be inspected.

    Examples
    --------
    >>> marker_mat = validate_marker_matrix(marker_mat, adata)
    """
    print("=" * 60)
    print("Validating Marker Matrix")
    print("=" * 60)

    # --- Orientation check ---
    # Heuristic: if the number of columns >> number of rows it is likely
    # that genes ended up as columns instead of rows.
    if marker_mat.shape[1] > marker_mat.shape[0]:
        warnings.warn(
            "Marker matrix has more columns than rows. "
            "Expected orientation: genes as index, cell types as columns. "
            "Transposing the matrix. Verify that this is correct.",
            UserWarning,
            stacklevel=2,
        )
        print("\n  [WARNING] Matrix appears transposed. Transposing automatically.")
        marker_mat = marker_mat.T

    print(f"\n  Input matrix: {marker_mat.shape[0]} genes x {marker_mat.shape[1]} cell types")

    # --- Check gene overlap ---
    adata_genes = set(adata.var_names)
    marker_genes = set(marker_mat.index)

    missing = marker_genes - adata_genes
    present = marker_genes & adata_genes

    if missing:
        print(f"\n  [WARNING] {len(missing)} marker gene(s) not found in adata.var_names:")
        for g in sorted(missing):
            print(f"    - {g}")

    print(f"\n  Genes in marker matrix   : {len(marker_genes)}")
    print(f"  Genes found in adata     : {len(present)}")
    print(f"  Genes missing (dropped)  : {len(missing)}")

    # Filter to present genes
    filtered = marker_mat.loc[marker_mat.index.isin(adata_genes)].copy()

    if filtered.shape[0] == 0:
        raise ValueError(
            "No marker genes remain after filtering against adata.var_names. "
            "Verify that gene identifiers (symbols, Ensembl IDs, etc.) match."
        )

    # --- Check per-type marker count ---
    markers_per_type = filtered.sum(axis=0)
    low_types = markers_per_type[markers_per_type < 2]
    if len(low_types) > 0:
        details = ", ".join(
            f"'{ct}' ({int(n)} marker{'s' if n != 1 else ''})"
            for ct, n in low_types.items()
        )
        raise ValueError(
            f"The following cell type(s) have fewer than 2 marker genes after "
            f"filtering: {details}. CellAssign requires at least 2 markers per "
            f"type to estimate parameters reliably. Add more markers or remove "
            f"this type."
        )

    # Print validation summary
    print(f"\n  Validated marker matrix: {filtered.shape[0]} genes x {filtered.shape[1]} cell types")
    print(f"\n  Retained markers per cell type:")
    for cell_type in filtered.columns:
        n_retained = int(markers_per_type[cell_type])
        print(f"    {cell_type}: {n_retained}")

    print(f"\n  ✓ Marker matrix validated")
    return filtered


# ---------------------------------------------------------------------------
# 3. train_cellassign
# ---------------------------------------------------------------------------

def train_cellassign(
    adata: sc.AnnData,
    marker_mat: pd.DataFrame,
    max_epochs: int = 400,
    save_model: Optional[Union[str, Path]] = None,
) -> Tuple[sc.AnnData, "scvi.external.CellAssign"]:
    """
    Train a CellAssign model and store predictions on the full AnnData.

    CellAssign (Zhang et al. 2019) uses a binary marker matrix as prior
    knowledge and fits cell-type assignments via stochastic EM with
    mini-batches over a negative-binomial generative model.

    Parameters
    ----------
    adata : AnnData
        AnnData object with raw integer counts in adata.layers['counts'].
    marker_mat : pd.DataFrame
        Binary gene x cell-type matrix (genes as index, types as columns).
        Will be validated against adata before training.
    max_epochs : int, optional
        Maximum training epochs (default: 400).
    save_model : str or Path, optional
        If provided, save the trained model to this directory (default: None).

    Returns
    -------
    tuple
        (adata, model) — the full AnnData (with predictions in .obs and
        metadata in .uns) and the trained CellAssign model object.

    Notes
    -----
    - CellAssign is located at ``scvi.external.CellAssign``.
    - The function subsets adata to marker genes for training but writes
      predictions back to the **full** adata.
    - Size factors are computed as library size divided by the median library
      size and stored in ``adata_subset.obs['size_factor']``.
    - Predictions are stored in ``adata.obs['cellassign_predictions']``.
    - Training metadata is stored in ``adata.uns['cellassign_info']``.

    Examples
    --------
    >>> adata, model = train_cellassign(adata, marker_mat, max_epochs=400)
    >>> adata.obs['cellassign_predictions'].value_counts()
    """
    print("=" * 60)
    print("CellAssign: Marker-Based Cell Type Assignment")
    print("=" * 60)

    # --- Validate marker matrix ---
    print("\nStep 1/5  Validating marker matrix...")
    marker_mat = validate_marker_matrix(marker_mat, adata)

    # --- Subset adata to marker genes ---
    print("\nStep 2/5  Subsetting to marker genes...")
    marker_genes = marker_mat.index.tolist()
    adata_subset = adata[:, marker_genes].copy()
    print(f"  Subset shape: {adata_subset.n_obs:,} cells x {adata_subset.n_vars:,} genes")

    # --- Compute size factors ---
    print("\nStep 3/5  Computing size factors...")
    from scipy import sparse

    if "counts" in adata_subset.layers:
        count_matrix = adata_subset.layers["counts"]
    else:
        warnings.warn(
            "No 'counts' layer found in adata. Using adata.X for size factor "
            "computation. Ensure adata.X contains raw integer counts.",
            UserWarning,
            stacklevel=2,
        )
        count_matrix = adata_subset.X

    if sparse.issparse(count_matrix):
        lib_size = np.asarray(count_matrix.sum(axis=1)).ravel()
    else:
        lib_size = np.asarray(count_matrix).sum(axis=1).ravel()

    median_lib = np.median(lib_size)
    if median_lib == 0:
        raise ValueError(
            "Median library size is zero. Check that adata.layers['counts'] "
            "contains non-zero raw counts."
        )

    size_factor = lib_size / median_lib
    adata_subset.obs["size_factor"] = size_factor

    print(f"  Median library size : {median_lib:,.1f}")
    print(f"  Size factor range   : [{size_factor.min():.3f}, {size_factor.max():.3f}]")
    print(f"  ✓ Size factors stored in adata_subset.obs['size_factor']")

    # --- Setup AnnData for CellAssign ---
    print("\nStep 4/5  Setting up CellAssign model...")

    layer = "counts" if "counts" in adata_subset.layers else None
    scvi.external.CellAssign.setup_anndata(
        adata_subset,
        layer=layer,
        size_factor_key="size_factor",
    )

    model = scvi.external.CellAssign(adata_subset, marker_mat)
    print(f"  Cell types modelled: {list(marker_mat.columns)}")
    print(f"  Marker genes used  : {adata_subset.n_vars}")

    # --- Train ---
    print(f"\nStep 5/5  Training CellAssign model...")
    accelerator = detect_accelerator()
    print(f"  Max epochs  : {max_epochs}")
    print(f"  Accelerator : {accelerator}")

    model.train(max_epochs=max_epochs, accelerator=accelerator)
    print(f"  ✓ Training complete")

    # --- Predictions ---
    print("\nExtracting predictions...")
    prob_df = model.predict()  # cells x cell_types, probabilities

    # Hard assignment: argmax across cell type columns
    predicted_types = prob_df.idxmax(axis=1).values

    # Write to the full adata (index alignment via .obs_names)
    adata.obs["cellassign_predictions"] = pd.Categorical(
        predicted_types, categories=list(marker_mat.columns)
    )

    # Store soft probabilities on full adata
    # Column name: cellassign_prob_<CellType>
    for cell_type in prob_df.columns:
        col_key = f"cellassign_prob_{cell_type.replace(' ', '_')}"
        adata.obs[col_key] = prob_df[cell_type].values

    n_assigned = (adata.obs["cellassign_predictions"] != "other").sum()
    print(f"  Assigned cells     : {n_assigned:,} / {adata.n_obs:,}")
    print(f"  ✓ Predictions stored in adata.obs['cellassign_predictions']")

    # --- Store metadata ---
    adata.uns["cellassign_info"] = {
        "cell_types": list(marker_mat.columns),
        "n_marker_genes": int(marker_mat.shape[0]),
        "n_cell_types": int(marker_mat.shape[1]),
        "max_epochs": max_epochs,
        "accelerator": accelerator,
        "layer": layer,
        "size_factor_key": "size_factor",
        "prediction_key": "cellassign_predictions",
        "markers_per_type": {
            ct: int(marker_mat[ct].sum()) for ct in marker_mat.columns
        },
    }

    # --- Save model ---
    if save_model is not None:
        save_path = Path(save_model)
        save_path.mkdir(parents=True, exist_ok=True)
        model.save(save_path, overwrite=True)
        print(f"\n  Model saved to: {save_path}")

    print("\n" + "=" * 60)
    print("CellAssign training complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  probs = get_assignment_probabilities(model, adata)")
    print("  summary = summarize_assignments(adata)")
    print("  sc.pl.umap(adata, color='cellassign_predictions')")

    return adata, model


# ---------------------------------------------------------------------------
# 4. get_assignment_probabilities
# ---------------------------------------------------------------------------

def get_assignment_probabilities(
    model: "scvi.external.CellAssign",
    adata: sc.AnnData,
) -> pd.DataFrame:
    """
    Retrieve soft cell-type assignment probabilities from a trained CellAssign model.

    Parameters
    ----------
    model : scvi.external.CellAssign
        A trained CellAssign model (returned by :func:`train_cellassign`).
    adata : AnnData
        The AnnData object used for training (needed for cell-level index).

    Returns
    -------
    pd.DataFrame
        DataFrame of shape (n_cells, n_cell_types) with probability values.
        Row index matches adata.obs_names.

    Notes
    -----
    model.predict() returns a DataFrame indexed 0..n-1; this function resets
    the index to adata.obs_names for downstream convenience.

    Examples
    --------
    >>> probs = get_assignment_probabilities(model, adata)
    >>> probs.head()
    """
    print("=" * 60)
    print("Retrieving Assignment Probabilities")
    print("=" * 60)

    prob_df: pd.DataFrame = model.predict()
    prob_df.index = adata.obs_names

    print(f"\n  Probability matrix shape: {prob_df.shape[0]:,} cells x {prob_df.shape[1]} cell types")
    print(f"\n  Summary statistics per cell type (mean probability):")

    for cell_type in prob_df.columns:
        col = prob_df[cell_type]
        print(
            f"    {cell_type:<30s}  mean={col.mean():.3f}  "
            f"median={col.median():.3f}  "
            f"max={col.max():.3f}"
        )

    print(f"\n  ✓ Probabilities returned as DataFrame")
    return prob_df


# ---------------------------------------------------------------------------
# 5. summarize_assignments
# ---------------------------------------------------------------------------

def summarize_assignments(
    adata: sc.AnnData,
    prediction_key: str = "cellassign_predictions",
) -> pd.DataFrame:
    """
    Summarise CellAssign cell type assignments stored in adata.obs.

    Computes cell counts, proportions, and mean confidence (if probabilities
    are available in adata.obs). Flags cell types with low mean confidence.

    Parameters
    ----------
    adata : AnnData
        AnnData object with predictions in adata.obs[prediction_key].
    prediction_key : str, optional
        Column in adata.obs containing cell type predictions
        (default: "cellassign_predictions").

    Returns
    -------
    pd.DataFrame
        Summary DataFrame with columns:
        - ``n_cells``: absolute cell count
        - ``proportion``: fraction of total cells
        - ``mean_confidence``: mean probability for the assigned type
          (NaN if probability columns are not in adata.obs)
        - ``low_confidence``: True if mean_confidence < 0.70

    Raises
    ------
    KeyError
        If prediction_key is not found in adata.obs.

    Examples
    --------
    >>> summary = summarize_assignments(adata)
    >>> summary[summary['low_confidence']]
    """
    print("=" * 60)
    print("CellAssign Assignment Summary")
    print("=" * 60)

    if prediction_key not in adata.obs.columns:
        raise KeyError(
            f"Prediction key '{prediction_key}' not found in adata.obs. "
            f"Run train_cellassign() first or check the prediction_key argument."
        )

    predictions = adata.obs[prediction_key]
    counts = predictions.value_counts().sort_index()
    proportions = counts / counts.sum()

    summary = pd.DataFrame(
        {
            "n_cells": counts,
            "proportion": proportions,
        }
    )

    # Try to attach mean confidence per type from stored probability columns
    LOW_CONFIDENCE_THRESHOLD = 0.70
    mean_conf: Dict[str, float] = {}

    for cell_type in summary.index:
        col_key = f"cellassign_prob_{cell_type.replace(' ', '_')}"
        if col_key in adata.obs.columns:
            mask = predictions == cell_type
            if mask.sum() > 0:
                mean_conf[cell_type] = float(adata.obs.loc[mask, col_key].mean())
            else:
                mean_conf[cell_type] = float("nan")

    if mean_conf:
        summary["mean_confidence"] = pd.Series(mean_conf)
        summary["low_confidence"] = summary["mean_confidence"] < LOW_CONFIDENCE_THRESHOLD
    else:
        summary["mean_confidence"] = float("nan")
        summary["low_confidence"] = False
        print(
            "\n  [INFO] Probability columns not found in adata.obs. "
            "Run train_cellassign() to populate per-type probability columns."
        )

    # --- Print formatted table ---
    total_cells = int(summary["n_cells"].sum())
    print(f"\n  Total cells: {total_cells:,}")
    print(f"\n  {'Cell Type':<30s}  {'N Cells':>8s}  {'Prop':>6s}  {'Mean Conf':>10s}  {'Flag':>5s}")
    print(f"  {'-'*30}  {'-'*8}  {'-'*6}  {'-'*10}  {'-'*5}")

    for cell_type, row in summary.iterrows():
        conf_str = f"{row['mean_confidence']:.3f}" if not np.isnan(row["mean_confidence"]) else "  n/a "
        flag_str = "LOW" if row["low_confidence"] else "  ok"
        print(
            f"  {str(cell_type):<30s}  {int(row['n_cells']):>8,}  "
            f"{row['proportion']:>5.1%}  {conf_str:>10s}  {flag_str:>5s}"
        )

    n_low = int(summary["low_confidence"].sum())
    if n_low > 0:
        print(
            f"\n  [WARNING] {n_low} cell type(s) have mean confidence < "
            f"{LOW_CONFIDENCE_THRESHOLD:.0%}. Consider revising marker lists "
            "or inspecting these populations manually."
        )
    else:
        print(f"\n  ✓ All cell types meet the confidence threshold ({LOW_CONFIDENCE_THRESHOLD:.0%})")

    print(f"\n  ✓ Summary returned as DataFrame")
    return summary


# ---------------------------------------------------------------------------
# __main__
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("CellAssign: Marker-Based Cell Type Assignment")
    print("=" * 60)
    print()
    print("Example workflow:")
    print()
    print("  from run_cellassign import (")
    print("      create_marker_matrix,")
    print("      validate_marker_matrix,")
    print("      train_cellassign,")
    print("      get_assignment_probabilities,")
    print("      summarize_assignments,")
    print("  )")
    print()
    print("  # 1. Define marker genes per cell type")
    print("  marker_dict = {")
    print("      'T cells':   ['CD3D', 'CD3E', 'CD4', 'CD8A'],")
    print("      'B cells':   ['CD19', 'MS4A1', 'CD79A'],")
    print("      'Monocytes': ['CD14', 'LYZ', 'CST3', 'FCGR3A'],")
    print("      'NK cells':  ['GNLY', 'NKG7', 'KLRD1'],")
    print("  }")
    print()
    print("  # 2. Build marker matrix")
    print("  marker_mat = create_marker_matrix(marker_dict)")
    print()
    print("  # 3. Train CellAssign (validates internally)")
    print("  adata, model = train_cellassign(")
    print("      adata, marker_mat, max_epochs=400, save_model='results/cellassign_model'")
    print("  )")
    print()
    print("  # 4. Retrieve soft probabilities")
    print("  probs = get_assignment_probabilities(model, adata)")
    print()
    print("  # 5. Summarise assignments")
    print("  summary = summarize_assignments(adata)")
    print()
    print("  # 6. Visualise")
    print("  sc.pl.umap(adata, color='cellassign_predictions')")
