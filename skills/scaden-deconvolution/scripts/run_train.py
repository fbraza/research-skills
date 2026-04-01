"""
run_train.py — Wrapper for `scaden train` with resource checks and timing.

Trains the Scaden ensemble of 3 deep neural networks (M256, M512, M1024)
on processed training data. Each model is trained independently for the
specified number of steps using Adam optimizer with L1 loss.

Architecture (fixed):
- M256:  256-128-64-32 nodes, no dropout
- M512:  512-256-128-64 nodes, dropout=0.5
- M1024: 1024-512-256-128 nodes, dropout=0.5
All models: ReLU activations, Softmax output, L1 loss, lr=0.0001, batch=128

Parameters
----------
processed_data : str
    Path to processed .h5ad file (from scaden process).
model_dir : str
    Directory to save trained model weights.
steps : int
    Training steps per model (default: 5000; do NOT exceed for simulated data).
batch_size : int
    Mini-batch size (default: 128).
learning_rate : float
    Adam optimizer learning rate (default: 0.0001).
seed : int
    Random seed for reproducibility (default: None).

Returns
-------
dict with keys:
    model_dir : str — path to trained model directory
    steps : int — steps trained
    training_time_sec : float — total training time in seconds

Example
-------
    from scripts.run_train import run_scaden_train

    result = run_scaden_train(
        processed_data="scaden_training/processed.h5ad",
        model_dir="scaden_model/",
        steps=5000
    )
"""

import os
import subprocess
import sys
import time


def run_scaden_train(
    processed_data: str,
    model_dir: str = "scaden_model/",
    steps: int = 5000,
    batch_size: int = 128,
    learning_rate: float = 0.0001,
    seed: int = None
) -> dict:
    """
    Train the Scaden ensemble model on processed training data.

    Parameters
    ----------
    processed_data : str
        Path to processed .h5ad file.
    model_dir : str
        Directory to save model weights.
    steps : int
        Training steps per model (recommended: 5000).
    batch_size : int
        Mini-batch size.
    learning_rate : float
        Adam optimizer learning rate.
    seed : int or None
        Random seed for reproducibility.

    Returns
    -------
    dict with model_dir, steps, training_time_sec.
    """
    # Validate input
    if not os.path.exists(processed_data):
        print(f"[ERROR] Processed data file not found: {processed_data}")
        sys.exit(1)

    os.makedirs(model_dir, exist_ok=True)

    # Warn about overfitting if steps > 5000
    if steps > 5000:
        print(f"[WARNING] steps={steps} exceeds recommended maximum of 5000.")
        print(f"  Training for more than 5000 steps on simulated data causes overfitting")
        print(f"  and reduces performance on real bulk RNA-seq data (see paper Fig. S3).")

    # Check available memory
    _check_memory()

    print(f"Training Scaden ensemble:")
    print(f"  Processed data: {processed_data}")
    print(f"  Model dir:      {model_dir}")
    print(f"  Steps/model:    {steps}")
    print(f"  Batch size:     {batch_size}")
    print(f"  Learning rate:  {learning_rate}")
    if seed is not None:
        print(f"  Seed:           {seed}")
    print(f"\n  Training 3 models (M256, M512, M1024)...")
    print(f"  Expected time: ~10 min (CPU) or ~3 min (GPU)")

    cmd = [
        "scaden", "train",
        processed_data,
        "--model_dir", model_dir,
        "--steps", str(steps),
        "--batch_size", str(batch_size),
        "--learning_rate", str(learning_rate)
    ]

    if seed is not None:
        cmd += ["--seed", str(seed)]

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time

    if result.returncode != 0:
        print(f"[ERROR] scaden train failed:")
        print(result.stderr)
        sys.exit(1)

    # Verify model files were created
    expected_subdirs = ["M256", "M512", "M1024"]
    missing = []
    for subdir in expected_subdirs:
        subdir_path = os.path.join(model_dir, subdir)
        if not os.path.isdir(subdir_path):
            missing.append(subdir)

    if missing:
        print(f"[WARNING] Expected model subdirectories not found: {missing}")
        print(f"  Contents of {model_dir}: {os.listdir(model_dir)}")
    else:
        print(f"\n✓ Training complete")
        print(f"  Model saved to: {model_dir}")
        print(f"  Subdirectories: {expected_subdirs}")
        print(f"  Training time: {elapsed/60:.1f} minutes")

    return {
        "model_dir": model_dir,
        "steps": steps,
        "training_time_sec": elapsed,
        "training_time_min": elapsed / 60
    }


def _check_memory():
    """Check available system memory and warn if low."""
    try:
        import psutil
        available_gb = psutil.virtual_memory().available / (1024 ** 3)
        total_gb = psutil.virtual_memory().total / (1024 ** 3)
        print(f"  Memory: {available_gb:.1f} GB available / {total_gb:.1f} GB total")
        if available_gb < 4:
            print(f"  [WARNING] Low memory ({available_gb:.1f} GB available)")
            print(f"  Scaden training requires ~1 GB; simulation requires up to 8 GB peak")
    except ImportError:
        pass  # psutil not available, skip check


def check_gpu_availability() -> bool:
    """
    Check if a GPU is available for TensorFlow.

    Returns
    -------
    bool : True if GPU is available.
    """
    try:
        import tensorflow as tf
        gpus = tf.config.list_physical_devices("GPU")
        if gpus:
            print(f"✓ GPU available: {[g.name for g in gpus]}")
            print(f"  Training will use GPU (~3× faster than CPU)")
            return True
        else:
            print(f"  No GPU detected — training will use CPU (~10 min for 5000 steps)")
            print(f"  For GPU support: pip install tensorflow-gpu")
            return False
    except ImportError:
        print(f"  TensorFlow not importable — cannot check GPU")
        return False


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train Scaden ensemble model")
    parser.add_argument("processed_data", help="Path to processed .h5ad file")
    parser.add_argument("--model_dir", default="scaden_model/", help="Model output directory")
    parser.add_argument("--steps", type=int, default=5000, help="Training steps per model")
    parser.add_argument("--batch_size", type=int, default=128, help="Batch size")
    parser.add_argument("--learning_rate", type=float, default=0.0001, help="Learning rate")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    args = parser.parse_args()

    check_gpu_availability()
    run_scaden_train(
        processed_data=args.processed_data,
        model_dir=args.model_dir,
        steps=args.steps,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        seed=args.seed
    )
