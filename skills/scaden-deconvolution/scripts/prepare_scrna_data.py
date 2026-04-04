"""
prepare_scrna_data.py — Convert annotated scRNA-seq AnnData to Scaden-compatible format.

Takes an AnnData object (h5ad) with cell type annotations and exports
the count matrix and cell type label files required by `scaden simulate`.

Supports:
- Single dataset export
- Multi-donor splitting (recommended for multi-subject datasets)
- AnnData h5ad format (v1.1.0+) as direct input to scaden simulate

Parameters
----------
adata_path : str
    Path to AnnData .h5ad file with raw or normalized counts.
celltype_column : str
    Column in adata.obs containing cell type labels (will be renamed to 'Celltype').
output_dir : str
    Directory to write output files.
prefix : str
    Prefix for output files (e.g., "pbmc" → "pbmc_counts.txt", "pbmc_celltypes.txt").
split_by_donor : bool
    If True, split by donor and write separate files per donor.
donor_column : str
    Column in adata.obs with donor/subject IDs (required if split_by_donor=True).
min_cells_per_type : int
    Minimum cells per cell type to include (default: 10).
exclude_celltypes : list
    Cell type labels to exclude (e.g., ["Unknown", "Doublet"]).

Returns
-------
list of dict, each with:
    prefix : str
    counts_file : str
    celltypes_file : str
    n_cells : int
    cell_types : list

Example
-------
    from scripts.prepare_scrna_data import prepare_scrna_for_scaden

    files = prepare_scrna_for_scaden(
        adata_path="pbmc_annotated.h5ad",
        celltype_column="cell_type",
        output_dir="scaden_input/",
        prefix="pbmc",
        split_by_donor=True,
        donor_column="donor_id"
    )
"""

import os
import sys
import warnings
import numpy as np
import pandas as pd


def prepare_scrna_for_scaden(
    adata_path: str,
    celltype_column: str,
    output_dir: str,
    prefix: str = "dataset",
    split_by_donor: bool = False,
    donor_column: str = None,
    min_cells_per_type: int = 10,
    exclude_celltypes: list = None,
    use_raw: bool = True,
    save_h5ad: bool = False
) -> list:
    """
    Convert annotated scRNA-seq AnnData to Scaden-compatible count and celltype files.

    Parameters
    ----------
    adata_path : str
        Path to AnnData .h5ad file.
    celltype_column : str
        Column in adata.obs with cell type labels.
    output_dir : str
        Output directory.
    prefix : str
        File prefix.
    split_by_donor : bool
        Split by donor for multi-subject data (recommended).
    donor_column : str
        Column in adata.obs with donor IDs.
    min_cells_per_type : int
        Minimum cells per cell type to retain.
    exclude_celltypes : list
        Cell types to exclude from training.
    use_raw : bool
        Use adata.raw if available (recommended for raw counts).
    save_h5ad : bool
        Also save as .h5ad with Celltype in obs (for scaden simulate --fmt h5ad).

    Returns
    -------
    list of dict with file paths and metadata per output file.
    """
    try:
        import scanpy as sc
        import anndata as ad
    except ImportError:
        print("[ERROR] scanpy and anndata required: pip install scanpy anndata")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    exclude_celltypes = exclude_celltypes or ["Unknown", "Doublet", "doublet", "unknown"]

    print(f"Loading AnnData from: {adata_path}")
    adata = sc.read_h5ad(adata_path)
    print(f"  Loaded: {adata.n_obs} cells × {adata.n_vars} genes")

    # Validate celltype column
    if celltype_column not in adata.obs.columns:
        print(f"[ERROR] Column '{celltype_column}' not found in adata.obs")
        print(f"  Available columns: {adata.obs.columns.tolist()}")
        sys.exit(1)

    # Get expression matrix
    if use_raw and adata.raw is not None:
        print("  Using adata.raw for counts")
        X = adata.raw.to_adata().X
        gene_names = adata.raw.var_names
    else:
        X = adata.X
        gene_names = adata.var_names

    # Convert sparse to dense if needed
    if hasattr(X, "toarray"):
        X = X.toarray()

    # Build base DataFrame
    counts_df = pd.DataFrame(X, index=adata.obs_names, columns=gene_names)
    celltypes_df = pd.DataFrame({"Celltype": adata.obs[celltype_column].values},
                                 index=adata.obs_names)

    # Exclude unwanted cell types
    mask = ~celltypes_df["Celltype"].isin(exclude_celltypes)
    counts_df = counts_df[mask]
    celltypes_df = celltypes_df[mask]
    if mask.sum() < len(mask):
        n_excluded = len(mask) - mask.sum()
        print(f"  Excluded {n_excluded} cells with types: {exclude_celltypes}")

    # Filter cell types with too few cells
    type_counts = celltypes_df["Celltype"].value_counts()
    valid_types = type_counts[type_counts >= min_cells_per_type].index
    removed_types = type_counts[type_counts < min_cells_per_type].index.tolist()
    if removed_types:
        print(f"  Removing cell types with <{min_cells_per_type} cells: {removed_types}")
        mask2 = celltypes_df["Celltype"].isin(valid_types)
        counts_df = counts_df[mask2]
        celltypes_df = celltypes_df[mask2]

    print(f"  Cell types retained: {celltypes_df['Celltype'].unique().tolist()}")
    print(f"  Cells retained: {len(counts_df)}")

    output_files = []

    if split_by_donor and donor_column is not None:
        if donor_column not in adata.obs.columns:
            print(f"[ERROR] Donor column '{donor_column}' not found in adata.obs")
            sys.exit(1)

        donors = adata.obs.loc[counts_df.index, donor_column].values
        donor_series = pd.Series(donors, index=counts_df.index)
        unique_donors = donor_series.unique()
        print(f"  Splitting by donor: {len(unique_donors)} donors found")

        for donor in unique_donors:
            donor_mask = donor_series == donor
            donor_counts = counts_df[donor_mask]
            donor_celltypes = celltypes_df[donor_mask]

            # Skip donors with too few cells
            if len(donor_counts) < 50:
                print(f"  Skipping donor {donor}: only {len(donor_counts)} cells")
                continue

            donor_prefix = f"{prefix}_{str(donor).replace(' ', '_')}"
            result = _write_scaden_files(
                donor_counts, donor_celltypes, output_dir, donor_prefix,
                save_h5ad=save_h5ad
            )
            output_files.append(result)

    else:
        result = _write_scaden_files(
            counts_df, celltypes_df, output_dir, prefix,
            save_h5ad=save_h5ad
        )
        output_files.append(result)

    print(f"\n✓ Preparation complete: {len(output_files)} file set(s) written to {output_dir}")
    print(f"  Use pattern '*_counts.txt' with scaden simulate")
    return output_files


def _write_scaden_files(counts_df, celltypes_df, output_dir, prefix, save_h5ad=False):
    """Write count matrix and celltype label files for one dataset."""
    counts_file = os.path.join(output_dir, f"{prefix}_counts.txt")
    celltypes_file = os.path.join(output_dir, f"{prefix}_celltypes.txt")

    counts_df.to_csv(counts_file, sep="\t")
    celltypes_df.to_csv(celltypes_file, sep="\t", index=False)

    print(f"  ✓ Saved {prefix}: {counts_df.shape[0]} cells × {counts_df.shape[1]} genes")
    print(f"    Cell types: {celltypes_df['Celltype'].value_counts().to_dict()}")

    result = {
        "prefix": prefix,
        "counts_file": counts_file,
        "celltypes_file": celltypes_file,
        "n_cells": len(counts_df),
        "cell_types": celltypes_df["Celltype"].unique().tolist()
    }

    if save_h5ad:
        import anndata as ad
        adata_out = ad.AnnData(X=counts_df.values,
                               obs=celltypes_df,
                               var=pd.DataFrame(index=counts_df.columns))
        h5ad_file = os.path.join(output_dir, f"{prefix}.h5ad")
        adata_out.write_h5ad(h5ad_file)
        result["h5ad_file"] = h5ad_file
        print(f"    Also saved as: {h5ad_file}")

    return result


def validate_scaden_input(counts_file: str, celltypes_file: str) -> bool:
    """
    Validate that count and celltype files are correctly formatted for Scaden.

    Parameters
    ----------
    counts_file : str
        Path to count matrix file.
    celltypes_file : str
        Path to cell type label file.

    Returns
    -------
    bool : True if valid, False otherwise.
    """
    valid = True

    counts = pd.read_csv(counts_file, sep="\t", index_col=0)
    celltypes = pd.read_csv(celltypes_file, sep="\t")

    print(f"Validating: {counts_file}")
    print(f"  Count matrix shape: {counts.shape}")

    # Check Celltype column
    if "Celltype" not in celltypes.columns:
        print(f"  [ERROR] 'Celltype' column missing from {celltypes_file}")
        print(f"  Found columns: {celltypes.columns.tolist()}")
        valid = False
    else:
        print(f"  ✓ 'Celltype' column present")
        print(f"  Cell types: {celltypes['Celltype'].unique().tolist()}")

    # Check row count match
    if len(counts) != len(celltypes):
        print(f"  [ERROR] Row count mismatch: {len(counts)} cells vs {len(celltypes)} labels")
        valid = False
    else:
        print(f"  ✓ Row counts match: {len(counts)} cells")

    # Check for log-transformed data (warn if values look log-transformed)
    max_val = counts.values.max()
    if max_val < 20:
        print(f"  [WARNING] Max expression value is {max_val:.2f} — data may already be log-transformed")
        print(f"  Scaden applies log2(x+1) internally. Pre-log-transformed data will degrade performance.")
    else:
        print(f"  ✓ Expression values look like raw/normalized counts (max={max_val:.1f})")

    # Check for NaN
    n_nan = counts.isna().sum().sum()
    if n_nan > 0:
        print(f"  [WARNING] {n_nan} NaN values found — fill with 0 before proceeding")
    else:
        print(f"  ✓ No NaN values")

    return valid


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Prepare scRNA-seq data for Scaden")
    parser.add_argument("adata_path", help="Path to AnnData .h5ad file")
    parser.add_argument("--celltype_column", default="cell_type", help="Cell type column in adata.obs")
    parser.add_argument("--output_dir", default="scaden_input/", help="Output directory")
    parser.add_argument("--prefix", default="dataset", help="File prefix")
    parser.add_argument("--split_by_donor", action="store_true", help="Split by donor")
    parser.add_argument("--donor_column", default=None, help="Donor column in adata.obs")
    args = parser.parse_args()

    prepare_scrna_for_scaden(
        adata_path=args.adata_path,
        celltype_column=args.celltype_column,
        output_dir=args.output_dir,
        prefix=args.prefix,
        split_by_donor=args.split_by_donor,
        donor_column=args.donor_column
    )
