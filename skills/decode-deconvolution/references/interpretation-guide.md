# DECODE Results Interpretation Guide

---

## Understanding the Output

### Predicted Proportions (`pred`)

`pred` is a numpy array of shape `(n_samples, n_cell_types)` where:
- Each row is one bulk tissue sample
- Each column is one cell type
- Values are proportions in [0, 1] that sum to 1 per row

```python
import pandas as pd
import numpy as np

# Convert to DataFrame
results_df = pd.DataFrame(pred, columns=type_list)
results_df.index.name = 'sample'

# Basic summary
print(results_df.describe())
print("\nMean proportions per cell type:")
print(results_df.mean().sort_values(ascending=False))
```

---

## Interpreting Evaluation Metrics

### Lin's CCC — The Primary Metric

CCC combines **precision** (correlation) and **accuracy** (mean agreement):

```
CCC = 2rσ_yσ_ŷ / (σ²_y + σ²_ŷ + (μ_y - μ_ŷ)²)
```

| CCC Range | Interpretation |
|---|---|
| > 0.95 | Excellent — near-perfect deconvolution |
| 0.90–0.95 | Very good — suitable for most analyses |
| 0.80–0.90 | Good — minor systematic bias present |
| 0.70–0.80 | Moderate — use with caution |
| < 0.70 | Poor — results unreliable |

**Why CCC > Pearson's r:** A method can have high Pearson's r (good correlation) but low CCC if it systematically over- or underestimates proportions. CCC penalizes both.

**Example from paper:**
- DECODE on lung transcriptomics (cross-donor): CCC = 0.978
- Scaden on same data: CCC ≈ 0.90
- MuSiC on same data: CCC ≈ 0.50

### RMSE — Absolute Error

RMSE is in proportion units (0–1):

| RMSE | Interpretation |
|---|---|
| < 0.03 | Excellent |
| 0.03–0.05 | Good |
| 0.05–0.10 | Moderate |
| > 0.10 | Poor |

**Context:** For a cell type with true proportion ~0.25, RMSE of 0.03 means predictions are typically within ±3 percentage points.

---

## Downstream Analyses

### 1. Differential Cell Abundance Between Conditions

```python
import pandas as pd
import numpy as np
from scipy import stats

# Assume results_df has columns: cell types + 'condition'
results_df['condition'] = ['tumor'] * 50 + ['normal'] * 50  # example

# t-test for each cell type
for cell_type in type_list:
    group_a = results_df[results_df['condition'] == 'tumor'][cell_type]
    group_b = results_df[results_df['condition'] == 'normal'][cell_type]
    t_stat, p_val = stats.ttest_ind(group_a, group_b)
    fold_change = group_a.mean() / group_b.mean()
    print(f"{cell_type}: FC={fold_change:.2f}, p={p_val:.4f}")
```

### 2. Correlation with Clinical Variables

```python
from scipy.stats import spearmanr

# Correlate cell type proportions with survival, grade, etc.
clinical_var = np.array([...])  # e.g., survival time

for cell_type in type_list:
    r, p = spearmanr(results_df[cell_type], clinical_var)
    print(f"{cell_type}: Spearman r={r:.3f}, p={p:.4f}")
```

### 3. Multi-Omics Consistency Check

```python
from scipy.stats import spearmanr
from scipy.special import kl_div

# Compare predictions from transcriptomics vs proteomics
# pred_rna, pred_prot: (n_samples, n_cell_types)

# Per-sample Spearman correlation
spearman_vals = [
    spearmanr(pred_rna[i], pred_prot[i]).correlation
    for i in range(len(pred_rna))
]
print(f"Cross-omics Spearman: {np.mean(spearman_vals):.3f} ± {np.std(spearman_vals):.3f}")
# DECODE achieves ~0.95+ cross-omics consistency

# KL divergence (lower = more consistent)
kl_vals = [
    np.sum(kl_div(pred_rna[i] + 1e-10, pred_prot[i] + 1e-10))
    for i in range(len(pred_rna))
]
print(f"Cross-omics KL divergence: {np.mean(kl_vals):.4f}")
```

### 4. Cell State Trajectory Analysis

```python
# For pseudotime deconvolution results
# pred shape: (n_samples, n_states) where states are pseudotime bins

import matplotlib.pyplot as plt

# Plot predicted state proportions over pseudotime
state_labels = [f'State {i+1}' for i in range(n_states)]
mean_props = pred.mean(axis=0)

plt.figure(figsize=(10, 4))
plt.bar(state_labels, mean_props)
plt.xlabel('Pseudotime State')
plt.ylabel('Mean Predicted Proportion')
plt.title('Cell State Distribution')
plt.tight_layout()
plt.savefig('state_distribution.png', dpi=150)
```

---

## Visualizations

### Stacked Bar Plot (Sample Composition)

```python
import matplotlib.pyplot as plt
import pandas as pd

results_df = pd.DataFrame(pred, columns=type_list)

fig, ax = plt.subplots(figsize=(max(8, len(results_df) * 0.3), 5))
results_df.plot(kind='bar', stacked=True, ax=ax, colormap='tab20')
ax.set_xlabel('Sample')
ax.set_ylabel('Cell Type Proportion')
ax.set_title('DECODE Deconvolution Results')
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig('stacked_bar.png', dpi=150, bbox_inches='tight')
```

### Scatter Plot: Predicted vs Ground Truth

```python
import matplotlib.pyplot as plt
import numpy as np

fig, axes = plt.subplots(1, len(type_list), figsize=(4 * len(type_list), 4))
if len(type_list) == 1:
    axes = [axes]

for i, (ax, ct) in enumerate(zip(axes, type_list)):
    ax.scatter(gt[:, i], pred[:, i], alpha=0.5, s=20)
    # Add 1:1 line
    lim = [0, max(gt[:, i].max(), pred[:, i].max()) * 1.05]
    ax.plot(lim, lim, 'r--', linewidth=1)
    ax.set_xlabel('True Proportion')
    ax.set_ylabel('Predicted Proportion')
    ax.set_title(ct)
    ax.set_xlim(lim); ax.set_ylim(lim)

plt.suptitle(f'DECODE: CCC={CCC:.3f}, RMSE={RMSE:.3f}', y=1.02)
plt.tight_layout()
plt.savefig('scatter_pred_vs_true.png', dpi=150, bbox_inches='tight')
```

### Heatmap of Cell Type Proportions

```python
import seaborn as sns
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(len(type_list) * 1.5, max(6, len(results_df) * 0.2)))
sns.heatmap(
    results_df,
    cmap='YlOrRd',
    vmin=0, vmax=1,
    ax=ax,
    xticklabels=True,
    yticklabels=False
)
ax.set_title('Cell Type Proportions (DECODE)')
ax.set_xlabel('Cell Type')
ax.set_ylabel('Sample')
plt.tight_layout()
plt.savefig('heatmap_proportions.png', dpi=150)
```

### Boxplot by Condition

```python
import seaborn as sns
import matplotlib.pyplot as plt

# Melt to long format
results_long = results_df.copy()
results_long['condition'] = conditions  # your condition labels
results_long = results_long.melt(
    id_vars='condition',
    value_vars=type_list,
    var_name='cell_type',
    value_name='proportion'
)

fig, ax = plt.subplots(figsize=(len(type_list) * 2, 5))
sns.boxplot(data=results_long, x='cell_type', y='proportion', hue='condition', ax=ax)
ax.set_xlabel('Cell Type')
ax.set_ylabel('Proportion')
ax.set_title('Cell Type Proportions by Condition')
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig('boxplot_by_condition.png', dpi=150)
```

---

## Benchmarking Against Other Methods

From the paper, expected CCC ranges for DECODE vs competitors:

### Transcriptomics

| Scenario | DECODE | Scaden | MuSiC | CIBERSORTx | TAPE |
|---|---|---|---|---|---|
| Cross-donor (lung) | ~0.97 | ~0.90 | ~0.50 | ~0.85 | ~0.88 |
| Cross-disease (breast) | ~0.95 | ~0.88 | ~0.55 | ~0.82 | ~0.90 |
| Real tissue (Monaco) | ~0.75 | ~0.72 | ~0.60 | ~0.65 | ~0.73 |
| Real tissue (Newman) | ~0.80 | ~0.75 | ~0.65 | ~0.70 | ~0.78 |

### Proteomics

| Scenario | DECODE | scpDeconv | Scaden | MuSiC |
|---|---|---|---|---|
| Cross-health state (breast) | ~0.95 | ~0.85 | ~0.70 | ~0.40 |
| Cross-dataset (cell lines) | ~0.88 | ~0.80 | ~0.65 | ~0.35 |

### Metabolomics

| Dataset | DECODE | All other methods |
|---|---|---|
| Bone marrow | ~0.65 | Near 0 or negative |
| Liver | ~0.80 | Near 0 or negative |
| Colorectal cancer | ~0.70 | Near 0 or negative |

---

## Robustness Scenarios

DECODE was tested under four perturbation scenarios. Expected performance degradation:

| Perturbation | DECODE CCC drop | Other methods |
|---|---|---|
| Unknown cells (up to 20%) | Minimal (<0.05) | Moderate (0.1–0.3) |
| Random noise ×0.9–1.1 (up to 20% features) | Minimal (<0.03) | Moderate |
| Systematic bias ×0.8 or ×1.2 (up to 20%) | Small (<0.08) | Large (0.2–0.5) |
| Feature deletion (up to 20%) | Small (<0.10) | Large |

**Key insight:** If your real data has batch effects, platform differences, or missing features, DECODE's robustness advantage over other methods is most pronounced.

---

## Reporting Results

When reporting DECODE results in a paper:

1. **Report all three metrics**: CCC (primary), RMSE, Pearson's r
2. **Specify the scenario**: cross-donor, cross-disease, real tissue, etc.
3. **Specify `if_pure`**: state whether denoiser pathway was used
4. **Report cell type resolution**: number of cell types deconvolved
5. **Report training data**: number of pseudotissue samples, HVG count

**Example methods text:**
> "Cell type deconvolution was performed using DECODE (Zhao et al., 2026) with 6,000 pseudotissue training samples generated from single-cell RNA-seq data. Highly variable genes (n=2,525) were used as input features. Stage 2 adversarial training was performed for 20 epochs (patience=3) followed by Stage 3 contrastive learning (200 epochs, patience=10). Inference used the denoiser pathway (if_pure=False) to account for potential unknown cell types in bulk tissue. Performance was evaluated using Lin's concordance correlation coefficient (CCC), RMSE, and Pearson's r."
