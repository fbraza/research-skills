"""
End-to-end ANANSE workflow runner.

Runs the complete pipeline: binding → network → influence → plot

Usage:
    from scripts.run_full_workflow import run_full_ananse_workflow
    results = run_full_ananse_workflow(
        source_atac_bams=['source_ATAC_rep1.bam', 'source_ATAC_rep2.bam'],
        source_rna_tpm=['source_rep1_TPM.txt', 'source_rep2_TPM.txt'],
        target_atac_bams=['target_ATAC_rep1.bam', 'target_ATAC_rep2.bam'],
        target_rna_tpm=['target_rep1_TPM.txt', 'target_rep2_TPM.txt'],
        degenes_file='deseq2_source_vs_target.tsv',
        output_dir='ananse_results',
        genome='hg38',
        remap_dir='/path/to/ANANSE.REMAP.model.v1.0',
        n_cores=8
    )
"""

import os
import time

from scripts.run_binding import run_ananse_binding
from scripts.run_network import run_ananse_network
from scripts.run_influence import run_ananse_influence
from scripts.plot_results import plot_influence_results
from scripts.export_results import export_ananse_results


def run_full_ananse_workflow(
    source_atac_bams,
    source_rna_tpm,
    target_atac_bams,
    target_rna_tpm,
    degenes_file,
    output_dir="ananse_results",
    genome="hg38",
    source_h3k27ac_bams=None,
    target_h3k27ac_bams=None,
    regions=None,
    remap_dir=None,
    n_edges=100000,
    padj_cutoff=0.05,
    n_tfs_plot=20,
    n_cores=8,
    skip_plot=False
):
    """
    Run the complete ANANSE pipeline from BAMs + TPM to ranked TFs.

    Steps:
    1. ananse binding (source condition)
    2. ananse binding (target condition)
    3. ananse network (source condition)
    4. ananse network (target condition)
    5. ananse influence (source → target)
    6. ananse plot (visualization)
    7. export results

    Parameters
    ----------
    source_atac_bams : list of str
        ATAC-seq BAM(s) for source condition
    source_rna_tpm : list of str
        RNA-seq TPM file(s) for source condition
    target_atac_bams : list of str
        ATAC-seq BAM(s) for target condition
    target_rna_tpm : list of str
        RNA-seq TPM file(s) for target condition
    degenes_file : str
        DESeq2 output file (gene, log2FoldChange, padj)
        log2FoldChange must be POSITIVE for TARGET upregulated genes
    output_dir : str
        Root output directory (default: "ananse_results")
    genome : str
        Genome name or FASTA path (default: "hg38")
    source_h3k27ac_bams : list of str, optional
        H3K27ac ChIP-seq BAM(s) for source condition
    target_h3k27ac_bams : list of str, optional
        H3K27ac ChIP-seq BAM(s) for target condition
    regions : list of str, optional
        Enhancer region BED/narrowPeak file(s) (union of all conditions)
    remap_dir : str, optional
        Path to REMAP model directory (hg38 only, strongly recommended)
    n_edges : int
        Number of top edges for influence (default: 100000)
    padj_cutoff : float
        padj cutoff for DE genes (default: 0.05)
    n_tfs_plot : int
        Number of top TFs to plot (default: 20)
    n_cores : int
        Number of CPU cores (default: 8)
    skip_plot : bool
        Skip plotting step (default: False)

    Returns
    -------
    dict with keys:
        - 'source_binding': path to source binding.h5
        - 'target_binding': path to target binding.h5
        - 'source_network': path to source network.tsv
        - 'target_network': path to target network.tsv
        - 'influence_file': path to influence.tsv
        - 'diffnetwork_file': path to influence_diffnetwork.tsv
        - 'output_dir': root output directory

    Example
    -------
    >>> from scripts.load_example_data import setup_example_data
    >>> paths = setup_example_data()
    >>> results = run_full_ananse_workflow(
    ...     source_atac_bams=paths['source_atac'],
    ...     source_rna_tpm=paths['source_rna'],
    ...     target_atac_bams=paths['target_atac'],
    ...     target_rna_tpm=paths['target_rna'],
    ...     degenes_file=paths['degenes'],
    ...     remap_dir=paths['remap_model'],
    ...     output_dir='ananse_results',
    ...     n_cores=8
    ... )
    """
    start_time = time.time()
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("ANANSE Full Workflow")
    print("=" * 60)
    print(f"Output directory: {output_dir}")
    print(f"Genome: {genome}")
    print(f"Cores: {n_cores}")
    print(f"REMAP model: {remap_dir}")
    print()

    results = {'output_dir': output_dir}

    # --- Step 1: Source binding ---
    print(f"[1/6] Source binding prediction...")
    source_binding_dir = os.path.join(output_dir, "source.binding")
    source_binding_h5 = run_ananse_binding(
        atac_bams=source_atac_bams,
        h3k27ac_bams=source_h3k27ac_bams,
        output_dir=source_binding_dir,
        genome=genome,
        regions=regions,
        remap_dir=remap_dir,
        n_cores=n_cores
    )
    results['source_binding'] = source_binding_h5

    # --- Step 2: Target binding ---
    print(f"\n[2/6] Target binding prediction...")
    target_binding_dir = os.path.join(output_dir, "target.binding")
    target_binding_h5 = run_ananse_binding(
        atac_bams=target_atac_bams,
        h3k27ac_bams=target_h3k27ac_bams,
        output_dir=target_binding_dir,
        genome=genome,
        regions=regions,
        remap_dir=remap_dir,
        n_cores=n_cores
    )
    results['target_binding'] = target_binding_h5

    # --- Step 3: Source network ---
    print(f"\n[3/6] Source GRN inference (⚠ requires ~12-15 GB RAM)...")
    source_network = os.path.join(output_dir, "source.network.tsv")
    run_ananse_network(
        binding_h5=source_binding_h5,
        expression_files=source_rna_tpm,
        output_file=source_network,
        genome=genome,
        n_cores=n_cores
    )
    results['source_network'] = source_network

    # --- Step 4: Target network ---
    print(f"\n[4/6] Target GRN inference (⚠ requires ~12-15 GB RAM)...")
    target_network = os.path.join(output_dir, "target.network.tsv")
    run_ananse_network(
        binding_h5=target_binding_h5,
        expression_files=target_rna_tpm,
        output_file=target_network,
        genome=genome,
        n_cores=n_cores
    )
    results['target_network'] = target_network

    # --- Step 5: Influence ---
    print(f"\n[5/6] Influence score calculation...")
    influence_file = os.path.join(output_dir, "influence.tsv")
    influence_results = run_ananse_influence(
        source_network=source_network,
        target_network=target_network,
        degenes_file=degenes_file,
        output_file=influence_file,
        full_output=True,
        n_edges=n_edges,
        padj_cutoff=padj_cutoff,
        n_cores=n_cores
    )
    results['influence_file'] = influence_results['influence_file']
    results['diffnetwork_file'] = influence_results['diffnetwork_file']

    # --- Step 6: Plot ---
    if not skip_plot:
        print(f"\n[6/6] Generating plots...")
        plots_dir = os.path.join(output_dir, "plots")
        plot_influence_results(
            influence_file=influence_results['influence_file'],
            diffnetwork_file=influence_results['diffnetwork_file'],
            output_dir=plots_dir,
            n_tfs=n_tfs_plot
        )
        results['plots_dir'] = plots_dir

    # --- Export ---
    print(f"\nExporting results...")
    export_dir = os.path.join(output_dir, "results")
    export_ananse_results(
        influence_file=influence_results['influence_file'],
        source_network=source_network,
        target_network=target_network,
        output_dir=export_dir
    )
    results['export_dir'] = export_dir

    # --- Summary ---
    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print("ANANSE Workflow Complete")
    print("=" * 60)
    print(f"Total runtime: {elapsed/60:.1f} minutes")
    print(f"\nOutput files:")
    for key, val in results.items():
        if val and isinstance(val, str) and os.path.exists(val):
            print(f"  {key}: {val}")
    print()

    return results
