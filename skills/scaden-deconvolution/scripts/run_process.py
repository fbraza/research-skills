"""
run_process.py — Wrapper for `scaden process` with gene overlap validation.

Pre-processes training data by:
1. Finding the intersection of genes between training and bulk prediction data
2. Removing uninformative genes (zero expression or variance < threshold)
3. Applying log2(x+1) transformation
4. Scaling each sample to [0,1] using MinMaxScaler (per-sample)

Parameters
----------
training_data : str
    Path to .h5ad training file (from scaden simulate).
prediction_data : str
    Path to bulk RNA-seq file to deconvolve (genes × samples, TSV).
output_dir : str
    Directory to write processed .h5ad file.
output_name : str
    Output filename (default: "processed.h5ad").
var_cutoff : float
    Remove genes with variance below this threshold (default: 0.1).

Returns
-------
dict with keys:
    processed_file : str — path to processed .h5ad
    n_genes_training : int — genes in training data before processing
    n_genes_bulk : int — genes in bulk data
    n_genes_overlap : int — overlapping genes used for training

Example
-------
    from scripts.run_process import run_scaden_process

    result = run_scaden_process(
        training_data="scaden_training/data.h5ad",
        prediction_data="bulk_expression.txt",
        output_dir="scaden_training/",
        output_name="processed.h5ad"
    )
    print(f"Overlapping genes: {result['n_genes_overlap']}")
"""

import os
import subprocess
import sys


def run_scaden_process(
    training_data: str,
    prediction_data: str,
    output_dir: str = ".",
    output_name: str = "processed.h5ad",
    var_cutoff: float = 0.1
) -> dict:
    """
    Run `scaden process` to align genes and preprocess training data.

    Parameters
    ----------
    training_data : str
        Path to .h5ad training file.
    prediction_data : str
        Path to bulk RNA-seq prediction file (genes × samples, TSV).
    output_dir : str
        Output directory.
    output_name : str
        Output filename.
    var_cutoff : float
        Variance cutoff for gene filtering.

    Returns
    -------
    dict with processed_file, n_genes_training, n_genes_bulk, n_genes_overlap.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Validate inputs
    for f in [training_data, prediction_data]:
        if not os.path.exists(f):
            print(f"[ERROR] File not found: {f}")
            sys.exit(1)

    processed_file = os.path.join(output_dir, output_name)

    # Pre-check gene overlap
    overlap_info = _check_gene_overlap(training_data, prediction_data)
    print(f"Gene overlap check:")
    print(f"  Training data genes: {overlap_info['n_train']}")
    print(f"  Bulk data genes:     {overlap_info['n_bulk']}")
    print(f"  Overlapping genes:   {overlap_info['n_overlap']}")

    if overlap_info["n_overlap"] < 500:
        print(f"\n[WARNING] Only {overlap_info['n_overlap']} overlapping genes found!")
        print(f"  This is likely due to a gene identifier mismatch.")
        print(f"  Training genes (first 5): {overlap_info['train_genes'][:5]}")
        print(f"  Bulk genes (first 5):     {overlap_info['bulk_genes'][:5]}")
        print(f"  Check that both use the same identifier type (HGNC symbols or Ensembl IDs).")
        print(f"  See references/troubleshooting.md for solutions.")
        if overlap_info["n_overlap"] < 100:
            print(f"[ERROR] Too few overlapping genes to proceed. Aborting.")
            sys.exit(1)
    elif overlap_info["n_overlap"] < 1000:
        print(f"  [WARNING] <1,000 overlapping genes — performance may be reduced")
    else:
        print(f"  ✓ Gene overlap is sufficient")

    print(f"\nRunning scaden process:")
    print(f"  Training data:  {training_data}")
    print(f"  Bulk data:      {prediction_data}")
    print(f"  Output:         {processed_file}")
    print(f"  Var cutoff:     {var_cutoff}")

    cmd = [
        "scaden", "process",
        training_data,
        prediction_data,
        "--processed_path", processed_file,
        "--var_cutoff", str(var_cutoff)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[ERROR] scaden process failed:")
        print(result.stderr)
        sys.exit(1)

    if not os.path.exists(processed_file):
        print(f"[ERROR] Expected output file not found: {processed_file}")
        sys.exit(1)

    # Inspect processed output
    try:
        import anndata as ad
        processed = ad.read_h5ad(processed_file)
        n_genes_final = processed.n_vars
        print(f"\n✓ Processing complete")
        print(f"  Processed file: {processed_file}")
        print(f"  Samples: {processed.n_obs}")
        print(f"  Genes after filtering: {n_genes_final}")
    except Exception:
        n_genes_final = "unknown"
        print(f"\n✓ Processing complete: {processed_file}")

    return {
        "processed_file": processed_file,
        "n_genes_training": overlap_info["n_train"],
        "n_genes_bulk": overlap_info["n_bulk"],
        "n_genes_overlap": overlap_info["n_overlap"],
        "n_genes_final": n_genes_final
    }


def _check_gene_overlap(training_data: str, prediction_data: str) -> dict:
    """Check gene overlap between training and bulk data before processing."""
    try:
        import anndata as ad
        import pandas as pd

        train = ad.read_h5ad(training_data)
        train_genes = set(train.var_names)

        bulk = pd.read_csv(prediction_data, sep="\t", index_col=0)
        bulk_genes = set(bulk.index)

        overlap = train_genes & bulk_genes

        return {
            "n_train": len(train_genes),
            "n_bulk": len(bulk_genes),
            "n_overlap": len(overlap),
            "train_genes": sorted(list(train_genes))[:10],
            "bulk_genes": sorted(list(bulk_genes))[:10]
        }
    except Exception as e:
        print(f"  [WARNING] Could not pre-check gene overlap: {e}")
        return {"n_train": "unknown", "n_bulk": "unknown", "n_overlap": "unknown",
                "train_genes": [], "bulk_genes": []}


def check_bulk_format(bulk_file: str) -> bool:
    """
    Validate bulk expression file format for Scaden.

    Parameters
    ----------
    bulk_file : str
        Path to bulk RNA-seq file.

    Returns
    -------
    bool : True if format is valid.
    """
    import pandas as pd

    print(f"Validating bulk file: {bulk_file}")
    valid = True

    try:
        bulk = pd.read_csv(bulk_file, sep="\t", index_col=0)
    except Exception as e:
        print(f"  [ERROR] Could not load file: {e}")
        return False

    print(f"  Shape: {bulk.shape[0]} genes × {bulk.shape[1]} samples")

    # Check orientation (should be genes × samples)
    if bulk.shape[0] < bulk.shape[1]:
        print(f"  [WARNING] More columns ({bulk.shape[1]}) than rows ({bulk.shape[0]})")
        print(f"  Scaden expects genes as rows and samples as columns.")
        print(f"  If your data is transposed, use: bulk.T.to_csv('bulk_fixed.txt', sep='\\t')")

    # Check for log-transformed data
    max_val = bulk.values.max()
    if max_val < 20:
        print(f"  [WARNING] Max value is {max_val:.2f} — data may be log-transformed")
        print(f"  Scaden applies log2(x+1) internally. Do NOT pre-log-transform.")
        valid = False
    else:
        print(f"  ✓ Values look like raw/normalized counts (max={max_val:.1f})")

    # Check for NaN
    n_nan = bulk.isna().sum().sum()
    if n_nan > 0:
        print(f"  [WARNING] {n_nan} NaN values — fill with 0 before processing")
    else:
        print(f"  ✓ No NaN values")

    print(f"  Sample names: {bulk.columns[:5].tolist()}")
    print(f"  Gene names (first 5): {bulk.index[:5].tolist()}")

    return valid


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run scaden process")
    parser.add_argument("training_data", help="Path to .h5ad training file")
    parser.add_argument("prediction_data", help="Path to bulk RNA-seq file")
    parser.add_argument("--output_dir", default="scaden_training/", help="Output directory")
    parser.add_argument("--output_name", default="processed.h5ad", help="Output filename")
    parser.add_argument("--var_cutoff", type=float, default=0.1, help="Variance cutoff")
    args = parser.parse_args()

    run_scaden_process(
        training_data=args.training_data,
        prediction_data=args.prediction_data,
        output_dir=args.output_dir,
        output_name=args.output_name,
        var_cutoff=args.var_cutoff
    )
