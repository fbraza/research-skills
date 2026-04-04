# Scaden Results Interpretation Guide

---

## Understanding the Predictions File

The main output `scaden_predictions.txt` is a tab-separated matrix:

```
          CD4_T   CD8_T   B_cell  Monocyte  NK_cell
sample1   0.312   0.198   0.145   0.221     0.124
sample2   0.289   0.201   0.167   0.198     0.145
sample3   0.401   0.155   0.112   0.198     0.134
```

- **Rows**: Bulk RNA-seq samples
- **Columns**: Cell types (from scRNA-seq reference)
- **Values**: Predicted cell type fractions (0–1)
- **Row sums**: Should be ~1.0 (Softmax output; minor floating-point deviations are normal)

---

## Evaluating Prediction Quality

### When Ground Truth is Available (Validation)

If you have flow cytometry, immunohistochemistry, or other orthogonal cell fraction measurements:

```python
import pandas as pd
import numpy as np
from scipy.stats import pearsonr

preds = pd.read_csv("scaden_predictions.txt", sep="\t", index_col=0)
truth = pd.read_csv("ground_truth_fractions.csv", index_col=0)

# Align samples
common = preds.index.intersection(truth.index)
preds = preds.loc[common]
truth = truth.loc[common]

# Per-cell-type Pearson r
for ct in preds.columns:
    if ct in truth.columns:
        r, p = pearsonr(truth[ct], preds[ct])
        print(f"{ct}: r={r:.3f}, p={p:.4f}")

# Overall RMSE
rmse = np.sqrt(((preds.values - truth.values)**2).mean())
print(f"Overall RMSE: {rmse:.4f}")
```

**Performance benchmarks from the paper (CCC values):**
| Dataset | Scaden | MuSiC | CIBERSORTx |
|---------|--------|-------|------------|
| PBMC (simulated) | 0.88 | 0.85 | 0.83 |
| PBMC1 (real) | 0.56 | -0.19 | 0.55 |
| PBMC2 (real) | 0.68 | -0.13 | 0.42 |
| Brain (ROSMAP) | 0.92 | 0.87 | 0.81 |
| Pancreas | 0.98 | 0.93 | 0.75 |

### When Ground Truth is Not Available

Signs of good predictions:
- ✅ Fractions are biologically plausible for your tissue
- ✅ Dominant cell types match known tissue composition
- ✅ Fractions vary meaningfully across samples (not all near-uniform)
- ✅ Samples from the same condition cluster together by composition

Signs of poor predictions:
- ❌ All samples have nearly identical fractions (model not learning)
- ❌ Fractions dominated by a single unexpected cell type
- ❌ Very high fractions for rare cell types
- ❌ Fractions don't correlate with known biology (e.g., immune-cold tumors showing high T cell fractions)

---

## Biological Interpretation

### Reading Stacked Bar Charts

Each bar represents one bulk sample. The height of each colored segment = predicted fraction of that cell type.

**What to look for:**
- **Consistent patterns within groups**: Samples from the same condition should have similar compositions
- **Shifts between conditions**: Increased immune infiltration in treated vs. untreated tumors
- **Outlier samples**: Samples with unusual composition may indicate technical issues or biological extremes

### Reading Fraction Heatmaps

Rows = cell types, columns = samples (or vice versa). Color intensity = fraction.

**What to look for:**
- **Cell type co-occurrence**: Cell types that tend to be high/low together
- **Sample clustering**: Samples with similar composition cluster together
- **Condition-specific patterns**: Systematic differences between experimental groups

---

## Downstream Analyses

### 1. Differential Composition Analysis

Compare cell type fractions between conditions:

```python
import pandas as pd
from scipy.stats import mannwhitneyu
import statsmodels.stats.multitest as mt

preds = pd.read_csv("scaden_predictions.txt", sep="\t", index_col=0)
metadata = pd.read_csv("sample_metadata.csv", index_col=0)

# Align
preds = preds.loc[metadata.index]

# Test each cell type
results = []
for ct in preds.columns:
    group_a = preds.loc[metadata["condition"] == "control", ct]
    group_b = preds.loc[metadata["condition"] == "treated", ct]
    stat, p = mannwhitneyu(group_a, group_b, alternative="two-sided")
    results.append({"cell_type": ct, "p_value": p,
                    "mean_control": group_a.mean(), "mean_treated": group_b.mean(),
                    "delta": group_b.mean() - group_a.mean()})

results_df = pd.DataFrame(results)
results_df["padj"] = mt.multipletests(results_df["p_value"], method="fdr_bh")[1]
results_df = results_df.sort_values("padj")
print(results_df)
```

### 2. Correlation with Clinical Variables

```python
from scipy.stats import spearmanr

# Correlate cell type fractions with a continuous variable (e.g., survival, age)
for ct in preds.columns:
    r, p = spearmanr(metadata["survival_months"], preds[ct])
    if p < 0.05:
        print(f"{ct}: Spearman r={r:.3f}, p={p:.4f}")
```

### 3. Composition-Corrected Differential Expression

Use predicted fractions as covariates in DESeq2/limma to remove composition effects:

```r
# In R — add cell type fractions as covariates
library(DESeq2)
preds <- read.table("scaden_predictions.txt", header=TRUE, row.names=1, sep="\t")

# Merge with sample metadata
coldata <- merge(coldata, preds, by="row.names")

# Include fractions as covariates in design
dds <- DESeqDataSetFromMatrix(
    countData = counts,
    colData = coldata,
    design = ~ CD4_T + CD8_T + Monocyte + condition  # Add cell type fractions
)
```

### 4. Survival Analysis with Cell Type Fractions

```python
from lifelines import CoxPHFitter
import pandas as pd

preds = pd.read_csv("scaden_predictions.txt", sep="\t", index_col=0)
clinical = pd.read_csv("clinical_data.csv", index_col=0)

# Merge
df = preds.join(clinical[["survival_months", "event"]])

# Cox proportional hazards
cph = CoxPHFitter()
cph.fit(df, duration_col="survival_months", event_col="event")
cph.print_summary()
```

---

## Common Biological Patterns

### Blood/PBMC
- Healthy PBMC: ~40-50% T cells, ~10-15% B cells, ~10-15% NK cells, ~15-20% Monocytes
- Infection/inflammation: Increased monocytes, decreased lymphocytes
- Autoimmune: Altered T cell subtype ratios

### Brain
- Normal cortex: ~50-60% neurons, ~20-30% astrocytes, ~5-10% oligodendrocytes, ~5% microglia
- Neurodegeneration (AD): Progressive neuronal loss with increasing Braak stage
- Glioma: Increased tumor cells, altered immune infiltration

### Tumor (Ascites/Solid)
- Immune-hot tumors: High T cell, NK cell fractions
- Immune-cold tumors: Low immune infiltration, high cancer cell fraction
- Immunotherapy response: Increased CD8 T cell fraction post-treatment

### Pancreas
- Healthy: ~50-60% acinar, ~15-20% ductal, ~10% beta cells, ~5% alpha cells
- Type 2 diabetes: Reduced beta cell fraction
- Pancreatitis: Increased inflammatory cells

---

## Caveats and Limitations

1. **Cell size differences**: Scaden does not model cell size. Larger cells contribute more RNA to bulk data, which can bias fraction estimates. Interpret fractions as RNA-weighted, not cell-count-weighted.

2. **Unknown cell types**: If your bulk tissue contains cell types not in the training data, their RNA is distributed across known cell types. Fractions of known types will be inflated.

3. **Cell type granularity**: Scaden can only distinguish cell types present in the scRNA-seq reference. Subtypes (e.g., CD4 Treg vs. CD4 Th17) require a reference with those annotations.

4. **Rare cell types**: Cell types present at <1-2% are difficult to estimate accurately. Treat low-fraction predictions with caution.

5. **Tissue heterogeneity**: Scaden assumes the bulk sample is a mixture of the cell types in the reference. If the tissue has unique cell states not captured in the reference, performance degrades.

6. **Simulated vs. real data gap**: Training on simulated data introduces a domain gap. Adding real bulk samples with known fractions to training (even a few) substantially improves performance.

7. **Per-cell-type accuracy varies**: Overall CCC may be high while individual cell types perform poorly. Always inspect per-cell-type predictions, not just aggregate metrics.
