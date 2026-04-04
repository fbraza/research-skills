"""
Visualization of ANANSE influence results.

Wraps `ananse plot` and provides additional Python-based visualizations
for influence scores and GRN networks.

Usage:
    from scripts.plot_results import plot_influence_results
    plot_influence_results(
        influence_file='influence.tsv',
        diffnetwork_file='influence_diffnetwork.tsv',
        output_dir='plots',
        n_tfs=20
    )
"""

import os
import subprocess
import shutil

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns


def plot_influence_results(
    influence_file,
    diffnetwork_file=None,
    output_dir="ANANSE_plots",
    n_tfs=20,
    file_type="pdf"
):
    """
    Generate all ANANSE visualizations using ananse plot + custom Python plots.

    Produces:
    - Official ananse dotplot (via ananse plot)
    - Official ananse GRN network figure (if diffnetwork provided)
    - Custom seaborn influence score barplot (PNG + SVG)
    - Custom scatter: influence score vs TF expression change (PNG + SVG)

    Parameters
    ----------
    influence_file : str
        Path to influence.tsv from ananse influence
    diffnetwork_file : str, optional
        Path to influence_diffnetwork.tsv (from ananse influence -f)
    output_dir : str
        Output directory for plots (default: "ANANSE_plots")
    n_tfs : int
        Number of top TFs to display (default: 20)
    file_type : str
        File type for ananse plot: 'pdf', 'png', or 'svg' (default: 'pdf')

    Returns
    -------
    list of str : Paths to generated plot files

    Example
    -------
    >>> plot_influence_results(
    ...     influence_file='influence.tsv',
    ...     diffnetwork_file='influence_diffnetwork.tsv',
    ...     output_dir='plots',
    ...     n_tfs=20
    ... )
    """
    os.makedirs(output_dir, exist_ok=True)
    generated_files = []

    # --- 1. Official ananse plot ---
    if shutil.which("ananse"):
        print("\n=== Running ananse plot ===")
        cmd = ["ananse", "plot", influence_file,
               "-o", output_dir,
               "--n-tfs", str(n_tfs),
               "-t", file_type]
        if diffnetwork_file and os.path.exists(diffnetwork_file):
            cmd += ["-d", diffnetwork_file]
        else:
            print("  ⚠ No diffnetwork file — GRN network figure will not be generated")
            print("    Re-run ananse influence with -f flag to generate diffnetwork")

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"  ✓ ananse plot completed in: {output_dir}/")
        else:
            print(f"  ⚠ ananse plot failed: {result.stderr}")
            print("    Falling back to Python-only plots...")
    else:
        print("  ⚠ ananse not in PATH — generating Python-only plots")

    # --- 2. Custom influence score barplot ---
    print("\n=== Generating custom influence barplot ===")
    barplot_files = _plot_influence_barplot(
        influence_file=influence_file,
        output_dir=output_dir,
        n_tfs=n_tfs
    )
    generated_files.extend(barplot_files)

    # --- 3. Influence vs expression scatter ---
    print("\n=== Generating influence vs expression scatter ===")
    scatter_files = _plot_influence_vs_expression(
        influence_file=influence_file,
        output_dir=output_dir,
        n_tfs=n_tfs
    )
    generated_files.extend(scatter_files)

    print(f"\n✓ All visualizations generated successfully!")
    print(f"  Output directory: {output_dir}")
    for f in generated_files:
        print(f"  - {os.path.basename(f)}")

    return generated_files


def _plot_influence_barplot(influence_file, output_dir, n_tfs=20):
    """Generate a horizontal barplot of top TFs by influence score."""
    influence = pd.read_csv(influence_file, sep='\t')
    top_tfs = influence.nlargest(n_tfs, 'influence_score').sort_values(
        'influence_score', ascending=True
    )

    fig, ax = plt.subplots(figsize=(8, max(4, n_tfs * 0.35)))

    colors = ['#E74C3C' if s > 0.5 else '#3498DB' if s > 0.2 else '#95A5A6'
              for s in top_tfs['influence_score']]

    bars = ax.barh(top_tfs['factor'], top_tfs['influence_score'],
                   color=colors, edgecolor='white', linewidth=0.5)

    ax.set_xlabel('Influence Score', fontsize=12)
    ax.set_title(f'Top {n_tfs} TFs by Influence Score', fontsize=13, fontweight='bold')
    ax.set_xlim(0, min(1.05, top_tfs['influence_score'].max() * 1.1))
    ax.axvline(x=0.5, color='#E74C3C', linestyle='--', alpha=0.4, linewidth=1)
    ax.axvline(x=0.2, color='#3498DB', linestyle='--', alpha=0.4, linewidth=1)

    # Add value labels
    for bar, val in zip(bars, top_tfs['influence_score']):
        ax.text(val + 0.01, bar.get_y() + bar.get_height() / 2,
                f'{val:.3f}', va='center', fontsize=8)

    sns.despine(ax=ax)
    plt.tight_layout()

    files = []
    for ext in ['png', 'svg']:
        path = os.path.join(output_dir, f'influence_barplot.{ext}')
        try:
            plt.savefig(path, dpi=150, bbox_inches='tight')
            files.append(path)
        except Exception as e:
            print(f"  ⚠ Could not save {ext}: {e}")
    plt.close()

    return files


def _plot_influence_vs_expression(influence_file, output_dir, n_tfs=20):
    """Generate scatter plot: influence score vs TF expression change."""
    influence = pd.read_csv(influence_file, sep='\t')

    if 'tf_expression_score' not in influence.columns:
        print("  ⚠ tf_expression_score column not found — skipping scatter plot")
        return []

    top_tfs = influence.nlargest(n_tfs, 'influence_score')

    fig, ax = plt.subplots(figsize=(8, 6))

    scatter = ax.scatter(
        top_tfs['tf_expression_score'],
        top_tfs['influence_score'],
        c=top_tfs['influence_score'],
        cmap='RdYlBu_r',
        s=80,
        alpha=0.8,
        edgecolors='white',
        linewidth=0.5
    )

    # Label top 10
    for _, row in top_tfs.head(10).iterrows():
        ax.annotate(
            row['factor'],
            (row['tf_expression_score'], row['influence_score']),
            fontsize=8,
            xytext=(5, 5),
            textcoords='offset points'
        )

    plt.colorbar(scatter, ax=ax, label='Influence Score')
    ax.set_xlabel('TF Expression Score', fontsize=12)
    ax.set_ylabel('Influence Score', fontsize=12)
    ax.set_title(f'Influence Score vs TF Expression Change\n(Top {n_tfs} TFs)',
                 fontsize=12, fontweight='bold')
    sns.despine(ax=ax)
    plt.tight_layout()

    files = []
    for ext in ['png', 'svg']:
        path = os.path.join(output_dir, f'influence_vs_expression.{ext}')
        try:
            plt.savefig(path, dpi=150, bbox_inches='tight')
            files.append(path)
        except Exception as e:
            print(f"  ⚠ Could not save {ext}: {e}")
    plt.close()

    return files
