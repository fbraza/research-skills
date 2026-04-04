# CellBender Results Interpretation Guide

---

## Reading the PDF Output

The PDF (`output.pdf`) contains three diagnostic plots. Examine them in order.

### Plot 1: ELBO Learning Curve

The ELBO (Evidence Lower BOund) measures how well the model fits the data. It should increase and plateau.

**Good learning curve:**
- Monotonically increasing (or nearly so)
- Reaches a stable plateau by the end of training
- Small noise fluctuations are normal

**Bad learning curve — action required:**

| Pattern | Cause | Fix |
|---|---|---|
| Large downward spikes | Learning rate too high | Re-run with `--learning-rate` halved (e.g., 5e-5) |
| Curve still rising at end | Not enough epochs | Re-run with `--epochs 300` from checkpoint |
| Curve drops at the end | Over-training or instability | Use the checkpoint from the best epoch; reduce LR |
| Flat from the start | Model not learning | Check input data; try `--model ambient` |

### Plot 2: UMI Rank Plot with Cell Probabilities

Shows the ranked UMI curve (log-log) with cell probability overlaid.

**What to look for:**
- Cell probabilities should be **bimodal**: most near 1.0 (cells) or near 0.0 (empty)
- The transition from high to low probability should be sharp, near the "knee" of the UMI curve
- The number of called cells should match your expectation

**Problems:**

| Pattern | Cause | Fix |
|---|---|---|
| Gradual probability transition | Poor convergence or wrong priors | Increase epochs; adjust `--expected-cells` |
| Too many cells called | Low-quality droplets called as cells | Filter downstream by MT%, gene count |
| Too few cells called | `--expected-cells` too low | Increase `--expected-cells` and `--total-droplets-included` |
| All probabilities near 0.5 | Model failed to converge | Reduce learning rate; increase epochs |

### Plot 3: PCA of Latent Gene Expression (`z`)

Shows a 2D PCA projection of the CellBender latent embedding for called cells.

**What to look for:**
- **Clusters present** = good. Different clusters likely correspond to different cell types.
- **No clusters** = could be normal (one cell type) or a QC problem

**If no clusters and you expect multiple cell types:**
1. Check if training converged (Plot 1)
2. Check if cells were called correctly (Plot 2)
3. Consider that cells may have been ruptured (all appear as same "type")
4. Run downstream clustering with and without CellBender and compare

---

## Key Latent Variables

### Per-cell variables (in `adata.obs` after loading)

| Variable | Range | Interpretation |
|---|---|---|
| `cell_probability` | [0, 1] | P(droplet contains a cell). Use >0.5 to call cells. |
| `background_fraction` | [0, 1] | Fraction of this droplet's counts that are ambient RNA. High values (>0.5) indicate heavily contaminated droplets. |
| `cell_size` | counts | Estimated true UMI count (signal only, no ambient). |
| `droplet_efficiency` | [0, 1] | Estimated capture efficiency of this droplet. |

### Per-gene variables (in `adata.var` after loading)

| Variable | Range | Interpretation |
|---|---|---|
| `ambient_expression` | [0, 1], sums to 1 | Normalized ambient RNA profile. High values = genes that are highly represented in the ambient soup. These are the genes most likely to cause false positives in non-expressing cells. |

### Inspecting the ambient profile
```python
import pandas as pd

# Top ambient genes
ambient = adata.var['ambient_expression'].sort_values(ascending=False)
print("Top 20 ambient genes:")
print(ambient.head(20))

# Plot ambient profile
import matplotlib.pyplot as plt
import seaborn as sns

fig, ax = plt.subplots(figsize=(12, 4))
ambient.head(50).plot(kind='bar', ax=ax)
ax.set_xlabel('Gene')
ax.set_ylabel('Ambient expression (normalized)')
ax.set_title('Top 50 Ambient RNA Genes')
plt.xticks(rotation=45, ha='right', fontsize=7)
plt.tight_layout()
plt.savefig('ambient_profile.png', dpi=150)
```

**Biological interpretation of ambient genes:**
- Hemoglobin genes (HBB, HBA1, HBA2) → red blood cell lysis
- Mitochondrial genes → dying cells
- Highly expressed housekeeping genes → general cell lysis
- Tissue-specific markers → dominant cell type in the sample

---

## Validating CellBender Worked

### Method 1: Compare ambient gene expression before/after

```python
from cellbender.remove_background.downstream import load_anndata_from_input_and_output
import scanpy as sc

adata = load_anndata_from_input_and_output(
    input_file='raw_feature_bc_matrix.h5',
    output_file='cellbender_output_filtered.h5',
    input_layer_key='raw',
)

# Pick a known ambient gene (e.g., top ambient gene from adata.var)
ambient_gene = adata.var['ambient_expression'].idxmax()
print(f"Top ambient gene: {ambient_gene}")

# Compare expression in non-expressing cell types
sc.pl.violin(adata, keys=ambient_gene, layer='raw',
             groupby='leiden', title=f'{ambient_gene} (raw)')
sc.pl.violin(adata, keys=ambient_gene,
             groupby='leiden', title=f'{ambient_gene} (CellBender)')
# Expect: reduced expression in cell types that shouldn't express this gene
```

### Method 2: Inspect what was removed

```python
import numpy as np
import scipy.sparse as sp

# Compute difference matrix
raw = adata.layers['raw']
cellbender = adata.X

if sp.issparse(raw):
    removed = raw - cellbender
else:
    removed = raw - cellbender

# Per-gene: how many counts were removed?
counts_removed_per_gene = np.array(removed.sum(axis=0)).flatten()
gene_names = adata.var_names

removed_df = pd.DataFrame({
    'gene': gene_names,
    'counts_removed': counts_removed_per_gene,
    'ambient_expression': adata.var['ambient_expression'].values
}).sort_values('counts_removed', ascending=False)

print("Top genes by counts removed:")
print(removed_df.head(20))
# These should match the top ambient genes
```

### Method 3: UMAP comparison

```python
# Compute UMAP on raw data
adata_raw = adata.copy()
adata_raw.X = adata_raw.layers['raw']
sc.pp.normalize_total(adata_raw); sc.pp.log1p(adata_raw)
sc.pp.pca(adata_raw); sc.pp.neighbors(adata_raw); sc.tl.umap(adata_raw)

# Compute UMAP on CellBender data
sc.pp.normalize_total(adata); sc.pp.log1p(adata)
sc.pp.pca(adata); sc.pp.neighbors(adata); sc.tl.umap(adata)

# Compare: CellBender should show cleaner cluster separation
# and reduced expression of ambient genes across clusters
```

### Method 4: Marker gene dotplots

```python
# Known marker genes for your cell types
markers = {'T cells': ['CD3D', 'CD3E'], 'B cells': ['CD19', 'MS4A1'],
           'Monocytes': ['CD14', 'LYZ'], 'NK cells': ['GNLY', 'NKG7']}

sc.pl.dotplot(adata, markers, groupby='leiden',
              layer='raw', title='Raw counts')
sc.pl.dotplot(adata, markers, groupby='leiden',
              title='CellBender counts')
# Expect: cleaner on/off patterns, less background in non-expressing clusters
```

---

## Choosing the Right FPR

The `--fpr` (false positive rate) controls the trade-off between noise removal and signal preservation.

| FPR | Behavior | Use case |
|---|---|---|
| 0.0 | Minimal removal — only very confident noise | Cohort DE analysis (preserve signal) |
| 0.01 | Conservative (default) | Most analyses |
| 0.05 | Moderate | Single-sample analysis, aggressive denoising |
| 0.1 | Aggressive | Heavily contaminated samples |
| 1.0 | Removes nearly everything | Never use |

**Practical approach**: Run with multiple FPR values and compare:
```bash
cellbender remove-background \
    --cuda \
    --input raw.h5 --output out.h5 \
    --fpr 0.0 0.01 0.05 0.1
```

```python
from cellbender.remove_background.downstream import load_anndata_from_input_and_outputs

adata = load_anndata_from_input_and_outputs(
    input_file='raw_feature_bc_matrix.h5',
    output_files={
        'fpr0.0':  'out.h5',
        'fpr0.01': 'out_fpr0.01.h5',
        'fpr0.05': 'out_fpr0.05.h5',
        'fpr0.1':  'out_fpr0.1.h5',
    },
    input_layer_key='raw',
)

# Compare ambient gene expression across FPR values
for fpr in ['fpr0.0', 'fpr0.01', 'fpr0.05', 'fpr0.1']:
    mean_ambient = adata[:, ambient_gene].layers[fpr].mean()
    print(f"{fpr}: mean {ambient_gene} = {mean_ambient:.3f}")
```

---

## Using the CellBender Embedding

The latent `z` embedding (`adata.obsm['cellbender_embedding']`) is a 64-dimensional representation of true gene expression, learned by the CellBender encoder. It can be used directly for clustering and UMAP instead of PCA.

```python
# Use CellBender embedding for neighbors (recommended)
sc.pp.neighbors(adata, use_rep='cellbender_embedding', metric='euclidean')
sc.tl.umap(adata)
sc.tl.leiden(adata, resolution=0.5)

# Compare with PCA-based neighbors
sc.pp.normalize_total(adata); sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.pp.pca(adata)
sc.pp.neighbors(adata, use_rep='X_pca', key_added='pca_neighbors')
sc.tl.umap(adata, neighbors_key='pca_neighbors', key_added='X_umap_pca')
```

**Advantage of CellBender embedding**: It was learned on denoised counts and is not confounded by ambient RNA. It may give better cluster separation for datasets with high ambient contamination.

---

## Interpreting metrics.csv for Automated Pipelines

Key metrics for automated QC decisions:

```python
import pandas as pd

metrics = pd.read_csv('cellbender_output_metrics.csv')

# Flag potential issues:
if metrics['convergence_indicator'].values[0] > 1.0:
    print("WARNING: Poor convergence. Consider re-running with more epochs or lower LR.")

if metrics['fraction_counts_removed_from_cells'].values[0] > 0.5:
    print("WARNING: >50% of cell counts removed. Check ambient contamination level.")

if metrics['ratio_of_found_cells_to_expected_cells'].values[0] > 3:
    print("WARNING: 3x more cells found than expected. Check --expected-cells.")

if metrics['ratio_of_found_cells_to_expected_cells'].values[0] < 0.3:
    print("WARNING: Far fewer cells found than expected. Increase --expected-cells.")
```

---

## Reporting in Methods

**Example methods text:**
> "Ambient RNA removal was performed using CellBender v0.3.2 (Fleming et al., 2023). For each sample, the raw unfiltered count matrix from CellRanger v[X] was processed with `cellbender remove-background` using default parameters (`--epochs 150`, `--fpr 0.01`, `--learning-rate 1e-4`) with GPU acceleration. The number of expected cells and total droplets included were set based on the UMI rank plot for each sample. Convergence was verified by inspection of the ELBO learning curve and the HTML report. Denoised count matrices were loaded using `cellbender.remove_background.downstream.load_anndata_from_input_and_output()` for downstream analysis."
