# CellBender Troubleshooting Guide

---

## Installation Issues

### `torch.cuda.is_available()` returns False
**Cause**: PyTorch installed without CUDA support, or CUDA drivers not installed.
**Fix**:
```bash
# Check CUDA version
nvidia-smi

# Reinstall PyTorch with matching CUDA version
# See https://pytorch.org/get-started/locally/
pip uninstall torch
pip install torch --index-url https://download.pytorch.org/whl/cu118  # for CUDA 11.8
```

### `ImportError: No module named 'tables'`
**Cause**: PyTables not installed.
**Fix**:
```bash
conda install -c anaconda pytables
# or
pip install tables
```

### Version conflict errors
**Fix**: Always install CellBender in its own conda environment:
```bash
conda create -n cellbender python=3.7
conda activate cellbender
pip install cellbender
```

---

## Input Data Issues

### "File not found" or format error
**Cause**: Wrong input file path, or using filtered instead of raw matrix.
**Fix**: Use the **raw/unfiltered** matrix:
- CellRanger v3: `outs/raw_feature_bc_matrix.h5`
- CellRanger v2: `outs/raw_gene_bc_matrices_h5.h5`
- NOT: `outs/filtered_feature_bc_matrix.h5`

### "No cells found!" error
**Cause**: `--expected-cells` is too low, or `--total-droplets-included` is too small.
**Fix**:
```bash
# Increase expected-cells significantly
cellbender remove-background \
    --input raw.h5 --output out.h5 \
    --expected-cells 10000 \
    --total-droplets-included 25000
```

### Warning: "few empty droplets identified"
**Cause**: `--low-count-threshold` (default 5) is higher than the empty droplet plateau UMI level. Empty droplets are being excluded.
**Fix**:
```bash
cellbender remove-background \
    --input raw.h5 --output out.h5 \
    --low-count-threshold 1
```

---

## Training / Convergence Issues

### Learning curve has large spikes or dips
**Cause**: Learning rate too high — inference "jumped" into a suboptimal region.
**Fix**: Reduce `--learning-rate` by 2×:
```bash
# Default is 1e-4, try:
cellbender remove-background \
    --input raw.h5 --output out.h5 \
    --learning-rate 5e-5
```

### ELBO has not converged (still increasing at end of training)
**Cause**: Not enough epochs.
**Fix**: Increase epochs (but do not exceed 300):
```bash
cellbender remove-background \
    --input raw.h5 --output out.h5 \
    --epochs 300 \
    --checkpoint ckpt.tar.gz  # resume from existing checkpoint
```

### `nan` error — tool crashed
**Cause**: Numerical instability during training. Rare but serious.
**Fix**:
1. Re-run with `--debug` flag and report the issue on GitHub
2. Try reducing `--learning-rate` to 1e-5
3. Try `--model ambient` instead of `full`

### GPU out-of-memory (process "Killed")
**Cause**: GPU VRAM exhausted during posterior sampling.
**Fix**: Reduce posterior batch size and restart from checkpoint:
```bash
cellbender remove-background \
    --cuda \
    --input raw.h5 --output out.h5 \
    --posterior-batch-size 64 \
    --checkpoint ckpt.tar.gz
```
Note: CellBender uses only 1 GPU. Extra GPUs will not help.

### Training is very slow on CPU
**Fix** (multiple strategies):
```bash
cellbender remove-background \
    --input raw.h5 --output out.h5 \
    --total-droplets-included 10000 \          # reduce barcodes analyzed
    --projected-ambient-count-threshold 1 \    # skip low-ambient genes
    --empty-drop-training-fraction 0.1         # fewer empties per minibatch
```
Alternatively, use Google Colab (free GPU) or Terra (~$0.30/sample).

---

## Cell Calling Issues

### Too many cells called
**Cause**: CellBender calls any droplet with >50% probability of being non-empty. Some may be low-quality cells, not healthy cells.
**Recommended approach**: Do NOT try to fix this by changing CellBender parameters. Instead, filter downstream:
```python
# Filter for mitochondrial reads, gene count, etc.
sc.pp.calculate_qc_metrics(adata, qc_vars=['mt'], inplace=True)
adata = adata[adata.obs['pct_counts_mt'] < 20]
adata = adata[adata.obs['n_genes_by_counts'] > 200]
```
**If still too many**: Try increasing `--total-droplets-included` or `--empty-drop-training-fraction`.

### Too few cells called
**Cause**: `--expected-cells` too low, or `--total-droplets-included` too small.
**Fix**:
```bash
# Increase both parameters
cellbender remove-background \
    --input raw.h5 --output out.h5 \
    --expected-cells 8000 \
    --total-droplets-included 20000
```

### Cell probabilities are not bimodal (gradual transition)
**Cause**: Convergence issue, or dataset has unusual UMI distribution.
**Fix**:
1. Check if ELBO has converged — increase `--epochs` if not
2. Try adjusting `--expected-cells` to better match the knee of the UMI curve
3. Try reducing `--learning-rate`

---

## Output Issues

### Negative counts in output matrix
**Cause**: You are using CellBender v0.3.1, which had a bug (integer overflow).
**Fix**: Salvage from checkpoint using v0.3.0 or v0.3.2:
```bash
cellbender remove-background \
    --input raw.h5 \
    --output fixed_output.h5 \
    --checkpoint path/to/ckpt.tar.gz \
    --force-use-checkpoint
```

### HTML report failed to generate
**Cause**: Jupyter notebook rendering issue (new in v0.3.0, less tested).
**Fix**: Report as GitHub issue. The count matrix output is unaffected.

### Seurat cannot load the output h5
**Cause**: CellBender adds extra metadata fields that Seurat's `Read10X_h5()` does not expect.
**Fix**: Strip extra metadata with ptrepack:
```bash
ptrepack --complevel 5 cellbender_output_filtered.h5:/matrix cellbender_seurat.h5:/matrix
```
Or use the scCustomize R package which handles CellBender output natively.

### Output file is very large
**Cause**: `ckpt.tar.gz` and `output_posterior.h5` are large.
**Fix**: Delete these after QC if you don't need to re-run:
```bash
rm ckpt.tar.gz output_posterior.h5
# Keep: output.h5, output_filtered.h5, output_report.html, output.pdf, output.log
```

---

## CITE-seq / Multiome Issues

### ATAC processing is very slow
**Cause**: 200k+ peak features.
**Fix** (choose one):
```bash
# Option 1: Exclude ATAC entirely (peaks pass through unchanged)
cellbender remove-background \
    --input raw.h5 --output out.h5 \
    --exclude-feature-types Peaks

# Option 2: Only analyze peaks with significant ambient signal
cellbender remove-background \
    --input raw.h5 --output out.h5 \
    --projected-ambient-count-threshold 2
```

### Running CellBender on Antibody Capture only
**Not recommended.** Gene Expression features are needed to form a good prior on cell type. Without them, the model cannot cluster similar cells together. Always include Gene Expression.

---

## Terra / WDL Issues

### Job failed with PAPI error code 9
**Cause**: Transient Google Cloud error.
**Fix**: Re-run without changes. The job will resume from the checkpoint automatically.

### How to estimate cost
~$0.30/sample on Google Cloud (as of 2022 pricing). Actual cost depends on dataset size and preemption rate.

---

## Interpreting Warnings in the HTML Report

| Warning | Meaning | Action |
|---|---|---|
| "ELBO did not converge" | Training stopped before plateau | Re-run with more epochs (up to 300) |
| "Learning rate may be too high" | Spikes in learning curve | Re-run with `--learning-rate` halved |
| "Cell calls look unusual" | Bimodal cell probability not achieved | Adjust `--expected-cells` and `--total-droplets-included` |
| "Few empty droplets" | Empty plateau not identified | Decrease `--low-count-threshold` to 1 |
| "High ambient fraction" | >50% of counts in cells are ambient | Dataset has severe contamination; consider re-running experiment |

---

## Getting Help

1. Check the [GitHub Issues](https://github.com/broadinstitute/CellBender/issues) — many questions already answered
2. Open a new issue with:
   - CellBender version (`cellbender --version`)
   - Full command used
   - Log file (lines 1–30 at minimum)
   - PDF output (learning curve)
   - Re-run with `--debug` flag if requested
