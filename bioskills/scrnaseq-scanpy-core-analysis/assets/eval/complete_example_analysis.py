"""
Complete Scanpy scRNA-seq Analysis Example — PBMC 3k Dataset
=============================================================

This script demonstrates a complete end-to-end single-cell RNA-seq analysis
using the PBMC 3k dataset from 10X Genomics, following the scrnaseq-scanpy-core-analysis
workflow exactly.

For dataset info: https://support.10xgenomics.com/single-cell-gene-expression/datasets/1.1.0/pbmc3k

Expected runtime: ~10-20 minutes on a standard laptop (first run downloads data ~50MB)
Expected output:  ~2,700 cells, 8-10 clusters, UMAP + marker gene plots

Usage:
    # From the workflow root directory:
    python assets/eval/complete_example_analysis.py

    # With custom output directory:
    python assets/eval/complete_example_analysis.py --output-dir my_results/
"""

import os
import sys
import argparse

# ── Path setup: add scripts/ to Python path ───────────────────────────────────
EVAL_DIR   = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR  = os.path.join(EVAL_DIR, "..", "..")
SCRIPT_DIR = os.path.join(SKILL_DIR, "scripts")
sys.path.insert(0, SCRIPT_DIR)

# ── Default output directory ──────────────────────────────────────────────────
DEFAULT_OUTPUT = os.path.join(SKILL_DIR, "results", "pbmc3k_example")


def run_complete_analysis(output_dir: str = DEFAULT_OUTPUT):
    """
    Run the complete scanpy workflow on PBMC 3k data.

    Steps:
        1. Load PBMC 3k example data
        2. QC metrics, MAD-based filtering, doublet detection
        3. Normalization, HVG selection, PCA
        4. Neighbor graph, Leiden clustering, UMAP
        5. Marker gene detection, cell type annotation
        6. Export results (AnnData, CSVs, plots)
    """

    os.makedirs(output_dir, exist_ok=True)
    print("=" * 70)
    print("COMPLETE SCANPY ANALYSIS — PBMC 3k")
    print("=" * 70)
    print(f"Output directory: {output_dir}\n")

    # ── STEP 1: Load example data ─────────────────────────────────────────────
    print("\n[Step 1] Loading PBMC 3k example data...")
    print("-" * 50)

    from load_example_data import load_example_data
    adata = load_example_data("pbmc3k")
    # Expected: AnnData object with ~2,700 cells × 32,738 genes
    print(f"  Loaded: {adata.n_obs} cells × {adata.n_vars} genes")

    # ── STEP 2: QC metrics, filtering, doublet detection ─────────────────────
    print("\n[Step 2] Quality control...")
    print("-" * 50)

    from qc_metrics import calculate_qc_metrics, batch_mad_outlier_detection
    from filter_cells import run_scrublet_detection, filter_by_mad_outliers

    # Calculate QC metrics (n_genes, total_counts, pct_counts_mt)
    adata = calculate_qc_metrics(adata, species="human")

    # MAD-based adaptive outlier detection (no hard thresholds)
    adata = batch_mad_outlier_detection(adata, batch_key=None)

    # Doublet detection with Scrublet
    adata = run_scrublet_detection(adata, batch_key=None)

    # Apply filters
    n_before = adata.n_obs
    adata = filter_by_mad_outliers(adata, remove_doublets=True)
    n_after = adata.n_obs
    retention = 100 * n_after / n_before
    print(f"  Retained {n_after}/{n_before} cells ({retention:.1f}%)")
    # Expected: ~2,600-2,700 cells retained (>95%)

    # ── STEP 3: Normalize, HVG, scale, PCA ───────────────────────────────────
    print("\n[Step 3] Normalization, HVG selection, PCA...")
    print("-" * 50)

    from normalize_data import run_standard_normalization
    from find_variable_genes import find_highly_variable_genes
    from scale_and_pca import scale_data, run_pca_analysis, suggest_n_pcs

    # Normalize to 10,000 counts per cell + log1p
    adata = run_standard_normalization(adata, target_sum=1e4)

    # Select 2,000 highly variable genes
    adata = find_highly_variable_genes(adata, n_top_genes=2000)

    # Scale (regress out total_counts and pct_counts_mt)
    adata = scale_data(adata, vars_to_regress=["total_counts", "pct_counts_mt"])

    # PCA (50 components)
    adata = run_pca_analysis(adata, n_pcs=50)

    # Get recommended number of PCs for downstream steps
    n_pcs_recommended = suggest_n_pcs(adata)
    print(f"  Recommended PCs for clustering: {n_pcs_recommended}")
    # Expected: typically 10-20 PCs for PBMC 3k

    # ── STEP 4: Neighbor graph, clustering, UMAP ─────────────────────────────
    print("\n[Step 4] Neighbor graph, Leiden clustering, UMAP...")
    print("-" * 50)

    from cluster_cells import build_neighbor_graph, cluster_leiden_multiple_resolutions
    from run_umap import run_umap_reduction
    from plot_dimreduction import plot_umap_clusters

    # Build neighbor graph using PCA embedding
    adata = build_neighbor_graph(
        adata,
        use_rep="X_pca",
        n_neighbors=10,
        n_pcs=n_pcs_recommended
    )

    # Cluster at multiple resolutions (0.4, 0.6, 0.8, 1.0)
    adata = cluster_leiden_multiple_resolutions(
        adata,
        resolutions=[0.4, 0.6, 0.8, 1.0]
    )

    # UMAP for visualization
    adata = run_umap_reduction(adata)

    # Plot UMAP colored by clusters (resolution 0.8 is default)
    plot_umap_clusters(
        adata,
        cluster_key="leiden_0.8",
        output_dir=os.path.join(output_dir, "umap")
    )
    n_clusters = adata.obs["leiden_0.8"].nunique()
    print(f"  Clusters at resolution 0.8: {n_clusters}")
    # Expected: 8-10 clusters for PBMC 3k

    # ── STEP 5: Marker genes and cell type annotation ─────────────────────────
    print("\n[Step 5] Marker gene detection and cell type annotation...")
    print("-" * 50)

    from find_markers import find_all_cluster_markers
    from annotate_celltypes import annotate_celltypes_from_markers
    from plot_dimreduction import plot_umap_gene_expression

    # Find marker genes for each cluster (Wilcoxon rank-sum test)
    markers = find_all_cluster_markers(
        adata,
        cluster_key="leiden_0.8",
        n_genes=25,
        method="wilcoxon"
    )
    print(f"  Marker genes found for {len(markers['cluster'].unique())} clusters")

    # Annotate cell types using known PBMC marker genes
    # (CD3D=T cells, MS4A1=B cells, LYZ=Monocytes, GNLY=NK cells, etc.)
    adata = annotate_celltypes_from_markers(
        adata,
        markers=markers,
        cluster_key="leiden_0.8",
        species="human",
        tissue="PBMC"
    )

    # Plot UMAP with cell type annotations
    plot_umap_clusters(
        adata,
        cluster_key="cell_type",
        output_dir=os.path.join(output_dir, "umap"),
        title="PBMC 3k — Cell Types"
    )

    # Plot canonical marker genes on UMAP
    canonical_markers = ["CD3D", "MS4A1", "LYZ", "GNLY", "PPBP", "FCER1A"]
    plot_umap_gene_expression(
        adata,
        genes=canonical_markers,
        output_dir=os.path.join(output_dir, "markers")
    )

    # ── STEP 6: Export results ────────────────────────────────────────────────
    print("\n[Step 6] Exporting results...")
    print("-" * 50)

    from export_results import export_anndata_results

    export_anndata_results(
        adata,
        markers=markers,
        output_dir=output_dir,
        prefix="pbmc3k"
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("✓ COMPLETE ANALYSIS FINISHED")
    print("=" * 70)
    print(f"\nFinal AnnData: {adata.n_obs} cells × {adata.n_vars} genes")
    print(f"Clusters (res=0.8): {n_clusters}")
    print(f"Cell types annotated: {adata.obs['cell_type'].nunique()}")
    print(f"\nOutput files saved to: {output_dir}/")
    print("  pbmc3k.h5ad              — Full AnnData object")
    print("  pbmc3k_metadata.csv      — Cell metadata (clusters, cell types)")
    print("  pbmc3k_markers.csv       — Marker genes per cluster")
    print("  umap/                    — UMAP plots (clusters + cell types)")
    print("  markers/                 — Marker gene expression UMAPs")

    return adata


# ── Expected results reference ─────────────────────────────────────────────────
EXPECTED_RESULTS = {
    "n_cells_raw":      2700,
    "n_cells_filtered": (2600, 2700),   # range after QC
    "n_clusters_08":    (8, 10),         # at resolution 0.8
    "cell_types": [
        "CD4 T cells",
        "CD8 T cells",
        "B cells",
        "NK cells",
        "CD14+ Monocytes",
        "FCGR3A+ Monocytes",
        "Dendritic cells",
        "Platelets"
    ],
    "canonical_markers": {
        "CD4 T cells":         ["CD3D", "CD4", "IL7R"],
        "CD8 T cells":         ["CD3D", "CD8A", "CD8B"],
        "B cells":             ["MS4A1", "CD79A", "CD79B"],
        "NK cells":            ["GNLY", "NKG7", "GZMB"],
        "CD14+ Monocytes":     ["LYZ", "CD14", "CST3"],
        "FCGR3A+ Monocytes":   ["FCGR3A", "MS4A7"],
        "Dendritic cells":     ["FCER1A", "CST3"],
        "Platelets":           ["PPBP", "PF4"]
    }
}


# ── CLI entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run complete Scanpy scRNA-seq analysis on PBMC 3k dataset."
    )
    parser.add_argument(
        "--output-dir", default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})"
    )
    args = parser.parse_args()

    adata = run_complete_analysis(output_dir=args.output_dir)
