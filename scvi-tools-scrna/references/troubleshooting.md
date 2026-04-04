# Troubleshooting Guide

## 1. Training Issues

### NaN Loss During Training
- **Cause:** Zero-variance genes, extreme outlier values, learning rate too high
- **Fix:** Filter genes with min_counts=3, check for NaN/Inf in count matrix, try reducing learning rate (lr=5e-4)
- **Diagnostic:** `np.isnan(adata.X.data).any()` or `(adata.layers['counts'].data < 0).any()`

```python
# Check for data issues
import numpy as np
assert not np.isnan(adata.layers['counts'].data).any(), "NaN values in counts"
assert not (adata.layers['counts'].data < 0).any(), "Negative values in counts"

# Reduce learning rate if NaN loss occurs
model.train(max_epochs=400, lr=5e-4)

# Use more stable likelihood
model = scvi.model.SCVI(adata, gene_likelihood="nb")
```

### ELBO Not Converging
- **Cause:** Insufficient epochs, data not properly registered, too few cells
- **Fix:** Increase max_epochs to 500-800, verify setup_anndata was called correctly, check adata.uns['_scvi']
- **Diagnostic:** Plot training curves — should show smooth decrease

```python
# Verify registration
print(adata.uns.get('_scvi', 'NOT REGISTERED'))

# Train longer with more capacity
model = scvi.model.SCVI(adata, n_hidden=256, n_layers=2)
model.train(max_epochs=600)

# Inspect training history
import matplotlib.pyplot as plt
train_elbo = model.history["elbo_train"]
plt.plot(train_elbo)
plt.xlabel("Epoch")
plt.ylabel("ELBO")
plt.title("Training curve — should decrease smoothly")
plt.show()
```

### Slow Training
- **Cause:** No GPU, large dataset, too many genes
- **Fix:** Use GPU (accelerator="gpu"), reduce to HVGs (2000-4000), increase batch_size
- **Diagnostic:** Check accelerator availability before training

```python
import torch

# Check available accelerator
print("CUDA available:", torch.cuda.is_available())
print("MPS available:", torch.backends.mps.is_available())

# Train with GPU acceleration
model.train(max_epochs=400, accelerator="gpu")

# Or on Apple Silicon
model.train(max_epochs=400, accelerator="mps")

# Increase batch size for throughput
model.train(max_epochs=400, batch_size=512)
```

---

## 2. Data Issues

### "Layer 'counts' not found"
- **Cause:** Raw counts not stored in expected location
- **Fix:** `adata.layers['counts'] = adata.X.copy()` before normalization, or pass `layer=None` if X has counts

```python
# Store raw counts before any normalization
adata.layers['counts'] = adata.X.copy()

# Then normalize adata.X for other analyses
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)

# Register with the correct layer
scvi.model.SCVI.setup_anndata(adata, layer="counts", batch_key="batch")
```

### Gene Filtering Problems
- **Cause:** Too aggressive or too lenient gene filtering
- **Fix:** Use min_counts=3 for gene filtering, select 2000-4000 HVGs with batch-aware selection

```python
# Recommended gene filtering
sc.pp.filter_genes(adata, min_counts=3)

# Batch-aware HVG selection (critical for multi-batch data)
sc.pp.highly_variable_genes(
    adata,
    n_top_genes=3000,
    subset=True,
    layer="counts",
    flavor="seurat_v3",
    batch_key="batch"  # Ensures HVGs are consistent across batches
)
```

### Wrong Data Type
- **Cause:** Passing normalized/log-transformed data instead of raw counts
- **Fix:** Check `adata.layers['counts']` contains integers (or near-integers for ambient RNA corrected data)
- **Diagnostic:** `np.allclose(adata.layers['counts'].data, np.round(adata.layers['counts'].data))`

```python
import numpy as np
import scipy.sparse as sp

layer = adata.layers['counts']
if sp.issparse(layer):
    data = layer.data
else:
    data = layer.flatten()

# Check for integer-like values (allows small float deviation from SoupX/CellBender)
is_integer_like = np.allclose(data, np.round(data), atol=0.1)
print(f"Counts appear integer-like: {is_integer_like}")

if not is_integer_like:
    print("WARNING: counts may be normalized or log-transformed — scVI requires raw counts")
    print(f"  min={data.min():.3f}, max={data.max():.3f}, mean={data.mean():.3f}")
```

### Duplicate Cell Barcodes
- **Cause:** Merging datasets without resetting index
- **Fix:** Reset obs_names after concatenation

```python
# Check for duplicates
n_dups = adata.obs_names.duplicated().sum()
print(f"Duplicate barcodes: {n_dups}")

# Fix by making barcodes unique
adata.obs_names_make_unique()

# Better: use index_unique when concatenating
adata = sc.concat([adata1, adata2], index_unique="-")
```

---

## 3. Model-Specific Issues

### scVI: Poor Batch Mixing
- **Cause:** Batch key not registered, insufficient latent dims, overcorrection
- **Fix:** Verify batch_key in setup_anndata, try n_latent=30-50, check LISI scores
- **Diagnostic:** UMAP colored by batch — should show mixing

```python
# Verify batch key is registered
print(adata.uns['_scvi']['data_registry'])

# Increase latent dimensionality
model = scvi.model.SCVI(adata, n_latent=50)

# Encode covariates more aggressively
model = scvi.model.SCVI(
    adata,
    encode_covariates=True,
    deeply_inject_covariates=False
)

# Evaluate batch mixing with scib
import scib
lisi_score = scib.metrics.ilisi_graph(adata, batch_key="batch", type_="embed", use_rep="X_scVI")
print(f"iLISI (higher = better mixing): {lisi_score:.3f}")
```

### scVI: Overcorrection (Losing Biology)
- **Cause:** Too many covariates registered, biology confounded with batch
- **Fix:** Only register true technical covariates, check batch-condition confounding, reduce n_latent

```python
# Check confounding before training
import pandas as pd
contingency = pd.crosstab(adata.obs["batch"], adata.obs["condition"])
print("Batch x Condition confounding:")
print(contingency)
# If each batch = one condition, batch correction will remove biological signal

# Register only technical covariates
scvi.model.SCVI.setup_anndata(
    adata,
    layer="counts",
    batch_key="sequencing_run",        # Technical batch only
    # Do NOT add condition here if confounded with batch
    continuous_covariate_keys=["pct_mito"]  # Technical covariates
)
```

### scANVI: Low Prediction Accuracy
- **Cause:** Poor quality seed labels, too few labeled cells, novel cell types not in training
- **Fix:** Verify label quality on known markers, ensure ≥5% cells labeled, check for populations not in reference
- **Diagnostic:** Confusion matrix on labeled cells, prediction confidence histogram

```python
# Always initialize scANVI from pretrained scVI
lvae = scvi.model.SCANVI.from_scvi_model(
    model,
    unlabeled_category="Unknown",
    labels_key="cell_type"
)
lvae.train(max_epochs=20, n_samples_per_label=100)

# Check prediction confidence
predictions = lvae.predict(soft=True)  # Returns probability matrix
confidence = predictions.max(axis=1)
print(f"Mean confidence: {confidence.mean():.3f}")
print(f"Low confidence cells (<0.5): {(confidence < 0.5).sum()}")

# Confusion matrix on labeled cells
from sklearn.metrics import confusion_matrix
labeled_mask = adata.obs["cell_type"] != "Unknown"
y_true = adata.obs.loc[labeled_mask, "cell_type"]
y_pred = lvae.predict()[labeled_mask]
cm = confusion_matrix(y_true, y_pred, labels=y_true.unique())
```

### scANVI: All Cells Predicted as One Type
- **Cause:** Degenerate training, labels too unbalanced, model not initialized from scVI
- **Fix:** Always initialize from pretrained scVI, balance training set, increase epochs

```python
# Never initialize scANVI from scratch — always from scVI
# Wrong:
# lvae = scvi.model.SCANVI(adata)  # Do not do this

# Correct:
scvi.model.SCVI.setup_anndata(adata, layer="counts", batch_key="batch", labels_key="cell_type")
vae = scvi.model.SCVI(adata)
vae.train(max_epochs=400)

lvae = scvi.model.SCANVI.from_scvi_model(vae, unlabeled_category="Unknown")
lvae.train(max_epochs=20, n_samples_per_label=100)  # n_samples_per_label helps balance
```

### LDVAE: Uninterpretable Loadings
- **Cause:** Too many latent dims, factors capturing noise
- **Fix:** Reduce n_latent to 5-15, check variance explained per factor, rotate loadings
- **Diagnostic:** `loadings.abs().sum(axis=0)` — factors with very small total loading may be noise

```python
# Get loadings from LDVAE
loadings = model.get_loadings()  # genes x n_latent

# Check total loading per factor
total_loading = loadings.abs().sum(axis=0)
print("Total loading per factor:")
print(total_loading.sort_values(ascending=False))
# Factors with near-zero total loading are likely noise

# Use fewer dimensions for cleaner factors
model = scvi.model.LinearSCVI(adata, n_latent=10)
```

### CellAssign: All Cells Assigned to One Type
- **Cause:** Marker genes not expressed, wrong matrix orientation, missing size factors
- **Fix:** Validate markers exist in data with `validate_marker_matrix()`, check matrix is genes×types (not transposed), compute size factors

```python
import scvi

# Always validate marker matrix first
marker_gene_mat = pd.DataFrame(markers)  # rows=genes, columns=cell types
# 1 = marker for that type, 0 = not a marker

# Check gene overlap
genes_in_data = set(adata.var_names)
marker_genes = set(marker_gene_mat.index)
missing = marker_genes - genes_in_data
print(f"Marker genes missing from data: {len(missing)}")
if missing:
    print(missing)

# Compute size factors (required by CellAssign)
sc.pp.normalize_total(adata, target_sum=None)  # creates size factors
adata.obs["size_factor"] = adata.obs["n_counts"] / np.median(adata.obs["n_counts"])

scvi.external.CellAssign.setup_anndata(adata, size_factor_key="size_factor")
model = scvi.external.CellAssign(adata, marker_gene_mat)
model.train()
```

### CellAssign: Marker Gene Not Found
- **Cause:** Gene name mismatch (symbols vs Ensembl IDs, species prefix)
- **Fix:** Check `adata.var_names` format, convert gene IDs if needed

```python
# Inspect var_names format
print("First 5 var_names:", adata.var_names[:5].tolist())
# Examples of common formats:
# Gene symbols: "CD3E", "CD4", "FOXP3"
# Ensembl IDs: "ENSG00000010610", "ENSG00000010626"
# With prefix: "GRCh38_CD3E" (common in 10x multi-genome references)

# If prefixed, strip the prefix
adata.var_names = adata.var_names.str.replace("GRCh38_", "")

# If Ensembl IDs, convert to symbols using pyensembl or biomart before CellAssign
```

### VeloVI: Low Permutation Scores
- **Cause:** Dataset has no transient dynamics (steady-state cells)
- **Fix:** This is informative — velocity analysis may not be appropriate for this dataset. Consider alternative trajectory methods.
- **Interpretation:** Low scores mean the model fits permuted data equally well — no directional dynamics detected

```python
# VeloVI permutation score interpretation
# Score > 0.5 suggests genuine dynamics
# Score ~ 0 suggests steady-state or no detectable RNA velocity

# If low permutation scores:
# 1. Check that dataset captures a dynamic process (differentiation, activation, etc.)
# 2. Consider trajectory inference without velocity (PAGA, diffusion pseudotime)
# 3. Verify spliced/unspliced counts are properly computed

import scvelo as scv
scv.tl.velocity(adata, mode="dynamical")  # Check fit quality per gene
scv.pl.scatter(adata, color="velocity_confidence")  # Low = poor fit
```

### VeloVI: Missing Spliced/Unspliced Layers
- **Cause:** scVelo preprocessing not run
- **Fix:** Run `scv.pp.filter_and_normalize` then `scv.pp.moments` before training VeloVI

```python
import scvelo as scv

# Required preprocessing for VeloVI
scv.pp.filter_and_normalize(adata, min_shared_counts=30, n_top_genes=2000)
scv.pp.moments(adata, n_pcs=30, n_neighbors=30)

# Verify layers exist
print("Layers:", list(adata.layers.keys()))
# Should include: 'spliced', 'unspliced', 'Ms', 'Mu'

# Then train VeloVI
scvi.external.VELOVI.setup_anndata(adata, spliced_layer="Ms", unspliced_layer="Mu")
vae = scvi.external.VELOVI(adata)
vae.train()
```

---

## 4. GPU / Performance Issues

### CUDA Out of Memory
- **Cause:** Dataset too large for GPU VRAM
- **Fix:** Reduce batch_size (64 or 32), use fewer HVGs, or fallback to CPU for very large datasets
- **Note:** CPU training is ~10-20x slower but works for any dataset size

```python
# Try progressively smaller batch sizes
for batch_size in [512, 256, 128, 64, 32]:
    try:
        model.train(max_epochs=400, batch_size=batch_size, accelerator="gpu")
        print(f"Training succeeded with batch_size={batch_size}")
        break
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"OOM at batch_size={batch_size}, trying smaller...")
            torch.cuda.empty_cache()
        else:
            raise

# If all GPU options fail, use CPU
model.train(max_epochs=400, accelerator="cpu")
```

### MPS (Apple Silicon) Issues
- **Cause:** Some PyTorch operations not yet supported on MPS backend
- **Fix:** If errors occur with accelerator="mps", fall back to accelerator="cpu"

```python
import torch

# Try MPS, fall back to CPU on errors
try:
    model.train(max_epochs=400, accelerator="mps")
except (RuntimeError, NotImplementedError) as e:
    print(f"MPS error: {e}")
    print("Falling back to CPU training")
    model.train(max_epochs=400, accelerator="cpu")
```

### Model Loading Fails
- **Cause:** scvi-tools version mismatch between save and load
- **Fix:** Check model_metadata.json for saved version, match scvi-tools version

```python
import json
import os

# Check saved model version
model_dir = "path/to/saved/model"
metadata_path = os.path.join(model_dir, "model_params.pt")
attr_path = os.path.join(model_dir, "attr.dict")

# Inspect scvi version at save time
import scvi
print(f"Current scvi-tools version: {scvi.__version__}")

# Load with allow_version_mismatch if needed (scvi >= 1.0)
model = scvi.model.SCVI.load(model_dir, adata=adata)
```

---

## 5. Quick Diagnostic Checklist

Before training any model, verify:

- [ ] Raw counts in `adata.layers['counts']` or `adata.X` (no NaN, no negatives, integer-like)
- [ ] HVGs selected (1000-4000 genes)
- [ ] Batch key registered (for multi-batch data)
- [ ] No duplicate cell barcodes (`adata.obs_names.duplicated().sum() == 0`)
- [ ] Sufficient cells (>500 per batch recommended)
- [ ] scvi-tools version ≥1.1

```python
import numpy as np
import scipy.sparse as sp

def scvi_preflight_check(adata, layer="counts", batch_key=None):
    """Run before any scVI model training."""
    issues = []

    # Check layer exists
    if layer not in adata.layers:
        issues.append(f"Layer '{layer}' not found. Available: {list(adata.layers.keys())}")
        return issues

    mat = adata.layers[layer]
    data = mat.data if sp.issparse(mat) else mat.flatten()

    # Check for NaN
    if np.isnan(data).any():
        issues.append("NaN values found in count matrix")

    # Check for negatives
    if (data < 0).any():
        issues.append("Negative values found in count matrix")

    # Check integer-like
    if not np.allclose(data, np.round(data), atol=0.1):
        issues.append("Counts do not appear integer-like — may be normalized")

    # Check HVGs
    if adata.n_vars > 5000:
        issues.append(f"Too many genes ({adata.n_vars}) — select 2000-4000 HVGs first")

    # Check cell count
    if adata.n_obs < 500:
        issues.append(f"Very few cells ({adata.n_obs}) — model may not train reliably")

    # Check duplicates
    n_dups = adata.obs_names.duplicated().sum()
    if n_dups > 0:
        issues.append(f"{n_dups} duplicate cell barcodes found")

    # Check batch key
    if batch_key and batch_key not in adata.obs:
        issues.append(f"Batch key '{batch_key}' not found in adata.obs")

    if issues:
        print("PRE-FLIGHT ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("Pre-flight check PASSED — ready to train")

    return issues

# Usage
issues = scvi_preflight_check(adata, layer="counts", batch_key="batch")
```
