"""
Wrapper for `ananse network` — GRN inference from binding predictions and expression data.

⚠️ Memory requirement: ~12–15 GB RAM for human genome.

Usage:
    from scripts.run_network import run_ananse_network
    run_ananse_network(
        binding_h5='source.binding/binding.h5',
        expression_files=['source_rep1_TPM.txt', 'source_rep2_TPM.txt'],
        output_file='source.network.tsv',
        genome='hg38',
        n_cores=8
    )
"""

import os
import subprocess
import shutil
import psutil


def run_ananse_network(
    binding_h5,
    expression_files,
    output_file="ANANSE_network.tsv",
    genome="hg38",
    annotation=None,
    columns=None,
    tfs=None,
    regions=None,
    full_output=False,
    include_promoter=True,
    include_enhancer=True,
    n_cores=4
):
    """
    Run `ananse network` to infer a condition-specific GRN.

    Parameters
    ----------
    binding_h5 : str
        Path to binding.h5 from `ananse binding` (required)
    expression_files : list of str or str
        Expression file(s) in TPM. Can be:
        - Salmon quant.sf files
        - Kallisto abundances.tsv files
        - Counts table TSV (genes × samples, TPM values)
        Multiple files = replicates (averaged)
    output_file : str
        Output network TSV file (default: "ANANSE_network.tsv")
    genome : str
        Genome name (genomepy) or FASTA path (default: "hg38")
    annotation : str, optional
        Gene annotation BED12 file (required if not using genomepy genome)
    columns : list of str, optional
        Column name(s) to extract from expression table (default: "tpm")
    tfs : list of str, optional
        Filter to specific TFs (default: all)
    regions : str, optional
        Filter to specific regions BED file (default: all)
    full_output : bool
        Export all 4 score components (default: False)
    include_promoter : bool
        Include peaks ≤ TSS ± 2kb (default: True)
    include_enhancer : bool
        Include peaks > TSS ± 2kb (default: True)
    n_cores : int
        Number of CPU cores (default: 4)

    Returns
    -------
    str : Path to output network TSV file

    Raises
    ------
    RuntimeError : If ananse network fails or output not created
    FileNotFoundError : If binding_h5 or expression files not found
    MemoryWarning : If available RAM < 12 GB

    Example
    -------
    >>> run_ananse_network(
    ...     binding_h5='source.binding/binding.h5',
    ...     expression_files=['source_rep1_TPM.txt', 'source_rep2_TPM.txt'],
    ...     output_file='source.network.tsv',
    ...     genome='hg38',
    ...     n_cores=8
    ... )
    """
    # --- Validation ---
    _check_ananse_installed()
    _check_binding_h5(binding_h5)
    _check_expression_files(expression_files)
    _check_memory()

    # Ensure output directory exists
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # --- Build command ---
    cmd = ["ananse", "network", binding_h5]

    expr_files = expression_files if isinstance(expression_files, list) else [expression_files]
    cmd += ["-e"] + expr_files

    cmd += ["-g", genome]

    if annotation:
        cmd += ["-a", annotation]

    if columns:
        col_list = columns if isinstance(columns, list) else [columns]
        cmd += ["-c"] + col_list

    if tfs:
        tf_list = tfs if isinstance(tfs, list) else [tfs]
        cmd += ["-t"] + tf_list

    if regions:
        cmd += ["-r", regions]

    if full_output:
        cmd += ["-f"]

    if not include_promoter:
        cmd += ["--exclude-promoter"]

    if not include_enhancer:
        cmd += ["--exclude-enhancer"]

    cmd += ["-o", output_file]
    cmd += ["-n", str(n_cores)]

    # --- Run ---
    print(f"\n=== Running ananse network ===")
    print(f"  Binding file: {binding_h5}")
    print(f"  Expression files: {expr_files}")
    print(f"  Output: {output_file}")
    print(f"  Genome: {genome}")
    print(f"  Cores: {n_cores}")
    print(f"  ⚠ Memory requirement: ~12–15 GB RAM")
    print(f"\n  Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"ananse network failed with exit code {result.returncode}.\n"
            "Common causes:\n"
            "  - Insufficient RAM (need ≥12 GB free)\n"
            "  - Gene symbol mismatch between expression file and motif database\n"
            "  - Genome annotation not found\n"
            "See references/troubleshooting.md for solutions."
        )

    # --- Verify output ---
    if not os.path.exists(output_file):
        raise RuntimeError(
            f"ananse network completed but output not found: {output_file}\n"
            "This may indicate a silent failure. Check logs above."
        )

    size_mb = os.path.getsize(output_file) / (1024 * 1024)
    print(f"\n✓ ananse network completed: {output_file} ({size_mb:.1f} MB)")

    # Quick sanity check on output
    with open(output_file) as f:
        n_lines = sum(1 for _ in f)
    print(f"  Network contains {n_lines - 1:,} TF-gene interactions")

    if n_lines < 100:
        print("  ⚠ WARNING: Very few interactions found. Check gene symbol matching.")
        print("    Run: ananse view binding.h5 -lt | head -5")
        print("    Compare with gene names in your expression file.")

    return output_file


def _check_ananse_installed():
    """Check that ananse is available in PATH."""
    if not shutil.which("ananse"):
        raise RuntimeError(
            "ananse not found in PATH.\n"
            "Activate the conda environment: conda activate ananse"
        )


def _check_binding_h5(binding_h5):
    """Check binding.h5 exists and is non-empty."""
    if not os.path.exists(binding_h5):
        raise FileNotFoundError(
            f"binding.h5 not found: {binding_h5}\n"
            "Run ananse binding first."
        )
    size_mb = os.path.getsize(binding_h5) / (1024 * 1024)
    if size_mb < 1:
        raise RuntimeError(
            f"binding.h5 appears empty ({size_mb:.1f} MB): {binding_h5}\n"
            "The binding step may have failed. Re-run ananse binding."
        )
    print(f"  ✓ binding.h5 found ({size_mb:.1f} MB)")


def _check_expression_files(expression_files):
    """Check expression files exist."""
    files = expression_files if isinstance(expression_files, list) else [expression_files]
    for f in files:
        if not os.path.exists(f):
            raise FileNotFoundError(f"Expression file not found: {f}")
    print(f"  ✓ {len(files)} expression file(s) found")


def _check_memory():
    """Warn if available RAM < 12 GB."""
    try:
        available_gb = psutil.virtual_memory().available / (1024 ** 3)
        if available_gb < 12:
            print(f"\n  ⚠ WARNING: Only {available_gb:.1f} GB RAM available.")
            print("    ananse network requires ~12–15 GB. This may fail or be very slow.")
            print("    Close other processes or use a machine with more RAM.")
        else:
            print(f"  ✓ Available RAM: {available_gb:.1f} GB")
    except ImportError:
        print("  (psutil not available — cannot check RAM)")
