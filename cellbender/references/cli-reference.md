# CellBender CLI Reference

Full reference for `cellbender remove-background` (v0.3.2).

---

## Synopsis

```
cellbender remove-background \
    --input INPUT_FILE \
    --output OUTPUT_FILE \
    [OPTIONS]
```

---

## Required Arguments

| Argument | Type | Description |
|---|---|---|
| `--input INPUT_FILE` | path | Raw (unfiltered) count matrix. Supported: CellRanger v2/v3 `.h5`, CellRanger directory (`.mtx`), AnnData `.h5ad`, Loom `.loom`, Drop-seq DGE `.txt`/`.txt.gz`, BD Rhapsody `.csv`/`.csv.gz`. **Must include empty droplets.** |
| `--output OUTPUT_FILE` | path | Output file path. **Must have `.h5` extension.** The directory must already exist. |

---

## Core Run Arguments

| Argument | Default | Type | Description |
|---|---|---|---|
| `--cuda` | False | flag | Run inference on GPU. **Strongly recommended.** Omit only if no GPU available. |
| `--expected-cells N` | auto | int | Approximate number of cells expected. Auto-detection works well for clean datasets. Set manually if auto-detection fails. A rough estimate within 2× is sufficient. |
| `--total-droplets-included N` | auto | int | Number of barcodes (rank-ordered by UMI) to include in analysis. Should cover all cells plus a few thousand empty droplets. Barcodes beyond this are assumed surely empty. Runtime scales linearly with this value. |
| `--epochs N` | 150 | int | Number of training epochs. 150 is usually sufficient. Increase to 300 if ELBO has not converged. **Do not exceed 300.** |
| `--fpr F [F ...]` | 0.01 | float(s) | Target false positive rate(s) in [0, 1). Controls aggressiveness of noise removal. Multiple values produce multiple output files. See FPR guide in SKILL.md. |
| `--learning-rate LR` | 1e-4 | float | Learning rate for variational inference. Reduce by 2× if learning curve has spikes or dips. Do not exceed 1e-3. |
| `--model MODEL` | full | choice | Generative model. Options: `naive` (subtract ambient profile), `simple` (debug only), `ambient` (ambient RNA only), `swapping` (barcode swapping only), `full` (ambient + swapping, recommended). |

---

## Checkpoint Arguments

| Argument | Default | Type | Description |
|---|---|---|---|
| `--checkpoint FILE` | ckpt.tar.gz | path | Checkpoint tarball from a previous run. If present and workflow hashes match, training resumes from this checkpoint automatically. |
| `--force-use-checkpoint` | False | flag | Bypass version/hash matching for checkpoint. Use to salvage v0.3.1 outputs (which had a bug). Ensure input and checkpoint match manually. |

---

## Cell Calling Arguments

| Argument | Default | Type | Description |
|---|---|---|---|
| `--force-cell-umi-prior N` | — | int | Override CellBender's automatic prior for UMI counts in cells. Use only if auto-detection is clearly wrong. |
| `--force-empty-umi-prior N` | — | int | Override CellBender's automatic prior for UMI counts in empty droplets. |
| `--low-count-threshold N` | 5 | int | Droplets with fewer UMIs than this are excluded entirely. Decrease to 1 if warning "few empty droplets identified" appears. |

---

## Architecture Arguments (Advanced)

| Argument | Default | Type | Description |
|---|---|---|---|
| `--z-dim N` | 64 | int | Dimension of latent variable `z` (gene expression embedding). Rarely needs changing. |
| `--z-layers N [N ...]` | [512] | int(s) | Hidden layer dimensions in the encoder for `z`. |
| `--training-fraction F` | 0.9 | float | Fraction of data used for training (rest held out for test ELBO). |
| `--empty-drop-training-fraction F` | 0.2 | float | Fraction of each training minibatch drawn from empty droplets. Increase if too many cells called; decrease to speed up CPU runs. |

---

## Feature Filtering Arguments

| Argument | Default | Type | Description |
|---|---|---|---|
| `--ignore-features I [I ...]` | [] | int(s) | Integer indices of features to exclude from analysis. These features pass through unchanged in the output. |
| `--exclude-feature-types T [T ...]` | [] | str(s) | Feature types to exclude (e.g., `Peaks` for ATAC in multiome). These features pass through unchanged. |
| `--projected-ambient-count-threshold T` | 0.1 | float | Exclude features estimated to have fewer than T total ambient counts across all cells. Increase (e.g., 1–2) to speed up CPU runs or ATAC processing. |

---

## Posterior / Output Arguments (Advanced)

| Argument | Default | Type | Description |
|---|---|---|---|
| `--posterior-batch-size N` | 128 | int | Batch size for posterior sampling. Reduce to 64 if GPU out-of-memory during posterior computation. Restart from `ckpt.tar.gz`. |
| `--posterior-regularization METHOD` | — | choice | Posterior regularization method. Options: `PRq` (quantile-targeting), `PRmu` (mean-targeting, v0.2.0 behavior), `PRmu_gene` (mean-targeting per gene). Not required for normal use. |
| `--alpha A` | — | float | Tunable parameter for `PRq` posterior regularization. Expert use only. |
| `--q Q` | — | float | Tunable parameter for CDF threshold estimation. Expert use only. |
| `--estimator METHOD` | mckp | choice | Output count estimation method. Options: `map`, `mean`, `cdf`, `sample`, `mckp`. Default `mckp` is recommended. |
| `--estimator-multiple-cpu` | False | flag | Use multiple CPUs for `mckp` estimator computation (parallel). |

---

## Training Robustness Arguments (Automated Pipelines)

| Argument | Default | Type | Description |
|---|---|---|---|
| `--num-training-tries N` | 1 | int | Number of training attempts. On failure (per ELBO criteria), retries with reduced learning rate. |
| `--learning-rate-retry-mult M` | 0.2 | float | Learning rate multiplier on each retry. |
| `--final-elbo-fail-fraction F` | — | float | Training fails if `(best_ELBO - final_ELBO) / (best_ELBO - initial_ELBO) > F`. |
| `--epoch-elbo-fail-fraction F` | — | float | Training fails if ELBO drops by more than this fraction in a single epoch. |
| `--checkpoint-mins M` | 7.0 | float | Minutes between checkpoint saves. |
| `--constant-learning-rate` | False | flag | Use ClippedAdam (constant LR) instead of OneCycleLR schedule. Required if you want to continue training from a checkpoint for more epochs than originally specified. |

---

## Utility Arguments

| Argument | Default | Type | Description |
|---|---|---|---|
| `--cpu-threads N` | auto | int | Number of CPU threads for PyTorch CPU operations. Defaults to logical core count. |
| `--debug` | False | flag | Log extra debug messages. Use when reporting issues on GitHub. |
| `--truth FILE` | — | path | Developer use only. Truth h5 file for simulated data. |

---

## Python API

### Loading outputs

```python
from cellbender.remove_background.downstream import (
    anndata_from_h5,
    load_anndata_from_input_and_output,
    load_anndata_from_input_and_outputs,
    dict_from_h5,
)
```

#### `anndata_from_h5(file, analyzed_barcodes_only=True)`
Load a CellBender output `.h5` into AnnData with all metadata.

```python
adata = anndata_from_h5('cellbender_output.h5')
# analyzed_barcodes_only=False to load all barcodes (matches raw matrix size)
```

**Returns**: AnnData with:
- `adata.obs`: `background_fraction`, `cell_probability`, `cell_size`, `droplet_efficiency`
- `adata.var`: `ambient_expression`, `feature_type`, `genome`, `gene_id`
- `adata.uns`: training metadata (ELBO curves, model parameters)
- `adata.obsm`: `gene_expression_encoding` (CellBender latent embedding)

#### `load_anndata_from_input_and_output(input_file, output_file, analyzed_barcodes_only=True, input_layer_key='cellranger', retain_input_metadata=False, gene_expression_encoding_key='cellbender_embedding')`
Load raw + CellBender output together. **Recommended for downstream analysis.**

```python
adata = load_anndata_from_input_and_output(
    input_file='raw_feature_bc_matrix.h5',
    output_file='cellbender_output.h5',
    input_layer_key='raw',
)
# adata.X = CellBender denoised counts
# adata.layers['raw'] = original counts
```

#### `load_anndata_from_input_and_outputs(input_file, output_files, ...)`
Load raw + multiple CellBender outputs (e.g., multiple FPR values) for comparison.

```python
adata = load_anndata_from_input_and_outputs(
    input_file='raw_feature_bc_matrix.h5',
    output_files={
        'fpr0.01': 'cellbender_output.h5',
        'fpr0.05': 'cellbender_output_fpr0.05.h5',
    },
    input_layer_key='raw',
)
# adata.layers['fpr0.01'], adata.layers['fpr0.05'], adata.layers['raw']
```

#### `dict_from_h5(file)`
Read all contents of an h5 file into a Python dictionary.

---

## Output h5 File Structure

```
output.h5
├── /matrix/                    # CellRanger v3-compatible count matrix
│   ├── barcodes                # All analyzed barcode sequences
│   ├── data, indices, indptr   # Sparse matrix (CSC format)
│   ├── shape                   # [n_genes, n_barcodes]
│   └── features/
│       ├── id, name, feature_type, genome
├── /droplet_latents/           # Per-droplet inferred variables
│   ├── background_fraction     # Fraction of counts that are ambient
│   ├── barcode_indices_for_latents
│   ├── cell_probability        # P(droplet contains a cell)
│   ├── cell_size               # Estimated true UMI count
│   ├── droplet_efficiency      # Capture efficiency
│   └── gene_expression_encoding  # Latent z (n_barcodes × z_dim)
├── /global_latents/            # Experiment-wide inferred variables
│   ├── ambient_expression      # Normalized ambient RNA profile (sums to 1)
│   ├── cell_size_lognormal_std
│   ├── empty_droplet_size_lognormal_loc
│   ├── empty_droplet_size_lognormal_scale
│   ├── posterior_regularization_lambda
│   ├── swapping_fraction_dist_params
│   └── target_false_positive_rate
└── /metadata/
    ├── barcodes_analyzed
    ├── barcodes_analyzed_inds
    ├── features_analyzed_inds
    ├── fraction_data_used_for_testing
    ├── test_elbo, test_epoch    # Test ELBO learning curve
    └── train_elbo, train_epoch  # Train ELBO learning curve
```

### Accessing h5 contents directly (PyTables)
```python
import tables

with tables.open_file('cellbender_output.h5', 'r') as f:
    ambient = f.root.global_latents.ambient_expression[:]
    cell_prob = f.root.droplet_latents.cell_probability[:]
    train_elbo = f.root.metadata.train_elbo[:]
```

### Seurat-compatible h5 (strip CellBender metadata)
```bash
ptrepack --complevel 5 cellbender_output_filtered.h5:/matrix cellbender_seurat.h5:/matrix
```

---

## metrics.csv Fields

| Field | Description |
|---|---|
| `total_raw_counts` | Sum of all input counts |
| `total_output_counts` | Sum of all output counts |
| `total_counts_removed` | Raw minus output |
| `fraction_counts_removed` | Fraction of total counts removed |
| `total_raw_counts_in_cells` | Raw counts in CellBender-called cells |
| `total_counts_removed_from_cells` | Counts removed from cells |
| `fraction_counts_removed_from_cells` | Fraction removed from cells |
| `average_counts_removed_per_cell` | Mean counts removed per cell |
| `target_fpr` | Input `--fpr` value |
| `expected_cells` | Input `--expected-cells` (blank if auto) |
| `found_cells` | Number of CellBender-called cells |
| `output_average_counts_per_cell` | Mean output counts per cell |
| `ratio_of_found_cells_to_expected_cells` | Sanity check ratio |
| `found_empties` | Number of empty droplets identified |
| `fraction_of_analyzed_droplets_that_are_nonempty` | Cell fraction |
| `convergence_indicator` | Mean abs ELBO change (last 3 epochs) / std (last 20 epochs). Typical: 0.25–0.35. Large = poor convergence. |
| `overall_change_in_train_elbo` | ELBO change from epoch 1 to last |
