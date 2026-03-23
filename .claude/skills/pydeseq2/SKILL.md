---
id: pydeseq2
name: PyDESeq2
description: >
  Python implementation of DESeq2 for bulk RNA-seq and pseudobulk differential
  expression analysis. USE ONLY when the user explicitly requests a Python-only
  pipeline or specifies PyDESeq2. For all other bulk RNA-seq and pseudobulk DE
  analyses, use the bulk-rnaseq-counts-to-de-deseq2 skill (R DESeq2) — it is
  the default and preferred tool.
  Trigger phrases: "PyDESeq2", "DESeq2 in Python", "Python DESeq2",
  "Python-only differential expression", "pydeseq2".
  DO NOT trigger for: "DESeq2", "differential expression", "bulk RNA-seq DE"
  without explicit Python/PyDESeq2 specification — route those to
  bulk-rnaseq-counts-to-de-deseq2 instead.
category: transcriptomics
short-description: "Python DESeq2 for bulk RNA-seq DE — use only when explicitly requested; default to R DESeq2."
detailed-description: "PyDESeq2 (Muzellec et al. 2023) is a Python reimplementation of DESeq2 using negative binomial GLMs, Wald tests, and BH FDR correction. Supports single-factor and multi-factor designs, batch correction, apeGLM LFC shrinkage, and AnnData input. Only use when user explicitly requests Python. For all standard bulk RNA-seq DE and pseudobulk analysis, R DESeq2 via bulk-rnaseq-counts-to-de-deseq2 is the default."
---

# PyDESeq2

**PRIORITY RULE:** R DESeq2 (`bulk-rnaseq-counts-to-de-deseq2`) is the default for all bulk RNA-seq
and pseudobulk differential expression analyses. Use PyDESeq2 ONLY when the user explicitly
requests it by name or specifies a Python-only workflow. Never substitute PyDESeq2 for R DESeq2
silently.

## When to Use This Skill

- User explicitly says "PyDESeq2" or "DESeq2 in Python"
- User requires a fully Python-based pipeline (no R dependency)
- Integrating DE into an existing Python/AnnData workflow where calling R is impractical

**Do NOT use for:** General "differential expression" or "DESeq2" requests without Python specification
→ route those to `bulk-rnaseq-counts-to-de-deseq2`.

## Installation

```bash
pip install pydeseq2
# Requires Python 3.10-3.11, anndata ≥ 0.8
```

## Core Workflow

### 1. Load data (samples × genes, integer counts)

```python
import pandas as pd
from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

# Input must be raw integer counts — NOT normalized, NOT log-transformed
counts_df = pd.read_csv("counts.csv", index_col=0).T  # genes×samples → samples×genes
metadata = pd.read_csv("metadata.csv", index_col=0)

# From AnnData (pseudobulk aggregated counts)
import anndata as ad
adata = ad.read_h5ad("pseudobulk.h5ad")
counts_df = pd.DataFrame(adata.X.toarray() if hasattr(adata.X, 'toarray') else adata.X,
                         index=adata.obs_names, columns=adata.var_names)
metadata = adata.obs

# Align samples
common = counts_df.index.intersection(metadata.index)
counts_df = counts_df.loc[common]
metadata = metadata.loc[common]

# Filter low-count genes
genes_to_keep = counts_df.columns[counts_df.sum(axis=0) >= 10]
counts_df = counts_df[genes_to_keep]
print(f"Retained {len(genes_to_keep)} genes after filtering")
```

### 2. Fit DESeq2

```python
dds = DeseqDataSet(
    counts=counts_df,
    metadata=metadata,
    design="~condition",          # Single-factor
    # design="~batch + condition", # Multi-factor: batch first, condition last
    refit_cooks=True,
    n_cpus=4
)
dds.deseq2()
```

### 3. Statistical testing

```python
ds = DeseqStats(
    dds,
    contrast=["condition", "treated", "control"],  # [variable, test, reference]
    alpha=0.05,
    cooks_filter=True,
    independent_filter=True
)
ds.summary()

# Optional: LFC shrinkage (for visualization only — does not affect p-values)
ds.lfc_shrink()

results = ds.results_df
print(f"Significant (padj ≤ 0.05): {(results.padj <= 0.05).sum()}")
```

**Always use `padj`, never raw `pvalue`.**

### 4. Export results

```python
import os
os.makedirs("./results", exist_ok=True)
results.to_csv("./results/deseq2_results.csv")
results[results.padj <= 0.05].to_csv("./results/significant_genes.csv")
```

## Common Design Patterns

```python
# Two-group
design = "~condition"

# Batch correction
design = "~batch + condition"   # Batch always before condition of interest

# Continuous covariate
metadata["age"] = pd.to_numeric(metadata["age"])
design = "~age + condition"

# Multiple comparisons (reuse fitted dds)
for treatment in ["A", "B", "C"]:
    ds = DeseqStats(dds, contrast=["condition", treatment, "control"])
    ds.summary()
    ds.results_df.to_csv(f"./results/de_{treatment}_vs_control.csv")
```

## Key Rules

- **Input must be raw integer counts** — never normalized, never log-transformed
- **Always use `padj ≤ 0.05`** — never raw p-value
- **LFC shrinkage** is for visualization/ranking only — run after statistical testing
- **Adjustment variables go before the variable of interest** in the design formula
- **Invoke The Reviewer** after completing DE analysis

## References

- [references/api_reference.md](references/api_reference.md) — DeseqDataSet / DeseqStats API
- [references/workflow_guide.md](references/workflow_guide.md) — Extended workflows and troubleshooting
- [scripts/run_deseq2_analysis.py](scripts/run_deseq2_analysis.py) — CLI script for standard analyses
- PyDESeq2 paper: Muzellec et al. (2023) Bioinformatics DOI:10.1093/bioinformatics/btad547
- Original DESeq2: Love et al. (2014) Genome Biology DOI:10.1186/s13059-014-0550-8
