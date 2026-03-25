---
id: scvi-tools-spatial
name: Spatial Transcriptomics Deconvolution and Niche Analysis
category: transcriptomics
short-description: "Cell type deconvolution (Cell2location, DestVI, Tangram) and cell-environment modeling (scVIVA) for spatial transcriptomics data using deep generative models."
detailed-description: "Estimate cell type compositions and analyze tissue microenvironments in spatial transcriptomics data. Cell2location provides robust Bayesian deconvolution with full posterior uncertainty. DestVI adds continuous within-type state variation for multi-resolution analysis. Tangram maps individual single cells to spatial coordinates and imputes unmeasured genes. scVIVA models how tissue niches shape cell states. Requires preprocessed spatial data from the spatial-transcriptomics skill and (for deconvolution) a labeled scRNA-seq reference from the scanpy or seurat skill. GPU recommended for Cell2location and DestVI."
starting-prompt: "Deconvolve spatial transcriptomics data to estimate cell type compositions using deep generative models."
---

# Spatial Transcriptomics Deconvolution and Niche Analysis

Estimate cell type compositions, map individual cells to spatial locations, impute unmeasured genes, and analyze how tissue microenvironments shape cell states. This skill covers four deep generative models that address the downstream analytical questions left open by the `spatial-transcriptomics` skill.

## When to Use This Skill

- **Cell type deconvolution** — estimate which cell types are present at each spatial spot (Cell2location, DestVI)
- **Single-cell spatial mapping** — map individual cells from scRNA-seq onto spatial coordinates (Tangram)
- **Gene imputation** — predict expression of genes not measured in spatial data (Tangram)
- **Within-type state variation** — capture continuous functional gradients within cell types across tissue (DestVI)
- **Niche/microenvironment analysis** — study how spatial context shapes cell states (scVIVA)

**Don't use for:**
- Spatial QC, preprocessing, clustering, or SVG detection → use `spatial-transcriptomics`
- scRNA-seq preprocessing → use `scrnaseq-scanpy-core-analysis` or `scrnaseq-seurat-core-analysis`
- Non-spatial scVI/scANVI analysis → use `scvi-tools-scrna`

**Prerequisites:**
- **Spatial data:** Preprocessed AnnData from the `spatial-transcriptomics` skill with raw counts in `adata.layers['counts']` or `adata.X` and spatial coordinates in `adata.obsm['spatial']`
- **Reference data (Cell2location, DestVI, Tangram):** Preprocessed scRNA-seq AnnData with raw counts and cell type labels from the `scrnaseq-scanpy-core-analysis` or `scrnaseq-seurat-core-analysis` skill
- **No reference needed:** scVIVA works on spatial data alone

## Installation

| Package | Version | License | Commercial Use | Installation |
|---------|---------|---------|----------------|--------------|
| cell2location | ≥0.1 | Apache-2.0 | Permitted | `pip install cell2location` |
| scvi-tools | ≥1.1 | BSD-3-Clause | Permitted | `pip install scvi-tools` |
| tangram-sc | ≥1.0 | BSD-3-Clause | Permitted | `pip install tangram-sc` |
| scanpy | ≥1.9 | BSD-3-Clause | Permitted | `pip install scanpy` |
| squidpy | ≥1.4 | BSD-3-Clause | Permitted | `pip install squidpy` |
| torch | ≥2.0 | BSD-3-Clause | Permitted | `pip install torch` |
| matplotlib | ≥3.4 | PSF | Permitted | `pip install matplotlib` |
| seaborn | ≥0.12 | BSD-3-Clause | Permitted | `pip install seaborn` |

**Install all:** `pip install cell2location scvi-tools tangram-sc scanpy squidpy torch matplotlib seaborn`

**GPU support:** `pip install cell2location scvi-tools[cuda12]`

## Inputs

**Required for all methods:**
- **Spatial AnnData** (.h5ad) with:
  - Raw counts in `adata.layers['counts']` or `adata.X`
  - Spatial coordinates in `adata.obsm['spatial']` (n_spots x 2 array)

**Required for Cell2location, DestVI, Tangram (deconvolution/mapping):**
- **Reference scRNA-seq AnnData** (.h5ad) with:
  - Raw counts in `adata.layers['counts']` or `adata.X`
  - Cell type labels in `adata.obs` (e.g., `cell_type` column)
  - Sufficient gene overlap with spatial data (≥500 shared genes recommended)

**Not required for scVIVA** (works on spatial data alone)

## Outputs

**Cell type compositions (Cell2location, DestVI, Tangram):**
- `adata_sp.obsm['cell_type_proportions']` — proportions per spot (n_spots x n_types)
- `adata_sp.obs['dominant_cell_type']` — highest-proportion type per spot
- Per-type proportion columns in `adata_sp.obs` (e.g., `prop_T_cells`)

**Cell2location-specific:**
- `adata_sp.obsm['q05_cell_abundance_w_sf']` — conservative abundance estimates (5th percentile)
- `adata_sp.obsm['q50_cell_abundance_w_sf']` — median abundance estimates
- `adata_sp.obsm['q95_cell_abundance_w_sf']` — upper bound abundance estimates
- Reference signatures in `adata_ref.varm['means_per_cluster_mu_fg']`

**DestVI-specific:**
- `adata_sp.obsm['destvi_proportions']` — cell type proportions
- Cell-type-specific gene expression per spot (via `get_scale_for_ct()`)
- Continuous state variation per type per spot (via `get_gamma()` — unique to DestVI)

**Tangram-specific:**
- Mapping matrix `ad_map.X` (cells x spots)
- `adata_sp.obsm['tangram_ct_pred']` — projected cell type annotations
- Imputed gene expression for unmeasured genes

**scVIVA-specific:**
- `adata_sp.obsm['X_scVIVA']` — niche-aware cell embeddings
- Niche-specific gene programs

**Visualization outputs:** Spatial proportion heatmaps, dominant type maps, validation scatter plots, training curves (PNG + SVG at 300 DPI)

## Clarification Questions

**Default settings (use unless user specifies otherwise):**
- Method: Cell2location | N_cells_per_location: 10 | detection_alpha: 20

### 1. **Task** (ASK THIS FIRST):
   - What do you need? Cell type proportions / Single-cell mapping / Gene imputation / Niche analysis
   - Multiple tasks can be combined (e.g., Cell2location for proportions + scVIVA for niche analysis)

### 2. **Data available?**
   - Do you have preprocessed spatial AnnData with raw counts and spatial coordinates?
   - Do you have a preprocessed scRNA-seq reference with cell type labels? (not needed for scVIVA)
   - If not → run `spatial-transcriptomics` and/or `scrnaseq-scanpy-core-analysis` first

### 3. **Spatial technology:**
   - Visium (10x)? MERFISH? Slide-seq? STARmap?
   - How many spots/cells? How many genes measured?

### 4. **Reference quality:**
   - How many cell types in the reference? How many cells per type?
   - Same tissue as spatial data?

### 5. **What distinguishes the analysis?**
   - Need uncertainty estimates? → Cell2location (Bayesian posteriors)
   - Expect within-type functional gradients? → DestVI (continuous γ)
   - Need to impute unmeasured genes? → Tangram
   - Study how microenvironment shapes cells? → scVIVA

### 6. **Hardware:**
   - GPU available? (Required for Cell2location; recommended for DestVI/scVIVA)

## Standard Workflow

**MANDATORY: USE SCRIPTS EXACTLY AS SHOWN — DO NOT WRITE INLINE CODE**

**Detailed model comparison:** [references/spatial-model-guide.md](references/spatial-model-guide.md)

**CRITICAL — DO NOT:**
- Write inline deconvolution code → **STOP: Use the script functions**
- Pass normalized data → **STOP: All models require raw counts**
- Skip gene overlap validation → **STOP: Always check shared genes first**

**IF SCRIPTS FAIL — Script Failure Hierarchy:**
1. **Fix and Retry (90%)** — Install missing package, re-run script
2. **Modify Script (5%)** — Edit the script file itself, document changes
3. **Use as Reference (4%)** — Read script, adapt approach, cite source
4. **Write from Scratch (1%)** — Only if genuinely impossible, explain why

---

**Step 1 — Validate & Setup** | [scripts/setup_spatial.py](scripts/setup_spatial.py)

```python
from setup_spatial import validate_spatial_anndata, validate_reference_anndata, compute_gene_overlap, subset_to_shared_genes

# Validate spatial data
validate_spatial_anndata(adata_sp, require_counts=True, require_spatial=True)

# Validate reference (skip for scVIVA)
validate_reference_anndata(adata_ref, labels_key="cell_type", min_cells_per_type=10)

# Check gene overlap
shared_genes = compute_gene_overlap(adata_sp, adata_ref, min_overlap=500)

# Subset to shared genes
adata_sp_sub, adata_ref_sub = subset_to_shared_genes(adata_sp, adata_ref)
```

**VERIFICATION:** `"✓ Validation passed"` with gene overlap summary.

---

**Step 2a — Cell2location (Bayesian Deconvolution)** [OPTION A] | [scripts/run_cell2location.py](scripts/run_cell2location.py)

```python
from run_cell2location import train_reference_model, train_cell2location, get_cell_type_proportions

# Stage 1: Train reference signatures (NB regression, ~10 min GPU)
adata_ref, ref_model = train_reference_model(
    adata_ref, labels_key="cell_type", max_epochs=250
)

# Stage 2: Spatial deconvolution (hierarchical Bayesian, ~2-6 hours GPU)
adata_sp, spatial_model = train_cell2location(
    adata_sp,
    reference_signatures=adata_ref.varm['means_per_cluster_mu_fg'],
    N_cells_per_location=10,
    max_epochs=30000
)

# Extract proportions (using conservative q05 quantile)
proportions = get_cell_type_proportions(adata_sp, quantile="q05")
```

**VERIFICATION:** Training converged, proportions sum to ~1 per spot, dominant cell types match known tissue architecture.

**Note:** Cell2location training is SLOW (30,000 epochs). GPU required for practical runtimes. This is normal.

---

**Step 2b — DestVI (Multi-Resolution Deconvolution)** [OPTION B] | [scripts/run_destvi.py](scripts/run_destvi.py)

```python
from run_destvi import train_destvi, get_cell_type_expression, get_continuous_variation

# PREREQUISITE: Train scVI on reference first (use scvi-tools-scrna skill)
# from run_scvi import train_scvi
# adata_ref, scvi_model = train_scvi(adata_ref, batch_key="batch", n_latent=30)

# Train DestVI from scVI reference model (~30 min GPU)
adata_sp, destvi_model = train_destvi(
    adata_sp, scvi_model, cell_type_key="cell_type", max_epochs=2500
)

# Get cell-type-specific expression at each spot
tcell_expr = get_cell_type_expression(destvi_model, "T_cells", adata_sp)

# Get continuous within-type variation (DestVI's unique feature)
gamma = get_continuous_variation(destvi_model, adata_sp)
```

**VERIFICATION:** Proportions extracted, gamma captures meaningful variation (not constant).

**Note:** DestVI requires a pretrained scVI model on the reference. Use the `scvi-tools-scrna` skill to train scVI first.

---

**Step 2c — Tangram (Single-Cell Mapping + Gene Imputation)** [OPTION C] | [scripts/run_tangram.py](scripts/run_tangram.py)

```python
from run_tangram import prepare_tangram_inputs, map_cells_to_space, project_annotations, impute_genes

# Prepare inputs with marker genes
adata_sc, adata_sp, markers = prepare_tangram_inputs(
    adata_sc, adata_sp, labels_key="cell_type", n_marker_genes=100
)

# Map cells to spatial locations
ad_map = map_cells_to_space(adata_sc, adata_sp, mode="clusters")

# Project cell type annotations
adata_sp = project_annotations(ad_map, adata_sp, annotation="cell_type")

# Impute unmeasured genes
adata_sp = impute_genes(ad_map, adata_sp, genes=["CD3D", "CD8A", "FOXP3"])
```

**VERIFICATION:** Projected annotations match expected tissue architecture, imputed genes correlate with known markers.

**Note:** Tangram is deterministic — no uncertainty estimates. Run multiple times and check consistency.

---

**Step 2d — scVIVA (Niche/Environment Analysis)** [OPTION D, EXPERIMENTAL] | [scripts/run_scviva.py](scripts/run_scviva.py)

```python
from run_scviva import train_scviva, get_environment_representation

# Train scVIVA (no reference needed — spatial data only)
adata_sp, scviva_model = train_scviva(adata_sp, spatial_key="spatial", n_latent=30)

# Get niche-aware embeddings
env_latent = get_environment_representation(scviva_model, adata_sp)
```

**VERIFICATION:** Latent embeddings stored, UMAP shows spatial structure.

**Note:** scVIVA is from a 2025 bioRxiv preprint — API may change. Mark results as preliminary.

---

**Step 3 — Visualize & Validate** | [scripts/plot_spatial_deconv.py](scripts/plot_spatial_deconv.py)

```python
from plot_spatial_deconv import plot_cell_type_proportions, plot_dominant_cell_type, plot_proportion_validation

# Spatial heatmaps per cell type
plot_cell_type_proportions(adata_sp, output_dir="results")

# Dominant cell type map
plot_dominant_cell_type(adata_sp, output_dir="results")

# Validate with known marker genes
plot_proportion_validation(adata_sp, marker_genes_dict={
    "T_cells": ["CD3D", "CD3E"],
    "B_cells": ["CD19", "MS4A1"],
    "Macrophages": ["CD68", "CD163"]
}, output_dir="results")
```

## Decision Guide

| Task | Model | When to Use | Key Parameter | Training Time |
|------|-------|-------------|---------------|---------------|
| Robust cell type proportions | Cell2location | Best quality, need uncertainty | `N_cells_per_location=10` | Hours (GPU) |
| Proportions + within-type states | DestVI | Functional gradients matter | `cell_type_key, max_epochs=2500` | ~30 min (GPU) |
| Single-cell mapping + imputation | Tangram | Need cell positions or imputed genes | `mode="clusters", n_marker_genes=100` | Minutes |
| Niche/environment analysis | scVIVA | How space shapes cell states | `spatial_key, n_latent=30` | ~30 min (GPU) |

**Detailed model comparison:** [references/spatial-model-guide.md](references/spatial-model-guide.md)

## Important DOs and DON'Ts

### DO
- Always use **raw counts** (not normalized) for all models
- Validate **gene overlap** between reference and spatial data (≥500 shared genes)
- Use **permissive gene filtering** for Cell2location (~10k-16k genes retained)
- **Validate results** against known marker genes and tissue architecture
- Train **scVI on reference first** before running DestVI (three-skill chain)
- Use **q05 quantile** (5th percentile) from Cell2location for conservative estimates
- Run Tangram **multiple times** and check consistency
- Use **GPU** for Cell2location (CPU is impractically slow)
- **Save trained models** for reproducibility
- **Compare methods** when feasible — Cell2location + DestVI give complementary views

### DON'T
- Don't pass **normalized or log-transformed** data to any model
- Don't skip **gene overlap validation** — insufficient overlap silently degrades results
- Don't use **restrictive gene filtering** for Cell2location (reduces robustness)
- Don't expect Cell2location to train in **minutes** — 30k epochs is normal
- Don't treat Tangram results as **probabilistic** — it has no uncertainty estimates
- Don't use scVIVA for **primary deconvolution** — it models niche effects, not proportions
- Don't ignore **reference quality** — poor cell type annotations propagate to deconvolution
- Don't assume DestVI's **gamma is interpretable** without validation against known biology
- Don't forget that Cell2location outputs **abundances** (cell counts), not proportions — normalize first

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `ImportError: cell2location` | Package not installed | `pip install cell2location` |
| `ImportError: tangram` | Package not installed | `pip install tangram-sc` |
| Gene overlap < 100 | Gene name format mismatch | Convert ENSEMBL ↔ symbols to match |
| Cell2location very slow | Expected — 30k epochs | Use GPU; training takes 2-6 hours |
| GPU out of memory | Large reference or spatial data | Reduce batch_size, subsample reference |
| All spots same proportions | Gene filtering too restrictive | Use permissive Cell2location defaults |
| DestVI requires scVI model | Missing prerequisite | Train scVI on reference first (scvi-tools-scrna skill) |
| Tangram poor mapping | Bad marker gene selection | Use more discriminative markers, try different n_marker_genes |
| scVIVA ImportError | scvi-tools version too old | `pip install scvi-tools --upgrade` |
| Spatial coords not found | obsm['spatial'] missing | Check AnnData was loaded with spatial info preserved |
| Proportions don't sum to 1 | Using abundances, not proportions | Normalize: `proportions / proportions.sum(axis=1, keepdims=True)` |

**Detailed troubleshooting:** [references/troubleshooting-spatial.md](references/troubleshooting-spatial.md)

## Suggested Next Steps

1. **Ligand-receptor analysis** — Use deconvolution results with `cell-cell-communication` skill (CellPhoneDB, COMMOT)
2. **Spatial differential expression** — Compare gene expression across tissue regions or conditions
3. **Multi-sample integration** — Integrate multiple spatial sections with batch correction
4. **Functional enrichment** — `functional-enrichment-from-degs` on spatially variable or niche-specific genes
5. **Trajectory inference** — Combine with `scrna-trajectory-inference` for spatial dynamics

## Related Skills

**Prerequisites:**
- `spatial-transcriptomics` — spatial data preprocessing (QC → clustering → SVGs)
- `scrnaseq-scanpy-core-analysis` or `scrnaseq-seurat-core-analysis` — reference scRNA-seq preprocessing

**DestVI prerequisite:** `scvi-tools-scrna` — train scVI model on reference before DestVI

**Downstream:** `functional-enrichment-from-degs`, `cell-cell-communication`, `scrna-trajectory-inference`

**Complementary:** `scvi-tools-scrna` (scRNA-seq deep generative models)

## References

1. **Cell2location:** Kleshchevnikov V, Shmatko A, Dann E, et al. (2022) Cell2location maps fine-grained cell types in spatial transcriptomics. *Nat Biotechnol*. 40:209-216.
2. **DestVI:** Lopez R, Li B, Keren-Shaul H, et al. (2022) DestVI identifies continuums of cell types in spatial transcriptomics data. *Nat Biotechnol*. 40:685-691.
3. **Tangram:** Biancalani T, Scalia G, Buffoni L, et al. (2021) Deep learning and alignment of spatially resolved single-cell transcriptomes with Tangram. *Nat Methods*. 18:1352-1362.
4. **scVIVA:** Levy N, Ingelfinger F, Bakulin A, et al. (2025) scVIVA: a probabilistic framework for representation of cells and their environments in spatial transcriptomics. *bioRxiv*. 2025.06.01.657182.
5. **scvi-tools:** Gayoso A, Lopez R, Xing G, et al. (2022) A Python library for probabilistic analysis of single-cell omics data. *Nat Biotechnol*. 40:163-166.

**Detailed guides:** [spatial-model-guide.md](references/spatial-model-guide.md) | [deconvolution-methods.md](references/deconvolution-methods.md) | [troubleshooting-spatial.md](references/troubleshooting-spatial.md)

**Scripts:** [scripts/](scripts/)
