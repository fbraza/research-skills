"""
run_cellbender.py — CellBender remove-background (single sample)

Wrapper script for running CellBender on a single sample with sensible
defaults, automatic UMI curve inspection, and post-run QC summary.

Usage:
    python run_cellbender.py \
        --input raw_feature_bc_matrix.h5 \
        --output cellbender_output.h5 \
        --cuda

    # With explicit cell/droplet counts:
    python run_cellbender.py \
        --input raw_feature_bc_matrix.h5 \
        --output cellbender_output.h5 \
        --cuda \
        --expected-cells 5000 \
        --total-droplets-included 15000 \
        --fpr 0.01

    # Multiple FPR values:
    python run_cellbender.py \
        --input raw_feature_bc_matrix.h5 \
        --output cellbender_output.h5 \
        --cuda \
        --fpr 0.0 0.01 0.05 0.1

    # CPU only (slower):
    python run_cellbender.py \
        --input raw_feature_bc_matrix.h5 \
        --output cellbender_output.h5 \
        --no-cuda

Requirements:
    pip install cellbender
"""

import argparse
import os
import subprocess
import sys
import time


def parse_args():
    parser = argparse.ArgumentParser(
        description='CellBender remove-background wrapper',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    # Required
    parser.add_argument('--input', required=True,
                        help='Raw (unfiltered) count matrix (.h5, .h5ad, .loom, .mtx dir, etc.)')
    parser.add_argument('--output', required=True,
                        help='Output .h5 file path')

    # Core parameters
    parser.add_argument('--cuda', action='store_true', default=True,
                        help='Use GPU (recommended)')
    parser.add_argument('--no-cuda', dest='cuda', action='store_false',
                        help='Disable GPU (CPU only)')
    parser.add_argument('--expected-cells', type=int, default=None,
                        help='Expected number of cells (auto-detected if not set)')
    parser.add_argument('--total-droplets-included', type=int, default=None,
                        help='Total droplets to analyze (auto-detected if not set)')
    parser.add_argument('--fpr', type=float, nargs='+', default=[0.01],
                        help='False positive rate(s). Multiple values produce multiple outputs.')
    parser.add_argument('--epochs', type=int, default=150,
                        help='Training epochs (150 recommended; max 300)')
    parser.add_argument('--learning-rate', type=float, default=1e-4,
                        help='Learning rate (reduce by 2x if learning curve has spikes)')

    # Advanced
    parser.add_argument('--model', default='full',
                        choices=['naive', 'simple', 'ambient', 'swapping', 'full'],
                        help='Generative model')
    parser.add_argument('--low-count-threshold', type=int, default=5,
                        help='Exclude droplets with fewer UMIs than this')
    parser.add_argument('--posterior-batch-size', type=int, default=128,
                        help='Reduce to 64 if GPU OOM during posterior sampling')
    parser.add_argument('--checkpoint', type=str, default=None,
                        help='Path to checkpoint file (auto-detected if ckpt.tar.gz exists)')
    parser.add_argument('--force-use-checkpoint', action='store_true',
                        help='Bypass checkpoint version matching (for v0.3.1 salvage)')
    parser.add_argument('--exclude-feature-types', nargs='+', default=None,
                        help='Feature types to exclude (e.g., Peaks for ATAC)')
    parser.add_argument('--projected-ambient-count-threshold', type=float, default=0.1,
                        help='Increase to 1-2 to speed up CPU runs')
    parser.add_argument('--empty-drop-training-fraction', type=float, default=0.2,
                        help='Fraction of training minibatch from empty droplets')
    parser.add_argument('--z-dim', type=int, default=64,
                        help='Latent dimension')
    parser.add_argument('--constant-learning-rate', action='store_true',
                        help='Use ClippedAdam (needed to continue training from checkpoint)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--dry-run', action='store_true',
                        help='Print command without running')

    return parser.parse_args()


def check_input(input_path):
    """Validate input file exists and is not filtered."""
    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)

    # Warn if looks like filtered matrix
    if 'filtered' in os.path.basename(input_path).lower():
        print("WARNING: Input filename contains 'filtered'. CellBender requires the "
              "RAW/UNFILTERED matrix. Ensure you are using the correct file.")
        print("  CellRanger v3: outs/raw_feature_bc_matrix.h5")
        print("  CellRanger v2: outs/raw_gene_bc_matrices_h5.h5")

    print(f"Input: {input_path}")
    size_mb = os.path.getsize(input_path) / 1e6
    print(f"  File size: {size_mb:.1f} MB")


def check_output_dir(output_path):
    """Ensure output directory exists."""
    output_dir = os.path.dirname(os.path.abspath(output_path))
    if not os.path.exists(output_dir):
        print(f"Creating output directory: {output_dir}")
        os.makedirs(output_dir, exist_ok=True)

    if not output_path.endswith('.h5'):
        print("WARNING: Output file should have .h5 extension")


def check_gpu():
    """Check GPU availability."""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            print(f"GPU detected: {gpu_name} ({gpu_mem:.1f} GB VRAM)")
            return True
        else:
            print("WARNING: No GPU detected. Running on CPU will be slow.")
            return False
    except ImportError:
        print("WARNING: PyTorch not found. Cannot check GPU.")
        return False


def build_command(args):
    """Build the cellbender command."""
    cmd = ['cellbender', 'remove-background']

    cmd += ['--input', args.input]
    cmd += ['--output', args.output]

    if args.cuda:
        cmd.append('--cuda')

    if args.expected_cells is not None:
        cmd += ['--expected-cells', str(args.expected_cells)]

    if args.total_droplets_included is not None:
        cmd += ['--total-droplets-included', str(args.total_droplets_included)]

    cmd += ['--fpr'] + [str(f) for f in args.fpr]
    cmd += ['--epochs', str(args.epochs)]
    cmd += ['--learning-rate', str(args.learning_rate)]
    cmd += ['--model', args.model]
    cmd += ['--low-count-threshold', str(args.low_count_threshold)]
    cmd += ['--posterior-batch-size', str(args.posterior_batch_size)]
    cmd += ['--projected-ambient-count-threshold',
            str(args.projected_ambient_count_threshold)]
    cmd += ['--empty-drop-training-fraction',
            str(args.empty_drop_training_fraction)]
    cmd += ['--z-dim', str(args.z_dim)]

    if args.checkpoint:
        cmd += ['--checkpoint', args.checkpoint]
    elif os.path.exists('ckpt.tar.gz'):
        print("Found existing ckpt.tar.gz — will resume from checkpoint")
        cmd += ['--checkpoint', 'ckpt.tar.gz']

    if args.force_use_checkpoint:
        cmd.append('--force-use-checkpoint')

    if args.exclude_feature_types:
        cmd += ['--exclude-feature-types'] + args.exclude_feature_types

    if args.constant_learning_rate:
        cmd.append('--constant-learning-rate')

    if args.debug:
        cmd.append('--debug')

    return cmd


def print_qc_summary(output_path):
    """Print a brief QC summary from metrics.csv."""
    metrics_path = output_path.replace('.h5', '_metrics.csv')
    if not os.path.exists(metrics_path):
        return

    try:
        import pandas as pd
        metrics = pd.read_csv(metrics_path)
        m = metrics.iloc[0]

        print("\n" + "=" * 50)
        print("QC SUMMARY")
        print("=" * 50)
        print(f"  Cells found:              {int(m.get('found_cells', 'N/A'))}")
        print(f"  Expected cells:           {m.get('expected_cells', 'auto')}")
        print(f"  Fraction counts removed:  {m.get('fraction_counts_removed', 0):.3f}")
        print(f"  Fraction removed (cells): {m.get('fraction_counts_removed_from_cells', 0):.3f}")
        print(f"  Convergence indicator:    {m.get('convergence_indicator', 'N/A'):.3f}")

        # Flag potential issues
        conv = float(m.get('convergence_indicator', 0))
        frac = float(m.get('fraction_counts_removed_from_cells', 0))
        ratio = float(m.get('ratio_of_found_cells_to_expected_cells', 1))

        if conv > 1.0:
            print("\n  WARNING: Poor convergence (indicator > 1.0).")
            print("  Consider re-running with --epochs 300 or lower --learning-rate.")
        if frac > 0.5:
            print("\n  WARNING: >50% of cell counts removed.")
            print("  Check ambient contamination level and inspect HTML report.")
        if ratio > 3:
            print("\n  WARNING: 3x more cells found than expected.")
            print("  Consider adjusting --expected-cells.")
        if ratio < 0.3:
            print("\n  WARNING: Far fewer cells found than expected.")
            print("  Consider increasing --expected-cells.")

    except Exception as e:
        print(f"  (Could not parse metrics.csv: {e})")


def main():
    args = parse_args()

    print("=" * 60)
    print("CellBender remove-background")
    print("=" * 60)

    # Validate inputs
    check_input(args.input)
    check_output_dir(args.output)

    # Check GPU
    gpu_available = check_gpu()
    if args.cuda and not gpu_available:
        print("WARNING: --cuda requested but no GPU found. Falling back to CPU.")
        args.cuda = False

    # Build command
    cmd = build_command(args)

    print("\nCommand:")
    print("  " + " \\\n    ".join(cmd))

    if args.dry_run:
        print("\n(Dry run — not executing)")
        return

    # Run
    print(f"\nStarting CellBender at {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)

    t0 = time.time()
    result = subprocess.run(cmd, check=False)
    elapsed = time.time() - t0

    print("-" * 60)
    print(f"Finished at {time.strftime('%Y-%m-%d %H:%M:%S')} "
          f"(elapsed: {elapsed/60:.1f} min)")

    if result.returncode != 0:
        print(f"\nERROR: CellBender exited with code {result.returncode}")
        print("Check the log file for details.")
        print("See references/troubleshooting.md for common fixes.")
        sys.exit(result.returncode)

    # QC summary
    print_qc_summary(args.output)

    # List output files
    output_base = args.output.replace('.h5', '')
    print("\nOutput files:")
    for suffix in ['', '_filtered', '_cell_barcodes.csv', '_report.html',
                   '.pdf', '.log', '_metrics.csv']:
        path = output_base + suffix if suffix.startswith('_') or suffix.startswith('.') \
               else args.output
        if suffix == '':
            path = args.output
        else:
            path = output_base + suffix
        if os.path.exists(path):
            size = os.path.getsize(path) / 1e6
            print(f"  {path} ({size:.1f} MB)")

    print("\nNext steps:")
    print("  1. Open output_report.html and check for warnings")
    print("  2. Inspect output.pdf (learning curve, cell calls, PCA)")
    print("  3. Load results: python scripts/qc_and_load.py --output", args.output)


if __name__ == '__main__':
    main()
