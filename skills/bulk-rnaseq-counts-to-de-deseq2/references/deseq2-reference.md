# DESeq2 Complete Reference

**Workflow:** bulk-rnaseq-counts-to-de-deseq2  
**Purpose:** Complete code patterns, alternative input formats, and advanced usage examples for DESeq2.

---

## Alternative Input Formats

### From CSV/TSV Count Matrix
```r
# Load count matrix (genes × samples, raw integer counts)
counts <- read.csv("counts.csv", row.names = 1)
counts <- as.matrix(counts)
mode(counts) <- "integer"  # Ensure integer type

# Load metadata
coldata <- read.csv("metadata.csv", row.names = 1)

# Validate sample ID match
stopifnot(all(colnames(counts) == rownames(coldata)))
```

### From Salmon/Kallisto via tximport
```r
library(tximport)
library(DESeq2)

# Load tximport object
files <- file.path("salmon_output", coldata$sample, "quant.sf")
names(files) <- coldata$sample

txi <- tximport(files, type = "salmon", tx2gene = tx2gene_df)

# Create DESeqDataSet from tximport (handles non-integer counts correctly)
dds <- DESeqDataSetFromTximport(txi, colData = coldata, design = ~ condition)
```

### From featureCounts / HTSeq
```r
# featureCounts output: first 6 columns are metadata, rest are counts
fc <- read.table("featureCounts_output.txt", header = TRUE, skip = 1, row.names = 1)
counts <- fc[, 6:ncol(fc)]
colnames(counts) <- gsub(".bam", "", colnames(counts))  # Clean sample names
```

### From SummarizedExperiment
```r
library(SummarizedExperiment)
se <- readRDS("summarized_experiment.rds")
dds <- DESeqDataSet(se, design = ~ condition)
```

---

## Design Formulas

### Simple two-group comparison
```r
dds <- DESeqDataSetFromMatrix(countData = counts,
                               colData = coldata,
                               design = ~ condition)
dds$condition <- relevel(dds$condition, ref = "control")  # Set reference
```

### Multi-factor with batch correction
```r
# Requires balanced design (batches present in both conditions)
dds <- DESeqDataSetFromMatrix(countData = counts,
                               colData = coldata,
                               design = ~ batch + condition)
```

### Paired samples
```r
# individual = patient/subject ID
dds <- DESeqDataSetFromMatrix(countData = counts,
                               colData = coldata,
                               design = ~ individual + condition)
```

### Interaction model (test genotype × treatment interaction)
```r
dds <- DESeqDataSetFromMatrix(countData = counts,
                               colData = coldata,
                               design = ~ genotype + treatment + genotype:treatment)
# Extract interaction term
res_interaction <- results(dds, name = "genotypeKO.treatmentDrug")
```

---

## Extracting Results

### Standard extraction
```r
dds <- DESeq(dds)
resultsNames(dds)  # Show available coefficients

# By coefficient name
res <- results(dds, name = "condition_treated_vs_control")

# By contrast (more explicit, recommended)
res <- results(dds, contrast = c("condition", "treated", "control"))

# With alpha threshold (affects independent filtering)
res <- results(dds, contrast = c("condition", "treated", "control"), alpha = 0.05)
```

### Multiple comparisons
```r
# All pairwise comparisons
conditions <- levels(dds$condition)
comparisons <- combn(conditions, 2, simplify = FALSE)

results_list <- lapply(comparisons, function(comp) {
  results(dds, contrast = c("condition", comp[1], comp[2]))
})
names(results_list) <- sapply(comparisons, paste, collapse = "_vs_")
```

---

## Log Fold Change Shrinkage

```r
library(apeglm)

# apeglm (recommended) — requires coefficient name, not contrast
resLFC <- lfcShrink(dds, coef = "condition_treated_vs_control", type = "apeglm")

# ashr — works with contrast, faster for large datasets
resLFC_ashr <- lfcShrink(dds, contrast = c("condition", "treated", "control"), type = "ashr")

# normal (legacy, not recommended)
resLFC_normal <- lfcShrink(dds, coef = "condition_treated_vs_control", type = "normal")
```

**When to use which:**
- `apeglm`: Default choice, best statistical properties, preserves large LFC
- `ashr`: Use when apeglm is slow (large datasets) or when using contrasts
- `normal`: Legacy only, avoid for new analyses

---

## Filtering Significant Genes

```r
# Standard thresholds
sig_genes <- subset(res, padj <= 0.05 & abs(log2FoldChange) >= 1)

# Relaxed (discovery)
sig_genes_relaxed <- subset(res, padj <= 0.1 & abs(log2FoldChange) >= 0.5)

# Stringent (validation)
sig_genes_strict <- subset(res, padj <= 0.01 & abs(log2FoldChange) >= 2)

# Upregulated only
up_genes <- subset(res, padj <= 0.05 & log2FoldChange >= 1)

# Downregulated only
down_genes <- subset(res, padj <= 0.05 & log2FoldChange <= -1)
```

**CRITICAL:** Always use `padj` (adjusted p-value), never raw `pvalue`.

---

## Normalization and Transformations

```r
# Size factor normalization (for differential expression)
dds <- estimateSizeFactors(dds)
normalized_counts <- counts(dds, normalized = TRUE)

# VST — for visualization, clustering, heatmaps (>30 samples)
vst_data <- vst(dds, blind = FALSE)
vst_matrix <- assay(vst_data)

# rlog — for visualization, clustering, heatmaps (<30 samples)
rlog_data <- rlog(dds, blind = FALSE)
rlog_matrix <- assay(rlog_data)

# blind = FALSE uses the design to improve transformation (recommended)
# blind = TRUE for QC when you don't want design to influence transformation
```

---

## Pre-filtering

```r
# Remove genes with very low counts (speeds up analysis, improves power)
keep <- rowSums(counts(dds) >= 10) >= min(table(dds$condition))
dds <- dds[keep, ]

# Alternative: at least 1 CPM in at least 2 samples
library(edgeR)
keep <- filterByExpr(counts(dds), group = dds$condition)
dds <- dds[keep, ]
```

---

## Independent Filtering

DESeq2 automatically applies independent filtering (removes low-mean genes to improve power). To inspect:

```r
# Check filtering threshold
metadata(res)$filterThreshold

# Genes removed by filtering have padj = NA
sum(is.na(res$padj))

# Disable independent filtering (not recommended)
res_nofilter <- results(dds, independentFiltering = FALSE)
```

---

## Exporting Results

```r
# Full results table
res_df <- as.data.frame(res)
res_df$gene <- rownames(res_df)
write.csv(res_df, "deseq2_results.csv", row.names = FALSE)

# Significant genes only
sig_df <- as.data.frame(sig_genes)
sig_df$gene <- rownames(sig_df)
write.csv(sig_df, "deseq2_significant.csv", row.names = FALSE)

# Normalized counts
write.csv(normalized_counts, "normalized_counts.csv")

# Save DESeqDataSet for downstream use
saveRDS(dds, "dds_object.rds")
```

---

## Session Info (for reproducibility)

Always report:
```r
sessionInfo()
# Key: R version, DESeq2 version, apeglm version
```

---

## Key References

- **DESeq2 paper:** Love MI, Huber W, Anders S (2014). *Genome Biology* 15:550. https://doi.org/10.1186/s13059-014-0550-8
- **apeglm paper:** Zhu A, Ibrahim JG, Love MI (2019). *Bioinformatics* 35:2084-2092.
- **DESeq2 vignette:** https://bioconductor.org/packages/release/bioc/vignettes/DESeq2/inst/doc/DESeq2.html
- **Bioconductor page:** https://bioconductor.org/packages/DESeq2
