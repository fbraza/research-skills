"""
Wrapper for `ananse influence` — identify key TFs driving source → target transition.

Usage:
    from scripts.run_influence import run_ananse_influence
    run_ananse_influence(
        source_network='source.network.tsv',
        target_network='target.network.tsv',
        degenes_file='deseq2_source_vs_target.tsv',
        output_file='influence.tsv',
        n_cores=8
    )
"""

import os
import subprocess
import shutil
import pandas as pd


def run_ananse_influence(
    target_network,
    degenes_file,
    source_network=None,
    output_file="ANANSE_influence.tsv",
    full_output=True,
    annotation=None,
    n_edges=100000,
    padj_cutoff=0.05,
    n_cores=4
):
    """
    Run `ananse influence` to rank TFs by their influence on the source → target transition.

    Parameters
    ----------
    target_network : str
        Path to target condition network TSV (from ananse network) — required
    degenes_file : str
        Path to DESeq2 differential expression file — required.
        Must have columns: gene, log2FoldChange, padj
        log2FoldChange must be POSITIVE for genes upregulated in TARGET
    source_network : str, optional
        Path to source condition network TSV (from ananse network)
    output_file : str
        Output influence TSV file (default: "ANANSE_influence.tsv")
    full_output : bool
        Export diffnetwork file (required for ananse plot) — default: True
    annotation : str, optional
        Gene annotation GTF for symbol conversion
    n_edges : int
        Number of top edges to use (default: 100000; try 500000 if results sparse)
    padj_cutoff : float
        Adjusted p-value cutoff for DE genes (default: 0.05)
    n_cores : int
        Number of CPU cores (default: 4)

    Returns
    -------
    dict with keys:
        - 'influence_file': path to influence.tsv
        - 'diffnetwork_file': path to influence_diffnetwork.tsv (if full_output=True)

    Raises
    ------
    RuntimeError : If ananse influence fails
    FileNotFoundError : If network or degenes files not found
    ValueError : If degenes file has wrong format

    Example
    -------
    >>> results = run_ananse_influence(
    ...     source_network='source.network.tsv',
    ...     target_network='target.network.tsv',
    ...     degenes_file='deseq2_source_vs_target.tsv',
    ...     output_file='influence.tsv',
    ...     n_cores=8
    ... )
    """
    # --- Validation ---
    _check_ananse_installed()
    _check_network_file(target_network, "target")
    if source_network:
        _check_network_file(source_network, "source")
    _validate_degenes_file(degenes_file)

    # Ensure output directory exists
    out_dir = os.path.dirname(output_file)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # --- Build command ---
    cmd = ["ananse", "influence"]
    cmd += ["-t", target_network]
    cmd += ["-d", degenes_file]

    if source_network:
        cmd += ["-s", source_network]

    cmd += ["-o", output_file]
    cmd += ["-i", str(n_edges)]
    cmd += ["-j", str(padj_cutoff)]
    cmd += ["-n", str(n_cores)]

    if full_output:
        cmd += ["-f"]

    if annotation:
        cmd += ["-a", annotation]

    # --- Run ---
    print(f"\n=== Running ananse influence ===")
    print(f"  Source network: {source_network}")
    print(f"  Target network: {target_network}")
    print(f"  DE genes file: {degenes_file}")
    print(f"  Output: {output_file}")
    print(f"  Edges: {n_edges:,}")
    print(f"  padj cutoff: {padj_cutoff}")
    print(f"  Cores: {n_cores}")
    print(f"\n  Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"ananse influence failed with exit code {result.returncode}.\n"
            "Common causes:\n"
            "  - Wrong log2FoldChange direction (must be positive for TARGET upregulated genes)\n"
            "  - NA values in padj column (filter them first)\n"
            "  - Gene symbol mismatch\n"
            "See references/troubleshooting.md for solutions."
        )

    # --- Verify output ---
    if not os.path.exists(output_file):
        raise RuntimeError(
            f"ananse influence completed but output not found: {output_file}"
        )

    # Load and summarize results
    influence = pd.read_csv(output_file, sep='\t')
    print(f"\n✓ ananse influence completed: {output_file}")
    print(f"  {len(influence)} TFs ranked")
    print(f"\n  Top 10 TFs by influence score:")
    top10 = influence.nlargest(10, 'influence_score')[['factor', 'influence_score']]
    for _, row in top10.iterrows():
        print(f"    {row['factor']:<20} {row['influence_score']:.4f}")

    # Check for diffnetwork file
    diffnetwork_file = None
    if full_output:
        # ANANSE names the diffnetwork file based on the output file
        base = output_file.replace('.tsv', '').replace('.txt', '')
        diffnetwork_file = base + "_diffnetwork.tsv"
        if os.path.exists(diffnetwork_file):
            print(f"\n✓ Diffnetwork file: {diffnetwork_file}")
        else:
            print(f"\n  ⚠ Diffnetwork file not found at expected path: {diffnetwork_file}")
            print("    Check the output directory for *_diffnetwork.tsv files")

    return {
        'influence_file': output_file,
        'diffnetwork_file': diffnetwork_file
    }


def prepare_degenes_from_deseq2(deseq2_file, output_file=None,
                                  gene_col='gene', lfc_col='log2FoldChange',
                                  padj_col='padj'):
    """
    Prepare a DESeq2 output file for use with ananse influence.

    Handles common issues:
    - Removes rows with NA padj
    - Renames columns to expected names
    - Validates log2FoldChange direction

    Parameters
    ----------
    deseq2_file : str
        Path to DESeq2 output CSV/TSV
    output_file : str, optional
        Path to save prepared file (default: degenes_for_ananse.tsv)
    gene_col : str
        Column name for gene symbols (default: 'gene')
    lfc_col : str
        Column name for log2 fold change (default: 'log2FoldChange')
    padj_col : str
        Column name for adjusted p-value (default: 'padj')

    Returns
    -------
    str : Path to prepared degenes file

    Example
    -------
    >>> degenes = prepare_degenes_from_deseq2(
    ...     'deseq2_results.csv',
    ...     output_file='degenes_for_ananse.tsv'
    ... )
    """
    sep = '\t' if deseq2_file.endswith('.tsv') else ','
    df = pd.read_csv(deseq2_file, sep=sep)

    # Handle case where gene is the index
    if gene_col not in df.columns and df.index.name == gene_col:
        df = df.reset_index()

    # Rename columns if needed
    rename_map = {}
    if gene_col != 'gene':
        rename_map[gene_col] = 'gene'
    if lfc_col != 'log2FoldChange':
        rename_map[lfc_col] = 'log2FoldChange'
    if padj_col != 'padj':
        rename_map[padj_col] = 'padj'
    if rename_map:
        df = df.rename(columns=rename_map)

    # Remove NA padj
    n_before = len(df)
    df = df.dropna(subset=['padj'])
    n_removed = n_before - len(df)
    if n_removed > 0:
        print(f"  Removed {n_removed} genes with NA padj")

    # Keep only required columns
    df = df[['gene', 'log2FoldChange', 'padj']]

    # Summary
    n_up = (df['log2FoldChange'] > 0).sum()
    n_down = (df['log2FoldChange'] < 0).sum()
    n_sig = (df['padj'] < 0.05).sum()
    print(f"  DE genes: {len(df)} total, {n_sig} significant (padj < 0.05)")
    print(f"  Upregulated (positive log2FC): {n_up}")
    print(f"  Downregulated (negative log2FC): {n_down}")
    print(f"  ⚠ Verify: positive log2FC = upregulated in TARGET condition")

    if output_file is None:
        output_file = "degenes_for_ananse.tsv"

    df.to_csv(output_file, sep='\t', index=False)
    print(f"  ✓ Saved: {output_file}")
    return output_file


def _check_ananse_installed():
    if not shutil.which("ananse"):
        raise RuntimeError(
            "ananse not found in PATH. Activate: conda activate ananse"
        )


def _check_network_file(network_file, label=""):
    if not os.path.exists(network_file):
        raise FileNotFoundError(
            f"{label} network file not found: {network_file}\n"
            "Run ananse network first."
        )
    size_mb = os.path.getsize(network_file) / (1024 * 1024)
    if size_mb < 0.1:
        raise RuntimeError(
            f"{label} network file appears empty ({size_mb:.1f} MB): {network_file}"
        )
    print(f"  ✓ {label} network: {network_file} ({size_mb:.1f} MB)")


def _validate_degenes_file(degenes_file):
    """Validate DESeq2 file format."""
    if not os.path.exists(degenes_file):
        raise FileNotFoundError(f"DE genes file not found: {degenes_file}")

    sep = '\t' if degenes_file.endswith('.tsv') else ','
    df = pd.read_csv(degenes_file, sep=sep, nrows=5)

    required_cols = ['log2FoldChange', 'padj']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(
            f"DE genes file missing required columns: {missing}\n"
            f"Found columns: {list(df.columns)}\n"
            "Use prepare_degenes_from_deseq2() to reformat your DESeq2 output."
        )

    # Check for gene column (first column or named 'gene')
    if 'gene' not in df.columns and df.columns[0] not in ['gene', 'Gene', 'GENE']:
        print(f"  ⚠ First column is '{df.columns[0]}' — ANANSE expects 'gene'")
        print("    Use prepare_degenes_from_deseq2() to rename columns.")

    print(f"  ✓ DE genes file validated: {degenes_file}")
