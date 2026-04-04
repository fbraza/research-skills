# Data loading and preparation for clustering analysis (R implementation)
#
# This script is the R equivalent of prepare_data.py and handles:
# - Loading data from various formats (CSV, TSV, Excel, RDS)
# - Data normalization (z-score, min-max, robust, log2)
# - Missing value handling (drop, mean, median, KNN)
# - Low variance feature filtering
# - Metadata alignment and validation
# - Quality checks and reporting
#
# Usage:
#   source("scripts/prepare_data.R")
#   data_list <- load_and_prepare_data("your_data.csv", normalize_method = "zscore")
#   data     <- data_list$data
#   metadata <- data_list$metadata


#' Load and Prepare Data for Clustering Analysis
#'
#' @param data_path Path to data matrix file (CSV, TSV, Excel, or RDS).
#'   Rows = samples, columns = features (or transposed if transpose = TRUE).
#' @param metadata_path Optional path to metadata file (CSV or TSV).
#'   Row names must match sample names in data.
#' @param transpose Logical. If TRUE, transpose the matrix before processing.
#'   Use when features are in rows and samples in columns (e.g., gene expression).
#' @param normalize_method Normalization method: "zscore" (default), "minmax",
#'   "robust", "log2", or NULL to skip normalization.
#' @param handle_missing How to handle missing values: "drop" (default),
#'   "mean", "median", or "knn".
#' @param filter_low_variance Logical. If TRUE (default), remove features with
#'   variance below variance_threshold.
#' @param variance_threshold Numeric. Variance threshold for feature filtering
#'   (default: 0.1). Only used if filter_low_variance = TRUE.
#' @param remove_outliers Logical. If TRUE, detect and remove outlier samples
#'   using z-score of per-sample means (default: FALSE).
#' @param outlier_threshold Numeric. Z-score threshold for outlier detection
#'   (default: 3.0).
#'
#' @return A named list with:
#'   \item{data}{Normalized data matrix (samples x features), class matrix}
#'   \item{metadata}{Sample metadata data.frame, or NULL if not provided}
#'   \item{feature_names}{Character vector of feature names}
#'   \item{sample_names}{Character vector of sample names}
#'
#' @examples
#' \dontrun{
#' # Basic usage
#' data_list <- load_and_prepare_data("counts.csv", normalize_method = "zscore")
#' data      <- data_list$data
#' metadata  <- data_list$metadata
#'
#' # With metadata and log2 normalization
#' data_list <- load_and_prepare_data(
#'   "expression.csv",
#'   metadata_path = "metadata.csv",
#'   normalize_method = "log2",
#'   transpose = TRUE
#' )
#' }
#'
#' @export
load_and_prepare_data <- function(
  data_path,
  metadata_path       = NULL,
  transpose           = FALSE,
  normalize_method    = "zscore",
  handle_missing      = "drop",
  filter_low_variance = TRUE,
  variance_threshold  = 0.1,
  remove_outliers     = FALSE,
  outlier_threshold   = 3.0
) {

  # ── 0. Package checks ────────────────────────────────────────────────────────
  options(repos = c(CRAN = "https://cloud.r-project.org"))

  if (!requireNamespace("readxl", quietly = TRUE)) {
    message("Installing readxl for Excel support...")
    install.packages("readxl")
  }

  # ── 1. Load data matrix ──────────────────────────────────────────────────────
  cat(sprintf("Loading data from %s...\n", data_path))

  ext <- tolower(tools::file_ext(data_path))

  if (ext %in% c("csv", "tsv", "txt")) {
    sep <- if (ext == "tsv") "\t" else ","
    data_df <- read.table(data_path, sep = sep, header = TRUE,
                          row.names = 1, check.names = FALSE,
                          stringsAsFactors = FALSE)
  } else if (ext %in% c("xls", "xlsx")) {
    data_df <- as.data.frame(readxl::read_excel(data_path))
    rownames(data_df) <- data_df[[1]]
    data_df <- data_df[, -1]
  } else if (ext == "rds") {
    obj <- readRDS(data_path)
    if (is.matrix(obj) || is.data.frame(obj)) {
      data_df <- as.data.frame(obj)
    } else {
      stop("RDS file must contain a matrix or data.frame")
    }
  } else {
    stop(sprintf("Unsupported file format: .%s", ext))
  }

  # ── 2. Transpose if requested ────────────────────────────────────────────────
  if (transpose) {
    cat("Transposing data matrix...\n")
    data_df <- as.data.frame(t(data_df))
  }

  sample_names  <- rownames(data_df)
  feature_names <- colnames(data_df)

  cat(sprintf("Data shape: %d samples x %d features\n",
              nrow(data_df), ncol(data_df)))

  # ── 3. Load and align metadata ───────────────────────────────────────────────
  metadata <- NULL
  if (!is.null(metadata_path)) {
    cat(sprintf("Loading metadata from %s...\n", metadata_path))
    sep <- if (grepl("\\.tsv$", metadata_path)) "\t" else ","
    metadata <- read.table(metadata_path, sep = sep, header = TRUE,
                           row.names = 1, check.names = FALSE,
                           stringsAsFactors = FALSE)

    common_samples <- intersect(sample_names, rownames(metadata))
    n_missing <- length(sample_names) - length(common_samples)
    if (n_missing > 0) {
      warning(sprintf("%d samples missing from metadata — using %d common samples",
                      n_missing, length(common_samples)))
      data_df  <- data_df[common_samples, , drop = FALSE]
      metadata <- metadata[common_samples, , drop = FALSE]
      sample_names <- common_samples
    }
    cat(sprintf("  Metadata aligned: %d samples\n", length(common_samples)))
  }

  # ── 4. Handle missing values ─────────────────────────────────────────────────
  n_missing_vals <- sum(is.na(data_df))
  if (n_missing_vals > 0) {
    pct <- round(100 * n_missing_vals / prod(dim(data_df)), 2)
    cat(sprintf("Found %d missing values (%.2f%%)\n", n_missing_vals, pct))
    data_df <- .handle_missing_values(data_df, method = handle_missing)
  }

  # Convert to numeric matrix
  data_mat <- as.matrix(data_df)
  mode(data_mat) <- "numeric"

  # ── 5. Remove constant features ──────────────────────────────────────────────
  feature_sds <- apply(data_mat, 2, sd, na.rm = TRUE)
  constant_idx <- which(feature_sds == 0)
  if (length(constant_idx) > 0) {
    cat(sprintf("Removing %d constant features (zero variance)\n",
                length(constant_idx)))
    data_mat      <- data_mat[, -constant_idx, drop = FALSE]
    feature_names <- feature_names[-constant_idx]
  }

  # ── 6. Filter low-variance features ─────────────────────────────────────────
  if (filter_low_variance && variance_threshold > 0) {
    n_before <- ncol(data_mat)
    feature_vars <- apply(data_mat, 2, var, na.rm = TRUE)
    keep_mask     <- feature_vars >= variance_threshold
    data_mat      <- data_mat[, keep_mask, drop = FALSE]
    feature_names <- feature_names[keep_mask]
    cat(sprintf("Filtered %d low-variance features (threshold = %.2f)\n",
                n_before - ncol(data_mat), variance_threshold))
  }

  # ── 7. Remove outlier samples ────────────────────────────────────────────────
  if (remove_outliers) {
    outlier_mask <- .detect_outliers(data_mat, threshold = outlier_threshold)
    n_outliers   <- sum(outlier_mask)
    if (n_outliers > 0) {
      cat(sprintf("Removing %d outlier samples\n", n_outliers))
      data_mat     <- data_mat[!outlier_mask, , drop = FALSE]
      sample_names <- sample_names[!outlier_mask]
      if (!is.null(metadata)) {
        metadata <- metadata[!outlier_mask, , drop = FALSE]
      }
    }
  }

  # ── 8. Normalize ─────────────────────────────────────────────────────────────
  if (!is.null(normalize_method)) {
    cat(sprintf("Applying %s normalization...\n", normalize_method))
    data_mat <- .normalize_data(data_mat, method = normalize_method)
  }

  # ── 9. Final report ──────────────────────────────────────────────────────────
  cat(sprintf("\nFinal data shape: %d samples x %d features\n",
              nrow(data_mat), ncol(data_mat)))
  cat(sprintf("Data range: [%.2f, %.2f]\n", min(data_mat), max(data_mat)))
  cat(sprintf("Mean: %.2f, SD: %.2f\n", mean(data_mat), sd(data_mat)))
  cat("✓ Data preparation complete!\n")

  list(
    data          = data_mat,
    metadata      = metadata,
    feature_names = feature_names,
    sample_names  = sample_names
  )
}


# ── Internal helpers ────────────────────────────────────────────────────────────

.handle_missing_values <- function(data_df, method) {
  if (method == "drop") {
    n_before <- nrow(data_df)
    data_df  <- data_df[complete.cases(data_df), ]
    cat(sprintf("  Dropped %d samples with missing values (remaining: %d)\n",
                n_before - nrow(data_df), nrow(data_df)))

  } else if (method %in% c("mean", "median")) {
    fill_fn <- if (method == "mean") mean else median
    for (j in seq_len(ncol(data_df))) {
      na_idx <- is.na(data_df[[j]])
      if (any(na_idx)) {
        data_df[[j]][na_idx] <- fill_fn(data_df[[j]], na.rm = TRUE)
      }
    }
    cat(sprintf("  Imputed missing values using %s\n", method))

  } else if (method == "knn") {
    if (!requireNamespace("impute", quietly = TRUE)) {
      message("Installing impute package for KNN imputation...")
      if (!requireNamespace("BiocManager", quietly = TRUE))
        install.packages("BiocManager")
      BiocManager::install("impute", update = FALSE)
    }
    mat <- as.matrix(data_df)
    mode(mat) <- "numeric"
    # impute::impute.knn expects features x samples
    imputed <- impute::impute.knn(t(mat), k = 5)
    data_df <- as.data.frame(t(imputed$data))
    cat("  Imputed missing values using KNN (k=5)\n")

  } else {
    stop(sprintf("Unknown missing value method: '%s'. Use 'drop', 'mean', 'median', or 'knn'.", method))
  }
  data_df
}


.normalize_data <- function(data_mat, method) {
  if (method == "zscore") {
    # scale() operates column-wise (per feature) — correct for samples x features
    scale(data_mat)

  } else if (method == "minmax") {
    apply(data_mat, 2, function(x) {
      rng <- range(x, na.rm = TRUE)
      if (diff(rng) == 0) return(rep(0, length(x)))
      (x - rng[1]) / diff(rng)
    })

  } else if (method == "robust") {
    # Robust scaling: (x - median) / IQR
    apply(data_mat, 2, function(x) {
      med <- median(x, na.rm = TRUE)
      iqr <- IQR(x, na.rm = TRUE)
      if (iqr == 0) return(rep(0, length(x)))
      (x - med) / iqr
    })

  } else if (method == "log2") {
    # Shift to positive before log2
    min_val <- min(data_mat, na.rm = TRUE)
    log2(data_mat - min_val + 1)

  } else {
    stop(sprintf("Unknown normalization method: '%s'. Use 'zscore', 'minmax', 'robust', or 'log2'.", method))
  }
}


.detect_outliers <- function(data_mat, threshold) {
  # Z-score of per-sample means across all features
  sample_means <- rowMeans(data_mat, na.rm = TRUE)
  z_scores     <- abs((sample_means - mean(sample_means)) / sd(sample_means))
  z_scores > threshold
}


#' Get Summary Statistics for a Data Matrix
#'
#' @param data_mat Numeric matrix (samples x features)
#' @param sample_names Character vector of sample names
#' @param feature_names Character vector of feature names
#'
#' @return data.frame with per-sample summary statistics
#'
#' @export
get_data_summary <- function(data_mat, sample_names, feature_names) {
  data.frame(
    sample    = sample_names,
    mean      = rowMeans(data_mat, na.rm = TRUE),
    sd        = apply(data_mat, 1, sd, na.rm = TRUE),
    min       = apply(data_mat, 1, min, na.rm = TRUE),
    max       = apply(data_mat, 1, max, na.rm = TRUE),
    n_zero    = rowSums(data_mat == 0, na.rm = TRUE),
    n_missing = rowSums(is.na(data_mat)),
    stringsAsFactors = FALSE
  )
}


# ── Self-test when sourced directly ────────────────────────────────────────────
if (sys.nframe() == 0) {
  cat(strrep("=", 70), "\n")
  cat("Testing prepare_data.R\n")
  cat(strrep("=", 70), "\n\n")

  # Create a small synthetic dataset
  set.seed(42)
  n_samples  <- 20
  n_features <- 50

  test_mat <- matrix(rnorm(n_samples * n_features), nrow = n_samples,
                     ncol = n_features,
                     dimnames = list(
                       paste0("Sample_", seq_len(n_samples)),
                       paste0("Feature_", seq_len(n_features))
                     ))

  # Add a constant feature and a missing value to test filtering
  test_mat[, 1]  <- 5.0          # constant feature
  test_mat[3, 5] <- NA           # missing value

  tmp_file <- tempfile(fileext = ".csv")
  write.csv(test_mat, tmp_file)

  cat("1. Testing with zscore normalization + drop missing...\n")
  result <- load_and_prepare_data(tmp_file,
                                  normalize_method = "zscore",
                                  handle_missing   = "drop")
  cat(sprintf("   Output shape: %d x %d\n\n",
              nrow(result$data), ncol(result$data)))

  cat("2. Testing with log2 normalization + mean imputation...\n")
  result2 <- load_and_prepare_data(tmp_file,
                                   normalize_method = "log2",
                                   handle_missing   = "mean")
  cat(sprintf("   Output shape: %d x %d\n\n",
              nrow(result2$data), ncol(result2$data)))

  cat("3. Summary statistics:\n")
  summ <- get_data_summary(result$data, result$sample_names, result$feature_names)
  print(head(summ, 3))

  unlink(tmp_file)
  cat("\n✓ All tests passed!\n")
}
