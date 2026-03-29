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

#' Apply log2 transformation to size-factor normalized counts
#'
#' Computes log2(normalized counts) with configurable zero handling.
#' This is a simpler alternative to VST/rlog that preserves absolute
#' expression magnitude but does not stabilize variance.
#'
#' @param dds DESeqDataSet object (must have size factors estimated)
#' @param zero_handling How to handle zeros: "remove" (default, drop genes
#'   with any zero across all samples), "pseudocount" (add 0.5 before log2),
#'   or "na" (set to NA, keep all genes)
#' @param pseudocount Value to add before log2 when zero_handling = "pseudocount"
#'   (default: 0.5)
#'
#' @return A list with:
#'   \item{matrix}{Numeric matrix of log2 values (genes × samples)}
#'   \item{genes_removed}{Number of genes removed (if zero_handling = "remove")}
#'   \item{genes_retained}{Number of genes in the output matrix}
#'   \item{method}{Description of the transformation}
#'
#' @export
apply_log2_normalization <- function(dds, zero_handling = "remove",
                                     pseudocount = 0.5) {
  cat("=== Log2 Normalized Counts ===\n")

  # Validate inputs
  stopifnot("dds must be a DESeqDataSet" = is(dds, "DESeqDataSet"))
  stopifnot("Size factors must be estimated first" =
              !is.null(sizeFactors(dds)) || !is.null(normalizationFactors(dds)))
  stopifnot("zero_handling must be 'remove', 'pseudocount', or 'na'" =
              zero_handling %in% c("remove", "pseudocount", "na"))

  norm_counts <- counts(dds, normalized = TRUE)
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
    # zero_handling == "remove" (paper approach)
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


#' Biological transcript-per-cell filter
#'
#' Filters genes based on a minimum number of transcripts per cell.
#' Used when the number of cells per sample is known (e.g., from FACS sorting).
#'
#' This filter was introduced by Burton et al. (2024, Immunity) for tissue Treg
#' RNA-seq where 2000 cells were sorted per sample. It requires that at least
#' one condition group has the gene expressed above threshold in ALL replicates.
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
