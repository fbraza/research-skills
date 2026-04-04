"""
run_full_workflow.py — End-to-end Scaden deconvolution pipeline.

Runs the complete Scaden workflow from scRNA-seq data to cell type predictions:
  1. scaden simulate — generate artificial bulk training samples
  2. scaden process  — align genes, log2-transform, scale
  3. scaden train    — train ensemble of 3 DNNs
  4. scaden predict  — deconvolve bulk RNA-seq samples

Can also start from a pre-built training dataset (skip simulation).

Parameters
----------
scrna_data_dir : str
    Directory with scRNA-seq count/celltype files (for simulation).
    Set to None if using a pre-built training dataset.
bulk_file : str
    Path to bulk RNA-seq file to deconvolve (genes × samples, TSV).
output_dir : str
    Root output directory for all intermediate and final files.
n_samples : int
    Number of simulated training samples (default: 5000).
cells_per_sample : int
    Cells per simulated sample (default: 500).
steps : int
    Training steps per model (default: 5000).
pattern : str
    Glob pattern for scRNA-seq count files (default: "*_counts.txt").
prebuilt_training_data : str
    Path to pre-built .h5ad training file (skips simulation step).
seed : int
    Random seed for reproducibility.

Returns
-------
dict with keys:
    predictions_file : str
    model_dir : str
    processed_file : str
    training_file : str
    predictions : pd.DataFrame

Example
-------
    from scripts.run_full_workflow import run_full_scaden_workflow

    # With your own scRNA-seq data
    results = run_full_scaden_workflow(
        scrna_data_dir="scaden_input/",
        bulk_file="bulk_expression.txt",
        output_dir="scaden_results/",
        n_samples=5000,
        steps=5000
    )

    # With a pre-built training dataset
    results = run_full_scaden_workflow(
        scrna_data_dir=None,
        bulk_file="bulk_expression.txt",
        output_dir="scaden_results/",
        prebuilt_training_data="pbmc_training_data.h5ad"
    )
"""

import os
import sys
import time


def run_full_scaden_workflow(
    bulk_file: str,
    output_dir: str = "scaden_results/",
    scrna_data_dir: str = None,
    n_samples: int = 5000,
    cells_per_sample: int = 500,
    steps: int = 5000,
    pattern: str = "*_counts.txt",
    prebuilt_training_data: str = None,
    seed: int = None,
    var_cutoff: float = 0.1,
    batch_size: int = 128,
    learning_rate: float = 0.0001
) -> dict:
    """
    Run the complete Scaden deconvolution pipeline.

    Parameters
    ----------
    bulk_file : str
        Path to bulk RNA-seq file (genes × samples, TSV).
    output_dir : str
        Root output directory.
    scrna_data_dir : str or None
        Directory with scRNA-seq files (for simulation). None if using prebuilt data.
    n_samples : int
        Number of simulated training samples.
    cells_per_sample : int
        Cells per simulated sample.
    steps : int
        Training steps per model.
    pattern : str
        Glob pattern for count files.
    prebuilt_training_data : str or None
        Path to pre-built .h5ad training file (skips simulation).
    seed : int or None
        Random seed.
    var_cutoff : float
        Variance cutoff for gene filtering.
    batch_size : int
        Training batch size.
    learning_rate : float
        Adam learning rate.

    Returns
    -------
    dict with all output file paths and predictions DataFrame.
    """
    # Import step-specific scripts
    sys.path.insert(0, os.path.dirname(__file__))
    from run_simulate import run_scaden_simulate
    from run_process import run_scaden_process
    from run_train import run_scaden_train
    from run_predict import run_scaden_predict

    # Validate inputs
    if not os.path.exists(bulk_file):
        print(f"[ERROR] Bulk file not found: {bulk_file}")
        sys.exit(1)

    if scrna_data_dir is None and prebuilt_training_data is None:
        print("[ERROR] Must provide either scrna_data_dir or prebuilt_training_data")
        sys.exit(1)

    if prebuilt_training_data and not os.path.exists(prebuilt_training_data):
        print(f"[ERROR] Pre-built training data not found: {prebuilt_training_data}")
        sys.exit(1)

    # Set up directory structure
    training_dir = os.path.join(output_dir, "training")
    model_dir = os.path.join(output_dir, "model")
    results_dir = os.path.join(output_dir, "predictions")

    for d in [output_dir, training_dir, model_dir, results_dir]:
        os.makedirs(d, exist_ok=True)

    total_start = time.time()

    print("=" * 60)
    print("SCADEN DECONVOLUTION PIPELINE")
    print("=" * 60)
    print(f"Bulk file:    {bulk_file}")
    print(f"Output dir:   {output_dir}")
    print(f"Steps/model:  {steps}")
    if prebuilt_training_data:
        print(f"Training data: {prebuilt_training_data} (pre-built)")
    else:
        print(f"scRNA-seq dir: {scrna_data_dir}")
        print(f"N samples:    {n_samples}")
    print("=" * 60)

    # ── Step 1: Simulate (or use pre-built) ──────────────────────────
    if prebuilt_training_data:
        print(f"\n[Step 1/3] Using pre-built training data: {prebuilt_training_data}")
        training_file = prebuilt_training_data
        simulate_result = {"h5ad_file": training_file, "n_samples": "pre-built"}
    else:
        print(f"\n[Step 1/4] Simulating training data...")
        simulate_result = run_scaden_simulate(
            data_dir=scrna_data_dir,
            output_dir=training_dir,
            n_samples=n_samples,
            cells_per_sample=cells_per_sample,
            pattern=pattern,
            prefix="data"
        )
        training_file = simulate_result["h5ad_file"]

    # ── Step 2: Process ───────────────────────────────────────────────
    step_num = 2 if prebuilt_training_data else 2
    total_steps = 3 if prebuilt_training_data else 4
    print(f"\n[Step {step_num}/{total_steps}] Processing training data...")
    process_result = run_scaden_process(
        training_data=training_file,
        prediction_data=bulk_file,
        output_dir=training_dir,
        output_name="processed.h5ad",
        var_cutoff=var_cutoff
    )
    processed_file = process_result["processed_file"]

    # ── Step 3: Train ─────────────────────────────────────────────────
    step_num += 1
    print(f"\n[Step {step_num}/{total_steps}] Training Scaden ensemble...")
    train_result = run_scaden_train(
        processed_data=processed_file,
        model_dir=model_dir,
        steps=steps,
        batch_size=batch_size,
        learning_rate=learning_rate,
        seed=seed
    )

    # ── Step 4: Predict ───────────────────────────────────────────────
    step_num += 1
    print(f"\n[Step {step_num}/{total_steps}] Predicting cell type fractions...")
    predict_result = run_scaden_predict(
        bulk_file=bulk_file,
        model_dir=model_dir,
        output_dir=results_dir,
        output_name="scaden_predictions.txt",
        seed=seed
    )

    total_elapsed = time.time() - total_start

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Total time: {total_elapsed/60:.1f} minutes")
    print(f"\nOutput files:")
    print(f"  Predictions:     {predict_result['predictions_file']}")
    print(f"  Model:           {model_dir}")
    print(f"  Processed data:  {processed_file}")
    if not prebuilt_training_data:
        print(f"  Training data:   {training_file}")
    print(f"\nNext steps:")
    print(f"  from scripts.plot_results import plot_deconvolution_results")
    print(f"  plot_deconvolution_results('{predict_result['predictions_file']}', output_dir='{output_dir}/plots/')")
    print(f"  from scripts.export_results import export_predictions")
    print(f"  export_predictions('{predict_result['predictions_file']}', output_dir='{output_dir}')")

    return {
        "predictions_file": predict_result["predictions_file"],
        "predictions": predict_result["predictions"],
        "model_dir": model_dir,
        "processed_file": processed_file,
        "training_file": training_file,
        "n_samples_deconvolved": predict_result["n_samples"],
        "cell_types": predict_result["cell_types"],
        "total_time_min": total_elapsed / 60
    }


def run_example_workflow(output_dir: str = "scaden_example_run/") -> dict:
    """
    Run the complete Scaden pipeline on built-in example data.

    Useful for testing the installation and pipeline end-to-end.

    Parameters
    ----------
    output_dir : str
        Output directory for all files.

    Returns
    -------
    dict with all output paths.
    """
    sys.path.insert(0, os.path.dirname(__file__))
    from load_example_data import generate_example_data

    print("Running Scaden example workflow...")
    example_dir = os.path.join(output_dir, "example_data")
    paths = generate_example_data(out_dir=example_dir)

    return run_full_scaden_workflow(
        bulk_file=paths["bulk_file"],
        output_dir=output_dir,
        scrna_data_dir=example_dir,
        n_samples=500,      # Small for quick testing
        cells_per_sample=100,
        steps=2000,         # Fewer steps for quick testing
        pattern="*_counts.txt"
    )


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run full Scaden deconvolution pipeline")
    parser.add_argument("bulk_file", nargs="?", help="Path to bulk RNA-seq file")
    parser.add_argument("--scrna_data_dir", default=None, help="scRNA-seq data directory")
    parser.add_argument("--prebuilt_training_data", default=None, help="Pre-built .h5ad training file")
    parser.add_argument("--output_dir", default="scaden_results/", help="Output directory")
    parser.add_argument("--n_samples", type=int, default=5000, help="Simulated training samples")
    parser.add_argument("--cells", type=int, default=500, help="Cells per simulated sample")
    parser.add_argument("--steps", type=int, default=5000, help="Training steps per model")
    parser.add_argument("--pattern", default="*_counts.txt", help="Count file pattern")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--example", action="store_true", help="Run example workflow")
    args = parser.parse_args()

    if args.example:
        run_example_workflow(output_dir=args.output_dir)
    elif args.bulk_file:
        run_full_scaden_workflow(
            bulk_file=args.bulk_file,
            output_dir=args.output_dir,
            scrna_data_dir=args.scrna_data_dir,
            prebuilt_training_data=args.prebuilt_training_data,
            n_samples=args.n_samples,
            cells_per_sample=args.cells,
            steps=args.steps,
            pattern=args.pattern,
            seed=args.seed
        )
    else:
        print("Usage: python run_full_workflow.py <bulk_file> [options]")
        print("       python run_full_workflow.py --example")
        parser.print_help()
