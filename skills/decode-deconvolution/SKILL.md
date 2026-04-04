---
name: decode-deconvolution
description: "DECODE (Deep learning-based COmmon DEconvolution framework) estimates cell-type and cell-state proportions from bulk tissue-level data across transcriptomics, proteomics, and metabolomics using single-cell data as a reference. It is the first universal deconvolution framework that works across all three omics modalities in a single consistent pipeline. DECODE uses a four-stage architecture: pseudotissue generation from single-cell data, adversarial domain adaptation for batch effect removal (Stage 2, DANN), contrastive denoising for noise robustness (Stage 3), and inference with an optional denoiser pathway for incomplete references (Stage 4). It outperforms Scaden, MuSiC, CIBERSORTx, and scpDeconv across all modalities. Use when you have bulk omics data and a matching annotated single-cell reference. Requires Python 3.8, PyTorch 2.0, and a CUDA-capable GPU."
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
starting-prompt: Deconvolve cell type proportions from my bulk omics data using DECODE.
---

# DECODE: Deep Learning-Based Common Deconvolution Framework

## What DECODE Does

DECODE estimates **cell-type and cell-state proportions** from bulk tissue-level data (transcriptomics, proteomics, or metabolomics) using single-cell data as a reference. It is the **first universal deconvolution framework** that works across all three omics modalities in a single consistent pipeline.

### Key Advantages Over Other Methods

| Feature | DECODE | Scaden | MuSiC | CIBERSORTx | scpDeconv |
|---|---|---|---|---|---|
| Transcriptomics | ✓ | ✓ | ✓ | ✓ | ✗ |
| Proteomics | ✓ | ✗ | ✗ | ✗ | ✓ |
| Metabolomics | ✓ | ✗ | ✗ | ✗ | ✗ |
| Spatial transcriptomics | ✓ | ✗ | ✗ | ✗ | ✗ |
| Cell state deconvolution | ✓ | ✗ | ✗ | ✗ | ✗ |
| Incomplete reference handling | ✓ | partial | ✗ | ✗ | ✗ |
| Batch effect removal | adversarial | ✗ | ✗ | ✗ | ✗ |

### Performance Benchmarks (Lin's CCC, from paper)

**Transcriptomics (cross-donor, 4 cell types):**
- DECODE: ~0.97 | Scaden: ~0.90 | MuSiC: ~0.50 | CIBERSORTx: ~0.85

**Proteomics (cross-health state, 6 cell types):**
- DECODE: ~0.95 | scpDeconv: ~0.85 | Scaden: ~0.70

**Metabolomics (bone marrow, 5 cell types):**
- DECODE: ~0.65 | All other methods: near 0 or negative

---

## Architecture: Four-Stage Framework

DECODE is built around four sequential training stages:

```
Stage 1: Pseudotissue Generation
  Single-cell data → random cell sampling → pseudobulk samples
  (uniform proportion sampling, m cells per pseudotissue, U total samples)

Stage 2: Batch Effect Removal (Adversarial Training)
  Encoder + Discriminator + eDeconvolver trained jointly
  Goal: discriminator cannot distinguish train-tissue from target-tissue
  Loss: L1 (deconvolution) + BCE (adversarial)
  Output: frozen encoder weights passed to Stage 3

Stage 3: Noise Robustness (Contrastive Learning)
  Artificial impurity cells injected (≤10% of pseudotissue)
  DimExpander → Denoiser (self-attention) → Linear Attention → Deconvolver
  Contrastive NCE loss: purified features ↔ positive pairs; noise features ↔ negative pairs
  Output: trained denoiser + deconvolver

Stage 4: Inference (Two Pathways)
  If reference covers all tissue cell types → standard pathway (no denoiser)
  If reference is incomplete (common real-world case) → denoiser pathway
```

### Neural Network Components

| Module | Architecture | Purpose |
|---|---|---|
| Encoder | Linear → LeakyReLU → LayerNorm → Dropout | Map features to latent space |
| Discriminator | Linear → LeakyReLU → Dropout → Sigmoid | Distinguish train vs target tissue |
| eDeconvolver | Linear → LeakyReLU → Dropout → Softmax | Shallow deconvolution for Stage 2 |
| DimExpander | Linear → Reshape | Expand to (B, C, w) for attention |
| Denoiser | Self-attention (Q/K/V) → Mask matrix | Separate signal from noise |
| Linear Attention | Linear → Transpose | Integrate multi-solution-space features |
| Deconvolver | Linear → LayerNorm → LeakyReLU → Softmax | Final proportion prediction |

---

## Installation

### Requirements
- Python 3.8.10
- PyTorch 2.0.0 + CUDA 11.8 (GPU strongly recommended)
- See `environment.yml` for full dependency list

### Setup

```bash
# Clone repository
git clone https://github.com/forceworker/DECODE.git
cd DECODE

# Create conda environment from environment.yml
conda env create --name DECODE -f environment.yml
conda activate DECODE
```

### Key Dependencies (from environment.yml)
```yaml
python=3.8.10
cudatoolkit=11.8
torch==2.0.0
anndata==0.9.2
scanpy==1.9.8
numpy==1.24.2
pandas==2.0.3
scikit-learn==1.3.2
scipy==1.10.1
h5py==3.11.0
umap-learn==0.5.6
matplotlib==3.7.1
seaborn==0.13.2
```

---

## Input Data Requirements

### Single-Cell Reference Data (h5ad format)

DECODE requires single-cell data in **AnnData h5ad format** with:
- `adata.obs['CellType']` — cell type labels (string column)
- `adata.X` — expression/abundance matrix (cells × features)

```python
import anndata as ad
adata = ad.read_h5ad('my_sc_data.h5ad')
print(adata.obs['CellType'].value_counts())  # Check cell type distribution
```

### Omics-Specific Preprocessing

**Transcriptomics (scRNA-seq reference):**
Following Scanpy workflow:
1. Filter: genes expressed in ≥3 cells; cells with ≥200 genes and ≥200 total counts
2. Filter: cells with mitochondrial gene expression ≤20%
3. Normalize: total counts per cell to 10,000 reads
4. Log-transform: log1p
5. Select highly variable genes (HVGs) — typically 1,000–3,500 features

**Proteomics (CyTOF or mass spec reference):**
- Use protein features directly (typically 30–1,500 features)
- No log-transform required; DECODE normalizes internally
- For cross-platform: use only overlapping features between train and test

**Metabolomics (single-cell metabolomics reference):**
- Use metabolite features directly (typically 100–250 features)
- High inter-cell-type similarity is expected — DECODE handles this via denoiser
- Normalize to [0,1] range (done internally by DECODE)

### Bulk Target Data

The bulk tissue data to deconvolve must:
- Have the **same features** as the single-cell reference (same genes/proteins/metabolites)
- Be normalized using the **same procedure** as the pseudotissue data
- DECODE normalizes both pseudotissue and real bulk data by dividing by the largest eigenvalue

---

## Complete Workflow

### Step 1: Prepare Single-Cell Data

```python
import anndata as ad
import numpy as np
from sklearn.model_selection import train_test_split

# --- TRANSCRIPTOMICS: separate donors for train/test ---
train_data = ad.read_h5ad('data/lung_rna/296C_train.h5ad')
test_data  = ad.read_h5ad('data/lung_rna/302C_test.h5ad')

# Define cell types of interest
type_list = ['Luminal_Macrophages', 'Type 2 alveolar', 'Fibroblasts', 'Dendritic cells']

# Optional: define noise cell types (unknown cells to test robustness)
noise = ['Neutrophils']

# Extract noise cells from test data
if noise:
    data_h5ad_noise = test_data[test_data.obs['CellType'].isin(noise)]
    data_h5ad_noise.obs.reset_index(drop=True, inplace=True)

# Filter to cell types of interest
train_data = train_data[train_data.obs['CellType'].isin(type_list)]
train_data.obs.reset_index(drop=True, inplace=True)
test_data  = test_data[test_data.obs['CellType'].isin(type_list)]
test_data.obs.reset_index(drop=True, inplace=True)
```

```python
# --- METABOLOMICS/PROTEOMICS: single dataset, split by cell type ---
data_h5ad = ad.read_h5ad('data/bone_marrow_mb/bone_marrow.h5ad')

# Merge subtypes if needed
data_h5ad.obs['CellType'] = data_h5ad.obs['CellType'].replace({
    'HSC (catulin+)': 'HSC', 'HSC (catulin-)': 'HSC'
})

type_list = ['Erythroid', 'T', 'B', 'GMP', 'Myeloid']
noise = ['HSC']

# Extract noise
if noise:
    data_h5ad_noise = data_h5ad[data_h5ad.obs['CellType'].isin(noise)]
    data_h5ad_noise.obs.reset_index(drop=True, inplace=True)

# Filter to cell types of interest
data_h5ad = data_h5ad[data_h5ad.obs['CellType'].isin(type_list)]
data_h5ad.obs.reset_index(drop=True, inplace=True)

# Split each cell type 50/50 into train/test
train_idx, test_idx = [], []
for cell_type in data_h5ad.obs['CellType'].unique():
    idx = data_h5ad.obs[data_h5ad.obs['CellType'] == cell_type].index.tolist()
    tr, te = train_test_split(idx, test_size=0.5, random_state=42)
    train_idx.extend(tr)
    test_idx.extend(te)

train_data = data_h5ad[train_idx]
test_data  = data_h5ad[test_idx]
```

### Step 2: Generate Pseudotissue Data

```python
from data.data_process import data_process

# Initialize data processor
# Parameters:
#   type_list         — list of cell type names (must match obs['CellType'])
#   train_sample_num  — number of pseudotissue training samples (default: 6000)
#   tissue_name       — name used for output file naming
#   test_sample_num   — number of pseudotissue test samples (default: 1000)
#   sample_size       — number of cells per pseudotissue (m in paper)
#   num_artificial_cells — number of artificial noise cells for Stage 3

# For transcriptomics (high-dimensional, many cells available):
dp = data_process(
    type_list,
    train_sample_num=6000,
    tissue_name='lung_rna',
    test_sample_num=1000,
    sample_size=30,
    num_artificial_cells=30
)

# For metabolomics/proteomics (low-dimensional, fewer cells):
dp = data_process(
    type_list,
    tissue_name='bone_marrow_mb',
    test_sample_num=1000,
    sample_size=30,
    num_artificial_cells=30
    # train_sample_num defaults to 6000
)

# Generate pseudotissue data
# data_h5ad_noise: AnnData of unknown/noise cell types (pass None if no noise)
dp.fit(train_data, test_data, data_h5ad_noise)
# Output: saves data/{tissue_name}/{tissue_name}{n_cell_types}cell.pkl
```

### Step 3: Load Pseudotissue Data and Create DataLoaders

```python
import pickle
import torch
from torch.utils.data import DataLoader
from model.utils import TrainCustomDataset, TestCustomDataset, data2h5ad

# Load generated pseudotissue data
with open(f'data/{tissue_name}/{tissue_name}{len(type_list)}cell.pkl', 'rb') as f:
    train = pickle.load(f)
    test  = pickle.load(f)
    test_with_noise = pickle.load(f)  # test data with unknown cells mixed in

# Unpack
train_x_sim, train_with_noise_1, train_with_noise_2, train_y = train
test_x_sim, test_y = test

# Carve out validation set from training data (for early stopping)
valid_size = 1000
valid_x_sim        = train_x_sim[:valid_size]
valid_with_noise_1 = train_with_noise_1[:valid_size]
valid_with_noise_2 = train_with_noise_2[:valid_size]
valid_y            = train_y[:valid_size]

train_x_sim        = train_x_sim[valid_size:]
train_with_noise_1 = train_with_noise_1[valid_size:]
train_with_noise_2 = train_with_noise_2[valid_size:]
train_y            = train_y[valid_size:]

# Create PyTorch datasets and dataloaders
test_dataset  = TestCustomDataset(test_x_sim, test_y)
valid_dataset = TestCustomDataset(valid_x_sim, valid_y)
test_dataloader  = DataLoader(test_dataset,  batch_size=64, shuffle=False)
valid_dataloader = DataLoader(valid_dataset, batch_size=64, shuffle=False)

train_dataset    = TrainCustomDataset(train_x_sim, train_with_noise_1, train_with_noise_2, train_y)
train_dataloader = DataLoader(train_dataset, batch_size=64, shuffle=True)

# Convert to h5ad format for Stage 2 (adversarial training)
source_data = data2h5ad(train_x_sim, train_y, type_list)
target_data = data2h5ad(test_x_sim,  test_y,  type_list)
valid_data  = data2h5ad(valid_x_sim, valid_y, type_list)
```

### Step 4: Train Stage 2 (Batch Effect Removal)

```python
import copy
from model.stage2 import DANN

# Hyperparameters
epoches       = 200
patience_s2   = 3      # early stopping patience for Stage 2 (aggressive)
batchsize_s2  = 50
lr_s2         = 0.0001

# Initialize and train Stage 2 (DANN = Domain Adversarial Neural Network)
model_da = DANN(epoches, batchsize_s2, lr_s2)

pred_loss, disc_loss, disc_loss_DA, best_model_weights = model_da.train(
    source_data,   # train pseudotissue (h5ad)
    target_data,   # test pseudotissue (h5ad)
    valid_data,    # validation set (h5ad)
    patience=patience_s2
)
# Training output per epoch:
#   Pred: L1 deconvolution loss
#   Disc: discriminator loss (train-tissue)
#   Disc_DA: discriminator loss (target-tissue)
#   Valid RMSE: validation RMSE (used for early stopping)
# Typical convergence: 15–30 epochs
```

### Step 5: Train Stage 3 (Denoising + Deconvolution)

```python
from model.deconv_model_with_stage_2 import MBdeconv  # transcriptomics (with Stage 2)
# OR
from model.deconv_model import MBdeconv               # metabolomics/proteomics (no Stage 2)

# Hyperparameters — adjust per omics type (see Parameter Guide below)
num_feat      = 3346   # number of input features (genes/proteins/metabolites)
feat_map_w    = 256    # encoder hidden dimension (w)
feat_map_h    = 10     # DimExpander expansion dimension (C)
num_cell_type = len(type_list)
epoches       = 200    # max epochs (500 for metabolomics)
patience      = 10     # early stopping patience (50 for metabolomics)
Alpha         = 1      # weight for L1 loss term 1
Beta          = 1      # weight for L1 loss term 2
model_save_name = 'my_tissue'

# Initialize model
model = MBdeconv(
    num_feat, feat_map_w, feat_map_h, num_cell_type,
    epoches, Alpha, Beta,
    train_dataloader, test_dataloader
)

# Move to GPU if available
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
if model.gpu_available:
    model = model.to(model.gpu)

# Transfer frozen encoder from Stage 2 (transcriptomics only)
model_da.encoder_da.load_state_dict(best_model_weights['encoder'])
encoder_params = copy.deepcopy(model_da.encoder_da.state_dict())
model.encoder.load_state_dict(encoder_params)

# Train Stage 3
loss1_list, loss2_list, nce_loss_list = model.train_model(
    model_save_name,
    True,       # use early stopping
    patience
)
# Training output per epoch:
#   Loss: total loss (L1_1 + L1_2 + NCE)
#   L1: deconvolution L1 loss (two terms)
#   NCE: noise contrastive estimation loss
#   Test RMSE/MAE: test set performance
# Model saved to: save_models/{num_feat}/{model_save_name}.pt
```

### Step 6: Inference (Stage 4)

```python
from model.utils import predict

# Load best saved model
model_test = MBdeconv(
    num_feat, feat_map_w, feat_map_h, num_cell_type,
    epoches, Alpha, Beta,
    train_dataloader, test_dataloader
)
model_test.load_state_dict(
    torch.load(f'save_models/{num_feat}/{model_save_name}.pt')
)
model_test.to(device)
model_test.eval()

# Run inference
# if_pure=True  → standard pathway (reference covers all cell types)
# if_pure=False → denoiser pathway (reference is incomplete — recommended for real data)
CCC, RMSE, Corr, pred, gt = predict(
    test_dataloader,
    type_list,
    model_test,
    if_pure=False   # use denoiser for real-world robustness
)

print(f"CCC:  {CCC:.4f}")   # Lin's concordance correlation coefficient (target: >0.9)
print(f"RMSE: {RMSE:.4f}")  # Root mean square error (target: <0.05)
print(f"Corr: {Corr:.4f}")  # Pearson's r (target: >0.95)

# pred: numpy array (n_samples × n_cell_types) — predicted proportions
# gt:   numpy array (n_samples × n_cell_types) — ground truth proportions
import pandas as pd
results_df = pd.DataFrame(pred, columns=type_list)
results_df.to_csv('deconvolution_results.csv', index=False)
```

---

## Parameter Guide

### data_process Parameters

| Parameter | Default | Notes |
|---|---|---|
| `type_list` | required | List of cell type names matching `obs['CellType']` |
| `train_sample_num` | 6000 | Number of pseudotissue training samples. Increase for more cell types. |
| `test_sample_num` | 1000 | Number of pseudotissue test samples |
| `tissue_name` | required | Used for output file naming |
| `sample_size` | 30 | Cells per pseudotissue (m). Keep at 30 for most cases. |
| `num_artificial_cells` | 30 | Artificial noise cells for Stage 3. Match to `sample_size`. |

### MBdeconv Parameters

| Parameter | Transcriptomics | Metabolomics/Proteomics | Notes |
|---|---|---|---|
| `num_feat` | n_HVGs (e.g. 3346) | n_features (e.g. 107) | Must match input feature count |
| `feat_map_w` | 256 | 256 | Encoder hidden dimension |
| `feat_map_h` | 10 | 10 | DimExpander expansion (C) |
| `epoches` | 200 | 500 | More epochs for low-dimensional data |
| `patience` | 10 | 50 | More patience for noisy metabolomics |
| `Alpha` | 1 | 1 | L1 loss weight (rarely needs tuning) |
| `Beta` | 1 | 1 | L1 loss weight (rarely needs tuning) |

### DANN (Stage 2) Parameters

| Parameter | Value | Notes |
|---|---|---|
| `epoches` | 200 | Max epochs |
| `batchsize` | 50 | Batch size for Stage 2 |
| `learning_rate` | 0.0001 | Adam optimizer LR |
| `patience` | 3 | Aggressive early stopping — Stage 2 converges fast (15–30 epochs) |

### Omics-Specific Recommended Settings

| Omics | `num_feat` | `epoches` | `patience` | Stage 2? | `if_pure` |
|---|---|---|---|---|---|
| Transcriptomics (scRNA-seq) | n_HVGs (1000–3500) | 200 | 10 | Yes | False |
| Proteomics (CyTOF/mass spec) | n_proteins (30–1500) | 200 | 10 | Yes | False |
| Metabolomics | n_metabolites (100–250) | 500 | 50 | No | False |
| Spatial transcriptomics | n_HVGs | 200 | 10 | Yes | False |

---

## Omics-Specific Notes

### Transcriptomics
- Use **highly variable genes (HVGs)** only — reduces noise and computation
- Select HVGs using `scanpy.pp.highly_variable_genes()` before creating h5ad
- Cross-donor experiments: use different donors for train and test
- Cross-disease: train on one condition, test on another
- For real bulk RNA-seq: normalize to 10,000 reads + log1p, then select same HVGs

### Proteomics
- For cross-platform experiments: use only **overlapping features** between datasets
- CyTOF data: arcsinh(x/5) transformation recommended before input
- Mass spec data: use raw protein intensities (DECODE normalizes internally)
- Cell cycle deconvolution: use only differentially expressed proteins across phases

### Metabolomics
- **Most challenging omics** — high inter-cell-type similarity, few features
- Use longer training (500 epochs) and higher patience (50)
- Do NOT use Stage 2 (adversarial training) for metabolomics — use `deconv_model.py` not `deconv_model_with_stage_2.py`
- Only DECODE achieves usable performance on metabolomics; all other methods fail
- For colorectal cancer: train on mismatch repair-deficient, test on conventional

### Spatial Transcriptomics
- Grid the spatial data into spots (e.g., 750µm × 750µm or 100µm × 100µm)
- Use ungridded single-cell data as reference
- DECODE outperforms RCTD, SPOTlight, Tangram, cell2location on spatial data

### Cell State Deconvolution
- Pseudotime states: discretize continuous pseudotime (0–1) into N intervals
- Cell cycle: use G1/S/G2 as state labels
- Drug response: use time points as state labels
- Ensure states are well-separated in feature space (check UMAP before running)

---

## Handling Incomplete Single-Cell References

A critical real-world scenario: your single-cell reference does not contain all cell types present in the bulk tissue.

```python
# Scenario: reference has 4 cell types, but tissue has 5 (neutrophils unknown)
type_list = ['Luminal_Macrophages', 'Type 2 alveolar', 'Fibroblasts', 'Dendritic cells']
noise = ['Neutrophils']  # unknown cell type in test tissue

# Pass noise cells to dp.fit() — they will be mixed into test pseudotissues
dp.fit(train_data, test_data, data_h5ad_noise)

# At inference, use denoiser pathway (if_pure=False)
CCC, RMSE, Corr, pred, gt = predict(test_dataloader, type_list, model_test, if_pure=False)
# DECODE will estimate proportions of the 4 known types, treating unknowns as noise
```

**Key insight**: `if_pure=False` activates the Stage 3 denoiser, which separates signal (known cell types) from noise (unknown cell types). This is the recommended setting for all real-world applications.

---

## Evaluation Metrics

DECODE reports three metrics, all computed cell-type-wise then averaged:

| Metric | Formula | Interpretation | Target |
|---|---|---|---|
| **CCC** (Lin's) | `2rσ_yσ_ŷ / (σ²_y + σ²_ŷ + (μ_y - μ_ŷ)²)` | Combines precision and accuracy; range [-1, 1] | >0.9 excellent |
| **RMSE** | `√(1/n Σ(yᵢ - ŷᵢ)²)` | Absolute error in proportion units | <0.05 excellent |
| **Pearson's r** | `cov(y,ŷ) / (σ_y σ_ŷ)` | Linear correlation; range [-1, 1] | >0.95 excellent |

**Important**: CCC is the primary metric. It penalizes both poor correlation AND systematic bias (mean shift), making it more stringent than Pearson's r alone. A method can have high Pearson's r but low CCC if it systematically over/underestimates proportions.

---

## Multi-Omics Integration Workflow

DECODE's key advantage for cohort studies: apply the same framework across omics layers for consistent results.

```python
# Step 1: Deconvolve transcriptomics cohort
CCC_rna, RMSE_rna, Corr_rna, pred_rna, gt_rna = predict(
    test_dataloader_rna, type_list, model_rna, if_pure=False
)

# Step 2: Deconvolve proteomics cohort (same cell types, different features)
CCC_prot, RMSE_prot, Corr_prot, pred_prot, gt_prot = predict(
    test_dataloader_prot, type_list, model_prot, if_pure=False
)

# Step 3: Compare consistency across omics
from scipy.stats import spearmanr
from scipy.special import kl_div
import numpy as np

# Spearman correlation between omics predictions (per sample)
spearman_per_sample = [
    spearmanr(pred_rna[i], pred_prot[i]).correlation
    for i in range(len(pred_rna))
]
print(f"Mean cross-omics Spearman r: {np.mean(spearman_per_sample):.3f}")
# DECODE achieves near-identical predictions across omics (Spearman ~0.95+)
```

---

## File Structure

```
DECODE/
├── environment.yml              # Conda environment specification
├── train_lung_rna.ipynb         # Example: transcriptomics (Scenario 1)
├── train_lung_rna_colab.ipynb   # Google Colab version of above
├── train_bone_marrow_mb.ipynb   # Example: metabolomics (bone marrow)
├── data/
│   ├── data_process.py          # data_process class — pseudotissue generation
│   ├── lung_rna/                # Example transcriptomics data
│   └── bone_marrow_mb/          # Example metabolomics data
├── model/
│   ├── deconv_model.py          # MBdeconv without Stage 2 (metabolomics/proteomics)
│   ├── deconv_model_with_stage_2.py  # MBdeconv with Stage 2 (transcriptomics)
│   ├── stage2.py                # DANN class — adversarial batch correction
│   └── utils.py                 # Dataset classes, predict(), data2h5ad()
├── save_models/                 # Trained model weights saved here
│   └── {num_feat}/
│       └── {model_save_name}.pt
└── fig/                         # Figures
```

---

## Quick Reference: Which Script to Use

| Use Case | Model Import | Stage 2? |
|---|---|---|
| Bulk RNA-seq deconvolution | `deconv_model_with_stage_2.MBdeconv` | Yes (DANN) |
| Spatial transcriptomics | `deconv_model_with_stage_2.MBdeconv` | Yes (DANN) |
| CyTOF / proteomics | `deconv_model_with_stage_2.MBdeconv` | Yes (DANN) |
| Metabolomics | `deconv_model.MBdeconv` | No |
| Cell state (pseudotime) | `deconv_model_with_stage_2.MBdeconv` | Yes (DANN) |
| Cell state (drug response) | `deconv_model.MBdeconv` | No |

---

## Citation

```bibtex
@article{zhao2026decode,
  title={DECODE: deep learning-based common deconvolution framework for various omics data},
  author={Zhao, Tianyi and Liu, Renjie and Sun, Yuzhi and Wang, Bingtian and Zhang, Liyuan 
          and Chen, Qiuhao and Luo, Ruibang and Yuan, Zhiyuan and Wang, Guohua 
          and Cheng, Liang and Wang, Yadong},
  journal={Nature Methods},
  volume={23},
  pages={596--608},
  year={2026},
  doi={10.1038/s41592-026-03007-y}
}
```

---

## See Also

- `references/cli-reference.md` — Full API reference for all classes and functions
- `references/troubleshooting.md` — Common errors and solutions
- `references/interpretation-guide.md` — How to interpret and use deconvolution results
- `references/datasets-guide.md` — Datasets used in the paper and how to access them
- `scripts/` — Ready-to-run Python scripts for common workflows
- Google Colab example: https://colab.research.google.com/github/forceworker/DECODE/blob/main/train_lung_rna_colab.ipynb
- Zenodo experiment records: https://doi.org/10.5281/zenodo.15687743
