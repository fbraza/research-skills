---
name: scvi-tools-scrna
description: Advanced single-cell RNA-seq modeling using scvi-tools deep generative models. Use after preprocessing with the Scanpy or Seurat skill. scVI provides probabilistic batch correction, normalized expression, and Bayesian DE. scANVI extends scVI with semi-supervised label transfer from partial annotations. LDVAE extracts interpretable gene programs via linear decoder. CellAssign performs probabilistic cell type assignment using marker gene panels. VeloVI adds RNA velocity with uncertainty quantification. All models use raw counts, produce latent representations in AnnData, and integrate with downstream Scanpy workflows. GPU recommended for datasets >10k cells.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
starting-prompt: "Apply deep generative modeling to preprocessed single-cell RNA-seq data using scvi-tools."
---

# scVI-tools for Single-Cell RNA-seq

Advanced deep generative modeling for single-cell RNA-seq using scvi-tools. This skill covers five models that address distinct analytical tasks beyond standard preprocessing: probabilistic batch integration, semi-supervised label transfer, interpretable gene programs, marker-based annotation, and RNA velocity with uncertainty.

## When to Use This Skill

- **Batch integration** with probabilistic modeling that accounts for count data distributions (scVI)
- **Semi-supervised label transfer** from reference annotations or partial labels (scANVI)
- **Interpretable gene program discovery** via linear decoder — know which genes drive each axis of variation (LDVAE)
- **Marker-based cell type annotation** when you have marker panels but no reference dataset (CellAssign)
- **RNA velocity with uncertainty quantification** — assess whether velocity analysis is even appropriate for your dataset (VeloVI)
- **Bayesian differential expression** with effect size thresholds and uncertainty estimates

**Don't use for:**
- Standard preprocessing/QC → use `scrnaseq-scanpy-core-analysis`
- R-based single-cell workflows → use `scrnaseq-seurat-core-analysis`
- Basic scVI integration within a standard pipeline → already covered by the Scanpy skill's `integrate_scvi.py`
- ATAC-seq or multimodal → future skills
- Spatial transcriptomics deconvolution → use `scvi-tools-spatial`

**Prerequisite:** Preprocessed AnnData from the Scanpy or Seurat skill with **raw counts preserved** in `adata.layers['counts']` or `adata.X`.

## Installation

| Package | Version | License | Commercial Use | Installation |
|---------|---------|---------|----------------|--------------|
| scvi-tools | ≥1.1 | BSD-3-Clause | Permitted | `pip install scvi-tools` |
| scanpy | ≥1.9 | BSD-3-Clause | Permitted | `pip install scanpy` |
| anndata | ≥0.8 | BSD-3-Clause | Permitted | `pip install anndata` |
| torch | ≥2.0 | BSD-3-Clause | Permitted | `pip install torch` |
| scvelo | ≥0.2.5 | BSD-3-Clause | Permitted | `pip install scvelo` (VeloVI only) |
| matplotlib | ≥3.4 | PSF | Permitted | `pip install matplotlib` |
| seaborn | ≥0.12 | BSD-3-Clause | Permitted | `pip install seaborn` |

**Install all:** `pip install scvi-tools scanpy anndata torch matplotlib seaborn`

**GPU support:** `pip install scvi-tools[cuda12]`

**Minimum versions:** Python ≥3.11 (required by scvi-tools ≥1.4), recommended Python 3.12, torch ≥2.0

## Inputs

**Required:**
- **Preprocessed AnnData** (.h5ad) with:
  - Raw counts in `adata.layers['counts']` or `adata.X` (integer or near-integer values)
  - Highly variable genes marked in `adata.var['highly_variable']` (1000-4000 recommended)
  - Batch key in `adata.obs` (for integration tasks)

**Model-specific inputs:**
- **(scANVI)** Partial cell type labels in `adata.obs` — unlabeled cells marked with a string category (e.g., "Unknown")
- **(CellAssign)** Binary marker gene matrix as pandas DataFrame (index=gene_names, columns=cell_types, values=0/1)
- **(VeloVI)** Spliced/unspliced count layers from scVelo preprocessing (`Ms`, `Mu` layers in AnnData)

## Outputs

**Latent representations (stored in adata.obsm):**
- `X_scVI` — batch-corrected latent space (scVI)
- `X_scANVI` — cell-type-aware latent space (scANVI)
- `X_LDVAE` — interpretable latent factors (LDVAE)

**Expression layers (stored in adata.layers):**
- `scvi_normalized` — denoised, normalized expression from scVI

**Predictions (stored in adata.obs):**
- `scanvi_predictions` — predicted cell types from scANVI
- `cellassign_predictions` — marker-based cell type assignments
- `velovi_latent_time` — inferred latent time per cell

**Additional outputs:**
- LDVAE gene loadings matrix (CSV) — genes × factors with loading weights
- DE results DataFrame (CSV) — lfc_mean, lfc_std, bayes_factor, is_de_fdr columns
- VeloVI velocity vectors (`adata.layers['velocity']`), permutation scores
- Training diagnostic plots (PNG + SVG at 300 DPI)
- Saved model directories (for persistence, transfer learning, reproducibility)

**Reports:**
- `scrna_analysis_report.pdf` - Agent-generated comprehensive PDF with Methods, Results, Figures, Conclusions

**PDF style rules:**
- **US Letter page size (8.5 x 11 in)** — always set page dimensions explicitly
- **No Unicode superscripts** — use `3.36e-06` or `3.36 x 10^(-6)`, not Unicode superscript chars
- **No half-empty pages** — group headings with their content
- **Figures ≥80% page width** — multi-panel figures must be large enough to read

## Clarification Questions

**Default settings (use unless user specifies otherwise):**
- Task: scVI batch integration | n_latent: 30 | gene_likelihood: nb | max_epochs: 400

### 1. **Task** (ASK THIS FIRST):
   - What do you need? Integration / Label transfer / Gene programs / Marker annotation / Velocity / DE
   - Multiple tasks can be chained (e.g., scVI → scANVI → DE)

### 2. **Preprocessed data available?**
   - Do you have a preprocessed AnnData (.h5ad) with raw counts preserved?
   - If not → run `scrnaseq-scanpy-core-analysis` first

### 3. **Batch structure:**
   - How many batches/samples? What is the batch key column name?
   - Is condition confounded with batch? (e.g., one sample per condition)

### 4. **(scANVI) Label information:**
   - What fraction of cells are labeled? Which column contains labels?
   - What string marks unlabeled cells? (default: "Unknown")

### 5. **(CellAssign) Marker genes:**
   - Do you have a marker gene matrix? Or need help constructing one from literature?
   - How many cell types? How many markers per type?

### 6. **(VeloVI) Velocity data:**
   - Has scVelo preprocessing been run (spliced/unspliced moments computed)?
   - Is this a developmental/differentiation dataset with expected transient dynamics?

### 7. **Hardware:**
   - GPU available? (Recommended for >10k cells; required for >100k)

## Standard Workflow

**MANDATORY: USE SCRIPTS EXACTLY AS SHOWN — DO NOT WRITE INLINE CODE**

**Detailed model guide:** [references/model-guide.md](references/model-guide.md)

**CRITICAL — DO NOT:**
- Write inline analysis code → **STOP: Use the script functions**
- Pass log-normalized or scaled data → **STOP: All models require raw counts**
- Skip convergence checks → **STOP: Always verify ELBO curves**

**IF SCRIPTS FAIL — Script Failure Hierarchy:**
1. **Fix and Retry (90%)** — Install missing package, re-run script
2. **Modify Script (5%)** — Edit the script file itself, document changes
3. **Use as Reference (4%)** — Read script, adapt approach, cite source
4. **Write from Scratch (1%)** — Only if genuinely impossible, explain why

**NEVER skip directly to writing inline code without trying the script first.**

---

**Step 1 — Validate & Setup** | [scripts/setup_scvi.py](scripts/setup_scvi.py)

```python
from setup_scvi import validate_anndata_for_scvi, register_anndata_scvi

# Validate input data
validate_anndata_for_scvi(adata, require_counts=True, require_hvg=True, batch_key="batch")

# Register data with scvi-tools
adata = register_anndata_scvi(adata, batch_key="batch", layer="counts")
```

**DO NOT write inline validation code.** The validation function checks: raw counts present, no NaN/negatives, HVGs marked, batch key valid.

**VERIFICATION:** `"✓ Input validated"` message with diagnostic summary.

---

**Step 2 — Train scVI (Foundation Model)** | [scripts/run_scvi.py](scripts/run_scvi.py)

```python
from run_scvi import train_scvi, get_scvi_normalized_expression

# Train scVI model (always run first for multi-batch data)
adata, scvi_model = train_scvi(
    adata, batch_key="batch", n_latent=30,
    save_model="results/scvi_model"
)

# Optional: get denoised normalized expression
adata = get_scvi_normalized_expression(scvi_model, adata)
```

**DO NOT write inline scVI training code.** The script handles GPU detection, convergence checking, and metadata storage automatically.

**VERIFICATION:**
- Training curves plotted (ELBO converging)
- `"✓ scVI training complete"` with final loss and convergence status
- `X_scVI` shape printed (n_cells × n_latent)

**After scVI, branch to the task you need:**

---

**Step 3a — Label Transfer (scANVI)** [OPTIONAL] | [scripts/run_scanvi.py](scripts/run_scanvi.py)

```python
from run_scanvi import train_scanvi_from_scvi, predict_cell_types, evaluate_predictions

# Initialize scANVI from pretrained scVI (recommended)
adata, scanvi_model = train_scanvi_from_scvi(
    scvi_model, adata,
    labels_key="cell_type",
    unlabeled_category="Unknown",
    save_model="results/scanvi_model"
)

# Get predictions with confidence scores
predictions = predict_cell_types(scanvi_model, adata)

# Evaluate on labeled cells
metrics = evaluate_predictions(adata, labels_key="cell_type")
```

**VERIFICATION:** Prediction accuracy on labeled cells printed, confidence distribution shown.

---

**Step 3b — Gene Programs (LDVAE)** [OPTIONAL] | [scripts/run_ldvae.py](scripts/run_ldvae.py)

```python
from run_ldvae import train_ldvae, get_gene_loadings, identify_gene_programs, plot_loadings_heatmap

# Train LDVAE with fewer latent dims (each must be interpretable)
adata, ldvae_model = train_ldvae(adata, n_latent=10)

# Extract and analyze gene loadings
loadings = get_gene_loadings(ldvae_model)
programs = identify_gene_programs(loadings, n_top_genes=50)
plot_loadings_heatmap(loadings, n_top=20, output_dir="results")
```

**VERIFICATION:** Loadings matrix shape printed, top genes per factor listed.

---

**Step 3c — Marker Annotation (CellAssign)** [OPTIONAL] | [scripts/run_cellassign.py](scripts/run_cellassign.py)

```python
from run_cellassign import create_marker_matrix, train_cellassign, summarize_assignments

# Build marker matrix from known markers
marker_mat = create_marker_matrix({
    "T cells": ["CD3D", "CD3E", "CD2"],
    "B cells": ["CD19", "MS4A1", "CD79A"],
    "Monocytes": ["CD14", "LYZ", "S100A8"],
    # ... add more types and markers
})

# Train CellAssign
adata, ca_model = train_cellassign(adata, marker_mat, save_model="results/cellassign_model")

# Review assignments
summary = summarize_assignments(adata)
```

**VERIFICATION:** Assignment proportions printed, low-confidence types flagged.

---

**Step 3d — RNA Velocity (VeloVI)** [OPTIONAL] | [scripts/run_velovi.py](scripts/run_velovi.py)

```python
from run_velovi import validate_velocity_data, preprocess_for_velovi, train_velovi, compute_permutation_scores

# Validate or preprocess velocity data
if not validate_velocity_data(adata):
    adata = preprocess_for_velovi(adata, n_top_genes=2000)

# Train VeloVI
adata, velo_model = train_velovi(adata, save_model="results/velovi_model")

# CRITICAL: Check dataset suitability
perm_scores = compute_permutation_scores(velo_model, adata)
```

**VERIFICATION:** Permutation scores printed — if low, velocity analysis may not be appropriate for this dataset.

---

**Step 4 — Bayesian Differential Expression** [OPTIONAL] | [scripts/run_scvi_de.py](scripts/run_scvi_de.py)

```python
from run_scvi_de import run_bayesian_de, filter_de_results, plot_volcano

# Run Bayesian DE with effect size threshold
de_results = run_bayesian_de(
    scvi_model, adata,
    groupby="cell_type", group1="TypeA", group2="TypeB",
    mode="change", delta=0.25, fdr_target=0.05
)

# Filter and visualize
up, down = filter_de_results(de_results)
plot_volcano(de_results, output_dir="results")

# Save results
de_results.to_csv("results/de_results.csv")
```

**DO NOT use "vanilla" mode without a delta threshold** — it finds trivially small effects. Always use `mode="change"` with a biologically meaningful `delta`.

**VERIFICATION:** DE gene counts printed, volcano plot saved.

**Important:** This is cell-level Bayesian DE — good for marker discovery and cell type characterization. For formal condition comparisons with biological replicates, use pseudobulk DE (DESeq2) from the Scanpy skill's `pseudobulk_de.py`. See [references/differential-expression.md](references/differential-expression.md) for detailed comparison.

---

**Step 5 — Diagnostics & Visualization** | [scripts/plot_scvi_diagnostics.py](scripts/plot_scvi_diagnostics.py)

```python
from plot_scvi_diagnostics import plot_training_history, plot_latent_umap, plot_batch_mixing

# Training convergence
plot_training_history(scvi_model, output_dir="results")

# Latent space visualization
plot_latent_umap(adata, color_keys=["batch", "cell_type"], rep_key="X_scVI", output_dir="results")

# Batch mixing assessment
plot_batch_mixing(adata, batch_key="batch", rep_key="X_scVI", output_dir="results")
```

## Decision Guide

| Task | Model | When to Use | Key Parameter | Script |
|------|-------|-------------|---------------|--------|
| Batch integration | scVI | Always run first for multi-batch data | `n_latent=30, batch_key` | `run_scvi.py` |
| Label transfer | scANVI | Have partial annotations or reference labels | `labels_key, unlabeled_category` | `run_scanvi.py` |
| Gene programs | LDVAE | Need interpretable factors (which genes drive which axis) | `n_latent=10-20` | `run_ldvae.py` |
| Marker annotation | CellAssign | Have marker panels, no reference dataset | `marker_gene_mat` | `run_cellassign.py` |
| RNA velocity | VeloVI | Have spliced/unspliced counts, developmental data | `spliced_layer, unspliced_layer` | `run_velovi.py` |
| Differential expression | scVI/scANVI | Compare conditions or cell types probabilistically | `mode="change", delta=0.25` | `run_scvi_de.py` |

**Detailed model comparison and selection flowchart:** [references/model-guide.md](references/model-guide.md)

## Important DOs and DON'Ts

### DO
- Always use **raw counts** (not log-transformed or normalized) for all scvi-tools models
- Filter to **highly variable genes** (1000-4000) before training
- **Register batch/technical covariates** in `setup_anndata()`
- **Initialize scANVI from a pre-trained scVI** model (better convergence, faster training)
- **Check training convergence** via ELBO curves before using results
- Use `mode="change"` with a **biologically meaningful delta** for DE
- **Run permutation scores** before interpreting VeloVI velocity results
- **Save trained models** for reproducibility and transfer learning
- **Set random seeds** for all stochastic methods

### DON'T
- Don't pass **log-normalized or scaled** data to any scvi-tools model
- Don't treat scVI **latent dimensions as interpretable** (use LDVAE for that)
- Don't expect scANVI to **discover novel cell types** absent from training labels
- Don't use CellAssign without **validating that marker genes exist** in your dataset
- Don't trust VeloVI results on datasets with **low permutation scores** (no transient dynamics)
- Don't use **"vanilla" mode DE** without a delta threshold (finds trivially small effects)
- Don't apply **double normalization** (scvi-tools normalizes internally)
- Don't ignore **batch-condition confounding** warnings

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| NaN loss during training | Zero-variance genes, extreme outliers | Filter genes with `min_counts=3`, check for NaN/Inf in data |
| ELBO not converging | Insufficient epochs or data registration issue | Increase `max_epochs`, verify `setup_anndata` was called |
| GPU out of memory | Dataset too large for VRAM | Reduce `batch_size`, use fewer HVGs, or use CPU |
| Batch overcorrection | Too many covariates or confounded design | Reduce covariates, check batch-condition confounding |
| scANVI low accuracy | Poor seed labels or too few labeled cells | Verify label quality, ensure ≥5% cells labeled |
| CellAssign all one type | Marker genes not expressed or wrong matrix orientation | Validate markers with `validate_marker_matrix()`, check genes×types |
| VeloVI low permutation scores | Dataset has no transient dynamics | Velocity analysis may not be appropriate; use other trajectory methods |
| LDVAE loadings uninterpretable | Too many/few latent dims | Try `n_latent` in 5-20 range, check variance per factor |
| `accelerator` parameter error | Old scvi-tools version | Upgrade to scvi-tools ≥1.1 |
| `ImportError: No module named 'scvi'` | Not installed | `pip install scvi-tools` |

**Expected warnings (not errors):**

| Warning | Meaning | Action |
|---------|---------|--------|
| SVG export failed | Optional SVG dependency unavailable | Normal — PNG always generated |
| Model not converged | ELBO still decreasing at max_epochs | Increase max_epochs or check data |
| Batch-condition confounding | Condition has N=1 sample | Integration valid, but composition comparisons need caveats |
| Low-confidence predictions | scANVI max_prob < 0.8 | Review these cells manually — may be novel types |

**Detailed troubleshooting:** [references/troubleshooting.md](references/troubleshooting.md)

## Suggested Next Steps

1. **Downstream clustering + UMAP** — Use Scanpy (`sc.pp.neighbors`, `sc.tl.umap`, `sc.tl.leiden`) on the scVI/scANVI latent space
2. **Functional Enrichment** — `functional-enrichment-from-degs` for pathway analysis of Bayesian DE results
3. **Trajectory Analysis** — `scrna-trajectory-inference` for developmental datasets
4. **Cell-Cell Communication** — `cell-cell-communication` for ligand-receptor analysis

## Related Skills

**Prerequisite:** `scrnaseq-scanpy-core-analysis` (Python) or `scrnaseq-seurat-core-analysis` (R, export to h5ad)

**Downstream:** `functional-enrichment-from-degs`, `scrna-trajectory-inference`, `cell-cell-communication`

**Complementary:** `experimental-design-statistics`

**Spatial extension:** `scvi-tools-spatial` (Cell2location, DestVI, Tangram, scVIVA for spatial deconvolution)

## References

1. **scVI:** Lopez R, Regier J, Cole MB, Jordan MI, Yosef N. (2018) Deep generative modeling for single-cell transcriptomics. *Nat Methods*. 15:1053-1058.
2. **scANVI:** Xu C, Lopez R, Mehlman E, Regier J, Jordan MI, Yosef N. (2021) Probabilistic harmonization and annotation of single-cell transcriptomics data with deep generative models. *Mol Syst Biol*. 17:e9620.
3. **LDVAE:** Svensson V, Gayoso A, Yosef N, Pachter L. (2020) Interpretable factor models of single-cell RNA-seq via variational autoencoders. *Bioinformatics*. 36:3418-3421.
4. **CellAssign:** Zhang AW, O'Flanagan C, Chavez EA, et al. (2019) Probabilistic cell-type assignment of single-cell RNA-seq for tumor microenvironment profiling. *Nat Methods*. 16:1007-1015.
5. **VeloVI:** Gayoso A, Weiler P, Lotfollahi M, et al. (2023) Deep generative modeling of transcriptional dynamics for RNA velocity analysis in single cells. *Nat Methods*. 21:50-59.
6. **scvi-tools:** Gayoso A, Lopez R, Xing G, et al. (2022) A Python library for probabilistic analysis of single-cell omics data. *Nat Biotechnol*. 40:163-166.

**Detailed guides:** [model-guide.md](references/model-guide.md) | [differential-expression.md](references/differential-expression.md) | [theoretical-foundations.md](references/theoretical-foundations.md) | [troubleshooting.md](references/troubleshooting.md)

**Scripts:** [scripts/](scripts/)
