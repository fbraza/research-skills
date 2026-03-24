# Basic DESeq2 workflow for differential expression analysis
#
# This script demonstrates the complete DESeq2 workflow using example data.
# For your own data, replace the data loading section with your count matrix and metadata.

library(DESeq2)
library(apeglm)

# =============================================================================
# OPTIONAL: PARALLEL PROCESSING (recommended for large datasets)
# Speeds up DESeq() dispersion estimation and GLM fitting.
# Enable by uncommenting the three lines below.
# =============================================================================
# library(BiocParallel)
# n_cores <- max(1L, floor(parallel::detectCores() * 0.75))
# register(MulticoreParam(n_cores))

# =============================================================================
# STEP 1: LOAD DATA
# =============================================================================

# --- OPTION A: Use example dataset (for testing) ---
source("scripts/load_example_data.R")
data <- load_pasilla_data()  # Installs pasilla if needed
counts <- data$counts
coldata <- data$coldata

# Prepare coldata for simple two-group comparison
coldata <- coldata[, "condition", drop = FALSE]  # Keep only condition column

# --- OPTION B: Load your own data (uncomment and modify) ---
# counts <- read.csv("path/to/counts.csv", row.names = 1)
# coldata <- read.csv("path/to/metadata.csv", row.names = 1)
# counts <- as.matrix(counts)  # Ensure counts is a matrix

# --- OPTION C: Use airway dataset (alternative example) ---
# source("scripts/load_example_data.R")
# data <- load_airway_data()
# counts <- data$counts
# coldata <- data$coldata[, "dex", drop = FALSE]
# colnames(coldata) <- "condition"  # Rename for consistency

# =============================================================================
# STEP 2: VALIDATE DATA (CRITICAL - prevents errors downstream)
# =============================================================================

cat("=== Data Validation ===\n")
if (!all(colnames(counts) %in% rownames(coldata))) {
  missing <- setdiff(colnames(counts), rownames(coldata))
  stop("Sample ID mismatch!\n",
       "  Count columns not in metadata: ", paste(head(missing, 5), collapse = ", "))
}

# Reorder coldata to match counts
coldata <- coldata[colnames(counts), , drop = FALSE]

cat("✓ Sample IDs validated\n")
cat("  Dimensions:", nrow(counts), "genes x", ncol(counts), "samples\n")
cat("  Groups:", paste(table(coldata$condition), "samples per group"), "\n\n")

# =============================================================================
# STEP 3: CREATE DESeqDataSet
# =============================================================================

cat("=== Creating DESeqDataSet ===\n")
dds <- DESeqDataSetFromMatrix(
  countData = counts,
  colData = coldata,
  design = ~ condition
)

cat("✓ DESeqDataSet created\n")
cat("  Design: ~ condition\n\n")

# =============================================================================
# STEP 4: PRE-FILTER LOW-COUNT GENES (REQUIRED - improves power)
# =============================================================================
#
# Two filtering strategies are available:
#
# A) rowSums filter (default) — fast, sample-count independent minimum.
#    Rule of thumb: keep genes with at least 10 counts across ALL samples.
#    Weakness: threshold scales poorly with unbalanced or multi-group designs
#    (e.g., 3 samples × 2 counts = 6 fails, while 12 samples × 1 count = 12 passes).
#
# B) CPM-based filter (recommended for multi-group / unbalanced designs) —
#    keeps genes that are detectably expressed (CPM >= min_cpm) in ALL
#    replicates of AT LEAST ONE condition group. This is more biologically
#    principled: a gene counts as expressed if it clears the threshold
#    consistently within at least one group, regardless of total sample count.
#
# Use both in sequence: rowSums first (remove absolute zeros quickly),
# then CPM to enforce per-group expression support.

#' CPM-based expression filter
#'
#' Keep genes with CPM >= min_cpm in all (or min_samples_per_group) replicates
#' of at least one condition group. More robust than rowSums for unbalanced
#' or multi-group designs.
#'
#' @param dds DESeqDataSet (before DESeq())
#' @param min_cpm CPM threshold for expression (default: 0.5)
#' @param condition_col colData column name for grouping (default: "condition")
#' @param min_samples_per_group Minimum replicates that must pass; NULL = all (default: NULL)
#' @return Filtered DESeqDataSet
filter_by_cpm <- function(dds, min_cpm = 0.5, condition_col = "condition",
                          min_samples_per_group = NULL) {
  lib_sizes <- colSums(counts(dds)) / 1e6
  cpm_mat   <- sweep(counts(dds), 2, lib_sizes, FUN = "/")
  groups    <- factor(colData(dds)[[condition_col]])

  if (length(levels(groups)) == 0) {
    warning("No groups found in condition column '", condition_col, "'. Returning dds unchanged.")
    return(dds)
  }

  keep <- Reduce("|", lapply(levels(groups), function(g) {
    idx   <- which(groups == g)
    n_req <- if (is.null(min_samples_per_group)) length(idx) else min_samples_per_group
    if (!is.null(min_samples_per_group) && min_samples_per_group > length(idx)) {
      warning(sprintf("min_samples_per_group (%d) > group size for '%s' (%d). Using group size.",
                      min_samples_per_group, g, length(idx)))
      n_req <- length(idx)
    }
    rowSums(cpm_mat[, idx, drop = FALSE] >= min_cpm) >= n_req
  }))

  cat("CPM filter (>= ", min_cpm, " CPM in all replicates of >= 1 group):\n", sep = "")
  cat("  Kept:", sum(keep), "  Removed:", sum(!keep), "\n")
  dds[keep, ]
}

cat("=== Pre-filtering Genes ===\n")
cat("Genes before filtering:", nrow(dds), "\n")

# --- OPTION A: rowSums filter (default, suitable for simple 2-group designs) ---
keep <- rowSums(counts(dds)) >= 10
dds <- dds[keep, ]
cat("After rowSums >= 10 filter:", nrow(dds), "genes (removed", sum(!keep), ")\n")

# --- OPTION B: CPM-based filter (recommended for multi-group / unbalanced designs) ---
# Uncomment to use instead of or in addition to the rowSums filter above.
# dds <- filter_by_cpm(dds, min_cpm = 0.5, condition_col = "condition")

cat("Genes after filtering:", nrow(dds), "\n\n")

# =============================================================================
# STEP 5: SET REFERENCE LEVEL (REQUIRED - ensures correct comparison direction)
# =============================================================================

cat("=== Setting Reference Level ===\n")
# Set first level alphabetically as reference (change as needed for your data)
ref_level <- levels(dds$condition)[1]
dds$condition <- relevel(dds$condition, ref = ref_level)

cat("✓ Reference level:", ref_level, "\n")
cat("  Comparison:", levels(dds$condition)[2], "vs", ref_level, "\n")
cat("  (Positive log2FC = higher in", levels(dds$condition)[2], ")\n\n")

# =============================================================================
# STEP 6: RUN DESeq2 ANALYSIS
# =============================================================================

cat("=== Running DESeq2 ===\n")
cat("This performs:\n")
cat("  1. Size factor normalization\n")
cat("  2. Dispersion estimation\n")
cat("  3. Negative binomial GLM fitting\n")
cat("  4. Wald test for differential expression\n\n")

set.seed(42)  # Reproducibility: DESeq() uses stochastic dispersion estimation
dds <- DESeq(dds)

cat("✓ DESeq2 analysis completed\n\n")

# =============================================================================
# STEP 7: EXTRACT RESULTS
# =============================================================================

cat("=== Extracting Results ===\n")

# Get coefficient name for shrinkage
coef_name <- resultsNames(dds)[2]  # First coefficient after Intercept

# Unshrunk results (for hypothesis testing)
res <- results(dds, name = coef_name)

# Shrunk results (for visualization and ranking)
resLFC <- lfcShrink(dds, coef = coef_name, type = "apeglm")

cat("✓ Results extracted\n")
cat("  Coefficient:", coef_name, "\n\n")

# =============================================================================
# STEP 8: SUMMARIZE RESULTS
# =============================================================================

cat("=== Results Summary ===\n")
summary(res, alpha = 0.05)

# Count significant genes
# Use res$padj for significance decisions (Wald test p-values).
# resLFC uses apeglm which recomputes padj under a different model — use it
# only for log2FoldChange values (visualization/ranking), not for thresholding.
sig_genes <- subset(res, padj <= 0.05 & abs(log2FoldChange) >= 1)
cat("\n=== Significant Genes (padj <= 0.05, |log2FC| >= 1) ===\n")
cat("Total significant:", nrow(sig_genes), "\n")
cat("  Upregulated:", sum(sig_genes$log2FoldChange > 0), "\n")
cat("  Downregulated:", sum(sig_genes$log2FoldChange < 0), "\n\n")

# Show top 10 genes by adjusted p-value (use shrunk LFC for display only)
cat("Top 10 genes by significance:\n")
sig_genes_sorted <- sig_genes[order(sig_genes$padj), ]
sig_lfc <- resLFC[rownames(sig_genes_sorted), ]
display_df <- data.frame(
  baseMean       = sig_genes_sorted$baseMean,
  log2FoldChange = sig_lfc$log2FoldChange,  # shrunk LFC for display
  padj           = sig_genes_sorted$padj
)
print(head(display_df, 10))

cat("\n✓ Basic workflow completed successfully!\n")
cat("\nNext steps:\n")
cat("  - Check QC plots: use scripts/qc_plots.R\n")
cat("  - Export results: use scripts/export_results.R\n")
cat("  - Filter genes: use de-results-to-gene-lists skill\n")
cat("  - Create plots: use de-results-to-plots skill\n")
