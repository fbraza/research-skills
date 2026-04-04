# Scaden Troubleshooting Guide

---

## Installation Issues

### `ModuleNotFoundError: No module named 'scaden'`
**Cause:** Scaden not installed or wrong Python environment active.
**Solution:**
```bash
pip install scaden
# Or check active environment:
which python
pip list | grep scaden
```

### `ModuleNotFoundError: No module named 'tensorflow'`
**Cause:** TensorFlow not installed (sometimes not auto-installed with scaden).
**Solution:**
```bash
pip install tensorflow          # CPU version
pip install tensorflow-gpu      # GPU version (requires CUDA)
```

### `ImportError: cannot import name 'xxx' from 'tensorflow'`
**Cause:** TensorFlow version incompatibility.
**Solution:**
```bash
pip install "tensorflow>=2.4,<2.12"
```

### `scaden: command not found`
**Cause:** Scaden installed but not in PATH.
**Solution:**
```bash
# Option 1: Use python -m
python -m scaden --help

# Option 2: Find and add to PATH
pip show scaden | grep Location
# Add <Location>/bin to PATH
```

---

## `scaden simulate` Issues

### `ValueError: No objects to concatenate`
**Cause:** No files found matching the `--pattern` in `--data` directory.
**Solution:**
```bash
# Check files exist
ls scrna_data/

# Ensure pattern includes *
scaden simulate --data scrna_data/ --pattern "*_counts.txt"
# NOT: --pattern "_counts.txt"  (missing *)
```

### `KeyError: 'Celltype'`
**Cause:** Cell type label file missing the required `Celltype` column.
**Solution:**
```python
import pandas as pd
labels = pd.read_csv("my_celltypes.txt", sep="\t")
print(labels.columns.tolist())  # Check column names

# Rename if needed
labels = labels.rename(columns={"cell_type": "Celltype", "CellType": "Celltype"})
labels.to_csv("my_celltypes.txt", sep="\t", index=False)
```

### `MemoryError` during simulation
**Cause:** Too many cells or samples requested.
**Solution:**
```bash
# Reduce cells per sample and/or number of samples
scaden simulate --data scrna_data/ -n 2000 --cells 200

# Or subsample scRNA-seq data first (in Python)
```
```python
import scanpy as sc
adata = sc.read_h5ad("scrna.h5ad")
sc.pp.subsample(adata, n_obs=5000)  # Keep 5,000 cells
```

### Simulation produces very few samples
**Cause:** scRNA-seq dataset has too few cells for the requested `--cells` per sample.
**Solution:** Reduce `--cells` to match your dataset size:
```bash
# If you have 500 cells, use --cells 50-100
scaden simulate --data scrna_data/ -n 1000 --cells 50
```

---

## `scaden process` Issues

### Very few overlapping genes (< 500)
**Cause:** Gene identifier mismatch between scRNA-seq and bulk data.
**Diagnosis:**
```python
import anndata as ad
import pandas as pd

# Check training data genes
train = ad.read_h5ad("data.h5ad")
print("Training genes (first 5):", train.var_names[:5].tolist())

# Check bulk data genes
bulk = pd.read_csv("bulk.txt", sep="\t", index_col=0)
print("Bulk genes (first 5):", bulk.index[:5].tolist())

# Check overlap
overlap = set(train.var_names) & set(bulk.index)
print(f"Overlapping genes: {len(overlap)}")
```

**Solutions:**
```python
# If one uses Ensembl IDs and other uses symbols, convert:
import mygene
mg = mygene.MyGeneInfo()

# Convert Ensembl to HGNC symbols
result = mg.querymany(ensembl_ids, scopes='ensembl.gene', fields='symbol', species='human')

# Or use gget
import gget
gget.setup("ensembl")
```

### `processed.h5ad` has 0 genes
**Cause:** Complete gene name mismatch (e.g., one dataset uses version suffixes like `ENSG00000001.5`).
**Solution:**
```python
# Strip version suffixes from Ensembl IDs
bulk.index = bulk.index.str.split('.').str[0]
bulk.to_csv("bulk_clean.txt", sep="\t")
```

### `ValueError: Input contains NaN`
**Cause:** Missing values in bulk expression file.
**Solution:**
```python
import pandas as pd
bulk = pd.read_csv("bulk.txt", sep="\t", index_col=0)
print(f"NaN values: {bulk.isna().sum().sum()}")
bulk = bulk.fillna(0)
bulk.to_csv("bulk_clean.txt", sep="\t")
```

---

## `scaden train` Issues

### Training loss not decreasing / stuck at high value
**Cause 1:** Data was pre-log-transformed before `scaden process`.
**Solution:** Re-run with raw or normalized (non-log) counts.

**Cause 2:** Too few training samples.
**Solution:** Increase `--n_samples` in `scaden simulate` to ≥2,000.

**Cause 3:** All cells are the same type (no diversity in training data).
**Solution:** Verify cell type labels are correct and diverse.

### `ResourceExhaustedError: OOM when allocating tensor`
**Cause:** GPU out of memory.
**Solution:**
```bash
# Reduce batch size
scaden train processed.h5ad --model_dir model/ --batch_size 64

# Or force CPU
CUDA_VISIBLE_DEVICES="" scaden train processed.h5ad --model_dir model/
```

### Training is very slow (>30 min for 5,000 steps)
**Cause:** Large number of genes or samples; no GPU.
**Solution:**
```bash
# Increase var_cutoff during processing to reduce gene count
scaden process data.h5ad bulk.txt --var_cutoff 0.5

# Or use GPU
pip install tensorflow-gpu
```

### `FileNotFoundError: model directory not found`
**Cause:** `--model_dir` path doesn't exist.
**Solution:**
```bash
mkdir -p scaden_model/
scaden train processed.h5ad --model_dir scaden_model/
```

---

## `scaden predict` Issues

### `FileNotFoundError: No such file or directory: 'M256'`
**Cause:** Model directory doesn't contain the expected subdirectories.
**Solution:**
```bash
# Check model directory contents
ls scaden_model/
# Should contain: M256/  M512/  M1024/

# If empty, re-run training
scaden train processed.h5ad --model_dir scaden_model/
```

### All predictions are near-uniform (e.g., all ~0.2 for 5 cell types)
**Cause 1:** Too few training steps.
**Solution:** Retrain with `--steps 5000`.

**Cause 2:** Very few overlapping genes between training and prediction data.
**Solution:** Check gene overlap (see `scaden process` issues above).

**Cause 3:** Bulk data is from a very different tissue than training data.
**Solution:** Use a tissue-matched scRNA-seq reference.

### Predictions don't sum to exactly 1.0
**Cause:** Normal floating-point behavior from Softmax output.
**Solution:** This is expected. Normalize if needed:
```python
import pandas as pd
preds = pd.read_csv("scaden_predictions.txt", sep="\t", index_col=0)
preds = preds.div(preds.sum(axis=1), axis=0)  # Row-normalize
```

### Cell type missing from predictions
**Cause:** Cell type was absent from training data (not in scRNA-seq reference).
**Solution:** Ensure all expected cell types are present in the scRNA-seq reference. Check:
```python
import anndata as ad
train = ad.read_h5ad("data.h5ad")
print("Cell types in training:", train.obs['Celltype'].unique().tolist())
```

### `ValueError: shapes do not match`
**Cause:** Bulk prediction file has different genes than what the model was trained on.
**Solution:** Always use the same bulk file for `scaden process` and `scaden predict`. The model is tied to the gene set used during processing.

---

## Data Format Issues

### Bulk file loading error
**Cause:** Incorrect file format (wrong separator, wrong orientation).
**Diagnosis:**
```python
import pandas as pd
# Check format
bulk = pd.read_csv("bulk.txt", sep="\t", index_col=0)
print(f"Shape: {bulk.shape}")  # Should be (n_genes, n_samples)
print(f"First rows:\n{bulk.head()}")
print(f"Index (genes): {bulk.index[:5].tolist()}")
print(f"Columns (samples): {bulk.columns[:5].tolist()}")
```

**Common fixes:**
```python
# If transposed (samples as rows, genes as columns)
bulk = bulk.T
bulk.to_csv("bulk_fixed.txt", sep="\t")

# If using comma separator
bulk = pd.read_csv("bulk.csv", sep=",", index_col=0)
bulk.to_csv("bulk.txt", sep="\t")
```

### scRNA-seq data already log-transformed
**Cause:** Input data was log-normalized before creating count/celltype files.
**Solution:** Reverse the log transformation:
```python
import numpy as np
import pandas as pd
counts = pd.read_csv("counts.txt", sep="\t", index_col=0)
counts_raw = np.expm1(counts)  # Reverse log1p
counts_raw.to_csv("counts_raw.txt", sep="\t")
```

---

## Performance Issues

### Scaden predictions are worse than CIBERSORT
**Likely causes and solutions:**

1. **Too few training samples**: Increase `--n_samples` to ≥5,000
2. **Wrong tissue reference**: Use scRNA-seq from the same tissue as bulk data
3. **Too few training steps**: Use `--steps 5000` (default)
4. **Gene mismatch**: Check overlapping genes (aim for >3,000)
5. **Pre-log-transformed input**: Re-run with raw/normalized (non-log) counts

### Scaden predicts high fractions for unexpected cell types
**Cause:** scRNA-seq reference contains cell types not present in bulk tissue, or cell type labels are incorrect.
**Solution:**
- Review and clean cell type annotations in scRNA-seq reference
- Remove cell types with very few cells (<50) from training data
- Check that "Unknown" or "Doublet" clusters are excluded from training
