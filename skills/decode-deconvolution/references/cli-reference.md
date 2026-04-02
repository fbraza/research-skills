# DECODE API Reference

Complete reference for all classes, methods, and functions in the DECODE codebase.

---

## `data.data_process.data_process`

Class for generating pseudotissue training and test data from single-cell AnnData objects.

### Constructor

```python
data_process(
    type_list,
    train_sample_num=6000,
    tissue_name='tissue',
    test_sample_num=1000,
    sample_size=30,
    num_artificial_cells=30
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `type_list` | `list[str]` | required | Cell type names. Must match values in `adata.obs['CellType']`. |
| `train_sample_num` | `int` | 6000 | Number of pseudotissue training samples to generate. |
| `tissue_name` | `str` | required | Name used for output `.pkl` file naming. |
| `test_sample_num` | `int` | 1000 | Number of pseudotissue test samples to generate. |
| `sample_size` | `int` | 30 | Number of cells per pseudotissue (m in paper). |
| `num_artificial_cells` | `int` | 30 | Number of artificial noise cells for Stage 3 contrastive learning. Should equal `sample_size`. |

### `fit(train_data, test_data, noise_data=None)`

Generates pseudotissue data and saves to disk.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `train_data` | `AnnData` | Single-cell data for generating training pseudotissues. Must have `obs['CellType']`. |
| `test_data` | `AnnData` | Single-cell data for generating test pseudotissues. |
| `noise_data` | `AnnData` or `None` | Single-cell data of unknown/noise cell types. Mixed into test pseudotissues to simulate incomplete reference. Pass `None` if not needed. |

**Output:**

Saves a `.pkl` file to `data/{tissue_name}/{tissue_name}{n_cell_types}cell.pkl` containing three pickled objects:
1. `train` — tuple `(train_x_sim, train_with_noise_1, train_with_noise_2, train_y)`
2. `test` — tuple `(test_x_sim, test_y)`
3. `test_with_noise` — tuple `(test_x_noise, test_y)` — test data with noise cells mixed in

**Printed output:**
```
Generating artificial cells...
Generating train pseudo_bulk samples...
train Samples: 100%|██████████| 6000/6000
Generating test pseudo_bulk samples...
test Samples: 100%|██████████| 1000/1000
The data processing is complete
```

---

## `model.stage2.DANN`

Domain Adversarial Neural Network for Stage 2 batch effect removal.

### Constructor

```python
DANN(epoches, batchsize, learning_rate)
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `epoches` | `int` | Maximum training epochs. |
| `batchsize` | `int` | Batch size. Recommended: 50. |
| `learning_rate` | `float` | Adam optimizer learning rate. Recommended: 0.0001. |

**Architecture:**
- `encoder_da`: Linear → LeakyReLU → LayerNorm → Dropout
- `discriminator`: Linear → LeakyReLU → Dropout → Sigmoid
- `eDeconvolver`: Linear → LeakyReLU → Dropout → Softmax

### `train(source_data, target_data, valid_data, patience=3)`

Trains Stage 2 adversarial model.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `source_data` | `AnnData` | Training pseudotissue data (h5ad format, from `data2h5ad()`). |
| `target_data` | `AnnData` | Test pseudotissue data (h5ad format). |
| `valid_data` | `AnnData` | Validation pseudotissue data (h5ad format). Used for early stopping. |
| `patience` | `int` | Early stopping patience. Default: 3. Stage 2 converges fast. |

**Returns:** `(pred_loss, disc_loss, disc_loss_DA, best_model_weights)`

| Return | Type | Description |
|---|---|---|
| `pred_loss` | `list[float]` | Per-epoch L1 deconvolution loss. |
| `disc_loss` | `list[float]` | Per-epoch discriminator loss (train-tissue). |
| `disc_loss_DA` | `list[float]` | Per-epoch discriminator loss (target-tissue). |
| `best_model_weights` | `dict` | State dict of best encoder weights. Key: `'encoder'`. |

**Printed output per epoch:**
```
[Ep N] | Pred: 0.0010 | Disc: 1.3878 | Disc_DA: 1.3853 | Valid RMSE: 0.0209
  ★ New best RMSE! Model saved.
```

**Attributes after training:**
- `model_da.encoder_da` — encoder module (use to transfer weights to Stage 3)

---

## `model.deconv_model_with_stage_2.MBdeconv`

Full DECODE model with Stage 2 encoder transfer. Use for **transcriptomics and proteomics**.

### Constructor

```python
MBdeconv(
    num_feat, feat_map_w, feat_map_h, num_cell_type,
    epoches, Alpha, Beta,
    train_dataloader, test_dataloader
)
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `num_feat` | `int` | Number of input features (genes/proteins). Must match data dimensionality. |
| `feat_map_w` | `int` | Encoder hidden dimension (w). Recommended: 256. |
| `feat_map_h` | `int` | DimExpander expansion dimension (C). Recommended: 10. |
| `num_cell_type` | `int` | Number of cell types to deconvolve. |
| `epoches` | `int` | Maximum training epochs. Recommended: 200. |
| `Alpha` | `float` | Weight for first L1 loss term. Recommended: 1. |
| `Beta` | `float` | Weight for second L1 loss term. Recommended: 1. |
| `train_dataloader` | `DataLoader` | PyTorch DataLoader for training data. |
| `test_dataloader` | `DataLoader` | PyTorch DataLoader for test data. |

**Attributes:**
- `model.gpu_available` — `bool`, whether CUDA GPU is available
- `model.gpu` — `torch.device`, GPU device if available

### `train_model(model_save_name, use_early_stopping=True, patience=10)`

Trains Stage 3 model.

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `model_save_name` | `str` | Name for saved model file. Saved to `save_models/{num_feat}/{model_save_name}.pt`. |
| `use_early_stopping` | `bool` | Whether to use early stopping. Default: True. |
| `patience` | `int` | Early stopping patience. Recommended: 10 (transcriptomics), 50 (metabolomics). |

**Returns:** `(loss1_list, loss2_list, nce_loss_list)`

| Return | Type | Description |
|---|---|---|
| `loss1_list` | `list[float]` | Per-epoch L1 loss (term 1). |
| `loss2_list` | `list[float]` | Per-epoch L1 loss (term 2). |
| `nce_loss_list` | `list[float]` | Per-epoch NCE contrastive loss. |

**Printed output per epoch:**
```
[Ep N] 1.8s | Loss: 3.4263 (L1: 0.0009, L2: 0.0009, NCE: 6.8473) | Test: RMSE=0.0297, MAE=0.0213
  ★ New best RMSE! Model saved.
```

---

## `model.deconv_model.MBdeconv`

DECODE model **without** Stage 2 encoder transfer. Use for **metabolomics** and standalone training.

Same constructor and `train_model()` signature as `deconv_model_with_stage_2.MBdeconv`, but does not require encoder weight transfer from DANN.

**Usage:**
```python
from model.deconv_model import MBdeconv

model = MBdeconv(num_feat, feat_map_w, feat_map_h, num_cell_type,
                 epoches, Alpha, Beta, train_dataloader, valid_dataloader)
# Note: pass valid_dataloader (not test_dataloader) as second dataloader for metabolomics
```

---

## `model.utils.predict`

Run inference on a trained model.

```python
predict(test_dataloader, type_list, model, if_pure)
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `test_dataloader` | `DataLoader` | PyTorch DataLoader for test data. |
| `type_list` | `list[str]` | Cell type names (same order as training). |
| `model` | `MBdeconv` | Trained model in eval mode. |
| `if_pure` | `bool` | `True` = standard pathway (reference covers all cell types). `False` = denoiser pathway (incomplete reference, recommended for real data). |

**Returns:** `(CCC, RMSE, Corr, pred, gt)`

| Return | Type | Shape | Description |
|---|---|---|---|
| `CCC` | `float` | scalar | Lin's concordance correlation coefficient (averaged over cell types). |
| `RMSE` | `float` | scalar | Root mean square error (averaged over cell types). |
| `Corr` | `float` | scalar | Pearson's r (averaged over cell types). |
| `pred` | `np.ndarray` | (n_samples, n_cell_types) | Predicted cell type proportions. Rows sum to 1. |
| `gt` | `np.ndarray` | (n_samples, n_cell_types) | Ground truth proportions (from pseudotissue labels). |

---

## `model.utils.TrainCustomDataset`

PyTorch Dataset for training data (Stage 3 requires triplet input).

```python
TrainCustomDataset(x_sim, with_noise_1, with_noise_2, y)
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `x_sim` | `np.ndarray` | Clean pseudotissue features. |
| `with_noise_1` | `np.ndarray` | Pseudotissue with artificial noise (first copy). |
| `with_noise_2` | `np.ndarray` | Pseudotissue with artificial noise (second copy). |
| `y` | `np.ndarray` | Cell type proportion labels. |

---

## `model.utils.TestCustomDataset`

PyTorch Dataset for test/validation data.

```python
TestCustomDataset(x_sim, y)
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `x_sim` | `np.ndarray` | Pseudotissue features. |
| `y` | `np.ndarray` | Cell type proportion labels. |

---

## `model.utils.data2h5ad`

Convert numpy arrays to AnnData format for Stage 2 input.

```python
data2h5ad(x_sim, y, type_list)
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `x_sim` | `np.ndarray` | Pseudotissue feature matrix. |
| `y` | `np.ndarray` | Cell type proportion labels. |
| `type_list` | `list[str]` | Cell type names. |

**Returns:** `AnnData` with:
- `adata.X` — feature matrix
- `adata.obs` — proportion labels (one column per cell type)
- `adata.uns['cell_types']` — cell type list

---

## Saved Model Files

Models are saved to `save_models/{num_feat}/{model_save_name}.pt`.

**Loading a saved model:**
```python
model_test = MBdeconv(num_feat, feat_map_w, feat_map_h, num_cell_type,
                      epoches, Alpha, Beta, train_dataloader, test_dataloader)
model_test.load_state_dict(torch.load(f'save_models/{num_feat}/{model_save_name}.pt'))
model_test.to(device)
model_test.eval()
```

**Note:** The `num_feat` subdirectory is created automatically. If you change `num_feat`, a new subdirectory is created.

---

## Evaluation Metric Formulas

All metrics are computed cell-type-wise and averaged:

```python
# Lin's CCC
def ccc(y_true, y_pred):
    r = np.corrcoef(y_true, y_pred)[0, 1]
    mean_true, mean_pred = np.mean(y_true), np.mean(y_pred)
    var_true, var_pred = np.var(y_true), np.var(y_pred)
    return (2 * r * np.std(y_true) * np.std(y_pred)) / (var_true + var_pred + (mean_true - mean_pred)**2)

# RMSE
def rmse(y_true, y_pred):
    return np.sqrt(np.mean((y_true - y_pred)**2))

# Pearson's r
from scipy.stats import pearsonr
r, _ = pearsonr(y_true.flatten(), y_pred.flatten())
```
