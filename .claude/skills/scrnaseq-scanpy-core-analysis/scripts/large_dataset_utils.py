"""
Large Dataset Utilities for AnnData / Scanpy workflows.

Use these functions when working with single-cell datasets that are too large to load
entirely into memory, or when concatenating many samples before analysis.

Functions:
    load_backed()               — Open an h5ad in backed mode, inspect, filter, load subset
    concat_samples_on_disk()    — Concatenate multiple h5ad files without loading into RAM
    concat_samples_lazy()       — Lazy multi-file view via AnnCollection
    concat_samples_inmemory()   — Standard in-memory concatenation with safety checks
    optimize_anndata_memory()   — Convert to sparse + categorical to reduce footprint
    chunked_gene_stats()        — Compute per-gene statistics on large backed dataset

Dependencies:
    pip install anndata numpy scipy pandas
    pip install fsspec s3fs  # optional, for Zarr/cloud access
"""

import sys
import numpy as np
import pandas as pd
import anndata as ad
from pathlib import Path
from scipy.sparse import csr_matrix, issparse
from typing import List, Optional, Union


# ---------------------------------------------------------------------------
# 1. Backed mode loader
# ---------------------------------------------------------------------------

def load_backed(
    path: str,
    filter_obs: Optional[dict] = None,
    load_to_memory: bool = True,
    mode: str = 'r'
) -> ad.AnnData:
    """
    Open an h5ad in backed mode, inspect metadata, optionally filter and load.

    Parameters
    ----------
    path
        Path to h5ad file.
    filter_obs
        Dict of {column: value} filters applied before loading into memory.
        E.g. {'quality_score': lambda x: x > 0.8, 'cell_type': 'T cell'}
    load_to_memory
        If True (default), load the (optionally filtered) object into RAM.
        If False, return the backed object as-is for further inspection.
    mode
        'r' for read-only, 'r+' for read-write (to modify obs/var on disk).

    Returns
    -------
    AnnData object (backed or in-memory depending on load_to_memory).

    Example
    -------
    >>> adata = load_backed(
    ...     'large.h5ad',
    ...     filter_obs={'quality_score': lambda x: x > 0.8},
    ...     load_to_memory=True
    ... )
    """
    print(f"Opening backed ({mode}): {path}")
    adata = ad.read_h5ad(path, backed=mode)
    print(f"  Shape: {adata.n_obs} cells × {adata.n_vars} genes")
    print(f"  obs columns: {adata.obs.columns.tolist()}")
    print(f"  var columns: {adata.var.columns.tolist()}")

    if filter_obs:
        mask = pd.Series([True] * adata.n_obs, index=adata.obs_names)
        for col, condition in filter_obs.items():
            if col not in adata.obs.columns:
                raise KeyError(f"Column '{col}' not found in adata.obs")
            if callable(condition):
                col_mask = condition(adata.obs[col])
            else:
                col_mask = adata.obs[col] == condition
            mask = mask & col_mask
            n_pass = mask.sum()
            print(f"  Filter [{col}]: {n_pass} / {adata.n_obs} cells pass")
        adata = adata[mask.values]

    if load_to_memory:
        print(f"  Loading {adata.n_obs} cells into memory...")
        adata = adata.to_memory()
        print(f"✓ Loaded: {adata.n_obs} cells × {adata.n_vars} genes")

    return adata


# ---------------------------------------------------------------------------
# 2. On-disk concatenation (no RAM required)
# ---------------------------------------------------------------------------

def concat_samples_on_disk(
    input_files: List[str],
    output_file: str,
    sample_keys: Optional[List[str]] = None,
    sample_label: str = 'sample',
    join: str = 'inner',
    backed_output: bool = True
) -> ad.AnnData:
    """
    Concatenate multiple h5ad files directly on disk without loading into memory.

    Parameters
    ----------
    input_files
        List of paths to h5ad files.
    output_file
        Path for the output h5ad file.
    sample_keys
        Labels for each file (used as values in sample_label column).
        Defaults to filename stems if not provided.
    sample_label
        obs column name to store sample identity.
    join
        'inner' (shared genes only) or 'outer' (all genes, fills missing with 0).
    backed_output
        If True (default), return the output file in backed mode.

    Returns
    -------
    AnnData backed on the output file (ready for further filtering).

    Example
    -------
    >>> adata = concat_samples_on_disk(
    ...     ['s1.h5ad', 's2.h5ad', 's3.h5ad'],
    ...     'combined.h5ad',
    ...     sample_keys=['S1', 'S2', 'S3']
    ... )
    """
    try:
        from anndata.experimental import concat_on_disk
    except ImportError:
        raise ImportError(
            "concat_on_disk requires anndata ≥ 0.10. "
            "Upgrade: pip install 'anndata>=0.10'"
        )

    if sample_keys is None:
        sample_keys = [Path(f).stem for f in input_files]

    if len(sample_keys) != len(input_files):
        raise ValueError("sample_keys must have same length as input_files")

    print(f"Concatenating {len(input_files)} files on disk → {output_file}")
    for f, k in zip(input_files, sample_keys):
        print(f"  {k}: {f}")

    concat_on_disk(
        in_files=input_files,
        out_file=output_file,
        join=join,
        label=sample_label,
        keys=sample_keys,
        index_unique='_'
    )

    print(f"✓ On-disk concatenation complete: {output_file}")

    # Return in backed mode for inspection / downstream filtering
    adata = ad.read_h5ad(output_file, backed='r')
    print(f"  Shape: {adata.n_obs} cells × {adata.n_vars} genes")
    print(f"  Sample distribution:\n{adata.obs[sample_label].value_counts().to_string()}")
    return adata


# ---------------------------------------------------------------------------
# 3. Lazy multi-file view (AnnCollection)
# ---------------------------------------------------------------------------

def concat_samples_lazy(
    input_files: List[str],
    sample_keys: Optional[List[str]] = None,
    sample_label: str = 'dataset',
    join_vars: str = 'inner'
):
    """
    Create a lazy view across multiple h5ad files using AnnCollection.

    Does not load X into memory. Useful for inspecting a cohort, computing
    metadata statistics, or filtering before deciding how much to load.

    Parameters
    ----------
    input_files
        List of paths to h5ad files.
    sample_keys
        Labels for each file. Defaults to filename stems.
    sample_label
        obs column name for sample identity.
    join_vars
        'inner' (shared genes) or 'outer' (all genes).

    Returns
    -------
    AnnCollection object (call .to_adata() to load all data).

    Example
    -------
    >>> coll = concat_samples_lazy(['s1.h5ad', 's2.h5ad'])
    >>> print(coll.obs['cell_type'].value_counts())
    >>> adata = coll[coll.obs['cell_type'] == 'Macrophage'].to_adata()
    """
    try:
        from anndata.experimental import AnnCollection
    except ImportError:
        raise ImportError(
            "AnnCollection requires anndata ≥ 0.9. "
            "Upgrade: pip install 'anndata>=0.9'"
        )

    if sample_keys is None:
        sample_keys = [Path(f).stem for f in input_files]

    print(f"Creating lazy AnnCollection from {len(input_files)} files")
    collection = AnnCollection(
        input_files,
        join_obs='outer',
        join_vars=join_vars,
        label=sample_label,
        keys=sample_keys
    )
    print(f"  Total cells: {collection.n_obs}")
    return collection


# ---------------------------------------------------------------------------
# 4. Standard in-memory concatenation (with safety checks)
# ---------------------------------------------------------------------------

def concat_samples_inmemory(
    adatas: dict,
    join: str = 'inner',
    sample_label: str = 'sample'
) -> ad.AnnData:
    """
    Concatenate a dict of AnnData objects in memory with safety checks.

    Parameters
    ----------
    adatas
        Dict of {sample_name: AnnData}. Each AnnData should contain raw counts.
    join
        'inner' or 'outer'.
    sample_label
        obs column name for sample identity.

    Returns
    -------
    Concatenated AnnData with unique barcodes and a sample column.

    Example
    -------
    >>> adatas = {
    ...     'donor1': ad.read_h5ad('donor1.h5ad'),
    ...     'donor2': ad.read_h5ad('donor2.h5ad'),
    ... }
    >>> adata = concat_samples_inmemory(adatas)
    """
    # Pre-flight checks
    gene_sets = {k: set(v.var_names) for k, v in adatas.items()}
    shared_genes = set.intersection(*gene_sets.values())
    all_genes = set.union(*gene_sets.values())
    print(f"Gene overlap: {len(shared_genes)} shared / {len(all_genes)} total across {len(adatas)} samples")
    if join == 'inner' and len(shared_genes) < len(all_genes):
        dropped = len(all_genes) - len(shared_genes)
        print(f"  inner join: dropping {dropped} genes not shared across all samples")

    combined = ad.concat(
        adatas,
        axis=0,
        join=join,
        label=sample_label,
        index_unique='_'
    )

    # Validate output
    assert combined.obs_names.is_unique, "Duplicate barcodes after concat — this should not happen"
    print(f"✓ Concatenation complete: {combined.n_obs} cells × {combined.n_vars} genes")
    print(f"  Sample distribution:\n{combined.obs[sample_label].value_counts().to_string()}")
    return combined


# ---------------------------------------------------------------------------
# 5. Memory optimization
# ---------------------------------------------------------------------------

def optimize_anndata_memory(adata: ad.AnnData, inplace: bool = True) -> ad.AnnData:
    """
    Reduce memory footprint by converting to sparse matrices and categoricals.

    Applies:
    - Convert dense X to CSR sparse if density < 50%
    - Convert string obs/var columns to categoricals
    - Downcast float64 layers to float32

    Parameters
    ----------
    adata
        AnnData object to optimize.
    inplace
        If True (default), modify in place. If False, work on a copy.

    Returns
    -------
    Optimized AnnData.

    Example
    -------
    >>> adata = optimize_anndata_memory(adata)
    >>> adata.write_h5ad('optimized.h5ad', compression='gzip')
    """
    if not inplace:
        adata = adata.copy()

    # 1. X → sparse CSR
    if not issparse(adata.X):
        density = np.count_nonzero(adata.X) / adata.X.size
        if density < 0.5:
            adata.X = csr_matrix(adata.X)
            print(f"  X converted to sparse CSR (density={density:.1%})")
        else:
            print(f"  X kept dense (density={density:.1%})")
    else:
        print(f"  X already sparse ({type(adata.X).__name__})")

    # 2. String columns → categoricals
    before_obs = adata.obs.memory_usage(deep=True).sum()
    adata.strings_to_categoricals()
    after_obs = adata.obs.memory_usage(deep=True).sum()
    print(f"  obs memory: {before_obs/1e6:.1f} MB → {after_obs/1e6:.1f} MB after categoricals")

    # 3. Downcast float64 layers to float32
    for key in list(adata.layers.keys()):
        layer = adata.layers[key]
        if hasattr(layer, 'dtype') and layer.dtype == np.float64:
            if issparse(layer):
                layer = layer.astype(np.float32)
            else:
                layer = layer.astype(np.float32)
            adata.layers[key] = layer
            print(f"  layers['{key}']: float64 → float32")

    print("✓ Memory optimization complete")
    return adata


# ---------------------------------------------------------------------------
# 6. Chunked statistics on large backed datasets
# ---------------------------------------------------------------------------

def chunked_gene_stats(
    path: str,
    chunk_size: int = 1000,
    genes: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Compute per-gene mean and fraction of expressing cells on a large backed dataset.

    Parameters
    ----------
    path
        Path to h5ad file (opened in backed mode internally).
    chunk_size
        Number of cells per chunk.
    genes
        Optional list of gene names to restrict to. Defaults to all genes.

    Returns
    -------
    DataFrame with columns: gene, mean_expression, frac_expressing

    Example
    -------
    >>> stats = chunked_gene_stats('large.h5ad', genes=['CD68', 'MRC1', 'CCL2'])
    >>> print(stats.sort_values('mean_expression', ascending=False))
    """
    adata = ad.read_h5ad(path, backed='r')
    print(f"Computing gene stats: {adata.n_obs} cells × {adata.n_vars} genes (chunk_size={chunk_size})")

    if genes is not None:
        missing = [g for g in genes if g not in adata.var_names]
        if missing:
            print(f"  Warning: {len(missing)} genes not found: {missing[:5]}...")
        genes = [g for g in genes if g in adata.var_names]
        gene_idx = [adata.var_names.get_loc(g) for g in genes]
    else:
        genes = adata.var_names.tolist()
        gene_idx = list(range(adata.n_vars))

    n_genes = len(genes)
    sum_expr = np.zeros(n_genes, dtype=np.float64)
    n_expressing = np.zeros(n_genes, dtype=np.int64)

    n_cells = 0
    for i in range(0, adata.n_obs, chunk_size):
        chunk = adata[i:i + chunk_size, gene_idx].to_memory()
        X = chunk.X
        if issparse(X):
            sum_expr += np.asarray(X.sum(axis=0)).flatten()
            n_expressing += np.asarray((X > 0).sum(axis=0)).flatten()
        else:
            sum_expr += X.sum(axis=0)
            n_expressing += (X > 0).sum(axis=0)
        n_cells += chunk.n_obs

    stats = pd.DataFrame({
        'gene': genes,
        'mean_expression': sum_expr / n_cells,
        'frac_expressing': n_expressing / n_cells
    }).set_index('gene')

    print(f"✓ Gene stats computed for {n_genes} genes across {n_cells} cells")
    return stats


# ---------------------------------------------------------------------------
# Quick demo
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print("large_dataset_utils.py — import and use individual functions.")
    print("Functions: load_backed, concat_samples_on_disk, concat_samples_lazy,")
    print("           concat_samples_inmemory, optimize_anndata_memory, chunked_gene_stats")
    sys.exit(0)
