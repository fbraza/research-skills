# DECODE Troubleshooting Guide

---

## Installation Issues

### `conda env create` fails with channel errors

**Symptom:** `PackagesNotFoundError` or `CondaHTTPError` during environment creation.

**Cause:** The `environment.yml` uses Tsinghua mirror channels (`mirrors.tuna.tsinghua.edu.cn`) which may be inaccessible outside China.

**Fix:** Edit `environment.yml` to use standard channels:
```yaml
channels:
  - pytorch
  - conda-forge
  - defaults
```
Then re-run `conda env create --name DECODE -f environment.yml`.

---

### `torch` not found after environment creation

**Symptom:** `ModuleNotFoundError: No module named 'torch'`

**Fix:** Ensure you activated the environment:
```bash
conda activate DECODE
python -c "import torch; print(torch.__version__)"
```

---

### CUDA not available

**Symptom:** `model.gpu_available` is `False`; training runs on CPU (very slow).

**Diagnosis:**
```python
import torch
print(torch.cuda.is_available())
print(torch.version.cuda)
```

**Fix options:**
1. Install CUDA 11.8 drivers matching your GPU
2. Install the correct PyTorch build: `pip install torch==2.0.0+cu118 --index-url https://download.pytorch.org/whl/cu118`
3. For CPU-only training: increase patience and reduce `train_sample_num` to 2000

---

## Data Preparation Issues

### `KeyError: 'CellType'`

**Symptom:** Error when running `dp.fit()` or filtering cells.

**Cause:** Your AnnData uses a different column name for cell type labels.

**Fix:**
```python
# Check available columns
print(adata.obs.columns.tolist())

# Rename to 'CellType'
adata.obs['CellType'] = adata.obs['cell_type']  # or whatever your column is named
```

---

### `ValueError: n_obs × n_vars = 0 × N` — empty AnnData after filtering

**Symptom:** After filtering by `type_list`, the AnnData has 0 cells.

**Cause:** Cell type names in `type_list` don't match `obs['CellType']` exactly (case-sensitive).

**Fix:**
```python
# Check exact cell type names
print(adata.obs['CellType'].unique())

# Fix case/spacing issues
type_list = ['Luminal_Macrophages', 'Type 2 alveolar']  # must match exactly
```

---

### `FileNotFoundError: data/{tissue_name}/{tissue_name}Ncell.pkl`

**Symptom:** Error when loading the `.pkl` file after `dp.fit()`.

**Cause:** `dp.fit()` was not run, or `tissue_name` or `len(type_list)` doesn't match.

**Fix:**
```python
import os
# Check what files were created
print(os.listdir(f'data/{tissue_name}/'))

# Ensure tissue_name and type_list match what was used in dp.fit()
with open(f'data/{tissue_name}/{tissue_name}{len(type_list)}cell.pkl', 'rb') as f:
    train = pickle.load(f)
```

---

### `MemoryError` during pseudotissue generation

**Symptom:** Out of memory during `dp.fit()`.

**Cause:** Too many training samples or too many cells in the single-cell reference.

**Fix:**
```python
# Reduce training samples
dp = data_process(type_list, train_sample_num=2000, ...)

# Or subsample the single-cell reference
import scanpy as sc
sc.pp.subsample(train_data, n_obs=5000)
```

---

### Features mismatch between train and test data

**Symptom:** Shape mismatch error during training or inference.

**Cause:** Train and test AnnData have different numbers of features (genes/proteins).

**Fix:**
```python
# Find common features
common_features = train_data.var_names.intersection(test_data.var_names)
train_data = train_data[:, common_features]
test_data  = test_data[:, common_features]
print(f"Common features: {len(common_features)}")
```

---

## Training Issues

### Stage 2 loss not converging (Disc stays at ~1.386)

**Symptom:** `Disc` and `Disc_DA` losses remain at ~1.386 (= ln(4)) throughout training.

**Cause:** This is actually **normal behavior** — ln(4) ≈ 1.386 is the theoretical maximum entropy for a binary classifier, indicating the discriminator cannot distinguish train from target tissue. This means batch effect removal is working correctly.

**What to watch:** The `Pred` loss (L1) should decrease. If it doesn't decrease below 0.01 within 10 epochs, there may be a data issue.

---

### Stage 3 RMSE not improving

**Symptom:** Test RMSE stays high (>0.15) and doesn't improve after many epochs.

**Possible causes and fixes:**

1. **Encoder weights not transferred from Stage 2:**
```python
# Ensure this is done BEFORE model.train_model()
model_da.encoder_da.load_state_dict(best_model_weights['encoder'])
encoder_params = copy.deepcopy(model_da.encoder_da.state_dict())
model.encoder.load_state_dict(encoder_params)
```

2. **Too few training samples for the number of cell types:**
```python
# Rule of thumb: train_sample_num >= 1000 × num_cell_types
dp = data_process(type_list, train_sample_num=8000, ...)
```

3. **Cell types are too similar (especially metabolomics):**
- Increase `epoches` to 500 and `patience` to 50
- Check feature similarity: `scipy.stats.kendalltau` between cell type mean profiles

4. **Wrong model class for omics type:**
- Metabolomics: use `from model.deconv_model import MBdeconv` (no Stage 2)
- Transcriptomics/proteomics: use `from model.deconv_model_with_stage_2 import MBdeconv`

---

### `RuntimeError: Expected all tensors to be on the same device`

**Symptom:** CUDA device mismatch error during training.

**Fix:**
```python
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = model.to(device)
# Ensure model is on device BEFORE loading encoder weights
model_da.encoder_da.load_state_dict(best_model_weights['encoder'])
encoder_params = copy.deepcopy(model_da.encoder_da.state_dict())
model.encoder.load_state_dict(encoder_params)
```

---

### `RuntimeError: size mismatch for encoder` when loading Stage 2 weights

**Symptom:** Error when transferring encoder weights from Stage 2 to Stage 3.

**Cause:** `num_feat` used for Stage 2 (DANN) and Stage 3 (MBdeconv) don't match.

**Fix:** Ensure both use the same `num_feat`:
```python
num_feat = train_x_sim.shape[1]  # derive from data, not hardcoded
model_da = DANN(epoches, batchsize, lr)  # DANN infers num_feat from data
model = MBdeconv(num_feat, ...)          # must match
```

---

### Early stopping triggers too quickly

**Symptom:** Training stops after only 5–10 epochs with high RMSE.

**Fix:** Increase patience:
```python
# Stage 2: increase from 3 to 5
pred_loss, disc_loss, disc_loss_DA, best_model_weights = model_da.train(
    source_data, target_data, valid_data, patience=5
)

# Stage 3: increase from 10 to 20
loss1_list, loss2_list, nce_loss_list = model.train_model(model_save_name, True, patience=20)
```

---

### Training is very slow (CPU)

**Symptom:** Each epoch takes >60 seconds.

**Fix options:**
1. Use GPU (strongly recommended — 10–50× speedup)
2. Reduce `train_sample_num` to 2000
3. Reduce `num_feat` by using fewer HVGs (e.g., 1000 instead of 3346)
4. Reduce `batch_size` to 32 (may affect convergence)

---

## Inference Issues

### `CCC` is negative or very low (<0.3)

**Symptom:** Poor deconvolution performance at inference.

**Possible causes:**

1. **Wrong `if_pure` setting:**
```python
# For real tissue with unknown cell types (most common case):
CCC, RMSE, Corr, pred, gt = predict(test_dataloader, type_list, model_test, if_pure=False)
```

2. **Model not in eval mode:**
```python
model_test.eval()  # MUST call before predict()
```

3. **Test data not normalized the same way as training data:**
- Ensure same HVG selection, same normalization (10,000 reads + log1p for RNA)
- Ensure same feature set (same genes/proteins)

4. **Too few cells per cell type in reference:**
- Minimum ~50 cells per cell type recommended
- Check: `train_data.obs['CellType'].value_counts()`

---

### `pred` values don't sum to 1

**Symptom:** Row sums of `pred` are not exactly 1.0.

**Cause:** Floating point precision. This is normal.

**Fix:**
```python
import numpy as np
pred_normalized = pred / pred.sum(axis=1, keepdims=True)
```

---

### `pred` has negative values

**Symptom:** Some predicted proportions are negative.

**Cause:** Should not happen with Softmax output. If it does, check for NaN in input data.

**Fix:**
```python
# Check for NaN/Inf in test data
print(np.isnan(test_x_sim).any(), np.isinf(test_x_sim).any())
pred = np.clip(pred, 0, 1)
pred = pred / pred.sum(axis=1, keepdims=True)
```

---

### `FileNotFoundError` when loading saved model

**Symptom:** `save_models/{num_feat}/{model_save_name}.pt` not found.

**Cause:** Training did not complete or model was saved to a different path.

**Fix:**
```python
import os
# Find saved models
for root, dirs, files in os.walk('save_models'):
    for f in files:
        if f.endswith('.pt'):
            print(os.path.join(root, f))
```

---

## Metabolomics-Specific Issues

### All methods including DECODE give poor CCC (<0.3) on metabolomics

**Symptom:** Very low performance on metabolomics data.

**Cause:** Metabolomics has high inter-cell-type similarity and few features — this is expected to be harder.

**Fixes:**
1. Increase training epochs: `epoches=500, patience=50`
2. Check that you're using `deconv_model.MBdeconv` (not `deconv_model_with_stage_2`)
3. Verify differential metabolites exist between cell types:
```python
import scanpy as sc
sc.tl.rank_genes_groups(adata, 'CellType', method='wilcoxon')
sc.pl.rank_genes_groups(adata, n_genes=10)
```
4. If fewer than 3 metabolites are differentially expressed per cell type, deconvolution may be fundamentally limited

---

### `CIBERSORTx protocol failed` (reference error)

**Note:** This is a known limitation of CIBERSORTx on metabolomics data (reported in the paper). DECODE is the only method that handles metabolomics deconvolution.

---

## Common Warnings (Safe to Ignore)

```
UserWarning: To copy construct from a tensor, it is recommended to use sourceTensor.clone()
```
→ PyTorch version compatibility warning. Does not affect results.

```
FutureWarning: X.dtype being converted to np.float32
```
→ AnnData dtype conversion. Does not affect results.

```
ConvergenceWarning: lbfgs failed to converge
```
→ Only relevant if using sklearn models for comparison. Not from DECODE itself.
