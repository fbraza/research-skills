---
name: cellbender
description: "CellBender remove-background uses a variational autoencoder (VAE) combined with Pyro probabilistic programming to remove two major technical artifacts from droplet-based single-cell experiments: ambient RNA (RNA from lysed cells that contaminates all droplets) and barcode swapping (PCR chimeras creating spurious counts in wrong cells). It fits a full generative model to the raw unfiltered count matrix, learning the ambient RNA expression profile from empty droplets and inferring per-cell contamination fractions, cell probabilities, and a denoised latent embedding of true gene expression. Use before any downstream analysis on 10x Chromium, Drop-seq, BD Rhapsody, or similar droplet-based data. Supports scRNA-seq, snRNA-seq, CITE-seq, and multiome (RNA+ATAC). Requires a CUDA GPU for practical runtimes (~30–45 min per sample on an NVIDIA T4)."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
starting-prompt: Remove ambient RNA contamination from my droplet-based single-cell RNA-seq data using CellBender.
---

# CellBender: Ambient RNA Removal

**Tool**: CellBender `remove-background`
**Version**: v0.3.2 (latest stable)
**Paper**: Fleming et al. (2023) *Nature Methods* — https://doi.org/10.1038/s41592-023-01943-7
**GitHub**: https://github.com/broadinstitute/CellBender
**Docs**: https://cellbender.readthedocs.io/en/latest/

---

## The Problem CellBender Solves

In droplet-based scRNA-seq (10x Genomics, Drop-seq, etc.), two major technical artifacts contaminate count matrices:

### 1. Ambient RNA
When cells are lysed during library preparation, RNA leaks into the suspension. This "ambient" or "soup" RNA is captured by empty droplets and also contaminates real cell droplets. The result:
- Every cell appears to express genes from lysed cells (e.g., hemoglobin genes in non-erythrocytes)
- Cell type boundaries blur — especially for rare or low-expressing populations
- Differential expression is confounded by ambient contamination

**Signature**: Empty droplets on the UMI curve have a non-zero "plateau" of counts — these are ambient RNA counts.

### 2. Barcode Swapping (PCR chimeras)
During PCR amplification and sequencing, barcodes can swap between molecules, creating spurious counts in the wrong cell. This is especially problematic on patterned flow cells (HiSeq 4000, NovaSeq).

### What CellBender Does
CellBender fits a **deep generative model** (variational autoencoder + Pyro probabilistic programming) to the raw count matrix. It learns:
- The ambient RNA expression profile (from empty droplets)
- Which counts in each cell are likely signal vs. noise
- Per-cell contamination fractions
- A low-dimensional latent embedding of true gene expression

It then outputs a **denoised count matrix** with ambient RNA and barcode swapping removed.

---

## Model Architecture

CellBender uses a **full** generative model (default `--model full`) that combines:

```
Observed counts = True cell expression + Ambient RNA + Barcode swapping noise
```

Key latent variables inferred per droplet:
- `cell_probability`: P(droplet contains a cell) — used for cell calling
- `cell_size`: Estimated total true UMI count in the cell
- `background_fraction`: Fraction of counts that are ambient
- `droplet_efficiency`: Capture efficiency of the droplet
- `z`: Low-dimensional embedding of true gene expression (default 64-dim)

Key global latent variables:
- `ambient_expression`: Normalized ambient RNA profile (sums to 1 across genes)
- `swapping_fraction_dist_params`: Parameters of the barcode swapping model

Training uses **ELBO** (Evidence Lower BOund) maximization via stochastic variational inference. The ELBO learning curve is the primary convergence diagnostic.

---

## Installation

### Recommended: conda + pip
```bash
conda create -n cellbender python=3.7
conda activate cellbender
pip install cellbender
```

### From source (for development)
```bash
conda create -n cellbender python=3.7
conda activate cellbender
conda install -c anaconda pytables
pip install torch  # ensure CUDA version matches your drivers
git clone https://github.com/broadinstitute/CellBender.git
pip install -e CellBender
```

### Specific version/commit
```bash
pip install --no-cache-dir -U git+https://github.com/broadinstitute/CellBender.git@v0.3.2
```

### Docker (GPU-enabled)
```bash
docker pull us.gcr.io/broad-dsde-methods/cellbender:latest
# Older versions: us.gcr.io/broad-dsde-methods/cellbender:0.3.0
```

### Terra / WDL (cloud, no GPU required locally)
- Workflow: `cellbender/remove-background` on Broad Methods Repository
- Also available on Dockstore
- Cost: ~$0.30/sample on Google Cloud (as of 2022)
- Uses preemptible instances + automatic checkpoint restart

### Version note
**Avoid v0.3.1** — it contained a bug causing incorrect output count matrices (integer overflow → negative entries). Use v0.3.0 or v0.3.2+. If you have v0.3.1 outputs, salvage them from the checkpoint:
```bash
cellbender remove-background \
    --input my_raw_count_matrix_file.h5 \
    --output my_cellbender_output_file.h5 \
    --checkpoint path/to/ckpt.tar.gz \
    --force-use-checkpoint
```

---

## Supported Input Formats

| Format | Notes |
|---|---|
| CellRanger v3 `.h5` | `raw_feature_bc_matrix.h5` — **recommended** |
| CellRanger v2 `.h5` | `raw_gene_bc_matrices_h5.h5` |
| CellRanger directory | Directory containing `.mtx` file |
| AnnData `.h5ad` | Must be unfiltered (include empty droplets) |
| Loom `.loom` | Supported |
| Drop-seq DGE `.txt` / `.txt.gz` | Supported |
| BD Rhapsody `.csv` / `.csv.gz` | Supported |

**Critical**: Always use the **raw/unfiltered** matrix — not the filtered one. CellBender needs empty droplets to learn the ambient profile.

---

## Complete Workflow

### Step 1: Inspect the UMI curve

Before running, look at the UMI rank plot from CellRanger's `web_summary.html`. Identify:
- The "knee" — where cell-containing droplets end
- The "empty droplet plateau" — the flat region of low-UMI empty droplets

This informs `--expected-cells` and `--total-droplets-included`.

**Three scenarios:**
- **Exhibit A** (very low plateau, <10 UMIs): Little ambient RNA — CellBender may not remove much. Still worth running.
- **Exhibit B** (clear plateau, 50–500 UMIs): Ideal case — CellBender will clean up significantly.
- **Exhibit C** (no identifiable plateau): Severe contamination — consider re-running the experiment. CellBender may struggle.

### Step 2: Run remove-background

**Minimal command (GPU):**
```bash
cellbender remove-background \
    --cuda \
    --input raw_feature_bc_matrix.h5 \
    --output cellbender_output.h5
```

**Full command with all key parameters:**
```bash
cellbender remove-background \
    --cuda \
    --input raw_feature_bc_matrix.h5 \
    --output cellbender_output.h5 \
    --expected-cells 5000 \
    --total-droplets-included 15000 \
    --fpr 0.01 \
    --epochs 150 \
    --learning-rate 1e-4
```

**CPU-only (slower, for small datasets):**
```bash
cellbender remove-background \
    --input raw_feature_bc_matrix.h5 \
    --output cellbender_output.h5 \
    --expected-cells 5000 \
    --total-droplets-included 15000 \
    --projected-ambient-count-threshold 1 \
    --empty-drop-training-fraction 0.1
```

**CITE-seq (RNA + Antibody Capture):**
```bash
cellbender remove-background \
    --cuda \
    --input raw_feature_bc_matrix.h5 \
    --output cellbender_output.h5
# Both Gene Expression and Antibody Capture features are processed together.
# Antibody Capture results are often even better than Gene Expression.
```

**snRNA-seq (nuclei):**
```bash
# Same command as scRNA-seq — CellBender handles snRNA-seq identically.
cellbender remove-background \
    --cuda \
    --input raw_feature_bc_matrix.h5 \
    --output cellbender_output.h5
```

**Multiple FPR outputs in one run:**
```bash
cellbender remove-background \
    --cuda \
    --input raw_feature_bc_matrix.h5 \
    --output cellbender_output.h5 \
    --fpr 0.0 0.01 0.05 0.1
# Produces: cellbender_output.h5, cellbender_output_fpr0.01.h5, etc.
```

**Resume from checkpoint:**
```bash
# Automatically resumes if ckpt.tar.gz is in the same directory.
# Or specify explicitly:
cellbender remove-background \
    --cuda \
    --input raw_feature_bc_matrix.h5 \
    --output cellbender_output.h5 \
    --checkpoint ckpt.tar.gz
```

### Step 3: Quality control

**Check in order:**

1. **Log file** (`cellbender_output.log`):
   - Lines 13–21: Verify auto-detected priors for cell UMI counts and empty droplet UMI counts match your expectations
   - Check "probable cells", "additional barcodes", "empty droplets" are all nonzero and reasonable
   - Look for any warnings

2. **HTML report** (`cellbender_output_report.html`):
   - Primary QC output — read all warnings and follow recommendations
   - Contains diagnostics, plots, and suggestions for re-running

3. **PDF output** (`cellbender_output.pdf`) — three plots:
   - **Upper**: ELBO learning curve — should increase monotonically and plateau. Spikes or downward dips → reduce `--learning-rate` by 2×
   - **Middle**: UMI rank plot with cell probabilities — most probabilities should be near 0 or 1 (bimodal). Gradual transition → potential issues
   - **Lower**: PCA of latent `z` — clusters = good (different cell types). No clusters = one cell type, or QC failure

4. **Convergence check**: If ELBO has not plateaued, re-run with `--epochs 300`. Do not exceed 300.

5. **Validation plots** (in scanpy):
   ```python
   # Compare UMAP before and after CellBender
   # Compare marker gene dotplots before and after
   # Subtract output from input to inspect what was removed
   ```

### Step 4: Load outputs for downstream analysis

**Recommended — load both raw and CellBender together:**
```python
from cellbender.remove_background.downstream import load_anndata_from_input_and_output

adata = load_anndata_from_input_and_output(
    input_file='raw_feature_bc_matrix.h5',
    output_file='cellbender_output.h5',
    input_layer_key='raw',
)
# adata.X = CellBender denoised counts
# adata.layers['raw'] = original CellRanger counts
# adata.obs['cell_probability'] = CellBender cell calls
# adata.obs['background_fraction'] = per-cell ambient fraction
# adata.var['ambient_expression'] = ambient RNA profile
# adata.obsm['cellbender_embedding'] = latent gene expression
```

**Simple load (scanpy-native):**
```python
import scanpy as sc
# Filtered (cells only, >50% cell probability):
adata = sc.read_10x_h5('cellbender_output_filtered.h5')
# All barcodes:
adata = sc.read_10x_h5('cellbender_output.h5')
```

**Load with CellBender metadata:**
```python
from cellbender.remove_background.downstream import anndata_from_h5
adata = anndata_from_h5('cellbender_output.h5')
# Filter to cells:
cells = adata[adata.obs['cell_probability'] > 0.5]
```

**For Seurat** — strip extra metadata first:
```bash
# In terminal (requires pytables):
ptrepack --complevel 5 cellbender_output_filtered.h5:/matrix cellbender_output_seurat.h5:/matrix
```
```r
library(Seurat)
data <- Read10X_h5('cellbender_output_seurat.h5', use.names=TRUE)
obj <- CreateSeuratObject(counts=data)
```

### Step 5: Downstream analysis

**Use CellBender latent embedding for clustering:**
```python
sc.pp.neighbors(adata, use_rep='cellbender_embedding', metric='euclidean')
sc.tl.umap(adata)
sc.tl.leiden(adata)
```

**Inspect ambient RNA profile:**
```python
import pandas as pd
ambient = adata.var['ambient_expression'].sort_values(ascending=False)
print("Top ambient genes:")
print(ambient.head(20))
# These are the genes most contaminating your data
```

**Compare before/after:**
```python
import matplotlib.pyplot as plt
import scanpy as sc

# Plot a known ambient gene (e.g., HBB in non-erythrocyte datasets)
sc.pl.violin(adata, keys='HBB', layer='raw', groupby='leiden', title='HBB (raw)')
sc.pl.violin(adata, keys='HBB', groupby='leiden', title='HBB (CellBender)')
```

---

## Parameter Guide

### Critical parameters

| Parameter | Default | Guidance |
|---|---|---|
| `--input` | — | **Required.** Raw (unfiltered) count matrix |
| `--output` | — | **Required.** Output `.h5` path |
| `--cuda` | False | **Always use if GPU available** — 10–30× faster |
| `--expected-cells` | auto | Estimated number of cells. Auto-detection works well for clean datasets. Set manually if auto-detection fails. |
| `--total-droplets-included` | auto | Number of barcodes to analyze. Should include all cells + a few thousand empty droplets. Auto-detection works well. |
| `--fpr` | 0.01 | False positive rate. 0.01 = conservative (recommended for most). 0.05–0.1 = more aggressive removal. 0.0 = for cohort DE analysis. |
| `--epochs` | 150 | Training epochs. 150 is usually sufficient. Increase to 300 if ELBO hasn't converged. Never exceed 300. |
| `--learning-rate` | 1e-4 | Reduce by 2× if learning curve has spikes or dips. |

### Setting `--expected-cells`
Look at the UMI rank plot. Find the "knee" — the point where the curve drops sharply. Pick a number where you are confident all droplets to the left are real cells. A rough estimate within 2× is sufficient.

```
Example: UMI curve shows clear knee at ~5000 barcodes → --expected-cells 5000
```

### Setting `--total-droplets-included`
Go a few thousand barcodes past the knee into the empty droplet plateau. Every barcode beyond this number should be "surely empty."

```
Example: Knee at ~5000, plateau starts at ~8000 → --total-droplets-included 15000
```

### Setting `--fpr`
| Use case | Recommended FPR |
|---|---|
| Standard analysis (most users) | 0.01 |
| Aggressive denoising (single sample) | 0.05 or 0.1 |
| Cohort differential expression | 0.0 |
| Comparison across FPR values | 0.0 0.01 0.05 0.1 (all at once) |

### Advanced parameters (rarely needed)

| Parameter | Default | When to change |
|---|---|---|
| `--model` | full | Use `ambient` if no barcode swapping suspected (e.g., non-patterned flow cells) |
| `--z-dim` | 64 | Latent dimension. Rarely needs changing. |
| `--z-layers` | [512] | Encoder hidden layer size. |
| `--low-count-threshold` | 5 | Decrease to 1 if warning about "few empty droplets identified" |
| `--projected-ambient-count-threshold` | 0.1 | Increase (e.g., 1–2) to speed up CPU runs by excluding low-ambient genes |
| `--posterior-batch-size` | 128 | Reduce to 64 if GPU OOM error during posterior sampling |
| `--num-training-tries` | 1 | Increase to 2–3 with `--final-elbo-fail-fraction` for automated pipelines |
| `--exclude-feature-types` | [] | Use `Peaks` to skip ATAC features in multiome data |
| `--ignore-features` | [] | Integer indices of features to leave unchanged in output |
| `--constant-learning-rate` | False | Use if you want to continue training from a checkpoint for more epochs |

---

## Output Files

| File | Description | Keep? |
|---|---|---|
| `output.h5` | Full denoised count matrix (all analyzed barcodes) | **Yes** |
| `output_filtered.h5` | Denoised counts, cells only (cell_probability > 0.5) | **Yes** |
| `output_cell_barcodes.csv` | List of cell barcodes | Yes |
| `output_report.html` | HTML QC report with warnings | **Yes** |
| `output.pdf` | Learning curve + cell calls + PCA | Yes |
| `output.log` | Full run log | Yes |
| `output_metrics.csv` | Scalar metrics for automated pipelines | Optional |
| `ckpt.tar.gz` | Model checkpoint + full posterior | Delete after QC to save space |
| `output_posterior.h5` | Full posterior noise probability matrix | Rarely needed |

**Minimum to keep**: `output_report.html` + `output.h5` (or `output_filtered.h5`)

---

## Omics-Specific Notes

### scRNA-seq (10x Chromium)
Standard use case. Use `raw_feature_bc_matrix.h5` from CellRanger output.

### snRNA-seq
Identical workflow to scRNA-seq. CellBender handles nuclear RNA the same way.

### CITE-seq (RNA + Antibody Capture)
Run on the combined raw matrix — CellBender processes both modalities jointly. Antibody Capture denoising is often even more effective than Gene Expression, due to higher ambient background for surface proteins.

### Multiome (RNA + ATAC)
ATAC features are less noisy and slow down the run significantly (200k+ peaks). Options:
- Exclude ATAC: `--exclude-feature-types Peaks` (ATAC features pass through unchanged)
- Speed up ATAC: `--projected-ambient-count-threshold 2` (only analyze peaks with ≥2 estimated ambient counts)

### Multiple samples / batch processing
Run CellBender **separately per sample** before any integration. Do not merge samples before running CellBender. See `scripts/run_cellbender_batch.py` for automation.

---

## Integration with Downstream Tools

### scanpy pipeline
```python
import scanpy as sc
from cellbender.remove_background.downstream import load_anndata_from_input_and_output

# Load with both raw and CellBender layers
adata = load_anndata_from_input_and_output(
    input_file='raw_feature_bc_matrix.h5',
    output_file='cellbender_output_filtered.h5',
    input_layer_key='raw',
)

# Standard preprocessing on CellBender counts (adata.X)
sc.pp.filter_cells(adata, min_genes=200)
sc.pp.filter_genes(adata, min_cells=3)
adata = adata[adata.obs['pct_counts_mt'] < 20]  # filter dying cells
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000)

# Use CellBender embedding for neighbors (optional but recommended)
sc.pp.neighbors(adata, use_rep='cellbender_embedding')
sc.tl.umap(adata)
sc.tl.leiden(adata)
```

### Seurat pipeline
```r
# After ptrepack conversion (see above)
library(Seurat)
data <- Read10X_h5('cellbender_output_seurat.h5', use.names=TRUE)
obj <- CreateSeuratObject(counts=data, min.cells=3, min.features=200)
obj <- PercentageFeatureSet(obj, pattern="^MT-", col.name="percent.mt")
obj <- subset(obj, subset=percent.mt < 20)
obj <- NormalizeData(obj) %>% FindVariableFeatures() %>% ScaleData() %>% RunPCA()
```

### Harmony / batch integration
```python
# Run CellBender per sample, then integrate:
import scanpy as sc
import harmonypy as hm

# Load each sample's CellBender output
adatas = [sc.read_10x_h5(f'sample{i}_cellbender_filtered.h5') for i in range(n_samples)]
adata = sc.concat(adatas, label='sample')

# Standard preprocessing, then Harmony
sc.pp.normalize_total(adata); sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, batch_key='sample')
sc.pp.pca(adata)
sc.external.pp.harmony_integrate(adata, 'sample')
sc.pp.neighbors(adata, use_rep='X_pca_harmony')
sc.tl.umap(adata)
```

---

## Computational Requirements

| Dataset size | GPU | Runtime | RAM |
|---|---|---|---|
| ~5,000 cells (10x v3) | T4 (16GB) | ~30 min | ~8 GB |
| ~10,000 cells | T4 (16GB) | ~45 min | ~12 GB |
| ~50,000 cells | T4 (16GB) | ~2–3 hr | ~20 GB |
| CPU only (small dataset) | — | Hours | ~8 GB |

**GPU recommendation**: NVIDIA Tesla T4 (16GB VRAM). CellBender uses only 1 GPU.

If GPU OOM: reduce `--posterior-batch-size` to 64 (restart from `ckpt.tar.gz`).

---

## Citation

Fleming SJ, Chaffin MD, Arduini A, Akkad A-D, Banks E, Marioni JC, Phillipakis AA, Ellinor PT, Babadi M. Unsupervised removal of systematic background noise from droplet-based single-cell experiments using CellBender. *Nature Methods*, 2023. https://doi.org/10.1038/s41592-023-01943-7
