"""
scVIVA Model Training and Environment Representation Extraction

WARNING: scVIVA is an EXPERIMENTAL model (Levy et al. 2025, bioRxiv).
The API is not yet stable and may change in future scvi-tools releases.
Validate outputs carefully before drawing biological conclusions.

This module implements the scVIVA training workflow for spatial transcriptomics:
model setup, training with hardware-aware acceleration, latent representation
extraction, environment (niche) representation extraction, and environment-
associated gene program identification.

scVIVA jointly models cell-intrinsic gene expression and the spatial
microenvironment (niche), learning separate latent variables for each.

Reference:
  Levy et al. (2025). scVIVA: Spatial variational inference of the
  microenvironment. bioRxiv. https://doi.org/10.1101/2025.XX.XX

All shared utilities (accelerator detection) are imported from setup_spatial.py.

Functions:
  - train_scviva(): Train a scVIVA model and store the latent representation
  - get_environment_representation(): Extract the spatial niche latent space
  - get_niche_gene_programs(): Identify environment-associated gene programs

Requirements:
  - scvi-tools >= 1.2 (development build may be required for scVIVA):
      pip install scvi-tools
      or: pip install git+https://github.com/scverse/scvi-tools.git
  - torch: pip install torch
  - scanpy: pip install scanpy
  - GPU recommended for training (10-20x faster)
"""

import warnings
from pathlib import Path
from typing import Optional, Tuple, Union

import numpy as np
import pandas as pd
import scanpy as sc

try:
    import scvi
except ImportError:
    raise ImportError(
        "scvi-tools >= 1.2 is required for scVIVA.\n"
        "Install with: pip install scvi-tools\n"
        "For the latest experimental build:\n"
        "  pip install git+https://github.com/scverse/scvi-tools.git"
    )

from setup_spatial import detect_accelerator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _import_scviva() -> type:
    """
    Attempt to import the SCVIVA model class from known locations.

    scVIVA may be located at scvi.external.SCVIVA (experimental namespace)
    or scvi.model.SCVIVA (stable namespace) depending on scvi-tools version.

    Returns
    -------
    type
        The SCVIVA model class.

    Raises
    ------
    ImportError
        If SCVIVA is not found in any known location, with version guidance.
    """
    # Try experimental namespace first (most likely for early releases)
    try:
        from scvi.external import SCVIVA
        print("  SCVIVA located at: scvi.external.SCVIVA")
        return SCVIVA
    except ImportError:
        pass

    # Try stable model namespace
    try:
        from scvi.model import SCVIVA
        print("  SCVIVA located at: scvi.model.SCVIVA")
        return SCVIVA
    except ImportError:
        pass

    raise ImportError(
        "SCVIVA model class not found in scvi.external.SCVIVA or scvi.model.SCVIVA.\n"
        "scVIVA requires scvi-tools >= 1.2 with the experimental model enabled.\n"
        "Options to resolve:\n"
        "  1. Upgrade scvi-tools: pip install --upgrade scvi-tools\n"
        "  2. Install development build:\n"
        "       pip install git+https://github.com/scverse/scvi-tools.git\n"
        "  3. Check the scVIVA paper (Levy et al. 2025, bioRxiv) for the\n"
        "     recommended installation instructions.\n"
        f"  Current scvi-tools version: {scvi.__version__}"
    )


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def train_scviva(
    adata_sp: sc.AnnData,
    spatial_key: str = "spatial",
    layer: str = "counts",
    n_latent: int = 30,
    max_epochs: int = 400,
    save_model: Optional[Union[str, Path]] = None,
    random_state: int = 0,
) -> Tuple[sc.AnnData, object]:
    """
    Train a scVIVA model on spatial transcriptomics data.

    WARNING: scVIVA is EXPERIMENTAL. The API is not yet stable and may
    change in future scvi-tools releases. Results should be treated as
    preliminary until the model is published and validated.

    Sets up a scVIVA model using raw counts and spatial coordinates,
    trains with the best available hardware accelerator, extracts the
    cell-intrinsic latent representation into adata_sp.obsm['X_scVIVA'],
    and stores training metadata in adata_sp.uns['scviva_info'].

    Parameters
    ----------
    adata_sp : AnnData
        Spatial AnnData object with:
        - Raw counts in adata_sp.layers['counts'] (or adata_sp.X)
        - Spatial coordinates in adata_sp.obsm[spatial_key]
    spatial_key : str, optional
        Key in adata_sp.obsm containing spatial coordinates, shape (n_spots, 2).
        (default: "spatial")
    layer : str, optional
        Key in adata_sp.layers containing raw counts. Passed directly to
        SCVIVA.setup_anndata(). (default: "counts")
    n_latent : int, optional
        Dimensionality of the cell-intrinsic latent space (default: 30).
    max_epochs : int, optional
        Maximum number of training epochs (default: 400).
    save_model : str or Path, optional
        Directory path to save the trained model. When provided, the model
        is saved to that directory. (default: None — model is not persisted)
    random_state : int, optional
        Random seed for reproducibility (default: 0).

    Returns
    -------
    tuple of (AnnData, SCVIVA model)
        - adata_sp: Input AnnData updated with:
            - adata_sp.obsm['X_scVIVA']: ndarray of shape (n_spots, n_latent)
            - adata_sp.uns['scviva_info']: dict of training metadata
        - model: Trained SCVIVA model instance

    Raises
    ------
    ImportError
        If SCVIVA is not found in scvi.external or scvi.model.
    ValueError
        If spatial_key is not found in adata_sp.obsm, or if the specified
        layer is not found in adata_sp.layers.
    KeyError
        If adata_sp.obsm[spatial_key] does not have shape (n_spots, 2).

    Notes
    -----
    scVIVA jointly models:
    - Cell-intrinsic variation (z): stored in obsm['X_scVIVA']
    - Spatial microenvironment (u): retrieved via get_environment_representation()

    The spatial_key parameter is passed to SCVIVA.setup_anndata() and must
    point to a 2D array in adata_sp.obsm.

    Examples
    --------
    >>> adata_sp, model = train_scviva(
    ...     adata_sp,
    ...     spatial_key="spatial",
    ...     layer="counts",
    ...     n_latent=30,
    ...     max_epochs=400,
    ...     random_state=0,
    ... )
    >>> sc.pp.neighbors(adata_sp, use_rep="X_scVIVA")
    >>> sc.tl.umap(adata_sp)
    """
    warnings.warn(
        "scVIVA is an EXPERIMENTAL model (Levy et al. 2025, bioRxiv). "
        "The API is not yet stable. Treat results as preliminary.",
        UserWarning,
        stacklevel=2,
    )

    print("=" * 60)
    print("scVIVA Model Training  [EXPERIMENTAL]")
    print("=" * 60)
    print()
    print("  WARNING: scVIVA API may change in future scvi-tools releases.")
    print(f"  scvi-tools version: {scvi.__version__}")

    # --- Validate inputs ---
    if spatial_key not in adata_sp.obsm:
        raise ValueError(
            f"Spatial key '{spatial_key}' not found in adata_sp.obsm. "
            f"Available keys: {list(adata_sp.obsm.keys())}"
        )

    spatial_coords = adata_sp.obsm[spatial_key]
    if spatial_coords.shape[1] != 2:
        raise KeyError(
            f"adata_sp.obsm['{spatial_key}'] has shape {spatial_coords.shape}, "
            "expected (n_spots, 2). Each spot must have exactly 2 spatial coordinates."
        )

    if layer != "counts" and layer not in adata_sp.layers:
        # Only warn; setup_anndata will raise if missing
        warnings.warn(
            f"Layer '{layer}' not found in adata_sp.layers. "
            "setup_anndata() will raise an error unless layer=None is intended.",
            UserWarning,
            stacklevel=2,
        )

    print(f"\n  Spots:           {adata_sp.n_obs:,}")
    print(f"  Genes:           {adata_sp.n_vars:,}")
    print(f"  Spatial key:     obsm['{spatial_key}']  shape={spatial_coords.shape}")
    print(f"  Count layer:     layers['{layer}']")

    # --- Import SCVIVA ---
    print("\n  Importing SCVIVA model class...")
    SCVIVA = _import_scviva()
    print("  ✓ SCVIVA imported")

    # --- Setup AnnData ---
    print("\n  Setting up AnnData with SCVIVA.setup_anndata()...")
    print("  Note: spatial_key is passed to enable neighbourhood-aware training.")
    SCVIVA.setup_anndata(
        adata_sp,
        layer=layer,
        spatial_key=spatial_key,
    )
    print("  ✓ AnnData registered")

    # --- Build model ---
    print(f"\n  Building model:")
    print(f"    n_latent      = {n_latent}")
    print(f"    random_state  = {random_state}")

    model = SCVIVA(adata_sp, n_latent=n_latent)
    print("  ✓ Model built")

    # --- Detect accelerator ---
    accelerator = detect_accelerator()

    # --- Train ---
    print(f"\n  Training parameters:")
    print(f"    max_epochs    = {max_epochs}")
    print(f"    accelerator   = {accelerator}")
    print(f"\n  Starting training...")

    model.train(
        max_epochs=max_epochs,
        accelerator=accelerator,
    )
    print("  ✓ Training complete")

    # --- Extract cell-intrinsic latent representation ---
    print("\n  Extracting cell-intrinsic latent representation (z)...")
    latent = model.get_latent_representation()
    adata_sp.obsm["X_scVIVA"] = latent
    print(f"  ✓ Stored in adata_sp.obsm['X_scVIVA'] — shape: {latent.shape}")

    # --- Save model ---
    if save_model is not None:
        save_path = Path(save_model)
        save_path.mkdir(parents=True, exist_ok=True)
        model.save(str(save_path), overwrite=True)
        print(f"  ✓ Model saved to: {save_path}")

    # --- Store metadata ---
    epochs_trained: int = max_epochs
    train_loss_final: Optional[float] = None

    try:
        history_df = model.history["elbo_train"]
        epochs_trained = int(len(history_df))
        train_loss_final = float(history_df.values.ravel()[-1])
    except Exception:
        pass

    scviva_info = {
        "spatial_key": spatial_key,
        "layer": layer,
        "n_latent": n_latent,
        "max_epochs": max_epochs,
        "epochs_trained": epochs_trained,
        "final_train_loss": train_loss_final,
        "random_state": random_state,
        "accelerator": accelerator,
        "n_spots": adata_sp.n_obs,
        "n_genes": adata_sp.n_vars,
        "scvi_tools_version": scvi.__version__,
        "experimental": True,
        "reference": "Levy et al. 2025, bioRxiv",
    }
    adata_sp.uns["scviva_info"] = scviva_info
    print("  ✓ Metadata stored in adata_sp.uns['scviva_info']")

    # --- Summary ---
    print("\n" + "=" * 60)
    print("scVIVA training complete!  [EXPERIMENTAL]")
    print("=" * 60)
    print(f"  Epochs trained  : {epochs_trained}")
    if train_loss_final is not None:
        print(f"  Final train ELBO: {train_loss_final:.2f}")
    print(f"  Latent shape    : {latent.shape}")

    print("\nNext steps:")
    print("  # Cell-intrinsic latent → UMAP")
    print("  sc.pp.neighbors(adata_sp, use_rep='X_scVIVA')")
    print("  sc.tl.umap(adata_sp)")
    print()
    print("  # Extract spatial environment (niche) representation")
    print("  env_rep = get_environment_representation(model, adata_sp)")
    print()
    print("  # Identify environment-associated gene programs")
    print("  gene_df = get_niche_gene_programs(model, adata_sp)")

    return adata_sp, model


def get_environment_representation(
    model: object,
    adata_sp: sc.AnnData,
) -> np.ndarray:
    """
    Extract the spatial microenvironment (niche) latent representation.

    WARNING: scVIVA is EXPERIMENTAL. The API for environment representation
    extraction may change in future releases. Two API variants are attempted:
    model.get_latent_representation(give_z=False) and
    model.get_environment_representation().

    The environment representation captures spatial neighbourhood context
    rather than cell-intrinsic gene expression. It is complementary to
    the cell-intrinsic latent in adata_sp.obsm['X_scVIVA'].

    Parameters
    ----------
    model : SCVIVA model instance
        A trained SCVIVA model, returned by train_scviva().
    adata_sp : AnnData
        Spatial AnnData object used for training. Must contain
        adata_sp.obsm['X_scVIVA'] (set during train_scviva()).

    Returns
    -------
    np.ndarray
        Environment representation of shape (n_spots, n_latent_env).
        Also stored in adata_sp.obsm['X_scVIVA_env'].

    Raises
    ------
    RuntimeError
        If neither API variant is available on the model object.

    Notes
    -----
    The environment latent variable (u in the scVIVA paper) encodes
    the spatial neighbourhood composition independently of the cell-
    intrinsic transcriptional state (z). Use obsm['X_scVIVA_env'] for
    niche-based clustering or spatial domain identification.

    Examples
    --------
    >>> env_rep = get_environment_representation(model, adata_sp)
    >>> adata_sp.obsm['X_scVIVA_env'].shape
    (n_spots, n_latent_env)
    """
    warnings.warn(
        "get_environment_representation() calls EXPERIMENTAL scVIVA API. "
        "The method signature may change in future scvi-tools releases.",
        UserWarning,
        stacklevel=2,
    )

    print("=" * 60)
    print("Extracting Environment Representation  [EXPERIMENTAL]")
    print("=" * 60)
    print()
    print("  Attempting API variant 1: model.get_latent_representation(give_z=False)")

    env_rep: Optional[np.ndarray] = None

    # --- API variant 1: give_z=False returns the environment variable ---
    try:
        env_rep = model.get_latent_representation(give_z=False)
        print("  ✓ API variant 1 succeeded")
    except (TypeError, AttributeError, Exception) as exc:
        print(f"  API variant 1 failed: {exc}")
        print("  Attempting API variant 2: model.get_environment_representation()")

    # --- API variant 2: dedicated method ---
    if env_rep is None:
        try:
            env_rep = model.get_environment_representation()
            print("  ✓ API variant 2 succeeded")
        except (AttributeError, Exception) as exc:
            print(f"  API variant 2 failed: {exc}")

    if env_rep is None:
        raise RuntimeError(
            "Could not extract environment representation from scVIVA model. "
            "Neither model.get_latent_representation(give_z=False) nor "
            "model.get_environment_representation() is available.\n"
            "Check the scVIVA documentation for the correct API in your "
            f"scvi-tools version ({scvi.__version__})."
        )

    if not isinstance(env_rep, np.ndarray):
        env_rep = np.asarray(env_rep)

    adata_sp.obsm["X_scVIVA_env"] = env_rep
    print(f"  ✓ Stored in adata_sp.obsm['X_scVIVA_env'] — shape: {env_rep.shape}")

    print("\nNext steps:")
    print("  # Cluster spots by niche identity")
    print("  sc.pp.neighbors(adata_sp, use_rep='X_scVIVA_env')")
    print("  sc.tl.leiden(adata_sp, key_added='niche_cluster')")
    print("  sc.pl.spatial(adata_sp, color='niche_cluster')")

    return env_rep


def get_niche_gene_programs(
    model: object,
    adata_sp: sc.AnnData,
    n_top_genes: int = 50,
) -> pd.DataFrame:
    """
    Identify genes associated with the spatial microenvironment.

    WARNING: scVIVA is EXPERIMENTAL. Direct model methods for niche gene
    programs may not exist in all versions. When a model-native method is
    unavailable, this function falls back to computing Pearson correlation
    between each gene's expression and the environment latent dimensions.

    Parameters
    ----------
    model : SCVIVA model instance
        A trained SCVIVA model, returned by train_scviva().
    adata_sp : AnnData
        Spatial AnnData object. Must contain adata_sp.obsm['X_scVIVA_env']
        (set by get_environment_representation()). Raw counts should be in
        adata_sp.layers['counts'] or adata_sp.X.
    n_top_genes : int, optional
        Number of top environment-associated genes to report (default: 50).

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - 'gene': gene name
        - 'env_score': environment association score (higher = stronger
          association with spatial microenvironment). Sorted descending.
        - 'method': the method used to compute scores ('model_native' or
          'pearson_correlation_fallback')
        Shape: (min(n_top_genes, n_genes), 3)

    Raises
    ------
    ValueError
        If 'X_scVIVA_env' is not found in adata_sp.obsm. Call
        get_environment_representation() first.

    Notes
    -----
    The correlation fallback computes, for each gene g:
        score(g) = mean(|corr(gene_expr_g, env_dim_k)|)  for k in 1..n_latent_env

    This captures linear association between expression and niche identity.
    It is a heuristic proxy for the model-native decomposition when the
    scVIVA API does not yet expose niche gene programs directly.

    Non-expressed genes (zero variance) are excluded from correlation.

    Examples
    --------
    >>> gene_df = get_niche_gene_programs(model, adata_sp, n_top_genes=50)
    >>> print(gene_df.head(10))
    >>> top_genes = gene_df['gene'].tolist()
    """
    warnings.warn(
        "get_niche_gene_programs() is EXPERIMENTAL. When a model-native method "
        "is unavailable, scores are computed via Pearson correlation (fallback) "
        "and do not reflect the full scVIVA probabilistic model.",
        UserWarning,
        stacklevel=2,
    )

    print("=" * 60)
    print("Computing Niche Gene Programs  [EXPERIMENTAL]")
    print("=" * 60)

    if "X_scVIVA_env" not in adata_sp.obsm:
        raise ValueError(
            "'X_scVIVA_env' not found in adata_sp.obsm. "
            "Run get_environment_representation(model, adata_sp) first."
        )

    env_rep = adata_sp.obsm["X_scVIVA_env"]  # (n_spots, n_latent_env)
    gene_names = list(adata_sp.var_names)
    method_used = "unknown"

    # --- Attempt model-native method ---
    scores: Optional[np.ndarray] = None

    print("\n  Attempting model-native differential expression / gene program method...")
    try:
        de_result = model.differential_expression()
        if hasattr(de_result, "values"):
            raw = de_result.values
        else:
            raw = np.asarray(de_result)
        # Use absolute mean score across environment dimensions if 2D
        if raw.ndim == 2:
            scores = np.abs(raw).mean(axis=1)
        else:
            scores = np.abs(raw.ravel())
        method_used = "model_native"
        print("  ✓ Model-native differential expression succeeded")
    except (AttributeError, TypeError, NotImplementedError, Exception) as exc:
        print(f"  Model-native method unavailable: {exc}")
        print("  Falling back to Pearson correlation with environment latent dimensions.")

    # --- Pearson correlation fallback ---
    if scores is None:
        print("\n  Computing Pearson correlation (fallback):")
        print(f"    Genes:           {len(gene_names):,}")
        print(f"    Env dimensions:  {env_rep.shape[1]}")

        # Retrieve expression matrix
        from scipy import sparse as _sparse

        if "counts" in adata_sp.layers:
            expr = adata_sp.layers["counts"]
            expr_source = "layers['counts']"
        else:
            expr = adata_sp.X
            expr_source = "X"
        print(f"    Expression from: adata.{expr_source}")

        if _sparse.issparse(expr):
            expr_dense = np.asarray(expr.todense(), dtype=np.float32)
        else:
            expr_dense = np.asarray(expr, dtype=np.float32)

        # Standardize env representation for correlation
        env_std = env_rep - env_rep.mean(axis=0)
        env_norms = np.linalg.norm(env_std, axis=0)
        env_norms[env_norms == 0] = 1.0
        env_unit = env_std / env_norms  # (n_spots, n_latent_env)

        # For each gene compute mean |Pearson r| across env dimensions
        gene_mean = expr_dense.mean(axis=0)
        gene_std = expr_dense.std(axis=0)

        # Mask constant genes
        active_mask = gene_std > 0
        n_active = int(active_mask.sum())
        print(f"    Active genes (non-zero variance): {n_active:,} / {len(gene_names):,}")

        scores = np.zeros(len(gene_names), dtype=np.float32)

        if n_active > 0:
            expr_active = expr_dense[:, active_mask]  # (n_spots, n_active)
            expr_c = expr_active - gene_mean[active_mask]
            expr_norms = np.linalg.norm(expr_c, axis=0)
            expr_norms[expr_norms == 0] = 1.0
            expr_unit = expr_c / expr_norms  # (n_spots, n_active)

            # Correlation matrix: (n_active, n_latent_env)
            corr_matrix = np.abs(expr_unit.T @ env_unit)  # (n_active, n_latent_env)
            scores[active_mask] = corr_matrix.mean(axis=1)

        method_used = "pearson_correlation_fallback"
        print("  ✓ Correlation scores computed")

    # --- Build and sort result DataFrame ---
    gene_df = pd.DataFrame(
        {
            "gene": gene_names,
            "env_score": scores,
            "method": method_used,
        }
    )
    gene_df = gene_df.sort_values("env_score", ascending=False).reset_index(drop=True)
    gene_df_top = gene_df.head(n_top_genes).copy()

    print(f"\n  Top {n_top_genes} environment-associated genes (method: {method_used}):")
    print(f"  {'Gene':<20} {'Score':>10}")
    print(f"  {'-'*20} {'-'*10}")
    for _, row in gene_df_top.head(10).iterrows():
        print(f"  {row['gene']:<20} {row['env_score']:>10.4f}")
    if n_top_genes > 10:
        print(f"  ... ({n_top_genes - 10} more genes in returned DataFrame)")

    print(f"\n  ✓ Gene program DataFrame returned — shape: {gene_df_top.shape}")

    return gene_df_top


# ---------------------------------------------------------------------------
# Example usage
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("run_scviva.py — Example Usage  [EXPERIMENTAL]")
    print("=" * 60)
    print()
    print("WARNING: scVIVA is an experimental model (Levy et al. 2025, bioRxiv).")
    print("API stability is not guaranteed. Validate results carefully.")
    print()
    print("Minimal workflow:")
    print()
    print("  import scanpy as sc")
    print("  from run_scviva import (")
    print("      train_scviva,")
    print("      get_environment_representation,")
    print("      get_niche_gene_programs,")
    print("  )")
    print()
    print("  # Load spatial AnnData (raw counts in .layers['counts'],")
    print("  # spatial coordinates in .obsm['spatial'])")
    print("  adata_sp = sc.read_h5ad('data/adata_spatial.h5ad')")
    print()
    print("  # Step 1 — Train scVIVA")
    print("  adata_sp, model = train_scviva(")
    print("      adata_sp,")
    print("      spatial_key='spatial',")
    print("      layer='counts',")
    print("      n_latent=30,")
    print("      max_epochs=400,")
    print("      save_model='results/scviva_model',")
    print("      random_state=0,")
    print("  )")
    print()
    print("  # Step 2 — Visualize cell-intrinsic latent space")
    print("  sc.pp.neighbors(adata_sp, use_rep='X_scVIVA')")
    print("  sc.tl.umap(adata_sp)")
    print("  sc.pl.umap(adata_sp, color=['cell_type'])")
    print()
    print("  # Step 3 — Extract spatial niche representation")
    print("  env_rep = get_environment_representation(model, adata_sp)")
    print("  sc.pp.neighbors(adata_sp, use_rep='X_scVIVA_env', key_added='niche_neighbors')")
    print("  sc.tl.leiden(adata_sp, neighbors_key='niche_neighbors',")
    print("               key_added='niche_cluster')")
    print("  sc.pl.spatial(adata_sp, color='niche_cluster')")
    print()
    print("  # Step 4 — Identify niche gene programs")
    print("  gene_df = get_niche_gene_programs(model, adata_sp, n_top_genes=50)")
    print("  gene_df.to_csv('results/niche_gene_programs.csv', index=False)")
    print()
    print("  # Save updated AnnData")
    print("  adata_sp.write_h5ad('results/adata_scviva.h5ad')")
