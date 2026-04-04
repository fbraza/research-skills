# Spatial Transcriptomics Troubleshooting Guide

---

## 1. General Spatial Issues

### Gene Name Format Mismatch
- **Cause:** ENSEMBL IDs in one dataset, gene symbols in the other; species prefixes from multi-genome CellRanger references; version suffixes on ENSEMBL IDs
- **Fix:** Inspect `var_names` in both datasets before any model setup. Convert gene IDs to match.

```python
# Inspect gene name formats in both datasets
print("Reference var_names (first 5):", sc_adata.var_names[:5].tolist())
print("Spatial var_names (first 5):", sp_adata.var_names[:5].tolist())

# Compute overlap BEFORE any filtering
overlap = len(set(sc_adata.var_names) & set(sp_adata.var_names))
print(f"Shared genes: {overlap}")

# Fix: strip species prefix (common with CellRanger multi-genome)
sp_adata.var_names = sp_adata.var_names.str.replace("GRCh38_", "")
sc_adata.var_names = sc_adata.var_names.str.replace("GRCh38_", "")

# Fix: strip ENSEMBL version suffix
sp_adata.var_names = sp_adata.var_names.str.split(".").str[0]

# Fix: convert ENSEMBL IDs to gene symbols using pyensembl or anndata var columns
# Check if symbols are stored as a var column
print(sp_adata.var.columns.tolist())
# If a "gene_name" or "symbol" column exists:
sp_adata.var_names = sp_adata.var["gene_name"].values
sp_adata.var_names_make_unique()
```

### Spatial Coordinates Not Found
- **Cause:** AnnData loaded without preserving spatial information; coordinates stored under a different key; Visium loaded without the spatial metadata flag
- **Fix:** Verify `obsm["spatial"]` exists and has shape (n_spots, 2)

```python
# Verify spatial coordinates
print("obsm keys:", list(sp_adata.obsm.keys()))

if "spatial" not in sp_adata.obsm:
    # Common fix 1: reload Visium data with spatial=True
    import scanpy as sc
    sp_adata = sc.read_visium(
        "path/to/visium/",
        count_file="filtered_feature_bc_matrix.h5",
        load_images=True,
    )
    # spatial coordinates are now in sp_adata.obsm["spatial"]

    # Common fix 2: coordinates stored under a different key
    # Check what keys are available
    for key in sp_adata.obsm.keys():
        print(f"  {key}: shape {sp_adata.obsm[key].shape}")

# Validate coordinate shape: must be (n_spots, 2)
coords = sp_adata.obsm["spatial"]
assert coords.shape == (sp_adata.n_obs, 2), (
    f"Expected coordinates shape ({sp_adata.n_obs}, 2), got {coords.shape}"
)
print(f"Spatial coordinates OK: {coords.shape}")
```

### Low Gene Overlap Between Reference and Spatial Data
- **Cause:** Gene name mismatch (see above); overly restrictive gene filtering applied before checking overlap; different genome versions
- **Fix:** Check overlap before filtering. Target a minimum of 500 shared genes; below 200 is a data quality problem.

```python
import numpy as np

shared_genes = np.intersect1d(sc_adata.var_names, sp_adata.var_names)
print(f"Shared genes: {len(shared_genes)}")

if len(shared_genes) < 500:
    print("WARNING: fewer than 500 shared genes — deconvolution quality will be poor")
    print("Steps to diagnose:")
    print("  1. Check gene name format consistency (symbols vs ENSEMBL IDs)")
    print("  2. Ensure gene filtering has not been applied before overlap check")
    print("  3. Verify both datasets are from the same species/genome version")
elif len(shared_genes) < 2000:
    print("CAUTION: fewer than 2000 shared genes — consider less restrictive filtering")
else:
    print("Gene overlap OK")
```

### Poor Reference Quality Propagates to Deconvolution
- **Cause:** Cell type annotations in the reference are inconsistent, poorly resolved, or contain mixed populations (doublets)
- **Fix:** Validate the reference before deconvolution by checking that known markers are enriched in the correct cell types

```python
import scanpy as sc

# Validate reference annotations using known markers
# If using Cell2location, this can be checked on the signature matrix
# For any reference, check dotplot of key markers per cell type

sc.pl.dotplot(
    sc_adata,
    var_names={
        "T cells": ["CD3D", "CD3E", "CD2"],
        "B cells": ["CD19", "MS4A1", "CD79A"],
        "Macrophages": ["CD68", "CSF1R", "MRC1"],
        "Fibroblasts": ["COL1A1", "DCN", "LUM"],
    },
    groupby="cell_type",
    standard_scale="var",
)
# Each cell type should show strong enrichment for its markers only
# Mixed enrichment patterns indicate poor reference annotations — fix before proceeding
```

---

## 2. Cell2location Issues

### Slow Training — Expected Behavior
- **Cause:** 30,000 epochs is the standard training duration for the spatial model; this is intentional
- **Fix:** Use GPU. On CPU, 30k epochs for a typical Visium dataset (3000 spots) takes many hours. On a modern GPU, expect 2–6 hours depending on spot count.

```python
import torch

# Check GPU availability
print("CUDA available:", torch.cuda.is_available())

# Always train Cell2location with GPU
sp_model.train(
    max_epochs=30000,
    batch_size=2500,
    train_size=1,
    use_gpu=True,
)

# Monitor training progress by inspecting ELBO history
import matplotlib.pyplot as plt
plt.plot(sp_model.history["elbo_train"])
plt.xlabel("Epoch")
plt.ylabel("ELBO")
plt.title("Cell2location training curve — should decrease monotonically")
plt.savefig("results/cell2loc_training_curve.png")
```

### GPU Out of Memory
- **Cause:** Spatial dataset too large for GPU VRAM; default batch_size too large
- **Fix:** Reduce batch_size; for very large tissue sections, consider subsampling spots for initial runs

```python
# Reduce batch_size progressively until training fits in VRAM
for batch_size in [2500, 1500, 1000, 500]:
    try:
        sp_model.train(max_epochs=30000, batch_size=batch_size, use_gpu=True)
        print(f"Training succeeded with batch_size={batch_size}")
        break
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"OOM at batch_size={batch_size}, trying smaller...")
            torch.cuda.empty_cache()
        else:
            raise
```

### N_cells_per_location Too High or Too Low
- **Cause:** The `N_cells_per_location` prior controls how many cells are expected per spot; if set very differently from the true biology, abundance estimates are biased
- **Fix:** Start with a value close to the expected cell count per spot for the technology used. Visium: 10–20. Slide-seq: 1–3. If unsure, run with two values (e.g., 8 and 20) and compare.

```python
# Check median counts per spot as a guide to cell density
import numpy as np
median_counts = np.median(sp_adata.X.sum(axis=1))
print(f"Median UMIs per spot: {median_counts:.0f}")
# Visium typically: 3000-10000 UMI/spot → N_cells_per_location ~ 10-20
# Slide-seq typically: 100-500 UMI/spot → N_cells_per_location ~ 1-5

# Train with two settings and compare
for n_cells in [8, 20]:
    model = cell2location.models.Cell2location(
        sp_adata,
        cell_state_df=inf_aver,
        N_cells_per_location=n_cells,
        detection_alpha=20,
    )
    model.train(max_epochs=30000, batch_size=2500, train_size=1, use_gpu=True)
    sp_adata_test = model.export_posterior(sp_adata.copy(), sample_kwargs={"num_samples": 1000})
    # Compare: do proportions show realistic spatial patterns at each setting?
```

### Signatures Look Wrong (No Diagonal Pattern)
- **Cause:** Reference cell type annotations are poor; too few cells per cell type in reference; highly similar cell types that cannot be distinguished
- **Fix:** Validate signatures as described in section 1. If annotations are mixed, re-cluster the reference or use coarser cell type labels.

```python
# Inspect the signature matrix for expected diagonal enrichment
import pandas as pd

inf_aver = sc_adata.varm["means_per_cluster_mu_fg"][
    [f"means_per_cluster_mu_fg_{ct}" for ct in sc_adata.uns["mod"]["factor_names"]]
].copy()
inf_aver.columns = sc_adata.uns["mod"]["factor_names"]

# Check that each cell type's top gene is a known marker
for ct in inf_aver.columns:
    top_gene = inf_aver[ct].idxmax()
    print(f"{ct}: top signature gene = {top_gene}")
# If cell types show unexpected top genes, the reference annotations need revision
```

### All Spots Have the Same Proportions
- **Cause:** Gene filtering too restrictive — only HVGs retained, losing discriminatory information; low gene overlap
- **Fix:** Use permissive gene filtering for Cell2location. Do not subset to top 2000 HVGs.

```python
import scanpy as sc

# Cell2location recommended filtering: permissive
sc.pp.filter_genes(sc_adata, min_cells=5)   # retain all genes expressed in ≥5 cells
# Do NOT apply sc.pp.highly_variable_genes() before Cell2location

# Check how many genes are shared after permissive filtering
shared = len(set(sc_adata.var_names) & set(sp_adata.var_names))
print(f"Shared genes after permissive filtering: {shared}")
# Target: 5000-16000 genes
```

### `export_posterior` Must Be Called Before Accessing Results
- **Cause:** Cell2location does not automatically populate `obsm` after training; `export_posterior` is a required explicit step
- **Fix:** Always call `export_posterior()` before attempting to access abundance results

```python
# Wrong: accessing obsm before export_posterior
# sp_adata.obsm["q05_cell_abundance_w_sf"]  # KeyError

# Correct:
sp_adata = sp_model.export_posterior(
    sp_adata,
    sample_kwargs={"num_samples": 1000, "batch_size": 2500, "use_gpu": True}
)

# Verify expected keys are present
expected_keys = ["q05_cell_abundance_w_sf", "means_cell_abundance_w_sf", "q95_cell_abundance_w_sf"]
for key in expected_keys:
    if key not in sp_adata.obsm:
        print(f"MISSING: {key}")
    else:
        print(f"OK: {key} — shape {sp_adata.obsm[key].shape}")
```

---

## 3. DestVI Issues

### Must Train scVI on Reference First
- **Cause:** DestVI is built on top of a pretrained scVI model; it cannot be instantiated without one
- **Fix:** Train scVI on the reference using the scvi-tools-scrna skill, then pass the trained model to `DestVI.from_rna_model()`

```python
import scvi

# Step 1: Train scVI on reference (always required before DestVI)
scvi.model.SCVI.setup_anndata(sc_adata, layer="counts", batch_key="batch")
sc_model = scvi.model.SCVI(sc_adata, n_latent=30, n_layers=2, gene_likelihood="nb")
sc_model.train(max_epochs=400)

# Step 2: Build DestVI from scVI model
scvi.model.DestVI.setup_anndata(sp_adata, layer="counts")
destvi_model = scvi.model.DestVI.from_rna_model(
    sp_adata,
    sc_model,
    cell_type_key="cell_type",
)
destvi_model.train(max_epochs=2500)
```

### `get_gamma()` Returns a Constant or Near-Constant Matrix
- **Cause:** Insufficient training; reference does not capture enough within-type variation; cell type is too rare or too uniform
- **Fix:** Increase training epochs; check that the reference for the target cell type spans genuine biological states

```python
# Diagnose gamma variation
import numpy as np

gamma = destvi_model.get_gamma("Macrophage")
print(f"Gamma shape: {gamma.shape}")  # (n_spots, n_latent)
print(f"Gamma variance per dimension: {gamma.var(axis=0)}")

# Expect meaningful variance across spots for at least some latent dimensions
# If all variances are near zero, the model captured no within-type variation
# Fix: train longer or check reference diversity for this cell type
low_var_dims = (gamma.var(axis=0) < 0.01).sum()
print(f"Latent dims with near-zero variance: {low_var_dims} / {gamma.shape[1]}")
```

### Proportions Sum to Greater or Less Than 1
- **Cause:** `get_proportions()` behavior may vary depending on scvi-tools version; numerical precision issues
- **Fix:** Always check and normalize explicitly

```python
import numpy as np

proportions = destvi_model.get_proportions()
row_sums = proportions.sum(axis=1)
print(f"Proportion row sums — min: {row_sums.min():.4f}, max: {row_sums.max():.4f}")

# If sums deviate from 1.0, normalize explicitly
if not np.allclose(row_sums, 1.0, atol=0.01):
    print("Normalizing proportions to sum to 1 per spot")
    proportions = proportions.div(row_sums, axis=0)

sp_adata.obsm["proportions"] = proportions
```

---

## 4. Tangram Issues

### Poor Mapping Quality
- **Cause:** Marker gene selection is insufficient or uninformative; too many noisy genes included; poor overlap between scRNA-seq and spatial expression
- **Fix:** Invest time in marker gene selection — this is the single most important factor in Tangram performance

```python
import scanpy as sc
import tangram as tg

# Approach 1: Use scanpy's rank_genes_groups to select top markers per type
sc.tl.rank_genes_groups(sc_adata, groupby="cell_type", method="wilcoxon", n_genes=100)
markers_df = sc.get.rank_genes_groups_df(sc_adata, group=None)
top_markers = (
    markers_df
    .query("pvals_adj <= 0.05 and logfoldchanges >= 1.0")
    .groupby("group")
    .head(50)
    ["names"]
    .unique()
    .tolist()
)

# Ensure markers are present in both datasets
shared_markers = [g for g in top_markers if g in sp_adata.var_names]
print(f"Informative markers in spatial data: {len(shared_markers)} / {len(top_markers)}")

# Approach 2: Provide curated marker list
curated_markers = ["CD3D", "CD8A", "FOXP3", "CD68", "MRC1", "CD19", "COL1A1"]
# Always check curated markers are present
missing = [g for g in curated_markers if g not in sp_adata.var_names]
if missing:
    print(f"WARNING: {len(missing)} curated markers not found: {missing}")

# Run pp_adatas with selected markers
tg.pp_adatas(sc_adata, sp_adata, genes=shared_markers)
```

### `mode="cells"` Is Very Slow or Runs Out of Memory
- **Cause:** `mode="cells"` maps each individual cell, creating an (n_cells × n_spots) matrix; for 50k cells × 3000 spots, this is a 150M-element matrix
- **Fix:** Start with `mode="clusters"` to validate alignment quality; use `mode="cells"` only on a subsampled reference for high-resolution analysis

```python
# Step 1: Run clusters mode first (fast, ~5 min)
ad_map_clusters = tg.map_cells_to_space(
    adata_sc=sc_adata,
    adata_sp=sp_adata,
    mode="clusters",
    cluster_label="cell_type",
    density_prior="rna_count_based",
    num_epochs=500,
    device="cuda:0",
)

# Step 2: Validate alignment quality before attempting cells mode
tg.project_cell_annotations(ad_map_clusters, sp_adata, annotation="cell_type")
sc.pl.spatial(sp_adata, color=list(sp_adata.obsm["tangram_ct_pred"].columns))
# Only proceed to cells mode if cluster mapping shows sensible patterns

# Step 3: If cells mode is needed, subsample reference
if sc_adata.n_obs > 10000:
    sc.pp.subsample(sc_adata, n_obs=5000, random_state=42)
    print(f"Subsampled to {sc_adata.n_obs} cells for mode='cells'")

ad_map_cells = tg.map_cells_to_space(
    adata_sc=sc_adata,
    adata_sp=sp_adata,
    mode="cells",
    density_prior="rna_count_based",
    num_epochs=500,
    device="cuda:0",
)
```

### Device Errors or Wrong Device Syntax
- **Cause:** Tangram uses PyTorch device string syntax (`"cuda:0"`, `"cpu"`), not scvi-tools accelerator syntax (`"gpu"`, `"mps"`)
- **Fix:** Use PyTorch device strings for Tangram

```python
import torch

# Check available devices
if torch.cuda.is_available():
    device = "cuda:0"
    print(f"Using CUDA GPU: {torch.cuda.get_device_name(0)}")
elif torch.backends.mps.is_available():
    device = "mps"  # Apple Silicon
    print("Using Apple MPS")
else:
    device = "cpu"
    print("Using CPU")

# Correct Tangram device syntax
ad_map = tg.map_cells_to_space(
    adata_sc=sc_adata,
    adata_sp=sp_adata,
    mode="clusters",
    cluster_label="cell_type",
    num_epochs=500,
    device=device,   # "cuda:0" — NOT accelerator="gpu"
)
```

### Inconsistent Results Across Runs
- **Cause:** Tangram uses stochastic gradient descent without a fixed random seed by default; results vary across runs, especially in `mode="cells"`
- **Fix:** Run multiple times and check consistency of the top mapping; set a random seed if reproducibility is required

```python
import torch
import numpy as np

# Set random seed for reproducibility
torch.manual_seed(42)
np.random.seed(42)

# Run multiple times and check consistency
results = []
for seed in [42, 123, 456]:
    torch.manual_seed(seed)
    ad_map = tg.map_cells_to_space(
        adata_sc=sc_adata,
        adata_sp=sp_adata,
        mode="clusters",
        cluster_label="cell_type",
        density_prior="rna_count_based",
        num_epochs=500,
        device=device,
    )
    tg.project_cell_annotations(ad_map, sp_adata.copy(), annotation="cell_type")
    results.append(sp_adata.obsm["tangram_ct_pred"].copy())

# Compare consistency across runs
import scipy.stats as stats
r01 = stats.pearsonr(results[0]["T cell"], results[1]["T cell"]).statistic
r02 = stats.pearsonr(results[0]["T cell"], results[2]["T cell"]).statistic
print(f"T cell proportion consistency: run0 vs run1 r={r01:.3f}, run0 vs run2 r={r02:.3f}")
# Expect r > 0.9 for stable results in clusters mode
```

---

## 5. scVIVA Issues

### ImportError or AttributeError
- **Cause:** scVIVA was added in a recent scvi-tools version; older installations will not have the class
- **Fix:** Upgrade scvi-tools to the latest version

```python
import scvi
print(f"scvi-tools version: {scvi.__version__}")

# Upgrade if needed
# pip install scvi-tools --upgrade

# Check if SCVIVA is available
try:
    from scvi.external import SCVIVA
    print("scVIVA is available")
except ImportError:
    print("scVIVA not found — upgrade scvi-tools: pip install scvi-tools --upgrade")
```

### `spatial_key` Not Found in `obsm`
- **Cause:** Spatial coordinates not loaded or stored under a different key
- **Fix:** Verify `obsm["spatial"]` exists before calling `setup_anndata`

```python
# Check obsm keys
print("Available obsm keys:", list(sp_adata.obsm.keys()))

# If coordinates are stored under a different name
for key in sp_adata.obsm.keys():
    arr = sp_adata.obsm[key]
    if hasattr(arr, "shape") and len(arr.shape) == 2 and arr.shape[1] == 2:
        print(f"Possible spatial coordinate key: '{key}' — shape {arr.shape}")

# Standardize key name
if "X_spatial" in sp_adata.obsm and "spatial" not in sp_adata.obsm:
    sp_adata.obsm["spatial"] = sp_adata.obsm["X_spatial"]
    print("Copied X_spatial to spatial")

# Validate
assert "spatial" in sp_adata.obsm, "spatial key not found — cannot run scVIVA"
assert sp_adata.obsm["spatial"].shape == (sp_adata.n_obs, 2), (
    f"spatial coordinates must be shape ({sp_adata.n_obs}, 2)"
)
```

### API Changed Between scvi-tools Versions
- **Cause:** scVIVA is based on a 2025 preprint and the API is not yet stable
- **Fix:** Always check the scvi-tools release notes and documentation for the installed version before using scVIVA

```python
import scvi

# Check version and print documentation URL
print(f"scvi-tools version: {scvi.__version__}")
print("scVIVA docs: https://docs.scvi-tools.org/en/stable/api/external.html")

# Inspect available methods for your installed version
from scvi.external import SCVIVA
print("SCVIVA methods:")
print([m for m in dir(SCVIVA) if not m.startswith("_")])
```

---

## 6. Quick Diagnostic Checklist

Run this checklist before starting any spatial deconvolution analysis.

- [ ] Spatial data contains raw counts (not normalized, not log-transformed)
- [ ] Spatial coordinates are in `adata.obsm["spatial"]` with shape (n_spots, 2)
- [ ] Reference scRNA-seq has raw counts and validated cell type labels in `obs`
- [ ] Gene names use the same format in both datasets (symbols vs. ENSEMBL IDs)
- [ ] Shared genes between reference and spatial data: minimum 500, target >2000
- [ ] No duplicate gene names in either dataset (run `var_names_make_unique()`)
- [ ] Reference has at least 10 cells per cell type (sparse types produce unreliable signatures)
- [ ] Low-quality spots removed from spatial data (filter by min_counts and min_genes)

```python
import numpy as np
import scanpy as sc

def spatial_preflight_check(sc_adata, sp_adata, sc_layer="counts", sp_layer="counts",
                             sc_label_key="cell_type"):
    """Run before any spatial deconvolution model."""
    issues = []

    # 1. Check raw counts in spatial data
    if sp_layer not in sp_adata.layers:
        issues.append(f"Spatial: layer '{sp_layer}' not found. Available: {list(sp_adata.layers.keys())}")
    else:
        import scipy.sparse as sp_
        mat = sp_adata.layers[sp_layer]
        data = mat.data if sp_.issparse(mat) else mat.flatten()
        if not np.allclose(data, np.round(data), atol=0.1):
            issues.append("Spatial counts do not appear integer-like — may be normalized")
        if (data < 0).any():
            issues.append("Negative values in spatial count matrix")

    # 2. Check spatial coordinates
    if "spatial" not in sp_adata.obsm:
        issues.append("Spatial coordinates missing: 'spatial' not in sp_adata.obsm")
    elif sp_adata.obsm["spatial"].shape != (sp_adata.n_obs, 2):
        issues.append(f"Spatial coordinates wrong shape: {sp_adata.obsm['spatial'].shape}, expected ({sp_adata.n_obs}, 2)")

    # 3. Check reference counts
    if sc_layer not in sc_adata.layers:
        issues.append(f"Reference: layer '{sc_layer}' not found. Available: {list(sc_adata.layers.keys())}")

    # 4. Check cell type labels in reference
    if sc_label_key not in sc_adata.obs.columns:
        issues.append(f"Reference: cell type column '{sc_label_key}' not found in obs")
    else:
        ct_counts = sc_adata.obs[sc_label_key].value_counts()
        sparse_types = ct_counts[ct_counts < 10].index.tolist()
        if sparse_types:
            issues.append(f"Reference: {len(sparse_types)} cell types with <10 cells: {sparse_types}")

    # 5. Check gene overlap
    shared = np.intersect1d(sc_adata.var_names, sp_adata.var_names)
    if len(shared) < 500:
        issues.append(f"Gene overlap too low: {len(shared)} shared genes (minimum 500)")
    elif len(shared) < 2000:
        issues.append(f"Gene overlap low: {len(shared)} shared genes — consider less restrictive filtering")

    # 6. Check for duplicate gene names
    sc_dups = sc_adata.var_names.duplicated().sum()
    sp_dups = sp_adata.var_names.duplicated().sum()
    if sc_dups > 0:
        issues.append(f"Reference: {sc_dups} duplicate gene names — run var_names_make_unique()")
    if sp_dups > 0:
        issues.append(f"Spatial: {sp_dups} duplicate gene names — run var_names_make_unique()")

    # Report
    if issues:
        print("PRE-FLIGHT ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print(f"Pre-flight check PASSED — {len(shared)} shared genes, ready to run deconvolution")

    return issues

# Usage
issues = spatial_preflight_check(sc_adata, sp_adata, sc_label_key="cell_type")
```
