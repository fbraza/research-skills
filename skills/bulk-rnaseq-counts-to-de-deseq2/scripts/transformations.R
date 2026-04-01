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
#'   "remove" (default), "pseudocount", or "na". See apply_log2_transform().
#' @param sample_groups For method = "log2" with TPC filter: named vector mapping
#'   samples to groups (e.g., c("Blood_T_1" = "Blood_T", ...)).
#' @param cells_per_sample For method = "log2" with TPC filter: number of cells
#'   per sample (default: 2000). Ask user for this value if unknown.
#' @param apply_tpc_filter For method = "log2": whether to apply transcript-per-cell
#'   filter before log2 (default: TRUE for biological filtering).
#'
#' @return DESeqTransform object (for vst/rlog) or list (for log2, see
#'   log2_workflow() return value)
#' @export
transform_counts <- function(dds, method = "auto", blind = FALSE,
                              zero_handling = "remove",
                              sample_groups = NULL,
                              cells_per_sample = 2000,
                              apply_tpc_filter = TRUE) {
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
        
        if (apply_tpc_filter) {
            if (is.null(sample_groups)) {
                stop("sample_groups required when apply_tpc_filter = TRUE.\n",
                     "  Provide a named vector mapping samples to groups, e.g.:\n",
                     "  sample_groups = c('Blood_T_1' = 'Blood_T', 'Blood_T_2' = 'Blood_T', ...)")
            }
            return(log2_workflow(dds, sample_groups,
                                  cells_per_sample = cells_per_sample,
                                  min_tpc = 0.01,
                                  apply_tpc_filter = TRUE))
        } else {
            return(apply_log2_normalization(dds, zero_handling = zero_handling))
        }
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
    cat("  • See: scripts/log2_normalization.R for details\n\n")
    
    cat("LOG2 WORKFLOW ORDER (CRITICAL):\n")
    cat("  1. Normalize     → DESeq2 size factors\n")
    cat("  2. TPC filter    → Remove low-expression genes (biological threshold)\n")
    cat("  3. Log2          → Transform to log scale\n")
    cat("  4. Complete cases → Remove genes with any NA\n\n")
    
    cat("LOG2 WITH TPC FILTER (sorted cell populations):\n")
    cat("  • cells_per_sample: Number of cells sorted (default: 2000)\n")
    cat("    → ASK USER if unknown (typical: FACS 500-5000, 10x 1000-10000)\n")
    cat("  • min_tpc: Minimum transcripts per cell (default: 0.01)\n")
    cat("  • sample_groups: Named vector mapping samples to groups (REQUIRED)\n")
    cat("  • Example:\n")
    cat("    sample_groups <- setNames(gsub('_[0-9]+$', '', colnames(counts)),\n")
    cat("                             colnames(counts))\n")
    cat("    result <- transform_counts(dds, method = 'log2',\n")
    cat("                               sample_groups = sample_groups,\n")
    cat("                               cells_per_sample = 2000)\n\n")
    
    cat("LOG2 WITHOUT TPC FILTER (bulk tissue):\n")
    cat("  • result <- transform_counts(dds, method = 'log2',\n")
    cat("                               apply_tpc_filter = FALSE)\n\n")

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
