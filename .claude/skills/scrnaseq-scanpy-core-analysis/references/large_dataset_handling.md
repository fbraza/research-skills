# Large Dataset Handling

Guide for working with single-cell datasets that exceed available RAM, require streaming access,
or involve concatenating many samples before analysis.

## When to Apply This Guide

| Situation | Strategy |
|-----------|----------|
| Single h5ad file > 2 GB or > 50k cells | Backed mode |
| Multiple samples to merge before analysis | `concat_on_disk` or `AnnCollection` |
| File stored on S3 / cloud | Zarr format |
| Per-cell or per-gene statistics on large matrix | Chunked processing |
| File write/read is slow | Memory optimization (sparse + categorical) |

---

## 1. Backed Mode

Backed mode keeps the expression matrix (`X`) on disk and loads data only when explicitly
accessed. Observation and variable metadata are always loaded into RAM (they are small).

### Read-only (inspect or filter without modifying)

```python
import anndata as ad

# Open without loading X
adata = ad.read_h5ad('large_dataset.h5ad', backed='r')

# Safe to inspect metadata immediately
print(f"Dataset: {adata.n_obs} cells × {adata.n_vars} genes")
print(adata.obs.columns.tolist())
print(adata.var.columns.tolist())

# Filter based on metadata — no X is loaded
high_quality = adata[adata.obs['quality_score'] > 0.8]

# Load only the filtered subset into memory
adata_memory = high_quality.to_memory()
```

### Read-write (add metadata columns without loading X)

```python
# Open in read-write backed mode
adata = ad.read_h5ad('data.h5ad', backed='r+')

# Add or modify obs/var columns — written to disk immediately
adata.obs['new_annotation'] = values

# X remains on disk; no full load needed
```

### Limitations of backed mode

- `adata.X` cannot be assigned in `'r'` mode — open with `'r+'` for that
- Some scanpy functions require X in memory — call `.to_memory()` first
- Cannot concatenate backed objects directly — use `concat_on_disk` instead (see below)
- After filtering, always call `.to_memory()` before passing to scanpy preprocessing

---

## 2. Multi-Sample Concatenation

### concat_on_disk — for datasets that won't fit in RAM

Concatenates h5ad files without loading them into memory. Result is written directly to disk.

```python
from anndata.experimental import concat_on_disk

# Concatenate without loading into memory
concat_on_disk(
    in_files=['sample1.h5ad', 'sample2.h5ad', 'sample3.h5ad'],
    out_file='combined.h5ad',
    join='inner',          # 'inner' = shared genes only; 'outer' = all genes (fills 0s)
    label='sample',        # Column name added to obs
    keys=['S1', 'S2', 'S3']  # Values for the label column
)

# Load result in backed mode for further filtering
adata = ad.read_h5ad('combined.h5ad', backed='r')
adata_filtered = adata[adata.obs['quality_score'] > 0.8].to_memory()
```

**Join type guidance:**
- `inner`: Use when samples were processed with the same genome annotation — safest default
- `outer`: Use when samples have slightly different feature sets (fills missing genes with 0)

### AnnCollection — lazy view across multiple files

Provides a unified interface across files without loading X. Useful for iterating or
inspecting a cohort before deciding how much to load.

```python
from anndata.experimental import AnnCollection

files = ['sample1.h5ad', 'sample2.h5ad', 'sample3.h5ad']
collection = AnnCollection(
    files,
    join_obs='outer',    # How to handle obs metadata mismatches
    join_vars='inner',   # Keep only shared genes
    label='dataset',
    keys=['S1', 'S2', 'S3']
)

# Inspect without loading X
print(f"Total cells: {collection.n_obs}")
print(collection.obs['cell_type'].value_counts())

# Subset lazily
t_cells = collection[collection.obs['cell_type'] == 'T cell']

# Convert to AnnData when ready (loads all data)
adata = t_cells.to_adata()
```

### Standard in-memory concatenation (for datasets that fit in RAM)

Use when all samples fit comfortably in memory after loading individually.

```python
import anndata as ad

adatas = {
    'S1': ad.read_h5ad('sample1.h5ad'),
    'S2': ad.read_h5ad('sample2.h5ad'),
    'S3': ad.read_h5ad('sample3.h5ad'),
}

adata = ad.concat(
    adatas,
    axis=0,
    join='inner',
    label='sample',        # Creates obs['sample'] column
    index_unique='_'       # Appends sample key to barcodes to ensure uniqueness
)

print(adata.obs['sample'].value_counts())
```

**Always verify after concatenation:**

```python
# Check dimensions
print(adata.shape)

# Check sample balance
print(adata.obs['sample'].value_counts())

# Check no duplicate barcodes
assert adata.obs_names.is_unique, "Duplicate barcodes after concat — use index_unique"

# Check gene metadata integrity
print(adata.var.head())
```

---

## 3. Chunked Processing

For computing per-cell or per-gene statistics on a large matrix without loading it entirely.

```python
import numpy as np
import anndata as ad

adata = ad.read_h5ad('huge_dataset.h5ad', backed='r')
chunk_size = 1000

per_cell_means = []
for i in range(0, adata.n_obs, chunk_size):
    chunk = adata[i:i + chunk_size, :].to_memory()
    per_cell_means.append(np.array(chunk.X.mean(axis=1)).flatten())

per_cell_means = np.concatenate(per_cell_means)

# Or use the built-in chunked X iterator (anndata ≥0.10)
results = []
for chunk in adata.chunked_X(chunk_size=1000):
    results.append(chunk.mean(axis=1))
```

---

## 4. Memory Optimization

Apply before writing to disk or when RAM is tight.

```python
import anndata as ad
import numpy as np
from scipy.sparse import csr_matrix, issparse

def optimize_anndata_memory(adata):
    """Convert to sparse + categorical to minimize memory footprint."""
    # 1. Convert to sparse if >50% zeros
    if not issparse(adata.X):
        density = np.count_nonzero(adata.X) / adata.X.size
        if density < 0.5:
            adata.X = csr_matrix(adata.X)
            print(f"Converted X to sparse (density={density:.1%})")

    # 2. Convert string columns to categoricals
    adata.strings_to_categoricals()

    # 3. Downcast float64 to float32 in layers if possible
    for key in adata.layers:
        if hasattr(adata.layers[key], 'dtype') and adata.layers[key].dtype == np.float64:
            adata.layers[key] = adata.layers[key].astype(np.float32)
            print(f"Downcast layers['{key}'] float64 → float32")

    return adata

# Usage
adata = optimize_anndata_memory(adata)
adata.write_h5ad('optimized.h5ad', compression='gzip')
```

---

## 5. Storage Formats

| Format | Best for | How to write | How to read |
|--------|----------|--------------|-------------|
| **h5ad** | Default; fast random access; backed mode | `adata.write_h5ad('f.h5ad', compression='gzip')` | `ad.read_h5ad('f.h5ad')` |
| **Zarr** | Cloud (S3/GCS); parallel I/O | `adata.write_zarr('f.zarr', chunks=(1000, 1000))` | `ad.read_zarr('f.zarr')` |
| **CSV** | Sharing with non-Python tools; small data | `adata.write_csvs('dir/')` | `ad.read_csv('data.csv')` |

### Zarr for cloud access

```python
import fsspec

# Read directly from S3 (no local download)
store = fsspec.get_mapper('s3://my-bucket/data.zarr')
adata = ad.read_zarr(store)

# Write to S3
store = fsspec.get_mapper('s3://my-bucket/output.zarr')
adata.write_zarr(store, chunks=(1000, 1000))
```

---

## 6. Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Modifying a view | `ImplicitModificationWarning` | Call `.copy()` on the subset before modifying |
| Index misalignment when merging metadata | Wrong values silently assigned | `external_df.set_index('cell_id').loc[adata.obs_names, col]` |
| Duplicate barcodes after concat | `assert` fails downstream | Use `index_unique='_'` in `ad.concat()` |
| Loading backed object before scanpy step | `NotImplementedError` | Call `.to_memory()` before `sc.pp.*` functions |
| Sparse × dense operation inflates memory | OOM during normalization | Check `issparse(adata.X)` and use sparse-safe ops |

---

## Related Scripts

- [large_dataset_utils.py](../scripts/large_dataset_utils.py) — ready-to-use functions for all strategies above

## References

- AnnData documentation: https://anndata.readthedocs.io/
- `concat_on_disk` API: https://anndata.readthedocs.io/en/latest/generated/anndata.experimental.concat_on_disk.html
- `AnnCollection` API: https://anndata.readthedocs.io/en/latest/generated/anndata.experimental.AnnCollection.html
