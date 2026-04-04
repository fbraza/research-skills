# QC Guide for DESeq2 Analysis

**Workflow:** bulk-rnaseq-counts-to-de-deseq2  
**Purpose:** Quality control checks, interpretation of QC plots, and custom plot styling guidance.

---

## Overview

Quality control is a mandatory step before trusting DESeq2 results. The `run_all_qc()` function generates four standard QC plots. This guide explains how to interpret each plot and what actions to take when issues are detected.

---

## QC Plot 1: Dispersion Plot

### What it shows
Gene-wise dispersion estimates vs mean normalized counts. DESeq2 shrinks gene-wise estimates toward a fitted trend.

### How to interpret

| Pattern | Interpretation | Action |
|---------|---------------|--------|
| Gene-wise estimates (black) scattered around fitted trend (red) | ✅ Normal — good fit | Proceed |
| Many genes far above trend | ⚠️ High variability — possible outlier samples | Check PCA, consider removing outliers |
| Fitted trend is flat (no mean-dispersion relationship) | ⚠️ Unusual — may indicate data issues | Check count matrix for normalization artifacts |
| Final estimates (blue) tightly follow trend | ✅ Normal — shrinkage working correctly | Proceed |

### Key check
```r
# Check dispersion fit type
dispersions(dds)[1:5]  # Should be numeric, not NA
```

---

## QC Plot 2: PCA Plot

### What it shows
Principal component analysis of variance-stabilized counts. PC1 and PC2 capture the largest sources of variation.

### How to interpret

| Pattern | Interpretation | Action |
|---------|---------------|--------|
| Samples cluster by condition on PC1 | ✅ Condition is the main source of variation | Proceed |
| Samples cluster by batch on PC1 | ⚠️ Batch effect dominates | Add batch to design: `~ batch + condition` |
| One sample far from its group | ⚠️ Potential outlier | Investigate, consider removing |
| No separation between conditions | ⚠️ Weak signal or wrong comparison | Check metadata, verify condition labels |
| PC1 explains < 20% variance | ⚠️ High heterogeneity | Check for sample swaps, contamination |

### Checking for batch effects
```r
# Color by different metadata variables to identify confounders
plotPCA(vst_data, intgroup = "batch")
plotPCA(vst_data, intgroup = "sex")
plotPCA(vst_data, intgroup = "sequencing_run")
```

---

## QC Plot 3: MA Plot

### What it shows
Log2 fold change (y-axis) vs mean normalized counts (x-axis). Each point is a gene; significant genes are colored.

### How to interpret

| Pattern | Interpretation | Action |
|---------|---------------|--------|
| Points symmetrically distributed around y=0 | ✅ Normal — no systematic bias | Proceed |
| Points skewed above or below y=0 | ⚠️ Systematic bias — possible normalization issue | Check size factors, consider alternative normalization |
| Large LFC only at low counts | ✅ Normal — low-count genes are noisy | Apply LFC shrinkage before visualization |
| After shrinkage: large LFC only at high counts | ✅ Correct behavior of apeglm/ashr | Proceed |
| Many significant genes at low counts | ⚠️ Pre-filtering may be insufficient | Increase pre-filtering threshold |

### Shrinkage effect on MA plot
```r
# Before shrinkage — noisy at low counts
plotMA(res, ylim = c(-5, 5))

# After shrinkage — cleaner, large LFC only at high counts
plotMA(resLFC, ylim = c(-5, 5))
```

---

## QC Plot 4: Volcano Plot

### What it shows
Log2 fold change (x-axis) vs -log10 adjusted p-value (y-axis). Significant genes are highlighted.

### How to interpret

| Pattern | Interpretation | Action |
|---------|---------------|--------|
| Symmetric distribution around x=0 | ✅ Normal — balanced up/down regulation | Proceed |
| All significant genes on one side | ⚠️ Asymmetric response | Check if expected biologically; verify reference level |
| Very few significant genes | ⚠️ Low power or weak effect | Check sample size, consider relaxing thresholds |
| Thousands of significant genes | ⚠️ Possible batch effect or wrong comparison | Check PCA, verify metadata |
| Horizontal band of points | ⚠️ Discrete p-values — may indicate count data issues | Check count matrix |

---

## Additional QC Checks

### Sample distance heatmap
```r
library(pheatmap)
sampleDists <- dist(t(assay(vst_data)))
sampleDistMatrix <- as.matrix(sampleDists)
pheatmap(sampleDistMatrix,
         clustering_distance_rows = sampleDists,
         clustering_distance_cols = sampleDists,
         color = colorRampPalette(c("navy", "white"))(100))
```
**Interpretation:** Samples within the same condition should cluster together and show low distance (dark color = similar).

### Size factor check
```r
sizeFactors(dds)
# Expected range: 0.5 – 2.0
# Outlier: size factor > 3 or < 0.3 → investigate that sample
```

### Library size check
```r
colSums(counts(dds))
# Flag samples with < 1M reads or > 5× the median library size
```

---

## Custom Plot Styling

The `run_all_qc()` script uses ggplot2 + ggprism theme by default. To customize:

### Change color palette
```r
# Edit scripts/qc_plots.R — find the color definitions:
COLORS <- list(
  significant = "#E41A1C",    # Red for significant genes
  not_significant = "#AAAAAA", # Grey for non-significant
  upregulated = "#E41A1C",    # Red for upregulated
  downregulated = "#377EB8",  # Blue for downregulated
  pc1_color = "#4DAF4A"       # Green for PCA points
)
```

### Change significance thresholds for coloring
```r
# In scripts/qc_plots.R, find:
PADJ_THRESHOLD <- 0.05
LFC_THRESHOLD <- 1.0
# Modify these values and re-source the script
```

### Export at higher resolution
```r
# In scripts/qc_plots.R, find ggsave calls:
ggsave("volcano_plot.png", plot = p, dpi = 600, width = 8, height = 6)
# Change dpi from 300 to 600 for publication
```

---

## Troubleshooting QC Issues

### Batch effects detected in PCA
```r
# Option 1: Add batch to design (preferred)
design(dds) <- ~ batch + condition
dds <- DESeq(dds)  # Re-run

# Option 2: Remove batch effect for visualization only (not for DE)
library(limma)
vst_corrected <- removeBatchEffect(assay(vst_data), batch = coldata$batch)
```

### Outlier sample detected
```r
# Remove outlier sample
dds_clean <- dds[, dds$sample != "outlier_sample_id"]
dds_clean <- DESeq(dds_clean)
```

### Cook's distance outliers (individual genes)
```r
# DESeq2 automatically flags genes with outlier counts
# Check how many genes were flagged
sum(is.na(res$pvalue) & !is.na(res$baseMean))

# To disable Cook's filtering (not recommended)
dds <- DESeq(dds, cooksCutoff = FALSE)
```

---

## References

- DESeq2 vignette (QC section): https://bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html
- ggprism documentation: https://cran.r-project.org/package=ggprism
- ggrepel documentation: https://cran.r-project.org/package=ggrepel
- ENCODE RNA-seq QC standards: https://www.encodeproject.org/data-standards/rna-seq/
