"""
Shared Utilities for Spatial Deconvolution with scvi-tools

This module provides common setup, validation, and diagnostic utilities
for spatial transcriptomics deconvolution workflows (Cell2location, DestVI, etc.).

For methodology and best practices, see references/spatial_deconvolution_guide.md

Functions:
  - validate_spatial_anndata(): Validate spatial AnnData (counts + coordinates)
  - validate_reference_anndata(): Validate scRNA-seq reference AnnData for deconvolution
  - compute_gene_overlap(): Compute gene overlap between spatial and reference data
  - subset_to_shared_genes(): Subset both datasets to shared genes
  - detect_accelerator(): Detect best available hardware accelerator
  - filter_genes_for_deconvolution(): Permissive gene filtering for Cell2location reference

Requirements:
  - scvi-tools >= 1.1: pip install scvi-tools
  - torch: pip install torch
  - scanpy: pip install scanpy
  - GPU recommended for training (10-20x faster)
"""

import numpy as np
import warnings
from typing import List, Optional, Tuple

try:
    import scanpy as sc
except ImportError:
    raise ImportError(
        "scanpy is required for this module.\n"
        "Install with: pip install scanpy"
    )

from anndata import AnnData
from scipy import sparse


def validate_spatial_anndata(
    adata_sp: AnnData,
    require_counts: bool = True,
    require_spatial: bool = True,
) -> bool:
    """
    Validate that an AnnData object meets spatial deconvolution requirements.

    Checks for raw integer counts and spatial coordinates. Prints a diagnostic
    summary of the spatial data.

    Parameters
    ----------
    adata_sp : AnnData
        Spatial AnnData object to validate.
    require_counts : bool, optional
        Require raw integer counts (default: True).
    require_spatial : bool, optional
        Require spatial coordinates in obsm['spatial'] (default: True).

    Returns
    -------
    bool
        True if validation passes.

    Raises
    ------
    ValueError
        If any validation check fails, with a clear diagnostic message.

    Examples
    --------
    >>> validate_spatial_anndata(adata_sp)
    >>> validate_spatial_anndata(adata_sp, require_counts=False)
    """
    print("=" * 60)
    print("Validating Spatial AnnData")
    print("=" * 60)

    errors: List[str] = []

    # --- Locate count data ---
    count_layer: Optional[str] = None
    if "counts" in adata_sp.layers:
        count_data = adata_sp.layers["counts"]
        count_layer = "layers['counts']"
    else:
        count_data = adata_sp.X
        count_layer = "X"

    print(f"\n  Spots: {adata_sp.n_obs:,}")
    print(f"  Genes: {adata_sp.n_vars:,}")
    print(f"  Count data location: adata.{count_layer}")

    # --- Check counts are valid ---
    if require_counts:
        if sparse.issparse(count_data):
            data_values = count_data.data
        else:
            data_values = np.asarray(count_data).ravel()

        # Check for NaN
        if np.any(np.isnan(data_values)):
            errors.append(
                f"NaN values found in adata.{count_layer}. "
                "Raw counts must not contain NaN."
            )

        # Check for negative values
        if np.any(data_values < 0):
            errors.append(
                f"Negative values found in adata.{count_layer}. "
                "Raw counts must be non-negative."
            )

        # Check integer-like (tolerance for float storage of integers)
        if data_values.size > 0:
            sample_size = min(100_000, data_values.size)
            rng = np.random.default_rng(42)
            sample_idx = rng.choice(data_values.size, size=sample_size, replace=False)
            sample_vals = data_values[sample_idx]
            non_integer = np.any(np.abs(sample_vals - np.round(sample_vals)) > 1e-6)
            if non_integer:
                errors.append(
                    f"Non-integer values found in adata.{count_layer}. "
                    "Spatial deconvolution requires raw integer counts. "
                    "Data may have been normalized or log-transformed."
                )

        if not errors:
            print(f"  Counts valid: no NaN, no negatives, integer-like")

    # --- Check spatial coordinates ---
    if require_spatial:
        if "spatial" not in adata_sp.obsm:
            errors.append(
                "No 'spatial' key in adata.obsm. "
                "Spatial coordinates must be stored in obsm['spatial'] "
                "as a 2D array of shape (n_spots, 2)."
            )
        else:
            spatial_coords = adata_sp.obsm["spatial"]
            coords_shape = spatial_coords.shape

            if len(coords_shape) != 2 or coords_shape[1] != 2:
                errors.append(
                    f"Spatial coordinates have shape {coords_shape}, "
                    f"expected (n_spots, 2). "
                    "Each spot must have exactly 2 coordinates (x, y)."
                )
            elif coords_shape[0] != adata_sp.n_obs:
                errors.append(
                    f"Spatial coordinates have {coords_shape[0]} rows, "
                    f"but AnnData has {adata_sp.n_obs} spots. Shapes must match."
                )
            else:
                spatial_arr = np.asarray(spatial_coords)
                if np.any(np.isnan(spatial_arr)):
                    errors.append(
                        "NaN values found in spatial coordinates. "
                        "All spots must have valid (x, y) positions."
                    )
                else:
                    print(f"  Spatial coords shape: {coords_shape}")
                    x_range = (float(spatial_arr[:, 0].min()), float(spatial_arr[:, 0].max()))
                    y_range = (float(spatial_arr[:, 1].min()), float(spatial_arr[:, 1].max()))
                    print(f"  X range: [{x_range[0]:.1f}, {x_range[1]:.1f}]")
                    print(f"  Y range: [{y_range[0]:.1f}, {y_range[1]:.1f}]")

    # --- Report result ---
    if errors:
        error_msg = "\n".join(f"  - {e}" for e in errors)
        print(f"\n  VALIDATION FAILED:")
        print(error_msg)
        raise ValueError(
            f"Spatial AnnData validation failed with {len(errors)} error(s):\n{error_msg}"
        )

    print(f"\n  Validation passed")
    return True


def validate_reference_anndata(
    adata_ref: AnnData,
    labels_key: str,
    require_counts: bool = True,
    min_cells_per_type: int = 10,
) -> bool:
    """
    Validate that a reference scRNA-seq AnnData is suitable for deconvolution.

    Checks for raw integer counts, cell type labels, and sufficient cells
    per cell type. Prints a diagnostic summary.

    Parameters
    ----------
    adata_ref : AnnData
        Reference scRNA-seq AnnData object.
    labels_key : str
        Column in adata_ref.obs containing cell type labels.
    require_counts : bool, optional
        Require raw integer counts (default: True).
    min_cells_per_type : int, optional
        Minimum cells per cell type before warning (default: 10).

    Returns
    -------
    bool
        True if validation passes.

    Raises
    ------
    ValueError
        If any validation check fails, with a clear diagnostic message.

    Examples
    --------
    >>> validate_reference_anndata(adata_ref, labels_key='cell_type')
    >>> validate_reference_anndata(adata_ref, labels_key='annotation', min_cells_per_type=20)
    """
    print("=" * 60)
    print("Validating Reference AnnData")
    print("=" * 60)

    errors: List[str] = []

    # --- Locate count data ---
    count_layer: Optional[str] = None
    if "counts" in adata_ref.layers:
        count_data = adata_ref.layers["counts"]
        count_layer = "layers['counts']"
    else:
        count_data = adata_ref.X
        count_layer = "X"

    print(f"\n  Cells: {adata_ref.n_obs:,}")
    print(f"  Genes: {adata_ref.n_vars:,}")
    print(f"  Count data location: adata.{count_layer}")

    # --- Check counts are valid ---
    if require_counts:
        if sparse.issparse(count_data):
            data_values = count_data.data
        else:
            data_values = np.asarray(count_data).ravel()

        # Check for NaN
        if np.any(np.isnan(data_values)):
            errors.append(
                f"NaN values found in adata.{count_layer}. "
                "Raw counts must not contain NaN."
            )

        # Check for negative values
        if np.any(data_values < 0):
            errors.append(
                f"Negative values found in adata.{count_layer}. "
                "Raw counts must be non-negative."
            )

        # Check integer-like
        if data_values.size > 0:
            sample_size = min(100_000, data_values.size)
            rng = np.random.default_rng(42)
            sample_idx = rng.choice(data_values.size, size=sample_size, replace=False)
            sample_vals = data_values[sample_idx]
            non_integer = np.any(np.abs(sample_vals - np.round(sample_vals)) > 1e-6)
            if non_integer:
                errors.append(
                    f"Non-integer values found in adata.{count_layer}. "
                    "Reference data must contain raw integer counts."
                )

        if not errors:
            print(f"  Counts valid: no NaN, no negatives, integer-like")

    # --- Check labels key ---
    if labels_key not in adata_ref.obs.columns:
        errors.append(
            f"Labels key '{labels_key}' not found in adata.obs. "
            f"Available columns: {list(adata_ref.obs.columns[:10])}"
        )
    else:
        cell_type_counts = adata_ref.obs[labels_key].value_counts()
        n_types = len(cell_type_counts)
        print(f"  Labels key: '{labels_key}' ({n_types} cell types)")
        print(f"  Cells per type: min={cell_type_counts.min():,}, "
              f"max={cell_type_counts.max():,}, "
              f"median={int(cell_type_counts.median()):,}")

        # Check for NaN labels
        n_nan = int(adata_ref.obs[labels_key].isna().sum())
        if n_nan > 0:
            errors.append(
                f"{n_nan:,} cells have NaN/missing labels in '{labels_key}'. "
                "All cells must have assigned cell type labels."
            )

        # Warn about rare cell types
        rare_types = cell_type_counts[cell_type_counts < min_cells_per_type]
        if len(rare_types) > 0:
            warnings.warn(
                f"{len(rare_types)} cell type(s) have fewer than {min_cells_per_type} cells: "
                f"{list(rare_types.index)}. "
                f"Deconvolution estimates for rare types may be unreliable."
            )
            print(f"  WARNING: {len(rare_types)} cell type(s) below "
                  f"{min_cells_per_type} cells threshold")

        # Print cell type summary
        print(f"\n  Cell type summary:")
        for ct, count in cell_type_counts.items():
            marker = " (LOW)" if count < min_cells_per_type else ""
            print(f"    {ct}: {count:,}{marker}")

    # --- Report result ---
    if errors:
        error_msg = "\n".join(f"  - {e}" for e in errors)
        print(f"\n  VALIDATION FAILED:")
        print(error_msg)
        raise ValueError(
            f"Reference AnnData validation failed with {len(errors)} error(s):\n{error_msg}"
        )

    print(f"\n  Validation passed")
    return True


def compute_gene_overlap(
    adata_sp: AnnData,
    adata_ref: AnnData,
    min_overlap: int = 500,
) -> List[str]:
    """
    Compute the gene overlap between spatial and reference datasets.

    Finds the intersection of var_names and prints overlap statistics.
    Warns if overlap is below 500 genes and raises if below 100.

    Parameters
    ----------
    adata_sp : AnnData
        Spatial AnnData object.
    adata_ref : AnnData
        Reference scRNA-seq AnnData object.
    min_overlap : int, optional
        Minimum acceptable gene overlap before warning (default: 500).

    Returns
    -------
    list of str
        Sorted list of shared gene names.

    Raises
    ------
    ValueError
        If fewer than 100 shared genes are found.

    Examples
    --------
    >>> shared_genes = compute_gene_overlap(adata_sp, adata_ref)
    >>> shared_genes = compute_gene_overlap(adata_sp, adata_ref, min_overlap=1000)
    """
    print("=" * 60)
    print("Computing Gene Overlap")
    print("=" * 60)

    spatial_genes = set(adata_sp.var_names)
    ref_genes = set(adata_ref.var_names)
    shared_genes = sorted(spatial_genes & ref_genes)

    n_spatial = len(spatial_genes)
    n_ref = len(ref_genes)
    n_shared = len(shared_genes)

    # Overlap percentage relative to the smaller dataset
    smaller = min(n_spatial, n_ref)
    overlap_pct = (n_shared / smaller * 100) if smaller > 0 else 0.0

    print(f"\n  Spatial genes: {n_spatial:,}")
    print(f"  Reference genes: {n_ref:,}")
    print(f"  Shared genes: {n_shared:,}")
    print(f"  Overlap: {overlap_pct:.1f}% (of smaller dataset)")

    # Hard failure threshold
    if n_shared < 100:
        msg = (
            f"Only {n_shared} shared genes found between spatial and reference data. "
            f"Minimum 100 required for deconvolution. "
            f"Check that gene IDs use the same namespace "
            f"(e.g., gene symbols vs Ensembl IDs)."
        )
        print(f"\n  GENE OVERLAP FAILED: {msg}")
        raise ValueError(msg)

    # Warning threshold
    if n_shared < min_overlap:
        warnings.warn(
            f"Only {n_shared} shared genes (below {min_overlap} threshold). "
            f"Deconvolution accuracy may be reduced. "
            f"Consider using a reference with broader gene coverage."
        )
        print(f"  WARNING: Below {min_overlap} gene overlap threshold")

    print(f"\n  Gene overlap computed")
    return shared_genes


def subset_to_shared_genes(
    adata_sp: AnnData,
    adata_ref: AnnData,
) -> Tuple[AnnData, AnnData]:
    """
    Subset both spatial and reference AnnData to their shared genes.

    Computes gene overlap and returns copies of both datasets restricted
    to the intersection of their var_names.

    Parameters
    ----------
    adata_sp : AnnData
        Spatial AnnData object.
    adata_ref : AnnData
        Reference scRNA-seq AnnData object.

    Returns
    -------
    tuple of (AnnData, AnnData)
        (adata_sp_subset, adata_ref_subset) restricted to shared genes.

    Examples
    --------
    >>> adata_sp_sub, adata_ref_sub = subset_to_shared_genes(adata_sp, adata_ref)
    """
    print("=" * 60)
    print("Subsetting to Shared Genes")
    print("=" * 60)

    shared_genes = compute_gene_overlap(adata_sp, adata_ref)

    adata_sp_subset = adata_sp[:, shared_genes].copy()
    adata_ref_subset = adata_ref[:, shared_genes].copy()

    print(f"\n  Spatial subset: {adata_sp_subset.n_obs:,} spots x {adata_sp_subset.n_vars:,} genes")
    print(f"  Reference subset: {adata_ref_subset.n_obs:,} cells x {adata_ref_subset.n_vars:,} genes")
    print(f"\n  Subsetting complete")

    return adata_sp_subset, adata_ref_subset


def detect_accelerator() -> str:
    """
    Detect the best available hardware accelerator for scvi-tools training.

    Checks for CUDA GPU, Apple MPS, then falls back to CPU.
    Prints device information including name and memory when available.

    Returns
    -------
    str
        Accelerator string for scvi-tools: "gpu", "mps", or "cpu".

    Examples
    --------
    >>> accelerator = detect_accelerator()
    >>> model.train(accelerator=accelerator)
    """
    print("=" * 60)
    print("Detecting Hardware Accelerator")
    print("=" * 60)

    try:
        import torch
    except ImportError:
        print("\n  PyTorch not installed. Using CPU.")
        print(f"  Accelerator: cpu")
        return "cpu"

    # Check CUDA GPU
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        device_memory = torch.cuda.get_device_properties(0).total_mem / (1024 ** 3)
        n_gpus = torch.cuda.device_count()
        print(f"\n  CUDA GPU detected")
        print(f"  Device: {device_name}")
        print(f"  Memory: {device_memory:.1f} GB")
        print(f"  GPU count: {n_gpus}")
        print(f"  Accelerator: gpu")
        return "gpu"

    # Check Apple MPS
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        print(f"\n  Apple MPS (Metal) detected")
        print(f"  Device: Apple Silicon GPU")
        print(f"  Note: MPS support in scvi-tools may be experimental")
        print(f"  Accelerator: mps")
        return "mps"

    # Fallback to CPU
    print(f"\n  No GPU detected. Using CPU.")
    print(f"  Tip: GPU training is 10-20x faster for scvi-tools models")
    print(f"  Accelerator: cpu")
    return "cpu"


def filter_genes_for_deconvolution(
    adata_ref: AnnData,
    cell_count_cutoff: int = 5,
    cell_pct_cutoff: float = 0.03,
    nonz_mean_cutoff: float = 1.12,
) -> AnnData:
    """
    Apply permissive gene filtering for Cell2location reference preparation.

    Filters genes based on detection across cells and expression magnitude.
    A gene is retained if it is detected in at least ``cell_count_cutoff``
    cells, in at least ``cell_pct_cutoff`` fraction of cells in any cell
    type (when labels are available), and has a nonzero mean expression
    above ``nonz_mean_cutoff``.

    Parameters
    ----------
    adata_ref : AnnData
        Reference scRNA-seq AnnData with raw counts in layers['counts'] or X.
    cell_count_cutoff : int, optional
        Minimum number of cells a gene must be detected in (default: 5).
    cell_pct_cutoff : float, optional
        Minimum fraction of cells within any cell type that must express
        the gene (default: 0.03).
    nonz_mean_cutoff : float, optional
        Minimum mean expression among cells where the gene is detected,
        i.e., nonzero mean (default: 1.12).

    Returns
    -------
    AnnData
        Filtered copy of adata_ref with only retained genes.

    Examples
    --------
    >>> adata_filtered = filter_genes_for_deconvolution(adata_ref)
    >>> adata_filtered = filter_genes_for_deconvolution(
    ...     adata_ref, cell_count_cutoff=10, nonz_mean_cutoff=1.5
    ... )
    """
    print("=" * 60)
    print("Filtering Genes for Deconvolution")
    print("=" * 60)

    n_genes_before = adata_ref.n_vars

    # --- Locate count data ---
    if "counts" in adata_ref.layers:
        count_data = adata_ref.layers["counts"]
        count_loc = "layers['counts']"
    else:
        count_data = adata_ref.X
        count_loc = "X"

    print(f"\n  Count data location: adata.{count_loc}")
    print(f"  Genes before filtering: {n_genes_before:,}")
    print(f"  Cells: {adata_ref.n_obs:,}")

    # --- Convert to sparse CSC for efficient column operations ---
    if sparse.issparse(count_data):
        count_csc = count_data.tocsc()
    else:
        count_csc = sparse.csc_matrix(count_data)

    # --- Filter 1: genes detected in at least cell_count_cutoff cells ---
    cells_per_gene = np.diff(count_csc.indptr)  # nonzero entries per column
    mask_cell_count = cells_per_gene >= cell_count_cutoff
    print(f"\n  Filter 1: detected in >= {cell_count_cutoff} cells")
    print(f"    Genes passing: {mask_cell_count.sum():,}")

    # --- Filter 2: nonzero mean expression > nonz_mean_cutoff ---
    gene_sums = np.asarray(count_csc.sum(axis=0)).ravel()
    # Avoid division by zero
    nonzero_counts = cells_per_gene.copy().astype(np.float64)
    nonzero_counts[nonzero_counts == 0] = 1.0
    nonzero_means = gene_sums / nonzero_counts
    mask_nonz_mean = nonzero_means > nonz_mean_cutoff
    print(f"  Filter 2: nonzero mean > {nonz_mean_cutoff}")
    print(f"    Genes passing: {mask_nonz_mean.sum():,}")

    # --- Filter 3: detected in >= cell_pct_cutoff fraction of cells ---
    cell_pct = cells_per_gene / adata_ref.n_obs
    mask_cell_pct = cell_pct >= cell_pct_cutoff
    print(f"  Filter 3: detected in >= {cell_pct_cutoff:.1%} of cells")
    print(f"    Genes passing: {mask_cell_pct.sum():,}")

    # --- Combine filters ---
    mask_keep = mask_cell_count & mask_nonz_mean & mask_cell_pct
    n_genes_after = int(mask_keep.sum())
    n_removed = n_genes_before - n_genes_after

    adata_filtered = adata_ref[:, mask_keep].copy()

    print(f"\n  Genes before: {n_genes_before:,}")
    print(f"  Genes after: {n_genes_after:,}")
    print(f"  Genes removed: {n_removed:,}")
    print(f"\n  Gene filtering complete")

    return adata_filtered


# Example usage
if __name__ == "__main__":
    print("Spatial Deconvolution Shared Utilities")
    print("=" * 60)
    print()
    print("Example workflow:")
    print()
    print("  from setup_spatial import (")
    print("      validate_spatial_anndata,")
    print("      validate_reference_anndata,")
    print("      compute_gene_overlap,")
    print("      subset_to_shared_genes,")
    print("      detect_accelerator,")
    print("      filter_genes_for_deconvolution,")
    print("  )")
    print()
    print("  # 1. Validate spatial data")
    print("  validate_spatial_anndata(adata_sp)")
    print()
    print("  # 2. Validate reference data")
    print("  validate_reference_anndata(adata_ref, labels_key='cell_type')")
    print()
    print("  # 3. Filter genes for deconvolution")
    print("  adata_ref_filt = filter_genes_for_deconvolution(adata_ref)")
    print()
    print("  # 4. Subset to shared genes")
    print("  adata_sp_sub, adata_ref_sub = subset_to_shared_genes(adata_sp, adata_ref_filt)")
    print()
    print("  # 5. Detect hardware")
    print("  accelerator = detect_accelerator()")
    print()
    print("  # 6. Proceed with Cell2location or DestVI model setup")
    print("  # See model-specific scripts for next steps")
