# Multi-Contrast Enrichment Analysis using compareCluster()
#
# When you have multiple DE contrasts (e.g., 4 tissues × Treg vs Tconv, or
# several treatment arms), running enrichment separately and stacking plots
# is far inferior to a single comparative view. compareCluster() from
# clusterProfiler generates one unified dotplot showing which pathways are
# enriched — and where — across all your contrasts simultaneously.
#
# Typical inputs: a named list of significant gene vectors, one per contrast
# (e.g., list("Lung_vs_Blood" = c("GENE1","GENE2",...), ...))

library(clusterProfiler)
library(ggplot2)
library(stringr)

# Try to load svglite for SVG export (optional)
.has_svglite <- requireNamespace("svglite", quietly = TRUE)
if (.has_svglite) library(svglite)

#' Save plot to PNG and SVG
#' @keywords internal
.save_plot <- function(plot, base_path, width = 12, height = 8, dpi = 300) {
  png_path <- sub("\\.(svg|png)$", ".png", base_path)
  ggsave(png_path, plot = plot, width = width, height = height, dpi = dpi, device = "png")
  cat("   Saved:", png_path, "\n")

  svg_path <- sub("\\.(svg|png)$", ".svg", base_path)
  tryCatch({
    ggsave(svg_path, plot = plot, width = width, height = height, device = "svg")
    cat("   Saved:", svg_path, "\n")
  }, error = function(e) {
    tryCatch({
      svg(svg_path, width = width, height = height)
      print(plot)
      dev.off()
      cat("   Saved:", svg_path, "\n")
    }, error = function(e2) {
      cat("   (SVG export failed)\n")
    })
  })
}

#' Run comparative enrichment across multiple contrasts (ORA)
#'
#' Takes a named list of gene vectors (one per contrast) and runs
#' clusterProfiler::compareCluster() to perform ORA on each set, then
#' returns a compareClusterResult object ready for plotting.
#'
#' Best for: multi-tissue, multi-treatment, or any design with ≥3 contrasts
#' where you want to see pathway enrichment side-by-side.
#'
#' @param contrast_gene_lists Named list of character vectors. Names become
#'   the x-axis labels in the comparative dotplot (e.g.,
#'   list("Lung_vs_Blood" = c("FOXP3","IL2RA"), "Gut_vs_Blood" = c("RORC"))).
#' @param term2gene TERM2GENE data frame (columns: term, gene). Use
#'   get_msigdb_genesets.R to retrieve MSigDB collections.
#' @param background Character vector of all tested genes (universe for
#'   hypergeometric test). Set to the full gene list from your DE results.
#'   CRITICAL: must be specified explicitly for correct statistics.
#' @param pvalue_cutoff Display threshold applied to adjusted p-value at the
#'   reporting stage (default: 0.05). Consider 0.1 for exploratory analyses
#'   (see note below). Note: compareCluster() is run with pvalueCutoff = 1 to
#'   retain all results; this threshold is applied only on p.adjust downstream.
#' @param min_size Minimum gene set size (default: 10)
#' @param max_size Maximum gene set size (default: 500)
#'
#' @return compareClusterResult object from clusterProfiler
#' @export
#'
#' @note On p-value thresholds: pathway gene sets are not independent (many
#'   genes overlap between pathways), so Benjamini-Hochberg correction is
#'   conservative at the pathway level. Using pvalue_cutoff = 0.1 is common
#'   practice for exploratory pathway analysis. Use 0.05 when presenting
#'   final/publication results.
#'
#' @examples
#' # Prepare input: named list of significant gene vectors per contrast
#' contrast_genes <- list(
#'   "Lung_vs_Blood"  = c("FOXP3", "IL2RA", "CTLA4", "IKZF2"),
#'   "Gut_vs_Blood"   = c("RORC", "IL17A", "CCR6", "AHR"),
#'   "Liver_vs_Blood" = c("CXCR6", "ITGAE", "BLIMP1", "TOX")
#' )
#'
#' # Get gene sets (e.g., Hallmark from MSigDB)
#' source("scripts/get_msigdb_genesets.R")
#' gene_sets <- get_msigdb_genesets(collection = "H", organism = "Homo sapiens")
#'
#' # Background = all genes tested in DE analysis
#' all_genes <- read.csv("de_results.csv")$gene
#'
#' ck <- run_comparative_enrichment(contrast_genes, gene_sets, background = all_genes)
#' plot_comparative_dotplot(ck, output_file = "results/comparative_enrichment.svg")
run_comparative_enrichment <- function(contrast_gene_lists,
                                       term2gene,
                                       background,
                                       pvalue_cutoff = 0.05,
                                       min_size = 10,
                                       max_size = 500) {

  if (length(contrast_gene_lists) < 2) {
    stop("Provide at least 2 contrasts. For a single contrast, use run_ora() instead.")
  }

  if (is.null(names(contrast_gene_lists)) || any(names(contrast_gene_lists) == "")) {
    stop("All elements of contrast_gene_lists must be named (names become plot labels).")
  }

  message("\n=== Running Comparative Enrichment (", length(contrast_gene_lists),
          " contrasts) ===")
  for (nm in names(contrast_gene_lists)) {
    message(sprintf("  %-30s  %d genes", nm, length(contrast_gene_lists[[nm]])))
  }
  message(sprintf("  Background: %d genes", length(background)))
  message(sprintf("  p.adjust cutoff: %.2f", pvalue_cutoff))

  # Use pvalueCutoff = 1 to retain ALL results before BH adjustment.
  # compareCluster(pvalueCutoff = x) filters by raw p-value internally, not
  # adjusted p-value — setting it to 1 prevents silent pre-adjustment filtering.
  # The user-supplied pvalue_cutoff is applied exclusively on p.adjust below.
  ck <- compareCluster(
    geneClusters  = contrast_gene_lists,
    fun           = "enricher",
    TERM2GENE     = term2gene,
    universe      = background,
    pvalueCutoff  = 1.0,
    pAdjustMethod = "BH",
    minGSSize     = min_size,
    maxGSSize     = max_size
  )

  if (is.null(ck) || nrow(as.data.frame(ck)) == 0) {
    message("No enrichments found across any contrast.")
    return(ck)
  }

  n_hits <- nrow(subset(as.data.frame(ck), p.adjust <= pvalue_cutoff))
  message(sprintf("Done: %d significant pathway-contrast pairs (p.adjust < %.2f)",
                  n_hits, pvalue_cutoff))

  return(ck)
}

#' Plot comparative enrichment dotplot
#'
#' Generates a publication-quality dotplot comparing pathway enrichment across
#' multiple contrasts. Dot size = gene ratio (numeric), dot color = adjusted
#' p-value (gradient: red = most significant, blue = least significant).
#' Long pathway names are automatically wrapped to prevent cramped labels.
#'
#' @param ck compareClusterResult object from run_comparative_enrichment()
#' @param top_n Maximum number of pathways to show (selected by lowest
#'   p.adjust across any contrast; default: 20)
#' @param label_wrap Width in characters for wrapping long pathway names
#'   (default: 30)
#' @param output_file Output file path (default: "comparative_enrichment.svg")
#' @param width Plot width in inches (default: 12)
#' @param height Plot height in inches (default: 8)
#'
#' @return ggplot object (also saves PNG + SVG)
#' @export
plot_comparative_dotplot <- function(ck,
                                     top_n = 20,
                                     label_wrap = 30,
                                     output_file = "comparative_enrichment.svg",
                                     width = 12,
                                     height = 8) {

  if (is.null(ck) || nrow(as.data.frame(ck)) == 0) {
    message("No results to plot.")
    return(NULL)
  }

  plot_data <- as.data.frame(ck)
  plot_data  <- subset(plot_data, !is.na(p.adjust))

  # Select top_n pathways by best (lowest) p.adjust across any contrast
  best_padj  <- tapply(plot_data$p.adjust, plot_data$ID, min, na.rm = TRUE)
  top_ids    <- names(sort(best_padj)[seq_len(min(top_n, length(best_padj)))])
  plot_data  <- plot_data[plot_data$ID %in% top_ids, ]
  plot_data  <- plot_data[order(plot_data$p.adjust, decreasing = TRUE), ]

  # Convert GeneRatio string ("5/100") to numeric for proper size scaling
  gr_parts         <- str_split(plot_data$GeneRatio, "/", simplify = TRUE)
  plot_data$GeneRatioNum <- as.numeric(gr_parts[, 1]) / as.numeric(gr_parts[, 2])

  # Wrap long pathway descriptions
  plot_data$Description <- str_wrap(plot_data$Description, width = label_wrap)

  # Preserve pathway order (sorted by p.adjust)
  pathway_order <- unique(plot_data$Description)
  plot_data$Description <- factor(plot_data$Description, levels = pathway_order)

  p <- ggplot(plot_data,
              aes(x = Cluster, y = Description)) +
    geom_point(aes(colour = p.adjust, size = GeneRatioNum)) +
    scale_colour_gradientn(
      colours = c("red3", "orange", "steelblue"),
      name    = "Adjusted\np-value"
    ) +
    scale_size_continuous(
      name   = "Gene ratio",
      range  = c(2, 8)
    ) +
    labs(
      x = "Contrast",
      y = "Pathway"
    ) +
    theme_bw(base_size = 12) +
    theme(
      axis.text.x  = element_text(angle = 45, hjust = 1, vjust = 1),
      axis.text.y  = element_text(size = 9),
      axis.title   = element_text(face = "bold"),
      legend.title = element_text(face = "bold"),
      panel.grid.major = element_line(colour = "grey90")
    )

  .save_plot(p, output_file, width = width, height = height)
  cat("✓ Comparative dotplot saved (", length(top_ids), "pathways x",
      length(unique(plot_data$Cluster)), "contrasts)\n")

  return(p)
}

#' Export comparative enrichment results to CSV
#'
#' @param ck compareClusterResult object
#' @param output_file Output CSV path (default: "comparative_enrichment.csv")
#' @export
export_comparative_results <- function(ck, output_file = "comparative_enrichment.csv") {
  if (is.null(ck) || nrow(as.data.frame(ck)) == 0) {
    message("No results to export.")
    return(invisible(NULL))
  }

  df <- as.data.frame(ck)
  write.csv(df, file = output_file, row.names = FALSE)
  cat("Saved:", output_file, "(", nrow(df), "rows)\n")
  return(invisible(df))
}

# =============================================================================
# Example usage:
# =============================================================================
#
# # Named list: one character vector of significant gene symbols per contrast
# contrast_genes <- list(
#   "Lung_vs_Blood"  = c("FOXP3", "IL2RA", "CTLA4"),
#   "Gut_vs_Blood"   = c("RORC", "IL17A", "CCR6"),
#   "Liver_vs_Blood" = c("CXCR6", "ITGAE", "TOX")
# )
#
# # Gene sets from MSigDB (Hallmark, KEGG, GO, Reactome)
# source("scripts/get_msigdb_genesets.R")
# hallmark <- get_msigdb_genesets(collection = "H", organism = "Homo sapiens")
#
# # Background = all genes in DE results (not just significant ones)
# background_genes <- read.csv("results/deseq2_results.csv")$gene
#
# # Run comparative ORA
# ck <- run_comparative_enrichment(
#   contrast_gene_lists = contrast_genes,
#   term2gene           = hallmark,
#   background          = background_genes,
#   pvalue_cutoff       = 0.1   # 0.1 is common for exploratory pathway analysis
# )
#
# # Plot
# p <- plot_comparative_dotplot(ck,
#                               top_n       = 20,
#                               output_file = "results/comparative_enrichment.svg")
#
# # Export table
# export_comparative_results(ck, "results/comparative_enrichment.csv")
