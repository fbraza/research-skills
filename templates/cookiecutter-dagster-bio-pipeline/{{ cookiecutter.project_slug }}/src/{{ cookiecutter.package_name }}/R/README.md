# R scripts

Place self-contained R scripts here when the pipeline uses R-native tooling such as DESeq2, edgeR, limma, Seurat, or CellChat.

## Conventions

- the Python asset defines dependencies and launches `Rscript`
- config and file paths are passed explicitly via environment variables
- the R script reads inputs and writes outputs explicitly
- use `{reticulate}` + `dagster_pipes` to report logs and metadata back to Dagster
- keep Python↔R exchange file-based

See `run_pipes_example.R` for a starter stub.
