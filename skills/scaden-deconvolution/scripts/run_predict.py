"""
run_predict.py — Wrapper for `scaden predict` with output validation.

Deconvolves bulk RNA-seq samples using a trained Scaden ensemble.
The ensemble averages predictions from 3 models (M256, M512, M1024)
to produce final cell type fraction estimates.

Parameters
----------
bulk_file : str
    Path to bulk RNA-seq file to deconvolve (genes × samples, TSV).
model_dir : str
    Directory containing trained model weights (with M256/, M512/, M1024/ subdirs).
output_dir : str
    Directory to write predictions file.
output_name : str
    Output filename (default: "scaden_predictions.txt").
seed : int
    Random seed (default: None).

Returns
-------
dict with keys:
    predictions_file : str — path to predictions file
    n_samples : int — number of samples deconvolved
    cell_types : list — predicted cell types
    predictions : pd.DataFrame — predictions matrix (samples × cell types)

Example
-------
    from scripts.run_predict import run_scaden_predict

    result = run_scaden_predict(
        bulk_file="bulk_expression.txt",
        model_dir="scaden_model/",
        output_dir="scaden_results/",
        output_name="scaden_predictions.txt"
    )
    print(result['predictions'].head())
"""

import os
import subprocess
import sys


def run_scaden_predict(
    bulk_file: str,
    model_dir: str = "scaden_model/",
    output_dir: str = "scaden_results/",
    output_name: str = "scaden_predictions.txt",
    seed: int = None
) -> dict:
    """
    Run `scaden predict` to deconvolve bulk RNA-seq samples.

    Parameters
    ----------
    bulk_file : str
        Path to bulk RNA-seq file (genes × samples, TSV).
    model_dir : str
        Directory with trained model weights.
    output_dir : str
        Output directory.
    output_name : str
        Output predictions filename.
    seed : int or None
        Random seed.

    Returns
    -------
    dict with predictions_file, n_samples, cell_types, predictions DataFrame.
    """
    # Validate inputs
    if not os.path.exists(bulk_file):
        print(f"[ERROR] Bulk file not found: {bulk_file}")
        sys.exit(1)

    if not os.path.isdir(model_dir):
        print(f"[ERROR] Model directory not found: {model_dir}")
        sys.exit(1)

    # Check model subdirectories
    expected_subdirs = ["M256", "M512", "M1024"]
    missing = [s for s in expected_subdirs if not os.path.isdir(os.path.join(model_dir, s))]
    if missing:
        print(f"[ERROR] Model subdirectories missing from {model_dir}: {missing}")
        print(f"  Contents: {os.listdir(model_dir)}")
        print(f"  Re-run scaden train to generate the model.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, output_name)

    print(f"Running scaden predict:")
    print(f"  Bulk file:  {bulk_file}")
    print(f"  Model dir:  {model_dir}")
    print(f"  Output:     {output_path}")

    cmd = [
        "scaden", "predict",
        bulk_file,
        "--model_dir", model_dir,
        "--outname", output_path
    ]

    if seed is not None:
        cmd += ["--seed", str(seed)]

    import time
    start = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start

    if result.returncode != 0:
        print(f"[ERROR] scaden predict failed:")
        print(result.stderr)
        sys.exit(1)

    if not os.path.exists(output_path):
        print(f"[ERROR] Expected output file not found: {output_path}")
        sys.exit(1)

    # Load and validate predictions
    import pandas as pd
    preds = pd.read_csv(output_path, sep="\t", index_col=0)

    # Basic validation
    row_sums = preds.sum(axis=1)
    if not (row_sums.between(0.95, 1.05).all()):
        print(f"  [WARNING] Some rows don't sum to ~1.0: min={row_sums.min():.3f}, max={row_sums.max():.3f}")

    print(f"\n✓ Prediction complete")
    print(f"  Predictions file: {output_path}")
    print(f"  Samples deconvolved: {preds.shape[0]}")
    print(f"  Cell types predicted: {preds.columns.tolist()}")
    print(f"  Prediction time: {elapsed:.1f} seconds")
    print(f"\n  Mean cell type fractions:")
    for ct in preds.columns:
        print(f"    {ct}: {preds[ct].mean():.3f} ± {preds[ct].std():.3f}")

    return {
        "predictions_file": output_path,
        "n_samples": preds.shape[0],
        "cell_types": preds.columns.tolist(),
        "predictions": preds
    }


def load_predictions(predictions_file: str):
    """
    Load Scaden predictions file into a DataFrame.

    Parameters
    ----------
    predictions_file : str
        Path to scaden_predictions.txt.

    Returns
    -------
    pd.DataFrame : samples × cell types, values are fractions.
    """
    import pandas as pd
    preds = pd.read_csv(predictions_file, sep="\t", index_col=0)
    print(f"Loaded predictions: {preds.shape[0]} samples × {preds.shape[1]} cell types")
    print(f"Cell types: {preds.columns.tolist()}")
    return preds


def validate_predictions(predictions_file: str) -> dict:
    """
    Validate Scaden predictions and compute basic QC metrics.

    Parameters
    ----------
    predictions_file : str
        Path to predictions file.

    Returns
    -------
    dict with validation results.
    """
    import pandas as pd
    import numpy as np

    preds = pd.read_csv(predictions_file, sep="\t", index_col=0)

    row_sums = preds.sum(axis=1)
    n_negative = (preds < 0).sum().sum()
    n_uniform = (preds.std(axis=1) < 0.01).sum()

    report = {
        "n_samples": preds.shape[0],
        "n_cell_types": preds.shape[1],
        "cell_types": preds.columns.tolist(),
        "row_sum_min": row_sums.min(),
        "row_sum_max": row_sums.max(),
        "n_negative_values": n_negative,
        "n_near_uniform_samples": int(n_uniform),
        "mean_fractions": preds.mean().to_dict(),
        "std_fractions": preds.std().to_dict()
    }

    print(f"\n=== Prediction Validation ===")
    print(f"  Samples: {report['n_samples']}")
    print(f"  Cell types: {report['n_cell_types']}")
    print(f"  Row sums: {report['row_sum_min']:.4f} – {report['row_sum_max']:.4f} (should be ~1.0)")
    if n_negative > 0:
        print(f"  [WARNING] {n_negative} negative values found")
    if n_uniform > 0:
        print(f"  [WARNING] {n_uniform} samples have near-uniform predictions (std < 0.01)")
        print(f"  This may indicate insufficient training data or gene overlap")

    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run scaden predict")
    parser.add_argument("bulk_file", help="Path to bulk RNA-seq file")
    parser.add_argument("--model_dir", default="scaden_model/", help="Model directory")
    parser.add_argument("--output_dir", default="scaden_results/", help="Output directory")
    parser.add_argument("--output_name", default="scaden_predictions.txt", help="Output filename")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    args = parser.parse_args()

    run_scaden_predict(
        bulk_file=args.bulk_file,
        model_dir=args.model_dir,
        output_dir=args.output_dir,
        output_name=args.output_name,
        seed=args.seed
    )
