"""
Core scVI Model Training and Expression Extraction

This module implements the primary scVI training workflow: model setup,
training with hardware-aware acceleration, convergence checking, latent
representation extraction, and scVI-normalized expression retrieval.

All shared utilities (accelerator detection, convergence checking, model
saving, training curve plotting) are imported from setup_scvi.py.

Functions:
  - train_scvi(): Train a scVI model and store the latent representation
  - get_scvi_normalized_expression(): Extract batch-corrected normalized counts

Requirements:
  - scvi-tools >= 1.1: pip install scvi-tools
  - torch: pip install torch
  - scanpy: pip install scanpy
  - matplotlib: pip install matplotlib
  - GPU recommended for training (10-20x faster)
"""

import warnings
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
import scanpy as sc

try:
    import scvi
except ImportError:
    raise ImportError(
        "scvi-tools >= 1.1 is required.\n"
        "Install with: pip install scvi-tools"
    )

from setup_scvi import (
    check_convergence,
    detect_accelerator,
    plot_training_curves,
    save_model_with_metadata,
)


def train_scvi(
    adata: sc.AnnData,
    batch_key: str,
    n_latent: int = 30,
    n_layers: int = 2,
    n_hidden: int = 128,
    gene_likelihood: str = "nb",
    dropout_rate: float = 0.1,
    max_epochs: int = 400,
    early_stopping: bool = True,
    batch_size: int = 128,
    save_model: Optional[Union[str, Path]] = None,
    random_state: int = 0,
) -> Tuple[sc.AnnData, "scvi.model.SCVI"]:
    """
    Train an scVI model and store the latent representation in adata.

    Sets up a scVI model using raw counts (prefers adata.layers['counts'],
    falls back to adata.X), trains with the best available hardware
    accelerator, checks convergence, extracts the latent representation into
    adata.obsm['X_scVI'], and optionally saves the model with metadata and
    training curve plots.

    Parameters
    ----------
    adata : AnnData
        AnnData object containing raw UMI counts.  If adata.var contains a
        'highly_variable' boolean column the model is trained on that gene
        subset only; the latent coordinates are written back to the full
        adata object.
    batch_key : str
        Column in adata.obs that identifies the technical batch / sample.
        Passed directly to SCVI.setup_anndata().
    n_latent : int, optional
        Dimensionality of the latent space (default: 30).
        Use 20 for simple datasets, 30–50 for complex multi-sample atlases.
    n_layers : int, optional
        Number of hidden layers in the encoder/decoder (default: 2).
    n_hidden : int, optional
        Number of nodes in each hidden layer (default: 128).
    gene_likelihood : str, optional
        Likelihood distribution for gene counts.  One of "nb" (negative
        binomial, default), "zinb" (zero-inflated NB), or "poisson"
        (default: "nb").
    dropout_rate : float, optional
        Dropout probability applied during training (default: 0.1).
    max_epochs : int, optional
        Maximum number of training epochs (default: 400).
        Early stopping may terminate training earlier.
    early_stopping : bool, optional
        Stop training when validation ELBO stops improving (default: True).
    batch_size : int, optional
        Mini-batch size during stochastic gradient descent (default: 128).
    save_model : str or Path, optional
        Directory path to save the trained model and metadata JSON.  When
        provided, training curves are also saved to that directory.
        (default: None — model is not persisted to disk)
    random_state : int, optional
        Random seed for reproducibility (default: 0).

    Returns
    -------
    tuple of (AnnData, scvi.model.SCVI)
        - adata: Input AnnData updated with:
            - adata.obsm['X_scVI']: ndarray of shape (n_cells, n_latent)
            - adata.uns['scvi_info']: dict of training metadata
        - model: Trained scvi.model.SCVI instance

    Raises
    ------
    ValueError
        If batch_key is not found in adata.obs.

    Notes
    -----
    Uses the scvi-tools >= 1.1 API.  The deprecated ``use_gpu`` parameter
    is replaced by ``accelerator`` (values: "gpu", "mps", "cpu").

    Examples
    --------
    >>> adata, model = train_scvi(adata, batch_key="sample", n_latent=30)
    >>> sc.pp.neighbors(adata, use_rep="X_scVI")
    >>> sc.tl.umap(adata)
    >>> sc.pl.umap(adata, color=["sample", "cell_type"])
    """
    print("=" * 60)
    print("scVI Model Training")
    print("=" * 60)

    # --- Validate batch key ---
    if batch_key not in adata.obs.columns:
        raise ValueError(
            f"Batch key '{batch_key}' not found in adata.obs. "
            f"Available columns: {list(adata.obs.columns[:10])}"
        )

    n_batches = adata.obs[batch_key].nunique()
    print(f"\n  Cells: {adata.n_obs:,}")
    print(f"  Genes: {adata.n_vars:,}")
    print(f"  Batches ({batch_key}): {n_batches}")

    # --- Subset to HVGs if annotated ---
    if "highly_variable" in adata.var.columns:
        n_hvgs = int(adata.var["highly_variable"].sum())
        print(f"  Subsetting to {n_hvgs:,} highly variable genes for training")
        adata_input = adata[:, adata.var["highly_variable"]].copy()
    else:
        print("  'highly_variable' not found in adata.var — using all genes")
        adata_input = adata.copy()

    # --- Determine count layer ---
    layer = "counts" if "counts" in adata_input.layers else None
    if layer == "counts":
        print("  Count source: adata.layers['counts']")
    else:
        print("  Count source: adata.X (no 'counts' layer found)")

    # --- Setup AnnData for scVI ---
    print("\n  Setting up AnnData with SCVI.setup_anndata()...")
    scvi.model.SCVI.setup_anndata(
        adata_input,
        layer=layer,
        batch_key=batch_key,
    )
    print("  ✓ AnnData registered")

    # --- Build model ---
    print(f"\n  Building model:")
    print(f"    n_latent      = {n_latent}")
    print(f"    n_layers      = {n_layers}")
    print(f"    n_hidden      = {n_hidden}")
    print(f"    gene_likelihood = {gene_likelihood}")
    print(f"    dropout_rate  = {dropout_rate}")

    model = scvi.model.SCVI(
        adata_input,
        n_latent=n_latent,
        n_layers=n_layers,
        n_hidden=n_hidden,
        gene_likelihood=gene_likelihood,
        dropout_rate=dropout_rate,
    )
    print("  ✓ Model built")

    # --- Detect accelerator ---
    accelerator = detect_accelerator()

    # --- Train ---
    print(f"\n  Training parameters:")
    print(f"    max_epochs           = {max_epochs}")
    print(f"    early_stopping       = {early_stopping}")
    print(f"    batch_size           = {batch_size}")
    print(f"    check_val_every_n_epoch = 10")
    print(f"    train_size           = 0.9")
    print(f"    random_state         = {random_state}")
    print(f"\n  Starting training...")

    model.train(
        max_epochs=max_epochs,
        accelerator=accelerator,
        early_stopping=early_stopping,
        batch_size=batch_size,
        check_val_every_n_epoch=10,
        train_size=0.9,
    )
    print("  ✓ Training complete")

    # --- Check convergence ---
    convergence_metrics = check_convergence(model, min_epochs=50)
    if not convergence_metrics["converged"]:
        warnings.warn(
            "scVI model may not have converged. "
            f"Relative loss delta: {convergence_metrics['relative_delta']:.2%}. "
            "Consider increasing max_epochs or adjusting learning rate.",
            UserWarning,
            stacklevel=2,
        )

    # --- Extract latent representation ---
    print("\n  Extracting latent representation...")
    latent = model.get_latent_representation()
    adata.obsm["X_scVI"] = latent
    print(f"  ✓ Stored in adata.obsm['X_scVI'] — shape: {latent.shape}")

    # --- Save model and training curves ---
    if save_model is not None:
        save_path = Path(save_model)
        save_model_with_metadata(model, str(save_path), adata=adata_input)
        plot_training_curves(model, output_dir=str(save_path))

    # --- Store metadata in adata.uns ---
    epochs_trained = convergence_metrics["epochs_trained"]
    train_loss_values = model.history["elbo_train"].values.ravel()
    val_loss = model.history.get("elbo_validation", None)

    scvi_info = {
        "batch_key": batch_key,
        "n_latent": n_latent,
        "n_layers": n_layers,
        "n_hidden": n_hidden,
        "gene_likelihood": gene_likelihood,
        "dropout_rate": dropout_rate,
        "max_epochs": max_epochs,
        "early_stopping": early_stopping,
        "batch_size": batch_size,
        "random_state": random_state,
        "accelerator": accelerator,
        "epochs_trained": epochs_trained,
        "final_train_loss": float(train_loss_values[-1]),
        "final_val_loss": (
            float(val_loss.values.ravel()[-1])
            if val_loss is not None and len(val_loss) > 0
            else None
        ),
        "converged": convergence_metrics["converged"],
        "relative_loss_delta": float(convergence_metrics["relative_delta"]),
        "n_genes_used": adata_input.n_vars,
        "used_hvg_subset": "highly_variable" in adata.var.columns,
        "scvi_tools_version": scvi.__version__,
    }
    adata.uns["scvi_info"] = scvi_info
    print("  ✓ Metadata stored in adata.uns['scvi_info']")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("scVI training complete!")
    print("=" * 60)
    print(f"  Epochs trained : {epochs_trained}")
    print(f"  Final train ELBO: {scvi_info['final_train_loss']:.2f}")
    if scvi_info["final_val_loss"] is not None:
        print(f"  Final val ELBO  : {scvi_info['final_val_loss']:.2f}")
    print(f"  Converged       : {convergence_metrics['converged']}")
    print(f"  Latent shape    : {latent.shape}")

    print("\nNext steps:")
    print("  # Compute neighbours and UMAP from scVI latent space")
    print("  sc.pp.neighbors(adata, use_rep='X_scVI')")
    print("  sc.tl.umap(adata)")
    print("  sc.pl.umap(adata, color=[batch_key, 'cell_type'])")
    print()
    print("  # Retrieve scVI-normalized expression (optional)")
    print("  adata = get_scvi_normalized_expression(model, adata)")
    print()
    print("  # Run Leiden clustering")
    print("  sc.tl.leiden(adata, resolution=0.5)")

    return adata, model


def get_scvi_normalized_expression(
    model: "scvi.model.SCVI",
    adata: sc.AnnData,
    library_size: float = 1e4,
    n_samples: int = 25,
) -> sc.AnnData:
    """
    Retrieve scVI-normalized expression and store it in adata.

    Calls model.get_normalized_expression() to obtain batch-corrected,
    library-size-normalized expression values averaged over ``n_samples``
    Monte Carlo samples from the posterior.  The result is stored in
    adata.layers['scvi_normalized'].

    Parameters
    ----------
    model : scvi.model.SCVI
        A trained scvi.model.SCVI instance.
    adata : AnnData
        AnnData object.  Must be the full (non-subsetted) object that was
        used to store adata.obsm['X_scVI'].  If the model was trained on an
        HVG subset, the normalized expression will cover only those genes;
        the layer is added at the matching variable positions.
    library_size : float, optional
        Target library size for normalization (default: 1e4).
        Expression values are scaled so each cell sums to this value.
    n_samples : int, optional
        Number of posterior samples to average (default: 25).
        Higher values reduce Monte Carlo noise at the cost of runtime.

    Returns
    -------
    AnnData
        The input adata with adata.layers['scvi_normalized'] populated.
        Shape matches adata (n_cells x n_vars).  Genes not in the trained
        model are filled with NaN when the model was trained on an HVG subset.

    Notes
    -----
    scVI-normalized expression removes batch effects and is suitable for
    visualization and gene-level exploration.  It is NOT appropriate as
    input to pseudobulk differential expression — use raw counts for that.

    Examples
    --------
    >>> adata, model = train_scvi(adata, batch_key="sample")
    >>> adata = get_scvi_normalized_expression(model, adata, library_size=1e4)
    >>> sc.pl.umap(adata, color="FOXP3", layer="scvi_normalized")
    """
    print("=" * 60)
    print("Extracting scVI Normalized Expression")
    print("=" * 60)

    print(f"\n  library_size : {library_size:,.0f}")
    print(f"  n_samples    : {n_samples}")
    print(f"  Retrieving normalized expression from model posterior...")

    normalized = model.get_normalized_expression(
        library_size=library_size,
        n_samples=n_samples,
        return_mean=True,
    )

    # normalized is a DataFrame with cells x genes (HVG subset if trained on HVGs)
    n_cells_model, n_genes_model = normalized.shape
    print(f"  ✓ Retrieved expression — shape: ({n_cells_model:,}, {n_genes_model:,})")

    if n_genes_model == adata.n_vars:
        # Model was trained on all genes — direct assignment
        adata.layers["scvi_normalized"] = normalized.values
        print(f"  ✓ Stored in adata.layers['scvi_normalized']")
        print(f"    Shape: {adata.layers['scvi_normalized'].shape}")
    else:
        # Model was trained on HVG subset — embed into full gene space with NaN
        print(
            f"  Model trained on {n_genes_model:,} genes; "
            f"adata has {adata.n_vars:,} genes. "
            "Inserting NaN for genes not in the trained model."
        )
        full_matrix = np.full((adata.n_obs, adata.n_vars), np.nan, dtype=np.float32)
        model_genes = normalized.columns.tolist()
        gene_index = {g: i for i, g in enumerate(adata.var_names)}
        col_positions = [gene_index[g] for g in model_genes if g in gene_index]
        matched_cols = [g for g in model_genes if g in gene_index]
        if len(matched_cols) < n_genes_model:
            warnings.warn(
                f"{n_genes_model - len(matched_cols)} model genes not found in "
                "adata.var_names and will be skipped.",
                UserWarning,
                stacklevel=2,
            )
        full_matrix[:, col_positions] = normalized[matched_cols].values
        adata.layers["scvi_normalized"] = full_matrix
        print(f"  ✓ Stored in adata.layers['scvi_normalized']")
        print(f"    Shape: {adata.layers['scvi_normalized'].shape}")
        print(f"    Genes filled: {len(col_positions):,} / {adata.n_vars:,}")

    print(f"\nNext steps:")
    print("  sc.pl.umap(adata, color='GENE_NAME', layer='scvi_normalized')")
    print("  sc.tl.rank_genes_groups(adata, groupby='leiden',")
    print("      layer='scvi_normalized', method='wilcoxon')")
    print("  NOTE: use raw counts (not scvi_normalized) for pseudobulk DE.")

    return adata


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("run_scvi.py — Example Usage")
    print("=" * 60)
    print()
    print("Minimal workflow (batch integration + UMAP):")
    print()
    print("  import scanpy as sc")
    print("  from run_scvi import train_scvi, get_scvi_normalized_expression")
    print()
    print("  # Load pre-processed AnnData (raw counts in .layers['counts'],")
    print("  # HVGs in .var['highly_variable'], batch in .obs['sample'])")
    print("  adata = sc.read_h5ad('data/adata_preprocessed.h5ad')")
    print()
    print("  # Step 1 — Train scVI")
    print("  adata, model = train_scvi(")
    print("      adata,")
    print("      batch_key='sample',")
    print("      n_latent=30,")
    print("      n_layers=2,")
    print("      n_hidden=128,")
    print("      max_epochs=400,")
    print("      early_stopping=True,")
    print("      save_model='results/scvi_model',")
    print("      random_state=0,")
    print("  )")
    print()
    print("  # Step 2 — Build graph and compute UMAP")
    print("  sc.pp.neighbors(adata, use_rep='X_scVI')")
    print("  sc.tl.umap(adata)")
    print("  sc.pl.umap(adata, color=['sample', 'cell_type'])")
    print()
    print("  # Step 3 (optional) — Retrieve batch-corrected expression")
    print("  adata = get_scvi_normalized_expression(model, adata, library_size=1e4)")
    print("  sc.pl.umap(adata, color='FOXP3', layer='scvi_normalized')")
    print()
    print("  # Save updated AnnData")
    print("  adata.write_h5ad('results/adata_scvi.h5ad')")
