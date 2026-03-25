"""
Cell2location Spatial Deconvolution

This module implements the two-stage Cell2location workflow: reference signature
estimation from annotated scRNA-seq data, followed by probabilistic spatial
deconvolution of Visium (or equivalent) spots into cell type abundances.

Cell2location is a separate package from scvi-tools. Install it with:
  pip install cell2location

Stage 1 — Reference model (RegressionModel):
  Learns per-cell-type mean expression signatures from annotated scRNA-seq.
  Training is fast (~250 epochs, minutes on GPU).

Stage 2 — Spatial model (Cell2location):
  Decomposes each spatial spot into cell type abundances using the reference
  signatures.  Training is slow: 30,000 epochs on a modern GPU takes 1-4 hours
  depending on dataset size.  Plan accordingly.

Functions:
  - train_reference_model(): Estimate cell type signatures from scRNA-seq reference
  - train_cell2location(): Deconvolve spatial spots using reference signatures
  - get_cell_type_proportions(): Convert raw abundances to normalized proportions

Requirements:
  - cell2location: pip install cell2location
  - scanpy: pip install scanpy
  - GPU strongly recommended (training on CPU is prohibitively slow)

References:
  Kleshchevnikov et al. (2022) Nature Biotechnology
  https://doi.org/10.1038/s41587-021-01139-4

Notes on hyperparameter tuning:
  - N_cells_per_location: Start with estimated average cells per spot.
    For Visium 10x data, typically 5-10 for dense tissue, up to 30 for cell-rich
    regions.  This is the single most important hyperparameter.
  - detection_alpha: Controls sensitivity to within-spot detection efficiency
    variation.  Default 20 works for most datasets.  Increase for highly
    variable capture efficiency.
  - The q05 quantile (5th posterior percentile) is the recommended output for
    downstream analysis: it is conservative and avoids inflated abundance
    estimates.
"""

import warnings
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
import pandas as pd
import scanpy as sc

try:
    import cell2location
    from cell2location.utils.filtering import filter_genes
except ImportError:
    raise ImportError(
        "cell2location is required for this module.\n"
        "Install with: pip install cell2location\n"
        "Note: cell2location is a separate package from scvi-tools."
    )

from setup_spatial import filter_genes_for_deconvolution


def _use_gpu_to_accelerator(use_gpu: bool) -> str:
    """Convert legacy use_gpu bool to accelerator string.

    cell2location 0.1.x was built for scvi-tools <1.1 which used use_gpu=.
    scvi-tools >=1.1 uses accelerator=. This helper bridges the gap.
    """
    if not use_gpu:
        return "cpu"
    try:
        import torch
        if torch.cuda.is_available():
            return "gpu"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "cpu"  # MPS often has float64 issues with cell2location
    except ImportError:
        pass
    return "cpu"


def train_reference_model(
    adata_ref: sc.AnnData,
    labels_key: str = "cell_type",
    batch_key: Optional[str] = None,
    max_epochs: int = 250,
    use_gpu: bool = True,
    save_model: Optional[Union[str, Path]] = None,
) -> Tuple[sc.AnnData, "cell2location.models.RegressionModel"]:
    """
    Train a Cell2location RegressionModel to estimate cell type signatures.

    Filters genes permissively, sets up and trains a negative-binomial
    regression model on annotated scRNA-seq data, exports posterior estimates
    of mean gene expression per cell type, and stores them in
    adata_ref.varm['means_per_cluster_mu_fg'].

    The resulting signatures are the direct input to ``train_cell2location``.

    Parameters
    ----------
    adata_ref : AnnData
        Annotated scRNA-seq AnnData with raw counts in layers['counts'] or X.
        Must contain cell type labels in ``labels_key``.
    labels_key : str, optional
        Column in adata_ref.obs containing cell type annotations (default:
        'cell_type').
    batch_key : str or None, optional
        Column in adata_ref.obs identifying technical batches / donors.  Pass
        None to fit a single-batch model (default: None).
    max_epochs : int, optional
        Maximum number of training epochs (default: 250).  250 is generally
        sufficient for reference model convergence.
    use_gpu : bool, optional
        Whether to use GPU for training (default: True).
        Cell2location uses ``use_gpu``, not the scvi-tools ``accelerator``
        parameter.
    save_model : str or Path or None, optional
        Directory path to save the trained model.  The directory is created
        if it does not exist.  (default: None — model is not persisted)

    Returns
    -------
    tuple of (AnnData, RegressionModel)
        - adata_ref: Input AnnData updated with:
            - adata_ref.varm['means_per_cluster_mu_fg']: DataFrame of shape
              (n_genes, n_cell_types) containing posterior mean signatures
            - adata_ref.uns['cell2location_ref_info']: dict of training metadata
        - model: Trained cell2location.models.RegressionModel instance

    Raises
    ------
    ValueError
        If ``labels_key`` is not found in adata_ref.obs.
    ImportError
        If cell2location is not installed.

    Notes
    -----
    Gene filtering uses ``filter_genes_for_deconvolution`` from setup_spatial,
    which applies permissive thresholds (cell_count_cutoff=5,
    cell_pct_cutoff=0.03, nonz_mean_cutoff=1.12) consistent with Cell2location
    defaults.

    Examples
    --------
    >>> adata_ref, mod_ref = train_reference_model(
    ...     adata_ref,
    ...     labels_key='cell_type',
    ...     batch_key='donor',
    ...     max_epochs=250,
    ...     use_gpu=True,
    ...     save_model='results/c2l_ref_model',
    ... )
    >>> ref_signatures = adata_ref.varm['means_per_cluster_mu_fg']
    """
    print("=" * 60)
    print("Cell2location: Reference Signature Model (Stage 1 / 2)")
    print("=" * 60)

    # --- Validate labels key ---
    if labels_key not in adata_ref.obs.columns:
        raise ValueError(
            f"Labels key '{labels_key}' not found in adata_ref.obs. "
            f"Available columns: {list(adata_ref.obs.columns[:10])}"
        )

    cell_type_counts = adata_ref.obs[labels_key].value_counts()
    n_cell_types = len(cell_type_counts)

    print(f"\n  Cells: {adata_ref.n_obs:,}")
    print(f"  Genes: {adata_ref.n_vars:,}")
    print(f"  Cell types ({labels_key}): {n_cell_types}")
    if batch_key is not None:
        if batch_key not in adata_ref.obs.columns:
            raise ValueError(
                f"Batch key '{batch_key}' not found in adata_ref.obs. "
                f"Available columns: {list(adata_ref.obs.columns[:10])}"
            )
        n_batches = adata_ref.obs[batch_key].nunique()
        print(f"  Batches ({batch_key}): {n_batches}")
    else:
        print(f"  Batches: none (single-batch model)")

    # --- Filter genes ---
    print()
    adata_ref = filter_genes_for_deconvolution(adata_ref)
    print(f"  ✓ Gene filtering complete: {adata_ref.n_vars:,} genes retained")

    # --- Setup AnnData for RegressionModel ---
    print("\n  Setting up AnnData with RegressionModel.setup_anndata()...")
    cell2location.models.RegressionModel.setup_anndata(
        adata_ref,
        batch_key=batch_key,
        labels_key=labels_key,
    )
    print("  ✓ AnnData registered")

    # --- Build model ---
    print("\n  Building RegressionModel...")
    model = cell2location.models.RegressionModel(adata_ref)
    print("  ✓ Model built")
    accelerator = _use_gpu_to_accelerator(use_gpu)
    print(f"\n  Training parameters:")
    print(f"    max_epochs  = {max_epochs}")
    print(f"    batch_size  = 2500")
    print(f"    train_size  = 1  (no validation split)")
    print(f"    accelerator = {accelerator}")
    print(f"\n  Starting training...")

    # --- Train ---
    # cell2location 0.1.x with scvi-tools >=1.1: use accelerator= not use_gpu=
    model.train(
        max_epochs=max_epochs,
        accelerator=accelerator,
        batch_size=2500,
        train_size=1,
    )
    print("  ✓ Training complete")

    # --- Export posterior ---
    print("\n  Exporting posterior (1000 samples, batch_size=2500)...")
    adata_ref = model.export_posterior(
        adata_ref,
        sample_kwargs={
            "num_samples": 1000,
            "batch_size": 2500,
            "accelerator": accelerator,
        },
    )
    print("  ✓ Posterior exported")

    # --- Confirm signatures ---
    ref_signatures = adata_ref.varm["means_per_cluster_mu_fg"]
    n_sig_genes, n_sig_types = ref_signatures.shape
    print(f"\n  Reference signatures stored in adata_ref.varm['means_per_cluster_mu_fg']")
    print(f"    Genes: {n_sig_genes:,}")
    print(f"    Cell types: {n_sig_types}")
    print(f"    Cell type names:")
    for ct in ref_signatures.columns:
        print(f"      - {ct}")

    # --- Save model ---
    if save_model is not None:
        save_path = Path(save_model)
        save_path.mkdir(parents=True, exist_ok=True)
        model.save(str(save_path), overwrite=True)
        print(f"\n  ✓ Model saved to: {save_path}")

    # --- Store metadata ---
    cell2location_version = getattr(cell2location, "__version__", "unknown")
    ref_info = {
        "labels_key": labels_key,
        "batch_key": batch_key,
        "max_epochs": max_epochs,
        "use_gpu": use_gpu,
        "n_cell_types": n_cell_types,
        "cell_types": list(ref_signatures.columns),
        "n_genes_signatures": n_sig_genes,
        "cell2location_version": cell2location_version,
    }
    adata_ref.uns["cell2location_ref_info"] = ref_info
    print("  ✓ Metadata stored in adata_ref.uns['cell2location_ref_info']")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("Reference model training complete!")
    print("=" * 60)
    print(f"  Cell types modelled : {n_sig_types}")
    print(f"  Signature genes     : {n_sig_genes:,}")
    print(f"  Signatures key      : adata_ref.varm['means_per_cluster_mu_fg']")

    print("\nNext steps:")
    print("  # Extract signatures and proceed to spatial deconvolution")
    print("  ref_signatures = adata_ref.varm['means_per_cluster_mu_fg']")
    print("  adata_sp, mod_sp = train_cell2location(")
    print("      adata_sp,")
    print("      reference_signatures=ref_signatures,")
    print("      N_cells_per_location=10,  # Tune to your tissue")
    print("      detection_alpha=20,")
    print("      max_epochs=30000,")
    print("      use_gpu=True,")
    print("  )")
    print()
    print("  WARNING: Spatial model training is slow.")
    print("  30,000 epochs on GPU = 1-4 hours depending on dataset size.")

    return adata_ref, model


def train_cell2location(
    adata_sp: sc.AnnData,
    reference_signatures: pd.DataFrame,
    N_cells_per_location: int = 10,
    detection_alpha: float = 20,
    max_epochs: int = 30000,
    use_gpu: bool = True,
    save_model: Optional[Union[str, Path]] = None,
) -> Tuple[sc.AnnData, "cell2location.models.Cell2location"]:
    """
    Deconvolve spatial spots into cell type abundances using Cell2location.

    Subsets the spatial data to genes present in the reference signatures,
    sets up and trains the Cell2location model, exports posterior quantiles
    (q05, q50, q95) into adata_sp.obsm, and stores training metadata in
    adata_sp.uns.

    WARNING: This function is computationally intensive.  Training 30,000
    epochs on a modern CUDA GPU takes approximately 1-4 hours depending on
    the number of spots and genes.  CPU training is not recommended.

    Parameters
    ----------
    adata_sp : AnnData
        Spatial AnnData object with raw counts in layers['counts'] or X.
        Must have spatial coordinates in obsm['spatial'].
    reference_signatures : pd.DataFrame
        Per-cell-type mean expression signatures, typically retrieved from
        adata_ref.varm['means_per_cluster_mu_fg'] after running
        ``train_reference_model``.  Index = gene names, columns = cell type
        names.
    N_cells_per_location : int, optional
        Expected average number of cells per spatial spot (default: 10).
        This is the most important hyperparameter.  For 10x Visium tissue
        sections:
          - Dense tissue (brain, tumor): 5-15
          - Loose tissue: 2-8
          - Cell-rich tissue: up to 30
        Check the Cell2location paper supplementary for guidance.
    detection_alpha : float, optional
        Controls sensitivity to per-spot detection efficiency variation
        (default: 20).  Higher values assume more uniform detection across
        spots.  The Cell2location default of 20 is appropriate for most
        Visium experiments.
    max_epochs : int, optional
        Maximum training epochs (default: 30,000).  30,000 is the recommended
        minimum for convergence.  Do not reduce below 10,000 without
        convergence diagnostics.
    use_gpu : bool, optional
        Whether to use GPU for training (default: True).
        Cell2location uses ``use_gpu``, not scvi-tools' ``accelerator``.
        CPU training at 30,000 epochs is not feasible for typical datasets.
    save_model : str or Path or None, optional
        Directory path to save the trained model.  The directory is created
        if it does not exist.  (default: None)

    Returns
    -------
    tuple of (AnnData, Cell2location)
        - adata_sp: Input AnnData (subset to signature genes) updated with:
            - adata_sp.obsm['q05_cell_abundance_w_sf']: conservative 5th
              percentile abundances (recommended for downstream use)
            - adata_sp.obsm['q50_cell_abundance_w_sf']: median abundances
            - adata_sp.obsm['q95_cell_abundance_w_sf']: 95th percentile
              abundances (upper credible interval)
            - adata_sp.uns['cell2location_info']: dict of training metadata
        - model: Trained cell2location.models.Cell2location instance

    Raises
    ------
    ValueError
        If no genes in adata_sp overlap with reference_signatures.index.

    Notes
    -----
    The q05 quantile is the recommended output for downstream spatial analysis.
    It provides conservative (lower-bound) cell abundance estimates, reducing
    false positives in cell type mapping.  See Kleshchevnikov et al. (2022)
    for statistical justification.

    Examples
    --------
    >>> adata_sp, mod_sp = train_cell2location(
    ...     adata_sp,
    ...     reference_signatures=adata_ref.varm['means_per_cluster_mu_fg'],
    ...     N_cells_per_location=10,
    ...     detection_alpha=20,
    ...     max_epochs=30000,
    ...     use_gpu=True,
    ...     save_model='results/c2l_spatial_model',
    ... )
    >>> props = get_cell_type_proportions(adata_sp, quantile='q05')
    """
    print("=" * 60)
    print("Cell2location: Spatial Deconvolution Model (Stage 2 / 2)")
    print("=" * 60)
    print()
    print("  NOTE: Training is slow. 30,000 epochs on GPU = 1-4 hours.")
    print("  CPU training at this scale is not recommended.")

    # --- Gene subsetting ---
    sig_genes = reference_signatures.index
    shared_genes = adata_sp.var_names[adata_sp.var_names.isin(sig_genes)]
    n_shared = len(shared_genes)

    if n_shared == 0:
        raise ValueError(
            "No genes in adata_sp.var_names overlap with reference_signatures.index. "
            "Ensure both datasets use the same gene ID namespace "
            "(e.g., gene symbols vs Ensembl IDs)."
        )

    if n_shared < 500:
        warnings.warn(
            f"Only {n_shared} genes shared between spatial data and reference signatures. "
            "Deconvolution accuracy may be reduced. "
            "Consider using a reference with broader gene coverage.",
            UserWarning,
            stacklevel=2,
        )

    print(f"\n  Spatial spots: {adata_sp.n_obs:,}")
    print(f"  Spatial genes (original): {adata_sp.n_vars:,}")
    print(f"  Reference signature genes: {len(sig_genes):,}")
    print(f"  Shared genes after subsetting: {n_shared:,}")

    adata_sp = adata_sp[:, shared_genes].copy()
    print(f"  ✓ Spatial data subset to {n_shared:,} signature genes")

    # --- Setup AnnData ---
    print("\n  Setting up AnnData with Cell2location.setup_anndata()...")
    cell2location.models.Cell2location.setup_anndata(adata_sp, batch_key=None)
    print("  ✓ AnnData registered")

    # --- Build model ---
    print(f"\n  Building Cell2location model:")
    print(f"    N_cells_per_location = {N_cells_per_location}")
    print(f"    detection_alpha      = {detection_alpha}")
    print(f"    Cell types           : {reference_signatures.shape[1]}")

    model = cell2location.models.Cell2location(
        adata_sp,
        cell_state_df=reference_signatures,
        N_cells_per_location=N_cells_per_location,
        detection_alpha=detection_alpha,
    )
    print("  ✓ Model built")

    # --- Train ---
    accelerator = _use_gpu_to_accelerator(use_gpu)
    print(f"\n  Training parameters:")
    print(f"    max_epochs  = {max_epochs}")
    print(f"    batch_size  = None  (full dataset per batch)")
    print(f"    train_size  = 1  (no validation split)")
    print(f"    accelerator = {accelerator}")
    print(f"\n  Starting training (this will take a while)...")

    # cell2location 0.1.x with scvi-tools >=1.1: use accelerator= not use_gpu=
    model.train(
        max_epochs=max_epochs,
        accelerator=accelerator,
        batch_size=None,
        train_size=1,
    )
    print("  ✓ Training complete")

    # --- Export posterior ---
    print("\n  Exporting posterior (1000 samples)...")
    adata_sp = model.export_posterior(
        adata_sp,
        sample_kwargs={
            "num_samples": 1000,
            "batch_size": 1000,
            "accelerator": accelerator,
        },
    )
    print("  ✓ Posterior exported")

    # --- Confirm obsm keys ---
    quantile_keys = [
        "q05_cell_abundance_w_sf",
        "q50_cell_abundance_w_sf",
        "q95_cell_abundance_w_sf",
    ]
    stored_keys = []
    for key in quantile_keys:
        if key in adata_sp.obsm:
            stored_keys.append(key)
            print(f"  ✓ Stored adata_sp.obsm['{key}'] — shape: {adata_sp.obsm[key].shape}")
        else:
            warnings.warn(
                f"Expected key '{key}' not found in adata_sp.obsm after export_posterior. "
                "The cell2location API may have changed. "
                "Inspect adata_sp.obsm.keys() for available abundance keys.",
                UserWarning,
                stacklevel=2,
            )

    # --- Save model ---
    if save_model is not None:
        save_path = Path(save_model)
        save_path.mkdir(parents=True, exist_ok=True)
        model.save(str(save_path), overwrite=True)
        print(f"\n  ✓ Model saved to: {save_path}")

    # --- Store metadata ---
    cell2location_version = getattr(cell2location, "__version__", "unknown")
    c2l_info = {
        "N_cells_per_location": N_cells_per_location,
        "detection_alpha": detection_alpha,
        "max_epochs": max_epochs,
        "use_gpu": use_gpu,
        "n_spots": adata_sp.n_obs,
        "n_genes_used": n_shared,
        "n_cell_types": reference_signatures.shape[1],
        "cell_types": list(reference_signatures.columns),
        "obsm_abundance_keys": stored_keys,
        "recommended_quantile": "q05_cell_abundance_w_sf",
        "cell2location_version": cell2location_version,
    }
    adata_sp.uns["cell2location_info"] = c2l_info
    print("  ✓ Metadata stored in adata_sp.uns['cell2location_info']")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("Cell2location spatial model training complete!")
    print("=" * 60)
    print(f"  Spots deconvolved : {adata_sp.n_obs:,}")
    print(f"  Cell types mapped : {reference_signatures.shape[1]}")
    print(f"  Genes used        : {n_shared:,}")
    print(f"  Posterior quantiles stored in adata_sp.obsm:")
    for key in stored_keys:
        print(f"    - '{key}'")
    print(f"  Recommended key   : 'q05_cell_abundance_w_sf' (conservative)")

    print("\nNext steps:")
    print("  # Convert abundances to proportions")
    print("  props = get_cell_type_proportions(adata_sp, quantile='q05')")
    print()
    print("  # Plot spatial distribution of a cell type")
    print("  import scanpy as sc")
    print("  sc.pl.spatial(adata_sp, color='prop_<CellType>', cmap='Reds')")
    print()
    print("  # Save the deconvolved AnnData")
    print("  adata_sp.write_h5ad('results/adata_spatial_deconvolved.h5ad')")

    return adata_sp, model


def get_cell_type_proportions(
    adata_sp: sc.AnnData,
    quantile: str = "q05",
) -> pd.DataFrame:
    """
    Convert Cell2location abundance estimates to normalized cell type proportions.

    Retrieves absolute cell type abundance estimates from the specified posterior
    quantile, row-normalizes each spot to sum to 1, adds per-type proportion
    columns to adata_sp.obs, assigns a dominant cell type label to each spot,
    and stores the full proportions matrix in adata_sp.obsm['cell_type_proportions'].

    Parameters
    ----------
    adata_sp : AnnData
        Spatial AnnData object after running ``train_cell2location``.  Must
        contain adata_sp.obsm[f'{quantile}_cell_abundance_w_sf'].
    quantile : str, optional
        Posterior quantile to use.  One of:
          - 'q05': 5th percentile — conservative, recommended for mapping
          - 'q50': median — central estimate, good for visualization
          - 'q95': 95th percentile — upper credible interval
        (default: 'q05')

    Returns
    -------
    pd.DataFrame
        DataFrame of shape (n_spots, n_cell_types) with row-normalized
        proportions summing to 1 per spot.  Index = spot barcodes,
        columns = cell type names.

    Raises
    ------
    KeyError
        If the expected obsm key for the chosen quantile is not found.

    Notes
    -----
    Proportion columns added to adata_sp.obs use the prefix 'prop_' followed
    by the cell type name with spaces replaced by underscores.  The dominant
    cell type column is 'dominant_cell_type'.

    Examples
    --------
    >>> props = get_cell_type_proportions(adata_sp, quantile='q05')
    >>> # Spatial plot of T cell proportions
    >>> import scanpy as sc
    >>> sc.pl.spatial(adata_sp, color='prop_T_cells', cmap='Reds', vmin=0, vmax=1)
    >>> # Dominant cell type map
    >>> sc.pl.spatial(adata_sp, color='dominant_cell_type')
    """
    print("=" * 60)
    print("Cell2location: Cell Type Proportions")
    print("=" * 60)

    obsm_key = f"{quantile}_cell_abundance_w_sf"

    if obsm_key not in adata_sp.obsm:
        available = [k for k in adata_sp.obsm.keys() if "abundance" in k]
        raise KeyError(
            f"Key '{obsm_key}' not found in adata_sp.obsm. "
            f"Run train_cell2location first. "
            f"Available abundance keys: {available}"
        )

    print(f"\n  Quantile: {quantile} ({obsm_key})")

    # --- Retrieve abundances ---
    abundance_array = adata_sp.obsm[obsm_key]

    # May be a DataFrame or ndarray depending on cell2location version
    if isinstance(abundance_array, pd.DataFrame):
        cell_types = list(abundance_array.columns)
        abundance_values = abundance_array.values
    else:
        abundance_values = np.asarray(abundance_array)
        # Retrieve cell type names from metadata if available
        c2l_info = adata_sp.uns.get("cell2location_info", {})
        cell_types = c2l_info.get("cell_types", None)
        if cell_types is None or len(cell_types) != abundance_values.shape[1]:
            cell_types = [f"cell_type_{i}" for i in range(abundance_values.shape[1])]
            warnings.warn(
                "Cell type names not found in adata_sp.uns['cell2location_info']. "
                "Using generic names 'cell_type_0', 'cell_type_1', etc. "
                "Re-run train_cell2location to store proper names.",
                UserWarning,
                stacklevel=2,
            )

    n_spots, n_types = abundance_values.shape
    print(f"  Spots: {n_spots:,}")
    print(f"  Cell types: {n_types}")

    # --- Row-normalize to proportions ---
    row_sums = abundance_values.sum(axis=1, keepdims=True)
    # Guard against all-zero spots (should not occur, but be defensive)
    row_sums_safe = np.where(row_sums == 0, 1.0, row_sums)
    proportions = abundance_values / row_sums_safe

    n_zero_spots = int((row_sums.ravel() == 0).sum())
    if n_zero_spots > 0:
        warnings.warn(
            f"{n_zero_spots} spots have zero total abundance. "
            "Their proportions are set to uniform (1/n_types). "
            "Consider checking these spots for quality issues.",
            UserWarning,
            stacklevel=2,
        )

    # --- Build proportions DataFrame ---
    proportions_df = pd.DataFrame(
        proportions,
        index=adata_sp.obs_names,
        columns=cell_types,
    )

    # --- Add per-type columns to obs ---
    for ct in cell_types:
        col_name = "prop_" + ct.replace(" ", "_")
        adata_sp.obs[col_name] = proportions_df[ct].values

    # --- Add dominant cell type ---
    dominant_idx = proportions.argmax(axis=1)
    adata_sp.obs["dominant_cell_type"] = [cell_types[i] for i in dominant_idx]
    print(f"  ✓ Added 'dominant_cell_type' to adata_sp.obs")

    # --- Store proportions matrix in obsm ---
    adata_sp.obsm["cell_type_proportions"] = proportions_df.values
    print(f"  ✓ Stored proportions in adata_sp.obsm['cell_type_proportions']"
          f" — shape: {proportions_df.shape}")

    # --- Print proportion summary ---
    print(f"\n  Mean proportion per cell type:")
    mean_props = proportions_df.mean(axis=0).sort_values(ascending=False)
    for ct, mean_prop in mean_props.items():
        col_name = "prop_" + ct.replace(" ", "_")
        print(f"    {ct:<35} {mean_prop:.3f}  (obs col: '{col_name}')")

    # --- Dominant type distribution ---
    dominant_counts = adata_sp.obs["dominant_cell_type"].value_counts()
    print(f"\n  Dominant cell type per spot:")
    for ct, cnt in dominant_counts.items():
        pct = cnt / n_spots * 100
        print(f"    {ct:<35} {cnt:>6,} spots  ({pct:.1f}%)")

    print("\nNext steps:")
    print("  # Spatial plot of individual cell type proportion")
    print("  import scanpy as sc")
    print("  sc.pl.spatial(adata_sp, color='prop_<CellType>', cmap='Reds',")
    print("      vmin=0, vmax=1, title='<CellType> proportion')")
    print()
    print("  # Plot dominant cell type map")
    print("  sc.pl.spatial(adata_sp, color='dominant_cell_type')")
    print()
    print("  # Save proportions table")
    print("  proportions_df.to_csv('results/cell_type_proportions.csv')")
    print()
    print("  # Save deconvolved AnnData")
    print("  adata_sp.write_h5ad('results/adata_spatial_deconvolved.h5ad')")

    return proportions_df


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("run_cell2location.py — Example Usage")
    print("=" * 60)
    print()
    print("Full Cell2location workflow (reference + spatial deconvolution):")
    print()
    print("  import scanpy as sc")
    print("  from run_cell2location import (")
    print("      train_reference_model,")
    print("      train_cell2location,")
    print("      get_cell_type_proportions,")
    print("  )")
    print("  from setup_spatial import (")
    print("      validate_spatial_anndata,")
    print("      validate_reference_anndata,")
    print("      subset_to_shared_genes,")
    print("  )")
    print()
    print("  # Load data")
    print("  adata_ref = sc.read_h5ad('data/reference_scrna.h5ad')")
    print("  adata_sp  = sc.read_h5ad('data/spatial_visium.h5ad')")
    print()
    print("  # Validate inputs")
    print("  validate_reference_anndata(adata_ref, labels_key='cell_type')")
    print("  validate_spatial_anndata(adata_sp)")
    print()
    print("  # Subset to shared genes before training")
    print("  adata_sp, adata_ref = subset_to_shared_genes(adata_sp, adata_ref)")
    print()
    print("  # Stage 1 — Train reference signature model (~minutes on GPU)")
    print("  adata_ref, mod_ref = train_reference_model(")
    print("      adata_ref,")
    print("      labels_key='cell_type',")
    print("      batch_key='donor',       # or None for single-batch data")
    print("      max_epochs=250,")
    print("      use_gpu=True,")
    print("      save_model='results/c2l_ref_model',")
    print("  )")
    print()
    print("  # Extract reference signatures")
    print("  ref_signatures = adata_ref.varm['means_per_cluster_mu_fg']")
    print()
    print("  # Stage 2 — Spatial deconvolution (~1-4 hours on GPU)")
    print("  # N_cells_per_location: tune to your tissue type")
    print("  #   Dense tissue (brain, tumor): 5-15")
    print("  #   Loose tissue: 2-8")
    print("  #   Cell-rich tissue: up to 30")
    print("  adata_sp, mod_sp = train_cell2location(")
    print("      adata_sp,")
    print("      reference_signatures=ref_signatures,")
    print("      N_cells_per_location=10,")
    print("      detection_alpha=20,")
    print("      max_epochs=30000,")
    print("      use_gpu=True,")
    print("      save_model='results/c2l_spatial_model',")
    print("  )")
    print()
    print("  # Convert abundances to proportions (use q05 = conservative)")
    print("  props = get_cell_type_proportions(adata_sp, quantile='q05')")
    print()
    print("  # Visualize")
    print("  sc.pl.spatial(adata_sp, color='dominant_cell_type')")
    print("  sc.pl.spatial(adata_sp, color='prop_T_cells', cmap='Reds')")
    print()
    print("  # Save outputs")
    print("  props.to_csv('results/cell_type_proportions.csv')")
    print("  adata_sp.write_h5ad('results/adata_spatial_deconvolved.h5ad')")
