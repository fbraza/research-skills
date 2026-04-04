"""
Semi-Supervised Cell Type Annotation with scANVI

This module implements scANVI (Single-Cell ANnotation using Variational Inference)
for semi-supervised cell type label transfer and batch-integrated latent space
learning. scANVI extends scVI by incorporating cell type labels during training,
improving annotation quality especially for rare or underrepresented populations.

For methodology and best practices, see references/scvi_tools_guide.md

Functions:
  - train_scanvi_from_scvi(): Initialize scANVI from a pretrained scVI model
  - train_scanvi_from_scratch(): Train scANVI without a pretrained scVI model
  - predict_cell_types(): Get cell type predictions with soft probabilities
  - evaluate_predictions(): Evaluate prediction quality against known labels

Requirements:
  - scvi-tools >= 1.1: pip install scvi-tools
  - torch: pip install torch
  - GPU recommended for training (10-20x faster)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional, Union, Dict, Any, Tuple

try:
    import scvi
except ImportError:
    raise ImportError(
        "scvi-tools >= 1.1 is required for this module.\n"
        "Install with: pip install scvi-tools"
    )

import scanpy as sc
import warnings

from setup_scvi import detect_accelerator


def train_scanvi_from_scvi(
    scvi_model: Any,
    adata: sc.AnnData,
    labels_key: str,
    unlabeled_category: str = "Unknown",
    max_epochs: int = 200,
    save_model: Optional[Union[str, Path]] = None,
) -> Tuple[sc.AnnData, Any]:
    """
    Initialize and train scANVI from a pretrained scVI model.

    This is the recommended workflow: train scVI first for unsupervised
    batch integration, then use scANVI to incorporate label supervision.
    The scVI encoder weights are transferred, reducing training time and
    typically improving annotation accuracy.

    Parameters
    ----------
    scvi_model : scvi.model.SCVI
        A trained scVI model instance. Must have been trained on data
        compatible with adata (same genes, same batch setup).
    adata : AnnData
        AnnData object used for training the scVI model.
        Must contain raw counts in adata.layers['counts'] or adata.X.
    labels_key : str
        Column in adata.obs containing cell type labels.
        Unlabeled cells must be marked with unlabeled_category.
    unlabeled_category : str, optional
        String value used to mark unlabeled cells in labels_key
        (default: "Unknown").
    max_epochs : int, optional
        Maximum number of training epochs (default: 200).
        scANVI typically converges faster than scVI due to warm-start
        from pretrained weights.
    save_model : str or Path, optional
        Directory to save the trained scANVI model (default: None).

    Returns
    -------
    tuple of (AnnData, scvi.model.SCANVI)
        adata : AnnData with the following additions:
            - .obsm['X_scANVI']: Integrated latent representation
            - .obs['scanvi_predictions']: Predicted cell type labels
            - .uns['scanvi_info']: Training metadata dict
        model : Trained scANVI model instance

    Notes
    -----
    Requires scvi-tools >= 1.1.
    GPU training is 10-20x faster than CPU.

    Examples
    --------
    >>> import scvi
    >>> scvi.model.SCVI.setup_anndata(adata, layer='counts', batch_key='batch')
    >>> vae = scvi.model.SCVI(adata, n_latent=30)
    >>> vae.train(max_epochs=400)
    >>> adata, scanvi_model = train_scanvi_from_scvi(
    ...     vae, adata, labels_key='cell_type', unlabeled_category='Unknown'
    ... )
    >>> sc.pp.neighbors(adata, use_rep='X_scANVI')
    >>> sc.tl.umap(adata)
    """
    print("=" * 60)
    print("scANVI Training (from pretrained scVI)")
    print("=" * 60)

    # --- Validate labels key ---
    if labels_key not in adata.obs.columns:
        raise ValueError(
            f"Labels key '{labels_key}' not found in adata.obs. "
            f"Available columns: {list(adata.obs.columns[:10])}"
        )

    # --- Label statistics ---
    n_labeled = int((adata.obs[labels_key] != unlabeled_category).sum())
    n_unlabeled = int((adata.obs[labels_key] == unlabeled_category).sum())
    label_values = adata.obs[labels_key][adata.obs[labels_key] != unlabeled_category]
    n_categories = label_values.nunique()

    print(f"\nLabel information:")
    print(f"  Labeled cells:    {n_labeled:,} ({100 * n_labeled / adata.n_obs:.1f}%)")
    print(f"  Unlabeled cells:  {n_unlabeled:,} ({100 * n_unlabeled / adata.n_obs:.1f}%)")
    print(f"  Cell type categories: {n_categories}")
    print(f"  Unlabeled marker: '{unlabeled_category}'")

    if n_labeled == 0:
        raise ValueError(
            f"No labeled cells found. All cells have labels_key == '{unlabeled_category}'. "
            "Provide at least some labeled cells for scANVI to learn from."
        )

    if n_labeled < 10:
        warnings.warn(
            f"Only {n_labeled} labeled cells found. scANVI requires sufficient labeled "
            "examples per class for reliable annotation. Consider labeling more cells."
        )

    # --- Initialize scANVI from scVI ---
    print("\nInitializing scANVI from pretrained scVI model...")
    model = scvi.model.SCANVI.from_scvi_model(
        scvi_model,
        unlabeled_category=unlabeled_category,
        labels_key=labels_key,
    )
    print("  scANVI initialized (scVI encoder weights transferred)")

    # --- Detect accelerator and train ---
    accelerator = detect_accelerator()

    print(f"\nTraining scANVI model...")
    print(f"  Max epochs: {max_epochs}")
    print(f"  Accelerator: {accelerator}")

    model.train(max_epochs=max_epochs, accelerator=accelerator)

    print("  Training complete")

    # --- Extract latent representation ---
    print("\nExtracting latent representation and predictions...")
    latent = model.get_latent_representation()
    adata.obsm["X_scANVI"] = latent
    print(f"  ✓ Added 'X_scANVI' to adata.obsm (shape: {latent.shape})")

    # --- Get predictions ---
    predictions = model.predict()
    adata.obs["scanvi_predictions"] = predictions
    print(f"  ✓ Added 'scanvi_predictions' to adata.obs")

    # --- Accuracy on labeled cells ---
    if n_labeled > 0:
        labeled_mask = adata.obs[labels_key] != unlabeled_category
        true_labels = adata.obs.loc[labeled_mask, labels_key]
        pred_labels = adata.obs.loc[labeled_mask, "scanvi_predictions"]
        accuracy = float((true_labels == pred_labels).mean())
        print(f"\n  Prediction accuracy on labeled cells: {accuracy:.1%}")
    else:
        accuracy = None

    # --- Save model if requested ---
    if save_model is not None:
        save_path = Path(save_model)
        save_path.mkdir(parents=True, exist_ok=True)
        model.save(save_path, overwrite=True)
        print(f"\n  Model saved to: {save_path}")

    # --- Store metadata ---
    adata.uns["scanvi_info"] = {
        "labels_key": labels_key,
        "unlabeled_category": unlabeled_category,
        "n_labeled": n_labeled,
        "n_unlabeled": n_unlabeled,
        "n_categories": int(n_categories),
        "max_epochs": max_epochs,
        "accelerator": accelerator,
        "from_scvi": True,
        "accuracy_on_labeled": accuracy,
    }

    print("\n" + "=" * 60)
    print("scANVI training complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  sc.pp.neighbors(adata, use_rep='X_scANVI')")
    print("  sc.tl.umap(adata)")
    print("  sc.pl.umap(adata, color=['scanvi_predictions', 'cell_type'])")

    return adata, model


def train_scanvi_from_scratch(
    adata: sc.AnnData,
    batch_key: str,
    labels_key: str,
    unlabeled_category: str = "Unknown",
    n_latent: int = 30,
    max_epochs: int = 200,
    save_model: Optional[Union[str, Path]] = None,
) -> Tuple[sc.AnnData, Any]:
    """
    Set up and train scANVI from scratch without a pretrained scVI model.

    Use this when no pretrained scVI model is available. Note that
    train_scanvi_from_scvi() is the recommended approach whenever
    possible, as transferring scVI encoder weights typically yields
    better integration and annotation quality.

    Parameters
    ----------
    adata : AnnData
        AnnData object with raw counts in adata.layers['counts'] or adata.X.
        Should have highly variable genes annotated in adata.var if
        subsetting to HVGs is desired (done upstream).
    batch_key : str
        Column in adata.obs containing batch/sample labels.
    labels_key : str
        Column in adata.obs containing cell type labels.
        Unlabeled cells must be marked with unlabeled_category.
    unlabeled_category : str, optional
        String value used to mark unlabeled cells (default: "Unknown").
    n_latent : int, optional
        Dimensionality of the latent space (default: 30).
        Use 20 for simple datasets, 30 for complex multi-batch data.
    max_epochs : int, optional
        Maximum number of training epochs (default: 200).
    save_model : str or Path, optional
        Directory to save the trained model (default: None).

    Returns
    -------
    tuple of (AnnData, scvi.model.SCANVI)
        adata : AnnData with the following additions:
            - .obsm['X_scANVI']: Integrated latent representation
            - .obs['scanvi_predictions']: Predicted cell type labels
            - .uns['scanvi_info']: Training metadata dict
        model : Trained scANVI model instance

    Notes
    -----
    Requires scvi-tools >= 1.1.
    The recommended workflow is to train scVI first, then call
    train_scanvi_from_scvi(). Use this function only when a pretrained
    scVI model is not available.

    Examples
    --------
    >>> adata, model = train_scanvi_from_scratch(
    ...     adata,
    ...     batch_key='batch',
    ...     labels_key='cell_type',
    ...     unlabeled_category='Unknown',
    ...     n_latent=30,
    ...     max_epochs=200,
    ... )
    >>> sc.pp.neighbors(adata, use_rep='X_scANVI')
    >>> sc.tl.umap(adata)
    """
    print("=" * 60)
    print("scANVI Training (from scratch)")
    print("=" * 60)

    print(
        "\n  [NOTE] Recommended: train scVI first, then call train_scanvi_from_scvi()."
    )

    # --- Validate keys ---
    for key, name in [(batch_key, "Batch key"), (labels_key, "Labels key")]:
        if key not in adata.obs.columns:
            raise ValueError(
                f"{name} '{key}' not found in adata.obs. "
                f"Available columns: {list(adata.obs.columns[:10])}"
            )

    # --- Label statistics ---
    n_labeled = int((adata.obs[labels_key] != unlabeled_category).sum())
    n_unlabeled = int((adata.obs[labels_key] == unlabeled_category).sum())
    label_values = adata.obs[labels_key][adata.obs[labels_key] != unlabeled_category]
    n_categories = label_values.nunique()
    n_batches = adata.obs[batch_key].nunique()

    print(f"\nData summary:")
    print(f"  Cells: {adata.n_obs:,}")
    print(f"  Genes: {adata.n_vars:,}")
    print(f"  Batches: {n_batches} ('{batch_key}')")
    print(f"\nLabel information:")
    print(f"  Labeled cells:    {n_labeled:,} ({100 * n_labeled / adata.n_obs:.1f}%)")
    print(f"  Unlabeled cells:  {n_unlabeled:,} ({100 * n_unlabeled / adata.n_obs:.1f}%)")
    print(f"  Cell type categories: {n_categories}")
    print(f"  Unlabeled marker: '{unlabeled_category}'")

    if n_labeled == 0:
        raise ValueError(
            f"No labeled cells found. All cells have labels_key == '{unlabeled_category}'. "
            "Provide at least some labeled cells for scANVI to learn from."
        )

    # --- Auto-detect count layer ---
    layer = "counts" if "counts" in adata.layers else None
    print(
        f"\n  Count layer: "
        + (f"adata.layers['counts']" if layer else "adata.X")
    )

    # --- Setup AnnData ---
    print("\nSetting up AnnData for scANVI...")
    scvi.model.SCANVI.setup_anndata(
        adata,
        layer=layer,
        batch_key=batch_key,
        labels_key=labels_key,
        unlabeled_category=unlabeled_category,
    )
    print("  ✓ AnnData registered with scANVI")

    # --- Create model ---
    model = scvi.model.SCANVI(
        adata,
        n_latent=n_latent,
    )

    print(f"\nModel architecture:")
    print(f"  Latent dimensions: {n_latent}")

    # --- Detect accelerator and train ---
    accelerator = detect_accelerator()

    print(f"\nTraining scANVI model...")
    print(f"  Max epochs: {max_epochs}")
    print(f"  Accelerator: {accelerator}")

    model.train(max_epochs=max_epochs, accelerator=accelerator)

    print("  Training complete")

    # --- Extract latent representation ---
    print("\nExtracting latent representation and predictions...")
    latent = model.get_latent_representation()
    adata.obsm["X_scANVI"] = latent
    print(f"  ✓ Added 'X_scANVI' to adata.obsm (shape: {latent.shape})")

    # --- Get predictions ---
    predictions = model.predict()
    adata.obs["scanvi_predictions"] = predictions
    print(f"  ✓ Added 'scanvi_predictions' to adata.obs")

    # --- Accuracy on labeled cells ---
    if n_labeled > 0:
        labeled_mask = adata.obs[labels_key] != unlabeled_category
        true_labels = adata.obs.loc[labeled_mask, labels_key]
        pred_labels = adata.obs.loc[labeled_mask, "scanvi_predictions"]
        accuracy = float((true_labels == pred_labels).mean())
        print(f"\n  Prediction accuracy on labeled cells: {accuracy:.1%}")
    else:
        accuracy = None

    # --- Save model if requested ---
    if save_model is not None:
        save_path = Path(save_model)
        save_path.mkdir(parents=True, exist_ok=True)
        model.save(save_path, overwrite=True)
        print(f"\n  Model saved to: {save_path}")

    # --- Store metadata ---
    adata.uns["scanvi_info"] = {
        "batch_key": batch_key,
        "labels_key": labels_key,
        "unlabeled_category": unlabeled_category,
        "n_labeled": n_labeled,
        "n_unlabeled": n_unlabeled,
        "n_categories": int(n_categories),
        "n_latent": n_latent,
        "max_epochs": max_epochs,
        "accelerator": accelerator,
        "from_scvi": False,
        "accuracy_on_labeled": accuracy,
    }

    print("\n" + "=" * 60)
    print("scANVI training complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  sc.pp.neighbors(adata, use_rep='X_scANVI')")
    print("  sc.tl.umap(adata)")
    print("  sc.pl.umap(adata, color=['scanvi_predictions', 'cell_type'])")

    return adata, model


def predict_cell_types(
    model: Any,
    adata: sc.AnnData,
) -> pd.DataFrame:
    """
    Get cell type predictions with per-class soft probabilities.

    Returns hard predictions alongside the full soft probability matrix.
    Cells whose maximum predicted probability falls below 0.8 are flagged
    as low-confidence and should be reviewed before accepting the label.

    Parameters
    ----------
    model : scvi.model.SCANVI
        A trained scANVI model instance.
    adata : AnnData
        AnnData object the model was trained on (or a new query dataset
        that has been registered against the trained model).

    Returns
    -------
    pd.DataFrame
        DataFrame indexed by cell barcodes with columns:
        - 'prediction': Hard predicted cell type label
        - 'max_probability': Maximum soft probability across classes
        - 'low_confidence': True if max_probability < 0.8
        - One column per cell type with its predicted probability

    Notes
    -----
    The 0.8 confidence threshold is a sensible default, but the appropriate
    cutoff is dataset-dependent. Always inspect the distribution of
    max_probability before accepting predictions.

    Examples
    --------
    >>> predictions_df = predict_cell_types(model, adata)
    >>> high_conf = predictions_df[~predictions_df['low_confidence']]
    >>> print(high_conf['prediction'].value_counts())
    """
    print("=" * 60)
    print("scANVI Cell Type Prediction")
    print("=" * 60)

    LOW_CONF_THRESHOLD = 0.8

    # --- Hard predictions ---
    print("\nComputing hard predictions...")
    hard_predictions = model.predict()

    # --- Soft probabilities ---
    print("Computing soft probabilities...")
    soft_probs: pd.DataFrame = model.predict(soft=True)

    # Ensure index aligns with adata
    soft_probs.index = adata.obs_names
    cell_types = soft_probs.columns.tolist()

    # --- Build output DataFrame ---
    max_prob = soft_probs.max(axis=1)
    low_confidence = max_prob < LOW_CONF_THRESHOLD

    result = pd.DataFrame(
        {
            "prediction": hard_predictions,
            "max_probability": max_prob.values,
            "low_confidence": low_confidence.values,
        },
        index=adata.obs_names,
    )

    # Append per-class probability columns
    for ct in cell_types:
        result[ct] = soft_probs[ct].values

    # --- Summary ---
    n_low_conf = int(low_confidence.sum())
    print(f"\n  Cells predicted: {len(result):,}")
    print(f"  Low-confidence (max_prob < {LOW_CONF_THRESHOLD}): {n_low_conf:,} "
          f"({100 * n_low_conf / len(result):.1f}%)")
    print(f"\n  Predicted type counts:")
    for cell_type, count in result["prediction"].value_counts().items():
        pct = 100 * count / len(result)
        print(f"    {cell_type}: {count:,} ({pct:.1f}%)")

    print(f"\n  ✓ Prediction DataFrame shape: {result.shape}")

    return result


def evaluate_predictions(
    adata: sc.AnnData,
    labels_key: str,
    predictions_key: str = "scanvi_predictions",
) -> Dict[str, Any]:
    """
    Evaluate scANVI prediction quality against known ground-truth labels.

    Comparison is restricted to labeled cells only (cells not marked as
    the unlabeled category in labels_key). Overall accuracy and per-class
    accuracy are reported, along with a confusion matrix summary for
    classes with prediction errors.

    Parameters
    ----------
    adata : AnnData
        AnnData object with ground-truth labels and scANVI predictions.
    labels_key : str
        Column in adata.obs containing ground-truth cell type labels.
        Cells with the unlabeled category marker are excluded.
    predictions_key : str, optional
        Column in adata.obs containing scANVI predicted labels
        (default: "scanvi_predictions").

    Returns
    -------
    dict
        Evaluation metrics with keys:
        - 'accuracy': float, overall fraction of correct predictions
        - 'per_class_accuracy': dict mapping cell type -> accuracy
        - 'n_labeled': int, number of labeled cells evaluated
        - 'n_low_confidence': int, number of low-confidence cells
          (only populated if 'low_confidence' column is present in adata.obs)
        - 'confusion_pairs': list of dicts with 'true', 'predicted', 'count'
          for all off-diagonal confusion pairs (sorted descending by count)

    Notes
    -----
    Only cells with non-unlabeled ground-truth labels are included in the
    evaluation. Cells labeled as the unlabeled category are intentionally
    skipped because no ground truth is available for them.

    Examples
    --------
    >>> metrics = evaluate_predictions(adata, labels_key='cell_type')
    >>> print(f"Overall accuracy: {metrics['accuracy']:.1%}")
    >>> for ct, acc in metrics['per_class_accuracy'].items():
    ...     print(f"  {ct}: {acc:.1%}")
    """
    print("=" * 60)
    print("scANVI Prediction Evaluation")
    print("=" * 60)

    # --- Validate columns ---
    for key, name in [(labels_key, "Labels key"), (predictions_key, "Predictions key")]:
        if key not in adata.obs.columns:
            raise ValueError(
                f"{name} '{key}' not found in adata.obs. "
                f"Available columns: {list(adata.obs.columns[:10])}"
            )

    # --- Detect unlabeled category from scanvi_info if available ---
    unlabeled_category: Optional[str] = None
    if "scanvi_info" in adata.uns:
        unlabeled_category = adata.uns["scanvi_info"].get("unlabeled_category", None)

    # Identify labeled cells
    if unlabeled_category is not None:
        labeled_mask = adata.obs[labels_key] != unlabeled_category
    else:
        # Heuristic: treat NaN as unlabeled
        labeled_mask = adata.obs[labels_key].notna()

    n_labeled = int(labeled_mask.sum())
    n_total = adata.n_obs

    print(f"\n  Total cells: {n_total:,}")
    print(f"  Labeled cells evaluated: {n_labeled:,}")
    print(f"  Skipped (unlabeled): {n_total - n_labeled:,}")

    if n_labeled == 0:
        raise ValueError(
            "No labeled cells available for evaluation. "
            "All cells appear to be marked with the unlabeled category."
        )

    # --- Subset to labeled cells ---
    true_labels = adata.obs.loc[labeled_mask, labels_key]
    pred_labels = adata.obs.loc[labeled_mask, predictions_key]

    # --- Overall accuracy ---
    correct = true_labels == pred_labels
    accuracy = float(correct.mean())

    # --- Per-class accuracy ---
    cell_types = true_labels.unique().tolist()
    per_class_accuracy: Dict[str, float] = {}
    for ct in sorted(cell_types):
        ct_mask = true_labels == ct
        n_ct = int(ct_mask.sum())
        if n_ct == 0:
            continue
        ct_acc = float((pred_labels[ct_mask] == ct).mean())
        per_class_accuracy[ct] = ct_acc

    # --- Low-confidence count ---
    n_low_confidence: int = 0
    if "low_confidence" in adata.obs.columns:
        n_low_confidence = int(adata.obs["low_confidence"].sum())

    # --- Confusion matrix (off-diagonal pairs only) ---
    confusion_pairs = []
    error_mask = ~correct
    if error_mask.sum() > 0:
        errors_df = pd.DataFrame(
            {
                "true": true_labels[error_mask].values,
                "predicted": pred_labels[error_mask].values,
            }
        )
        pair_counts = (
            errors_df.groupby(["true", "predicted"])
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        confusion_pairs = pair_counts.to_dict(orient="records")

    # --- Print summary ---
    print(f"\n  Overall accuracy: {accuracy:.1%}")
    print(f"\n  Per-class accuracy:")
    for ct, acc in sorted(per_class_accuracy.items(), key=lambda x: x[1]):
        n_ct = int((true_labels == ct).sum())
        marker = "  [LOW]" if acc < 0.8 else ""
        print(f"    {ct}: {acc:.1%}  (n={n_ct:,}){marker}")

    if n_low_confidence > 0:
        print(f"\n  Low-confidence predictions: {n_low_confidence:,}")

    if confusion_pairs:
        print(f"\n  Top confusion pairs (true -> predicted):")
        for pair in confusion_pairs[:10]:
            print(f"    {pair['true']} -> {pair['predicted']}: {pair['count']:,} cells")

    metrics: Dict[str, Any] = {
        "accuracy": accuracy,
        "per_class_accuracy": per_class_accuracy,
        "n_labeled": n_labeled,
        "n_low_confidence": n_low_confidence,
        "confusion_pairs": confusion_pairs,
    }

    print(f"\n  ✓ Evaluation complete")

    return metrics


# Example usage
if __name__ == "__main__":
    print("scANVI Cell Type Annotation Workflows")
    print("=" * 60)
    print()
    print("Recommended workflow (scVI -> scANVI):")
    print()
    print("  import scvi")
    print("  from run_scanvi import (")
    print("      train_scanvi_from_scvi,")
    print("      predict_cell_types,")
    print("      evaluate_predictions,")
    print("  )")
    print()
    print("  # 1. Train scVI first")
    print("  scvi.model.SCVI.setup_anndata(adata, layer='counts', batch_key='batch')")
    print("  vae = scvi.model.SCVI(adata, n_latent=30, n_layers=2)")
    print("  vae.train(max_epochs=400)")
    print()
    print("  # 2. Initialize scANVI from scVI")
    print("  adata, model = train_scanvi_from_scvi(")
    print("      vae, adata, labels_key='cell_type', unlabeled_category='Unknown'")
    print("  )")
    print()
    print("  # 3. Get soft probabilities")
    print("  preds_df = predict_cell_types(model, adata)")
    print()
    print("  # 4. Evaluate on labeled cells")
    print("  metrics = evaluate_predictions(adata, labels_key='cell_type')")
    print()
    print("  # 5. Downstream analysis")
    print("  sc.pp.neighbors(adata, use_rep='X_scANVI')")
    print("  sc.tl.umap(adata)")
    print("  sc.pl.umap(adata, color=['scanvi_predictions', 'cell_type'])")
    print()
    print("Scratch workflow (no pretrained scVI):")
    print()
    print("  from run_scanvi import train_scanvi_from_scratch")
    print()
    print("  adata, model = train_scanvi_from_scratch(")
    print("      adata,")
    print("      batch_key='batch',")
    print("      labels_key='cell_type',")
    print("      unlabeled_category='Unknown',")
    print("      n_latent=30,")
    print("      max_epochs=200,")
    print("  )")
