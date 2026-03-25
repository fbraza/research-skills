# Plan: Create `scvi-tools-scrna` Skill

> **First action:** Write this plan as `/Users/fbraza/Documents/Biomni/plans/scvi-tools-scrna-plan.md` so the user has a durable copy for future reference. Then proceed with implementation.

## Context

The project has mature scRNA-seq skills for Scanpy (Python) and Seurat (R) that handle the full pipeline from QC to annotation. scvi-tools is already used as an integration option within the Scanpy skill (`integrate_scvi.py`), but its advanced capabilities (semi-supervised annotation, interpretable factors, marker-based classification, probabilistic velocity) are not exposed as a standalone skill.

The `/Users/fbraza/Documents/Biomni/TO_EVALUATE/scvi/scvi-tools/` folder contains draft reference files covering the full scvi-tools ecosystem (all modalities). This plan narrows the scope to **scRNA-seq models only**: scVI, scANVI, LDVAE, CellAssign, and VeloVI — based on the papers (Lopez 2018, Xu 2021, Svensson 2020, Zhang 2019, Gayoso 2023) and official tutorials.

**Goal:** Create a production-ready skill that complements the existing Scanpy/Seurat skills for advanced deep generative modeling tasks, with modular scripts, detailed references, and cross-skill integration.

---

## 1. Directory Structure

```
skills/scvi-tools-scrna/
├── SKILL.md
├── references/
│   ├── theoretical-foundations.md    (adapted from TO_EVALUATE)
│   ├── model-guide.md               (NEW — decision trees, DOs/DON'Ts per model)
│   ├── differential-expression.md   (adapted from TO_EVALUATE, trimmed to scRNA-seq)
│   └── troubleshooting.md           (NEW — consolidated from TO_EVALUATE + model-specific)
├── scripts/
│   ├── setup_scvi.py                (shared utilities: validation, GPU, training diagnostics)
│   ├── run_scvi.py                  (scVI: integration, latent, normalized expression)
│   ├── run_scanvi.py                (scANVI: semi-supervised label transfer)
│   ├── run_ldvae.py                 (LDVAE: interpretable factors, gene loadings)
│   ├── run_cellassign.py            (CellAssign: marker-based annotation)
│   ├── run_velovi.py                (VeloVI: probabilistic RNA velocity)
│   ├── run_scvi_de.py               (Bayesian DE: shared across scVI/scANVI)
│   └── plot_scvi_diagnostics.py     (training curves, UMAP, batch mixing, etc.)
└── assets/                          (empty for now; eval scripts can be added later)
```

---

## 2. SKILL.md — Content Outline

**File:** `skills/scvi-tools-scrna/SKILL.md`
**Pattern:** Follow `skills/scrnaseq-scanpy-core-analysis/SKILL.md` structure exactly.

### Frontmatter
```yaml
id: scvi-tools-scrna
name: scVI-tools for Single-Cell RNA-seq
category: transcriptomics
short-description: "Deep generative models (scVI, scANVI, LDVAE, CellAssign, VeloVI) for advanced scRNA-seq analysis: probabilistic batch integration, semi-supervised label transfer, interpretable gene programs, marker-based annotation, and RNA velocity with uncertainty."
detailed-description: "Advanced single-cell RNA-seq modeling using scvi-tools deep generative models. Use after preprocessing with the Scanpy or Seurat skill. scVI provides probabilistic batch correction, normalized expression, and Bayesian DE. scANVI extends scVI with semi-supervised label transfer from partial annotations. LDVAE extracts interpretable gene programs via linear decoder. CellAssign performs probabilistic cell type assignment using marker gene panels. VeloVI adds RNA velocity with uncertainty quantification. All models use raw counts, produce latent representations in AnnData, and integrate with downstream Scanpy workflows. GPU recommended for datasets >10k cells."
starting-prompt: "Apply deep generative modeling to preprocessed single-cell RNA-seq data using scvi-tools."
```

### Sections (in order)

1. **When to Use This Skill**
   - Batch integration with probabilistic modeling (scVI)
   - Semi-supervised label transfer from reference annotations (scANVI)
   - Interpretable gene program discovery (LDVAE)
   - Marker-based cell type annotation without reference datasets (CellAssign)
   - RNA velocity with uncertainty quantification (VeloVI)
   - Bayesian differential expression with effect size thresholds
   - **Don't use for:** Standard preprocessing/QC (→ scanpy skill), R-based workflows (→ seurat skill), ATAC-seq/multimodal/spatial (future skills), basic integration already covered by scanpy skill
   - **Prerequisite:** Preprocessed AnnData from Scanpy or Seurat skill with raw counts preserved

2. **Installation** (table format)
   - scvi-tools ≥1.1, scanpy ≥1.9, anndata ≥0.8, torch >=2.0, scvelo ≥0.2.5 (VeloVI only), matplotlib, seaborn
   - GPU install variant: `pip install scvi-tools[cuda12]`

3. **Inputs**
   - Preprocessed AnnData (.h5ad) with raw counts in `adata.layers['counts']` or `adata.X`
   - HVGs marked in `adata.var['highly_variable']`
   - Batch key in `adata.obs` (for integration)
   - (scANVI) Partial cell type labels in `adata.obs`; unlabeled cells marked with a category string
   - (CellAssign) Binary marker gene matrix as a pandas DataFrame (index=gene_names, columns=cell_types)
   - (VeloVI) Spliced/unspliced counts from scVelo preprocessing (layers `Ms`, `Mu`)

4. **Outputs**
   - Latent representations: `adata.obsm['X_scVI']`, `['X_scANVI']`, `['X_LDVAE']`
   - Normalized expression: `adata.layers['scvi_normalized']`
   - Predictions: `adata.obs['scanvi_predictions']`, `['cellassign_predictions']`
   - LDVAE gene loadings: CSV + DataFrame
   - DE results: DataFrame (CSV) with lfc_mean, lfc_std, bayes_factor, is_de_fdr columns
   - VeloVI outputs: velocities, latent_time, kinetic rates (α, β, γ), permutation scores
   - Training diagnostics: PNG + SVG plots
   - Saved model directories (.pt files for persistence/transfer learning)

5. **Clarification Questions**
   - Which task? (integration / label transfer / gene programs / marker annotation / velocity / DE)
   - Preprocessed AnnData available? If not → run scanpy/seurat skill first
   - Batch structure? (batch_key, number of batches, condition confounding?)
   - (scANVI) Fraction of labeled cells? Label column name?
   - (CellAssign) Marker gene matrix available? Or need help constructing one?
   - (VeloVI) Has scVelo preprocessing been run?
   - GPU available?

6. **Standard Workflow** — task-centric, branching after Step 2

   **Step 1 — Validate & Setup** | `scripts/setup_scvi.py`
   ```python
   from setup_scvi import validate_anndata_for_scvi, register_anndata_scvi
   validate_anndata_for_scvi(adata, require_counts=True, require_hvg=True)
   adata = register_anndata_scvi(adata, batch_key="batch", layer="counts")
   ```
   VERIFICATION: `"✓ Input validated"` message

   **Step 2 — Train scVI (Foundation)** | `scripts/run_scvi.py`
   ```python
   from run_scvi import train_scvi
   adata, scvi_model = train_scvi(adata, batch_key="batch", n_latent=30, save_model="results/scvi_model")
   ```
   VERIFICATION: Training curves plotted, ELBO converged, `X_scVI` shape printed

   **Step 3a — Label Transfer (scANVI)** [OPTIONAL] | `scripts/run_scanvi.py`
   ```python
   from run_scanvi import train_scanvi_from_scvi, predict_cell_types
   adata, scanvi_model = train_scanvi_from_scvi(scvi_model, adata, labels_key="cell_type", unlabeled_category="Unknown")
   predictions = predict_cell_types(scanvi_model, adata)
   ```
   VERIFICATION: Prediction accuracy on labeled cells, confidence distribution

   **Step 3b — Gene Programs (LDVAE)** [OPTIONAL] | `scripts/run_ldvae.py`
   ```python
   from run_ldvae import train_ldvae, get_gene_loadings, identify_gene_programs
   adata, ldvae_model = train_ldvae(adata, n_latent=10)
   loadings = get_gene_loadings(ldvae_model)
   programs = identify_gene_programs(loadings, n_top_genes=50)
   ```
   VERIFICATION: Loadings matrix shape, top genes per factor printed

   **Step 3c — Marker Annotation (CellAssign)** [OPTIONAL] | `scripts/run_cellassign.py`
   ```python
   from run_cellassign import create_marker_matrix, train_cellassign
   marker_mat = create_marker_matrix({"T cells": ["CD3D","CD3E"], "B cells": ["CD19","MS4A1"], ...})
   adata, ca_model = train_cellassign(adata, marker_mat)
   ```
   VERIFICATION: Assignment proportions printed, confidence distribution

   **Step 3d — RNA Velocity (VeloVI)** [OPTIONAL] | `scripts/run_velovi.py`
   ```python
   from run_velovi import validate_velocity_data, train_velovi, compute_permutation_scores
   validate_velocity_data(adata)
   adata, velo_model = train_velovi(adata)
   perm_scores = compute_permutation_scores(velo_model, adata)
   ```
   VERIFICATION: Permutation score > reference threshold, coherence scores printed

   **Step 4 — Bayesian DE** [OPTIONAL] | `scripts/run_scvi_de.py`
   ```python
   from run_scvi_de import run_bayesian_de, filter_de_results, plot_volcano
   de_results = run_bayesian_de(scvi_model, adata, groupby="cell_type", group1="TypeA", group2="TypeB", mode="change", delta=0.25)
   up, down = filter_de_results(de_results)
   plot_volcano(de_results, output_dir="results")
   ```
   VERIFICATION: DE gene counts printed, volcano plot saved

   **Step 5 — Diagnostics & Export** | `scripts/plot_scvi_diagnostics.py`
   ```python
   from plot_scvi_diagnostics import plot_training_history, plot_latent_umap, plot_batch_mixing
   plot_training_history(scvi_model, output_dir="results")
   plot_latent_umap(adata, color_keys=["batch","cell_type"], output_dir="results")
   ```

7. **Decision Guide** (table)

   | Task | Model | When to Use | Key Parameter |
   |------|-------|-------------|---------------|
   | Batch integration | scVI | Always run first; multi-batch data | `n_latent=30, batch_key` |
   | Label transfer | scANVI | Have partial annotations or reference labels | `unlabeled_category, labels_key` |
   | Gene programs | LDVAE | Need interpretable factors (which genes drive which axis) | `n_latent=10-20` |
   | Marker annotation | CellAssign | Have marker lists, no reference dataset | `marker_gene_mat` |
   | RNA velocity | VeloVI | Have spliced/unspliced counts, developmental data | `spliced_layer, unspliced_layer` |
   | Differential expression | scVI/scANVI DE | Compare conditions/cell types probabilistically | `mode="change", delta=0.25` |

8. **Important DOs and DON'Ts** (consolidated from papers)

   **DO:**
   - Always use raw counts (not log-transformed or normalized) for all scvi-tools models
   - Filter to highly variable genes (1000-4000) before training
   - Register batch/technical covariates in `setup_anndata()`
   - Initialize scANVI from a pre-trained scVI model (better convergence)
   - Check training convergence via ELBO curves before using results
   - Use `mode="change"` with a biologically meaningful `delta` for DE
   - Run permutation scores before interpreting VeloVI velocity results
   - Save trained models for reproducibility and transfer learning
   - Set random seeds for all stochastic methods

   **DON'T:**
   - Don't pass log-normalized or scaled data to any scvi-tools model
   - Don't treat scVI latent dimensions as interpretable (use LDVAE for that)
   - Don't expect scANVI to discover novel cell types absent from training labels
   - Don't use CellAssign without validating that marker genes exist in your dataset
   - Don't trust VeloVI results on datasets with low permutation scores (no transient dynamics)
   - Don't use "vanilla" mode DE without a delta threshold (finds trivially small effects)
   - Don't apply double normalization (scvi-tools normalizes internally)
   - Don't ignore batch-condition confounding warnings

9. **Common Issues** (table)

   | Issue | Cause | Solution |
   |-------|-------|----------|
   | NaN loss during training | Zero-variance genes, extreme outliers | Filter genes with `min_counts=3`, check for NaN/Inf in data |
   | ELBO not converging | Insufficient epochs or learning rate | Increase `max_epochs`, check data registration |
   | GPU out of memory | Dataset too large for VRAM | Reduce `batch_size`, use fewer HVGs, or use CPU |
   | Batch overcorrection | Too many batch keys or confounded design | Reduce covariates, check batch-condition confounding |
   | scANVI low accuracy | Poor seed labels or too few labeled cells | Verify label quality, ensure ≥5% labeled cells |
   | CellAssign all one type | Marker genes not expressed or wrong matrix orientation | Validate markers exist in `adata.var_names`, check matrix is genes×types |
   | VeloVI low permutation scores | Dataset has no transient dynamics | Velocity analysis inappropriate for this dataset; use other methods |
   | LDVAE loadings uninterpretable | Too many/few latent dims | Try `n_latent` in range 5-20, check variance explained per factor |
   | `accelerator` parameter error | Old scvi-tools version uses `use_gpu` | Upgrade to scvi-tools ≥1.1 or use `use_gpu=True` for older versions |

10. **Suggested Next Steps**
    - Downstream clustering + UMAP with Scanpy skill (if not already done)
    - Functional enrichment on DE results → `functional-enrichment-from-degs`
    - Trajectory inference → `scrna-trajectory-inference`
    - Cell-cell communication → `cell-cell-communication`

11. **Related Skills**
    - **Prerequisite:** `scrnaseq-scanpy-core-analysis` (Python) or `scrnaseq-seurat-core-analysis` (R, export to h5ad)
    - **Downstream:** `functional-enrichment-from-degs`, `scrna-trajectory-inference`, `cell-cell-communication`
    - **Complementary:** `experimental-design-statistics`

12. **References** (with DOIs)
    - Lopez R, et al. (2018) *Nat Methods* 15:1053-1058 [scVI]
    - Xu C, et al. (2021) *Mol Syst Biol* 17:e9620 [scANVI]
    - Svensson V, et al. (2020) *Bioinformatics* 36:3418-3421 [LDVAE]
    - Zhang AW, et al. (2019) *Nat Methods* 16:1007-1015 [CellAssign]
    - Gayoso A, et al. (2023) *Nat Methods* 21:50-59 [VeloVI]
    - Gayoso A, et al. (2022) *Nat Biotechnol* 40:163-166 [scvi-tools framework]

---

## 3. Reference Files — Content

### `references/theoretical-foundations.md`
**Source:** `/Users/fbraza/Documents/Biomni/TO_EVALUATE/scvi/scvi-tools/references/theoretical-foundations.md` (439 lines)
**Action:** Copy and modify:
- Keep: Variational inference, VAE architecture, amortized inference, count distributions (NB, ZINB), batch correction framework, differential expression framework
- Remove: MrVI section, totalVI/PeakVI references, any spatial/ATAC content
- Add: LDVAE section (linear decoder = W matrix, interpretability, gene loadings), CellAssign generative model (hierarchical NB with marker over-expression δ), VeloVI model (spliced/unspliced kinetics with latent time sharing across genes)

### `references/model-guide.md`
**Source:** NEW file, consolidating from `TO_EVALUATE/references/models-scrna-seq.md` and papers
**Structure per model:**
1. Purpose (1 paragraph, from paper abstracts)
2. When to Use (bullet list)
3. Key Parameters (table: parameter, default, recommended range, notes)
4. API Quick Reference (setup_anndata → train → extract)
5. DOs and DON'Ts (derived from papers — biological caveats, statistical assumptions)
6. Output Interpretation (what each output means, how to use it)

End with **Model Selection Flowchart:**
```
Start → Need batch correction? → Yes → scVI (always first)
                                → Then need labels? → scANVI
                                → Then need interpretable factors? → LDVAE
       → Have marker genes, no reference? → CellAssign
       → Have spliced/unspliced data? → VeloVI
       → Need DE between conditions? → scVI/scANVI DE
```

### `references/differential-expression.md`
**Source:** `/Users/fbraza/Documents/Biomni/TO_EVALUATE/scvi/scvi-tools/references/differential-expression.md` (582 lines)
**Action:** Copy and modify:
- Remove: Multi-modal DE sections (totalVI protein DE lines ~398-425, PeakVI accessibility lines ~427-442)
- Keep: Everything else (core framework, basic usage, key parameters, interpretation, advanced usage, visualization, best practices, complete workflow example)
- Add: Section on "When to use Bayesian DE vs pseudobulk DE" — clarify that scvi-tools DE is cell-level Bayesian testing (good for exploratory marker discovery), while pseudobulk DE (DESeq2) remains the gold standard for condition comparisons with biological replicates. Cross-reference the scanpy skill's `pseudobulk_de_guide.md`.

### `references/troubleshooting.md`
**Source:** NEW file, consolidating from `TO_EVALUATE/references/workflows.md` (troubleshooting section ~lines 439-508) + new content
**Sections:**
1. Training Issues (NaN loss, non-convergence, slow training, GPU OOM)
2. Data Issues (missing counts, wrong layer, gene filtering, HVG selection)
3. Model-Specific Issues:
   - scVI: Poor batch mixing, overcorrection
   - scANVI: Low prediction accuracy, label leakage, novel cell types
   - LDVAE: Uninterpretable loadings, choosing n_latent
   - CellAssign: Marker matrix errors, all-one-type assignment, gene name mismatches
   - VeloVI: Low permutation scores, preprocessing errors, scVelo compatibility
4. Performance Optimization (batch size tuning, GPU vs CPU, large dataset strategies)

---

## 4. Script Files — Detailed Specifications

All scripts follow the pattern established by `/Users/fbraza/Documents/Biomni/skills/scrnaseq-scanpy-core-analysis/scripts/integrate_scvi.py`:
- Module docstring (purpose, functions, requirements)
- Type hints on all functions
- `try/except ImportError` for optional dependencies
- Progress messages with `"✓"` verification checkmarks
- Return AnnData objects (or tuples of AnnData + model) for chaining
- Store metadata in `adata.uns['{model}_info']`
- Print "Next steps" suggestions at the end
- `if __name__ == "__main__"` block with example usage

### `scripts/setup_scvi.py` — Shared Utilities

```python
"""
Shared utilities for scvi-tools models.

Functions:
  - validate_anndata_for_scvi(): Check AnnData has required fields
  - detect_accelerator(): Detect GPU/MPS/CPU
  - register_anndata_scvi(): Wrapper around setup_anndata with validation
  - plot_training_curves(): ELBO loss curves
  - check_convergence(): Convergence metrics
  - save_model_with_metadata(): Save model + metadata JSON
"""

def validate_anndata_for_scvi(adata, require_counts=True, require_hvg=True, batch_key=None) -> bool:
    """Validate AnnData is ready for scvi-tools. Checks: raw counts (no NaN, no negatives,
    integer-like values), HVGs marked, batch key exists. Prints diagnostic summary."""

def detect_accelerator() -> str:
    """Detect best available accelerator. Returns 'gpu', 'mps', or 'cpu'.
    Prints device info (CUDA version, GPU name, memory)."""

def register_anndata_scvi(adata, batch_key, layer="counts",
                           categorical_covariate_keys=None,
                           continuous_covariate_keys=None) -> sc.AnnData:
    """Wrapper around SCVI.setup_anndata() with pre-validation.
    Detects layer automatically if layer param is None."""

def plot_training_curves(model, output_dir="results") -> None:
    """Plot ELBO train/validation loss curves. Save PNG + SVG at 300 DPI."""

def check_convergence(model, min_epochs=50) -> dict:
    """Assess model convergence. Returns dict with final_loss, loss_delta,
    epochs_trained, converged (bool). Warns if not converged."""

def save_model_with_metadata(model, path, adata=None) -> None:
    """Save model + write metadata JSON (model params, training epochs,
    software versions, data shape)."""
```

### `scripts/run_scvi.py` — scVI

```python
"""
scVI: Single-Cell Variational Inference
Train scVI for probabilistic batch correction and latent representation.

Functions:
  - train_scvi(): Train model, extract latent, store in adata
  - get_scvi_normalized_expression(): Denoised normalized expression
"""

def train_scvi(adata, batch_key, n_latent=30, n_layers=2, n_hidden=128,
               gene_likelihood="nb", dropout_rate=0.1, max_epochs=400,
               early_stopping=True, batch_size=128,
               save_model=None, random_state=0) -> tuple:
    """Train scVI model.
    Returns (adata, model).
    Stores: adata.obsm['X_scVI'], adata.uns['scvi_info']"""

def get_scvi_normalized_expression(model, adata, library_size=1e4,
                                    n_samples=25) -> sc.AnnData:
    """Get denoised normalized expression from trained scVI model.
    Stores in adata.layers['scvi_normalized']. Returns adata."""
```

### `scripts/run_scanvi.py` — scANVI

```python
"""
scANVI: Semi-supervised label transfer and annotation.

Functions:
  - train_scanvi_from_scvi(): Initialize from pretrained scVI (recommended)
  - train_scanvi_from_scratch(): Train from scratch
  - predict_cell_types(): Extract predictions with probabilities
  - evaluate_predictions(): Accuracy, confusion matrix, confidence
"""

def train_scanvi_from_scvi(scvi_model, adata, labels_key,
                            unlabeled_category="Unknown",
                            max_epochs=200, save_model=None) -> tuple:
    """Initialize scANVI from pretrained scVI model (recommended path).
    Returns (adata, scanvi_model).
    Stores: adata.obsm['X_scANVI'], adata.obs['scanvi_predictions']"""

def train_scanvi_from_scratch(adata, batch_key, labels_key,
                               unlabeled_category="Unknown",
                               n_latent=30, max_epochs=200,
                               save_model=None) -> tuple:
    """Train scANVI from scratch. Less recommended than from_scvi path."""

def predict_cell_types(model, adata) -> pd.DataFrame:
    """Extract predictions + per-cell-type probabilities.
    Returns DataFrame with columns: prediction, max_probability, + one col per type.
    Flags low-confidence cells (max_prob < 0.8)."""

def evaluate_predictions(adata, labels_key,
                          predictions_key="scanvi_predictions") -> dict:
    """Evaluate on labeled cells. Returns accuracy, per-class accuracy,
    confusion matrix, low-confidence count."""
```

### `scripts/run_ldvae.py` — Linear Decoder VAE

```python
"""
LDVAE: Interpretable dimensionality reduction with linear decoder.

Functions:
  - train_ldvae(): Train LinearSCVI model
  - get_gene_loadings(): Extract gene loadings matrix
  - identify_gene_programs(): Top genes per latent dimension
  - plot_loadings_heatmap(): Visualize loadings
"""

def train_ldvae(adata, batch_key=None, n_latent=10, n_hidden=128,
                max_epochs=400, save_model=None, random_state=0) -> tuple:
    """Train LinearSCVI (LDVAE). Returns (adata, model).
    Stores: adata.obsm['X_LDVAE'], adata.uns['ldvae_info']"""

def get_gene_loadings(model) -> pd.DataFrame:
    """Extract loadings matrix (genes x latent_dims).
    Returns DataFrame with gene names as index, Factor_0..N as columns."""

def identify_gene_programs(loadings_df, n_top_genes=50) -> dict:
    """For each latent dim, extract top positive and negative genes.
    Returns dict: {factor_name: {'positive': [...], 'negative': [...]}}"""

def plot_loadings_heatmap(loadings_df, n_top=20, output_dir="results") -> None:
    """Heatmap of top gene loadings per factor. PNG + SVG at 300 DPI."""
```

### `scripts/run_cellassign.py` — CellAssign

```python
"""
CellAssign: Probabilistic marker-based cell type annotation.

Functions:
  - create_marker_matrix(): Build binary marker matrix from dict
  - validate_marker_matrix(): Check genes exist in adata
  - train_cellassign(): Train model and extract assignments
  - get_assignment_probabilities(): Soft assignments per cell
  - summarize_assignments(): Cell type counts and confidence
"""

def create_marker_matrix(marker_dict: dict) -> pd.DataFrame:
    """Convert {cell_type: [gene_list]} to binary DataFrame (genes x types).
    Validates no duplicate genes across types."""

def validate_marker_matrix(marker_mat, adata) -> pd.DataFrame:
    """Check marker genes exist in adata.var_names. Warns about missing genes.
    Returns filtered matrix with only matching genes.
    Raises if <2 genes per type remain."""

def train_cellassign(adata, marker_mat, max_epochs=400,
                      save_model=None) -> tuple:
    """Train CellAssign. Returns (adata, model).
    Stores: adata.obs['cellassign_predictions'], adata.uns['cellassign_info']"""

def get_assignment_probabilities(model, adata) -> pd.DataFrame:
    """Soft assignments: probability per cell type per cell.
    Returns DataFrame (cells x cell_types)."""

def summarize_assignments(adata, prediction_key="cellassign_predictions") -> pd.DataFrame:
    """Summary table: cell type, count, proportion, mean confidence.
    Flags types with mean confidence < 0.7."""
```

### `scripts/run_velovi.py` — VeloVI

```python
"""
VeloVI: Probabilistic RNA velocity with uncertainty quantification.

Functions:
  - validate_velocity_data(): Check spliced/unspliced layers
  - preprocess_for_velovi(): scVelo preprocessing if needed
  - train_velovi(): Train VeloVI model
  - get_velocity_results(): Extract velocities, latent time, rates
  - compute_permutation_scores(): Dataset suitability assessment
  - compute_coherence_scores(): Per-cell velocity coherence
"""

def validate_velocity_data(adata) -> bool:
    """Check spliced/unspliced layers exist ('Ms', 'Mu' or 'spliced', 'unspliced').
    Prints instructions if missing."""

def preprocess_for_velovi(adata, min_shared_counts=30, n_top_genes=2000) -> sc.AnnData:
    """Run scVelo preprocessing: filter_and_normalize, moments.
    Returns preprocessed adata with Ms/Mu layers."""

def train_velovi(adata, spliced_layer="Ms", unspliced_layer="Mu",
                  n_latent=30, max_epochs=500,
                  save_model=None) -> tuple:
    """Train VeloVI. Returns (adata, model).
    Stores: adata.obs['velovi_latent_time'], adata.layers['velocity'],
    adata.uns['velovi_info']"""

def get_velocity_results(model, adata) -> sc.AnnData:
    """Extract velocities, latent time, kinetic rates (alpha, beta, gamma),
    switch times. Stores all in adata layers/obs/uns."""

def compute_permutation_scores(model, adata, n_permutations=10) -> pd.DataFrame:
    """Per-gene permutation scores for dataset suitability.
    Returns DataFrame with gene, score, significant columns.
    Prints summary: fraction of genes with significant dynamics."""

def compute_coherence_scores(adata) -> pd.Series:
    """Per-cell velocity coherence. High = consistent dynamics, Low = noisy.
    Stores in adata.obs['velocity_coherence']. Returns Series."""
```

### `scripts/run_scvi_de.py` — Bayesian Differential Expression

```python
"""
Bayesian differential expression using scVI/scANVI trained models.

Functions:
  - run_bayesian_de(): Wrapper around model.differential_expression
  - filter_de_results(): Split into up/down regulated
  - plot_volcano(): Volcano plot (LFC vs Bayes factor)
  - summarize_de(): Counts and effect size summary
"""

def run_bayesian_de(model, adata, groupby, group1, group2=None,
                     mode="change", delta=0.25, fdr_target=0.05,
                     n_samples=5000, batch_correction=True) -> pd.DataFrame:
    """Run Bayesian DE with change mode (recommended).
    Returns DataFrame with lfc_mean, lfc_std, bayes_factor, is_de_fdr columns.
    Prints summary counts."""

def filter_de_results(de_results, fdr_col="is_de_fdr_0.05",
                       lfc_threshold=0.25) -> tuple:
    """Split into (upregulated, downregulated) DataFrames.
    Both sorted by abs(lfc_mean) descending."""

def plot_volcano(de_results, output_dir="results", title=None,
                  lfc_threshold=0.25) -> None:
    """Volcano plot: LFC vs -log10(1/Bayes factor). Colors: significant (red/blue),
    non-significant (grey). Labels top 10 genes. PNG + SVG at 300 DPI."""

def summarize_de(de_results, fdr_col="is_de_fdr_0.05") -> dict:
    """Returns dict: total_tested, total_de, n_up, n_down,
    median_lfc_up, median_lfc_down, top5_up, top5_down."""
```

### `scripts/plot_scvi_diagnostics.py` — Visualization

```python
"""
Diagnostic plots for scvi-tools models.

Functions:
  - plot_training_history(): ELBO curves
  - plot_latent_umap(): UMAP colored by metadata
  - plot_batch_mixing(): Before/after integration comparison
  - plot_scanvi_confidence(): Prediction probability histogram
  - plot_ldvae_loadings(): Gene loadings heatmap
  - plot_cellassign_probabilities(): Cell x type probability heatmap
  - plot_velovi_diagnostics(): Permutation scores, coherence, latent time
"""

# Each function:
# - Takes adata and output_dir
# - Saves PNG + SVG at 300 DPI
# - Uses consistent color scheme (avoid rainbow/jet)
# - Prints "✓ Plot saved: {path}"
```

---

## 5. Cross-Skill Modifications

### 5a. Scanpy Skill: `skills/scrnaseq-scanpy-core-analysis/SKILL.md`

**Location:** Lines 267-273 (Suggested Next Steps + Related Skills)

**Add to Suggested Next Steps (after item 3):**
```
4. **Advanced Deep Generative Modeling** — scvi-tools-scrna for probabilistic label transfer (scANVI), interpretable gene programs (LDVAE), marker-based annotation (CellAssign), Bayesian DE, or RNA velocity with uncertainty (VeloVI)
```

**Update Related Skills line:**
```
**Complementary:** bulk-omics-clustering, experimental-design-statistics, scvi-tools-scrna (advanced deep generative models)
```

### 5b. Seurat Skill: `skills/scrnaseq-seurat-core-analysis/SKILL.md`

**Location:** Lines 555-570 (Suggested Next Steps + Related Skills)

**Add to Suggested Next Steps (after item 4):**
```
5. **Advanced Deep Generative Modeling (Python)** — Export Seurat object to h5ad format, then use scvi-tools-scrna for probabilistic label transfer (scANVI), gene programs (LDVAE), marker-based annotation (CellAssign), or Bayesian DE. Requires Python environment.
```

**Update Related Skills:**
```
**Complementary:** bulk-omics-clustering (non-scRNA-seq), experimental-design-statistics (plan experiments), scvi-tools-scrna (Python-based deep generative models; requires h5ad export)
```

### 5c. CLAUDE.md Skill Dispatch Table

**Location:** Lines 58-92 (Skill Dispatch table)

**Add new row after the scRNA-seq (R) row:**
```
| scVI-tools deep generative models (scRNA-seq) | `scvi-tools-scrna` |
```

---

## 6. Implementation Sequence (for execution)

| Step | Files | Dependencies |
|------|-------|-------------|
| 1 | Create directory: `skills/scvi-tools-scrna/`, `references/`, `scripts/` | None |
| 2 | Write `scripts/setup_scvi.py` | None (shared utilities needed by all scripts) |
| 3 | Write `scripts/run_scvi.py` | `setup_scvi.py` |
| 4 | Write `scripts/run_scanvi.py` | `setup_scvi.py` |
| 5 | Write `scripts/run_ldvae.py` | `setup_scvi.py` |
| 6 | Write `scripts/run_cellassign.py` | `setup_scvi.py` |
| 7 | Write `scripts/run_velovi.py` | `setup_scvi.py` |
| 8 | Write `scripts/run_scvi_de.py` | `setup_scvi.py` |
| 9 | Write `scripts/plot_scvi_diagnostics.py` | `setup_scvi.py` |
| 10 | Write `references/theoretical-foundations.md` | Adapt from TO_EVALUATE |
| 11 | Write `references/model-guide.md` | New, based on papers + TO_EVALUATE |
| 12 | Write `references/differential-expression.md` | Adapt from TO_EVALUATE |
| 13 | Write `references/troubleshooting.md` | New, based on TO_EVALUATE + papers |
| 14 | Write `SKILL.md` | After all scripts and references are done |
| 15 | Update Scanpy `SKILL.md` cross-references | Small edit (2 lines) |
| 16 | Update Seurat `SKILL.md` cross-references | Small edit (2 lines) |
| 17 | Update `CLAUDE.md` skill dispatch table | Small edit (1 line) |

**Parallelizable:** Steps 3-9 (all scripts) can be done in parallel. Steps 10-13 (references) can be done in parallel. Step 14 depends on all prior steps.

---

## 7. Key Sources to Reference During Implementation

| File | Purpose |
|------|---------|
| `/Users/fbraza/Documents/Biomni/skills/scrnaseq-scanpy-core-analysis/SKILL.md` | Template for SKILL.md structure |
| `/Users/fbraza/Documents/Biomni/skills/scrnaseq-scanpy-core-analysis/scripts/integrate_scvi.py` | Template for script pattern (docstrings, error handling, return conventions) |
| `/Users/fbraza/Documents/Biomni/TO_EVALUATE/scvi/scvi-tools/references/theoretical-foundations.md` | Source for theoretical-foundations.md |
| `/Users/fbraza/Documents/Biomni/TO_EVALUATE/scvi/scvi-tools/references/models-scrna-seq.md` | Source for model-guide.md |
| `/Users/fbraza/Documents/Biomni/TO_EVALUATE/scvi/scvi-tools/references/differential-expression.md` | Source for differential-expression.md |
| `/Users/fbraza/Documents/Biomni/TO_EVALUATE/scvi/scvi-tools/references/workflows.md` | Source for troubleshooting.md + workflow patterns |
| `/Users/fbraza/Documents/Biomni/CLAUDE.md` (lines 58-92) | Skill dispatch table to update |

---

## 8. Verification Plan

1. **Script syntax:** Each script should be parseable Python (no syntax errors)
2. **Import chain:** `setup_scvi.py` has no internal dependencies; all other scripts import from it
3. **API correctness:** Verify scvi-tools ≥1.1 API:
   - `SCVI.setup_anndata()` uses `layer=` not `data_layer=`
   - `model.train()` uses `accelerator="gpu"` not `use_gpu=True`
   - `LinearSCVI` is the correct class for LDVAE
   - `VELOVI` is at `scvi.external.VELOVI` not `scvi.model.VELOVI`
   - `CellAssign` is at `scvi.external.CellAssign`
4. **Cross-references:** All file paths in SKILL.md match actual files
5. **Consistency:** All `adata.obsm` keys use consistent naming (`X_scVI`, `X_scANVI`, `X_LDVAE`)
6. **No hallucinated APIs:** Every method call should be verifiable against scvi-tools docs
