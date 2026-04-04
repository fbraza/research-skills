"""
Tangram: Single-Cell to Spatial Mapping via Optimal Transport

This module implements the Tangram workflow for mapping single-cell RNA-seq
data to spatial transcriptomics coordinates. Tangram uses optimal transport
to learn a probabilistic mapping between cells and spatial spots, enabling
cell type annotation transfer and gene imputation at spatial resolution.

Tangram is a SEPARATE package from scvi-tools.
Install with: pip install tangram-sc

Unlike scvi-tools probabilistic models (Cell2location, DestVI), Tangram is
an optimal-transport-based method. It is NOT a VAE. It does not provide
uncertainty estimates. Results may vary between runs due to random
initialization of the optimizer.

Two mapping modes are available:
  - mode="clusters": Faster. Maps cell type proportions per spot using
    cluster centroids. Recommended for most use cases.
  - mode="cells":    Slower. Maps individual cells to spots at single-cell
    resolution. Use when spatial resolution matches single-cell scale (e.g.,
    MERFISH, seqFISH+).

Functions:
  - prepare_tangram_inputs(): Find marker genes and preprocess both AnnData
    objects for Tangram mapping.
  - map_cells_to_space(): Run optimal-transport mapping. Returns a mapping
    AnnData (cells x spots).
  - project_annotations(): Transfer cell type labels to spatial spots.
  - impute_genes(): Impute gene expression at spatial locations.

Requirements:
  - tangram-sc >= 1.0: pip install tangram-sc
  - scanpy: pip install scanpy
  - anndata: pip install anndata
  - GPU optional but recommended for large datasets (device="cuda:0")
"""

import warnings
from typing import List, Optional, Tuple

import numpy as np
import scanpy as sc
from anndata import AnnData

try:
    import tangram as tg
except ImportError:
    raise ImportError(
        "tangram-sc is required.\n"
        "Install with: pip install tangram-sc\n"
        "Note: Tangram is a separate package from scvi-tools."
    )


def prepare_tangram_inputs(
    adata_sc: AnnData,
    adata_sp: AnnData,
    labels_key: str = "cell_type",
    n_marker_genes: int = 100,
    marker_method: str = "wilcoxon",
) -> Tuple[AnnData, AnnData, List[str]]:
    """
    Find marker genes and preprocess both AnnData objects for Tangram.

    Runs differential expression per cell type using scanpy to select
    informative marker genes, then calls ``tg.pp_adatas()`` to align both
    datasets to the shared marker gene space. The quality of marker gene
    selection directly affects mapping accuracy.

    Parameters
    ----------
    adata_sc : AnnData
        Single-cell reference AnnData with cell type annotations in
        ``adata_sc.obs[labels_key]``. Should contain log-normalised
        expression in ``adata_sc.X`` (scanpy default after
        ``sc.pp.normalize_total`` + ``sc.pp.log1p``).
    adata_sp : AnnData
        Spatial AnnData. Should contain raw or normalised counts in
        ``adata_sp.X``. Must share gene names with ``adata_sc``.
    labels_key : str, optional
        Column in ``adata_sc.obs`` containing cell type labels (default:
        "cell_type").
    n_marker_genes : int, optional
        Maximum number of top marker genes to select per cell type
        (default: 100). Total unique genes used will be <= n_cell_types *
        n_marker_genes after deduplication and intersection with spatial genes.
    marker_method : str, optional
        Statistical test for ``sc.tl.rank_genes_groups`` (default:
        "wilcoxon"). Other valid options: "t-test", "logreg".

    Returns
    -------
    tuple of (AnnData, AnnData, list of str)
        - adata_sc: Single-cell AnnData preprocessed in-place by
          ``tg.pp_adatas()``; training genes annotated in ``.var``.
        - adata_sp: Spatial AnnData preprocessed in-place by
          ``tg.pp_adatas()``; training genes annotated in ``.var``.
        - marker_genes: List of unique marker gene names used for mapping,
          after intersection with spatial gene space.

    Raises
    ------
    ValueError
        If ``labels_key`` is not found in ``adata_sc.obs``.
    ValueError
        If no marker genes survive the intersection with spatial genes.

    Notes
    -----
    ``tg.pp_adatas()`` modifies both input AnnData objects in-place by
    annotating ``.var['is_training']`` and filtering to the shared gene
    space. Always work on copies if you need the originals unchanged.

    Examples
    --------
    >>> adata_sc, adata_sp, marker_genes = prepare_tangram_inputs(
    ...     adata_sc, adata_sp, labels_key="cell_type", n_marker_genes=100
    ... )
    >>> print(f"Mapping with {len(marker_genes)} marker genes")
    """
    print("=" * 60)
    print("Preparing Tangram Inputs")
    print("=" * 60)

    # --- Validate labels key ---
    if labels_key not in adata_sc.obs.columns:
        raise ValueError(
            f"Labels key '{labels_key}' not found in adata_sc.obs. "
            f"Available columns: {list(adata_sc.obs.columns[:10])}"
        )

    n_cell_types = adata_sc.obs[labels_key].nunique()
    cell_types = sorted(adata_sc.obs[labels_key].dropna().unique().tolist())

    print(f"\n  Single-cell data:")
    print(f"    Cells   : {adata_sc.n_obs:,}")
    print(f"    Genes   : {adata_sc.n_vars:,}")
    print(f"    Cell types ({labels_key}): {n_cell_types}")
    for ct in cell_types:
        n = int((adata_sc.obs[labels_key] == ct).sum())
        print(f"      {ct}: {n:,}")

    print(f"\n  Spatial data:")
    print(f"    Spots  : {adata_sp.n_obs:,}")
    print(f"    Genes  : {adata_sp.n_vars:,}")

    # --- Run differential expression to find marker genes ---
    print(f"\n  Finding marker genes:")
    print(f"    Method        : {marker_method}")
    print(f"    Top per type  : {n_marker_genes}")
    print(f"    Groupby       : {labels_key}")

    sc.tl.rank_genes_groups(
        adata_sc,
        groupby=labels_key,
        method=marker_method,
        use_raw=False,
    )
    print(f"  ✓ Differential expression complete")

    # --- Extract top n_marker_genes per cell type ---
    marker_genes_per_type: dict = {}
    for ct in cell_types:
        try:
            genes_ct = sc.get.rank_genes_groups_df(adata_sc, group=ct)
            top_genes = genes_ct["names"].head(n_marker_genes).tolist()
            marker_genes_per_type[ct] = top_genes
        except Exception as exc:
            warnings.warn(
                f"Could not extract marker genes for cell type '{ct}': {exc}. "
                "This type will contribute no marker genes.",
                UserWarning,
                stacklevel=2,
            )
            marker_genes_per_type[ct] = []

    # Collect unique markers across all cell types
    all_markers: List[str] = []
    seen: set = set()
    for ct in cell_types:
        for g in marker_genes_per_type[ct]:
            if g not in seen:
                all_markers.append(g)
                seen.add(g)

    n_total_before = len(all_markers)
    print(f"\n  Unique marker genes before spatial intersection: {n_total_before:,}")
    print(f"  Top {n_marker_genes} per type x {n_cell_types} types = "
          f"{n_cell_types * n_marker_genes:,} raw; "
          f"{n_total_before:,} after deduplication")

    # --- Check intersection with spatial gene space ---
    spatial_genes = set(adata_sp.var_names)
    marker_genes = [g for g in all_markers if g in spatial_genes]
    n_intersection = len(marker_genes)
    n_dropped = n_total_before - n_intersection

    if n_dropped > 0:
        warnings.warn(
            f"{n_dropped:,} marker genes not found in spatial data and will be excluded. "
            f"{n_intersection:,} genes remain after intersection.",
            UserWarning,
            stacklevel=2,
        )

    if n_intersection == 0:
        raise ValueError(
            "No marker genes survived the intersection with spatial gene space. "
            "Check that gene identifiers use the same namespace "
            "(e.g., gene symbols vs Ensembl IDs) in both datasets."
        )

    print(f"  Genes dropped (not in spatial): {n_dropped:,}")
    print(f"  Genes used for mapping         : {n_intersection:,}")

    # --- Preprocess both AnnData objects for Tangram ---
    print(f"\n  Running tg.pp_adatas() to align datasets...")
    tg.pp_adatas(adata_sc, adata_sp, genes=marker_genes)
    print(f"  ✓ Both datasets aligned to {n_intersection:,} marker genes")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("Tangram input preparation complete!")
    print("=" * 60)
    print(f"  Cell types         : {n_cell_types}")
    print(f"  Marker genes / type: up to {n_marker_genes}")
    print(f"  Total unique markers: {n_total_before:,}")
    print(f"  Genes used (in spatial): {n_intersection:,}")

    return adata_sc, adata_sp, marker_genes


def map_cells_to_space(
    adata_sc: AnnData,
    adata_sp: AnnData,
    mode: str = "clusters",
    cluster_label: str = "cell_type",
    density_prior: str = "rna_count_based",
    num_epochs: int = 500,
    device: str = "cpu",
) -> AnnData:
    """
    Map single-cell data to spatial locations using Tangram optimal transport.

    Runs ``tg.map_cells_to_space()`` to compute a probabilistic mapping
    matrix between cells (or cell type clusters) and spatial spots. The
    returned AnnData encodes this mapping in ``.X`` (cells x spots).

    Tangram is NOT a VAE. It uses optimal transport with gradient descent
    and random initialization, so results may vary slightly between runs.
    There are no uncertainty estimates.

    Parameters
    ----------
    adata_sc : AnnData
        Single-cell AnnData preprocessed by ``prepare_tangram_inputs()``.
        Must have ``.var['is_training']`` set by ``tg.pp_adatas()``.
    adata_sp : AnnData
        Spatial AnnData preprocessed by ``prepare_tangram_inputs()``.
        Must have ``.var['is_training']`` set by ``tg.pp_adatas()``.
    mode : str, optional
        Mapping mode (default: "clusters").
        - "clusters": Uses cell type cluster centroids. Faster. Maps
          proportions of each cell type per spot. Recommended for Visium
          and other low-resolution spatial technologies.
        - "cells": Maps individual cells to spots. Slower but provides
          single-cell resolution. Suitable for MERFISH, seqFISH+.
    cluster_label : str, optional
        Column in ``adata_sc.obs`` with cell type labels. Used only when
        ``mode="clusters"`` (default: "cell_type").
    density_prior : str, optional
        Prior on the density of cells across spots (default:
        "rna_count_based"). Uses total RNA counts per spot to estimate
        cell density. Alternatively, "uniform" assumes equal density.
    num_epochs : int, optional
        Number of optimisation epochs (default: 500). Increase to 1000+
        for difficult datasets or poor initial convergence.
    device : str, optional
        Compute device for PyTorch operations (default: "cpu").
        Use "cuda:0" for NVIDIA GPU or "mps" for Apple Silicon.

    Returns
    -------
    AnnData
        Mapping AnnData ``ad_map`` with:
        - ``ad_map.X``: mapping matrix of shape (n_cells, n_spots) or
          (n_cell_types, n_spots) when mode="clusters". Values represent
          the probability of each cell (or type) being present at each spot.
        - ``ad_map.uns['tangram_info']``: dict of mapping metadata.

    Notes
    -----
    Both input AnnData objects must have been preprocessed by
    ``prepare_tangram_inputs()`` (i.e., ``tg.pp_adatas()`` must have been
    called) before passing to this function.

    Examples
    --------
    >>> ad_map = map_cells_to_space(
    ...     adata_sc, adata_sp,
    ...     mode="clusters",
    ...     cluster_label="cell_type",
    ...     num_epochs=500,
    ...     device="cpu",
    ... )
    >>> print(ad_map.X.shape)  # (n_cell_types, n_spots)
    """
    print("=" * 60)
    print("Tangram: Mapping Cells to Space")
    print("=" * 60)

    print(f"\n  Mapping parameters:")
    print(f"    mode            : {mode}")
    print(f"    cluster_label   : {cluster_label}")
    print(f"    density_prior   : {density_prior}")
    print(f"    num_epochs      : {num_epochs}")
    print(f"    device          : {device}")

    if mode == "clusters" and cluster_label not in adata_sc.obs.columns:
        raise ValueError(
            f"cluster_label '{cluster_label}' not found in adata_sc.obs. "
            f"Available columns: {list(adata_sc.obs.columns[:10])}"
        )

    print(f"\n  Input shapes:")
    print(f"    Single-cell: {adata_sc.n_obs:,} cells x {adata_sc.n_vars:,} genes")
    print(f"    Spatial    : {adata_sp.n_obs:,} spots x {adata_sp.n_vars:,} genes")

    # --- Run Tangram mapping ---
    print(f"\n  Running tg.map_cells_to_space()...")
    ad_map = tg.map_cells_to_space(
        adata_sc=adata_sc,
        adata_sp=adata_sp,
        mode=mode,
        cluster_label=cluster_label,
        density_prior=density_prior,
        num_epochs=num_epochs,
        device=device,
        verbose=True,
    )
    print(f"  ✓ Mapping complete")

    # --- Report mapping matrix properties ---
    mapping_matrix = ad_map.X
    if hasattr(mapping_matrix, "toarray"):
        mapping_matrix_dense = mapping_matrix.toarray()
    else:
        mapping_matrix_dense = np.asarray(mapping_matrix)

    mapping_shape = mapping_matrix_dense.shape
    mapping_sum = float(mapping_matrix_dense.sum())
    mapping_max = float(mapping_matrix_dense.max())
    mapping_sparsity = float((mapping_matrix_dense == 0).mean())

    print(f"\n  Mapping matrix:")
    print(f"    Shape     : {mapping_shape}  "
          f"({'cells' if mode == 'cells' else 'cell types'} x spots)")
    print(f"    Total mass: {mapping_sum:.4f} (should be ~1.0 if normalised)")
    print(f"    Max value : {mapping_max:.6f}")
    print(f"    Sparsity  : {mapping_sparsity:.1%} zero entries")

    # --- Retrieve convergence info from uns if Tangram stored it ---
    training_history = ad_map.uns.get("training_history", {})
    final_loss = None
    if "main_loss" in training_history:
        loss_values = training_history["main_loss"]
        if len(loss_values) > 0:
            final_loss = float(loss_values[-1])
            print(f"\n  Convergence:")
            print(f"    Final loss  : {final_loss:.6f}")
            print(f"    Epochs run  : {len(loss_values)}")

    # --- Store metadata in ad_map.uns ---
    tangram_info = {
        "mode": mode,
        "cluster_label": cluster_label,
        "density_prior": density_prior,
        "num_epochs": num_epochs,
        "device": device,
        "mapping_shape": list(mapping_shape),
        "mapping_total_mass": mapping_sum,
        "mapping_max_value": mapping_max,
        "mapping_sparsity": mapping_sparsity,
        "final_loss": final_loss,
        "n_sc_cells": adata_sc.n_obs,
        "n_sp_spots": adata_sp.n_obs,
        "tangram_version": tg.__version__,
    }
    ad_map.uns["tangram_info"] = tangram_info
    print(f"  ✓ Metadata stored in ad_map.uns['tangram_info']")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("Tangram mapping complete!")
    print("=" * 60)
    print(f"  Mapping matrix shape: {mapping_shape}")
    print(f"  Mode                : {mode}")
    if final_loss is not None:
        print(f"  Final loss          : {final_loss:.6f}")

    print("\nNext steps:")
    print("  # Project cell type annotations to spatial spots")
    print("  adata_sp = project_annotations(ad_map, adata_sp, annotation='cell_type')")
    print()
    print("  # Impute specific genes in spatial data")
    print("  genes = ['CD3D', 'CD8A', 'CD4', 'FOXP3']")
    print("  adata_sp = impute_genes(ad_map, adata_sp, genes=genes)")

    return ad_map


def project_annotations(
    ad_map: AnnData,
    adata_sp: AnnData,
    annotation: str = "cell_type",
) -> AnnData:
    """
    Transfer cell type annotations from the mapping matrix to spatial spots.

    Calls ``tg.project_cell_annotations()`` to compute the expected cell
    type composition at each spot by multiplying the mapping matrix by
    one-hot-encoded cell type labels. Results are stored in
    ``adata_sp.obsm['tangram_ct_pred']`` (spots x cell types) and copied
    to per-type columns in ``adata_sp.obs``.

    A dominant cell type column is added as ``adata_sp.obs['tangram_dominant_type']``
    using argmax across predicted cell type scores.

    Parameters
    ----------
    ad_map : AnnData
        Mapping AnnData returned by ``map_cells_to_space()``. Must contain
        the mapping matrix in ``.X`` (cells/types x spots).
    adata_sp : AnnData
        Spatial AnnData to annotate in-place with cell type predictions.
    annotation : str, optional
        Column in the single-cell AnnData (carried in ``ad_map.obs``)
        containing cell type labels (default: "cell_type").

    Returns
    -------
    AnnData
        The input ``adata_sp`` updated with:
        - ``adata_sp.obsm['tangram_ct_pred']``: DataFrame of shape
          (n_spots, n_cell_types) with predicted cell type scores per spot.
        - ``adata_sp.obs['tangram_<cell_type>']``: Per-type score column
          for each cell type (useful for direct spatial plotting).
        - ``adata_sp.obs['tangram_dominant_type']``: Dominant (argmax) cell
          type per spot.

    Notes
    -----
    Cell type scores are NOT probabilities and do NOT sum to 1. They are
    proportional to the expected number of cells of each type per spot.
    No uncertainty estimates are available.

    Tangram does not produce confidence intervals. Treat dominant type
    assignments with caution in spots with similar scores across types.

    Examples
    --------
    >>> adata_sp = project_annotations(ad_map, adata_sp, annotation="cell_type")
    >>> sc.pl.spatial(adata_sp, color="tangram_dominant_type")
    >>> sc.pl.spatial(adata_sp, color="tangram_T cells")
    """
    print("=" * 60)
    print("Projecting Cell Type Annotations to Space")
    print("=" * 60)

    print(f"\n  Annotation key : {annotation}")
    print(f"  Spots          : {adata_sp.n_obs:,}")

    # --- Validate annotation key in ad_map.obs ---
    if annotation not in ad_map.obs.columns:
        raise ValueError(
            f"Annotation key '{annotation}' not found in ad_map.obs. "
            f"Available columns: {list(ad_map.obs.columns[:10])}"
        )

    # --- Project cell annotations ---
    print(f"\n  Running tg.project_cell_annotations()...")
    tg.project_cell_annotations(ad_map, adata_sp, annotation=annotation)
    print(f"  ✓ Annotation projection complete")

    # --- Extract prediction matrix from obsm ---
    # tg.project_cell_annotations stores results in adata_sp.obsm['tangram_ct_pred']
    if "tangram_ct_pred" not in adata_sp.obsm:
        raise RuntimeError(
            "Expected 'tangram_ct_pred' in adata_sp.obsm after "
            "tg.project_cell_annotations(), but it was not found. "
            "Check your tangram-sc version."
        )

    ct_pred = adata_sp.obsm["tangram_ct_pred"]

    # ct_pred may be a DataFrame or ndarray depending on tangram version
    try:
        cell_types = ct_pred.columns.tolist()
        ct_array = ct_pred.values
    except AttributeError:
        # ndarray fallback — try to recover column names from ad_map.obs
        cell_types = sorted(ad_map.obs[annotation].unique().tolist())
        ct_array = np.asarray(ct_pred)

    n_cell_types = len(cell_types)
    print(f"\n  Cell types in prediction: {n_cell_types}")

    # --- Copy per-type scores to obs ---
    for ct in cell_types:
        col_name = f"tangram_{ct}"
        try:
            adata_sp.obs[col_name] = ct_pred[ct].values
        except (TypeError, KeyError):
            # fallback for ndarray
            ct_idx = cell_types.index(ct)
            adata_sp.obs[col_name] = ct_array[:, ct_idx]

    print(f"  ✓ Per-type scores added to adata_sp.obs as 'tangram_<cell_type>'")

    # --- Dominant cell type per spot (argmax) ---
    dominant_idx = np.argmax(ct_array, axis=1)
    dominant_types = np.array(cell_types)[dominant_idx]
    adata_sp.obs["tangram_dominant_type"] = dominant_types
    adata_sp.obs["tangram_dominant_type"] = adata_sp.obs["tangram_dominant_type"].astype("category")
    print(f"  ✓ Dominant cell type stored in adata_sp.obs['tangram_dominant_type']")

    # --- Annotation summary ---
    print(f"\n  Cell type score summary (mean across spots):")
    dominant_counts = adata_sp.obs["tangram_dominant_type"].value_counts()
    for ct in cell_types:
        col_name = f"tangram_{ct}"
        mean_score = float(adata_sp.obs[col_name].mean())
        n_dominant = int(dominant_counts.get(ct, 0))
        print(f"    {ct:<30s}  mean_score={mean_score:.4f}  "
              f"dominant_in={n_dominant:,} spots")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("Cell type annotation projection complete!")
    print("=" * 60)
    print(f"  Cell types projected    : {n_cell_types}")
    print(f"  Spots annotated         : {adata_sp.n_obs:,}")
    print(f"  Dominant type breakdown :")
    for ct, n in dominant_counts.items():
        pct = n / adata_sp.n_obs * 100
        print(f"    {ct:<30s}  {n:,} spots ({pct:.1f}%)")

    print("\nNext steps:")
    print("  import scanpy as sc")
    print("  # Visualise dominant cell type")
    print("  sc.pl.spatial(adata_sp, color='tangram_dominant_type')")
    print()
    print("  # Visualise a specific cell type's score")
    print("  sc.pl.spatial(adata_sp, color='tangram_Macrophage', cmap='viridis')")

    return adata_sp


def impute_genes(
    ad_map: AnnData,
    adata_sp: AnnData,
    genes: List[str],
) -> AnnData:
    """
    Impute gene expression at spatial locations using the Tangram mapping.

    Calls ``tg.project_genes()`` to impute expression of genes not
    measured (or sparsely measured) in the spatial data by projecting
    single-cell expression through the mapping matrix. Imputed values are
    stored in a new AnnData and also added as a layer in ``adata_sp``.

    Parameters
    ----------
    ad_map : AnnData
        Mapping AnnData returned by ``map_cells_to_space()``.
    adata_sp : AnnData
        Spatial AnnData to receive imputed gene expression.
    genes : list of str
        Gene names to impute. Must be present in ``ad_map.var_names``
        (i.e., in the single-cell data). Genes absent from the mapping
        AnnData will be skipped with a warning.

    Returns
    -------
    AnnData
        The input ``adata_sp`` updated with:
        - ``adata_sp.layers['tangram_imputed']``: ndarray of shape
          (n_spots, n_imputed_genes) with imputed expression values for
          the requested genes. Columns correspond to ``genes_found``.
        - ``adata_sp.uns['tangram_imputed_genes']``: list of gene names
          whose imputed values are stored in the layer.

    Notes
    -----
    ``tg.project_genes()`` returns a new AnnData (spots x genes) with
    imputed expression. This function extracts that data and attaches it
    to ``adata_sp`` as a layer for convenience.

    Imputed expression reflects the average single-cell profile mapped to
    each spot. It is NOT a measurement and should not be used for
    differential expression analysis.

    Examples
    --------
    >>> genes = ["CD3D", "CD8A", "CD4", "FOXP3", "CD68"]
    >>> adata_sp = impute_genes(ad_map, adata_sp, genes=genes)
    >>> sc.pl.spatial(adata_sp, layer="tangram_imputed", color="FOXP3")
    """
    print("=" * 60)
    print("Tangram: Gene Imputation at Spatial Locations")
    print("=" * 60)

    # --- Validate gene list ---
    sc_genes = set(ad_map.var_names)
    genes_found = [g for g in genes if g in sc_genes]
    genes_missing = [g for g in genes if g not in sc_genes]

    if genes_missing:
        warnings.warn(
            f"{len(genes_missing)} requested gene(s) not found in mapping AnnData "
            f"and will be skipped: {genes_missing}",
            UserWarning,
            stacklevel=2,
        )

    if not genes_found:
        raise ValueError(
            "None of the requested genes are present in ad_map.var_names. "
            "Ensure genes were measured in the single-cell data used for mapping."
        )

    n_impute = len(genes_found)
    print(f"\n  Genes requested : {len(genes):,}")
    print(f"  Genes found     : {n_impute:,}")
    print(f"  Genes skipped   : {len(genes_missing):,}")
    if genes_missing:
        print(f"  Missing genes   : {genes_missing}")
    print(f"\n  Genes to impute :")
    for g in genes_found:
        print(f"    {g}")

    # --- Run gene imputation ---
    print(f"\n  Running tg.project_genes()...")
    adata_ge = tg.project_genes(ad_map, adata_sp, genes=genes_found)
    print(f"  ✓ Gene projection complete")

    # --- Extract imputed expression ---
    # tg.project_genes returns an AnnData (spots x genes)
    imputed_shape = adata_ge.shape
    print(f"\n  Imputed AnnData shape: {imputed_shape}  (spots x genes)")

    # Extract imputed matrix
    if hasattr(adata_ge.X, "toarray"):
        imputed_matrix = adata_ge.X.toarray()
    else:
        imputed_matrix = np.asarray(adata_ge.X)

    # Align to requested gene order
    imputed_genes_order = adata_ge.var_names.tolist()

    # --- Store in adata_sp ---
    # We store as a dense layer; genes are documented in uns
    adata_sp.layers["tangram_imputed"] = imputed_matrix
    adata_sp.uns["tangram_imputed_genes"] = imputed_genes_order
    print(f"  ✓ Imputed expression stored in adata_sp.layers['tangram_imputed']")
    print(f"    Shape : {imputed_matrix.shape}  (spots x {n_impute} genes)")
    print(f"  ✓ Gene names stored in adata_sp.uns['tangram_imputed_genes']")

    # --- Expression summary ---
    print(f"\n  Imputed expression summary (mean across spots):")
    gene_to_col = {g: i for i, g in enumerate(imputed_genes_order)}
    for g in genes_found:
        if g in gene_to_col:
            col_mean = float(imputed_matrix[:, gene_to_col[g]].mean())
            col_max = float(imputed_matrix[:, gene_to_col[g]].max())
            print(f"    {g:<20s}  mean={col_mean:.4f}  max={col_max:.4f}")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("Gene imputation complete!")
    print("=" * 60)
    print(f"  Genes imputed      : {n_impute:,}")
    print(f"  Spots              : {adata_sp.n_obs:,}")
    print(f"  Layer key          : 'tangram_imputed'")
    print(f"  Gene list in uns   : 'tangram_imputed_genes'")

    print("\nNext steps:")
    print("  import scanpy as sc")
    print("  import pandas as pd")
    print()
    print("  # Map gene name -> column index for plotting")
    print("  gene_idx = {g: i for i, g in enumerate(adata_sp.uns['tangram_imputed_genes'])}")
    print()
    print("  # Attach a single imputed gene to obs for spatial plot")
    print("  gene = 'FOXP3'")
    print("  adata_sp.obs[f'imputed_{gene}'] = adata_sp.layers['tangram_imputed'][:, gene_idx[gene]]")
    print("  sc.pl.spatial(adata_sp, color=f'imputed_{gene}', cmap='viridis')")

    return adata_sp


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("run_tangram.py — Example Usage")
    print("=" * 60)
    print()
    print("Tangram: single-cell to spatial mapping via optimal transport.")
    print()
    print("NOTE: Tangram is a separate package from scvi-tools.")
    print("      Install with: pip install tangram-sc")
    print()
    print("NOTE: Tangram uses optimal transport, NOT a VAE.")
    print("      It is stochastic (random initialisation) — results may")
    print("      vary slightly between runs. No uncertainty estimates.")
    print()
    print("Minimal workflow (cell type annotation transfer):")
    print()
    print("  import scanpy as sc")
    print("  from run_tangram import (")
    print("      prepare_tangram_inputs,")
    print("      map_cells_to_space,")
    print("      project_annotations,")
    print("      impute_genes,")
    print("  )")
    print()
    print("  # Load pre-processed AnnData objects")
    print("  # adata_sc: log-normalised counts in .X, cell types in .obs['cell_type']")
    print("  # adata_sp: normalised counts in .X, spatial coords in .obsm['spatial']")
    print("  adata_sc = sc.read_h5ad('data/adata_sc_processed.h5ad')")
    print("  adata_sp = sc.read_h5ad('data/adata_spatial.h5ad')")
    print()
    print("  # Step 1 — Find marker genes and align datasets")
    print("  adata_sc, adata_sp, marker_genes = prepare_tangram_inputs(")
    print("      adata_sc,")
    print("      adata_sp,")
    print("      labels_key='cell_type',")
    print("      n_marker_genes=100,")
    print("      marker_method='wilcoxon',")
    print("  )")
    print()
    print("  # Step 2 — Map cells to spatial coordinates")
    print("  # Use mode='clusters' for Visium (faster, uses cell type centroids)")
    print("  # Use mode='cells' for MERFISH/seqFISH+ (slower, single-cell resolution)")
    print("  ad_map = map_cells_to_space(")
    print("      adata_sc,")
    print("      adata_sp,")
    print("      mode='clusters',          # or 'cells'")
    print("      cluster_label='cell_type',")
    print("      density_prior='rna_count_based',")
    print("      num_epochs=500,")
    print("      device='cpu',             # or 'cuda:0' for GPU")
    print("  )")
    print()
    print("  # Step 3 — Project cell type annotations onto spots")
    print("  adata_sp = project_annotations(")
    print("      ad_map,")
    print("      adata_sp,")
    print("      annotation='cell_type',")
    print("  )")
    print()
    print("  # Step 4 (optional) — Impute genes not measured in spatial data")
    print("  genes_of_interest = ['CD3D', 'CD8A', 'CD4', 'FOXP3', 'CD68', 'PDCD1']")
    print("  adata_sp = impute_genes(ad_map, adata_sp, genes=genes_of_interest)")
    print()
    print("  # Step 5 — Visualise results")
    print("  sc.pl.spatial(adata_sp, color='tangram_dominant_type')")
    print("  sc.pl.spatial(adata_sp, color='tangram_Macrophage', cmap='viridis')")
    print()
    print("  # Visualise imputed gene")
    print("  gene_idx = {g: i for i, g in enumerate(adata_sp.uns['tangram_imputed_genes'])}")
    print("  adata_sp.obs['imputed_FOXP3'] = adata_sp.layers['tangram_imputed'][:, gene_idx['FOXP3']]")
    print("  sc.pl.spatial(adata_sp, color='imputed_FOXP3', cmap='viridis')")
    print()
    print("  # Save updated AnnData")
    print("  adata_sp.write_h5ad('results/adata_spatial_tangram.h5ad')")
