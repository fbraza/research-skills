# Spatial Deconvolution: Theoretical Foundations

A reference document covering the statistical and computational frameworks underlying spatial transcriptomics deconvolution. Intended as background reading before model selection and as a resource for interpreting outputs.

---

## Table of Contents

1. [What is Spatial Deconvolution?](#1-what-is-spatial-deconvolution)
2. [Statistical Frameworks](#2-statistical-frameworks)
3. [Abundance vs. Proportion](#3-abundance-vs-proportion)
4. [Uncertainty Quantification](#4-uncertainty-quantification)
5. [Gene Overlap and Selection](#5-gene-overlap-and-selection)
6. [Validation Approaches](#6-validation-approaches)

---

## 1. What is Spatial Deconvolution?

Spatial transcriptomics technologies such as 10x Visium capture gene expression at spatially defined positions (spots) across a tissue section. However, each spot typically contains a mixture of multiple cell types — Visium spots are approximately 55 µm in diameter and capture 10–30 cells on average. The measured expression at each spot is therefore a weighted sum of the expression profiles of all cell types present.

Spatial deconvolution is the computational problem of recovering the cellular composition of each spot from the observed mixed expression signal. Formally, given:

- A spatial expression matrix **Y** (n_spots × n_genes) containing raw counts
- A reference signature matrix **S** (n_genes × n_cell_types) learned from a matched scRNA-seq atlas

the goal is to estimate the abundance matrix **C** (n_spots × n_cell_types) such that:

> **Y** ≈ **C** × **S**^T

subject to constraints on **C** (e.g., non-negativity, sum-to-one for proportions).

Different models differ in how they parameterize this relationship, what statistical assumptions they make about the noise process, and whether they can capture variation beyond this linear mixing model.

---

## 2. Statistical Frameworks

### 2.1 Negative Binomial Regression (Cell2location)

Cell2location uses a hierarchical negative binomial (NB) model in two stages.

**Stage 1 — Reference signature learning:** A NB regression model is trained on the single-cell reference data. For each gene g and cell type k, the model estimates a mean expression rate µ_{g,k} from the count distribution. The result is a signature matrix where each entry encodes the expected normalized count for gene g in cell type k, corrected for sequencing depth and optional batch effects.

**Stage 2 — Spatial deconvolution:** Each spot s is modeled as:

> Y_{s,g} ~ NegativeBinomial(mean = Σ_k c_{s,k} × µ_{g,k} × d_s, dispersion = α_g)

where c_{s,k} is the cell abundance of type k at spot s, and d_s is a per-spot detection efficiency parameter. A hierarchical prior on c_{s,k} borrows statistical strength across spots — spots with similar spatial contexts share information, improving estimation for rare cell types.

The key advantages of this framework are:
- Full posterior distributions over cell abundances (not point estimates)
- Hierarchical structure reduces estimation variance for rare cell types
- Explicit modeling of detection efficiency differences across spots

### 2.2 Conditional VAE (DestVI)

DestVI uses two coupled variational autoencoders.

**scLVM (single-cell latent variable model):** Trained on the reference, this VAE learns a cell-type-specific expression model with a continuous per-cell latent variable z that captures intra-type variation. For a cell i of type k:

> x_i | z_i, k ~ NegativeBinomial(decoder_k(z_i))

The latent variable z encodes continuous biological state (e.g., activation level, maturation stage) independently of cell type identity.

**stLVM (spatial latent variable model):** Applied to the spatial data, this model uses the scLVM as a prior. For each spot s and cell type k:

> Y_{s,g} ≈ Σ_k w_{s,k} × f_k(γ_{s,k})

where w_{s,k} is the proportion of type k at spot s, and γ_{s,k} is the local continuous state of type k at spot s — the gamma parameter that distinguishes DestVI from purely proportional methods.

**Key distinction from Cell2location:** DestVI captures continuous within-type variation through γ, enabling spotwise characterization of cell states (not just "how much macrophage" but "what activation state are the macrophages in?").

### 2.3 Optimal Transport (Tangram)

Tangram frames the mapping problem as optimal transport: find the mapping matrix M (n_cells × n_spots) that minimizes a transport cost between the single-cell and spatial gene expression distributions.

The optimization minimizes:

> Loss = -cosine_similarity(M^T × X_sc, X_sp) + regularization(M)

where X_sc is the single-cell expression matrix (n_cells × n_genes) and X_sp is the spatial matrix (n_spots × n_genes). The mapping matrix M is constrained to be non-negative with the density prior controlling how mass is distributed across spots.

Tangram learns M via gradient descent using PyTorch. The result is a probabilistic assignment of each cell to spatial locations, where M_{i,j} represents the probability that single cell i is located at spot j.

**Limitation:** Tangram is deterministic — M is a point estimate with no posterior distribution. Run-to-run variability reflects optimization stochasticity rather than statistical uncertainty.

### 2.4 Environment-Aware VAE (scVIVA)

scVIVA conditions a standard VAE on the spatial niche of each spot. The niche of spot s is defined as the expression and composition of its K nearest spatial neighbors. Formally:

> z_s ~ encoder(x_s, niche_s)
> x_s | z_s ~ decoder(z_s)

where niche_s is computed from the spatial graph of the tissue (K-nearest neighbors in 2D Euclidean space). The latent variable z_s therefore encodes both the intrinsic transcriptional state of the spot and the influence of its microenvironment.

Unlike all other models described here, scVIVA does not require a reference and does not perform deconvolution. Its output is a niche-aware representation of each spot, not a decomposition into cell type proportions.

---

## 3. Abundance vs. Proportion

Cell2location and DestVI both output cell type abundance estimates, but the distinction between absolute abundance and relative proportion matters for biological interpretation.

**Absolute abundance (Cell2location default output: `q05_cell_abundance_w_sf`):** Represents the estimated number of cells of each type at each spot, corrected for detection efficiency. Values are in units of cells. A spot with abundance values [Macrophage: 5.2, T cell: 2.1, Fibroblast: 0.8] is estimated to contain roughly 5 macrophages, 2 T cells, and 1 fibroblast.

Absolute abundances reflect:
- Cell density differences across tissue regions (e.g., lymphoid aggregates vs. stroma)
- True variation in cellularity (e.g., dense vs. sparse areas)

**Relative proportion:** Computed by row-normalizing the abundance matrix so values sum to 1 per spot. A spot with normalized proportions [Macrophage: 0.62, T cell: 0.25, Fibroblast: 0.10] contains predominantly macrophages by relative composition.

Relative proportions:
- Remove information about total cell density
- Are useful for comparing relative cell type composition across spots
- Are appropriate for most visualization and comparative analyses

**Recommendation:** Use absolute abundances (`q05_cell_abundance_w_sf` or `means_cell_abundance_w_sf`) when comparing cell density across tissue regions. Use row-normalized proportions when comparing relative composition (e.g., proportion of T cells in lesion vs. perilesional tissue).

---

## 4. Uncertainty Quantification

Different models provide fundamentally different levels of uncertainty information, and this distinction should drive analysis choices.

**Cell2location — Full Bayesian posterior:**
Cell2location exports three quantiles from the posterior distribution of cell abundances:
- `q05_cell_abundance_w_sf`: 5th percentile — conservative lower bound; a spot is confidently said to contain cell type k if q05 > threshold
- `means_cell_abundance_w_sf`: posterior mean — best point estimate; use for visualization
- `q95_cell_abundance_w_sf`: 95th percentile — upper bound; use to identify high but uncertain estimates

The spread between q05 and q95 is a direct readout of estimation uncertainty. Wide intervals indicate that the data are insufficient to constrain the estimate (e.g., few informative genes, low counts). Narrow intervals reflect confident estimates.

**DestVI — Variational posterior:**
DestVI provides posterior samples via the variational approximation. Uncertainty in proportions and gamma values is available through repeated sampling from the posterior, but DestVI does not provide the same clean quantile summaries as Cell2location. Uncertainty is encoded implicitly in the variational approximation.

**Tangram — No uncertainty:**
Tangram produces a single deterministic mapping matrix M. There is no built-in uncertainty quantification. Run-to-run variation from stochastic optimization can be used as a practical proxy for stability, but it does not represent statistical uncertainty.

**scVIVA — Stochastic sampling:**
As a VAE, scVIVA can produce multiple samples from the latent posterior for each spot. However, uncertainty is not currently exposed through standard output methods. The stochastic nature means repeated calls to `get_latent_representation()` will produce slightly different embeddings unless sampling is disabled.

**Practical implication:** When downstream analyses require confident cell type assignments (e.g., thresholding spots as containing or not containing a cell type), prefer Cell2location's q05 quantile. Never use Tangram outputs for thresholding decisions — the absence of uncertainty estimates means it is unknown whether low probability mappings are biologically real or estimation artifacts.

---

## 5. Gene Overlap and Selection

All reference-based deconvolution models require shared genes between the scRNA-seq reference and the spatial data. The number and identity of shared genes directly affects deconvolution quality.

**Minimum overlap:** Aim for at least 500 shared genes. Below this threshold, cell type signatures become unreliable. Fewer than 200 shared genes should be treated as a data quality failure requiring gene name harmonization.

**Strategy by model:**

| Model | Gene selection strategy | Rationale |
|---|---|---|
| Cell2location | Permissive filtering: retain all genes expressed in ≥5 cells in reference, intersect with spatial | More genes improve NB regression stability; restrictive HVG selection degrades signatures |
| DestVI | Inherits from scVI HVG selection (~2000–4000 HVGs) | scVI trains on HVGs; DestVI uses the same gene set |
| Tangram | Selective marker genes (100–500) | Optimal transport is sensitive to noisy genes; informative markers dominate the mapping signal |
| scVIVA | Standard HVG selection | As a self-contained VAE on spatial data, follows standard scRNA-seq practice |

**Gene name harmonization:** The most common source of low overlap is gene naming inconsistency between the reference and spatial data. Frequent issues include:
- ENSEMBL IDs in one dataset, gene symbols in the other
- Species prefixes added by CellRanger multi-genome references (e.g., `GRCh38_CD3E`)
- Version suffixes on ENSEMBL IDs (e.g., `ENSG00000010610.3`)
- Mixed capitalization (mouse gene symbols in lowercase, human in uppercase)

Always inspect `sc_adata.var_names[:10]` and `sp_adata.var_names[:10]` before running any deconvolution model to detect naming mismatches early.

---

## 6. Validation Approaches

Spatial deconvolution results cannot be directly validated against ground truth in most experimental settings. The following validation strategies assess biological plausibility and technical consistency.

### 6.1 Marker Gene Correlation

The strongest cell-type-specific marker genes (e.g., CD3D for T cells, CD68 for macrophages) should correlate with the estimated proportion of their respective cell types across spots.

```python
import scipy.stats as stats
import pandas as pd

# Example: validate T cell proportions using CD3D expression
if "CD3D" in sp_adata.var_names:
    cd3d_expr = sp_adata[:, "CD3D"].X.toarray().flatten()
    t_cell_prop = sp_adata.obsm["cell_type_proportions"]["T cell"].values
    r, p = stats.pearsonr(cd3d_expr, t_cell_prop)
    print(f"CD3D vs T cell proportion: r={r:.3f}, p={p:.2e}")
    # Expect r > 0.4 for a well-performing deconvolution
```

A Pearson correlation r > 0.4 between a cell type's top marker and its estimated proportion is a reasonable benchmark. Very low correlations (r < 0.2) indicate potential problems with the reference, gene overlap, or cell type annotation.

### 6.2 Spatial Coherence

Estimated cell type proportions should form biologically plausible spatial patterns consistent with known tissue anatomy. Validation steps:

1. Visualize each cell type's proportions as a spatial heatmap using `sc.pl.spatial()`
2. Confirm that tissue-structure-defining cell types are enriched in their expected anatomical zones (e.g., epithelial cells at tissue boundaries, immune cells in known immune niches)
3. Check that proportions are spatially smooth with local coherence — random "salt-and-pepper" patterns across every spot suggest poor deconvolution

### 6.3 Cross-Method Comparison

When multiple deconvolution methods are available, comparing their outputs provides a consistency check. Cell2location and DestVI are expected to produce correlated proportion estimates for the same cell types in the same tissue.

```python
# Compare Cell2location and DestVI proportions for the same cell type
import numpy as np
import scipy.stats as stats

c2l_prop = sp_adata.obsm["q50_cell_abundance_w_sf_norm"]["Macrophage"]
destvi_prop = sp_adata.obsm["proportions"]["Macrophage"]

r, p = stats.pearsonr(c2l_prop, destvi_prop)
print(f"Cell2location vs DestVI (Macrophage): r={r:.3f}")
# r > 0.7 indicates good agreement between methods
```

Strong cross-method agreement (r > 0.7) increases confidence in the biological signal. Major discrepancies should be investigated by inspecting the gene overlap, reference quality, and model training diagnostics.

### 6.4 Reference Self-Consistency

Before running spatial deconvolution, validate the reference signatures by examining the signature matrix:

```python
import seaborn as sns
import matplotlib.pyplot as plt

# Cell2location: visualize signature matrix (genes × cell types)
# Should show strong diagonal enrichment when sorted by cell type
sig_matrix = sc_adata.varm["means_per_cluster_mu_fg"].T  # cell_types × genes
top_markers = {}
for ct in sig_matrix.index:
    top_markers[ct] = sig_matrix.loc[ct].nlargest(5).index.tolist()

# Plot heatmap of top markers per cell type
marker_genes = list(set([g for genes in top_markers.values() for g in genes]))
plt.figure(figsize=(12, 6))
sns.heatmap(
    sig_matrix[marker_genes],
    cmap="viridis",
    xticklabels=True,
)
plt.title("Reference signatures — expect diagonal enrichment")
plt.tight_layout()
plt.savefig("results/signature_validation.png", dpi=150)
```

If the signature matrix does not show clear enrichment of known markers for each cell type, the reference annotations are likely unreliable and should be corrected before proceeding.
