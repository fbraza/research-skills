"""
load_example_data.py — Generate Scaden example data for pipeline testing.

Uses Scaden's built-in `scaden example` command to generate synthetic
count, celltype, and bulk expression files for testing the full pipeline.

Parameters
----------
out_dir : str
    Directory to write example files (default: "scaden_example/")

Returns
-------
dict with keys:
    counts_file : str — path to example_counts.txt
    celltypes_file : str — path to example_celltypes.txt
    bulk_file : str — path to example_bulk_data.txt

Example
-------
    from scripts.load_example_data import generate_example_data
    paths = generate_example_data(out_dir="scaden_example/")
    print(paths)
"""

import os
import subprocess
import sys


def generate_example_data(out_dir: str = "scaden_example/") -> dict:
    """
    Generate Scaden example data using the built-in `scaden example` command.

    Parameters
    ----------
    out_dir : str
        Output directory for example files.

    Returns
    -------
    dict
        Paths to generated files: counts_file, celltypes_file, bulk_file.
    """
    os.makedirs(out_dir, exist_ok=True)

    print(f"Generating Scaden example data in: {out_dir}")

    result = subprocess.run(
        ["scaden", "example", "--out", out_dir],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"[ERROR] scaden example failed:\n{result.stderr}")
        sys.exit(1)

    counts_file = os.path.join(out_dir, "example_counts.txt")
    celltypes_file = os.path.join(out_dir, "example_celltypes.txt")
    bulk_file = os.path.join(out_dir, "example_bulk_data.txt")

    # Verify files were created
    for f in [counts_file, celltypes_file, bulk_file]:
        if not os.path.exists(f):
            print(f"[ERROR] Expected file not found: {f}")
            sys.exit(1)

    # Report basic stats
    import pandas as pd
    counts = pd.read_csv(counts_file, sep="\t", index_col=0)
    celltypes = pd.read_csv(celltypes_file, sep="\t")
    bulk = pd.read_csv(bulk_file, sep="\t", index_col=0)

    print(f"✓ Example data generated successfully")
    print(f"  scRNA-seq counts: {counts.shape[0]} cells × {counts.shape[1]} genes")
    print(f"  Cell types: {celltypes['Celltype'].unique().tolist()}")
    print(f"  Bulk data: {bulk.shape[0]} genes × {bulk.shape[1]} samples")

    return {
        "counts_file": counts_file,
        "celltypes_file": celltypes_file,
        "bulk_file": bulk_file,
        "out_dir": out_dir
    }


def inspect_example_data(paths: dict) -> None:
    """
    Print a summary of the example data files.

    Parameters
    ----------
    paths : dict
        Output from generate_example_data().
    """
    import pandas as pd

    print("\n=== Example Data Summary ===")

    counts = pd.read_csv(paths["counts_file"], sep="\t", index_col=0)
    print(f"\nCount matrix ({paths['counts_file']}):")
    print(f"  Shape: {counts.shape[0]} cells × {counts.shape[1]} genes")
    print(f"  Value range: {counts.values.min():.1f} – {counts.values.max():.1f}")
    print(f"  First 3 genes: {counts.columns[:3].tolist()}")

    celltypes = pd.read_csv(paths["celltypes_file"], sep="\t")
    print(f"\nCell type labels ({paths['celltypes_file']}):")
    print(f"  Total cells: {len(celltypes)}")
    print(f"  Cell types: {celltypes['Celltype'].value_counts().to_dict()}")

    bulk = pd.read_csv(paths["bulk_file"], sep="\t", index_col=0)
    print(f"\nBulk expression ({paths['bulk_file']}):")
    print(f"  Shape: {bulk.shape[0]} genes × {bulk.shape[1]} samples")
    print(f"  Sample names: {bulk.columns.tolist()}")


if __name__ == "__main__":
    paths = generate_example_data()
    inspect_example_data(paths)
