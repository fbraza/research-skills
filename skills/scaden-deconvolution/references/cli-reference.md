# Scaden CLI Reference

Full command-line reference for Scaden v1.1.2. All commands follow the pattern:
```
scaden <command> [OPTIONS] [ARGUMENTS]
```

---

## `scaden example`

Generate example data files to test the full pipeline.

```bash
scaden example [--out OUT_DIR]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--out` | path | `.` (current dir) | Directory to write example files |

**Output files:**
- `example_counts.txt` — Example scRNA-seq count matrix (cells × genes)
- `example_celltypes.txt` — Example cell type labels (cells × 1, column: `Celltype`)
- `example_bulk_data.txt` — Example bulk RNA-seq file (genes × samples)

**Usage:**
```bash
mkdir example_data
scaden example --out example_data/
```

---

## `scaden simulate`

Generate artificial bulk RNA-seq training samples from scRNA-seq data.

```bash
scaden simulate --data DATA_DIR [OPTIONS]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--data` | path | **required** | Directory containing scRNA-seq count and celltype files |
| `--pattern` | str | `"*_counts.txt"` | Glob pattern to find count files (must include `*`) |
| `-n`, `--n_samples` | int | `1000` | Number of artificial bulk samples to generate |
| `--cells` | int | `100` | Number of cells per simulated sample |
| `--out` | path | `.` | Output directory for `.h5ad` training file |
| `--prefix` | str | `"data"` | Prefix for output file (produces `<prefix>.h5ad`) |
| `--fmt` | str | `"txt"` | Input format: `"txt"` or `"h5ad"` |

**File naming convention (required):**
- Count matrix: `<prefix>_counts.txt`
- Cell type labels: `<prefix>_celltypes.txt`

**Example:**
```bash
# Single dataset
scaden simulate --data scrna_data/ --pattern "*_counts.txt" -n 5000 --cells 500 --out training/ --prefix data

# Multiple datasets (all matching pattern in same directory)
scaden simulate --data scrna_data/ --pattern "*_counts.txt" -n 10000 --out training/
```

**Output:** `<out>/<prefix>.h5ad` — AnnData file with simulated bulk samples and ground-truth fractions

**Notes:**
- Cells from different datasets are NOT merged into the same simulated sample (preserves within-subject relationships)
- For multi-donor data: split by donor, name files `donor1_counts.txt`, `donor1_celltypes.txt`, etc.
- Recommended `--cells 500` for best performance (matches paper benchmark)
- Increasing `--n_samples` beyond ~15,000 gives diminishing returns

---

## `scaden process`

Pre-process training data: align genes with bulk data, log2-transform, and scale to [0,1].

```bash
scaden process TRAINING_DATA PREDICTION_DATA [OPTIONS]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `TRAINING_DATA` | path | **required** | Path to `.h5ad` training file (from `scaden simulate`) |
| `PREDICTION_DATA` | path | **required** | Path to bulk RNA-seq file to deconvolve |
| `--processed_path` | path | `"processed.h5ad"` | Output path for processed training file |
| `--var_cutoff` | float | `0.1` | Remove genes with variance below this threshold |

**What this step does:**
1. Finds the intersection of genes between training data and bulk data
2. Removes uninformative genes (zero expression or variance < `--var_cutoff`)
3. Applies log2(x+1) transformation
4. Scales each sample to [0,1] using MinMaxScaler (per-sample, not per-gene)

**Example:**
```bash
scaden process training/data.h5ad bulk_expression.txt --processed_path training/processed.h5ad
```

**Output:** `processed.h5ad` — Gene-filtered, log2-transformed, scaled training data

**Notes:**
- ⚠️ Do NOT pre-log-transform your input data — this step applies log2 internally
- The bulk prediction file is used ONLY to determine the gene intersection; it is not modified
- Aim for >1,000 overlapping genes; <500 indicates a gene naming mismatch

---

## `scaden train`

Train the Scaden ensemble of 3 deep neural networks on processed training data.

```bash
scaden train PROCESSED_DATA [OPTIONS]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `PROCESSED_DATA` | path | **required** | Path to processed `.h5ad` file (from `scaden process`) |
| `--model_dir` | path | `.` | Directory to save trained model weights |
| `--steps` | int | `5000` | Training steps per model (3 models trained independently) |
| `--batch_size` | int | `128` | Mini-batch size for Adam optimizer |
| `--learning_rate` | float | `0.0001` | Adam optimizer learning rate |
| `--seed` | int | `None` | Random seed for reproducibility |

**Ensemble architecture (fixed):**
| Model | Hidden layers | Dropout |
|-------|--------------|---------|
| M256 | 256-128-64-32 | No |
| M512 | 512-256-128-64 | Yes (0.5) |
| M1024 | 1024-512-256-128 | Yes (0.5) |

All models use: ReLU activations, Softmax output, L1 loss, Adam optimizer.

**Example:**
```bash
scaden train training/processed.h5ad --model_dir scaden_model/ --steps 5000
```

**Output:** Three model subdirectories in `--model_dir`: `M256/`, `M512/`, `M1024/`

**Notes:**
- Training 5,000 steps takes ~10 min on CPU, ~3 min on GPU
- Do NOT train for >5,000 steps on simulated data — models overfit and performance on real bulk data decreases
- The `--seed` parameter ensures reproducible training across runs

---

## `scaden predict`

Deconvolve bulk RNA-seq samples using a trained Scaden ensemble.

```bash
scaden predict PREDICTION_FILE [OPTIONS]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `PREDICTION_FILE` | path | **required** | Bulk RNA-seq file to deconvolve (genes × samples) |
| `--model_dir` | path | `.` | Directory containing trained model weights |
| `--outname` | path | `"scaden_predictions.txt"` | Output file path for predictions |
| `--seed` | int | `None` | Random seed |

**Example:**
```bash
scaden predict bulk_expression.txt --model_dir scaden_model/ --outname results/scaden_predictions.txt
```

**Output:** Tab-separated file (samples × cell types) with predicted fractions (values 0–1, sum to ~1 per row)

**Notes:**
- Prediction is very fast: ~8 seconds for 500 samples
- The bulk file is log2-transformed and scaled internally before prediction
- Predictions are the average of the 3 ensemble model outputs

---

## `scaden merge`

Merge multiple `.h5ad` training files into one (v1.1.0+).

```bash
scaden merge [OPTIONS]
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--data` | path | None | Directory of `.h5ad` files to merge |
| `--files` | str | None | Comma-separated list of `.h5ad` files to merge |
| `--out` | path | `"merged.h5ad"` | Output merged file path |

**Example:**
```bash
# Merge all h5ad files in a directory
scaden merge --data training_datasets/ --out merged_training.h5ad

# Merge specific files
scaden merge --files dataset1.h5ad,dataset2.h5ad,dataset3.h5ad --out merged.h5ad
```

---

## Bulk Expression File Format

The prediction file (bulk RNA-seq) must be tab-separated with this exact format:

```
\tsample1\tsample2\tsample3
GENE1\t12.5\t8.3\t15.1
GENE2\t0.0\t2.1\t0.5
...
```

- **Row 1**: Header — empty first cell, then sample names
- **Rows 2+**: Gene name (first column), then expression values
- **Values**: Raw counts or normalized (NOT log-transformed)
- **Gene names**: Must match the scRNA-seq reference (same identifier type)

**Load in Python:**
```python
import pandas as pd
bulk = pd.read_csv("bulk_expression.txt", sep="\t", index_col=0)
# bulk.shape = (n_genes, n_samples)
```

---

## scRNA-seq Count File Format

```
\tGENE1\tGENE2\tGENE3
CELL1\t5\t0\t12
CELL2\t0\t3\t8
...
```

- **Row 1**: Header — empty first cell, then gene names
- **Rows 2+**: Cell barcode (first column), then count values
- **Values**: Raw counts or library-size normalized (NOT log-transformed)

## Cell Type Label File Format

```
Celltype
T cell
B cell
T cell
Monocyte
...
```

- **Column name**: Must be exactly `Celltype` (capital C)
- **One row per cell**, same order as count matrix
- Additional columns are allowed but ignored

---

## Performance Benchmarks (from paper)

| Task | Hardware | Time | Memory |
|------|----------|------|--------|
| Simulate 2,000 samples | Intel Xeon 6-core CPU | 13 min | 8 GB peak |
| Train (5,000 steps) | Intel Xeon 6-core CPU | ~11 min | <1 GB |
| Train (5,000 steps) | GeForce RTX 2060 GPU | ~3 min | <1 GB |
| Predict 500 samples | Any CPU | ~8 sec | <1 GB |
| Full demo pipeline | Intel Xeon 6-core CPU | ~22 min | 8 GB peak |
