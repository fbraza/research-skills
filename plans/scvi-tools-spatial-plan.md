# Plan: Create `scvi-tools-spatial` Skill

## Context

The existing `scvi-tools-scrna` skill covers scRNA-seq deep generative models (scVI, scANVI, LDVAE, CellAssign, VeloVI). The `spatial-transcriptomics` skill covers Visium preprocessing with Squidpy/Scanpy (QC → normalization → clustering → SVGs → neighborhood enrichment) but explicitly punts deconvolution to "Suggested Next Steps" (line 234: "Cell type deconvolution with cell2location or RCTD").

**Goal:** Create a new `scvi-tools-spatial` skill covering 4 spatial models — Cell2location, DestVI, Tangram, scVIVA — with modular scripts, references, and cross-skill integration. These models answer the deconvolution and niche analysis questions the spatial skill leaves open.

**Why a new skill (not expanding scvi-tools-scrna):** The spatial models have fundamentally different inputs (spatial data + reference), different prerequisites (spatial-transcriptomics skill output), and different workflows. Keeping them separate maintains discoverability and focused scope.

---

## 1. Directory Structure

```
skills/scvi-tools-spatial/
├── SKILL.md
├── references/
│   ├── spatial-model-guide.md          (per-model: purpose, params, API, DOs/DON'Ts)
│   ├── deconvolution-methods.md        (theoretical: what is deconvolution, statistical frameworks)
│   └── troubleshooting-spatial.md      (model-specific issues)
├── scripts/
│   ├── setup_spatial.py                (shared: validation, gene overlap, accelerator)
│   ├── run_cell2location.py            (Cell2location two-stage: reference → spatial)
│   ├── run_destvi.py                   (DestVI from scVI reference)
│   ├── run_tangram.py                  (Tangram mapping + projection + imputation)
│   ├── run_scviva.py                   (scVIVA cell-environment analysis)
│   └── plot_spatial_deconv.py          (spatial proportion maps, validation, summaries)
└── assets/
```

---

## 2. How the 4 Models Fit Together

| Model | Package | Task | Input | Output | Unique Capability |
|-------|---------|------|-------|--------|-------------------|
| **Cell2location** | `cell2location` (separate) | Probabilistic deconvolution | scRNA ref + spatial | Cell type abundances with uncertainty (posteriors) | Most robust; hierarchical Bayesian; gold standard proportions |
| **DestVI** | `scvi.model.DestVI` | Multi-resolution deconvolution | scVI model + spatial | Proportions + continuous within-type variation (γ) | Captures functional states within cell types |
| **Tangram** | `tangram` (separate) | Optimal transport cell mapping | scRNA ref + spatial | Mapping matrix (cells→spots), gene imputation | Maps individual cells; imputes unmeasured genes |
| **scVIVA** | `scvi.external.SCVIVA` | Cell-environment modeling | Spatial data only | Niche-aware embeddings, niche gene programs | Only method modeling how neighborhoods shape cell states |

**When to use which:**
```
START
  │
  ├─ Need reliable cell type proportions? ──────> Cell2location (most robust)
  │
  ├─ Need proportions + within-type states? ────> DestVI (continuous variation)
  │
  ├─ Need single-cell mapping + gene imputation? > Tangram
  │
  └─ Want to study how niches shape cell states? > scVIVA (no reference needed)
```

**Workflow position:** All models come AFTER the spatial-transcriptomics skill's preprocessing (QC → normalization → clustering → spatial neighbors). Cell2location, DestVI, and Tangram also require a preprocessed scRNA-seq reference from the scanpy/seurat skill.

---

## 3. SKILL.md — Content Outline

**File:** `skills/scvi-tools-spatial/SKILL.md`

### Frontmatter
```yaml
id: scvi-tools-spatial
name: Spatial Transcriptomics Deconvolution and Niche Analysis
category: transcriptomics
short-description: "Cell type deconvolution (Cell2location, DestVI, Tangram) and cell-environment modeling (scVIVA) for spatial transcriptomics data."
detailed-description: "Estimate cell type compositions and analyze tissue microenvironments in spatial transcriptomics data. Cell2location provides robust Bayesian deconvolution with uncertainty. DestVI adds continuous within-type state variation. Tangram maps individual cells to spatial locations and imputes genes. scVIVA models how tissue niches shape cell states. Requires preprocessed spatial data from the spatial-transcriptomics skill and (for deconvolution) a labeled scRNA-seq reference. GPU recommended."
starting-prompt: "Deconvolve spatial transcriptomics data to estimate cell type compositions using deep generative models."
```

### Sections
1. **When to Use** — deconvolution, cell mapping, gene imputation, niche analysis
   - **Don't use for:** Spatial QC/preprocessing (→ spatial-transcriptomics), scRNA-seq analysis (→ scvi-tools-scrna)
   - **Prerequisites:** Preprocessed spatial AnnData (from spatial-transcriptomics skill) + preprocessed scRNA-seq reference (from scanpy/seurat skill, for Cell2location/DestVI/Tangram)
2. **Installation** — table: cell2location, scvi-tools ≥1.1, tangram-sc, scanpy, squidpy, torch
3. **Inputs** — spatial AnnData with counts + coords, reference AnnData with counts + labels
4. **Outputs** — proportions, abundances, mapping matrices, niche embeddings, imputed genes
5. **Clarification Questions** — task? spatial data available? reference available? which method?
6. **Standard Workflow** — Step 1 Validate → Step 2a-2d model branches → Step 3 Visualize
7. **Decision Guide** — table: task → model → script
8. **DOs and DON'Ts** (from papers)
9. **Common Issues** — table
10. **Suggested Next Steps** — ligand-receptor, spatial DE, multi-sample
11. **Related Skills**
12. **References** (4 papers + scvi-tools)

---

## 4. Script Specifications

### `scripts/setup_spatial.py` — Shared Utilities

```python
def validate_spatial_anndata(adata_sp, require_counts=True, require_spatial=True) -> bool
    # Check: raw counts, spatial coords in obsm['spatial'], no NaN

def validate_reference_anndata(adata_ref, labels_key, require_counts=True, min_cells_per_type=10) -> bool
    # Check: raw counts, labels exist, sufficient cells per type

def compute_gene_overlap(adata_sp, adata_ref, min_overlap=500) -> list
    # Return shared gene list, warn if <500, raise if <100

def subset_to_shared_genes(adata_sp, adata_ref) -> tuple
    # Return (adata_sp_subset, adata_ref_subset) on shared genes

def detect_accelerator() -> str
    # GPU/MPS/CPU detection (same pattern as setup_scvi.py)

def filter_genes_for_deconvolution(adata_ref, cell_count_cutoff=5, cell_pct_cutoff=0.03, nonz_mean_cutoff=1.12) -> AnnData
    # Permissive gene filtering for Cell2location (retain ~10k-16k genes)
```

### `scripts/run_cell2location.py` — Cell2location

```python
def train_reference_model(adata_ref, labels_key="cell_type", batch_key=None,
                           max_epochs=250, save_model=None) -> tuple
    # Stage 1: cell2location.models.RegressionModel
    # Exports signatures to adata_ref.varm['means_per_cluster_mu_fg']
    # Returns (adata_ref, ref_model)

def train_cell2location(adata_sp, reference_signatures,
                         N_cells_per_location=10, detection_alpha=20,
                         max_epochs=30000, save_model=None) -> tuple
    # Stage 2: cell2location.models.Cell2location
    # Stores q05/q50/q95 abundances in adata_sp.obsm
    # Returns (adata_sp, spatial_model)

def get_cell_type_proportions(adata_sp, quantile="q05") -> pd.DataFrame
    # Convert abundances to proportions
    # Add to adata_sp.obs per-type proportion columns
    # Add adata_sp.obs['dominant_cell_type']
```

**Note:** Cell2location uses `use_gpu=True` (not `accelerator=`). It's a separate package.

### `scripts/run_destvi.py` — DestVI

```python
def train_destvi(adata_sp, scvi_model, cell_type_key="cell_type",
                  max_epochs=2500, save_model=None) -> tuple
    # scvi.model.DestVI.from_rna_model(adata_sp, scvi_model, cell_type_key)
    # Stores proportions in adata_sp.obsm['destvi_proportions']
    # Returns (adata_sp, destvi_model)

def get_cell_type_expression(destvi_model, cell_type, adata_sp) -> pd.DataFrame
    # model.get_scale_for_ct(cell_type)
    # Cell-type-specific gene expression per spot

def get_continuous_variation(destvi_model, adata_sp) -> dict
    # model.get_gamma()
    # Unique DestVI feature: within-type continuous state variation
    # Returns {cell_type: state_values_per_spot}
```

**Prerequisite:** scVI model trained on reference (from scvi-tools-scrna skill).

### `scripts/run_tangram.py` — Tangram

```python
def prepare_tangram_inputs(adata_sc, adata_sp, labels_key="cell_type",
                            n_marker_genes=100) -> tuple
    # Find marker genes via sc.tl.rank_genes_groups
    # Run tg.pp_adatas()
    # Returns (adata_sc, adata_sp, marker_genes)

def map_cells_to_space(adata_sc, adata_sp, mode="clusters",
                        cluster_label="cell_type",
                        density_prior="rna_count_based", device="cpu") -> AnnData
    # tg.map_cells_to_space()
    # Returns ad_map (mapping AnnData)

def project_annotations(ad_map, adata_sp, annotation="cell_type") -> AnnData
    # tg.project_cell_annotations()
    # Stores in adata_sp.obsm['tangram_ct_pred']

def impute_genes(ad_map, adata_sp, genes) -> AnnData
    # tg.project_genes()
    # Impute unmeasured genes in spatial data
```

**Note:** Tangram is deterministic (no uncertainty estimates). Uses separate `tangram-sc` package.

### `scripts/run_scviva.py` — scVIVA

```python
def train_scviva(adata_sp, spatial_key="spatial", layer="counts",
                  n_latent=30, max_epochs=400, save_model=None) -> tuple
    # scvi.external.SCVIVA or scvi.model.SCVIVA (verify version)
    # Stores X_scVIVA in adata_sp.obsm
    # Returns (adata_sp, model)

def get_environment_representation(model, adata_sp) -> np.ndarray
    # Environment-specific latent representations

def get_niche_gene_programs(model, adata_sp) -> pd.DataFrame
    # Niche-associated gene expression programs
```

**Note:** scVIVA is from a 2025 bioRxiv preprint — mark as experimental. Needs version check.

### `scripts/plot_spatial_deconv.py` — Visualization

```python
def plot_cell_type_proportions(adata_sp, proportions_key, cell_types=None,
                                n_cols=3, output_dir="results") -> None
    # Spatial heatmap per cell type. Uses sc.pl.spatial or manual matplotlib.

def plot_dominant_cell_type(adata_sp, output_dir="results") -> None
    # Spatial map colored by highest-proportion cell type per spot.

def plot_proportion_validation(adata_sp, marker_genes_dict, proportions_key,
                                output_dir="results") -> None
    # Scatter: marker expression vs estimated proportion. Pearson r.

def plot_deconvolution_summary(adata_sp, proportions_key, output_dir="results") -> None
    # Stacked bar chart + pie chart of mean proportions.

def plot_training_history_spatial(model, model_name="", output_dir="results") -> None
    # Training curves (adapts to cell2location vs scvi-tools model.history)
```

---

## 5. Reference Files

### `references/spatial-model-guide.md`
Per-model sections (mirroring `model-guide.md` from scvi-tools-scrna):
- For each: Purpose, When to Use, Key Parameters table, API Quick Reference, DOs/DON'Ts, Output Interpretation
- Model selection flowchart
- Comparison table (probabilistic?, uncertainty?, reference needed?, unique capability)
- Source: Adapt from `TO_EVALUATE/scvi/scvi-tools/references/models-spatial.md` + papers

### `references/deconvolution-methods.md`
- What is spatial deconvolution and why it's needed
- Statistical frameworks: NB regression (Cell2location), conditional VAE (DestVI), optimal transport (Tangram), environment-aware VAE (scVIVA)
- Abundance vs. proportion (and why the distinction matters)
- Posterior uncertainty quantification (Cell2location q05/q50/q95)
- Gene overlap requirements and strategies
- Validation approaches (marker correlation, spatial coherence)

### `references/troubleshooting-spatial.md`
- **Cell2location:** Slow training (30k epochs normal on GPU), memory for large refs, N_cells_per_location tuning, gene filtering params
- **DestVI:** Needs scVI first, 2500 epochs standard, registration issues
- **Tangram:** Gene overlap too low, mode="cells" vs "clusters" choice, device selection
- **scVIVA:** API not found (version too old), spatial_key issues
- **General:** Gene name format mismatches (ENSEMBL vs symbol), spatial coords not in obsm

---

## 6. Cross-Skill Modifications

### 6a. `skills/spatial-transcriptomics/SKILL.md`
**Lines 233-234** — Replace:
```
- **Cell type deconvolution** with cell2location or RCTD (specialized workflow)
```
With:
```
- **Cell type deconvolution & niche analysis** → use `scvi-tools-spatial` skill (Cell2location, DestVI, Tangram, scVIVA)
```

**Lines 239-247** (Related Skills table) — Add row:
```
| `scvi-tools-spatial` | Downstream: cell type deconvolution and niche analysis |
```

### 6b. `skills/spatial-transcriptomics/references/spatial-analysis-guide.md`
**Line 178** — Replace:
```
1. **Cell type deconvolution:** Use SVG results + scRNA-seq reference to estimate cell type proportions per spot (cell2location, RCTD, STdeconvolve)
```
With:
```
1. **Cell type deconvolution:** Use `scvi-tools-spatial` skill for probabilistic deconvolution (Cell2location, DestVI) or single-cell mapping (Tangram). Requires scRNA-seq reference.
```

### 6c. `skills/scvi-tools-scrna/SKILL.md`
**"Don't use for" section** — Update spatial line from "future skills" to:
```
- Spatial transcriptomics deconvolution → use `scvi-tools-spatial`
```

**Related Skills section** — Add:
```
**Spatial extension:** `scvi-tools-spatial` (Cell2location, DestVI, Tangram, scVIVA for spatial deconvolution)
```

### 6d. `CLAUDE.md` Skill Dispatch Table
Add row after spatial-transcriptomics:
```
| Spatial deconvolution / cell type mapping | `scvi-tools-spatial` |
```

---

## 7. Implementation Sequence

| Step | Files | Notes |
|------|-------|-------|
| 1 | Create directory structure | `skills/scvi-tools-spatial/{scripts,references,assets}` |
| 2 | `scripts/setup_spatial.py` | No model dependencies, just scanpy/anndata |
| 3 | `scripts/run_cell2location.py` | Separate package, two-stage workflow |
| 4 | `scripts/run_destvi.py` | scvi.model.DestVI, from_rna_model pattern |
| 5 | `scripts/run_tangram.py` | Separate package (tangram-sc), deterministic |
| 6 | `scripts/run_scviva.py` | scvi.external.SCVIVA, experimental |
| 7 | `scripts/plot_spatial_deconv.py` | Shared visualization |
| 8 | `references/spatial-model-guide.md` | Adapt TO_EVALUATE content + papers |
| 9 | `references/deconvolution-methods.md` | New theoretical content |
| 10 | `references/troubleshooting-spatial.md` | New troubleshooting content |
| 11 | `SKILL.md` | After all scripts and references |
| 12 | Cross-skill updates | spatial-transcriptomics, scvi-tools-scrna, CLAUDE.md |

**Parallelizable:** Steps 3-7 (scripts) in parallel. Steps 8-10 (references) in parallel.

---

## 8. Key Sources

| File | Purpose |
|------|---------|
| `TO_EVALUATE/scvi/scvi-tools/references/models-spatial.md` | Starting content for DestVI, Tangram, scVIVA |
| `TO_EVALUATE/spatial/spatial-transcriptomics/spatial-deconvolution/SKILL.md` | Cell2location + Tangram workflow drafts |
| `skills/scvi-tools-scrna/scripts/setup_scvi.py` | Pattern for setup_spatial.py |
| `skills/scvi-tools-scrna/SKILL.md` | Template for SKILL.md structure |
| `skills/scvi-tools-scrna/references/model-guide.md` | Template for spatial-model-guide.md |
| `skills/spatial-transcriptomics/SKILL.md` | Cross-reference target |

---

## 9. Verification Plan

1. **Syntax check:** All 6 Python scripts pass `py_compile`
2. **SKILL.md structure:** Frontmatter, all required sections, script enforcement
3. **Link verification:** All file references in SKILL.md resolve
4. **API checks:** Cell2location uses separate package API, DestVI uses `scvi.model.DestVI`, Tangram uses `tangram` package, scVIVA uses `scvi.external.SCVIVA`
5. **Cross-references:** spatial-transcriptomics, scvi-tools-scrna, and CLAUDE.md all updated
6. **Integration test:** Cell2location or DestVI with example data (if packages installed)
