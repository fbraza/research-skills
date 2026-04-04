"""
Export ANANSE results to human-readable CSV/TSV files.

Usage:
    from scripts.export_results import export_ananse_results
    export_ananse_results(
        influence_file='influence.tsv',
        source_network='source.network.tsv',
        target_network='target.network.tsv',
        output_dir='results'
    )
"""

import os
import pandas as pd


def export_ananse_results(
    influence_file,
    source_network=None,
    target_network=None,
    diffnetwork_file=None,
    output_dir="ananse_results",
    n_top_tfs=50,
    n_top_targets=100,
    min_interaction_score=0.0
):
    """
    Export all ANANSE results to clean, human-readable CSV files.

    Exports:
    - top_tfs.csv: Top TFs ranked by influence score
    - top_tf_targets_source.csv: Top TF-gene interactions in source network
    - top_tf_targets_target.csv: Top TF-gene interactions in target network
    - network_summary.csv: Per-TF network statistics

    Parameters
    ----------
    influence_file : str
        Path to influence.tsv from ananse influence
    source_network : str, optional
        Path to source network.tsv from ananse network
    target_network : str, optional
        Path to target network.tsv from ananse network
    diffnetwork_file : str, optional
        Path to influence_diffnetwork.tsv
    output_dir : str
        Output directory for exported files (default: "ananse_results")
    n_top_tfs : int
        Number of top TFs to export (default: 50)
    n_top_targets : int
        Number of top target genes per TF to export (default: 100)
    min_interaction_score : float
        Minimum interaction score to include in network exports (default: 0.0)

    Returns
    -------
    dict : Mapping of output name → file path

    Example
    -------
    >>> files = export_ananse_results(
    ...     influence_file='influence.tsv',
    ...     source_network='source.network.tsv',
    ...     target_network='target.network.tsv',
    ...     output_dir='results'
    ... )
    """
    os.makedirs(output_dir, exist_ok=True)
    exported = {}

    print("\n=== Exporting ANANSE Results ===")

    # --- 1. Top TFs ---
    influence = pd.read_csv(influence_file, sep='\t')
    top_tfs = influence.nlargest(n_top_tfs, 'influence_score')

    top_tfs_file = os.path.join(output_dir, "top_tfs.csv")
    top_tfs.to_csv(top_tfs_file, index=False)
    exported['top_tfs'] = top_tfs_file
    print(f"  ✓ Top {len(top_tfs)} TFs: {top_tfs_file}")

    # --- 2. Source network (top interactions) ---
    if source_network and os.path.exists(source_network):
        src_net = _load_and_filter_network(
            source_network, top_tfs['factor'].tolist(),
            n_top_targets, min_interaction_score
        )
        src_file = os.path.join(output_dir, "top_tf_targets_source.csv")
        src_net.to_csv(src_file, index=False)
        exported['source_network_top'] = src_file
        print(f"  ✓ Source network (top interactions): {src_file}")

    # --- 3. Target network (top interactions) ---
    if target_network and os.path.exists(target_network):
        tgt_net = _load_and_filter_network(
            target_network, top_tfs['factor'].tolist(),
            n_top_targets, min_interaction_score
        )
        tgt_file = os.path.join(output_dir, "top_tf_targets_target.csv")
        tgt_net.to_csv(tgt_file, index=False)
        exported['target_network_top'] = tgt_file
        print(f"  ✓ Target network (top interactions): {tgt_file}")

    # --- 4. Network summary (per-TF statistics) ---
    if source_network and target_network:
        summary = _compute_network_summary(
            source_network, target_network,
            top_tfs['factor'].tolist()
        )
        summary_file = os.path.join(output_dir, "network_summary.csv")
        summary.to_csv(summary_file, index=False)
        exported['network_summary'] = summary_file
        print(f"  ✓ Network summary: {summary_file}")

    # --- 5. Diffnetwork (top edges) ---
    if diffnetwork_file and os.path.exists(diffnetwork_file):
        diff = pd.read_csv(diffnetwork_file, sep='\t')
        diff_top = diff[diff['tf'].isin(top_tfs['factor'].head(20))]
        diff_file = os.path.join(output_dir, "diffnetwork_top20_tfs.csv")
        diff_top.to_csv(diff_file, index=False)
        exported['diffnetwork_top'] = diff_file
        print(f"  ✓ Diffnetwork (top 20 TFs): {diff_file}")

    # --- Print summary ---
    print(f"\n=== Export Complete ===")
    print(f"Output directory: {output_dir}")
    print(f"\nTop 10 TFs by influence score:")
    print(top_tfs[['factor', 'influence_score']].head(10).to_string(index=False))
    print()

    return exported


def get_tf_targets(network_file, tf_name, n_top=50, min_score=0.0):
    """
    Get top target genes for a specific TF from a network file.

    Parameters
    ----------
    network_file : str
        Path to network.tsv from ananse network
    tf_name : str
        TF name (HGNC symbol)
    n_top : int
        Number of top targets to return (default: 50)
    min_score : float
        Minimum interaction score (default: 0.0)

    Returns
    -------
    pd.DataFrame : TF-target interactions sorted by score

    Example
    -------
    >>> targets = get_tf_targets('target.network.tsv', 'GATA4', n_top=20)
    >>> print(targets)
    """
    network = pd.read_csv(network_file, sep='\t')

    # Handle different column name conventions
    tf_col = 'tf' if 'tf' in network.columns else network.columns[0]
    target_col = 'target' if 'target' in network.columns else network.columns[1]
    score_col = 'prob' if 'prob' in network.columns else network.columns[2]

    tf_targets = network[network[tf_col] == tf_name]
    if min_score > 0:
        tf_targets = tf_targets[tf_targets[score_col] >= min_score]

    return tf_targets.nlargest(n_top, score_col)


def compare_networks(source_network_file, target_network_file, tf_name):
    """
    Compare TF-target interactions between source and target networks.

    Parameters
    ----------
    source_network_file : str
        Path to source network.tsv
    target_network_file : str
        Path to target network.tsv
    tf_name : str
        TF name to compare

    Returns
    -------
    pd.DataFrame : Merged comparison with source and target scores

    Example
    -------
    >>> comparison = compare_networks('source.network.tsv', 'target.network.tsv', 'GATA4')
    >>> print(comparison.head(10))
    """
    src = get_tf_targets(source_network_file, tf_name, n_top=500)
    tgt = get_tf_targets(target_network_file, tf_name, n_top=500)

    src = src.rename(columns={'prob': 'prob_source'})
    tgt = tgt.rename(columns={'prob': 'prob_target'})

    merged = src.merge(tgt, on=['tf', 'target'], how='outer').fillna(0)
    merged['prob_diff'] = merged['prob_target'] - merged['prob_source']
    merged = merged.sort_values('prob_diff', ascending=False)

    return merged


def _load_and_filter_network(network_file, tf_list, n_top_targets, min_score):
    """Load network and filter to top TFs and interactions."""
    network = pd.read_csv(network_file, sep='\t')

    tf_col = 'tf' if 'tf' in network.columns else network.columns[0]
    score_col = 'prob' if 'prob' in network.columns else network.columns[2]

    # Filter to top TFs
    filtered = network[network[tf_col].isin(tf_list)]

    # Filter by score
    if min_score > 0:
        filtered = filtered[filtered[score_col] >= min_score]

    # Top N targets per TF
    filtered = (filtered
                .sort_values(score_col, ascending=False)
                .groupby(tf_col)
                .head(n_top_targets)
                .reset_index(drop=True))

    return filtered


def _compute_network_summary(source_network_file, target_network_file, tf_list):
    """Compute per-TF network statistics comparing source and target."""
    src = pd.read_csv(source_network_file, sep='\t')
    tgt = pd.read_csv(target_network_file, sep='\t')

    tf_col = 'tf' if 'tf' in src.columns else src.columns[0]
    score_col = 'prob' if 'prob' in src.columns else src.columns[2]

    rows = []
    for tf in tf_list:
        src_tf = src[src[tf_col] == tf]
        tgt_tf = tgt[tgt[tf_col] == tf]

        rows.append({
            'tf': tf,
            'n_targets_source': len(src_tf),
            'n_targets_target': len(tgt_tf),
            'mean_score_source': src_tf[score_col].mean() if len(src_tf) > 0 else 0,
            'mean_score_target': tgt_tf[score_col].mean() if len(tgt_tf) > 0 else 0,
            'max_score_source': src_tf[score_col].max() if len(src_tf) > 0 else 0,
            'max_score_target': tgt_tf[score_col].max() if len(tgt_tf) > 0 else 0,
        })

    summary = pd.DataFrame(rows)
    summary['score_diff'] = summary['mean_score_target'] - summary['mean_score_source']
    return summary.sort_values('score_diff', ascending=False)
