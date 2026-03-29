# DESeq2 Decision Guide

Decision trees for choosing between DESeq2 methods and approaches.

---

## Decision 1: Transformation Method

**When:** After DESeq(), before PCA/heatmaps
**Question:** Which transformation — vst(), rlog(), or log2(normalized counts)?

### Option A: VST (Variance Stabilizing Transformation)

**Use when:** n > 30 samples, need fast computation

**Pros:** Fast (1000+ samples OK), suitable for large datasets
**Cons:** Less accurate for small samples (n < 10)

```r
vsd <- vst(dds, blind = FALSE)  # blind=FALSE uses design (recommended)
```

### Option B: rlog (Regularized Log)

**Use when:** n < 30 samples, want best stabilization

**Pros:** Better for small samples, better at low counts
**Cons:** Slow for large datasets (>100 samples)

```r
rld <- rlog(dds, blind = FALSE)
```

### Option C: log2(normalized counts) — special cases only

> **Not recommended as a default.** VST or rlog should be used for routine PCA, clustering, and heatmaps. log2(normalized counts) provides no variance stabilization — low-count genes with high Poisson noise will dominate ordination, and the "remove zeros" approach can discard 30-60% of genes, introducing survivorship bias. Use only for the specific scenarios listed below.

**Use when:** Replicating a published analysis that used this exact method (e.g., Burton et al. 2024), or after aggressive pre-filtering (e.g., transcripts-per-cell) that already removed most low-count genes.

**Pros:** Simple, interpretable, preserves absolute magnitude, no complex shrinkage
**Cons:** No variance stabilization (low-count genes dominate PCA/clustering due to noise), genes with any zero in any sample are removed (can lose 30-60% of genes, introducing survivorship bias), sensitive to sequencing depth differences

**Note:** Some training materials (e.g., Galaxy Project tutorials) use log2 + pseudocount as a pedagogical simplification. This is not incorrect for teaching, but the DESeq2 authors (Love et al. 2014) and the Bioconductor vignette explicitly recommend VST or rlog for downstream analyses that assume homoskedasticity.

```r
source("scripts/log2_normalization.R")
result <- apply_log2_normalization(dds, zero_handling = "remove")
log2_mat <- result$matrix  # genes x samples
```

**Zero handling options:**
- `"remove"` (default, paper approach): Drop genes with any zero via `complete.cases()`
- `"pseudocount"`: Add 0.5 before log2 — keeps all genes but distorts low counts
- `"na"`: Set zeros to NA — useful for downstream methods that handle NA

**Biological filter (optional):** When the number of cells per sample is known (e.g., FACS sorting), use `filter_transcripts_per_cell()` to apply a biologically motivated expression threshold before log2 transformation.

```r
source("scripts/log2_normalization.R")
norm_counts <- counts(dds, normalized = TRUE)
filtered <- filter_transcripts_per_cell(norm_counts, sample_groups,
                                        cells_per_sample = 2000,
                                        min_tpc = 0.01)
```

**How log2 relates to rlog and VST:** rlog is NOT the same as log2(normalized counts). rlog fits a GLM with shrinkage priors — for low-count genes, values are shrunken toward the intercept, stabilizing variance. For high-count genes, rlog approximates log2(normalized counts) because shrinkage is minimal. VST uses a different variance-stabilizing function but is also asymptotically log2 for large counts. DESeq2 also provides `normTransform(dds)` which computes `log2(normalized_counts + 1)` and returns a `DESeqTransform` object — use it when a pseudocount of 1 is acceptable. The functions in `log2_normalization.R` offer the "remove zeros" approach (no pseudocount) that `normTransform()` does not support.

**Reference:** Burton et al. (2024) *Immunity* 57:1586-1602.e10 ([doi:10.1016/j.immuni.2024.05.023](https://doi.org/10.1016/j.immuni.2024.05.023)) used this approach for tissue Treg RNA-seq PCA (GitHub: AdrianListon/TissueTregs).

### Decision Tree

```
What is the downstream task?
├─ Differential expression → DO NOT transform (use raw counts with DESeq())
└─ PCA / clustering / heatmap → Choose transformation:
    ├─ Standard approach (recommended for most users):
    │   ├─ n > 30 → vst()
    │   └─ n ≤ 30 → rlog()
    └─ Log2 normalized counts (special cases only):
        └─ ONLY when replicating a published analysis that used this method,
           OR after aggressive pre-filtering removed most low-count genes
           ⚠ No variance stabilization — low-count noise dominates PCA
```

**When to use blind = TRUE (VST/rlog only):** Exploratory analysis without design, initial QC, want natural clustering

---

## Decision 2: LFC Shrinkage Method

**When:** After results(), before ranking/plotting
**Question:** Which shrinkage method?

### Option A: apeglm (Recommended)

**Use when:** Ranking genes, publication plots, want best performance

**Pros:** Best shrinkage, preserves large LFC, accurate posteriors
**Cons:** Requires `coef` (not `contrast`), needs package, slightly slower

```r
library(apeglm)
resLFC <- lfcShrink(dds, coef = resultsNames(dds)[2], type = 'apeglm')
```

**Note:** Cannot use contrast specification
```r
# Works:
res <- lfcShrink(dds, coef = 'condition_treated_vs_control', type = 'apeglm')

# Doesn't work:
# res <- lfcShrink(dds, contrast = c('condition', 'treated', 'control'), type = 'apeglm')
```

### Option B: ashr

**Use when:** Large datasets (apeglm slow), need contrast specification

**Pros:** Good performance, fast, works with contrasts
**Cons:** May over-shrink large FC, inferior to apeglm for ranking

```r
resLFC <- lfcShrink(dds, coef = 'condition_treated_vs_control', type = 'ashr')
# Also works with contrasts
resLFC <- lfcShrink(dds, contrast = c('condition', 'treated', 'control'), type = 'ashr')
```

### Option C: normal (Legacy)

**Use when:** Backward compatibility, no apeglm/ashr

**Pros:** Fast, simple, no extra packages
**Cons:** Inferior shrinkage, not recommended for new analyses

```r
resLFC <- lfcShrink(dds, coef = 'condition_treated_vs_control', type = 'normal')
```

### Shrinkage vs Unshrunk

**Use SHRUNK for:**
- ✓ Ranking genes by effect size
- ✓ Visualization (volcano, MA plots, heatmaps)
- ✓ GSEA
- ✓ Selecting top genes for validation

**Use UNSHRUNK for:**
- ✓ Hypothesis testing (p-values)
- ✓ Reporting fold changes with CI
- ✓ Testing specific FC thresholds

```r
res <- results(dds)  # Unshrunk: hypothesis testing
resLFC <- lfcShrink(dds, coef = 'condition_treated_vs_control', type = 'apeglm')  # Shrunk: ranking/viz
```

---

## Decision 3: Design Formula

**When:** Before creating DESeqDataSet
**Question:** Include covariates in design?

### Option A: Simple (`~ condition`)

**Use when:** No batch effects, single factor, exploratory

**Pros:** Straightforward, easy to explain, maximum power for simple comparisons
**Cons:** Lower power if batch effects present, can't control confounders

```r
dds <- DESeqDataSetFromMatrix(counts, coldata, design = ~ condition)
```

**Check first:**
```r
vsd <- vst(dds, blind = TRUE)
plotPCA(vsd, intgroup = "condition")
# Samples cluster by condition? → Use simple design
# Samples cluster by batch? → Use multi-factor design
```

### Option B: Multi-Factor (`~ batch + condition`)

**Use when:** Known batch effects, sequencing runs, PCA shows batch clustering

**Pros:** Controls confounders, higher power with batch, more accurate FC
**Cons:** Requires balanced design, uses degrees of freedom, complex interpretation

```r
dds <- DESeqDataSetFromMatrix(counts, coldata, design = ~ batch + condition)
res <- results(dds, name = 'condition_treated_vs_control')
```

**Critical:** Design must not be confounded
```r
# ✅ Works (balanced):
# batch 1: control, control, treated, treated
# batch 2: control, control, treated, treated

# ❌ Fails (confounded):
# batch 1: control, control
# batch 2: treated, treated
```

### Option C: Paired (`~ individual + condition`)

**Use when:** Same individuals before/after, matched pairs (tumor/normal)

**Pros:** Controls individual effects, higher power, reduces noise
**Cons:** Requires paired structure, can't test between-individual effects

```r
coldata <- data.frame(
  individual = factor(rep(1:5, each = 2)),
  condition = factor(rep(c('before', 'after'), 5))
)
dds <- DESeqDataSetFromMatrix(counts, coldata, design = ~ individual + condition)
```

### Option D: Interaction (`~ genotype * treatment`)

**Use when:** Test if treatment effect differs by genotype, gene × environment

**Pros:** Tests interactions, identifies genotype-specific responses
**Cons:** Requires more samples (n ≥ 4 per group), complex interpretation

```r
design = ~ genotype + treatment + genotype:treatment
dds <- DESeq(dds)

# Main effects
res_genotype <- results(dds, name = 'genotype_KO_vs_WT')
res_treatment <- results(dds, name = 'treatment_drug_vs_vehicle')

# Interaction: Does treatment effect differ by genotype?
res_interaction <- results(dds, name = 'genotypeKO.treatmentdrug')
```

### Decision Tree

```
Known batch effects or technical covariates?
├─ YES → Balanced design (batches in both conditions)?
│        ├─ YES → ~ batch + condition
│        └─ NO → Cannot adjust (confounded); consider batch correction
│
└─ NO → Paired samples (before/after, tumor/normal)?
        ├─ YES → ~ individual + condition
        └─ NO → Testing interactions?
                ├─ YES → ~ genotype * treatment
                └─ NO → ~ condition
```

### Checking Design

```r
# Check if full rank (not confounded)
design_matrix <- model.matrix(~ batch + condition, coldata)
Matrix::rankMatrix(design_matrix) == ncol(design_matrix)  # Should be TRUE

# Check PCA to see if batch correction helps
vsd <- vst(dds, blind = TRUE)
plotPCA(vsd, intgroup = c("condition", "batch"))
```

---

## Decision 4: Pre-Filtering Strategy

**When:** After creating DESeqDataSet, before DESeq()

### Option A: Minimum Total Counts (Standard)

```r
keep <- rowSums(counts(dds)) >= 10
dds <- dds[keep,]
```
**Use:** Standard approach for most datasets

### Option B: Minimum Samples with Counts

```r
keep <- rowSums(counts(dds) >= 10) >= 3  # ≥3 samples with 10+ counts
dds <- dds[keep,]
```
**Use:** Small sample size, want genes expressed in multiple samples

### Option C: Mean Expression

```r
keep <- rowMeans(counts(dds)) >= 10
dds <- dds[keep,]
```
**Use:** Large sample size, filter by average expression

**Recommendation:** Use Option A for most analyses - simple and effective

---

## Decision 5: Significance Thresholds

**When:** Filtering results

### Standard Thresholds

| Threshold | Use Case | Stringency |
|-----------|----------|------------|
| padj < 0.1 | DESeq2 default, discovery | Relaxed |
| padj < 0.05 | Standard, most studies | Moderate |
| padj < 0.01 | High confidence | Stringent |

### Fold Change Thresholds

| Threshold | FC | Use Case |
|-----------|-----|----------|
| \|log2FC\| > 0.5 | 1.4× | Small effect |
| \|log2FC\| > 1 | 2× | Standard |
| \|log2FC\| > 2 | 4× | Large effect |

### Examples

```r
# Standard
sig <- subset(res, padj < 0.05 & abs(log2FoldChange) > 1)

# Discovery
sig <- subset(res, padj < 0.1)

# High confidence
sig <- subset(res, padj < 0.01 & abs(log2FoldChange) > 2)
```

---

## Quick Reference Table

| Decision | Use This | When |
|----------|----------|------|
| **Transformation** | vst() | n > 30 samples |
| | rlog() | n ≤ 30 samples |
| | log2(normalized) | Special cases: replicating published analyses, after aggressive pre-filtering |
| **LFC Shrinkage** | apeglm | Ranking/visualization |
| | ashr | Need contrasts/speed |
| **Design** | ~ condition | Simple, no batch |
| | ~ batch + condition | Known batch effects |
| | ~ individual + condition | Paired samples |
| | ~ genotype * treatment | Interactions |
| **Pre-filtering** | rowSums >= 10 | Standard |
| **Significance** | padj < 0.05 & \|log2FC\| > 1 | Standard |

---

## Best Practices

1. **Always check PCA first** before finalizing design formula
2. **Use shrinkage for visualization**, unshrunk for testing
3. **Document decisions** in analysis code
4. **Report both** unshrunk and shrunk results
5. **Validate top hits** with independent method
