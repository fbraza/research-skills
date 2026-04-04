"""
export_results.py — Export and summarize Scaden deconvolution predictions.

Converts Scaden's predictions file into clean, analysis-ready formats:
- Long-format CSV (sample, cell_type, fraction) for R/ggplot2
- Summary statistics (mean ± SD per cell type)
- Ranked cell types by mean fraction
- Differential composition table (if metadata provided)
- Correlation matrix between cell types

Parameters
----------
predictions_file : str
    Path to scaden_predictions.txt.
output_dir : str
    Directory to write exported files.
metadata_file : str or None
    Optional sample metadata TSV for differential composition.
group_column : str
    Metadata column for group comparison (default: "condition").

Returns
-------
dict with paths to all exported files.

Example
-------
    from scripts.export_results import export_predictions

    files = export_predictions(
        predictions_file="scaden_results/scaden_predictions.txt",
        output_dir="scaden_results/",
        metadata_file="sample_metadata.tsv",
        group_column="condition"
    )
"""

import os
import sys


def export_predictions(
    predictions_file: str,
    output_dir: str = "scaden_results/",
    metadata_file: str = None,
    group_column: str = "condition"
) -> dict:
    """
    Export Scaden predictions to analysis-ready formats.

    Parameters
    ----------
    predictions_file : str
        Path to scaden_predictions.txt.
    output_dir : str
        Output directory.
    metadata_file : str or None
        Optional sample metadata TSV.
    group_column : str
        Metadata column for group comparison.

    Returns
    -------
    dict mapping export name to file path.
    """
    import pandas as pd
    import numpy as np

    os.makedirs(output_dir, exist_ok=True)

    # Load predictions
    preds = pd.read_csv(predictions_file, sep="\t", index_col=0)
    print(f"Exporting predictions: {preds.shape[0]} samples × {preds.shape[1]} cell types")

    exported = {}

    # ── 1. Wide-format (original, cleaned) ───────────────────────────
    wide_file = os.path.join(output_dir, "predictions_wide.csv")
    preds.to_csv(wide_file)
    exported["wide"] = wide_file
    print(f"  ✓ Wide-format predictions: {wide_file}")

    # ── 2. Long-format ────────────────────────────────────────────────
    long_df = preds.reset_index().melt(
        id_vars="index",
        var_name="cell_type",
        value_name="fraction"
    ).rename(columns={"index": "sample"})
    long_file = os.path.join(output_dir, "predictions_long.csv")
    long_df.to_csv(long_file, index=False)
    exported["long"] = long_file
    print(f"  ✓ Long-format predictions: {long_file}")

    # ── 3. Summary statistics ─────────────────────────────────────────
    summary = pd.DataFrame({
        "mean_fraction": preds.mean(),
        "std_fraction": preds.std(),
        "median_fraction": preds.median(),
        "min_fraction": preds.min(),
        "max_fraction": preds.max(),
        "n_samples": preds.shape[0]
    }).sort_values("mean_fraction", ascending=False)
    summary_file = os.path.join(output_dir, "predictions_summary.csv")
    summary.to_csv(summary_file)
    exported["summary"] = summary_file
    print(f"  ✓ Summary statistics: {summary_file}")

    # Print summary table
    print(f"\n  Cell type composition summary:")
    print(f"  {'Cell type':<25} {'Mean':>8} {'SD':>8} {'Median':>8}")
    print(f"  {'-'*55}")
    for ct, row in summary.iterrows():
        print(f"  {ct:<25} {row['mean_fraction']:>8.3f} {row['std_fraction']:>8.3f} {row['median_fraction']:>8.3f}")

    # ── 4. Cell type correlation matrix ───────────────────────────────
    corr = preds.corr()
    corr_file = os.path.join(output_dir, "celltype_correlation.csv")
    corr.to_csv(corr_file)
    exported["correlation"] = corr_file
    print(f"\n  ✓ Cell type correlation matrix: {corr_file}")

    # ── 5. Differential composition (if metadata provided) ────────────
    if metadata_file and os.path.exists(metadata_file):
        diff_file = _export_differential_composition(
            preds, metadata_file, group_column, output_dir
        )
        if diff_file:
            exported["differential"] = diff_file

    # ── 6. Per-sample metadata merge (if metadata provided) ───────────
    if metadata_file and os.path.exists(metadata_file):
        metadata = pd.read_csv(metadata_file, sep="\t", index_col=0)
        common = preds.index.intersection(metadata.index)
        if len(common) > 0:
            merged = metadata.loc[common].join(preds.loc[common])
            merged_file = os.path.join(output_dir, "predictions_with_metadata.csv")
            merged.to_csv(merged_file)
            exported["merged"] = merged_file
            print(f"  ✓ Predictions + metadata: {merged_file}")

    print(f"\n✓ Export complete. Files written to: {output_dir}")
    return exported


def _export_differential_composition(preds, metadata_file, group_column, output_dir):
    """Compute differential cell type composition between groups."""
    import pandas as pd
    import numpy as np
    from scipy.stats import mannwhitneyu
    import statsmodels.stats.multitest as mt

    metadata = pd.read_csv(metadata_file, sep="\t", index_col=0)
    common = preds.index.intersection(metadata.index)
    preds_aligned = preds.loc[common]
    meta_aligned = metadata.loc[common]

    if group_column not in meta_aligned.columns:
        print(f"  [WARNING] Column '{group_column}' not found in metadata. Skipping differential analysis.")
        return None

    groups = meta_aligned[group_column].unique()
    if len(groups) != 2:
        print(f"  [WARNING] Differential analysis requires exactly 2 groups, found: {groups}")
        return None

    g1, g2 = groups
    g1_samples = meta_aligned[meta_aligned[group_column] == g1].index
    g2_samples = meta_aligned[meta_aligned[group_column] == g2].index

    results = []
    for ct in preds_aligned.columns:
        v1 = preds_aligned.loc[g1_samples, ct].values
        v2 = preds_aligned.loc[g2_samples, ct].values
        stat, p = mannwhitneyu(v1, v2, alternative="two-sided")
        results.append({
            "cell_type": ct,
            f"mean_{g1}": v1.mean(),
            f"mean_{g2}": v2.mean(),
            "delta": v2.mean() - v1.mean(),
            "p_value": p
        })

    results_df = pd.DataFrame(results)
    results_df["padj"] = mt.multipletests(results_df["p_value"], method="fdr_bh")[1]
    results_df = results_df.sort_values("padj")

    diff_file = os.path.join(output_dir, f"differential_composition_{g1}_vs_{g2}.csv")
    results_df.to_csv(diff_file, index=False)
    print(f"  ✓ Differential composition ({g1} vs {g2}): {diff_file}")

    # Print significant results
    sig = results_df[results_df["padj"] < 0.05]
    if len(sig) > 0:
        print(f"  Significant cell types (padj < 0.05):")
        for _, row in sig.iterrows():
            direction = "↑" if row["delta"] > 0 else "↓"
            print(f"    {direction} {row['cell_type']}: delta={row['delta']:.3f}, padj={row['padj']:.4f}")
    else:
        print(f"  No significant differences found (padj < 0.05)")

    return diff_file


def compute_validation_metrics(predictions_file: str, ground_truth_file: str) -> dict:
    """
    Compute validation metrics comparing Scaden predictions to ground truth.

    Parameters
    ----------
    predictions_file : str
        Path to scaden_predictions.txt.
    ground_truth_file : str
        Path to ground truth fractions (same format as predictions).

    Returns
    -------
    dict with RMSE, Pearson r, and Lin's CCC per cell type and overall.
    """
    import pandas as pd
    import numpy as np
    from scipy.stats import pearsonr

    preds = pd.read_csv(predictions_file, sep="\t", index_col=0)
    truth = pd.read_csv(ground_truth_file, sep="\t", index_col=0)

    # Align
    common_samples = preds.index.intersection(truth.index)
    common_types = preds.columns.intersection(truth.columns)
    preds = preds.loc[common_samples, common_types]
    truth = truth.loc[common_samples, common_types]

    print(f"Validation: {len(common_samples)} samples, {len(common_types)} cell types")

    results = {}

    # Overall metrics
    p_flat = preds.values.flatten()
    t_flat = truth.values.flatten()
    rmse_overall = np.sqrt(np.mean((p_flat - t_flat) ** 2))
    r_overall, _ = pearsonr(t_flat, p_flat)
    ccc_overall = _lin_ccc(t_flat, p_flat)

    results["overall"] = {
        "RMSE": rmse_overall,
        "Pearson_r": r_overall,
        "CCC": ccc_overall
    }

    print(f"\nOverall metrics:")
    print(f"  RMSE: {rmse_overall:.4f}")
    print(f"  Pearson r: {r_overall:.4f}")
    print(f"  Lin's CCC: {ccc_overall:.4f}")

    # Per-cell-type metrics
    print(f"\nPer-cell-type metrics:")
    print(f"  {'Cell type':<25} {'RMSE':>8} {'r':>8} {'CCC':>8}")
    print(f"  {'-'*55}")

    for ct in common_types:
        p = preds[ct].values
        t = truth[ct].values
        rmse = np.sqrt(np.mean((p - t) ** 2))
        r, _ = pearsonr(t, p)
        ccc = _lin_ccc(t, p)
        results[ct] = {"RMSE": rmse, "Pearson_r": r, "CCC": ccc}
        print(f"  {ct:<25} {rmse:>8.4f} {r:>8.4f} {ccc:>8.4f}")

    return results


def _lin_ccc(y_true, y_pred):
    """Compute Lin's Concordance Correlation Coefficient."""
    import numpy as np
    mean_true = np.mean(y_true)
    mean_pred = np.mean(y_pred)
    var_true = np.var(y_true)
    var_pred = np.var(y_pred)
    cov = np.cov(y_true, y_pred)[0, 1]
    ccc = (2 * cov) / (var_true + var_pred + (mean_true - mean_pred) ** 2)
    return ccc


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Export Scaden predictions")
    parser.add_argument("predictions_file", help="Path to scaden_predictions.txt")
    parser.add_argument("--output_dir", default="scaden_results/", help="Output directory")
    parser.add_argument("--metadata_file", default=None, help="Sample metadata TSV")
    parser.add_argument("--group_column", default="condition", help="Grouping column")
    parser.add_argument("--ground_truth", default=None, help="Ground truth fractions for validation")
    args = parser.parse_args()

    export_predictions(
        predictions_file=args.predictions_file,
        output_dir=args.output_dir,
        metadata_file=args.metadata_file,
        group_column=args.group_column
    )

    if args.ground_truth:
        compute_validation_metrics(args.predictions_file, args.ground_truth)
