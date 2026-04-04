"""
Wrapper for `ananse binding` — TF binding prediction from ATAC-seq and/or H3K27ac.

Usage:
    from scripts.run_binding import run_ananse_binding
    run_ananse_binding(
        atac_bams=['source_ATAC_rep1.bam', 'source_ATAC_rep2.bam'],
        h3k27ac_bams=['source_H3K27ac_rep1.bam'],
        output_dir='source.binding',
        genome='hg38',
        remap_dir='/path/to/ANANSE.REMAP.model.v1.0',
        n_cores=8
    )
"""

import os
import subprocess
import shutil


def run_ananse_binding(
    atac_bams=None,
    h3k27ac_bams=None,
    output_dir="ANANSE_binding",
    genome="hg38",
    regions=None,
    pfmfile=None,
    remap_dir=None,
    columns=None,
    pfmscorefile=None,
    tfs=None,
    jaccard_cutoff=0.1,
    n_cores=4
):
    """
    Run `ananse binding` to predict TF binding probabilities at enhancers.

    Parameters
    ----------
    atac_bams : list of str, optional
        ATAC-seq BAM file(s) or path to counts table TSV.
        Multiple BAMs are treated as replicates (averaged).
    h3k27ac_bams : list of str, optional
        H3K27ac ChIP-seq BAM file(s) or path to counts table TSV.
        Optional but improves prediction accuracy.
    output_dir : str
        Output directory for binding.h5 (default: "ANANSE_binding")
    genome : str
        Genome name (genomepy) or path to FASTA (default: "hg38")
    regions : list of str, optional
        Enhancer region BED/narrowPeak file(s). Not needed for hg38 with REMAP.
        Use UNION of peaks from all conditions.
    pfmfile : str, optional
        Path to motif PFM file. Default: gimme.vertebrate.v5.0
    remap_dir : str, optional
        Path to REMAP model directory (hg38 only, strongly recommended)
    columns : list of str, optional
        Column names to extract from counts table(s)
    pfmscorefile : str, optional
        Path to precomputed motif scores (from `gimme scan -Tz --gc`)
    tfs : list of str, optional
        Filter to specific TFs (default: all)
    jaccard_cutoff : float
        Min motif similarity for model sharing (default: 0.1)
    n_cores : int
        Number of CPU cores (default: 4)

    Returns
    -------
    str : Path to output binding.h5 file

    Raises
    ------
    RuntimeError : If ananse binding fails or output not created
    ValueError : If neither atac_bams nor h3k27ac_bams provided

    Example
    -------
    >>> run_ananse_binding(
    ...     atac_bams=['source_ATAC_rep1.bam', 'source_ATAC_rep2.bam'],
    ...     h3k27ac_bams=['source_H3K27ac_rep1.bam'],
    ...     output_dir='source.binding',
    ...     genome='hg38',
    ...     remap_dir='/data/ANANSE.REMAP.model.v1.0',
    ...     n_cores=8
    ... )
    """
    # --- Validation ---
    if not atac_bams and not h3k27ac_bams:
        raise ValueError("At least one of atac_bams or h3k27ac_bams must be provided.")

    _check_ananse_installed()

    if atac_bams:
        _validate_bam_files(atac_bams, "ATAC-seq")
    if h3k27ac_bams:
        _validate_bam_files(h3k27ac_bams, "H3K27ac")

    os.makedirs(output_dir, exist_ok=True)

    # --- Build command ---
    cmd = ["ananse", "binding"]

    if atac_bams:
        bams = atac_bams if isinstance(atac_bams, list) else [atac_bams]
        cmd += ["-A"] + bams

    if h3k27ac_bams:
        bams = h3k27ac_bams if isinstance(h3k27ac_bams, list) else [h3k27ac_bams]
        cmd += ["-H"] + bams

    cmd += ["-g", genome]

    if remap_dir:
        if not os.path.exists(remap_dir):
            print(f"  ⚠ REMAP model directory not found: {remap_dir}")
            print("    Download from: https://zenodo.org/record/4768075")
            print("    Continuing without REMAP model (lower accuracy)...")
        else:
            cmd += ["-R", remap_dir]

    if regions:
        region_list = regions if isinstance(regions, list) else [regions]
        cmd += ["-r"] + region_list

    if pfmfile:
        cmd += ["-p", pfmfile]

    if pfmscorefile:
        cmd += ["--pfmscorefile", pfmscorefile]

    if columns:
        col_list = columns if isinstance(columns, list) else [columns]
        cmd += ["-c"] + col_list

    if tfs:
        tf_list = tfs if isinstance(tfs, list) else [tfs]
        cmd += ["-t"] + tf_list

    cmd += ["--jaccard-cutoff", str(jaccard_cutoff)]
    cmd += ["-o", output_dir]
    cmd += ["-n", str(n_cores)]

    # --- Run ---
    print(f"\n=== Running ananse binding ===")
    print(f"  Output directory: {output_dir}")
    print(f"  Genome: {genome}")
    print(f"  ATAC BAMs: {atac_bams}")
    print(f"  H3K27ac BAMs: {h3k27ac_bams}")
    print(f"  REMAP model: {remap_dir}")
    print(f"  Cores: {n_cores}")
    print(f"\n  Command: {' '.join(cmd)}\n")

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        raise RuntimeError(
            f"ananse binding failed with exit code {result.returncode}.\n"
            "Check the output above for error messages.\n"
            "See references/troubleshooting.md for solutions."
        )

    # --- Verify output ---
    binding_h5 = os.path.join(output_dir, "binding.h5")
    if not os.path.exists(binding_h5):
        raise RuntimeError(
            f"ananse binding completed but binding.h5 not found at: {binding_h5}\n"
            "This may indicate a silent failure. Check logs above."
        )

    size_mb = os.path.getsize(binding_h5) / (1024 * 1024)
    print(f"\n✓ ananse binding completed: {binding_h5} ({size_mb:.1f} MB)")
    return binding_h5


def _check_ananse_installed():
    """Check that ananse is available in PATH."""
    if not shutil.which("ananse"):
        raise RuntimeError(
            "ananse not found in PATH.\n"
            "Activate the conda environment: conda activate ananse\n"
            "Or install: conda create -n ananse ananse"
        )


def _validate_bam_files(bam_files, label=""):
    """Check BAM files exist and are indexed."""
    files = bam_files if isinstance(bam_files, list) else [bam_files]
    for bam in files:
        if not os.path.exists(bam):
            raise FileNotFoundError(f"{label} BAM file not found: {bam}")
        # Check for index (only for actual BAM files, not counts tables)
        if bam.endswith(".bam"):
            bai = bam + ".bai"
            if not os.path.exists(bai):
                print(f"  ⚠ BAM index missing: {bai}")
                print(f"    Attempting to index: samtools index {bam}")
                result = subprocess.run(
                    ["samtools", "index", bam],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    raise RuntimeError(
                        f"Failed to index BAM: {bam}\n"
                        f"Run manually: samtools sort -o sorted.bam {bam} && samtools index sorted.bam"
                    )
                print(f"  ✓ BAM indexed: {bai}")
