"""
run_simulate.py — Wrapper for `scaden simulate` with validation and reporting.

Generates artificial bulk RNA-seq training samples from scRNA-seq data.
Each simulated sample is created by randomly subsampling cells from the
scRNA-seq dataset and summing their expression profiles.

Parameters
----------
data_dir : str
    Directory containing scRNA-seq count and celltype files.
output_dir : str
    Directory to write the output .h5ad training file.
n_samples : int
    Number of artificial bulk samples to generate (default: 5000).
cells_per_sample : int
    Number of cells aggregated per simulated sample (default: 500).
pattern : str
    Glob pattern to find count files (default: "*_counts.txt").
prefix : str
    Prefix for output file (default: "data" → "data.h5ad").

Returns
-------
dict with keys:
    h5ad_file : str — path to output .h5ad training file
    n_samples : int — number of samples generated
    cell_types : list — cell types in training data

Example
-------
    from scripts.run_simulate import run_scaden_simulate

    result = run_scaden_simulate(
        data_dir="scaden_input/",
        output_dir="scaden_training/",
        n_samples=5000,
        cells_per_sample=500,
        pattern="*_counts.txt"
    )
"""

import os
import subprocess
import sys


def run_scaden_simulate(
    data_dir: str,
    output_dir: str = ".",
    n_samples: int = 5000,
    cells_per_sample: int = 500,
    pattern: str = "*_counts.txt",
    prefix: str = "data",
    fmt: str = "txt"
) -> dict:
    """
    Run `scaden simulate` to generate artificial bulk RNA-seq training data.

    Parameters
    ----------
    data_dir : str
        Directory with scRNA-seq count and celltype files.
    output_dir : str
        Output directory for .h5ad training file.
    n_samples : int
        Number of simulated bulk samples.
    cells_per_sample : int
        Cells per simulated sample (paper default: 500).
    pattern : str
        Glob pattern for count files (must include *).
    prefix : str
        Output file prefix.
    fmt : str
        Input format: "txt" or "h5ad".

    Returns
    -------
    dict with h5ad_file, n_samples, cell_types.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Validate data directory
    if not os.path.isdir(data_dir):
        print(f"[ERROR] Data directory not found: {data_dir}")
        sys.exit(1)

    # Check for matching files
    import glob
    matching = glob.glob(os.path.join(data_dir, pattern.replace("*", "*")))
    if not matching:
        print(f"[ERROR] No files found matching pattern '{pattern}' in {data_dir}")
        print(f"  Files in directory: {os.listdir(data_dir)}")
        sys.exit(1)

    print(f"Found {len(matching)} count file(s) matching '{pattern}':")
    for f in matching:
        print(f"  {os.path.basename(f)}")

    # Validate pattern includes *
    if "*" not in pattern:
        print(f"[WARNING] Pattern '{pattern}' does not include '*' — scaden simulate requires a wildcard")
        pattern = "*" + pattern

    print(f"\nRunning scaden simulate:")
    print(f"  Data dir:    {data_dir}")
    print(f"  Pattern:     {pattern}")
    print(f"  N samples:   {n_samples}")
    print(f"  Cells/sample:{cells_per_sample}")
    print(f"  Output dir:  {output_dir}")
    print(f"  Prefix:      {prefix}")

    cmd = [
        "scaden", "simulate",
        "--data", data_dir,
        "--pattern", pattern,
        "-n", str(n_samples),
        "--cells", str(cells_per_sample),
        "--out", output_dir,
        "--prefix", prefix,
        "--fmt", fmt
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[ERROR] scaden simulate failed:")
        print(result.stderr)
        sys.exit(1)

    h5ad_file = os.path.join(output_dir, f"{prefix}.h5ad")

    if not os.path.exists(h5ad_file):
        print(f"[ERROR] Expected output file not found: {h5ad_file}")
        print(f"  stdout: {result.stdout}")
        print(f"  stderr: {result.stderr}")
        sys.exit(1)

    # Inspect output
    output_info = _inspect_training_data(h5ad_file)

    print(f"\n✓ Simulation complete")
    print(f"  Training file: {h5ad_file}")
    print(f"  Samples generated: {output_info['n_samples']}")
    print(f"  Cell types: {output_info['cell_types']}")
    print(f"  Genes: {output_info['n_genes']}")

    return {
        "h5ad_file": h5ad_file,
        "n_samples": output_info["n_samples"],
        "cell_types": output_info["cell_types"],
        "n_genes": output_info["n_genes"]
    }


def _inspect_training_data(h5ad_file: str) -> dict:
    """Load and inspect the simulated training data."""
    try:
        import anndata as ad
        adata = ad.read_h5ad(h5ad_file)
        cell_types = list(adata.obs.columns) if adata.obs.shape[1] > 0 else []
        # Cell type fractions are stored as obs columns
        return {
            "n_samples": adata.n_obs,
            "n_genes": adata.n_vars,
            "cell_types": cell_types
        }
    except Exception as e:
        print(f"  [WARNING] Could not inspect training data: {e}")
        return {"n_samples": "unknown", "n_genes": "unknown", "cell_types": []}


def merge_training_datasets(h5ad_files: list, output_file: str) -> str:
    """
    Merge multiple .h5ad training files into one using `scaden merge`.

    Parameters
    ----------
    h5ad_files : list of str
        Paths to .h5ad files to merge.
    output_file : str
        Output merged .h5ad file path.

    Returns
    -------
    str : Path to merged file.
    """
    if not h5ad_files:
        print("[ERROR] No files provided to merge")
        sys.exit(1)

    files_str = ",".join(h5ad_files)
    cmd = ["scaden", "merge", "--files", files_str, "--out", output_file]

    print(f"Merging {len(h5ad_files)} training datasets...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[ERROR] scaden merge failed:\n{result.stderr}")
        sys.exit(1)

    print(f"✓ Merged training data saved to: {output_file}")
    return output_file


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run scaden simulate")
    parser.add_argument("data_dir", help="Directory with scRNA-seq count/celltype files")
    parser.add_argument("--output_dir", default="scaden_training/", help="Output directory")
    parser.add_argument("--n_samples", type=int, default=5000, help="Number of simulated samples")
    parser.add_argument("--cells", type=int, default=500, help="Cells per simulated sample")
    parser.add_argument("--pattern", default="*_counts.txt", help="Glob pattern for count files")
    parser.add_argument("--prefix", default="data", help="Output file prefix")
    args = parser.parse_args()

    run_scaden_simulate(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        n_samples=args.n_samples,
        cells_per_sample=args.cells,
        pattern=args.pattern,
        prefix=args.prefix
    )
