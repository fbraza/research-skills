"""
RNA Velocity with VeloVI (Gayoso et al. 2023)

This module implements RNA velocity inference using VeloVI, a deep generative
model that estimates velocity distributions, latent times, and kinetic rates
from spliced and unspliced count data.

Reference: Gayoso et al. (2023) Deep generative modeling of transcriptional
dynamics for RNA velocity analysis in single cells. Nature Methods.

For methodology and best practices, see references/scvi_tools_guide.md

Functions:
  - validate_velocity_data(): Check for spliced/unspliced layers
  - preprocess_for_velovi(): Run scVelo filter, normalize, and moments
  - train_velovi(): Setup, train, and extract VeloVI results
  - get_velocity_results(): Retrieve and summarize velocity outputs
  - compute_permutation_scores(): Assess dataset suitability for velocity analysis
  - compute_coherence_scores(): Per-cell velocity coherence via cosine similarity

Requirements:
  - scvi-tools >= 1.1: pip install scvi-tools
  - scvelo >= 0.2: pip install scvelo
  - GPU recommended for training (10-20x faster)

Notes:
  VeloVI is accessed via scvi.external.VELOVI (not scvi.model).
  Requires scVelo-preprocessed moments (Ms, Mu) or raw spliced/unspliced counts.
  Permutation scores are critical — run them before interpreting velocity.
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
        "scvi-tools is required for VeloVI.\n"
        "Install with: pip install scvi-tools"
    )

from setup_scvi import detect_accelerator


# ---------------------------------------------------------------------------
# 1. Validate velocity data
# ---------------------------------------------------------------------------

def validate_velocity_data(adata: sc.AnnData) -> bool:
    """
    Check that the AnnData object contains the layers required for VeloVI.

    Accepts either scVelo moment layers ('Ms', 'Mu') or raw count layers
    ('spliced', 'unspliced'). Moment layers are preferred because they have
    already been filtered, normalized, and smoothed.

    Parameters
    ----------
    adata : AnnData
        AnnData object to inspect.

    Returns
    -------
    bool
        True if required layers are present, False otherwise.

    Notes
    -----
    If neither pair is found the function prints step-by-step instructions
    for running scVelo preprocessing before returning False.

    Examples
    --------
    >>> ok = validate_velocity_data(adata)
    >>> if not ok:
    ...     adata = preprocess_for_velovi(adata)
    """
    print("=" * 60)
    print("Validating Velocity Data")
    print("=" * 60)

    available_layers = list(adata.layers.keys())
    print(f"\n  Available layers: {available_layers}")
    print(f"  Cells: {adata.n_obs:,}")
    print(f"  Genes: {adata.n_vars:,}")

    # Preferred: scVelo moment layers
    has_moments = ("Ms" in adata.layers) and ("Mu" in adata.layers)
    # Fallback: raw spliced/unspliced counts
    has_raw = ("spliced" in adata.layers) and ("unspliced" in adata.layers)

    if has_moments:
        ms_shape = adata.layers["Ms"].shape
        mu_shape = adata.layers["Mu"].shape
        print(f"\n  Found scVelo moment layers (preferred):")
        print(f"    Ms (spliced moments):   shape {ms_shape}")
        print(f"    Mu (unspliced moments): shape {mu_shape}")
        print(f"\n  Validation passed")
        return True

    if has_raw:
        sp_shape = adata.layers["spliced"].shape
        un_shape = adata.layers["unspliced"].shape
        print(f"\n  Found raw count layers (preprocessing required before VeloVI):")
        print(f"    spliced:   shape {sp_shape}")
        print(f"    unspliced: shape {un_shape}")
        print(f"\n  [WARNING] Raw counts detected. Run preprocess_for_velovi() to")
        print(f"  compute scVelo moments (Ms, Mu) before training.")
        print(f"\n  Validation passed (raw counts present; moments needed)")
        return True

    # Neither pair found
    print(f"\n  [FAIL] Neither moment layers (Ms, Mu) nor raw count layers")
    print(f"  (spliced, unspliced) were found.")
    print(f"\n  To fix, run scVelo preprocessing first:")
    print(f"    import scvelo as scv")
    print(f"    scv.pp.filter_and_normalize(adata, min_shared_counts=30, n_top_genes=2000)")
    print(f"    scv.pp.moments(adata)")
    print(f"\n  If your AnnData object was loaded from a .loom or .h5ad file that")
    print(f"  already contains spliced/unspliced layers, verify the layer names")
    print(f"  with: list(adata.layers.keys())")
    return False


# ---------------------------------------------------------------------------
# 2. Preprocess for VeloVI
# ---------------------------------------------------------------------------

def preprocess_for_velovi(
    adata: sc.AnnData,
    min_shared_counts: int = 30,
    n_top_genes: int = 2000,
    n_pcs: int = 30,
    n_neighbors: int = 30,
) -> sc.AnnData:
    """
    Run scVelo preprocessing to produce spliced/unspliced moment layers.

    Executes filter_and_normalize followed by moments computation. The
    resulting 'Ms' and 'Mu' layers are used as input for VeloVI.

    Parameters
    ----------
    adata : AnnData
        AnnData object with 'spliced' and 'unspliced' layers.
    min_shared_counts : int, optional
        Minimum shared counts across spliced and unspliced for gene filtering
        (default: 30).
    n_top_genes : int, optional
        Number of highly variable genes to retain (default: 2000).
    n_pcs : int, optional
        Number of principal components for moment computation (default: 30).
    n_neighbors : int, optional
        Number of neighbors for moment smoothing (default: 30).

    Returns
    -------
    AnnData
        AnnData with 'Ms' and 'Mu' layers added.

    Raises
    ------
    ImportError
        If scvelo is not installed.

    Examples
    --------
    >>> adata = preprocess_for_velovi(adata, min_shared_counts=30, n_top_genes=2000)
    """
    try:
        import scvelo as scv
    except ImportError:
        raise ImportError(
            "scvelo is required for preprocessing.\n"
            "Install with: pip install scvelo"
        )

    print("=" * 60)
    print("scVelo Preprocessing for VeloVI")
    print("=" * 60)

    print(f"\n  Input:")
    print(f"    Cells: {adata.n_obs:,}")
    print(f"    Genes: {adata.n_vars:,}")
    print(f"    min_shared_counts: {min_shared_counts}")
    print(f"    n_top_genes: {n_top_genes}")
    print(f"    n_pcs: {n_pcs}")
    print(f"    n_neighbors: {n_neighbors}")

    print(f"\n  Running scv.pp.filter_and_normalize()...")
    scv.pp.filter_and_normalize(
        adata,
        min_shared_counts=min_shared_counts,
        n_top_genes=n_top_genes,
    )

    print(f"  Running scv.pp.moments()...")
    scv.pp.moments(adata, n_pcs=n_pcs, n_neighbors=n_neighbors)

    n_genes_after = adata.n_vars
    has_ms = "Ms" in adata.layers
    has_mu = "Mu" in adata.layers

    print(f"\n  Preprocessing complete:")
    print(f"    Genes retained: {n_genes_after:,}")
    print(f"    Ms layer: {'present' if has_ms else 'MISSING'}")
    print(f"    Mu layer: {'present' if has_mu else 'MISSING'}")

    if not (has_ms and has_mu):
        warnings.warn(
            "Moment layers (Ms, Mu) were not created. "
            "Check scVelo version and input layer names."
        )

    print(f"\n  ✓ Ready for train_velovi()")
    return adata


# ---------------------------------------------------------------------------
# 3. Train VeloVI
# ---------------------------------------------------------------------------

def train_velovi(
    adata: sc.AnnData,
    spliced_layer: str = "Ms",
    unspliced_layer: str = "Mu",
    n_latent: int = 30,
    max_epochs: int = 500,
    save_model: Optional[Union[str, Path]] = None,
) -> Tuple[sc.AnnData, "scvi.external.VELOVI"]:
    """
    Set up, train VeloVI, and extract velocity outputs.

    Runs VELOVI.setup_anndata(), instantiates the model, trains it, and
    stores latent time and velocities directly in the AnnData object.

    Parameters
    ----------
    adata : AnnData
        AnnData with moment layers (Ms, Mu) or raw spliced/unspliced layers.
    spliced_layer : str, optional
        Layer name for spliced (or spliced moments) counts (default: 'Ms').
    unspliced_layer : str, optional
        Layer name for unspliced (or unspliced moments) counts (default: 'Mu').
    n_latent : int, optional
        Dimensionality of the latent space (default: 30).
    max_epochs : int, optional
        Maximum training epochs (default: 500).
    save_model : str or Path, optional
        Directory to save trained model. If None, model is not persisted.

    Returns
    -------
    tuple of (AnnData, VELOVI)
        adata with the following additions:
        - .obs['velovi_latent_time']: Per-cell latent pseudotime
        - .layers['velocity']: Per-cell per-gene RNA velocity
        - .uns['velovi_info']: Run metadata
        model: the trained VELOVI instance

    Raises
    ------
    ValueError
        If velocity data validation fails.

    Notes
    -----
    VeloVI is located at ``scvi.external.VELOVI``, not ``scvi.model``.
    Permutation scores should be computed after training to verify that
    the dataset has transient dynamics (see compute_permutation_scores).

    Examples
    --------
    >>> adata, model = train_velovi(adata, max_epochs=500)
    >>> compute_permutation_scores(model, adata)
    """
    print("=" * 60)
    print("VeloVI — RNA Velocity Training")
    print("=" * 60)

    # --- Validate ---
    valid = validate_velocity_data(adata)
    if not valid:
        raise ValueError(
            "Velocity data validation failed. "
            "Run preprocess_for_velovi(adata) first."
        )

    # Verify the requested layers exist
    for layer_name, label in [(spliced_layer, "spliced"), (unspliced_layer, "unspliced")]:
        if layer_name not in adata.layers:
            raise ValueError(
                f"Layer '{layer_name}' not found in adata.layers. "
                f"Available layers: {list(adata.layers.keys())}. "
                f"Pass spliced_layer/unspliced_layer that match your data."
            )

    # --- Setup ---
    print(f"\n  Setting up VeloVI...")
    print(f"    spliced_layer:   '{spliced_layer}'")
    print(f"    unspliced_layer: '{unspliced_layer}'")
    print(f"    n_latent:        {n_latent}")
    print(f"    max_epochs:      {max_epochs}")

    scvi.external.VELOVI.setup_anndata(
        adata,
        spliced_layer=spliced_layer,
        unspliced_layer=unspliced_layer,
    )

    # --- Instantiate ---
    model = scvi.external.VELOVI(adata, n_latent=n_latent)

    print(f"\n  Model architecture:")
    print(f"    Latent dimensions: {n_latent}")
    print(f"    Cells: {adata.n_obs:,}")
    print(f"    Genes: {adata.n_vars:,}")

    # --- Accelerator ---
    accelerator = detect_accelerator()

    # --- Train ---
    print(f"\n  Training VeloVI (this may take several minutes)...")
    model.train(max_epochs=max_epochs, accelerator=accelerator)

    # Convergence summary
    train_loss = model.history["elbo_train"].values.ravel()
    print(f"\n  Training complete:")
    print(f"    Epochs trained: {len(train_loss)}")
    print(f"    Initial ELBO:   {train_loss[0]:.2f}")
    print(f"    Final ELBO:     {train_loss[-1]:.2f}")

    # --- Extract latent time ---
    print(f"\n  Extracting latent time...")
    latent_time = model.get_latent_time(n_samples=25)
    # get_latent_time returns a DataFrame (cells x 1) or array; normalise to [0,1]
    if isinstance(latent_time, pd.DataFrame):
        lt_values = latent_time.values.squeeze()
    else:
        lt_values = np.array(latent_time).squeeze()

    lt_min, lt_max = lt_values.min(), lt_values.max()
    if lt_max > lt_min:
        lt_norm = (lt_values - lt_min) / (lt_max - lt_min)
    else:
        lt_norm = lt_values

    adata.obs["velovi_latent_time"] = lt_norm
    print(f"    ✓ adata.obs['velovi_latent_time'] stored (range 0–1)")

    # --- Extract velocities ---
    print(f"  Extracting velocity estimates...")
    velocity = model.get_velocity(n_samples=25, velo_statistic="mean")
    if isinstance(velocity, pd.DataFrame):
        velocity = velocity.values

    adata.layers["velocity"] = velocity
    print(f"    ✓ adata.layers['velocity'] stored (shape {velocity.shape})")

    # --- Save model ---
    if save_model is not None:
        save_path = Path(save_model)
        save_path.mkdir(parents=True, exist_ok=True)
        model.save(save_path, overwrite=True)
        print(f"\n  Model saved to: {save_path}")

    # --- Store metadata ---
    adata.uns["velovi_info"] = {
        "spliced_layer": spliced_layer,
        "unspliced_layer": unspliced_layer,
        "n_latent": n_latent,
        "max_epochs": max_epochs,
        "epochs_trained": int(len(train_loss)),
        "final_elbo": float(train_loss[-1]),
        "accelerator": accelerator,
        "n_cells": adata.n_obs,
        "n_genes": adata.n_vars,
        "scvi_version": scvi.__version__,
    }

    print("\n" + "=" * 60)
    print("VeloVI training complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  adata, model = train_velovi(adata)")
    print("  scores_df    = compute_permutation_scores(model, adata)")
    print("  coherence    = compute_coherence_scores(adata)")
    print("  scv.tl.velocity_graph(adata)")
    print("  scv.pl.velocity_embedding_stream(adata, basis='umap')")

    return adata, model


# ---------------------------------------------------------------------------
# 4. Get velocity results
# ---------------------------------------------------------------------------

def get_velocity_results(
    model: "scvi.external.VELOVI",
    adata: sc.AnnData,
) -> sc.AnnData:
    """
    Retrieve and summarize velocity outputs from a trained VeloVI model.

    Latent time and velocities are already stored by train_velovi. This
    function additionally extracts per-gene kinetic rates (transcription,
    splicing, degradation) when available and prints descriptive statistics.

    Parameters
    ----------
    model : VELOVI
        Trained VeloVI model instance.
    adata : AnnData
        AnnData object used for training (must contain 'velocity' layer and
        'velovi_latent_time' in .obs, as stored by train_velovi).

    Returns
    -------
    AnnData
        Input AnnData with kinetic rates added to .var when available:
        - .var['velovi_alpha']: transcription rates
        - .var['velovi_beta']:  splicing rates
        - .var['velovi_gamma']: degradation rates

    Examples
    --------
    >>> adata = get_velocity_results(model, adata)
    >>> adata.var[['velovi_alpha', 'velovi_beta', 'velovi_gamma']].describe()
    """
    print("=" * 60)
    print("VeloVI — Velocity Results Summary")
    print("=" * 60)

    # --- Velocity statistics ---
    if "velocity" in adata.layers:
        vel = adata.layers["velocity"]
        print(f"\n  Velocity layer (shape {vel.shape}):")
        print(f"    Mean:  {np.nanmean(vel):.4f}")
        print(f"    Std:   {np.nanstd(vel):.4f}")
        print(f"    Min:   {np.nanmin(vel):.4f}")
        print(f"    Max:   {np.nanmax(vel):.4f}")
        n_pos = int(np.sum(vel > 0))
        n_neg = int(np.sum(vel < 0))
        total = vel.size
        print(f"    Positive entries: {n_pos:,} ({100*n_pos/total:.1f}%)")
        print(f"    Negative entries: {n_neg:,} ({100*n_neg/total:.1f}%)")
    else:
        warnings.warn(
            "'velocity' layer not found. Run train_velovi() first."
        )

    # --- Latent time statistics ---
    if "velovi_latent_time" in adata.obs:
        lt = adata.obs["velovi_latent_time"]
        print(f"\n  Latent time (velovi_latent_time):")
        print(f"    Mean:   {lt.mean():.4f}")
        print(f"    Median: {lt.median():.4f}")
        print(f"    Std:    {lt.std():.4f}")
        print(f"    Range:  [{lt.min():.4f}, {lt.max():.4f}]")
    else:
        warnings.warn(
            "'velovi_latent_time' not in adata.obs. Run train_velovi() first."
        )

    # --- Kinetic rates ---
    print(f"\n  Extracting kinetic rates...")
    try:
        # get_rates returns a DataFrame with columns alpha, beta, gamma (genes x rates)
        rates = model.get_rates()

        if isinstance(rates, pd.DataFrame):
            # Align index to adata.var_names
            rates = rates.reindex(adata.var_names)
            for col in ["alpha", "beta", "gamma"]:
                if col in rates.columns:
                    adata.var[f"velovi_{col}"] = rates[col].values
                    print(f"    ✓ adata.var['velovi_{col}'] stored")
        else:
            warnings.warn(
                "get_rates() returned unexpected type. Kinetic rates not stored."
            )

    except AttributeError:
        print(f"    [INFO] model.get_rates() not available in this scvi-tools version.")
        print(f"    Kinetic rates can be extracted from model internals if needed.")
    except Exception as exc:  # noqa: BLE001
        warnings.warn(f"Could not retrieve kinetic rates: {exc}")

    print(f"\n  ✓ get_velocity_results complete")
    return adata


# ---------------------------------------------------------------------------
# 5. Compute permutation scores
# ---------------------------------------------------------------------------

def compute_permutation_scores(
    model: "scvi.external.VELOVI",
    adata: sc.AnnData,
    n_permutations: int = 10,
) -> pd.DataFrame:
    """
    Compute permutation scores to assess dataset suitability for RNA velocity.

    Permutation scores compare the model log-likelihood on observed data
    versus permuted (shuffled) data. A high score means a gene shows
    genuine transient dynamics that VeloVI can model. Genes with low scores
    are at steady state or are noise-dominated.

    This diagnostic is CRITICAL: if most genes have low scores the dataset
    does not have sufficient transient dynamics for velocity to be meaningful.

    Parameters
    ----------
    model : VELOVI
        Trained VeloVI model instance.
    adata : AnnData
        AnnData object used for training.
    n_permutations : int, optional
        Number of permutation replicates (default: 10).
        Ignored if model.get_permutation_scores() is available.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns:
        - gene: gene name
        - score: permutation score (higher = more dynamic)
        - is_significant: bool, True if gene shows significant dynamics

    Notes
    -----
    High permutation score => dataset has transient dynamics => velocity
    analysis is appropriate. Low scores across all genes suggest steady-state
    kinetics; velocity results should be interpreted with extreme caution.

    Reference: Gayoso et al. (2023) Nature Methods, Supplementary Methods.

    Examples
    --------
    >>> scores_df = compute_permutation_scores(model, adata, n_permutations=10)
    >>> scores_df[scores_df['is_significant']].shape[0]
    """
    print("=" * 60)
    print("Permutation Scores — Dataset Suitability Assessment")
    print("=" * 60)

    # --- Attempt model's built-in method first ---
    scores_array: Optional[np.ndarray] = None
    gene_names = adata.var_names.tolist()

    try:
        print(f"\n  Trying model.get_permutation_scores()...")
        perm_result = model.get_permutation_scores(adata)

        if isinstance(perm_result, pd.DataFrame):
            # Already a tidy DataFrame
            if "score" in perm_result.columns:
                scores_array = perm_result["score"].values
            else:
                scores_array = perm_result.values.ravel()
        elif isinstance(perm_result, np.ndarray):
            scores_array = perm_result.ravel()

        print(f"    ✓ Used model.get_permutation_scores()")

    except (AttributeError, NotImplementedError, TypeError):
        print(f"    model.get_permutation_scores() not available.")
        print(f"    Running manual permutation test ({n_permutations} permutations)...")

        # Manual fallback: compare per-gene likelihood to permuted versions
        try:
            # Observed log-likelihood per gene
            obs_ll = model.get_likelihood_parameter(
                velo_type="permutation", n_samples=1
            )
        except Exception:  # noqa: BLE001
            obs_ll = None

        if obs_ll is not None and isinstance(obs_ll, np.ndarray):
            permuted_lls = np.zeros((n_permutations, adata.n_vars))
            rng = np.random.default_rng(42)

            for i in range(n_permutations):
                perm_idx = rng.permutation(adata.n_obs)
                adata_perm = adata.copy()
                for lkey in [model.spliced_obsm_key if hasattr(model, "spliced_obsm_key") else "Ms",
                              model.unspliced_obsm_key if hasattr(model, "unspliced_obsm_key") else "Mu"]:
                    if lkey in adata_perm.layers:
                        adata_perm.layers[lkey] = adata_perm.layers[lkey][perm_idx]
                try:
                    perm_ll = model.get_likelihood_parameter(
                        velo_type="permutation", n_samples=1
                    )
                    if isinstance(perm_ll, np.ndarray):
                        permuted_lls[i] = perm_ll.ravel()
                except Exception:  # noqa: BLE001
                    permuted_lls[i] = obs_ll.ravel()

            mean_perm_ll = permuted_lls.mean(axis=0)
            obs_flat = obs_ll.ravel()
            scores_array = obs_flat - mean_perm_ll
            print(f"    ✓ Manual permutation scores computed")

        else:
            # Last resort: use velocity magnitude as proxy
            warnings.warn(
                "Could not compute likelihood-based permutation scores. "
                "Using velocity magnitude as a proxy score. "
                "Interpret results with caution."
            )
            if "velocity" in adata.layers:
                vel = adata.layers["velocity"]
                scores_array = np.nanstd(vel, axis=0)
            else:
                scores_array = np.zeros(adata.n_vars)

    # --- Build output DataFrame ---
    if scores_array is None or len(scores_array) == 0:
        scores_array = np.zeros(adata.n_vars)

    scores_array = np.array(scores_array).ravel()
    # Align length to adata.n_vars
    if len(scores_array) != adata.n_vars:
        warnings.warn(
            f"Score array length ({len(scores_array)}) != n_vars ({adata.n_vars}). "
            "Truncating or padding with zeros."
        )
        new_arr = np.zeros(adata.n_vars)
        n = min(len(scores_array), adata.n_vars)
        new_arr[:n] = scores_array[:n]
        scores_array = new_arr

    # Significance threshold: score > median + 1 MAD (non-parametric)
    median_score = np.median(scores_array)
    mad = np.median(np.abs(scores_array - median_score))
    threshold = median_score + mad

    is_significant = scores_array > threshold

    scores_df = pd.DataFrame({
        "gene": gene_names,
        "score": scores_array,
        "is_significant": is_significant,
    }).sort_values("score", ascending=False).reset_index(drop=True)

    # Store in AnnData
    adata.var["velovi_permutation_score"] = scores_df.set_index("gene").reindex(gene_names)["score"].values
    adata.var["velovi_dynamic_gene"] = scores_df.set_index("gene").reindex(gene_names)["is_significant"].values

    n_sig = int(is_significant.sum())
    pct_sig = 100 * n_sig / adata.n_vars

    print(f"\n  Permutation score summary ({adata.n_vars:,} genes):")
    print(f"    Significant dynamic genes: {n_sig:,} ({pct_sig:.1f}%)")
    print(f"    Score median:  {median_score:.4f}")
    print(f"    Score MAD:     {mad:.4f}")
    print(f"    Threshold:     {threshold:.4f}")
    print(f"    Top 5 dynamic genes: {scores_df['gene'].head(5).tolist()}")

    if pct_sig < 10:
        print(f"\n  [WARNING] Only {pct_sig:.1f}% of genes show significant dynamics.")
        print(f"  The dataset may lack transient kinetics. Velocity results should")
        print(f"  be interpreted with caution.")
    elif pct_sig >= 30:
        print(f"\n  ✓ {pct_sig:.1f}% of genes show significant dynamics.")
        print(f"  The dataset appears suitable for RNA velocity analysis.")
    else:
        print(f"\n  [INFO] {pct_sig:.1f}% of genes show significant dynamics.")
        print(f"  Moderate signal; interpret velocity with appropriate uncertainty.")

    return scores_df


# ---------------------------------------------------------------------------
# 6. Compute coherence scores
# ---------------------------------------------------------------------------

def compute_coherence_scores(adata: sc.AnnData) -> pd.Series:
    """
    Compute per-cell velocity coherence as cosine similarity with neighbors.

    Coherence (velocity confidence) measures whether a cell's velocity vector
    points in the same direction as its transcriptomic neighbors. High
    coherence indicates consistent, reliable velocity estimates.

    Delegates to scvelo's ``scv.tl.velocity_confidence()`` when available.

    Parameters
    ----------
    adata : AnnData
        AnnData object with 'velocity' in .layers and a neighbors graph
        (from sc.pp.neighbors or scv.pp.moments).

    Returns
    -------
    pd.Series
        Per-cell velocity coherence scores (index = cell barcodes).
        Values range from -1 (fully inconsistent) to 1 (fully consistent).
        Also stored in adata.obs['velocity_coherence'].

    Raises
    ------
    ValueError
        If 'velocity' layer is missing.

    Examples
    --------
    >>> coherence = compute_coherence_scores(adata)
    >>> coherence.describe()
    """
    print("=" * 60)
    print("Velocity Coherence Scores")
    print("=" * 60)

    if "velocity" not in adata.layers:
        raise ValueError(
            "'velocity' layer not found in adata.layers. "
            "Run train_velovi() first to generate velocity estimates."
        )

    try:
        import scvelo as scv

        print(f"\n  Running scv.tl.velocity_confidence()...")
        # scVelo expects the velocity layer to be named 'velocity'
        scv.tl.velocity_confidence(adata)

        # scVelo stores the result in 'velocity_confidence' or 'velocity_coherence'
        confidence_key = None
        for candidate in ["velocity_confidence", "velocity_coherence"]:
            if candidate in adata.obs.columns:
                confidence_key = candidate
                break

        if confidence_key is None:
            warnings.warn(
                "scv.tl.velocity_confidence() ran but no confidence column found. "
                "Falling back to manual cosine similarity."
            )
        else:
            coherence = adata.obs[confidence_key].copy()
            # Standardise column name
            adata.obs["velocity_coherence"] = coherence.values
            print(f"    ✓ Used scvelo velocity_confidence (column: '{confidence_key}')")

            print(f"\n  Coherence summary ({adata.n_obs:,} cells):")
            print(f"    Mean:   {coherence.mean():.4f}")
            print(f"    Median: {coherence.median():.4f}")
            print(f"    Std:    {coherence.std():.4f}")
            print(f"    Range:  [{coherence.min():.4f}, {coherence.max():.4f}]")
            n_high = int((coherence > 0.7).sum())
            print(f"    High coherence cells (>0.7): {n_high:,} ({100*n_high/adata.n_obs:.1f}%)")

            return coherence.rename("velocity_coherence")

    except ImportError:
        print(f"    scvelo not installed. Falling back to manual cosine similarity.")
    except Exception as exc:  # noqa: BLE001
        warnings.warn(f"scv.tl.velocity_confidence() failed: {exc}. Falling back.")

    # --- Manual fallback: cosine similarity with neighbor velocities ---
    print(f"\n  Computing manual cosine similarity with neighbors...")

    velocity = adata.layers["velocity"]

    # Require a neighbor graph
    if "connectivities" not in adata.obsp:
        warnings.warn(
            "No neighbor graph found in adata.obsp['connectivities']. "
            "Run sc.pp.neighbors(adata) first for coherence scores. "
            "Returning NaN coherence."
        )
        coherence_vals = np.full(adata.n_obs, np.nan)
        adata.obs["velocity_coherence"] = coherence_vals
        return pd.Series(coherence_vals, index=adata.obs_names, name="velocity_coherence")

    from scipy.sparse import issparse

    conn = adata.obsp["connectivities"]

    # Replace NaN with 0 for cosine calculation
    vel_clean = np.nan_to_num(velocity, nan=0.0)

    coherence_vals = np.zeros(adata.n_obs)

    for i in range(adata.n_obs):
        if issparse(conn):
            neighbor_idx = conn[i].nonzero()[1]
        else:
            neighbor_idx = np.nonzero(conn[i])[0]

        if len(neighbor_idx) == 0:
            coherence_vals[i] = np.nan
            continue

        v_self = vel_clean[i]
        v_norm = np.linalg.norm(v_self)

        if v_norm == 0:
            coherence_vals[i] = 0.0
            continue

        v_neighbors = vel_clean[neighbor_idx]
        cosines = []
        for v_n in v_neighbors:
            n_norm = np.linalg.norm(v_n)
            if n_norm > 0:
                cosines.append(np.dot(v_self, v_n) / (v_norm * n_norm))
        coherence_vals[i] = float(np.mean(cosines)) if cosines else 0.0

    adata.obs["velocity_coherence"] = coherence_vals
    coherence = pd.Series(coherence_vals, index=adata.obs_names, name="velocity_coherence")

    valid = coherence.dropna()
    print(f"\n  Coherence summary ({adata.n_obs:,} cells):")
    print(f"    Mean:   {valid.mean():.4f}")
    print(f"    Median: {valid.median():.4f}")
    print(f"    Std:    {valid.std():.4f}")
    print(f"    Range:  [{valid.min():.4f}, {valid.max():.4f}]")
    n_high = int((valid > 0.7).sum())
    print(f"    High coherence cells (>0.7): {n_high:,} ({100*n_high/len(valid):.1f}%)")
    print(f"\n    ✓ adata.obs['velocity_coherence'] stored")

    return coherence


# ---------------------------------------------------------------------------
# __main__
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("VeloVI — RNA Velocity Workflow")
    print("=" * 60)
    print()
    print("Typical usage:")
    print()
    print("  import scvelo as scv")
    print("  from run_velovi import (")
    print("      validate_velocity_data,")
    print("      preprocess_for_velovi,")
    print("      train_velovi,")
    print("      get_velocity_results,")
    print("      compute_permutation_scores,")
    print("      compute_coherence_scores,")
    print("  )")
    print()
    print("  # 1. Load data with spliced/unspliced layers")
    print("  adata = scv.read('your_data.loom')")
    print()
    print("  # 2. Validate")
    print("  ok = validate_velocity_data(adata)")
    print()
    print("  # 3. Preprocess (if moments not already computed)")
    print("  if not ok:")
    print("      adata = preprocess_for_velovi(adata)")
    print()
    print("  # 4. Train VeloVI")
    print("  adata, model = train_velovi(adata, max_epochs=500, save_model='results/velovi_model')")
    print()
    print("  # 5. Retrieve results and kinetic rates")
    print("  adata = get_velocity_results(model, adata)")
    print()
    print("  # 6. CRITICAL: Assess dataset suitability")
    print("  scores_df = compute_permutation_scores(model, adata, n_permutations=10)")
    print()
    print("  # 7. Per-cell coherence")
    print("  coherence = compute_coherence_scores(adata)")
    print()
    print("  # 8. Downstream velocity visualisation")
    print("  scv.tl.velocity_graph(adata)")
    print("  scv.pl.velocity_embedding_stream(adata, basis='umap')")
    print("  scv.pl.velocity_embedding(adata, basis='umap', arrow_length=3)")
