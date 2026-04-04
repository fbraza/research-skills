"""
plot_results.py — DECODE Results Visualization

Generates publication-quality figures from DECODE deconvolution results.

Usage:
    # Basic (predictions + ground truth in same directory):
    python plot_results.py \
        --results_dir results/transcriptomics/ \
        --output_dir figures/

    # With condition labels for differential analysis:
    python plot_results.py \
        --results_dir results/transcriptomics/ \
        --conditions_file metadata/conditions.csv \
        --output_dir figures/

    # Multi-omics comparison:
    python plot_results.py \
        --results_dirs results/rna/ results/protein/ \
        --omics_labels RNA Protein \
        --output_dir figures/multi_omics/

Inputs:
    results_dir/predictions.csv  — (n_samples, n_cell_types)
    results_dir/ground_truth.csv — (n_samples, n_cell_types) [optional]
    results_dir/metrics.csv      — CCC, RMSE, Pearson_r [optional]
"""

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from scipy.stats import pearsonr, spearmanr

sns.set_theme(style='ticks', font_scale=1.1)
PALETTE = sns.color_palette('tab20')


def parse_args():
    parser = argparse.ArgumentParser(description='DECODE results visualization')
    parser.add_argument('--results_dir', default=None,
                        help='Single results directory (predictions.csv, ground_truth.csv)')
    parser.add_argument('--results_dirs', nargs='+', default=None,
                        help='Multiple results directories for multi-omics comparison')
    parser.add_argument('--omics_labels', nargs='+', default=None,
                        help='Labels for each results_dir (e.g., RNA Protein)')
    parser.add_argument('--conditions_file', default=None,
                        help='CSV with sample conditions (columns: sample, condition)')
    parser.add_argument('--output_dir', default='figures/',
                        help='Output directory for figures')
    parser.add_argument('--dpi', type=int, default=150)
    parser.add_argument('--format', default='png', choices=['png', 'svg', 'pdf'])
    return parser.parse_args()


def load_results(results_dir):
    """Load predictions, ground truth, and metrics from a results directory."""
    pred_path = os.path.join(results_dir, 'predictions.csv')
    gt_path   = os.path.join(results_dir, 'ground_truth.csv')
    met_path  = os.path.join(results_dir, 'metrics.csv')

    if not os.path.exists(pred_path):
        raise FileNotFoundError(f"predictions.csv not found in {results_dir}")

    pred = pd.read_csv(pred_path)
    gt   = pd.read_csv(gt_path)   if os.path.exists(gt_path)  else None
    metrics = pd.read_csv(met_path).iloc[0].to_dict() if os.path.exists(met_path) else None

    cell_types = pred.columns.tolist()
    return pred, gt, metrics, cell_types


def save_fig(fig, output_dir, name, fmt, dpi):
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, f"{name}.{fmt}")
    fig.savefig(path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"  Saved: {path}")


# ── Figure 1: Scatter plots (predicted vs ground truth) ─────────────────────

def plot_scatter(pred, gt, cell_types, metrics, output_dir, fmt, dpi):
    """Per-cell-type scatter: predicted vs true proportions."""
    if gt is None:
        print("  Skipping scatter plot (no ground truth)")
        return

    n = len(cell_types)
    ncols = min(4, n)
    nrows = (n + ncols - 1) // ncols

    fig, axes = plt.subplots(nrows, ncols, figsize=(4 * ncols, 4 * nrows))
    axes = np.array(axes).flatten() if n > 1 else [axes]

    for i, ct in enumerate(cell_types):
        ax = axes[i]
        x = gt[ct].values
        y = pred[ct].values
        r, _ = pearsonr(x, y)

        ax.scatter(x, y, alpha=0.4, s=15, color=PALETTE[i % len(PALETTE)])
        lim = [0, max(x.max(), y.max()) * 1.05]
        ax.plot(lim, lim, 'r--', lw=1, label='y=x')
        ax.set_xlabel('True Proportion', fontsize=9)
        ax.set_ylabel('Predicted Proportion', fontsize=9)
        ax.set_title(f"{ct}\nr={r:.3f}", fontsize=9)
        ax.set_xlim(lim); ax.set_ylim(lim)

    # Hide unused axes
    for j in range(n, len(axes)):
        axes[j].set_visible(False)

    title = "DECODE: Predicted vs True Proportions"
    if metrics:
        title += f"\nCCC={metrics['CCC']:.3f}  RMSE={metrics['RMSE']:.3f}  r={metrics['Pearson_r']:.3f}"
    fig.suptitle(title, fontsize=11, y=1.01)
    plt.tight_layout()
    save_fig(fig, output_dir, 'scatter_pred_vs_true', fmt, dpi)


# ── Figure 2: Stacked bar chart ──────────────────────────────────────────────

def plot_stacked_bar(pred, cell_types, output_dir, fmt, dpi, n_show=50):
    """Stacked bar chart of predicted cell type proportions."""
    n_show = min(n_show, len(pred))
    df = pred.iloc[:n_show][cell_types]

    fig, ax = plt.subplots(figsize=(max(8, n_show * 0.35), 4))
    df.plot(kind='bar', stacked=True, ax=ax,
            color=PALETTE[:len(cell_types)], width=0.9, edgecolor='none')
    ax.set_xlabel('Sample', fontsize=10)
    ax.set_ylabel('Proportion', fontsize=10)
    ax.set_title('DECODE Predicted Cell Type Proportions', fontsize=11)
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=8)
    ax.set_ylim(0, 1)
    plt.xticks(rotation=45, ha='right', fontsize=7)
    plt.tight_layout()
    save_fig(fig, output_dir, 'stacked_bar', fmt, dpi)


# ── Figure 3: Heatmap ────────────────────────────────────────────────────────

def plot_heatmap(pred, cell_types, output_dir, fmt, dpi):
    """Heatmap of cell type proportions across samples."""
    fig, ax = plt.subplots(figsize=(len(cell_types) * 1.5, max(5, len(pred) * 0.15)))
    sns.heatmap(
        pred[cell_types],
        cmap='YlOrRd', vmin=0, vmax=1,
        ax=ax, xticklabels=True, yticklabels=False,
        cbar_kws={'label': 'Proportion'}
    )
    ax.set_title('Cell Type Proportions (DECODE)', fontsize=11)
    ax.set_xlabel('Cell Type', fontsize=10)
    ax.set_ylabel('Sample', fontsize=10)
    plt.tight_layout()
    save_fig(fig, output_dir, 'heatmap_proportions', fmt, dpi)


# ── Figure 4: Boxplot by condition ───────────────────────────────────────────

def plot_boxplot_by_condition(pred, cell_types, conditions, output_dir, fmt, dpi):
    """Boxplot of cell type proportions grouped by condition."""
    df = pred[cell_types].copy()
    df['condition'] = conditions

    df_long = df.melt(id_vars='condition', value_vars=cell_types,
                      var_name='cell_type', value_name='proportion')

    n_conditions = df['condition'].nunique()
    palette = sns.color_palette('Set2', n_conditions)

    fig, ax = plt.subplots(figsize=(len(cell_types) * 2, 5))
    sns.boxplot(data=df_long, x='cell_type', y='proportion',
                hue='condition', ax=ax, palette=palette,
                fliersize=3, linewidth=1)
    ax.set_xlabel('Cell Type', fontsize=10)
    ax.set_ylabel('Proportion', fontsize=10)
    ax.set_title('Cell Type Proportions by Condition', fontsize=11)
    ax.legend(title='Condition', bbox_to_anchor=(1.02, 1), loc='upper left')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    save_fig(fig, output_dir, 'boxplot_by_condition', fmt, dpi)


# ── Figure 5: Multi-omics consistency ────────────────────────────────────────

def plot_multi_omics(preds, labels, cell_types, output_dir, fmt, dpi):
    """Scatter matrix comparing predictions across omics types."""
    n = len(preds)
    if n < 2:
        return

    fig, axes = plt.subplots(n, n, figsize=(4 * n, 4 * n))

    for i in range(n):
        for j in range(n):
            ax = axes[i][j]
            if i == j:
                # Diagonal: distribution
                for k, ct in enumerate(cell_types):
                    ax.hist(preds[i][ct], bins=20, alpha=0.5,
                            color=PALETTE[k], label=ct, density=True)
                ax.set_title(labels[i], fontsize=10)
                if i == 0:
                    ax.legend(fontsize=7)
            else:
                # Off-diagonal: scatter
                common_types = [ct for ct in cell_types if ct in preds[i].columns and ct in preds[j].columns]
                for k, ct in enumerate(common_types):
                    x = preds[j][ct].values[:min(len(preds[i]), len(preds[j]))]
                    y = preds[i][ct].values[:min(len(preds[i]), len(preds[j]))]
                    ax.scatter(x, y, alpha=0.3, s=10, color=PALETTE[k])
                r, _ = pearsonr(
                    preds[i][common_types].values.flatten()[:min(len(preds[i]), len(preds[j])) * len(common_types)],
                    preds[j][common_types].values.flatten()[:min(len(preds[i]), len(preds[j])) * len(common_types)]
                )
                ax.set_title(f"{labels[i]} vs {labels[j]}\nr={r:.3f}", fontsize=9)
                ax.set_xlabel(labels[j], fontsize=8)
                ax.set_ylabel(labels[i], fontsize=8)

    plt.suptitle('Multi-Omics Consistency', fontsize=12, y=1.01)
    plt.tight_layout()
    save_fig(fig, output_dir, 'multi_omics_consistency', fmt, dpi)


# ── Figure 6: Per-cell-type CCC bar chart ────────────────────────────────────

def plot_per_celltype_metrics(pred, gt, cell_types, output_dir, fmt, dpi):
    """Bar chart of per-cell-type CCC."""
    if gt is None:
        return

    cccs = []
    for ct in cell_types:
        x, y = gt[ct].values, pred[ct].values
        mean_x, mean_y = np.mean(x), np.mean(y)
        var_x, var_y = np.var(x), np.var(y)
        cov = np.mean((x - mean_x) * (y - mean_y))
        ccc = (2 * cov) / (var_x + var_y + (mean_x - mean_y) ** 2)
        cccs.append(ccc)

    fig, ax = plt.subplots(figsize=(len(cell_types) * 1.5, 4))
    bars = ax.bar(cell_types, cccs, color=PALETTE[:len(cell_types)], edgecolor='white')
    ax.axhline(0.9, color='red', linestyle='--', lw=1, label='CCC=0.9 threshold')
    ax.set_xlabel('Cell Type', fontsize=10)
    ax.set_ylabel("Lin's CCC", fontsize=10)
    ax.set_title('Per-Cell-Type Concordance Correlation Coefficient', fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=9)
    for bar, ccc in zip(bars, cccs):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                f'{ccc:.3f}', ha='center', va='bottom', fontsize=8)
    plt.xticks(rotation=30, ha='right')
    plt.tight_layout()
    save_fig(fig, output_dir, 'per_celltype_ccc', fmt, dpi)


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    os.makedirs(args.output_dir, exist_ok=True)

    # Load conditions if provided
    conditions = None
    if args.conditions_file and os.path.exists(args.conditions_file):
        cond_df = pd.read_csv(args.conditions_file)
        conditions = cond_df['condition'].values
        print(f"Loaded conditions: {np.unique(conditions)}")

    # Single results directory
    if args.results_dir:
        print(f"\nLoading results from: {args.results_dir}")
        pred, gt, metrics, cell_types = load_results(args.results_dir)

        print(f"  Samples: {len(pred)}, Cell types: {cell_types}")
        if metrics:
            print(f"  CCC={metrics['CCC']:.4f}, RMSE={metrics['RMSE']:.4f}, r={metrics['Pearson_r']:.4f}")

        print("\nGenerating figures...")
        plot_scatter(pred, gt, cell_types, metrics, args.output_dir, args.format, args.dpi)
        plot_stacked_bar(pred, cell_types, args.output_dir, args.format, args.dpi)
        plot_heatmap(pred, cell_types, args.output_dir, args.format, args.dpi)
        plot_per_celltype_metrics(pred, gt, cell_types, args.output_dir, args.format, args.dpi)

        if conditions is not None:
            plot_boxplot_by_condition(pred, cell_types, conditions,
                                      args.output_dir, args.format, args.dpi)

    # Multi-omics comparison
    elif args.results_dirs:
        labels = args.omics_labels or [f'Omics{i+1}' for i in range(len(args.results_dirs))]
        preds = []
        all_cell_types = None

        for d, label in zip(args.results_dirs, labels):
            print(f"\nLoading {label} from: {d}")
            pred, gt, metrics, cell_types = load_results(d)
            preds.append(pred)
            if all_cell_types is None:
                all_cell_types = cell_types
            if metrics:
                print(f"  CCC={metrics['CCC']:.4f}, RMSE={metrics['RMSE']:.4f}")

        print("\nGenerating multi-omics figures...")
        plot_multi_omics(preds, labels, all_cell_types, args.output_dir, args.format, args.dpi)

        # Also plot individual stacked bars
        for pred, label in zip(preds, labels):
            sub_dir = os.path.join(args.output_dir, label.lower())
            plot_stacked_bar(pred, all_cell_types, sub_dir, args.format, args.dpi)

    else:
        print("Error: Provide --results_dir or --results_dirs")
        return

    print(f"\nAll figures saved to: {args.output_dir}")


if __name__ == '__main__':
    main()
