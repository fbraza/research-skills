"""
run_cellbender_batch.py — CellBender batch processing (multiple samples)

Runs CellBender remove-background on multiple samples, either sequentially
or in parallel. Reads sample configuration from a CSV file.

Usage:
    # Run all samples sequentially:
    python run_cellbender_batch.py \
        --samples samples.csv \
        --output-dir results/cellbender/ \
        --cuda

    # Run in parallel (N jobs at a time):
    python run_cellbender_batch.py \
        --samples samples.csv \
        --output-dir results/cellbender/ \
        --cuda \
        --n-jobs 4

    # Dry run (print commands only):
    python run_cellbender_batch.py \
        --samples samples.csv \
        --output-dir results/cellbender/ \
        --dry-run

Input CSV format (samples.csv):
    sample_id,input_path,expected_cells,total_droplets
    sample1,/data/sample1/raw_feature_bc_matrix.h5,5000,15000
    sample2,/data/sample2/raw_feature_bc_matrix.h5,8000,20000
    sample3,/data/sample3/raw_feature_bc_matrix.h5,,        # auto-detect

    Columns:
        sample_id       (required) Unique sample identifier
        input_path      (required) Path to raw count matrix
        expected_cells  (optional) Leave blank for auto-detection
        total_droplets  (optional) Leave blank for auto-detection

Requirements:
    pip install cellbender pandas
"""

import argparse
import os
import subprocess
import sys
import time
import pandas as pd
from concurrent.futures import ProcessPoolExecutor, as_completed


def parse_args():
    parser = argparse.ArgumentParser(
        description='CellBender batch processing',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument('--samples', required=True,
                        help='CSV file with sample information (see docstring for format)')
    parser.add_argument('--output-dir', required=True,
                        help='Output directory (one subdirectory per sample)')
    parser.add_argument('--cuda', action='store_true', default=True,
                        help='Use GPU')
    parser.add_argument('--no-cuda', dest='cuda', action='store_false')
    parser.add_argument('--fpr', type=float, nargs='+', default=[0.01],
                        help='False positive rate(s)')
    parser.add_argument('--epochs', type=int, default=150)
    parser.add_argument('--learning-rate', type=float, default=1e-4)
    parser.add_argument('--model', default='full',
                        choices=['naive', 'simple', 'ambient', 'swapping', 'full'])
    parser.add_argument('--n-jobs', type=int, default=1,
                        help='Number of parallel jobs. Use 1 for sequential. '
                             'WARNING: each job uses one GPU — only parallelize if '
                             'you have multiple GPUs or are running on CPU.')
    parser.add_argument('--skip-existing', action='store_true',
                        help='Skip samples that already have output files')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print commands without running')
    parser.add_argument('--exclude-feature-types', nargs='+', default=None,
                        help='Feature types to exclude (e.g., Peaks)')
    return parser.parse_args()


def load_samples(samples_csv):
    """Load and validate sample CSV."""
    df = pd.read_csv(samples_csv)

    required_cols = ['sample_id', 'input_path']
    for col in required_cols:
        if col not in df.columns:
            print(f"ERROR: samples CSV must have column '{col}'")
            sys.exit(1)

    # Optional columns with defaults
    if 'expected_cells' not in df.columns:
        df['expected_cells'] = None
    if 'total_droplets' not in df.columns:
        df['total_droplets'] = None

    # Validate input files exist
    missing = []
    for _, row in df.iterrows():
        if not os.path.exists(row['input_path']):
            missing.append(row['input_path'])

    if missing:
        print("ERROR: The following input files do not exist:")
        for p in missing:
            print(f"  {p}")
        sys.exit(1)

    print(f"Loaded {len(df)} samples from {samples_csv}")
    return df


def build_sample_command(row, output_dir, args):
    """Build cellbender command for a single sample."""
    sample_id = row['sample_id']
    sample_output_dir = os.path.join(output_dir, sample_id)
    os.makedirs(sample_output_dir, exist_ok=True)

    output_file = os.path.join(sample_output_dir, f'{sample_id}_cellbender.h5')

    cmd = ['cellbender', 'remove-background']
    cmd += ['--input', row['input_path']]
    cmd += ['--output', output_file]

    if args.cuda:
        cmd.append('--cuda')

    # Per-sample cell counts (if provided)
    if pd.notna(row.get('expected_cells')) and row.get('expected_cells') != '':
        cmd += ['--expected-cells', str(int(row['expected_cells']))]

    if pd.notna(row.get('total_droplets')) and row.get('total_droplets') != '':
        cmd += ['--total-droplets-included', str(int(row['total_droplets']))]

    cmd += ['--fpr'] + [str(f) for f in args.fpr]
    cmd += ['--epochs', str(args.epochs)]
    cmd += ['--learning-rate', str(args.learning_rate)]
    cmd += ['--model', args.model]

    if args.exclude_feature_types:
        cmd += ['--exclude-feature-types'] + args.exclude_feature_types

    # Auto-resume from checkpoint if exists
    ckpt = os.path.join(sample_output_dir, 'ckpt.tar.gz')
    if os.path.exists(ckpt):
        cmd += ['--checkpoint', ckpt]

    return cmd, output_file, sample_output_dir


def run_sample(sample_id, cmd, output_file, log_file):
    """Run CellBender for a single sample. Returns (sample_id, success, elapsed)."""
    t0 = time.time()
    print(f"[{time.strftime('%H:%M:%S')}] Starting: {sample_id}")

    with open(log_file, 'w') as log:
        result = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, check=False)

    elapsed = time.time() - t0
    success = result.returncode == 0

    status = "DONE" if success else "FAILED"
    print(f"[{time.strftime('%H:%M:%S')}] {status}: {sample_id} "
          f"({elapsed/60:.1f} min, exit code {result.returncode})")

    return sample_id, success, elapsed


def collect_metrics(output_dir, sample_ids):
    """Collect metrics.csv from all samples into a summary DataFrame."""
    records = []
    for sid in sample_ids:
        metrics_path = os.path.join(output_dir, sid, f'{sid}_cellbender_metrics.csv')
        if os.path.exists(metrics_path):
            try:
                m = pd.read_csv(metrics_path).iloc[0].to_dict()
                m['sample_id'] = sid
                records.append(m)
            except Exception:
                pass

    if records:
        return pd.DataFrame(records).set_index('sample_id')
    return pd.DataFrame()


def main():
    args = parse_args()

    print("=" * 60)
    print("CellBender Batch Processing")
    print("=" * 60)

    # Load samples
    samples_df = load_samples(args.samples)
    os.makedirs(args.output_dir, exist_ok=True)

    # Build commands
    commands = []
    for _, row in samples_df.iterrows():
        cmd, output_file, sample_dir = build_sample_command(row, args.output_dir, args)
        log_file = os.path.join(sample_dir, f"{row['sample_id']}_run.log")

        # Skip if output exists
        if args.skip_existing and os.path.exists(output_file):
            print(f"  Skipping {row['sample_id']} (output exists)")
            continue

        commands.append((row['sample_id'], cmd, output_file, log_file))

    if not commands:
        print("No samples to process.")
        return

    print(f"\nProcessing {len(commands)} samples")
    print(f"Parallel jobs: {args.n_jobs}")
    print(f"Output dir: {args.output_dir}")

    if args.dry_run:
        print("\nDry run — commands:")
        for sid, cmd, _, _ in commands:
            print(f"\n  [{sid}]")
            print("  " + " \\\n    ".join(cmd))
        return

    # Run
    t_start = time.time()
    results = []

    if args.n_jobs == 1:
        # Sequential
        for sid, cmd, output_file, log_file in commands:
            sid_result = run_sample(sid, cmd, output_file, log_file)
            results.append(sid_result)
    else:
        # Parallel
        if args.cuda and args.n_jobs > 1:
            print("\nWARNING: Running multiple GPU jobs in parallel.")
            print("Ensure you have enough GPUs (CellBender uses 1 GPU per job).")

        with ProcessPoolExecutor(max_workers=args.n_jobs) as executor:
            futures = {
                executor.submit(run_sample, sid, cmd, output_file, log_file): sid
                for sid, cmd, output_file, log_file in commands
            }
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    sid = futures[future]
                    print(f"ERROR in {sid}: {e}")
                    results.append((sid, False, 0))

    # Summary
    total_elapsed = time.time() - t_start
    n_success = sum(1 for _, s, _ in results if s)
    n_failed = len(results) - n_success

    print("\n" + "=" * 60)
    print("BATCH SUMMARY")
    print("=" * 60)
    print(f"  Total samples:  {len(results)}")
    print(f"  Succeeded:      {n_success}")
    print(f"  Failed:         {n_failed}")
    print(f"  Total time:     {total_elapsed/60:.1f} min")

    if n_failed > 0:
        print("\nFailed samples:")
        for sid, success, _ in results:
            if not success:
                log = os.path.join(args.output_dir, sid, f'{sid}_run.log')
                print(f"  {sid} — check log: {log}")

    # Collect and save metrics summary
    sample_ids = [sid for sid, _, _ in results if _]
    metrics_df = collect_metrics(args.output_dir, [sid for sid, s, _ in results if s])

    if not metrics_df.empty:
        summary_path = os.path.join(args.output_dir, 'batch_metrics_summary.csv')
        metrics_df.to_csv(summary_path)
        print(f"\nMetrics summary saved: {summary_path}")

        # Flag potential issues
        print("\nPotential issues:")
        flagged = False
        for sid, row in metrics_df.iterrows():
            issues = []
            if float(row.get('convergence_indicator', 0)) > 1.0:
                issues.append("poor convergence")
            if float(row.get('fraction_counts_removed_from_cells', 0)) > 0.5:
                issues.append(">50% counts removed")
            if float(row.get('ratio_of_found_cells_to_expected_cells', 1)) > 3:
                issues.append("3x more cells than expected")
            if float(row.get('ratio_of_found_cells_to_expected_cells', 1)) < 0.3:
                issues.append("far fewer cells than expected")
            if issues:
                print(f"  {sid}: {', '.join(issues)}")
                flagged = True
        if not flagged:
            print("  None detected.")

    print(f"\nOutputs in: {args.output_dir}")
    print("Next: inspect HTML reports and PDFs for each sample")


if __name__ == '__main__':
    main()
