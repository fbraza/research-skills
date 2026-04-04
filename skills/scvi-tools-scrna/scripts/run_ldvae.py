"""
Linearly Decoded Variational Autoencoder (LDVAE) for Gene Program Discovery

This module trains LDVAE (Svensson et al. 2020) on single-cell RNA-seq data and
extracts interpretable gene programs. Unlike scVI's non-linear decoder, LDVAE
uses a linear decoder: each latent dimension maps directly and additively to gene
expression. This preserves biological interpretability — factor loadings are gene
weights, analogous to PCA or NMF components but with a probabilistic generative
model.

Key distinction from scVI:
  - scVI: deep non-linear decoder → rich representation, no direct interpretability
  - LDVAE: linear decoder → loadings are directly readable gene programs

Recommended use cases:
  - Discovering co-expression gene programs
  - Identifying driver genes per latent factor
  - Exploratory factor analysis of scRNA-seq

Reference:
  Svensson V, Gayoso A, Yosef N, Pachter L (2020). Interpretable factor models
  of single-cell RNA-seq via variational autoencoders. Bioinformatics 36(11):
  3418-3421. https://doi.org/10.1093/bioinformatics/btaa169

Functions:
  - train_ldvae(): Train LinearSCVI model and extract latent representation
  - get_gene_loadings(): Extract linear decoder factor loadings as a DataFrame
  - identify_gene_programs(): Map each factor to its top positive/negative genes
  - plot_loadings_heatmap(): Visualise top-gene loadings per factor as a heatmap

Requirements:
  - scvi-tools >= 1.1: pip install scvi-tools
  - seaborn: pip install seaborn
  - GPU recommended for training (10-20x faster)
"""

import warnings
from pathlib import Path
from typing import Optional, Union, Dict, List, Tuple, Any

import numpy as np
import pandas as pd
import scanpy as sc

try:
    import scvi
except ImportError:
    raise ImportError(
        "scvi-tools is required for LDVAE.\n"
        "Install with: pip install scvi-tools"
    )


# ---------------------------------------------------------------------------
# Core training function
# ---------------------------------------------------------------------------

def train_ldvae(
    adata: sc.AnnData,
    batch_key: Optional[str] = None,
    n_latent: int = 10,
    n_hidden: int = 128,
    max_epochs: int = 400,
    save_model: Optional[Union[str, Path]] = None,
    random_state: int = 0,
) -> Tuple[sc.AnnData, Any]:
    """
    Train a LinearSCVI (LDVAE) model and embed cells in the latent space.

    LinearSCVI uses a variational autoencoder with a *linear* decoder, so each
    latent dimension directly corresponds to an additive gene expression program.
    Recommend n_latent 10-20; fewer factors than scVI because every factor must
    remain interpretable.

    Parameters
    ----------
    adata : AnnData
        AnnData object with raw integer counts. Counts must be stored in
        ``adata.layers['counts']`` (recommended) or ``adata.X``.
        Subset to highly variable genes before calling this function.
    batch_key : str, optional
        Column in ``adata.obs`` containing batch labels. If ``None``, no batch
        correction is performed (default: None).
    n_latent : int, optional
        Number of latent dimensions / gene programs (default: 10).
        Recommendation: 10-20. More factors reduce per-factor interpretability.
    n_hidden : int, optional
        Number of nodes in the encoder hidden layer (default: 128).
        The decoder is always linear regardless of this setting.
    max_epochs : int, optional
        Maximum number of training epochs (default: 400).
    save_model : str or Path, optional
        Directory to save the trained model. If None, model is not saved
        (default: None).
    random_state : int, optional
        Random seed for reproducibility (default: 0).

    Returns
    -------
    tuple
        - adata : AnnData with ``adata.obsm['X_LDVAE']`` (n_cells x n_latent)
          and ``adata.uns['ldvae_info']`` metadata dict.
        - model : Trained ``scvi.model.LinearSCVI`` instance.

    Notes
    -----
    - LinearSCVI was introduced by Svensson et al. (2020).
    - The linear decoder means ``model.get_loadings()`` returns biologically
      interpretable gene weights, one row per gene, one column per factor.
    - Always run ``sc.pp.highly_variable_genes()`` before training; using all
      genes inflates training time without improving factor quality.

    Examples
    --------
    >>> adata, model = train_ldvae(adata, batch_key='sample', n_latent=15)
    >>> sc.pp.neighbors(adata, use_rep='X_LDVAE')
    >>> sc.tl.umap(adata)
    """
    from setup_scvi import detect_accelerator, check_convergence

    print("=" * 60)
    print("LDVAE Training (LinearSCVI)")
    print("=" * 60)

    # --- Input summary ---
    print(f"\nInput data:")
    print(f"  Cells  : {adata.n_obs:,}")
    print(f"  Genes  : {adata.n_vars:,}")
    if batch_key is not None:
        if batch_key not in adata.obs.columns:
            raise ValueError(
                f"batch_key '{batch_key}' not found in adata.obs. "
                f"Available columns: {list(adata.obs.columns[:10])}"
            )
        n_batches = adata.obs[batch_key].nunique()
        print(f"  Batches: {n_batches} ('{batch_key}')")
    else:
        print(f"  Batches: none (no batch correction)")

    if 'highly_variable' in adata.var.columns:
        n_hvg = adata.var['highly_variable'].sum()
        print(f"  HVGs   : {n_hvg:,} annotated (using all {adata.n_vars:,} genes in adata)")
    else:
        warnings.warn(
            "No 'highly_variable' column found in adata.var. "
            "Consider subsetting to HVGs before training LDVAE for faster "
            "training and cleaner factors."
        )

    print(f"\nModel architecture:")
    print(f"  Latent dimensions : {n_latent}")
    print(f"  Encoder hidden    : {n_hidden}")
    print(f"  Decoder           : linear (LDVAE)")
    print(f"  Gene likelihood   : negative binomial")
    print(f"  Random seed       : {random_state}")

    # --- Setup AnnData ---
    print("\nRegistering AnnData with LinearSCVI...")
    layer = "counts" if "counts" in adata.layers else None
    if layer is None:
        warnings.warn(
            "No 'counts' layer found. Using adata.X as raw counts. "
            "Ensure adata.X contains raw integer counts (not normalised values)."
        )
    else:
        print(f"  Count layer: adata.layers['counts']")

    scvi.model.LinearSCVI.setup_anndata(
        adata,
        layer=layer,
        batch_key=batch_key,
    )
    print("  Registration complete")

    # --- Build model ---
    model = scvi.model.LinearSCVI(
        adata,
        n_latent=n_latent,
        n_hidden=n_hidden,
    )

    # --- Detect accelerator ---
    accelerator = detect_accelerator()

    # --- Train ---
    print(f"\nTraining LDVAE model...")
    print(f"  Max epochs  : {max_epochs}")
    print(f"  Accelerator : {accelerator}")

    model.train(
        max_epochs=max_epochs,
        accelerator=accelerator,
        check_val_every_n_epoch=10,
        train_size=0.9,
    )

    # --- Convergence check ---
    convergence_metrics = check_convergence(model, min_epochs=50)

    # --- Extract latent representation ---
    print("\nExtracting latent representation...")
    latent = model.get_latent_representation()
    adata.obsm['X_LDVAE'] = latent
    print(f"  Added 'X_LDVAE' to adata.obsm  (shape: {latent.shape})")

    # --- Save model ---
    if save_model is not None:
        save_path = Path(save_model)
        save_path.mkdir(parents=True, exist_ok=True)
        model.save(save_path, overwrite=True)
        print(f"\n  Model saved to: {save_path}")

    # --- Store metadata ---
    train_loss = model.history['elbo_train']
    val_loss = model.history.get('elbo_validation', None)

    adata.uns['ldvae_info'] = {
        'model_class': 'LinearSCVI',
        'n_latent': n_latent,
        'n_hidden': n_hidden,
        'batch_key': batch_key,
        'layer': layer,
        'max_epochs': max_epochs,
        'epochs_trained': convergence_metrics['epochs_trained'],
        'final_train_loss': convergence_metrics['final_loss'],
        'final_val_loss': float(val_loss.values.ravel()[-1]) if val_loss is not None and len(val_loss) > 0 else None,
        'converged': convergence_metrics['converged'],
        'random_state': random_state,
        'n_cells': adata.n_obs,
        'n_genes': adata.n_vars,
        'reference': 'Svensson et al. 2020, Bioinformatics 36(11):3418-3421',
    }

    print("\n" + "=" * 60)
    print("LDVAE training complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  loadings_df = get_gene_loadings(model)")
    print("  programs    = identify_gene_programs(loadings_df, n_top_genes=50)")
    print("  plot_loadings_heatmap(loadings_df, n_top=20, output_dir='results')")
    print("  sc.pp.neighbors(adata, use_rep='X_LDVAE')")
    print("  sc.tl.umap(adata)")

    return adata, model


# ---------------------------------------------------------------------------
# Loadings extraction
# ---------------------------------------------------------------------------

def get_gene_loadings(model: Any) -> pd.DataFrame:
    """
    Extract linear decoder factor loadings from a trained LinearSCVI model.

    Because LDVAE uses a linear decoder, each entry in the loadings matrix is
    the direct additive contribution of one latent factor to one gene. Positive
    loading: factor activates the gene. Negative loading: factor suppresses it.

    Parameters
    ----------
    model : scvi.model.LinearSCVI
        A trained LinearSCVI model.

    Returns
    -------
    DataFrame
        Shape (n_genes, n_latent). Index is gene names. Columns are renamed
        to ``Factor_0``, ``Factor_1``, ..., ``Factor_N``.

    Notes
    -----
    - ``model.get_loadings()`` returns a DataFrame with default column names;
      this function standardises them to ``Factor_<i>`` for downstream use.
    - The sign of factors is arbitrary (as in PCA). Interpret positive and
      negative gene sets together as one co-expression program.

    Examples
    --------
    >>> loadings_df = get_gene_loadings(model)
    >>> loadings_df.head()
    """
    print("=" * 60)
    print("Extracting Gene Loadings")
    print("=" * 60)

    raw_loadings = model.get_loadings()

    # Rename columns to Factor_0, Factor_1, ...
    n_factors = raw_loadings.shape[1]
    raw_loadings.columns = [f"Factor_{i}" for i in range(n_factors)]

    print(f"\n  Loadings matrix shape : {raw_loadings.shape[0]:,} genes x {n_factors} factors")
    print(f"  Columns               : {list(raw_loadings.columns)}")
    print(f"  Index (gene names)    : {list(raw_loadings.index[:5])} ...")

    # Summary statistics
    abs_max = raw_loadings.abs().max().round(4)
    print(f"\n  Max |loading| per factor:")
    for col, val in abs_max.items():
        print(f"    {col}: {val:.4f}")

    print(f"\n  ✓ Gene loadings extracted")
    return raw_loadings


# ---------------------------------------------------------------------------
# Gene program identification
# ---------------------------------------------------------------------------

def identify_gene_programs(
    loadings_df: pd.DataFrame,
    n_top_genes: int = 50,
) -> Dict[str, Dict[str, List[str]]]:
    """
    Map each latent factor to its top positive and negative driver genes.

    For each factor column in ``loadings_df``, genes are ranked by their
    loading value. The top ``n_top_genes`` by highest (positive) loading and
    lowest (negative) loading are returned as gene programs.

    Biological interpretation:
      - Positive genes: co-activated when the factor is high
      - Negative genes: co-suppressed when the factor is high
      Together they define one co-expression module.

    Parameters
    ----------
    loadings_df : DataFrame
        Gene loadings DataFrame as returned by ``get_gene_loadings()``.
        Shape (n_genes, n_factors). Index must be gene names.
    n_top_genes : int, optional
        Number of top genes to retrieve per pole (positive / negative) per
        factor (default: 50).

    Returns
    -------
    dict
        Nested dict keyed by factor name::

            {
                'Factor_0': {
                    'positive': ['GeneA', 'GeneB', ...],  # n_top_genes entries
                    'negative': ['GeneC', 'GeneD', ...],  # n_top_genes entries
                },
                ...
            }

    Examples
    --------
    >>> programs = identify_gene_programs(loadings_df, n_top_genes=50)
    >>> programs['Factor_0']['positive'][:10]
    """
    print("=" * 60)
    print("Identifying Gene Programs per Factor")
    print("=" * 60)

    programs: Dict[str, Dict[str, List[str]]] = {}

    for factor in loadings_df.columns:
        col = loadings_df[factor]

        positive_genes: List[str] = (
            col.sort_values(ascending=False)
            .head(n_top_genes)
            .index.tolist()
        )
        negative_genes: List[str] = (
            col.sort_values(ascending=True)
            .head(n_top_genes)
            .index.tolist()
        )

        programs[factor] = {
            'positive': positive_genes,
            'negative': negative_genes,
        }

        # Print summary (top 5 each pole)
        top5_pos = ', '.join(positive_genes[:5])
        top5_neg = ', '.join(negative_genes[:5])
        loading_range = f"[{col.min():.3f}, {col.max():.3f}]"
        print(f"\n  {factor}  loading range {loading_range}")
        print(f"    + top 5: {top5_pos}")
        print(f"    - top 5: {top5_neg}")

    print(f"\n  ✓ Gene programs identified  "
          f"({len(programs)} factors x {n_top_genes} genes/pole)")
    return programs


# ---------------------------------------------------------------------------
# Heatmap visualisation
# ---------------------------------------------------------------------------

def plot_loadings_heatmap(
    loadings_df: pd.DataFrame,
    n_top: int = 20,
    output_dir: str = "results",
) -> None:
    """
    Plot a heatmap of the top genes per factor by absolute loading value.

    For each factor, the top ``n_top`` genes by absolute loading are selected.
    The union of these gene sets across all factors is used as rows, giving a
    compact view of the most informative genes in the loading matrix.

    Parameters
    ----------
    loadings_df : DataFrame
        Gene loadings DataFrame as returned by ``get_gene_loadings()``.
        Shape (n_genes, n_factors). Index must be gene names.
    n_top : int, optional
        Number of top genes per factor (by absolute loading) to include in
        the heatmap (default: 20).
    output_dir : str, optional
        Directory to save figures (default: "results").
        PNG (300 DPI) and SVG are both saved.

    Returns
    -------
    None

    Notes
    -----
    - Uses a diverging colormap (RdBu_r) centred at zero: red = positive
      loading, blue = negative loading.
    - Genes are ordered by hierarchical clustering (seaborn clustermap default).
    - Large n_top values (>50) may produce a figure that is difficult to read.

    Examples
    --------
    >>> plot_loadings_heatmap(loadings_df, n_top=20, output_dir='results/ldvae')
    """
    try:
        import seaborn as sns
    except ImportError:
        raise ImportError(
            "seaborn is required for plotting.\n"
            "Install with: pip install seaborn"
        )
    import matplotlib.pyplot as plt

    print("=" * 60)
    print("Plotting Loadings Heatmap")
    print("=" * 60)

    # Select union of top-n genes by absolute loading across all factors
    top_genes_set: set = set()
    for factor in loadings_df.columns:
        top_genes = (
            loadings_df[factor]
            .abs()
            .sort_values(ascending=False)
            .head(n_top)
            .index.tolist()
        )
        top_genes_set.update(top_genes)

    top_genes_list = sorted(top_genes_set)
    plot_df = loadings_df.loc[top_genes_list]

    n_genes_shown = len(top_genes_list)
    n_factors = loadings_df.shape[1]
    print(f"\n  Factors          : {n_factors}")
    print(f"  Top genes/factor : {n_top}")
    print(f"  Unique genes shown: {n_genes_shown} (union across factors)")

    # Determine figure height based on gene count
    fig_height = max(8, n_genes_shown * 0.25)
    fig_width = max(6, n_factors * 1.2)

    # Symmetric colormap range
    vmax = float(np.abs(plot_df.values).max())
    vmin = -vmax

    g = sns.clustermap(
        plot_df,
        cmap="RdBu_r",
        vmin=vmin,
        vmax=vmax,
        figsize=(fig_width, fig_height),
        col_cluster=False,   # keep factor order
        row_cluster=True,    # cluster genes
        linewidths=0,
        xticklabels=True,
        yticklabels=True,
        cbar_kws={"label": "Loading", "shrink": 0.5},
    )
    g.fig.suptitle(
        f"LDVAE Gene Loadings — top {n_top} genes per factor",
        y=1.01,
        fontsize=13,
    )
    g.ax_heatmap.set_xlabel("Factor", fontsize=11)
    g.ax_heatmap.set_ylabel("Gene", fontsize=11)
    g.ax_heatmap.tick_params(axis='y', labelsize=7)
    g.ax_heatmap.tick_params(axis='x', labelsize=9)

    # Save
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    png_path = output_path / "ldvae_loadings_heatmap.png"
    svg_path = output_path / "ldvae_loadings_heatmap.svg"

    g.fig.savefig(png_path, dpi=300, bbox_inches="tight")
    g.fig.savefig(svg_path, format="svg", bbox_inches="tight")
    plt.close(g.fig)

    print(f"\n  ✓ Loadings heatmap saved")
    print(f"    PNG : {png_path}")
    print(f"    SVG : {svg_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("LDVAE — Linearly Decoded Variational Autoencoder")
    print("=" * 60)
    print()
    print("Reference:")
    print("  Svensson et al. 2020, Bioinformatics 36(11):3418-3421")
    print("  https://doi.org/10.1093/bioinformatics/btaa169")
    print()
    print("Example workflow:")
    print()
    print("  from run_ldvae import (")
    print("      train_ldvae,")
    print("      get_gene_loadings,")
    print("      identify_gene_programs,")
    print("      plot_loadings_heatmap,")
    print("  )")
    print()
    print("  # 1. Subset to HVGs (recommended before training)")
    print("  sc.pp.highly_variable_genes(adata, n_top_genes=3000, flavor='seurat_v3',")
    print("                              layer='counts')")
    print("  adata_hvg = adata[:, adata.var.highly_variable].copy()")
    print()
    print("  # 2. Train LDVAE")
    print("  adata_hvg, model = train_ldvae(")
    print("      adata_hvg,")
    print("      batch_key='sample',   # or None")
    print("      n_latent=15,")
    print("      n_hidden=128,")
    print("      max_epochs=400,")
    print("      save_model='results/ldvae_model',")
    print("  )")
    print()
    print("  # 3. Extract loadings")
    print("  loadings_df = get_gene_loadings(model)")
    print()
    print("  # 4. Identify gene programs")
    print("  programs = identify_gene_programs(loadings_df, n_top_genes=50)")
    print()
    print("  # 5. Visualise heatmap")
    print("  plot_loadings_heatmap(loadings_df, n_top=20, output_dir='results/ldvae')")
    print()
    print("  # 6. Downstream clustering")
    print("  sc.pp.neighbors(adata_hvg, use_rep='X_LDVAE')")
    print("  sc.tl.umap(adata_hvg)")
    print("  sc.pl.umap(adata_hvg, color=['Factor_0', 'Factor_1', 'cell_type'])")
    print()
    print("Notes:")
    print("  - Use n_latent 10-20 (fewer, more interpretable than scVI's 30)")
    print("  - Factor signs are arbitrary: read positive + negative genes together")
    print("  - loadings_df rows are genes; columns are Factor_0 … Factor_N")
    print("  - Transfer latent coords to original adata via index alignment:")
    print("    adata.obsm['X_LDVAE'] = adata_hvg.obsm['X_LDVAE']")
