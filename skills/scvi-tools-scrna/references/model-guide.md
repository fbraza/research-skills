# scvi-tools scRNA-seq Model Guide

A practical reference for choosing and using each scvi-tools model for single-cell RNA-seq analysis. Covers model purpose, parameter selection, API usage, and output interpretation.

---

## Table of Contents

1. [scVI](#scvi-lopez-et-al-2018)
2. [scANVI](#scanvi-xu-et-al-2021)
3. [LDVAE](#ldvae-svensson-et-al-2020)
4. [CellAssign](#cellassign-zhang-et-al-2019)
5. [VeloVI](#velovi-gayoso-et-al-2023)
6. [Model Selection Flowchart](#model-selection-flowchart)

---

## scVI (Lopez et al. 2018)

### Purpose

scVI (Single-Cell Variational Inference) is a deep generative model based on a variational autoencoder (VAE) that models raw count data using a negative binomial or zero-inflated negative binomial likelihood. The model learns a low-dimensional latent representation of each cell that captures biological variation while treating technical effects — batch of origin, sequencing depth, and other covariates — as nuisance variables. This disentanglement enables downstream tasks such as batch-corrected dimensionality reduction, denoised normalized expression estimation, and probabilistic differential expression testing that accounts for the full posterior uncertainty rather than point estimates.

### When to Use

- Starting any new scRNA-seq project — scVI is the standard first-pass integration and embedding step
- Integrating data from multiple batches, donors, protocols, or studies
- Generating batch-corrected latent embeddings for clustering and UMAP visualization
- Obtaining denoised, library-size-normalized expression values for visualization or downstream scoring
- Running probabilistic differential expression between two or more groups within a batch-corrected framework
- As a prerequisite model before training scANVI, LDVAE, or Solo

### Key Parameters

| Parameter | Default | Recommended Range | Notes |
|---|---|---|---|
| `n_latent` | 10 | 10–50 | Use 30 for datasets >10k cells; too few collapses variation, too many adds noise |
| `n_layers` | 1 | 1–3 | 2 layers improves reconstruction for complex datasets; rarely need >3 |
| `n_hidden` | 128 | 64–256 | Scale up for very large or heterogeneous datasets |
| `gene_likelihood` | `"zinb"` | `"nb"`, `"zinb"`, `"poisson"` | `"nb"` preferred for most 10x datasets; `"zinb"` for highly sparse data; `"poisson"` rarely needed |
| `dropout_rate` | 0.1 | 0.0–0.2 | Applied to encoder only; higher values regularize more |
| `dispersion` | `"gene"` | `"gene"`, `"gene-batch"`, `"gene-cell"` | `"gene"` is stable; `"gene-batch"` for strong batch-specific noise |
| `batch_key` | `None` | — | Always set when data has multiple batches; leave `None` only for homogeneous data |
| `max_epochs` | auto | 200–400 | Auto-set based on dataset size; monitor ELBO to confirm convergence |

### API Quick Reference

```python
import scvi

# 1. Register AnnData — always use raw counts stored in a layer or .X
scvi.model.SCVI.setup_anndata(
    adata,
    layer="counts",        # key in adata.layers containing raw integer counts
    batch_key="batch",     # column in adata.obs; omit only for single-batch data
)

# 2. Instantiate and train
model = scvi.model.SCVI(adata, n_latent=30, n_layers=2, gene_likelihood="nb")
model.train(max_epochs=300)

# 3. Extract results
adata.obsm["X_scVI"] = model.get_latent_representation()   # (n_cells, n_latent)
adata.layers["scVI_norm"] = model.get_normalized_expression()  # denoised counts

# 4. Differential expression (Bayesian, group1 vs group2)
de_results = model.differential_expression(
    groupby="cell_type",
    group1="Macrophage",
    group2="Monocyte",
)

# 5. Save and reload model
model.save("models/scvi_model/", overwrite=True)
model = scvi.model.SCVI.load("models/scvi_model/", adata=adata)
```

### DOs and DON'Ts

**DO:**
- Always pass raw integer counts (not log-normalized values)
- Filter to highly variable genes (HVGs) before training — typically 2,000–5,000 genes
- Always register a `batch_key` when data comes from multiple sources
- Monitor ELBO convergence by checking `model.history["elbo_train"]`; flat curves indicate convergence
- Save trained models with `model.save()` — retraining is expensive
- Use `get_normalized_expression()` for gene expression visualization, not raw counts
- Set a random seed with `scvi.settings.seed = 42` before training for reproducibility

**DON'T:**
- Pass log-normalized or scaled data — the model expects raw counts
- Treat individual latent dimensions as biologically interpretable — the latent space is a collective representation
- Ignore training loss curves — non-converging models produce unreliable embeddings
- Skip `batch_key` registration for multi-batch data — embeddings will confound biology with technical variation
- Use DE results without the `lfc_mean` (log fold change) alongside `proba_de` — significance without effect size is uninformative

### Output Interpretation

| Output | Method | Interpretation |
|---|---|---|
| Latent embedding | `get_latent_representation()` | Batch-corrected cell coordinates; use for UMAP, clustering (Leiden/Louvain), and kNN graphs |
| Normalized expression | `get_normalized_expression()` | Library-size-normalized, denoised expression; suitable for dot plots, violin plots, scoring |
| DE table | `differential_expression()` | Reports `lfc_mean` (expected log FC), `proba_de` (posterior probability of DE), `bayes_factor`; threshold on `lfc_mean > 0.5` and `proba_de > 0.8` |
| Feature correlations | `get_feature_correlation_matrix()` | Gene-gene correlations in latent space; use for co-expression analysis or gene module discovery |

---

## scANVI (Xu et al. 2021)

### Purpose

scANVI (Single-Cell ANnotation using Variational Inference) extends scVI with a semi-supervised classification objective. Given a dataset where some cells carry known cell type labels and others do not, scANVI simultaneously learns a batch-corrected latent representation and a classifier that assigns cell types to unlabeled cells. The model can be initialized from a pretrained scVI model — the recommended approach — which transfers learned batch correction to the annotation step. The resulting latent space is cell type-aware: cells of the same type cluster together even across batches, making it superior to scVI alone for reference-based annotation and query-to-reference mapping.

### When to Use

- Annotating new (query) cells using labels from a reference dataset with at least partial annotations
- Transfer learning: propagating well-validated labels from one study to an unlabeled dataset
- Joint analysis of labeled and unlabeled cells from the same experiment
- Building a cell type classifier with calibrated uncertainty (soft probabilities) rather than hard assignments
- Improving latent space structure for rare cell types that may not cluster cleanly in unsupervised scVI

### Key Parameters

| Parameter | Default | Recommended Range | Notes |
|---|---|---|---|
| `labels_key` | required | — | Column in `adata.obs` containing cell type labels; must be set |
| `unlabeled_category` | `"Unknown"` | any string | Cells with this label are treated as unlabeled; all other categories are used as supervision |
| `n_latent` | 10 | 10–30 | Inherits from scVI; use same value as pretrained scVI model |
| `n_layers` | 1 | 1–3 | Must match pretrained scVI when using `from_scvi_model` |
| `n_hidden` | 128 | 64–256 | Must match pretrained scVI when using `from_scvi_model` |
| `max_epochs` | auto | 20–100 | scANVI converges faster than scVI when initialized from pretrained model |

### API Quick Reference

```python
import scvi

# --- Recommended: initialize from a pretrained scVI model ---

# Step 1: Train scVI first (see scVI section)
scvi.model.SCVI.setup_anndata(adata, layer="counts", batch_key="batch")
scvi_model = scvi.model.SCVI(adata, n_latent=30, n_layers=2)
scvi_model.train(max_epochs=300)

# Step 2: Convert to scANVI, specifying which label marks unlabeled cells
scanvi_model = scvi.model.SCANVI.from_scvi_model(
    scvi_model,
    labels_key="cell_type",        # column in adata.obs
    unlabeled_category="Unknown",  # cells with this label are unlabeled
)
scanvi_model.train(max_epochs=20)  # fine-tuning on top of scVI

# Step 3: Extract results
adata.obsm["X_scANVI"] = scanvi_model.get_latent_representation()
adata.obs["predicted_cell_type"] = scanvi_model.predict()
soft_probs = scanvi_model.predict(soft=True)  # DataFrame: n_cells x n_cell_types

# --- Alternative: train from scratch (less preferred) ---
scvi.model.SCANVI.setup_anndata(
    adata,
    layer="counts",
    batch_key="batch",
    labels_key="cell_type",
    unlabeled_category="Unknown",
)
scanvi_model = scvi.model.SCANVI(adata)
scanvi_model.train()
```

### DOs and DON'Ts

**DO:**
- Initialize scANVI from a pretrained scVI model using `from_scvi_model` — this produces better batch correction than training from scratch
- Use high-quality, consistent seed labels; noisy or mislabeled seeds degrade performance for all cells
- Check prediction confidence: flag cells with maximum soft probability below 0.8 as uncertain
- Verify predictions on the labeled subset — prediction accuracy on known labels is a sanity check for the full dataset
- Use `get_latent_representation()` from scANVI (not scVI) for downstream analyses when annotation matters

**DON'T:**
- Expect scANVI to discover novel cell types not present in training labels — it is a classifier, not a discovery tool
- Use poorly curated labels (e.g., contaminated clusters, mixed doublets) as seeds — garbage in, garbage out
- Ignore low-confidence predictions — cells with max soft probability below 0.5 may be novel types, doublets, or contamination
- Use scANVI as a substitute for unsupervised exploration — run scVI first to identify structure, then apply scANVI

### Output Interpretation

| Output | Method | Interpretation |
|---|---|---|
| Cell type-aware embedding | `get_latent_representation()` | Same format as scVI but biased toward cell type separation; preferred for type-aware visualization |
| Hard predictions | `predict()` | Most likely cell type per cell; use as starting point, not ground truth |
| Soft probabilities | `predict(soft=True)` | DataFrame of probabilities per type per cell; low max probability indicates ambiguity or a possible novel type |

---

## LDVAE (Svensson et al. 2020)

### Purpose

LDVAE (Linearly Decoded Variational Autoencoder) replaces the nonlinear decoder of scVI with a single linear layer. Each latent dimension corresponds to a gene loading vector, making the factors directly interpretable as gene programs — analogous to independent components in ICA or factors in NMF, but learned within a probabilistic count model. The trade-off is reduced reconstruction quality compared to scVI: the linear decoder cannot capture nonlinear gene-factor relationships. LDVAE is appropriate when interpretability of latent factors is the primary goal and when the biological question is "what gene programs structure this data" rather than "what is the best batch-corrected embedding."

### When to Use

- Discovering interpretable transcriptional programs that drive cell state variation
- Generating a loadings matrix to identify top genes per biological axis
- Situations where you need to communicate or validate latent factors biologically (e.g., grant figures, mechanistic follow-up)
- As a complement to scVI: run scVI for clustering/integration, run LDVAE for factor interpretation
- Datasets where factor interpretability is more valuable than optimal reconstruction

### Key Parameters

| Parameter | Default | Recommended Range | Notes |
|---|---|---|---|
| `n_latent` | 10 | 5–20 | Use fewer dimensions than scVI — each must be biologically interpretable; 10 is a practical upper bound for most analyses |
| `n_hidden` | 128 | 64–256 | Controls encoder capacity only (decoder is linear) |
| `n_layers` | 1 | 1–2 | Encoder layers only |
| `dropout_rate` | 0.1 | 0.0–0.2 | Applied to encoder |
| `gene_likelihood` | `"nb"` | `"nb"`, `"zinb"` | Same as scVI |

### API Quick Reference

```python
import scvi
import pandas as pd

# 1. Register AnnData (same requirements as scVI — raw counts)
scvi.model.LinearSCVI.setup_anndata(
    adata,
    layer="counts",
    batch_key="batch",
)

# 2. Instantiate and train — use fewer latent dims than scVI
model = scvi.model.LinearSCVI(adata, n_latent=10)
model.train(max_epochs=300)

# 3. Extract latent representation (use for UMAP, clustering)
adata.obsm["X_LDVAE"] = model.get_latent_representation()

# 4. Extract loadings matrix — rows are genes, columns are latent factors
loadings = model.get_loadings()          # returns DataFrame: n_genes x n_latent
adata.varm["LDVAE_loadings"] = loadings.values

# 5. Identify top genes per factor
n_top = 20
for factor in loadings.columns:
    top_genes = loadings[factor].abs().nlargest(n_top).index.tolist()
    print(f"{factor}: {top_genes}")
```

### DOs and DON'Ts

**DO:**
- Use fewer latent dimensions than you would with scVI — each factor needs to be biologically interpretable, so quality beats quantity
- Examine the full loadings matrix: look at both the sign and magnitude of gene weights per factor
- Identify top positive and top negative genes per factor separately — they represent opposing ends of a biological axis
- Validate factors against known biology: factor genes should form coherent pathways or cell-type signatures
- Use LDVAE alongside scVI rather than instead of it — scVI for integration, LDVAE for interpretation

**DON'T:**
- Expect reconstruction quality comparable to scVI — the linear decoder is a deliberate constraint, not a bug
- Use LDVAE as the primary tool for batch correction or integration — the nonlinear decoder in scVI handles this better
- Use more than 20 latent dimensions — interpretability degrades rapidly and factors become redundant
- Ignore factor sign — negative loadings are as meaningful as positive ones

### Output Interpretation

| Output | Method | Interpretation |
|---|---|---|
| Latent embedding | `get_latent_representation()` | Cell coordinates in factor space; use for UMAP and clustering as with scVI, but factors have gene-level meaning |
| Loadings matrix | `get_loadings()` | DataFrame (n_genes x n_factors); each column is a gene program; positive loading = gene increases along that factor, negative = decreases; rank by absolute value to find top drivers |

---

## CellAssign (Zhang et al. 2019)

### Purpose

CellAssign is a probabilistic model for marker-based cell type annotation. Rather than learning labels from a reference dataset (as in scANVI), CellAssign uses a user-supplied binary marker gene matrix encoding prior biological knowledge about which genes are elevated in each cell type. It models each cell's expression using a negative binomial likelihood conditioned on cell-type-specific marker gene activity, and assigns each cell to the type that maximizes posterior probability. The model handles marker gene overlap and expression ambiguity through soft assignments with calibrated uncertainty. CellAssign is the appropriate choice when validated marker gene lists are available but a labeled reference dataset is not.

### When to Use

- Annotating cells using established marker genes from the literature or curated databases (e.g., CellMarker, PanglaoDB)
- Situations where a labeled scRNA-seq reference does not exist for your tissue or species
- Rapid, hypothesis-driven annotation where specific cell types are expected a priori
- Validating cluster-based annotation: use CellAssign in parallel to confirm marker-based identity
- Clinical or translational datasets where cell types are well-defined by established markers

### Key Parameters

| Parameter | Default | Recommended Range | Notes |
|---|---|---|---|
| `marker_gene_mat` | required | — | Binary DataFrame: rows = genes, columns = cell types; 1 = marker, 0 = not; must be genes present in `adata.var_names` |
| `size_factor_key` | required | — | Column in `adata.obs` with per-cell size factors (library size or scran-estimated); must be set |
| `max_epochs` | 1000 | 400–1000 | CellAssign typically converges slower than scVI-based models |

### API Quick Reference

```python
import scvi
import pandas as pd
import numpy as np

# 1. Build binary marker gene matrix (genes x cell types)
#    Rows must be gene names matching adata.var_names
marker_gene_mat = pd.DataFrame({
    "Macrophage":  [1, 1, 0, 0, 0],  # CD68, CSF1R, CD3D, CD19, EPCAM
    "T_cell":      [0, 0, 1, 0, 0],
    "B_cell":      [0, 0, 0, 1, 0],
    "Epithelial":  [0, 0, 0, 0, 1],
}, index=["CD68", "CSF1R", "CD3D", "CD19", "EPCAM"])

# Verify all marker genes are in the dataset
missing = [g for g in marker_gene_mat.index if g not in adata.var_names]
if missing:
    raise ValueError(f"Marker genes missing from adata: {missing}")

# Subset adata to marker genes only (required by CellAssign)
adata_markers = adata[:, marker_gene_mat.index].copy()

# 2. Compute size factors (library-size normalization)
#    Option A: simple library size
adata_markers.obs["size_factor"] = (
    adata_markers.layers["counts"].sum(axis=1).A1
    / np.median(adata_markers.layers["counts"].sum(axis=1).A1)
)
#    Option B: use scran-estimated size factors (preferred for droplet data)

# 3. Register AnnData
scvi.external.CellAssign.setup_anndata(
    adata_markers,
    layer="counts",
    size_factor_key="size_factor",
)

# 4. Train
model = scvi.external.CellAssign(adata_markers, marker_gene_mat)
model.train(max_epochs=1000)

# 5. Predict
predictions = model.predict()  # DataFrame: n_cells x n_cell_types (probabilities)
adata.obs["cellassign_type"] = predictions.idxmax(axis=1)
adata.obs["cellassign_confidence"] = predictions.max(axis=1)
```

### DOs and DON'Ts

**DO:**
- Validate that every gene in `marker_gene_mat` is present in `adata.var_names` before training — missing genes cause silent failures
- Include an "other" or "unassigned" catch-all column in the marker matrix to capture cells that do not match any defined type; without it, every cell is forced into one of the listed types
- Use at least 3 marker genes per cell type — single-marker types are unreliable due to dropout
- Check per-cell confidence scores (max probability column) — cells below 0.7 should be flagged as ambiguous
- Use scran or library-size-estimated size factors stored in `adata.obs` before calling `setup_anndata`

**DON'T:**
- Use CellAssign without first verifying the marker matrix: low-specificity markers (e.g., housekeeping genes) produce noise
- Expect annotation of cell types not listed in the marker matrix — CellAssign is a closed-set classifier
- Use poor-quality marker genes (e.g., genes that are not specifically elevated in the target type in your tissue/context)
- Forget to compute and register size factors — omitting them or using incorrect normalization degrades probability estimates

### Output Interpretation

| Output | Method | Interpretation |
|---|---|---|
| Probability matrix | `predict()` | DataFrame (n_cells x n_cell_types); each row sums to 1; high max probability (>0.8) = confident assignment |
| Hard labels | `predictions.idxmax(axis=1)` | Most probable cell type; always inspect alongside confidence score |
| Confidence score | `predictions.max(axis=1)` | Values below 0.7 indicate ambiguous cells — investigate manually or label as "unassigned" |

---

## VeloVI (Gayoso et al. 2023)

### Purpose

VeloVI (Variational Inference for RNA Velocity) models the joint distribution of spliced and unspliced RNA counts using a deep generative model to estimate RNA velocity with uncertainty quantification. Classical RNA velocity methods (scVelo) fit deterministic kinetic equations per gene but do not propagate uncertainty through the velocity estimates. VeloVI instead learns a latent representation of cell state that governs transcriptional kinetics for all genes simultaneously, enabling principled uncertainty estimates for both velocity magnitude and direction. This is particularly valuable for validating whether observed dynamics are statistically supported and for identifying genes with coherent versus noisy velocity signals.

### When to Use

- Inferring cellular differentiation trajectories using spliced and unspliced RNA counts from STARsolo, Alevin, or Velocyto
- RNA velocity analysis in datasets with suspected batch effects (VeloVI integrates batch correction into the velocity model)
- Any velocity analysis where you need uncertainty quantification — do not trust point-estimate velocity methods for sparse or noisy data
- Verifying whether velocity signals are biologically meaningful using permutation-based coherence scores
- Comparing velocity-based trajectory direction across conditions or batches within a single integrated model

### Key Parameters

| Parameter | Default | Recommended Range | Notes |
|---|---|---|---|
| `spliced_layer` | `"Ms"` | `"Ms"`, `"spliced"` | Key in `adata.layers` for smoothed spliced counts from scVelo preprocessing |
| `unspliced_layer` | `"Mu"` | `"Mu"`, `"unspliced"` | Key in `adata.layers` for smoothed unspliced counts |
| `n_latent` | 10 | 10–30 | Latent dimensions for cell state; 20–30 for complex differentiation trajectories |
| `n_layers` | 2 | 1–3 | Hidden layers in encoder and decoder |
| `n_hidden` | 128 | 64–256 | Hidden units per layer |

### API Quick Reference

```python
import scvi
import scvelo as scv

# 1. Prerequisite: preprocess with scVelo to obtain smoothed spliced/unspliced layers
scv.pp.filter_and_normalize(adata, min_shared_counts=20, n_top_genes=2000)
scv.pp.moments(adata, n_pcs=30, n_neighbors=30)
# adata.layers now contains "Ms" (spliced) and "Mu" (unspliced)

# 2. Register AnnData
scvi.external.VELOVI.setup_anndata(
    adata,
    spliced_layer="Ms",
    unspliced_layer="Mu",
)

# 3. Train
model = scvi.external.VELOVI(adata, n_latent=20)
model.train(max_epochs=500)

# 4. Extract velocity and latent time
adata.layers["velocity"] = model.get_velocity()       # (n_cells, n_genes) velocities
adata.obs["latent_time"] = model.get_latent_time()    # (n_cells,) pseudotime [0, 1]

# 5. Compute velocity coherence (permutation-based validation)
#    High coherence = velocity is consistent with cell neighborhood structure
scv.tl.velocity_graph(adata, vkey="velocity")
scv.tl.velocity_confidence(adata, vkey="velocity")

# 6. Visualize
scv.pl.velocity_embedding_stream(adata, basis="umap", vkey="velocity")
scv.pl.latent_time(adata)
```

### DOs and DON'Ts

**DO:**
- Always preprocess with `scvelo.pp.filter_and_normalize` and `scvelo.pp.moments` before VeloVI — the model expects smoothed `Ms`/`Mu` layers
- Validate velocity using permutation scores (`scv.tl.velocity_confidence`) — uninformative velocity is indistinguishable from noise without this check
- Examine velocity coherence per cell type: low coherence in a subpopulation suggests that type is in steady state or that velocity is unreliable there
- Verify your dataset contains transient dynamics (i.e., actively differentiating or cycling cells) — velocity is meaningless for fully differentiated, quiescent populations
- Use `get_latent_time()` as a pseudotime measure only in lineages where velocity is coherent

**DON'T:**
- Apply VeloVI to steady-state datasets where all cells have reached equilibrium — velocity estimates will be noise
- Trust velocity arrows on 2D UMAP projections without permutation validation — UMAP distorts distances and arrows can be misleading
- Skip scVelo preprocessing — raw spliced/unspliced counts without moment smoothing produce poor velocity estimates
- Interpret `latent_time` as wall-clock time or generation time — it is a relative ordering, not an absolute timescale
- Ignore the uncertainty outputs — high variance in velocity for a gene means that gene's contribution to the velocity vector should be down-weighted in interpretation

### Output Interpretation

| Output | Method | Interpretation |
|---|---|---|
| Velocity vectors | `get_velocity()` | Per-cell, per-gene velocity values (n_cells x n_genes); positive = gene is being upregulated (unspliced > expected from spliced), negative = being downregulated; used as input to `scv.tl.velocity_graph` |
| Latent time | `get_latent_time()` | Per-cell pseudotime value in [0, 1]; valid only in lineages with coherent velocity; use for ordering cells along a differentiation axis |
| Velocity coherence | `scv.tl.velocity_confidence()` | Per-cell score measuring consistency of velocity direction with neighborhood structure; values below 0.7 indicate unreliable velocity; inspect per cell type |

---

## Model Selection Flowchart

```
START
  │
  ├─ Need batch integration or embedding? ──────────────────> scVI (always run first)
  │     │
  │     ├─ Have partial cell type labels? ──────────────────> scANVI (from pretrained scVI)
  │     ├─ Need interpretable gene programs? ───────────────> LDVAE
  │     └─ Need condition comparison DE? ───────────────────> scVI / scANVI Bayesian DE
  │
  ├─ Have marker gene panel, no labeled reference? ─────────> CellAssign
  │
  └─ Have spliced/unspliced counts + transient dynamics? ───> VeloVI
```

### Summary Decision Table

| Goal | Model | Notes |
|---|---|---|
| Batch correction + embedding | scVI | Always the starting point |
| Cell type annotation from labels | scANVI | Initialize from scVI |
| Interpretable gene programs | LDVAE | Complement to scVI, not a replacement |
| Marker-based annotation, no reference | CellAssign | Requires curated marker gene matrix |
| RNA velocity + uncertainty | VeloVI | Requires scVelo preprocessing |

---

*Models are listed in recommended workflow order. In practice, most projects begin with scVI, layer in scANVI or LDVAE for annotation/interpretation, and optionally add CellAssign or VeloVI for specialized questions.*
