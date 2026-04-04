# scvi-tools Spatial Transcriptomics Model Guide

A practical reference for choosing and using each spatial transcriptomics model supported in the scvi-tools ecosystem. Covers model purpose, parameter selection, API usage, and output interpretation.

---

## Table of Contents

1. [Cell2location](#cell2location-kleshchevnikov-et-al-2022)
2. [DestVI](#destvi-lopez-et-al-2022)
3. [Tangram](#tangram-biancalani-et-al-2021)
4. [scVIVA](#scviva-levy-et-al-2025--experimental)
5. [Model Selection Flowchart](#model-selection-flowchart)

---

## Cell2location (Kleshchevnikov et al. 2022)

### Purpose

Cell2location is a hierarchical Bayesian model for robust, probabilistic cell type deconvolution of spatial transcriptomics data. The model operates in two sequential stages: first, a negative binomial regression model is trained on a single-cell reference to learn per-gene, per-cell-type expression signatures (reference signatures); second, a hierarchical factorization model decomposes each spatial spot's expression as a linear combination of those signatures, estimating the absolute cellular abundance per cell type per spot with full posterior uncertainty. The hierarchical priors borrow statistical strength across spots, enabling reliable estimation even in spots with few cells or low sequencing depth. Cell2location is the current gold standard for cell type proportion estimation in spot-based spatial transcriptomics.

### When to Use

- Need reliable cell type abundance estimates with full posterior uncertainty quantification
- Have a well-annotated scRNA-seq reference atlas for the same tissue type
- Working with spot-based spatial data (Visium, Slide-seq, or similar technologies)
- Want to compare cell type distributions across tissue regions or conditions
- Need conservative abundance estimates using posterior quantiles for robust downstream testing

### Key Parameters

| Parameter | Default | Recommended Range | Notes |
|---|---|---|---|
| `labels_key` | required | — | Column in `sc_adata.obs` with cell type labels; must be set for RegressionModel |
| `batch_key` | `None` | — | Set when reference has multiple batches, donors, or samples; improves signature robustness |
| `N_cells_per_location` | 10 | 5–30 | Expected number of cells per spot; Visium is typically 10–20; lower for sparser platforms |
| `detection_alpha` | 20 | 5–200 | Controls sensitivity to between-spot variation in detection efficiency; higher = more regularization |
| `max_epochs` (RegressionModel) | 250 | 200–400 | Sufficient for reference signature training; monitor ELBO |
| `max_epochs` (Cell2location) | 30000 | 20000–40000 | Long training is expected and necessary; do not reduce prematurely |
| `batch_size` | 2500 | 1000–5000 | Larger batches improve GPU throughput; reduce if GPU OOM |
| `use_gpu` | auto | — | Always use GPU when available; CPU training at 30k epochs is prohibitively slow |

### API Quick Reference

```python
import cell2location
import scanpy as sc

# ===== Stage 1: Build reference signatures =====

# 1a. Prepare reference scRNA-seq (raw counts required)
sc_adata.layers["counts"] = sc_adata.X.copy()

# 1b. Filter genes — use permissive filtering (~10k-16k genes)
sc.pp.filter_genes(sc_adata, min_cells=5)

# 1c. Register and train RegressionModel
cell2location.models.RegressionModel.setup_anndata(
    sc_adata,
    layer="counts",
    labels_key="cell_type",  # column in sc_adata.obs
    batch_key="sample",      # set if reference has multiple samples/donors
)
ref_model = cell2location.models.RegressionModel(sc_adata)
ref_model.train(max_epochs=250, use_gpu=True)

# 1d. Export posterior and extract signatures
sc_adata = ref_model.export_posterior(
    sc_adata,
    sample_kwargs={"num_samples": 1000, "batch_size": 2500, "use_gpu": True}
)

# Extract the per-gene, per-cell-type signature matrix
inf_aver = sc_adata.varm["means_per_cluster_mu_fg"][
    [f"means_per_cluster_mu_fg_{ct}" for ct in sc_adata.uns["mod"]["factor_names"]]
].copy()
inf_aver.columns = sc_adata.uns["mod"]["factor_names"]

# ===== Stage 2: Spatial deconvolution =====

# 2a. Filter spatial data to genes in reference
intersect = np.intersect1d(sp_adata.var_names, inf_aver.index)
sp_adata = sp_adata[:, intersect].copy()
inf_aver = inf_aver.loc[intersect, :]

# 2b. Register and train Cell2location
cell2location.models.Cell2location.setup_anndata(
    sp_adata,
    layer="counts",
    batch_key="sample",  # optional: spatial sample/batch
)
sp_model = cell2location.models.Cell2location(
    sp_adata,
    cell_state_df=inf_aver,
    N_cells_per_location=10,
    detection_alpha=20,
)
sp_model.train(
    max_epochs=30000,
    batch_size=2500,
    train_size=1,
    use_gpu=True,
)

# 2c. Export posterior
sp_adata = sp_model.export_posterior(
    sp_adata,
    sample_kwargs={"num_samples": 1000, "batch_size": 2500, "use_gpu": True}
)

# 2d. Extract cell type abundances
# q05: conservative lower bound; q50: median estimate; q95: upper bound
abundance_q05 = sp_adata.obsm["q05_cell_abundance_w_sf"]
abundance_q50 = sp_adata.obsm["means_cell_abundance_w_sf"]

# Convert to proportions (row-normalize)
proportions = abundance_q05.div(abundance_q05.sum(axis=1), axis=0)
sp_adata.obsm["cell_type_proportions"] = proportions

# Save models and results
ref_model.save("models/ref_model/", overwrite=True)
sp_model.save("models/cell2loc_model/", overwrite=True)
sp_adata.write("results/spatial_deconvolved.h5ad")
```

### DOs and DON'Ts

**DO:**
- Use permissive gene filtering for the reference (~10k–16k genes retained); restrictive filtering removes informative genes and degrades signature quality
- Set `batch_key` in the RegressionModel when the reference spans multiple donors, samples, or protocols — this learns donor-invariant signatures
- Validate signatures by plotting the signature matrix: each cell type should show strong enrichment for its known marker genes (diagonal pattern when sorted by cell type)
- Train the spatial model with `train_size=1` (use all spots for training — no validation split needed)
- Use `q05_cell_abundance_w_sf` for conservative downstream analyses (e.g., thresholding spots as containing a cell type); use `means_cell_abundance_w_sf` for visualization
- Always call `export_posterior()` before accessing results in `obsm` — the posterior is not stored until explicitly exported
- Train on GPU; 30k epochs on CPU is not practical for any dataset above a few hundred spots

**DON'T:**
- Use restrictive gene filtering (e.g., top 2000 HVGs) — Cell2location is designed for many genes and performs worse with few
- Skip signature validation — poor reference annotations silently propagate to spatial estimates
- Reduce `max_epochs` below 20k expecting acceptable results — training loss at 30k epochs is still meaningfully lower than at 10k
- Forget to export the posterior before inspecting `obsm` — the keys will not exist otherwise
- Interpret raw abundance values as cell counts without accounting for detection efficiency — use the `w_sf`-corrected outputs

### Output Interpretation

| Output | Key in `obsm` | Interpretation |
|---|---|---|
| Conservative abundance | `q05_cell_abundance_w_sf` | 5th percentile of posterior; use for thresholding (cells present/absent per spot) |
| Median abundance | `means_cell_abundance_w_sf` | Posterior mean; use for visualization and spatial plots |
| Upper abundance | `q95_cell_abundance_w_sf` | 95th percentile; use to identify spots with high but uncertain cell type presence |
| Cell type proportions | Derived by row-normalizing any of the above | Relative composition per spot; computed manually after export |

---

## DestVI (Lopez et al. 2022)

### Purpose

DestVI (Deconvolution of Spatial Transcriptomics using Variational Inference) is a multi-resolution deconvolution model that captures not only discrete cell type proportions but also continuous within-cell-type variation at each spatial location. The model consists of two coupled variational autoencoders: a single-cell latent variable model (scLVM) trained on the reference to learn cell-type-specific expression and a continuous per-cell latent variable capturing intra-type state variation; and a spatial latent variable model (stLVM) that deconvolves each spot using the scLVM as a prior. The key distinguishing feature is the gamma (γ) parameter: a per-cell-type, per-spot continuous variable encoding the local expression state of each cell type, allowing DestVI to detect, for example, M1 versus M2 macrophage activation gradients within a tissue without requiring discrete subtype annotations.

### When to Use

- Expect biologically meaningful continuous variation within a cell type (activation gradients, metabolic states, maturation axes)
- Need more than proportions: want to characterize gene expression state of each cell type per spot
- Study tissues where cell states vary spatially (e.g., tumor microenvironment, inflamed tissue zones)
- Have already trained a scVI model on the reference — DestVI is built directly on top of it
- Want to complement Cell2location results with within-type state information

### Key Parameters

| Parameter | Default | Recommended Range | Notes |
|---|---|---|---|
| `cell_type_key` | required | — | Column in `sc_adata.obs` with cell type labels; passed to `from_rna_model` |
| `amortization` | `"both"` | `"both"`, `"latent"`, `"proportion"` | Controls which parts are amortized; `"both"` is the default and recommended starting point |
| `max_epochs` | 2500 | 1500–3000 | Substantially fewer epochs than Cell2location; typically 30–60 minutes on GPU |
| `n_latent` | inherited | — | Inherited from the scVI model; not set directly in DestVI |

### API Quick Reference

```python
import scvi
import scanpy as sc

# ===== Step 1: Train scVI on single-cell reference =====
# (See scvi-tools-scrna skill for full scVI workflow)
scvi.model.SCVI.setup_anndata(
    sc_adata,
    layer="counts",
    batch_key="batch",
)
sc_model = scvi.model.SCVI(sc_adata, n_latent=30, n_layers=2, gene_likelihood="nb")
sc_model.train(max_epochs=400)

# ===== Step 2: Build DestVI from the scVI model =====
scvi.model.DestVI.setup_anndata(
    sp_adata,
    layer="counts",
)
destvi_model = scvi.model.DestVI.from_rna_model(
    sp_adata,
    sc_model,
    cell_type_key="cell_type",  # column in sc_adata.obs
)
destvi_model.train(max_epochs=2500)

# ===== Step 3: Extract results =====
# Cell type proportions (n_spots × n_cell_types)
proportions = destvi_model.get_proportions()
sp_adata.obsm["proportions"] = proportions

# Cell type-specific gene expression at each spot (n_spots × n_genes, for one cell type)
macrophage_expr = destvi_model.get_scale_for_ct("Macrophage")

# Continuous within-type state per spot (n_spots × n_latent, for one cell type)
macrophage_gamma = destvi_model.get_gamma("Macrophage")
sp_adata.obsm["gamma_Macrophage"] = macrophage_gamma

# Add proportions to .obs for easy spatial plotting
for ct in proportions.columns:
    sp_adata.obs[f"prop_{ct}"] = proportions[ct].values

# Save
destvi_model.save("models/destvi_model/", overwrite=True)
sc_model.save("models/scvi_ref_model/", overwrite=True)
```

### DOs and DON'Ts

**DO:**
- Train scVI on the reference first (using the scvi-tools-scrna skill) before building DestVI — the scVI model is a prerequisite, not optional
- Examine the gamma outputs for cell types where you expect biological gradients: gamma encodes the within-type continuous state and is DestVI's key distinguishing feature over Cell2location
- Validate that gamma variation correlates with known biology (e.g., gamma PC1 correlates with distance from tumor edge for macrophages in tumor sections)
- Use in combination with Cell2location for complementary views: Cell2location for robust proportion estimates, DestVI for state characterization
- Set `batch_key` in the scVI reference model to account for donor effects before transferring to spatial

**DON'T:**
- Skip the scVI training step — DestVI cannot be instantiated without a pretrained scVI model
- Ignore the gamma outputs: if you only want proportions, Cell2location is more appropriate; DestVI's value is in gamma
- Expect DestVI to capture within-type variation for cell types with few cells or low expression in the reference — the scLVM needs adequate reference representation
- Use for purely discrete cell type classification without any expectation of continuous variation — Cell2location is better suited

### Output Interpretation

| Output | Method | Interpretation |
|---|---|---|
| Proportions | `get_proportions()` | DataFrame (n_spots × n_cell_types); row sums to 1; analogous to Cell2location q50 proportions |
| Cell type expression | `get_scale_for_ct(cell_type)` | Estimated gene expression for a given cell type at each spot; enables spotwise DE within a cell type |
| Within-type state | `get_gamma(cell_type)` | Continuous latent variable (n_spots × n_latent) encoding the intra-type state; use PCA or UMAP to interpret; high-loading genes in each gamma PC represent state axes |

---

## Tangram (Biancalani et al. 2021)

### Purpose

Tangram learns an optimal transport mapping between single-cell RNA-seq data and spatial transcriptomics data, placing individual cells (or cell clusters) into specific spatial locations. The model minimizes the transport cost between the single-cell and spatial gene expression distributions using gradient descent on a cosine similarity loss, producing a mapping matrix M of dimensions (n_cells × n_spots) where each entry encodes the probability that a given cell is located at a given spot. This mapping enables two key operations: projecting cell type annotations and other single-cell metadata into spatial coordinates, and imputing the spatial expression of genes measured in scRNA-seq but not in the spatial panel. Unlike Cell2location and DestVI, Tangram does not use a Bayesian framework and provides no uncertainty estimates, but it operates at single-cell resolution and is substantially faster to run.

### When to Use

- Want to map individual cells (or cell clusters) to their most probable spatial location
- Need to impute genes not measured in the spatial panel using the matched scRNA-seq data
- Have good, informative marker genes for the spatial-to-single-cell alignment
- Exploring spatial organization at single-cell resolution as a complement to spot-level deconvolution
- Quick initial analysis before running a full Bayesian deconvolution pipeline

### Key Parameters

| Parameter | Default | Recommended Range | Notes |
|---|---|---|---|
| `mode` | `"cells"` | `"cells"`, `"clusters"` | `"clusters"` maps one embedding per cell type (faster, lower memory); `"cells"` maps each individual cell (higher resolution, slow for large references) |
| `density_prior` | `"rna_count_based"` | `"rna_count_based"`, `"uniform"` | `"rna_count_based"` weights cells by their RNA content, matching the spatial signal better; use `"uniform"` only when cell sizes are homogeneous |
| `num_epochs` | 500 | 300–1000 | Increase if training loss has not plateaued |
| `device` | `"cpu"` | `"cpu"`, `"cuda:0"` | Tangram uses PyTorch device syntax, not scvi-tools accelerator= syntax |
| `cluster_label` | required for clusters mode | — | Column in `sc_adata.obs` specifying cell type/cluster for `mode="clusters"` |

### API Quick Reference

```python
import tangram as tg
import scanpy as sc

# ===== Step 1: Prepare datasets =====
# Both datasets must be filtered to shared genes before alignment
# Select informative marker genes (100–500 recommended)
sc.tl.rank_genes_groups(sc_adata, groupby="cell_type", method="wilcoxon")
markers_df = sc.get.rank_genes_groups_df(sc_adata, group=None)
top_markers = markers_df.groupby("group").head(50)["names"].unique().tolist()

# Filter both datasets to marker genes
tg.pp_adatas(sc_adata, sp_adata, genes=top_markers)

# ===== Step 2: Map cells to space =====
# mode="clusters" — faster, maps average expression per cell type
ad_map = tg.map_cells_to_space(
    adata_sc=sc_adata,
    adata_sp=sp_adata,
    mode="clusters",
    cluster_label="cell_type",      # column in sc_adata.obs
    density_prior="rna_count_based",
    num_epochs=500,
    device="cuda:0",                # or "cpu"
)

# mode="cells" — single-cell resolution (slow for >10k cells)
# ad_map = tg.map_cells_to_space(
#     adata_sc=sc_adata,
#     adata_sp=sp_adata,
#     mode="cells",
#     density_prior="rna_count_based",
#     num_epochs=500,
#     device="cuda:0",
# )

# ad_map.X is the mapping matrix (n_cells/clusters × n_spots)

# ===== Step 3: Project cell type annotations to spatial =====
tg.project_cell_annotations(
    ad_map,
    sp_adata,
    annotation="cell_type",         # column in sc_adata.obs to project
)
# Results stored in sp_adata.obsm["tangram_ct_pred"]

# ===== Step 4: Impute genes not in spatial panel =====
# Specify genes measured in scRNA-seq but absent from spatial data
genes_to_impute = ["CD3D", "CD8A", "FOXP3", "CD163", "SPP1"]
ad_ge = tg.project_genes(
    adata_map=ad_map,
    adata_sc=sc_adata,
)
# ad_ge.X contains imputed gene expression at each spatial spot

# ===== Step 5: Visualize =====
sc.pl.spatial(
    sp_adata,
    color=list(sp_adata.obsm["tangram_ct_pred"].columns),
    spot_size=150,
)

# Validate: compare known spatial markers to Tangram imputation
sc.pl.spatial(sp_adata, color="imputed_FOXP3", spot_size=150)
```

### DOs and DON'Ts

**DO:**
- Select informative, specific marker genes before running Tangram — using all genes dilutes the signal; 100–500 curated markers outperform genome-wide alignment
- Run `mode="clusters"` first to validate alignment quality, then refine with `mode="cells"` if single-cell resolution is needed
- Validate results using genes with known spatial expression patterns: if Tangram correctly recovers the spatial distribution of a held-out marker, the mapping is trustworthy
- Run multiple independent training runs to check result consistency — Tangram is stochastic and individual runs can vary, especially in `mode="cells"`
- Use the mapping matrix from `ad_map.X` directly for custom analyses (e.g., computing spot-to-cell assignment confidence)

**DON'T:**
- Expect uncertainty estimates from Tangram — it is a deterministic optimal transport method; there are no posterior intervals
- Use all genes without marker selection — gene-level noise overwhelms the spatial signal in low-gene-count spatial panels
- Skip validation against known spatial patterns — without it, poor mapping quality is undetectable
- Treat a single Tangram run as final for `mode="cells"` — run at least 3 times and check consistency of top predictions
- Confuse Tangram's device parameter (`device="cuda:0"`) with scvi-tools' accelerator syntax (`accelerator="gpu"`) — they are different APIs

### Output Interpretation

| Output | Location | Interpretation |
|---|---|---|
| Mapping matrix | `ad_map.X` | n_cells/clusters × n_spots; entry (i, j) = probability that cell/cluster i is at spot j; use to compute per-spot abundance |
| Projected annotations | `sp_adata.obsm["tangram_ct_pred"]` | DataFrame (n_spots × n_cell_types); each column is the projected proportion/score for a cell type at each spot |
| Imputed gene expression | `ad_ge.X` or per-gene in `sp_adata` | Predicted expression for genes not measured spatially; validate against held-out spatial markers before use |

---

## scVIVA (Levy et al. 2025) — EXPERIMENTAL

### Purpose

scVIVA (Spatial Cellular Variation via Variational Autoencoders) models how the tissue microenvironment — defined by the spatial neighborhood of a cell or spot — shapes cell state and gene expression. Unlike Cell2location and DestVI, scVIVA does not perform deconvolution and does not require a single-cell reference. Instead, it trains an environment-aware VAE directly on the spatial data, conditioning the latent representation on the composition and expression of K nearest spatial neighbors (the niche). The resulting latent space captures both cell-intrinsic transcriptional state and environment-driven variation, enabling identification of niche-specific gene programs and spatial context effects that standard scRNA-seq analysis cannot detect.

### When to Use

- Primary question is how spatial context (niche) influences cell state, not what cell types are present
- No single-cell reference is available or needed — scVIVA operates on spatial data alone
- Studying tissues where niche effects are biologically central: tumor microenvironment, germinal centers, inflammatory niches
- Want to identify gene programs differentially active in specific spatial neighborhoods
- As a follow-up to deconvolution: first establish proportions with Cell2location, then use scVIVA to characterize niche biology

**Experimental status:** scVIVA was published as a preprint in 2025. The API may change between scvi-tools versions. Always verify method signatures against the installed version documentation.

### Key Parameters

| Parameter | Default | Recommended Range | Notes |
|---|---|---|---|
| `spatial_key` | `"spatial"` | — | Key in `adata.obsm` containing spot/cell coordinates (n_spots × 2); must be set |
| `n_latent` | 30 | 20–50 | Latent dimensions; increase for highly heterogeneous tissues |
| `n_neighbors` (K) | 10 | 6–20 | Number of spatial nearest neighbors defining the niche; smaller K = finer spatial resolution |
| `max_epochs` | auto | 200–400 | Similar to scVI; monitor ELBO |

### API Quick Reference

```python
import scvi

# ===== Prerequisites =====
# Spatial coordinates must be in adata.obsm["spatial"] (n_spots × 2)
# Verify before proceeding
assert "spatial" in sp_adata.obsm, "Spatial coordinates not found in obsm['spatial']"
print(f"Coordinate shape: {sp_adata.obsm['spatial'].shape}")  # Should be (n_spots, 2)

# Raw counts required
sp_adata.layers["counts"] = sp_adata.X.copy()

# ===== Setup and train =====
scvi.external.SCVIVA.setup_anndata(
    sp_adata,
    layer="counts",
    spatial_key="spatial",      # key in obsm with 2D coordinates
)

model = scvi.external.SCVIVA(
    sp_adata,
    n_latent=30,
)
model.train(max_epochs=400)

# ===== Extract outputs =====
# Latent representation incorporating niche context
sp_adata.obsm["X_scVIVA"] = model.get_latent_representation()

# Downstream: UMAP on niche-aware latent space
import scanpy as sc
sc.pp.neighbors(sp_adata, use_rep="X_scVIVA")
sc.tl.umap(sp_adata)
sc.tl.leiden(sp_adata, key_added="scviva_clusters")

# Identify niche-specific gene programs via DE between clusters
# (Use Bayesian DE or standard methods on the cluster assignments)
```

### DOs and DON'Ts

**DO:**
- Verify spatial coordinates are in `adata.obsm["spatial"]` before setup — scVIVA cannot infer coordinates from other locations
- Use scVIVA after deconvolution (Cell2location) for a complete picture: proportions first, then niche biology
- Apply to tissues where spatial context is expected to matter biologically — scVIVA adds least value in well-mixed or uniform tissues
- Check your installed scvi-tools version before using scVIVA and consult the version-specific documentation — the API is not yet stable

**DON'T:**
- Use scVIVA as a primary deconvolution tool — it does not estimate cell type proportions and does not require a reference
- Expect stable API across scvi-tools versions — this is a 2025 preprint and methods may change
- Ignore spatial coordinates — scVIVA's niche definition depends entirely on accurate spatial positioning
- Apply to datasets where cells have no meaningful spatial organization (e.g., dissociated cells mapped back to spatial coordinates without true spatial structure)

### Output Interpretation

| Output | Method | Interpretation |
|---|---|---|
| Niche-aware latent embedding | `get_latent_representation()` | Per-spot representation (n_spots × n_latent) integrating cell-intrinsic state and spatial neighborhood context; use for clustering, UMAP, DE between niches |
| Niche clusters | Leiden on `X_scVIVA` | Spots grouped by similar niche-aware transcriptional state; biologically interprets as spatial niches or microenvironments |
| Niche gene programs | DE between niche clusters | Genes differentially expressed between spatial contexts; represents niche-specific transcriptional programs |

---

## Model Selection Flowchart

```
START
  │
  ├─ Need cell type proportions with uncertainty?
  │   └─ YES → Cell2location (gold standard, Bayesian, hierarchical)
  │         │
  │         └─ Also need within-type continuous states?
  │               └─ YES → DestVI (multi-resolution; requires scVI on reference first)
  │
  ├─ Need single-cell resolution spatial mapping or gene imputation?
  │   └─ YES → Tangram (optimal transport, deterministic, fast)
  │
  └─ Want to study how the spatial niche shapes cell state?
      └─ YES → scVIVA (environment-aware VAE, experimental, no reference needed)
```

### Comparison Table

| Feature | Cell2location | DestVI | Tangram | scVIVA |
|---|---|---|---|---|
| Primary output | Cell type abundances | Proportions + within-type states | Cell-to-spot mapping | Niche-aware embeddings |
| Probabilistic | Yes (full posterior) | Yes (posterior) | No (deterministic) | Yes (stochastic VAE) |
| Uncertainty quantification | q05 / q50 / q95 | Posterior samples | None | Stochastic sampling |
| scRNA-seq reference required | Yes | Yes (scVI model) | Yes | No |
| Package | `cell2location` | `scvi-tools` | `tangram-sc` | `scvi-tools` |
| Approximate training time | 2–6 hours (30k epochs, GPU) | 30–60 min (2.5k epochs) | 5–30 min | 30–60 min |
| Unique capability | Posterior abundance with spatial priors | Gamma: continuous intra-type state per spot | Gene imputation + single-cell mapping | Niche effect modeling |
| Best for | Standard deconvolution (all use cases) | State variation within types | Gene imputation, single-cell resolution | Microenvironment biology |
| API stability | Stable | Stable | Stable | Experimental (2025 preprint) |

---

### Summary Decision Table

| Goal | Model | Notes |
|---|---|---|
| Robust cell type proportions with uncertainty | Cell2location | Always the starting point for deconvolution |
| Proportions + intra-type state gradients | DestVI | Requires pretrained scVI on reference |
| Single-cell mapping to spatial coordinates | Tangram | Use `mode="clusters"` first, then `mode="cells"` |
| Gene imputation (unmeasured genes) | Tangram | Requires good marker genes for alignment |
| Niche effect on cell state | scVIVA | No reference needed; API is experimental |

---

*Models are listed in recommended workflow order. For a new spatial transcriptomics project, begin with Cell2location for cell type composition, optionally add DestVI for state resolution, use Tangram for gene imputation, and apply scVIVA to characterize niche biology after establishing proportions.*
