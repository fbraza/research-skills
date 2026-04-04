"""
Shared Utilities for scvi-tools Models

This module provides common setup, validation, and diagnostic utilities
used across scvi-tools model workflows (scVI, scANVI, totalVI, etc.).

For methodology and best practices, see references/scvi_tools_guide.md

Functions:
  - validate_anndata_for_scvi(): Validate AnnData meets scvi-tools requirements
  - detect_accelerator(): Detect best available hardware accelerator
  - register_anndata_scvi(): Register AnnData with scVI model (setup_anndata wrapper)
  - plot_training_curves(): Plot ELBO training and validation loss curves
  - check_convergence(): Assess model training convergence
  - save_model_with_metadata(): Save model with JSON metadata sidecar

Requirements:
  - scvi-tools >= 1.1: pip install scvi-tools
  - torch: pip install torch
  - matplotlib: pip install matplotlib
  - GPU recommended for training (10-20x faster)
"""

import numpy as np
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    import scvi
except ImportError:
    raise ImportError(
        "scvi-tools is required for this module.\n"
        "Install with: pip install scvi-tools"
    )

import scanpy as sc
import warnings


def validate_anndata_for_scvi(
    adata: sc.AnnData,
    require_counts: bool = True,
    require_hvg: bool = True,
    batch_key: Optional[str] = None
) -> bool:
    """
    Validate that an AnnData object meets scvi-tools requirements.

    Checks for raw integer counts, highly variable genes, and batch annotations.
    Prints a diagnostic summary of the data.

    Parameters
    ----------
    adata : AnnData
        AnnData object to validate
    require_counts : bool, optional
        Require raw integer counts (default: True)
    require_hvg : bool, optional
        Require highly variable genes annotation (default: True)
    batch_key : str, optional
        Column in adata.obs containing batch labels (default: None)

    Returns
    -------
    bool
        True if validation passes

    Raises
    ------
    ValueError
        If any validation check fails, with a clear diagnostic message

    Examples
    --------
    >>> validate_anndata_for_scvi(adata, batch_key='sample')
    """
    print("=" * 60)
    print("Validating AnnData for scvi-tools")
    print("=" * 60)

    errors: List[str] = []

    # --- Locate count data ---
    count_layer: Optional[str] = None
    if "counts" in adata.layers:
        count_data = adata.layers["counts"]
        count_layer = "layers['counts']"
    else:
        count_data = adata.X
        count_layer = "X"

    print(f"\n  Cells: {adata.n_obs:,}")
    print(f"  Genes: {adata.n_vars:,}")
    print(f"  Count data location: adata.{count_layer}")

    # --- Check counts are valid ---
    if require_counts:
        # Convert sparse to dense for checks (sample for large datasets)
        from scipy import sparse

        if sparse.issparse(count_data):
            # Sample up to 10,000 elements for efficiency
            data_values = count_data.data
        else:
            data_values = np.asarray(count_data).ravel()

        # Check for NaN
        if np.any(np.isnan(data_values)):
            errors.append(
                f"NaN values found in adata.{count_layer}. "
                "Raw counts must not contain NaN."
            )

        # Check for negative values
        if np.any(data_values < 0):
            errors.append(
                f"Negative values found in adata.{count_layer}. "
                "Raw counts must be non-negative."
            )

        # Check integer-like (tolerance for float storage of integers)
        if data_values.size > 0:
            sample_size = min(100_000, data_values.size)
            rng = np.random.default_rng(42)
            sample_idx = rng.choice(data_values.size, size=sample_size, replace=False)
            sample_vals = data_values[sample_idx]
            non_integer = np.any(np.abs(sample_vals - np.round(sample_vals)) > 1e-6)
            if non_integer:
                errors.append(
                    f"Non-integer values found in adata.{count_layer}. "
                    "scvi-tools requires raw integer counts (UMI counts). "
                    "Data may have been normalized or log-transformed."
                )

        if not errors:
            print(f"  Counts valid: no NaN, no negatives, integer-like")

    # --- Check HVGs ---
    n_hvgs = 0
    if require_hvg:
        if "highly_variable" not in adata.var.columns:
            errors.append(
                "No 'highly_variable' column in adata.var. "
                "Run sc.pp.highly_variable_genes() first."
            )
        else:
            n_hvgs = int(adata.var["highly_variable"].sum())
            print(f"  Highly variable genes: {n_hvgs:,}")
            if n_hvgs < 500:
                warnings.warn(
                    f"Only {n_hvgs} HVGs found. Consider increasing n_top_genes "
                    "or checking HVG selection parameters."
                )
    else:
        if "highly_variable" in adata.var.columns:
            n_hvgs = int(adata.var["highly_variable"].sum())
            print(f"  Highly variable genes: {n_hvgs:,} (check not required)")
        else:
            print(f"  Highly variable genes: not annotated (check not required)")

    # --- Check batch key ---
    n_batches = 0
    if batch_key is not None:
        if batch_key not in adata.obs.columns:
            errors.append(
                f"Batch key '{batch_key}' not found in adata.obs. "
                f"Available columns: {list(adata.obs.columns[:10])}"
            )
        else:
            n_batches = adata.obs[batch_key].nunique()
            batch_counts = adata.obs[batch_key].value_counts()
            print(f"  Batch key: '{batch_key}' ({n_batches} batches)")
            print(f"  Batch sizes: min={batch_counts.min():,}, "
                  f"max={batch_counts.max():,}, "
                  f"median={int(batch_counts.median()):,}")

    # --- Report result ---
    if errors:
        error_msg = "\n".join(f"  - {e}" for e in errors)
        print(f"\n  VALIDATION FAILED:")
        print(error_msg)
        raise ValueError(
            f"AnnData validation failed with {len(errors)} error(s):\n{error_msg}"
        )

    print(f"\n  Validation passed")
    return True


def detect_accelerator() -> str:
    """
    Detect the best available hardware accelerator for scvi-tools training.

    Checks for CUDA GPU, Apple MPS, then falls back to CPU.
    Prints device information including name and memory when available.

    Returns
    -------
    str
        Accelerator string for scvi-tools: "gpu", "mps", or "cpu"

    Examples
    --------
    >>> accelerator = detect_accelerator()
    >>> model.train(accelerator=accelerator)
    """
    print("=" * 60)
    print("Detecting Hardware Accelerator")
    print("=" * 60)

    try:
        import torch
    except ImportError:
        print("\n  PyTorch not installed. Using CPU.")
        print(f"  Accelerator: cpu")
        return "cpu"

    # Check CUDA GPU
    if torch.cuda.is_available():
        device_name = torch.cuda.get_device_name(0)
        device_memory = torch.cuda.get_device_properties(0).total_mem / (1024 ** 3)
        n_gpus = torch.cuda.device_count()
        print(f"\n  CUDA GPU detected")
        print(f"  Device: {device_name}")
        print(f"  Memory: {device_memory:.1f} GB")
        print(f"  GPU count: {n_gpus}")
        print(f"  Accelerator: gpu")
        return "gpu"

    # Check Apple MPS
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        print(f"\n  Apple MPS (Metal) detected")
        print(f"  Device: Apple Silicon GPU")
        print(f"  Note: MPS support in scvi-tools may be experimental")
        print(f"  Accelerator: mps")
        return "mps"

    # Fallback to CPU
    print(f"\n  No GPU detected. Using CPU.")
    print(f"  Tip: GPU training is 10-20x faster for scvi-tools models")
    print(f"  Accelerator: cpu")
    return "cpu"


def register_anndata_scvi(
    adata: sc.AnnData,
    batch_key: str,
    layer: Optional[str] = "counts",
    categorical_covariate_keys: Optional[List[str]] = None,
    continuous_covariate_keys: Optional[List[str]] = None
) -> sc.AnnData:
    """
    Register AnnData with scVI model via setup_anndata.

    Wrapper around scvi.model.SCVI.setup_anndata() with pre-validation
    and automatic layer detection.

    Parameters
    ----------
    adata : AnnData
        AnnData object with raw counts
    batch_key : str
        Column in adata.obs containing batch labels
    layer : str, optional
        Layer containing raw counts (default: "counts").
        If None, auto-detects: checks 'counts' layer first, then falls back to X.
    categorical_covariate_keys : list of str, optional
        Additional categorical covariates to model (default: None)
    continuous_covariate_keys : list of str, optional
        Additional continuous covariates to model (default: None)

    Returns
    -------
    AnnData
        The registered AnnData object (modified in place)

    Examples
    --------
    >>> adata = register_anndata_scvi(adata, batch_key='sample')
    >>> model = scvi.model.SCVI(adata)
    """
    print("=" * 60)
    print("Registering AnnData for scVI")
    print("=" * 60)

    # --- Auto-detect layer ---
    if layer is None:
        if "counts" in adata.layers:
            layer = "counts"
            print(f"\n  Auto-detected count layer: adata.layers['counts']")
        else:
            layer = None  # scvi-tools will use adata.X
            print(f"\n  No 'counts' layer found. Using adata.X")
    else:
        if layer not in adata.layers:
            raise ValueError(
                f"Layer '{layer}' not found in adata.layers. "
                f"Available layers: {list(adata.layers.keys())}"
            )
        print(f"\n  Count layer: adata.layers['{layer}']")

    # --- Validate batch key ---
    if batch_key not in adata.obs.columns:
        raise ValueError(
            f"Batch key '{batch_key}' not found in adata.obs. "
            f"Available columns: {list(adata.obs.columns[:10])}"
        )

    n_batches = adata.obs[batch_key].nunique()
    print(f"  Batch key: '{batch_key}' ({n_batches} batches)")

    # --- Validate covariate keys ---
    if categorical_covariate_keys is not None:
        for key in categorical_covariate_keys:
            if key not in adata.obs.columns:
                raise ValueError(
                    f"Categorical covariate '{key}' not found in adata.obs."
                )
        print(f"  Categorical covariates: {categorical_covariate_keys}")

    if continuous_covariate_keys is not None:
        for key in continuous_covariate_keys:
            if key not in adata.obs.columns:
                raise ValueError(
                    f"Continuous covariate '{key}' not found in adata.obs."
                )
        print(f"  Continuous covariates: {continuous_covariate_keys}")

    # --- Register ---
    print(f"\n  Running scvi.model.SCVI.setup_anndata()...")

    scvi.model.SCVI.setup_anndata(
        adata,
        batch_key=batch_key,
        layer=layer,
        categorical_covariate_keys=categorical_covariate_keys,
        continuous_covariate_keys=continuous_covariate_keys,
    )

    print(f"  Registration complete")
    print(f"\n  Data summary:")
    print(f"    Cells: {adata.n_obs:,}")
    print(f"    Genes: {adata.n_vars:,}")
    print(f"    Batches: {n_batches}")

    return adata


def plot_training_curves(
    model: Any,
    output_dir: str = "results"
) -> None:
    """
    Plot ELBO training and validation loss curves from a trained scvi-tools model.

    Saves figures as both PNG (300 DPI) and SVG format.

    Parameters
    ----------
    model : scvi-tools model
        A trained scvi-tools model (e.g., scvi.model.SCVI)
    output_dir : str, optional
        Directory to save plots (default: "results")

    Examples
    --------
    >>> model.train(max_epochs=400)
    >>> plot_training_curves(model, output_dir="results/scvi")
    """
    import matplotlib.pyplot as plt

    print("=" * 60)
    print("Plotting Training Curves")
    print("=" * 60)

    # Extract training history
    train_loss = model.history["elbo_train"]
    val_loss = model.history.get("elbo_validation", None)

    fig, ax = plt.subplots(1, 1, figsize=(8, 5))

    epochs_train = train_loss.index.tolist()
    ax.plot(epochs_train, train_loss.values.ravel(), label="Train ELBO", linewidth=1.5)

    if val_loss is not None and len(val_loss) > 0:
        epochs_val = val_loss.index.tolist()
        ax.plot(epochs_val, val_loss.values.ravel(), label="Validation ELBO", linewidth=1.5)

    ax.set_xlabel("Epoch", fontsize=12)
    ax.set_ylabel("ELBO Loss", fontsize=12)
    ax.set_title("scvi-tools Training Curves", fontsize=14)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    # Save figures
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    png_path = output_path / "training_curves.png"
    svg_path = output_path / "training_curves.svg"

    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(fig)

    print(f"\n  Training epochs: {len(train_loss)}")
    print(f"  Final train ELBO: {train_loss.values.ravel()[-1]:.2f}")
    if val_loss is not None and len(val_loss) > 0:
        print(f"  Final validation ELBO: {val_loss.values.ravel()[-1]:.2f}")
    print(f"  Training curves saved to:")
    print(f"    {png_path}")
    print(f"    {svg_path}")


def check_convergence(
    model: Any,
    min_epochs: int = 50
) -> Dict[str, Any]:
    """
    Assess training convergence of a scvi-tools model.

    Evaluates whether the model has converged based on loss trajectory
    over the final training epochs.

    Parameters
    ----------
    model : scvi-tools model
        A trained scvi-tools model (e.g., scvi.model.SCVI)
    min_epochs : int, optional
        Minimum epochs required for convergence (default: 50)

    Returns
    -------
    dict
        Convergence metrics:
        - final_loss: float, final training ELBO
        - loss_delta: float, mean absolute change over last 10 epochs
        - epochs_trained: int, total epochs trained
        - converged: bool, True if loss_delta < 1% of final_loss AND epochs > min_epochs

    Examples
    --------
    >>> metrics = check_convergence(model, min_epochs=100)
    >>> if not metrics['converged']:
    ...     model.train(max_epochs=200, continue_training=True)
    """
    print("=" * 60)
    print("Checking Model Convergence")
    print("=" * 60)

    train_loss = model.history["elbo_train"]
    loss_values = train_loss.values.ravel()
    epochs_trained = len(loss_values)

    final_loss = float(loss_values[-1])

    # Calculate loss delta over last 10 epochs (or all if fewer)
    n_tail = min(10, epochs_trained)
    tail_losses = loss_values[-n_tail:]
    loss_delta = float(np.mean(np.abs(np.diff(tail_losses))))

    # Convergence criteria
    relative_delta = loss_delta / abs(final_loss) if final_loss != 0 else float("inf")
    converged = (relative_delta < 0.01) and (epochs_trained >= min_epochs)

    metrics = {
        "final_loss": final_loss,
        "loss_delta": loss_delta,
        "relative_delta": relative_delta,
        "epochs_trained": epochs_trained,
        "min_epochs": min_epochs,
        "converged": converged,
    }

    print(f"\n  Epochs trained: {epochs_trained}")
    print(f"  Final train ELBO: {final_loss:.2f}")
    print(f"  Loss delta (last {n_tail} epochs): {loss_delta:.4f}")
    print(f"  Relative delta: {relative_delta:.4%}")
    print(f"  Min epochs required: {min_epochs}")

    if converged:
        print(f"\n  Convergence: PASSED")
        print(f"  Loss is stable (delta < 1% of final loss) and epochs >= {min_epochs}")
    else:
        reasons = []
        if relative_delta >= 0.01:
            reasons.append(
                f"loss still changing ({relative_delta:.2%} >= 1%)"
            )
        if epochs_trained < min_epochs:
            reasons.append(
                f"too few epochs ({epochs_trained} < {min_epochs})"
            )
        print(f"\n  Convergence: NOT CONVERGED")
        print(f"  Reason(s): {'; '.join(reasons)}")
        print(f"  Consider increasing max_epochs or adjusting learning rate")

    return metrics


def save_model_with_metadata(
    model: Any,
    path: str,
    adata: Optional[sc.AnnData] = None
) -> None:
    """
    Save a scvi-tools model with a JSON metadata sidecar file.

    Saves the model using model.save() and writes a companion metadata
    JSON containing model architecture, training info, and software versions.

    Parameters
    ----------
    model : scvi-tools model
        A trained scvi-tools model (e.g., scvi.model.SCVI)
    path : str
        Directory path to save the model
    adata : AnnData, optional
        AnnData used for training. If provided, data shape is recorded
        in metadata. (default: None)

    Examples
    --------
    >>> save_model_with_metadata(model, "results/scvi_model", adata=adata)
    """
    import torch

    print("=" * 60)
    print("Saving Model with Metadata")
    print("=" * 60)

    save_path = Path(path)
    save_path.mkdir(parents=True, exist_ok=True)

    # Save the model
    model.save(save_path, overwrite=True)

    # --- Build metadata ---
    metadata: Dict[str, Any] = {}

    # Model class
    metadata["model_class"] = type(model).__name__

    # Architecture parameters (extract from model if available)
    if hasattr(model, "module"):
        module = model.module
        metadata["n_latent"] = getattr(module, "n_latent", None)
        metadata["n_layers"] = getattr(module, "n_layers", None)
        metadata["n_hidden"] = getattr(module, "n_hidden", None)

    # Training info
    if hasattr(model, "history") and "elbo_train" in model.history:
        train_loss = model.history["elbo_train"]
        metadata["epochs_trained"] = len(train_loss)
        metadata["final_train_loss"] = float(train_loss.values.ravel()[-1])
    else:
        metadata["epochs_trained"] = None
        metadata["final_train_loss"] = None

    # Software versions
    metadata["software_versions"] = {
        "scvi-tools": scvi.__version__,
        "torch": torch.__version__,
        "scanpy": sc.__version__,
        "numpy": np.__version__,
    }

    # Data shape
    if adata is not None:
        metadata["data_shape"] = {
            "n_cells": adata.n_obs,
            "n_genes": adata.n_vars,
        }
    else:
        metadata["data_shape"] = None

    # Write metadata JSON
    metadata_path = save_path / "model_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2, default=str)

    print(f"\n  Model class: {metadata['model_class']}")
    if metadata.get("n_latent") is not None:
        print(f"  Latent dimensions: {metadata['n_latent']}")
    if metadata.get("epochs_trained") is not None:
        print(f"  Epochs trained: {metadata['epochs_trained']}")
    print(f"  scvi-tools version: {scvi.__version__}")
    print(f"  PyTorch version: {torch.__version__}")
    if adata is not None:
        print(f"  Data shape: {adata.n_obs:,} cells x {adata.n_vars:,} genes")

    print(f"\n  Model saved to: {save_path}")
    print(f"  Metadata saved to: {metadata_path}")


# Example usage
if __name__ == "__main__":
    print("scvi-tools Shared Utilities")
    print("=" * 60)
    print()
    print("Example workflow:")
    print()
    print("  from setup_scvi import (")
    print("      validate_anndata_for_scvi,")
    print("      detect_accelerator,")
    print("      register_anndata_scvi,")
    print("      plot_training_curves,")
    print("      check_convergence,")
    print("      save_model_with_metadata,")
    print("  )")
    print()
    print("  # 1. Validate data")
    print("  validate_anndata_for_scvi(adata, batch_key='sample')")
    print()
    print("  # 2. Detect hardware")
    print("  accelerator = detect_accelerator()")
    print()
    print("  # 3. Register AnnData")
    print("  adata = register_anndata_scvi(adata, batch_key='sample')")
    print()
    print("  # 4. Create and train model")
    print("  model = scvi.model.SCVI(adata, n_latent=30, n_layers=2)")
    print("  model.train(max_epochs=400, accelerator=accelerator)")
    print()
    print("  # 5. Check convergence")
    print("  metrics = check_convergence(model, min_epochs=100)")
    print()
    print("  # 6. Plot training curves")
    print("  plot_training_curves(model, output_dir='results/scvi')")
    print()
    print("  # 7. Save model with metadata")
    print("  save_model_with_metadata(model, 'results/scvi_model', adata=adata)")
