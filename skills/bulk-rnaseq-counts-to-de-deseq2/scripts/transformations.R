# Data transformations for DESeq2
# Variance stabilization for visualization and clustering

library(DESeq2)

# Resolve script directory at source-time for sibling script loading.
# Walk frames top-down to find the ofile of THIS source() call.
.transformations_script_dir <- local({
  for (i in sys.nframe():1L) {
    ofile <- sys.frame(i)$ofile
    if (!is.null(ofile))
      return(normalizePath(dirname(ofile), mustWork = TRUE))
  }
  normalizePath(".", mustWork = TRUE)
})

#' Get normalized counts from DESeqDataSet
#'
#' @param dds DESeqDataSet object (after DESeq())
#'
#' @return Matrix of size-factor normalized counts
#' @export
get_normalized_counts <- function(dds) {
    cat("Extracting normalized counts...\n")
    norm_counts <- counts(dds, normalized = TRUE)

    # Show size factors
    cat("Size factors:\n")
    print(sizeFactors(dds))
    cat("\n")

    return(norm_counts)
}

#' Apply variance stabilizing transformation
#'
#' @param dds DESeqDataSet object (after DESeq())
#' @param blind Whether to estimate dispersions ignoring design (default: FALSE)
#'
#' @return DESeqTransform object with VST values
#' @export
apply_vst <- function(dds, blind = FALSE) {
    cat("Applying variance stabilizing transformation (VST)...\n")

    if (blind) {
        cat("  blind = TRUE: Estimating dispersions without design\n")
    } else {
        cat("  blind = FALSE: Using design for transformation\n")
    }

    vsd <- vst(dds, blind = blind)

    cat("  Recommended for: >30 samples\n")
    cat("  VST transformation complete\n\n")

    return(vsd)
}

#' Apply regularized log transformation
#'
#' @param dds DESeqDataSet object (after DESeq())
#' @param blind Whether to estimate dispersions ignoring design (default: FALSE)
#'
#' @return DESeqTransform object with rlog values
#' @export
apply_rlog <- function(dds, blind = FALSE) {
    cat("Applying regularized log transformation (rlog)...\n")

    if (blind) {
        cat("  blind = TRUE: Estimating dispersions without design\n")
    } else {
        cat("  blind = FALSE: Using design for transformation\n")
    }

    if (ncol(dds) > 100) {
        warning("rlog is slow for large datasets (>100 samples). Consider using VST instead.")
    }

    rld <- rlog(dds, blind = blind)

    cat("  Recommended for: <30 samples\n")
    cat("  rlog transformation complete\n\n")

    return(rld)
}

#' Choose and apply appropriate transformation
#'
#' @param dds DESeqDataSet object (after DESeq())
#' @param method Transformation method: 'auto', 'vst', 'rlog', or 'log2'
#'   (default: 'auto'). 'log2' uses log2(normalized counts) — see
#'   scripts/log2_normalization.R for details and trade-offs.
#' @param blind Whether to estimate dispersions ignoring design (default: FALSE).
#'   Only applies to 'vst' and 'rlog' methods.
#' @param zero_handling For method = "log2" only: how to handle zeros.
#'   "remove" (default), "pseudocount", or "na". See apply_log2_normalization().
#'
#' @return DESeqTransform object (for vst/rlog) or list (for log2, see
#'   apply_log2_normalization return value)
#' @export
transform_counts <- function(dds, method = "auto", blind = FALSE,
                             zero_handling = "remove") {
    n_samples <- ncol(dds)

    cat("=== Transforming Counts ===\n")
    cat("Samples:", n_samples, "\n\n")

    if (method == "auto") {
        if (n_samples > 30) {
            cat("Auto-selecting VST (>30 samples)\n\n")
            return(apply_vst(dds, blind = blind))
        } else {
            cat("Auto-selecting rlog (<30 samples)\n\n")
            return(apply_rlog(dds, blind = blind))
        }
    } else if (method == "vst") {
        return(apply_vst(dds, blind = blind))
    } else if (method == "rlog") {
        return(apply_rlog(dds, blind = blind))
    } else if (method == "log2") {
        source(file.path(.transformations_script_dir,
                         "log2_normalization.R"), local = TRUE)
        return(apply_log2_normalization(dds, zero_handling = zero_handling))
    } else {
        stop("method must be 'auto', 'vst', 'rlog', or 'log2'")
    }
}

#' Extract transformed values as matrix
#'
#' @param transformed DESeqTransform object (from vst or rlog)
#'
#' @return Matrix of transformed values
#' @export
get_transformed_matrix <- function(transformed) {
    return(assay(transformed))
}

#' Compare VST and rlog transformations
#'
#' @param dds DESeqDataSet object (after DESeq())
#'
#' @export
compare_transformations <- function(dds) {
    cat("=== Comparing Transformations ===\n\n")

    # Get both transformations
    cat("Computing VST...\n")
    vsd <- vst(dds, blind = FALSE)

    cat("Computing rlog...\n")
    if (ncol(dds) > 100) {
        cat("⚠ Warning: rlog may be slow for large datasets\n")
    }
    rld <- rlog(dds, blind = FALSE)

    # Extract matrices
    vsd_mat <- assay(vsd)
    rld_mat <- assay(rld)

    # Compare
    cat("\n=== Comparison ===\n")
    cat("Correlation between VST and rlog:", cor(vsd_mat[,1], rld_mat[,1]), "\n")

    # Plot comparison
    par(mfrow = c(1, 2))

    # VST
    plot(vsd_mat[,1], vsd_mat[,2],
         main = "VST",
         xlab = colnames(vsd_mat)[1],
         ylab = colnames(vsd_mat)[2],
         pch = 16, cex = 0.5)

    # rlog
    plot(rld_mat[,1], rld_mat[,2],
         main = "rlog",
         xlab = colnames(rld_mat)[1],
         ylab = colnames(rld_mat)[2],
         pch = 16, cex = 0.5)

    par(mfrow = c(1, 1))

    cat("\nRecommendation:\n")
    if (ncol(dds) > 30) {
        cat("  Use VST for your dataset (n =", ncol(dds), "samples)\n")
    } else {
        cat("  Use rlog for your dataset (n =", ncol(dds), "samples)\n")
    }
}

# Transformation decision guide
#' Print transformation decision guide
#'
#' @export
print_transformation_guide <- function() {
    cat("=== Transformation Decision Guide ===\n\n")
    cat("WHEN TO USE TRANSFORMATIONS:\n")
    cat("  ✓ For visualization (PCA, heatmaps)\n")
    cat("  ✓ For clustering analysis\n")
    cat("  ✓ When methods assume homoscedasticity\n")
    cat("  ✗ NOT for differential expression (use raw counts)\n\n")

    cat("VST (Variance Stabilizing Transformation):\n")
    cat("  • Use when: n > 30 samples\n")
    cat("  • Pros: Fast, suitable for large datasets\n")
    cat("  • Cons: Less accurate for very small samples\n")
    cat("  • Function: vst(dds, blind = FALSE)\n\n")

    cat("RLOG (Regularized Log Transformation):\n")
    cat("  • Use when: n < 30 samples\n")
    cat("  • Pros: Better stabilization for small samples\n")
    cat("  • Cons: Slow for large datasets (>100 samples)\n")
    cat("  • Function: rlog(dds, blind = FALSE)\n\n")

    cat("LOG2 NORMALIZED COUNTS (special cases only):\n")
    cat("  ⚠ WARNING: Not recommended as default for PCA/clustering/heatmaps.\n")
    cat("    No variance stabilization — low-count gene noise dominates ordination.\n")
    cat("    Use VST or rlog unless you have a specific reason for log2.\n")
    cat("  • Use when: Replicating a published analysis that used this method,\n")
    cat("              or after aggressive pre-filtering removed low-count genes\n")
    cat("  • Pros: Simple, interpretable, preserves absolute magnitude\n")
    cat("  • Cons: No variance stabilization, genes with zeros removed (30-60% loss)\n")
    cat("  • Function: transform_counts(dds, method = 'log2')\n")
    cat("  • See: scripts/log2_normalization.R for details\n")
    cat("  • Note: DESeq2 also provides normTransform(dds) which computes\n")
    cat("          log2(normalized + 1) and returns a DESeqTransform object.\n")
    cat("          Use apply_log2_normalization() when you need the 'remove zeros'\n")
    cat("          approach (no pseudocount) or other zero_handling modes.\n\n")

    cat("BLIND PARAMETER (VST/rlog only):\n")
    cat("  • blind = FALSE: Use design formula (recommended)\n")
    cat("  • blind = TRUE: Ignore design (exploratory only)\n\n")
}

# Example usage:
# library(DESeq2)
# source("scripts/transformations.R")
#
# # After DESeq2 analysis
# dds <- DESeq(dds)
#
# # Show decision guide
# print_transformation_guide()
#
# # Auto-select transformation
# transformed <- transform_counts(dds, method = "auto")
# transformed_matrix <- get_transformed_matrix(transformed)
#
# # Or manually choose
# vsd <- apply_vst(dds, blind = FALSE)
# rld <- apply_rlog(dds, blind = FALSE)
#
# # Compare both methods
# compare_transformations(dds)
