"""
Cell Type Deconvolution of Spatial Transcriptomics with DestVI

This module implements DestVI (Deconvolution of Spatial Transcriptomics using
Variational Inference) for reference-based deconvolution of spot-based spatial
transcriptomics data (e.g., Visium). DestVI requires a pretrained scVI model
trained on a matched single-cell RNA-seq reference; the scVI encoder weights
are transferred to the spatial context via from_rna_model().

DestVI's defining feature over other deconvolution tools is the continuous
variation variable (gamma), which captures within-cell-type functional
heterogeneity across spots — not just how much of a cell type is present,
but in what transcriptional state.

For methodology and best practices, see references/models-spatial.md

Prerequisites:
  Run the scvi-tools-scrna skill to train an scVI model on the reference
  single-cell dataset before calling any function in this module.

Functions:
  - train_destvi(): Transfer scVI reference model to spatial and estimate
    cell type proportions at each spot
  - get_cell_type_expression(): Retrieve cell-type-specific gene expression
    profiles at each spatial spot
  - get_continuous_variation(): Extract per-cell-type continuous state
    variables (gamma) capturing within-type functional heterogeneity

Requirements:
  - scvi-tools >= 1.1: pip install scvi-tools
  - torch: pip install torch
  - GPU recommended for training (10-20x faster)
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

try:
    import scvi
except ImportError:
    raise ImportError(
        "scvi-tools >= 1.1 is required for this module.\n"
        "Install with: pip install scvi-tools"
    )

import scanpy as sc

from setup_spatial import detect_accelerator


def train_destvi(
    adata_sp: sc.AnnData,
    scvi_model: Any,
    cell_type_key: str = "cell_type",
    max_epochs: int = 2500,
    save_model: Optional[Union[str, Path]] = None,
) -> Tuple[sc.AnnData, Any]:
    """
    Transfer a pretrained scVI reference model to spatial data and train DestVI.

    DestVI deconvolves each spatial spot into cell type proportions by learning
    from a pretrained scVI model on the matched single-cell reference. The scVI
    encoder encodes reference cell states; DestVI then learns to explain spatial
    spot expression as mixtures of those states.

    This function:
    - Registers the spatial AnnData with DestVI
    - Constructs the DestVI model from the scVI reference via from_rna_model()
    - Trains with the best available hardware accelerator
    - Stores proportions in obsm['destvi_proportions'] (DataFrame)
    - Adds per-cell-type proportion columns to obs (e.g., 'destvi_prop_T_cells')
    - Adds a dominant cell type column to obs ('destvi_dominant_type')
    - Records metadata in uns['destvi_info']

    Parameters
    ----------
    adata_sp : sc.AnnData
        Spatial AnnData object. Must contain raw counts in
        adata_sp.layers['counts'] (preferred) or adata_sp.X.
        Genes must overlap with the genes used to train scvi_model.
    scvi_model : scvi.model.SCVI
        A trained scVI model instance from the scvi-tools-scrna skill.
        Must have been trained on a reference dataset that shares genes with
        adata_sp and contains the column cell_type_key in its .adata.obs.
    cell_type_key : str, optional
        Column in scvi_model.adata.obs containing cell type labels
        (default: "cell_type"). These labels define the deconvolution targets.
    max_epochs : int, optional
        Maximum training epochs (default: 2500). DestVI typically converges
        well within 2500 epochs, which is the standard recommendation.
    save_model : str or Path, optional
        Directory to save the trained DestVI model (default: None).

    Returns
    -------
    tuple of (sc.AnnData, scvi.model.DestVI)
        adata_sp : AnnData with the following additions:
            - .obsm['destvi_proportions']: DataFrame (spots x cell types)
            - .obs['destvi_prop_{cell_type}']: Proportion column per cell type
              (spaces replaced with underscores)
            - .obs['destvi_dominant_type']: Cell type with highest proportion
              at each spot
            - .uns['destvi_info']: Training metadata dict
        model : Trained DestVI model instance

    Raises
    ------
    ValueError
        If cell_type_key is not found in scvi_model.adata.obs.

    Notes
    -----
    Requires scvi-tools >= 1.1.
    The standard DestVI workflow trains scVI first on the scRNA-seq reference
    (scvi-tools-scrna skill), then calls this function. Do not skip the scVI
    step — DestVI's from_rna_model() depends on the pretrained reference encoder.

    Examples
    --------
    >>> # Train scVI on reference first (scvi-tools-scrna skill)
    >>> scvi.model.SCVI.setup_anndata(adata_ref, layer='counts')
    >>> sc_model = scvi.model.SCVI(adata_ref)
    >>> sc_model.train(max_epochs=400)
    >>>
    >>> # Deconvolve spatial data with DestVI
    >>> adata_sp, destvi_model = train_destvi(
    ...     adata_sp, sc_model, cell_type_key='cell_type', max_epochs=2500
    ... )
    >>> # Visualize T cell proportions
    >>> sc.pl.spatial(adata_sp, color='destvi_prop_T_cells', spot_size=150)
    """
    print("=" * 60)
    print("DestVI Spatial Deconvolution")
    print("=" * 60)

    # --- Validate cell_type_key in reference ---
    ref_obs = scvi_model.adata.obs
    if cell_type_key not in ref_obs.columns:
        raise ValueError(
            f"Cell type key '{cell_type_key}' not found in scvi_model.adata.obs. "
            f"Available columns: {list(ref_obs.columns[:10])}"
        )

    cell_types = ref_obs[cell_type_key].unique().tolist()
    n_cell_types = len(cell_types)

    print(f"\nReference summary:")
    print(f"  Reference cells: {scvi_model.adata.n_obs:,}")
    print(f"  Reference genes: {scvi_model.adata.n_vars:,}")
    print(f"  Cell type key: '{cell_type_key}'")
    print(f"  Cell types ({n_cell_types}): {sorted(cell_types)}")

    print(f"\nSpatial data summary:")
    print(f"  Spots: {adata_sp.n_obs:,}")
    print(f"  Genes: {adata_sp.n_vars:,}")

    # --- Determine count layer ---
    layer: Optional[str] = "counts" if "counts" in adata_sp.layers else None
    print(
        f"\n  Count layer: "
        + ("adata.layers['counts']" if layer else "adata.X (no 'counts' layer found)")
    )

    # --- Setup AnnData for DestVI ---
    print("\nRegistering spatial AnnData with DestVI...")
    scvi.model.DestVI.setup_anndata(adata_sp, layer=layer)
    print("  Spatial AnnData registered with DestVI")

    # --- Build DestVI from reference scVI model ---
    print("\nConstructing DestVI model from scVI reference...")
    model = scvi.model.DestVI.from_rna_model(
        adata_sp,
        scvi_model,
        cell_type_key=cell_type_key,
    )
    print("  DestVI model constructed (scVI reference encoder transferred)")

    # --- Detect accelerator and train ---
    accelerator = detect_accelerator()

    print(f"\nTraining DestVI model...")
    print(f"  Max epochs: {max_epochs}")
    print(f"  Accelerator: {accelerator}")
    print(f"  Note: DestVI typically requires ~2500 epochs to converge")

    model.train(max_epochs=max_epochs, accelerator=accelerator)
    print("  Training complete")

    # --- Get proportions ---
    print("\nExtracting cell type proportions...")
    proportions: pd.DataFrame = model.get_proportions()

    # Ensure index aligns with spots
    proportions.index = adata_sp.obs_names

    # Store full proportions DataFrame in obsm
    adata_sp.obsm["destvi_proportions"] = proportions
    print(f"  ✓ Added 'destvi_proportions' to adata_sp.obsm (shape: {proportions.shape})")

    # --- Add per-type columns to obs ---
    print("\nAdding per-cell-type proportion columns to adata_sp.obs...")
    obs_col_map: Dict[str, str] = {}
    for ct in proportions.columns:
        safe_name = ct.replace(" ", "_").replace("/", "_").replace("-", "_")
        col_name = f"destvi_prop_{safe_name}"
        adata_sp.obs[col_name] = proportions[ct].values
        obs_col_map[ct] = col_name

    print(f"  ✓ Added {len(obs_col_map)} proportion columns to adata_sp.obs")

    # --- Add dominant cell type per spot ---
    dominant_type = proportions.idxmax(axis=1)
    adata_sp.obs["destvi_dominant_type"] = dominant_type.values
    print(f"  ✓ Added 'destvi_dominant_type' to adata_sp.obs")

    # --- Proportion statistics ---
    print(f"\nProportion summary (mean across spots):")
    for ct in proportions.columns:
        mean_prop = float(proportions[ct].mean())
        max_prop = float(proportions[ct].max())
        print(f"  {ct}: mean={mean_prop:.3f}, max={max_prop:.3f}")

    dominant_counts = adata_sp.obs["destvi_dominant_type"].value_counts()
    print(f"\nDominant cell type distribution (n spots):")
    for ct, count in dominant_counts.items():
        pct = 100 * count / adata_sp.n_obs
        print(f"  {ct}: {count:,} spots ({pct:.1f}%)")

    # --- Save model if requested ---
    if save_model is not None:
        save_path = Path(save_model)
        save_path.mkdir(parents=True, exist_ok=True)
        model.save(save_path, overwrite=True)
        print(f"\n  Model saved to: {save_path}")

    # --- Store metadata ---
    adata_sp.uns["destvi_info"] = {
        "cell_type_key": cell_type_key,
        "n_cell_types": n_cell_types,
        "cell_types": sorted(cell_types),
        "n_spots": adata_sp.n_obs,
        "n_genes": adata_sp.n_vars,
        "max_epochs": max_epochs,
        "accelerator": accelerator,
        "layer": layer,
        "obs_proportion_columns": obs_col_map,
    }

    print("\n" + "=" * 60)
    print("DestVI training complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  sc.pl.spatial(adata_sp, color='destvi_dominant_type', spot_size=150)")
    print("  sc.pl.spatial(adata_sp, color='destvi_prop_T_cells', spot_size=150)")
    print("  ct_expr = get_cell_type_expression(model, 'T cells', adata_sp)")
    print("  gamma = get_continuous_variation(model, adata_sp)")

    return adata_sp, model


def get_cell_type_expression(
    destvi_model: Any,
    cell_type: str,
    adata_sp: sc.AnnData,
) -> pd.DataFrame:
    """
    Retrieve cell-type-specific gene expression at each spatial spot.

    Calls get_scale_for_ct() to obtain the expression profile of a given cell
    type as decoded by DestVI at each spatial location. The result reflects the
    expected gene expression of that cell type conditional on the spatial context
    of each spot — not a global average from the reference.

    Parameters
    ----------
    destvi_model : scvi.model.DestVI
        A trained DestVI model instance returned by train_destvi().
    cell_type : str
        Name of the cell type to query. Must exactly match a category in the
        cell_type_key column used during training.
    adata_sp : sc.AnnData
        Spatial AnnData object used to train destvi_model. Used to align
        the output index (obs_names) and var_names.

    Returns
    -------
    pd.DataFrame
        DataFrame of shape (n_spots, n_genes) containing the decoded expression
        scale for cell_type at each spot. Index is spot barcodes; columns are
        gene names.

    Notes
    -----
    Spots with near-zero proportion of cell_type may have uninformative
    expression estimates. Consider masking by proportion threshold before
    interpreting results.

    Examples
    --------
    >>> t_cell_expr = get_cell_type_expression(model, 'T cells', adata_sp)
    >>> # Top expressed T cell genes
    >>> top_genes = t_cell_expr.mean(axis=0).nlargest(10)
    >>> print(top_genes)
    """
    print("=" * 60)
    print(f"Cell-Type-Specific Expression: '{cell_type}'")
    print("=" * 60)

    print(f"\nQuerying DestVI for cell type: '{cell_type}'...")
    expr_array = destvi_model.get_scale_for_ct(cell_type)

    # Wrap in DataFrame with spot and gene labels
    ct_expr = pd.DataFrame(
        expr_array,
        index=adata_sp.obs_names,
        columns=adata_sp.var_names,
    )

    print(f"  ✓ Expression matrix shape: {ct_expr.shape} (spots x genes)")

    # --- Top expressed genes (mean across spots) ---
    mean_expr = ct_expr.mean(axis=0)
    top_genes = mean_expr.nlargest(10)

    print(f"\nTop 10 expressed genes for '{cell_type}' (mean across spots):")
    for gene, val in top_genes.items():
        print(f"  {gene}: {val:.4f}")

    # --- Expression range summary ---
    global_min = float(ct_expr.values.min())
    global_max = float(ct_expr.values.max())
    global_mean = float(ct_expr.values.mean())
    print(f"\nExpression scale range: [{global_min:.4f}, {global_max:.4f}]  "
          f"mean={global_mean:.4f}")

    return ct_expr


def get_continuous_variation(
    destvi_model: Any,
    adata_sp: sc.AnnData,
) -> Dict[str, np.ndarray]:
    """
    Extract DestVI's continuous cell-type-specific state variables (gamma).

    Gamma is DestVI's unique feature: a continuous latent variable that captures
    within-cell-type functional heterogeneity across spatial spots. While cell
    type proportions answer "how much of each type is here?", gamma answers
    "in what transcriptional state is that cell type here?".

    Calls get_gamma() on the trained DestVI model, which returns per-spot,
    per-cell-type continuous state vectors. These can be used to identify
    spatially-variable functional states within a cell type.

    Parameters
    ----------
    destvi_model : scvi.model.DestVI
        A trained DestVI model instance returned by train_destvi().
    adata_sp : sc.AnnData
        Spatial AnnData object used to train destvi_model. Used to retrieve
        cell type names from uns['destvi_info'] if available.

    Returns
    -------
    dict of {str: np.ndarray}
        Dictionary mapping each cell type name to a NumPy array of shape
        (n_spots, n_latent_continuous) containing the gamma values at each
        spot for that cell type. n_latent_continuous is determined by the
        DestVI model configuration (typically equal to the scVI n_latent).

    Notes
    -----
    Gamma values are only meaningful at spots where that cell type has a
    non-negligible proportion. Spots with near-zero proportion for a given
    type produce gamma values that are not biologically interpretable.
    Always cross-reference with destvi_proportions before interpreting gamma.

    This is what distinguishes DestVI from Cell2location: DestVI models
    continuous within-type variation, not just discrete proportions.

    Examples
    --------
    >>> gamma = get_continuous_variation(model, adata_sp)
    >>> # Gamma values for T cells across all spots
    >>> t_cell_gamma = gamma['T cells']  # shape: (n_spots, n_latent)
    >>> # Store for downstream spatial analysis
    >>> adata_sp.obsm['destvi_gamma_T_cells'] = t_cell_gamma
    """
    print("=" * 60)
    print("DestVI Continuous Variation (Gamma)")
    print("=" * 60)

    print("\nExtracting gamma (continuous cell-type state variables)...")

    # get_gamma() returns a dict: {cell_type_name: array (n_spots, n_latent)}
    gamma_raw = destvi_model.get_gamma()

    # Resolve cell type names
    # get_gamma() may return integer-keyed or string-keyed dict depending on version
    if "destvi_info" in adata_sp.uns:
        cell_types: list = adata_sp.uns["destvi_info"].get("cell_types", [])
    else:
        cell_types = []

    # Build output dict, aligning keys to cell type names when possible
    gamma_dict: Dict[str, np.ndarray] = {}

    if isinstance(gamma_raw, dict):
        # If keys are already strings, use them directly
        first_key = next(iter(gamma_raw))
        if isinstance(first_key, str):
            gamma_dict = {k: np.asarray(v) for k, v in gamma_raw.items()}
        else:
            # Integer-indexed: map to cell type names if available
            if cell_types and len(cell_types) == len(gamma_raw):
                for idx, ct in enumerate(cell_types):
                    gamma_dict[ct] = np.asarray(gamma_raw[idx])
            else:
                # Fall back to string-ified integer keys
                gamma_dict = {str(k): np.asarray(v) for k, v in gamma_raw.items()}
    elif isinstance(gamma_raw, np.ndarray):
        # Some versions return a 3D array: (n_cell_types, n_spots, n_latent)
        if gamma_raw.ndim == 3 and cell_types and gamma_raw.shape[0] == len(cell_types):
            for i, ct in enumerate(cell_types):
                gamma_dict[ct] = gamma_raw[i]
        else:
            # Cannot map to named cell types; return as single entry
            gamma_dict = {"all_types": gamma_raw}
    else:
        # Unexpected format: wrap as-is
        gamma_dict = {"raw": np.asarray(gamma_raw)}

    print(f"  ✓ Gamma extracted for {len(gamma_dict)} cell type(s)")

    # --- Per-type summary ---
    print(f"\nGamma summary per cell type:")
    for ct, gamma_arr in gamma_dict.items():
        arr = np.asarray(gamma_arr)
        shape_str = str(arr.shape)
        g_min = float(arr.min())
        g_max = float(arr.max())
        g_mean = float(arr.mean())
        print(f"  {ct}:")
        print(f"    Shape: {shape_str}  (spots x latent dims)")
        print(f"    Range: [{g_min:.4f}, {g_max:.4f}]  mean={g_mean:.4f}")

    print(
        "\n  [NOTE] Gamma captures within-type functional heterogeneity across spots."
    )
    print(
        "  Meaningful only where cell type proportion > 0. "
        "Cross-reference with destvi_proportions."
    )
    print(
        "\n  Suggested usage:"
    )
    print(
        "    for ct, gamma_arr in gamma.items():"
    )
    print(
        "        adata_sp.obsm[f'destvi_gamma_{ct}'] = gamma_arr"
    )

    return gamma_dict


# Example usage
if __name__ == "__main__":
    print("DestVI Spatial Deconvolution Workflow")
    print("=" * 60)
    print()
    print("Prerequisites:")
    print("  1. Train scVI on the scRNA-seq reference (scvi-tools-scrna skill)")
    print("  2. Subset both datasets to shared genes (setup_spatial.py)")
    print()
    print("Imports:")
    print()
    print("  import scvi")
    print("  from run_destvi import (")
    print("      train_destvi,")
    print("      get_cell_type_expression,")
    print("      get_continuous_variation,")
    print("  )")
    print()
    print("Step 1 — Train scVI on reference (scvi-tools-scrna skill):")
    print()
    print("  scvi.model.SCVI.setup_anndata(adata_ref, layer='counts')")
    print("  sc_model = scvi.model.SCVI(adata_ref, n_latent=30, n_layers=2)")
    print("  sc_model.train(max_epochs=400)")
    print()
    print("Step 2 — Deconvolve spatial data with DestVI:")
    print()
    print("  adata_sp, destvi_model = train_destvi(")
    print("      adata_sp,")
    print("      sc_model,")
    print("      cell_type_key='cell_type',")
    print("      max_epochs=2500,")
    print("  )")
    print()
    print("Step 3 — Visualize proportions:")
    print()
    print("  import scanpy as sc")
    print("  sc.pl.spatial(adata_sp, color='destvi_dominant_type', spot_size=150)")
    print("  sc.pl.spatial(adata_sp, color='destvi_prop_T_cells', spot_size=150,")
    print("                cmap='viridis')")
    print()
    print("Step 4 — Cell-type-specific expression at each spot:")
    print()
    print("  t_cell_expr = get_cell_type_expression(destvi_model, 'T cells', adata_sp)")
    print("  # t_cell_expr: DataFrame (spots x genes)")
    print()
    print("Step 5 — Continuous variation (gamma), DestVI's unique output:")
    print()
    print("  gamma = get_continuous_variation(destvi_model, adata_sp)")
    print("  # gamma: dict {cell_type -> array (n_spots, n_latent)}")
    print("  for ct, g in gamma.items():")
    print("      adata_sp.obsm[f'destvi_gamma_{ct}'] = g")
    print()
    print("DestVI vs Cell2location:")
    print("  - Both estimate cell type proportions at each spot")
    print("  - DestVI adds gamma: continuous within-type functional variation")
    print("  - DestVI: 2500 epochs  vs  Cell2location: ~30000 epochs")
    print("  - DestVI requires a pretrained scVI reference model")
