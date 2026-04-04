# Log2 normalized counts transformation for DESeq2
# Special-case alternative to VST/rlog — NOT a general replacement
#
# Used in some published analyses (e.g., Burton et al. 2024) where aggressive
# pre-filtering (transcripts-per-cell) already removed most low-count genes.
#
# WARNING: For routine PCA, clustering, and heatmaps, use VST or rlog instead.
# log2 provides NO variance stabilization — low-count genes with high Poisson
# noise will dominate ordination, and the "remove zeros" approach can discard
# 30-60% of genes, introducing survivorship bias.
#
# CORRECT ORDER (per Burton et al. 2024):
#   1. Normalize (DESeq2 size factors)
#   2. Filter by transcripts-per-cell (biological threshold)
#   3. Log2 transform
#   4. Remove genes with any NA (complete.cases)
#
# When to use:
#   - Replicating a published analysis that used this exact method
#   - After aggressive pre-filtering removed most low-count genes
#
# Trade-offs vs VST/rlog:
#   - Simpler and more interpretable
#   - Preserves absolute magnitude differences
#   - No variance stabilization → low-count gene noise dominates PCA/clustering
#   - Genes with zero counts in ANY sample are removed (can lose 30-60% of genes)

library(DESeq2)

#' Filter genes by transcripts-per-cell threshold
#'
#' Biologically motivated filter for sorted cell populations.
#' Keeps genes expressed above threshold in ALL replicates of at least one group.
#'
#' @param norm_counts Matrix of size-factor normalized counts (genes × samples)
#' @param sample_groups Named character vector mapping sample names to group labels
#'   (e.g., c("Blood_T_1" = "Blood_T", "Blood_T_2" = "Blood_T", ...))
#' @param cells_per_sample Number of cells sorted per sample (default: 2000)
#' @param min_tpc Minimum transcripts per cell threshold (default: 0.01)
#'
#' @return Filtered normalized count matrix
#'
#' @export
filter_transcripts_per_cell <- function(norm_counts, sample_groups,
                                         cells_per_sample = 2000,
                                         min_tpc = 0.01) {
  cat("=== Transcript-per-Cell Filter ===\n")
  cat("  Cells per sample:", cells_per_sample, "\n")
  cat("  Min transcripts/cell:", min_tpc, "\n")
  cat("  Input genes:", nrow(norm_counts), "\n")

  groups <- unique(sample_groups)
  n_genes <- nrow(norm_counts)
  selection <- logical(n_genes)

  for (i in seq_len(n_genes)) {
    for (grp in groups) {
      cols <- names(sample_groups)[sample_groups == grp]
      cols <- cols[cols %in% colnames(norm_counts)]
      if (length(cols) > 0 &&
          all((norm_counts[i, cols] / cells_per_sample) > min_tpc)) {
        selection[i] <- TRUE
        break
      }
    }
  }

  filtered <- norm_counts[selection, ]
  cat("  Output genes:", nrow(filtered), "\n")
  cat("  Removed:", n_genes - nrow(filtered), "genes\n\n")
  filtered
}

#' Apply log2 transformation to normalized counts
#'
#' Computes log2(normalized counts) with configurable zero handling.
#' This is a simpler alternative to VST/rlog that preserves absolute
#' expression magnitude but does not stabilize variance.
#'
#' @param norm_counts Matrix of normalized counts (genes × samples)
#' @param zero_handling How to handle zeros: "remove" (default, drop genes
#'   with any zero), "pseudocount" (add 0.5 before log2), or "na" (set to NA)
#' @param pseudocount Value to add before log2 when zero_handling = "pseudocount"
#'
#' @return A list with:
#'   \item{matrix}{Numeric matrix of log2 values (genes × samples)}
#'   \item{genes_removed}{Number of genes removed}
#'   \item{genes_retained}{Number of genes in output}
#'   \item{method}{Description of transformation}
#'
#' @export
apply_log2_transform <- function(norm_counts, zero_handling = "remove",
                                  pseudocount = 0.5) {
  cat("=== Log2 Transformation ===\n")
  n_genes_input <- nrow(norm_counts)
  cat("  Input genes:", n_genes_input, "\n")
  cat("  Samples:", ncol(norm_counts), "\n")
  cat("  Zero handling:", zero_handling, "\n")

  if (zero_handling == "pseudocount") {
    cat("  Pseudocount:", pseudocount, "\n")
    log2_mat <- log2(norm_counts + pseudocount)
    n_removed <- 0
    method_desc <- paste0("log2(norm_counts + ", pseudocount, ")")

  } else if (zero_handling == "na") {
    log2_mat <- log2(norm_counts)
    log2_mat[!is.finite(log2_mat)] <- NA
    n_removed <- 0
    method_desc <- "log2(norm_counts), zeros → NA"

  } else {
    log2_mat <- log2(norm_counts)
    log2_mat[!is.finite(log2_mat)] <- NA
    complete_genes <- complete.cases(log2_mat)
    log2_mat <- log2_mat[complete_genes, ]
    n_removed <- n_genes_input - nrow(log2_mat)
    method_desc <- "log2(norm_counts), genes with any zero removed"
  }

  n_genes_output <- nrow(log2_mat)
  cat("  Output genes:", n_genes_output, "\n")
  if (n_removed > 0) {
    cat("  Genes removed (had zeros):", n_removed,
        sprintf("(%.1f%%)\n", 100 * n_removed / n_genes_input))
  }
  cat("  Method:", method_desc, "\n\n")

  list(
    matrix        = log2_mat,
    genes_removed = n_removed,
    genes_retained = n_genes_output,
    method        = method_desc
  )
}

#' Complete workflow: Normalize → TPC Filter → Log2 → Complete cases
#'
#' This function chains all steps in the correct order as used in
#' Burton et al. (2024, Immunity) for tissue Treg RNA-seq PCA.
#'
#' @param dds DESeqDataSet object (must have size factors estimated)
#' @param sample_groups Named character vector mapping samples to groups
#' @param cells_per_sample Number of cells sorted per sample (default: 2000)
#' @param min_tpc Minimum transcripts per cell (default: 0.01)
#' @param apply_tpc_filter Whether to apply TPC filter (default: TRUE)
#'
#' @return A list with:
#'   \item{matrix}{Log2 transformed matrix (genes × samples)}
#'   \item{genes_initial}{Number of genes before filtering}
#'   \item{genes_after_tpc}{Number of genes after TPC filter}
#'   \item{genes_final}{Number of genes in final matrix}
#'   \item{tpc_applied}{Whether TPC filter was applied}
#'   \item{cells_per_sample}{Cells per sample used}
#'   \item{min_tpc}{Min TPC threshold used}
#'
#' @export
log2_workflow <- function(dds, sample_groups,
                          cells_per_sample = 2000,
                          min_tpc = 0.01,
                          apply_tpc_filter = TRUE) {

  cat("=== Log2 Normalization Workflow ===\n")
  cat("Following Burton et al. (2024, Immunity) methodology\n\n")

  stopifnot("dds must be a DESeqDataSet" = is(dds, "DESeqDataSet"))
  stopifnot("Size factors must be estimated first" =
              !is.null(sizeFactors(dds)) || !is.null(normalizationFactors(dds)))

  genes_initial <- nrow(dds)
  cat("Step 1: Extract normalized counts\n")
  norm_counts <- counts(dds, normalized = TRUE)
  cat("  Genes:", nrow(norm_counts), "\n")
  cat("  Samples:", ncol(norm_counts), "\n\n")

  if (apply_tpc_filter) {
    cat("Step 2: Filter by transcripts-per-cell\n")
    filtered_counts <- filter_transcripts_per_cell(
      norm_counts,
      sample_groups,
      cells_per_sample = cells_per_sample,
      min_tpc = min_tpc
    )
    genes_after_tpc <- nrow(filtered_counts)
  } else {
    cat("Step 2: TPC filter skipped (apply_tpc_filter = FALSE)\n")
    filtered_counts <- norm_counts
    genes_after_tpc <- nrow(filtered_counts)
    cat("\n")
  }

  cat("Step 3: Log2 transform\n")
  log2_result <- apply_log2_transform(filtered_counts, zero_handling = "remove")

  cat("Step 4: Complete cases (handled in log2 transform)\n\n")

  cat("=== Summary ===\n")
  cat("  Initial genes:", genes_initial, "\n")
  if (apply_tpc_filter) {
    cat("  After TPC filter:", genes_after_tpc, "\n")
  }
  cat("  Final genes:", log2_result$genes_retained, "\n")
  cat("  Total removed:", genes_initial - log2_result$genes_retained,
      sprintf("(%.1f%%)\n\n", 100 * (genes_initial - log2_result$genes_retained) / genes_initial))

  list(
    matrix           = log2_result$matrix,
    genes_initial    = genes_initial,
    genes_after_tpc  = genes_after_tpc,
    genes_final      = log2_result$genes_retained,
    tpc_applied      = apply_tpc_filter,
    cells_per_sample = cells_per_sample,
    min_tpc          = min_tpc,
    method           = log2_result$method
  )
}


# Legacy function names for backward compatibility
# These wrap the new functions for existing code

#' Apply log2 transformation to DESeqDataSet (legacy wrapper)
#'
#' @param dds DESeqDataSet object
#' @param zero_handling How to handle zeros
#' @param pseudocount Value to add for pseudocount method
#'
#' @return List with transformed matrix and metadata
#'
#' @export
apply_log2_normalization <- function(dds, zero_handling = "remove",
                                      pseudocount = 0.5) {

  norm_counts <- counts(dds, normalized = TRUE)
  apply_log2_transform(norm_counts, zero_handling, pseudocount)
}
