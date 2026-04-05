---
name: scaden-deconvolution
description: "Estimate the cellular composition of bulk RNA-seq samples using Scaden, a deep neural network ensemble that learns to deconvolve tissue expression profiles. Scaden is trained on artificial bulk samples simulated from scRNA-seq data, making it reference-free (no GEP matrix required) and robust to batch effects and noise. The workflow covers four steps: scRNA-seq data simulation, data processing, model training, and prediction. Use when you have bulk RNA-seq data and a matching scRNA-seq reference dataset and want to estimate cell type fractions without constructing a gene expression profile (GEP) matrix. Outperforms CIBERSORT, MuSiC, and CIBERSORTx in precision and robustness across tissues, species, and data types."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
starting-prompt: Deconvolve cell type composition from my bulk RNA-seq data using Scaden.
---

# Cell Type Deconvolution (Scaden)

Estimate the cellular composition of bulk RNA-seq samples using Scaden — a deep neural network ensemble trained on simulated bulk data generated from scRNA-seq datasets. Scaden requires no hand-curated gene expression profile (GEP) matrix and is robust to batch effects, noise, and cross-species transfer.

## When to Use This Skill

Use Scaden when you need to:
- ✅ **Estimate cell type fractions** from bulk RNA-seq or microarray data
- ✅ **Avoid GEP matrix construction** — no marker gene selection required
- ✅ **Use scRNA-seq as reference** — any annotated scRNA-seq dataset from the same tissue
- ✅ **Leverage multiple scRNA-seq datasets** — Scaden can train on data from multiple donors/batches simultaneously
- ✅ **Deconvolve across species** — a mouse-trained model can deconvolve human data
- ✅ **Deconvolve across data types** — RNA-seq-trained model can deconvolve microarray data
- ✅ **Use pre-built training data** — ready-made datasets available for PBMC, brain, pancreas, ascites

**Don't use this skill for:**
- ❌ Single-cell RNA-seq data → Use clustering/annotation workflows instead
- ❌ No scRNA-seq reference available for your tissue → Use CIBERSORT with curated GEPs
- ❌ Spatial transcriptomics deconvolution → Use RCTD, SPOTlight, or cell2location
- ❌ Estimating cell-type-specific gene expression → Scaden predicts fractions only
- ❌ Very rare cell types (<1% expected fraction) → Low-abundance types are hard to recover

**Key Concept:** Scaden replaces the GEP matrix with a trained DNN. Instead of selecting marker genes, the network learns latent features from thousands of simulated bulk samples, making it inherently robust to noise and batch effects that confound linear regression methods.

**The Scaden Pipeline:**
1. **Simulate** (`scaden simulate`): Generate artificial bulk samples with known composition from scRNA-seq data
2. **Process** (`scaden process`): Align genes between training and prediction data; log2-transform and scale
3. **Train** (`scaden train`): Train an ensemble of 3 DNNs on simulated data (5,000 steps each)
4. **Predict** (`scaden predict`): Deconvolve bulk RNA-seq samples using the trained ensemble

## Quick Start

**Fastest way to test the workflow (~25 minutes on CPU):**

```python
# Step 1: Generate example data
from scripts.load_example_data import generate_example_data
paths = generate_example_data(out_dir="scaden_example/")

# Step 2: Run the complete pipeline
from scripts.run_full_workflow import run_full_scaden_workflow
results = run_full_scaden_workflow(
    scrna_data_dir="scaden_example/",
    bulk_file="scaden_example/example_bulk_data.txt",
    output_dir="scaden_results/",
    n_samples=1000,
    steps=5000
)

# Step 3: Plot and export
from scripts.plot_results import plot_deconvolution_results
from scripts.export_results import export_predictions
plot_deconvolution_results(results['predictions_file'], output_dir="scaden_results/plots/")
export_predictions(results['predictions_file'], output_dir="scaden_results/")
```

**Expected output:** `scaden_predictions.txt` with cell type fractions per sample, stacked bar chart, heatmap.

## Installation

### Required Software

| Software | Version | License | Commercial Use | Installation |
|----------|---------|---------|----------------|--------------|
| scaden | ≥1.1.2 | MIT | ✅ Permitted | `pip install scaden` |
| tensorflow | ≥2.x | Apache 2.0 | ✅ Permitted | Installed with scaden |
| anndata | ≥0.7 | BSD-3-Clause | ✅ Permitted | Installed with scaden |
| scanpy | ≥1.6 | BSD-3-Clause | ✅ Permitted | `pip install scanpy` |
| pandas | ≥1.2 | BSD-3-Clause | ✅ Permitted | `pip install pandas` |
| numpy | ≥1.20 | BSD-3-Clause | ✅ Permitted | `pip install numpy` |
| matplotlib | ≥3.3 | PSF-based | ✅ Permitted | `pip install matplotlib` |
| seaborn | ≥0.11 | BSD-3-Clause | ✅ Permitted | `pip install seaborn` |

**Minimum Python version:** Python ≥3.7

**Quick install:**
```bash
pip install scaden scanpy pandas numpy matplotlib seaborn
```

### GPU Support (Optional)

Scaden can use a GPU for ~3× faster training. Without GPU, training takes ~10 minutes on CPU (5,000 steps, 2,000 samples).

```bash
# For GPU support (TensorFlow-GPU)
pip install tensorflow-gpu
```

### Docker (Alternative)

```bash
# CPU container
docker pull ghcr.io/kevinmenden/scaden/scaden

# GPU container
docker pull ghcr.io/kevinmenden/scaden/scaden-gpu

# Run with Docker
docker run -v $(pwd):/data ghcr.io/kevinmenden/scaden/scaden scaden --help
```

### Web Tool (No Installation)

A browser-based tool is available at https://scaden.ims.bio with pre-built training datasets for several tissues. Upload your bulk expression file and download predictions directly.

## Inputs

### Required Inputs

**Option A — Use your own scRNA-seq reference:**

1. **scRNA-seq count matrix** (per dataset, tab-separated):
   - File: `<prefix>_counts.txt`
   - Shape: cells × genes (rows = cells, columns = genes)
   - Values: raw counts or library-size normalized (NOT log-transformed)
   - Gene names as column headers; cell barcodes as row index

2. **Cell type labels** (per dataset, tab-separated):
   - File: `<prefix>_celltypes.txt`
   - Shape: cells × 1 (must have a column named exactly `Celltype`)
   - One row per cell, same order as count matrix

3. **Bulk RNA-seq prediction file** (tab-separated):
   - Shape: genes × samples (rows = genes, columns = samples)
   - Leave the gene column header empty (just `\t`)
   - Values: raw counts or normalized (NOT log-transformed)
   - Gene names must overlap with scRNA-seq data

**Option B — Use a pre-built training dataset:**

Download a pre-built `.h5ad` training file (see [references/datasets-guide.md](references/datasets-guide.md)) and skip directly to the `scaden process` step.

**Option C — Use AnnData format (v1.1.0+):**

scRNA-seq data can also be provided as `.h5ad` files where `adata.obs` contains a `Celltype` column.

### Data Requirements

| Parameter | Minimum | Recommended |
|-----------|---------|-------------|
| Cells per scRNA-seq dataset | 500 | 2,000+ |
| Simulated training samples | 1,000 | 5,000–30,000 |
| Cells per simulated sample | 100 | 500 (default) |
| Training steps | 2,000 | 5,000 (default) |
| RAM | 8 GB | 16 GB |
| Gene overlap (train vs bulk) | 1,000 | 5,000+ |

### Important Data Notes

- **Do NOT log-transform** input data — Scaden applies log2(x+1) internally during `scaden process`
- **Gene naming**: Ensure consistent gene identifiers between scRNA-seq and bulk data (both HGNC symbols, or both Ensembl IDs)
- **Multiple datasets**: Store all scRNA-seq datasets in the same directory with a consistent naming pattern (e.g., `*_counts.txt`)
- **Multi-donor data**: Split by donor and generate separate count/celltype files per donor — Scaden learns inter-subject heterogeneity this way

## Outputs

### Files Generated

**Predictions:**
- `scaden_predictions.txt` — Main output: samples × cell types, values are predicted fractions (sum to 1 per sample)
  - Load with: `pd.read_csv('scaden_predictions.txt', sep='\t', index_col=0)`

**Intermediate files:**
- `data.h5ad` — Simulated training data (output of `scaden simulate`)
- `processed.h5ad` — Gene-aligned, log2-transformed, scaled training data (output of `scaden process`)
- `model/` — Trained model weights directory (3 sub-models: M256, M512, M1024)

**Visualizations (from scripts):**
- `stacked_bar.png/.svg` — Cell type fractions per sample as stacked bar chart
- `fraction_heatmap.png/.svg` — Heatmap of cell type fractions across samples
- `cell_type_boxplot.png/.svg` — Distribution of each cell type fraction across samples

**Exports (from scripts):**
- `predictions_long.csv` — Long-format predictions (sample, cell_type, fraction)
- `predictions_summary.csv` — Mean ± SD per cell type across all samples
- `top_cell_types.csv` — Ranked cell types by mean fraction

## Clarification Questions

**Before running, confirm:**

1. **Input data** (ASK THIS FIRST):
   - Do you have bulk RNA-seq data to deconvolve?
   - Do you have a matching scRNA-seq reference dataset for the same tissue?
   - Or would you like to use a pre-built training dataset (PBMC, brain, pancreas, ascites)?

2. **Tissue type?**
   - Blood/PBMC → Pre-built dataset available (32,000 samples, 4 datasets)
   - Brain → Pre-built dataset available (mouse, 30,000 samples)
   - Pancreas → Pre-built dataset available (12,000 samples)
   - Ascites → Pre-built dataset available (6,000 samples)
   - Other → Must simulate from your own scRNA-seq data

3. **Gene identifier format?**
   - HGNC symbols (e.g., CD3E, PTPRC) — most common for human
   - Ensembl IDs (e.g., ENSG00000...) — ensure consistency between datasets
   - MGI symbols — for mouse data

4. **Number of bulk samples to deconvolve?**
   - <100 samples → Standard workflow, ~8 seconds prediction time
   - 100–1,000 samples → Standard workflow, seconds to minutes
   - >1,000 samples → Standard workflow, prediction scales linearly

5. **Computational resources?**
   - CPU only → ~10 min training (5,000 steps, 2,000 samples); GPU gives ~3× speedup
   - GPU available → Install `tensorflow-gpu` for faster training

## Standard Workflow

🚨 **MANDATORY: SCRIPTS ARE TEMPLATES — COPY TO PROJECT WORKING DIRECTORY, THEN ADAPT TO STUDY** 🚨

---

### Step 0 — Prepare scRNA-seq data (skip if using pre-built dataset)

```python
# Prepare your scRNA-seq data into Scaden-compatible format
from scripts.prepare_scrna_data import prepare_scrna_for_scaden

prepare_scrna_for_scaden(
    adata_path="my_scrna.h5ad",          # AnnData with raw counts
    celltype_column="cell_type",          # Column in adata.obs with cell type labels
    output_dir="scaden_input/",
    prefix="my_tissue",                   # Output: my_tissue_counts.txt + my_tissue_celltypes.txt
    split_by_donor=True,                  # Recommended: split by donor for multi-subject data
    donor_column="donor_id"               # Column in adata.obs with donor IDs
)
```

**✅ VERIFICATION:** You should see:
- `"✓ Saved X cells × Y genes to my_tissue_counts.txt"`
- `"✓ Saved cell type labels to my_tissue_celltypes.txt"`
- `"✓ Cell types found: [list of cell types]"`

---

### Step 1 — Simulate training data

```python
from scripts.run_simulate import run_scaden_simulate

run_scaden_simulate(
    data_dir="scaden_input/",
    output_dir="scaden_training/",
    n_samples=5000,          # Number of artificial bulk samples to generate
    cells_per_sample=500,    # Cells aggregated per simulated sample
    pattern="*_counts.txt",  # Pattern to find count files
    prefix="data"            # Output: data.h5ad
)
```

**✅ VERIFICATION:** You should see:
- `"✓ Simulation complete: 5000 samples generated"`
- `"✓ Training file saved: scaden_training/data.h5ad"`
- `"✓ Cell types in training data: [list]"`

**Decision point — How many samples to simulate?**

| Dataset size | Recommended n_samples | Notes |
|---|---|---|
| Small scRNA-seq (<2,000 cells) | 1,000–2,000 | More samples won't help much |
| Medium (2,000–10,000 cells) | 5,000–10,000 | Good balance |
| Large (>10,000 cells) | 10,000–30,000 | Diminishing returns above ~15,000 |
| Pre-built datasets | N/A | Already simulated |

---

### Step 2 — Process data

```python
from scripts.run_process import run_scaden_process

run_scaden_process(
    training_data="scaden_training/data.h5ad",
    prediction_data="bulk_expression.txt",   # Your bulk RNA-seq file
    output_dir="scaden_training/",
    output_name="processed.h5ad"             # Default name
)
```

**✅ VERIFICATION:** You should see:
- `"✓ Processing complete"`
- `"✓ Genes in training data: X"`
- `"✓ Genes in bulk data: Y"`
- `"✓ Overlapping genes used for training: Z"` ← Z should be >1,000

⚠️ **If Z < 1,000 overlapping genes**: Check that gene identifiers match between scRNA-seq and bulk data (both HGNC symbols, or both Ensembl IDs). See [references/troubleshooting.md](references/troubleshooting.md).

---

### Step 3 — Train model

```python
from scripts.run_train import run_scaden_train

run_scaden_train(
    processed_data="scaden_training/processed.h5ad",
    model_dir="scaden_model/",
    steps=5000,       # Default: 5,000 steps per model (3 models total)
    batch_size=128    # Default batch size
)
```

**✅ VERIFICATION:** You should see:
- `"Training model M256..."`, `"Training model M512..."`, `"Training model M1024..."`
- `"✓ Training complete. Model saved to scaden_model/"`
- Three subdirectories in `scaden_model/`: `M256/`, `M512/`, `M1024/`

**Decision point — How many training steps?**

| Scenario | Steps | Notes |
|---|---|---|
| Quick test | 1,000–2,000 | Faster, lower accuracy |
| Standard (recommended) | 5,000 | Default; good for ~30,000 samples |
| Large dataset (>15,000 samples) | 5,000–10,000 | More steps may help |
| Avoid overfitting | ≤5,000 | Models overfit on simulated data if trained too long |

---

### Step 4 — Predict cell type fractions

```python
from scripts.run_predict import run_scaden_predict

run_scaden_predict(
    bulk_file="bulk_expression.txt",
    model_dir="scaden_model/",
    output_dir="scaden_results/",
    output_name="scaden_predictions.txt"
)
```

**✅ VERIFICATION:** You should see:
- `"✓ Prediction complete"`
- `"✓ Predictions saved to scaden_results/scaden_predictions.txt"`
- `"✓ Samples deconvolved: N"`
- `"✓ Cell types predicted: [list]"`

---

### Step 5 — Visualize and export results

```python
from scripts.plot_results import plot_deconvolution_results
from scripts.export_results import export_predictions

# Generate all plots
plot_deconvolution_results(
    predictions_file="scaden_results/scaden_predictions.txt",
    output_dir="scaden_results/plots/",
    metadata_file=None    # Optional: path to sample metadata TSV for grouping
)

# Export clean tables
export_predictions(
    predictions_file="scaden_results/scaden_predictions.txt",
    output_dir="scaden_results/"
)
```

**✅ VERIFICATION:** You should see:
- `"✓ Stacked bar chart saved"`
- `"✓ Fraction heatmap saved"`
- `"✓ Cell type boxplot saved"`
- `"✓ Long-format predictions exported"`
- `"✓ Summary statistics exported"`

---

⚠️ **CRITICAL — DO NOT:**
- ❌ **Log-transform input data before running** → Scaden applies log2(x+1) internally in `scaden process`
- ❌ **Mix gene identifier types** → Ensure scRNA-seq and bulk data use the same gene naming convention

**⚠️ IF SCRIPTS FAIL — Script Failure Hierarchy:**
1. **Fix and Retry (90%)** — Install missing package, re-run script
2. **Modify Script (5%)** — Edit the script file itself, document changes
3. **Use as Reference (4%)** — Read script, adapt approach, cite source
4. **Write from Scratch (1%)** — Only if genuinely impossible, explain why

**NEVER skip directly to writing inline code without trying the script first.**

## Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| **Very few overlapping genes (<500)** | Gene ID mismatch between scRNA-seq and bulk | Ensure both use HGNC symbols (or both Ensembl IDs); check for version mismatches |
| **`KeyError: 'Celltype'`** | Cell type label file missing required column | Rename your cell type column to exactly `Celltype` (capital C) |
| **`ValueError: No objects to concatenate`** | No files found matching pattern | Check `--pattern` includes `*`; verify files exist in `--data` directory |
| **Memory error during simulation** | Too many cells or samples | Reduce `--n_samples` or `--cells`; subsample scRNA-seq to 5,000–10,000 cells |
| **Training loss not decreasing** | Learning rate or batch size issue | Use default parameters (lr=0.0001, batch=128); check data is not pre-log-transformed |
| **All predictions near uniform fractions** | Too few training steps or samples | Increase `--steps` to 5,000; increase `--n_samples` to ≥2,000 |
| **`ModuleNotFoundError: tensorflow`** | TensorFlow not installed | `pip install tensorflow` (CPU) or `pip install tensorflow-gpu` (GPU) |
| **Predictions don't sum to 1** | Normal floating point behavior | Values sum to ~1.0 within floating point tolerance; normalize if needed |
| **Cell type missing from predictions** | Cell type absent from training data | Ensure all expected cell types are present in scRNA-seq reference |
| **`scaden: command not found`** | Scaden not in PATH | Activate conda environment or use `python -m scaden` |
| **Slow training on CPU** | No GPU available | Normal; CPU training takes ~10 min for 5,000 steps. Use GPU or Docker GPU image for speedup |

## Suggested Next Steps

After completing Scaden deconvolution:

1. **Validate predictions**: If ground-truth fractions are available (e.g., flow cytometry), compute CCC and RMSE
2. **Differential composition analysis**: Compare cell type fractions between conditions using linear models or Wilcoxon tests
3. **Correlation with clinical variables**: Correlate predicted fractions with survival, disease stage, treatment response
4. **Cell-type-specific expression**: Use predicted fractions with PSEA or CIBERSORTx to infer cell-type-specific gene expression
5. **Visualization**: Generate UMAP of samples colored by dominant cell type; stacked bar charts per group
6. **Integration with DEG analysis**: Regress out cell type composition before differential expression to isolate intrinsic expression changes

## Related Skills

- **scrnaseq-scanpy-core-analysis** — Upstream: Preprocessing and annotating the scRNA-seq reference
- **scrnaseq-seurat-core-analysis** — Upstream: Alternative scRNA-seq preprocessing (R)
- **bulk-rnaseq-counts-to-de-deseq2** — Related: Differential expression on the same bulk data
- **functional-enrichment-from-degs** — Downstream: Pathway analysis after composition-corrected DEG
- **survival-analysis-clinical** — Downstream: Correlate cell type fractions with clinical outcomes

## References

- Menden et al. (2020). Deep learning–based cell composition analysis from tissue expression profiles. *Science Advances*, 6(30), eaba2619. [doi:10.1126/sciadv.aba2619](https://doi.org/10.1126/sciadv.aba2619)
- Scaden Documentation: https://scaden.readthedocs.io/
- Scaden GitHub: https://github.com/KevinMenden/scaden
- Scaden Web Tool: https://scaden.ims.bio
