# Starter example for an R script executed through Dagster Pipes.
# Adapt this to your real R-native computation.

library(reticulate)
dagster_pipes <- reticulate::import("dagster_pipes")

with(dagster_pipes$open_dagster_pipes() %as% pipes, {
  context <- dagster_pipes$PipesContext$get()

  input_path <- Sys.getenv("INPUT_PATH")
  output_path <- Sys.getenv("OUTPUT_PATH")

  if (input_path == "" || output_path == "") {
    stop("INPUT_PATH and OUTPUT_PATH must be set")
  }

  df <- read.csv(input_path, check.names = FALSE)
  summary_df <- data.frame(
    column = names(df),
    n_missing = vapply(df, function(x) sum(is.na(x)), numeric(1)),
    stringsAsFactors = FALSE
  )

  write.csv(summary_df, output_path, row.names = FALSE)

  context$log$info(paste("Wrote summary to", output_path))
  context$report_asset_materialization(
    metadata = list(
      output_path = reticulate::r_to_py(output_path),
      n_rows = reticulate::r_to_py(nrow(summary_df))
    )
  )
})
