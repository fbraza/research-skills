"""
qc_and_load.py — CellBender QC, loading, and downstream integration

Loads CellBender output, performs QC checks, generates validation plots,
and prepares AnnData for downstream analysis (scanpy / Seurat export).

Usage:
    # Basic QC and load:
    python qc_and_load.py \
        --input raw_feature_bc_matrix.h5 \
        --output cellbender_output.h5 \
        --figures-dir figures/

    # With cell type annotation for validation:
    python qc_and_load.py \
        --input raw_feature_bc_matrix.h5 \
        --output cellbender_output.h5 \
        --figures-dir figures/ \
        --ambient-genes HBB HBA1 HBA2 \
        --save-adata adata_cellbender.h5ad

    # Multiple FPR comparison:
    python qc_and_load.py \
        --input raw_feature_bc_matrix.h5 \
        --output cellbender_output.h5 \
        --compare-outputs cellbender_fpr0.05.h5 cellbender_fpr0.1.h5 \
        --compare-labels fpr0.01 fpr0.05 fpr0.1 \
        --figures-dir figures/

Requirements:
    pip install cellbender scanpy matplotlib seaborn pandas
"""

import argparse
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style='ticks', font_scale=1.1)


def parse_args():
    parser = argparse.ArgumentParser(
        description='CellBender QC and downstream loading',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--input', required=True,
                        help='Raw input count matrix (same file used for CellBender)')
    parser.add_argument('--output', required=True,
                        help='CellBender output .h5 file')
    parser.add_argument('--figures-dir', default='figures/',
                        help='Directory to save QC figures')
    parser.add_argument('--ambient-genes', nargs='+', default=None,
                        help='Known ambient genes to validate removal (e.g., HBB HBA1)')
    parser.add_argument('--mt-prefix', default='MT-',
                        help='Mitochondrial gene prefix (MT- for human, mt- for mouse)')
    parser.add_argument('--min-genes', type=int, default=200,
                        help='Minimum genes per cell for filtering')
    parser.add_argument('--max-mt-pct', type=float, default=20,
                        help='Maximum mitochondrial percentage for filtering')
    parser.add_argument('--cell-prob-threshold', type=float, default=0.5,
                        help='Cell probability threshold for cell calling')
    parser.add_argument('--compare-outputs', nargs='+', default=None,
                        help='Additional CellBender output files for FPR comparison')
    parser.add_argument('--compare-labels', nargs='+', default=None,
                        help='Labels for comparison outputs')
    parser.add_argument('--save-adata', default=None,
                        help='Save processed AnnData to this .h5ad path')
    parser.add_argument('--export-seurat', default=None,
                        help='Export Seurat-compatible h5 to this path (requires ptrepack)')
    parser.add_argument('--dpi', type=int, default=150)
    return parser.parse_args()


def load_data(input_file, output_file, compare_outputs=None, compare_labels=None):
    """Load CellBender output with raw data."""
    try:
        from cellbender.remove_background.downstream import (
            load_anndata_from_input_and_output,
            load_anndata_from_input_and_outputs,
        )
    except ImportError:
        print("ERROR: cellbender not installed. Run: pip install cellbender")
        sys.exit(1)

    print(f"Loading data...")
    print(f"  Input:  {input_file}")
    print(f"  Output: {output_file}")

    if compare_outputs:
        labels = compare_labels or [f'fpr{i}' for i in range(len(compare_outputs))]
        output_files = {'cellbender': output_file}
        for label, path in zip(labels[1:], compare_outputs):
            output_files[label] = path

        adata = load_anndata_from_input_and_outputs(
            input_file=input_file,
            output_files=output_files,
            input_layer_key='raw',
        )
    else:
        adata = load_anndata_from_input_and_output(
            input_file=input_file,
            output_file=output_file,
            input_layer_key='raw',
        )

    print(f"  Loaded: {adata.shape[0]} barcodes × {adata.shape[1]} genes")
    return adata


def print_qc_stats(adata, cell_prob_threshold):
    """Print basic QC statistics."""
    print("\n" + "=" * 50)
    print("QC STATISTICS")
    print("=" * 50)

    n_cells = (adata.obs['cell_probability'] > cell_prob_threshold).sum()
    print(f"  Cell probability threshold: {cell_prob_threshold}")
    print(f"  Cells called:               {n_cells}")
    print(f"  Total barcodes analyzed:    {adata.shape[0]}")

    if 'background_fraction' in adata.obs:
        cells = adata[adata.obs['cell_probability'] > cell_prob_threshold]
        mean_bg = cells.obs['background_fraction'].mean()
        median_bg = cells.obs['background_fraction'].median()
        print(f"\n  Background fraction in cells:")
        print(f"    Mean:   {mean_bg:.3f}")
        print(f"    Median: {median_bg:.3f}")
        if mean_bg > 0.3:
            print("    WARNING: High mean background fraction (>30%). "
                  "Dataset has significant ambient contamination.")

    if 'ambient_expression' in adata.var:
        top_ambient = adata.var['ambient_expression'].sort_values(ascending=False).head(10)
        print(f"\n  Top 10 ambient genes:")
        for gene, val in top_ambient.items():
            print(f"    {gene:<20} {val:.4f}")


def plot_cell_probability(adata, output_dir, dpi, cell_prob_threshold):
    """Plot cell probability distribution."""
    import scipy.sparse as sp

    fig, axes = plt.subplots(1, 2, figsize=(12, 4))

    # UMI rank plot with cell probability
    ax = axes[0]
    if 'n_raw' in adata.obs:
        umi_counts = adata.obs['n_raw'].values
    else:
        raw = adata.layers.get('raw', adata.X)
        umi_counts = np.array(raw.sum(axis=1)).flatten() if sp.issparse(raw) \
                     else raw.sum(axis=1)

    sorted_idx = np.argsort(umi_counts)[::-1]
    sorted_umis = umi_counts[sorted_idx]
    cell_probs = adata.obs['cell_probability'].values[sorted_idx]

    rank = np.arange(1, len(sorted_umis) + 1)
    ax.semilogy(rank, sorted_umis, color='lightgray', linewidth=1, label='UMI count')
    ax2 = ax.twinx()
    ax2.scatter(rank, cell_probs, c=cell_probs, cmap='RdYlGn',
                s=1, alpha=0.5, vmin=0, vmax=1)
    ax2.axhline(cell_prob_threshold, color='red', linestyle='--', lw=1,
                label=f'Threshold ({cell_prob_threshold})')
    ax2.set_ylabel('Cell Probability', color='green')
    ax2.set_ylim(-0.05, 1.05)
    ax.set_xlabel('Barcode Rank')
    ax.set_ylabel('UMI Count')
    ax.set_title('UMI Rank Plot + Cell Probabilities')
    ax.legend(loc='upper right')

    # Cell probability histogram
    ax = axes[1]
    ax.hist(adata.obs['cell_probability'], bins=50, color='steelblue', edgecolor='white')
    ax.axvline(cell_prob_threshold, color='red', linestyle='--', lw=1.5,
               label=f'Threshold ({cell_prob_threshold})')
    ax.set_xlabel('Cell Probability')
    ax.set_ylabel('Number of Barcodes')
    ax.set_title('Cell Probability Distribution')
    ax.legend()

    plt.tight_layout()
    path = os.path.join(output_dir, 'cell_probability.png')
    plt.savefig(path, dpi=dpi, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def plot_ambient_profile(adata, output_dir, dpi, n_genes=40):
    """Plot ambient RNA expression profile."""
    if 'ambient_expression' not in adata.var:
        return

    ambient = adata.var['ambient_expression'].sort_values(ascending=False).head(n_genes)

    fig, ax = plt.subplots(figsize=(max(10, n_genes * 0.4), 4))
    colors = ['#d62728' if v > 0.02 else '#1f77b4' for v in ambient.values]
    ax.bar(range(len(ambient)), ambient.values, color=colors)
    ax.set_xticks(range(len(ambient)))
    ax.set_xticklabels(ambient.index, rotation=45, ha='right', fontsize=8)
    ax.set_xlabel('Gene')
    ax.set_ylabel('Ambient Expression (normalized)')
    ax.set_title(f'Top {n_genes} Ambient RNA Genes\n(red = >2% of ambient profile)')
    plt.tight_layout()
    path = os.path.join(output_dir, 'ambient_profile.png')
    plt.savefig(path, dpi=dpi, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def plot_background_fraction(adata, output_dir, dpi, cell_prob_threshold):
    """Plot per-cell background fraction distribution."""
    if 'background_fraction' not in adata.obs:
        return

    cells = adata[adata.obs['cell_probability'] > cell_prob_threshold]

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(cells.obs['background_fraction'], bins=50,
            color='steelblue', edgecolor='white')
    ax.axvline(cells.obs['background_fraction'].mean(), color='red',
               linestyle='--', lw=1.5,
               label=f"Mean: {cells.obs['background_fraction'].mean():.3f}")
    ax.set_xlabel('Background Fraction')
    ax.set_ylabel('Number of Cells')
    ax.set_title('Per-Cell Ambient RNA Fraction (CellBender cells)')
    ax.legend()
    plt.tight_layout()
    path = os.path.join(output_dir, 'background_fraction.png')
    plt.savefig(path, dpi=dpi, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def plot_counts_removed(adata, output_dir, dpi, ambient_genes=None):
    """Plot counts removed per gene."""
    import scipy.sparse as sp

    raw = adata.layers.get('raw', None)
    cellbender = adata.layers.get('cellbender', adata.X)

    if raw is None:
        print("  Skipping counts-removed plot (no raw layer)")
        return

    if sp.issparse(raw):
        raw_arr = np.array(raw.sum(axis=0)).flatten()
    else:
        raw_arr = raw.sum(axis=0)

    if sp.issparse(cellbender):
        cb_arr = np.array(cellbender.sum(axis=0)).flatten()
    else:
        cb_arr = cellbender.sum(axis=0)

    removed = raw_arr - cb_arr
    frac_removed = np.where(raw_arr > 0, removed / raw_arr, 0)

    removed_df = pd.DataFrame({
        'gene': adata.var_names,
        'raw_counts': raw_arr,
        'counts_removed': removed,
        'frac_removed': frac_removed,
    }).sort_values('counts_removed', ascending=False)

    # Plot top 40 genes by counts removed
    top = removed_df.head(40)
    fig, ax = plt.subplots(figsize=(12, 4))
    colors = ['#d62728' if g in (ambient_genes or []) else '#1f77b4'
              for g in top['gene']]
    ax.bar(range(len(top)), top['counts_removed'], color=colors)
    ax.set_xticks(range(len(top)))
    ax.set_xticklabels(top['gene'], rotation=45, ha='right', fontsize=8)
    ax.set_xlabel('Gene')
    ax.set_ylabel('Total Counts Removed')
    ax.set_title('Top 40 Genes by Counts Removed\n(red = user-specified ambient genes)')
    plt.tight_layout()
    path = os.path.join(output_dir, 'counts_removed_per_gene.png')
    plt.savefig(path, dpi=dpi, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")

    # Save table
    table_path = os.path.join(output_dir, 'counts_removed_per_gene.csv')
    removed_df.to_csv(table_path, index=False)
    print(f"  Saved: {table_path}")


def plot_ambient_gene_validation(adata, ambient_genes, output_dir, dpi,
                                 cell_prob_threshold):
    """Violin plots of ambient genes before/after CellBender."""
    import scipy.sparse as sp

    if not ambient_genes:
        return

    # Filter to genes present in data
    present = [g for g in ambient_genes if g in adata.var_names]
    if not present:
        print(f"  WARNING: None of the specified ambient genes found in data: {ambient_genes}")
        return

    cells = adata[adata.obs['cell_probability'] > cell_prob_threshold]

    fig, axes = plt.subplots(2, len(present), figsize=(4 * len(present), 7))
    if len(present) == 1:
        axes = axes.reshape(2, 1)

    for j, gene in enumerate(present):
        gene_idx = list(adata.var_names).index(gene)

        # Raw counts
        raw = cells.layers.get('raw', cells.X)
        if sp.issparse(raw):
            raw_vals = np.array(raw[:, gene_idx].todense()).flatten()
        else:
            raw_vals = raw[:, gene_idx].flatten()

        # CellBender counts
        cb = cells.layers.get('cellbender', cells.X)
        if sp.issparse(cb):
            cb_vals = np.array(cb[:, gene_idx].todense()).flatten()
        else:
            cb_vals = cb[:, gene_idx].flatten()

        axes[0, j].hist(raw_vals, bins=30, color='#d62728', alpha=0.7)
        axes[0, j].set_title(f'{gene}\n(raw)', fontsize=10)
        axes[0, j].set_xlabel('Counts')
        axes[0, j].set_ylabel('Cells')

        axes[1, j].hist(cb_vals, bins=30, color='#1f77b4', alpha=0.7)
        axes[1, j].set_title(f'{gene}\n(CellBender)', fontsize=10)
        axes[1, j].set_xlabel('Counts')
        axes[1, j].set_ylabel('Cells')

        # Add mean lines
        for ax, vals, color in [(axes[0, j], raw_vals, '#d62728'),
                                 (axes[1, j], cb_vals, '#1f77b4')]:
            ax.axvline(np.mean(vals), color='black', linestyle='--', lw=1,
                       label=f'Mean: {np.mean(vals):.2f}')
            ax.legend(fontsize=8)

    plt.suptitle('Ambient Gene Expression: Raw vs CellBender', fontsize=12, y=1.01)
    plt.tight_layout()
    path = os.path.join(output_dir, 'ambient_gene_validation.png')
    plt.savefig(path, dpi=dpi, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {path}")


def export_seurat(output_h5, seurat_path):
    """Export Seurat-compatible h5 using ptrepack."""
    import subprocess
    cmd = ['ptrepack', '--complevel', '5',
           f'{output_h5}:/matrix', f'{seurat_path}:/matrix']
    result = subprocess.run(cmd, check=False)
    if result.returncode == 0:
        print(f"  Seurat-compatible h5 saved: {seurat_path}")
    else:
        print("  ERROR: ptrepack failed. Install with: conda install -c anaconda pytables")


def main():
    args = parse_args()
    os.makedirs(args.figures_dir, exist_ok=True)

    print("=" * 60)
    print("CellBender QC and Loading")
    print("=" * 60)

    # Load data
    adata = load_data(
        args.input, args.output,
        args.compare_outputs, args.compare_labels
    )

    # Print QC stats
    print_qc_stats(adata, args.cell_prob_threshold)

    # Generate plots
    print("\nGenerating QC figures...")
    plot_cell_probability(adata, args.figures_dir, args.dpi, args.cell_prob_threshold)
    plot_ambient_profile(adata, args.figures_dir, args.dpi)
    plot_background_fraction(adata, args.figures_dir, args.dpi, args.cell_prob_threshold)
    plot_counts_removed(adata, args.figures_dir, args.dpi, args.ambient_genes)

    if args.ambient_genes:
        plot_ambient_gene_validation(
            adata, args.ambient_genes, args.figures_dir,
            args.dpi, args.cell_prob_threshold
        )

    # Filter to cells
    cells = adata[adata.obs['cell_probability'] > args.cell_prob_threshold].copy()
    print(f"\nFiltered to {cells.shape[0]} cells (cell_probability > {args.cell_prob_threshold})")

    # Basic cell QC
    try:
        import scanpy as sc
        sc.pp.calculate_qc_metrics(
            cells, qc_vars=[args.mt_prefix.rstrip('-')],
            percent_top=None, log1p=False, inplace=True
        )
        before = cells.shape[0]
        cells = cells[cells.obs['n_genes_by_counts'] >= args.min_genes]
        cells = cells[cells.obs[f'pct_counts_{args.mt_prefix.rstrip("-")}'] <= args.max_mt_pct]
        print(f"After QC filtering: {cells.shape[0]} cells "
              f"(removed {before - cells.shape[0]} low-quality cells)")
    except Exception as e:
        print(f"  (Skipping scanpy QC: {e})")

    # Save AnnData
    if args.save_adata:
        cells.write_h5ad(args.save_adata)
        print(f"\nAnnData saved: {args.save_adata}")
        print(f"  Shape: {cells.shape}")
        print(f"  Layers: {list(cells.layers.keys())}")
        print(f"  obs columns: {list(cells.obs.columns)}")

    # Export for Seurat
    if args.export_seurat:
        export_seurat(args.output.replace('.h5', '_filtered.h5'), args.export_seurat)

    print(f"\nAll figures saved to: {args.figures_dir}")
    print("\nNext steps:")
    print("  1. Review figures in", args.figures_dir)
    print("  2. Load adata for downstream analysis:")
    print("     from cellbender.remove_background.downstream import load_anndata_from_input_and_output")
    print("     adata = load_anndata_from_input_and_output(input_file, output_file)")


if __name__ == '__main__':
    main()
