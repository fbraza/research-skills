"""
Download and set up ANANSE example data (fibroblast → heart transition).

Official example data from: https://zenodo.org/record/4769814
REMAP model from: https://zenodo.org/record/4768075

Usage:
    from scripts.load_example_data import setup_example_data
    paths = setup_example_data(output_dir="ananse_example")
"""

import os
import subprocess
import sys


def setup_example_data(output_dir="ananse_example", download_remap=True):
    """
    Download and set up ANANSE example data and REMAP model.

    Parameters
    ----------
    output_dir : str
        Directory to store example data (default: "ananse_example")
    download_remap : bool
        Whether to download the REMAP model (hg38 only, ~2GB, default: True)

    Returns
    -------
    dict with keys:
        - 'source_atac': list of source ATAC-seq BAM paths
        - 'source_h3k27ac': list of source H3K27ac BAM paths
        - 'source_rna': list of source RNA-seq TPM paths
        - 'target_atac': list of target ATAC-seq BAM paths
        - 'target_h3k27ac': list of target H3K27ac BAM paths
        - 'target_rna': list of target RNA-seq TPM paths
        - 'degenes': path to DESeq2 differential expression file
        - 'remap_model': path to REMAP model directory (or None)

    Example
    -------
    >>> paths = setup_example_data(output_dir="ananse_example")
    >>> print(paths['source_atac'])
    ['ananse_example/ANANSE_example_data/ATAC/fibroblast_ATAC_rep1.bam', ...]
    """
    os.makedirs(output_dir, exist_ok=True)

    # --- Download example data ---
    example_data_dir = os.path.join(output_dir, "ANANSE_example_data")
    if not os.path.exists(example_data_dir):
        print("Downloading ANANSE example data (~500 MB)...")
        tgz = os.path.join(output_dir, "ANANSE_example_data.tgz")
        _run_cmd(
            f"wget -q https://zenodo.org/record/4769814/files/ANANSE_example_data.tgz "
            f"-O {tgz}",
            "Downloading example data"
        )
        _run_cmd(
            f"tar xvzf {tgz} -C {output_dir}",
            "Extracting example data"
        )
        os.remove(tgz)
        print(f"✓ Example data extracted to: {example_data_dir}")
    else:
        print(f"✓ Example data already present: {example_data_dir}")

    # --- Download REMAP model ---
    remap_dir = None
    if download_remap:
        remap_dir = os.path.join(output_dir, "ANANSE.REMAP.model.v1.0")
        if not os.path.exists(remap_dir) or not os.listdir(remap_dir):
            print("Downloading REMAP model (~2 GB)...")
            os.makedirs(remap_dir, exist_ok=True)
            tgz = os.path.join(output_dir, "ANANSE.REMAP.model.v1.0.tgz")
            _run_cmd(
                f"wget -q https://zenodo.org/record/4768075/files/ANANSE.REMAP.model.v1.0.tgz "
                f"-O {tgz}",
                "Downloading REMAP model"
            )
            _run_cmd(
                f"tar xvzf {tgz} -C {remap_dir}",
                "Extracting REMAP model"
            )
            os.remove(tgz)
            print(f"✓ REMAP model extracted to: {remap_dir}")
        else:
            print(f"✓ REMAP model already present: {remap_dir}")

    # --- Build paths dict ---
    atac_dir = os.path.join(example_data_dir, "ATAC")
    h3k27ac_dir = os.path.join(example_data_dir, "H3K27ac")
    rna_dir = os.path.join(example_data_dir, "RNAseq")

    paths = {
        'source_atac': [
            os.path.join(atac_dir, "fibroblast_ATAC_rep1.bam"),
            os.path.join(atac_dir, "fibroblast_ATAC_rep2.bam"),
        ],
        'source_h3k27ac': [
            os.path.join(h3k27ac_dir, "fibroblast_H3K27ac_rep1.bam"),
        ],
        'source_rna': [
            os.path.join(rna_dir, "fibroblast_rep1_TPM.txt"),
            os.path.join(rna_dir, "fibroblast_rep2_TPM.txt"),
        ],
        'target_atac': [
            os.path.join(atac_dir, "heart_ATAC_rep1.bam"),
            os.path.join(atac_dir, "heart_ATAC_rep2.bam"),
        ],
        'target_h3k27ac': [
            os.path.join(h3k27ac_dir, "heart_H3K27ac_rep1.bam"),
        ],
        'target_rna': [
            os.path.join(rna_dir, "heart_rep1_TPM.txt"),
            os.path.join(rna_dir, "heart_rep2_TPM.txt"),
        ],
        'degenes': os.path.join(rna_dir, "fibroblast2heart_degenes.csv"),
        'remap_model': remap_dir,
    }

    # --- Validate files exist ---
    print("\nValidating example data files...")
    all_ok = True
    for key, val in paths.items():
        if val is None:
            continue
        files = val if isinstance(val, list) else [val]
        for f in files:
            if os.path.exists(f):
                print(f"  ✓ {os.path.basename(f)}")
            else:
                print(f"  ✗ MISSING: {f}")
                all_ok = False

    if all_ok:
        print("\n✓ All example data files present and ready.")
    else:
        print("\n⚠ Some files are missing. Check download logs above.")

    return paths


def validate_input_files(paths):
    """
    Validate that all input files in a paths dict exist and are non-empty.

    Parameters
    ----------
    paths : dict
        Dictionary with keys: source_atac, source_rna, target_atac, target_rna, degenes

    Returns
    -------
    bool : True if all files valid, False otherwise
    """
    print("Validating input files...")
    all_ok = True

    required_keys = ['source_atac', 'source_rna', 'target_atac', 'target_rna', 'degenes']
    for key in required_keys:
        if key not in paths:
            print(f"  ✗ Missing key: {key}")
            all_ok = False
            continue
        files = paths[key] if isinstance(paths[key], list) else [paths[key]]
        for f in files:
            if not os.path.exists(f):
                print(f"  ✗ File not found: {f}")
                all_ok = False
            elif os.path.getsize(f) == 0:
                print(f"  ✗ File is empty: {f}")
                all_ok = False
            else:
                print(f"  ✓ {os.path.basename(f)} ({_human_size(os.path.getsize(f))})")

    # Check BAM index files
    for key in ['source_atac', 'target_atac', 'source_h3k27ac', 'target_h3k27ac']:
        if key not in paths:
            continue
        bams = paths[key] if isinstance(paths[key], list) else [paths[key]]
        for bam in bams:
            if bam and os.path.exists(bam):
                bai = bam + ".bai"
                if not os.path.exists(bai):
                    print(f"  ⚠ BAM index missing: {bai}")
                    print(f"    Run: samtools index {bam}")
                    all_ok = False

    if all_ok:
        print("✓ All input files validated successfully.")
    else:
        print("⚠ Some input files have issues. See messages above.")

    return all_ok


def _run_cmd(cmd, description=""):
    """Run a shell command and raise on failure."""
    if description:
        print(f"  {description}...")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr}")
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result


def _human_size(size_bytes):
    """Convert bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
