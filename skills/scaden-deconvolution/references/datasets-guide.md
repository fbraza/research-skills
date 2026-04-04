# Scaden Datasets Guide

Pre-built training datasets are available for several tissues. Using these datasets skips the `scaden simulate` step entirely — start directly at `scaden process`.

---

## Available Pre-Built Datasets

### Human PBMC

| Property | Value |
|----------|-------|
| **Simulated samples** | 32,000 |
| **Source datasets** | 4 (data6k, data8k, donorA, donorC — 10X Genomics) |
| **Gene identifier** | HGNC Symbol |
| **Cell types** | CD4 T cells, CD8 T cells, B cells, NK cells, Monocytes, Dendritic cells |
| **Best for** | Blood, immune profiling, PBMC bulk RNA-seq |
| **Download** | https://figshare.com/projects/Scaden/62834 |

### Mouse Brain

| Property | Value |
|----------|-------|
| **Simulated samples** | 30,000 |
| **Source datasets** | 5 (Zeisel, Tasic, Romanov, Campbell, Chen) |
| **Gene identifier** | MGI Symbol |
| **Cell types** | Neurons, Astrocytes, Oligodendrocytes, Microglia, Endothelial, OPC |
| **Best for** | Mouse brain bulk RNA-seq; also works for human brain (cross-species) |
| **Download** | https://figshare.com/projects/Scaden/62834 |

### Human Pancreas

| Property | Value |
|----------|-------|
| **Simulated samples** | 12,000 |
| **Source datasets** | 2 (Segerstolpe, Baron) |
| **Gene identifier** | HGNC Symbol |
| **Cell types** | Alpha, Beta, Delta, Gamma, Ductal, Acinar, Stellate |
| **Best for** | Pancreatic bulk RNA-seq, diabetes studies |
| **Download** | https://figshare.com/projects/Scaden/62834 |

### Human Ascites

| Property | Value |
|----------|-------|
| **Simulated samples** | 6,000 |
| **Source datasets** | 1 (Schelker et al.) |
| **Gene identifier** | HGNC Symbol |
| **Cell types** | T cells, B cells, NK cells, Macrophages, Cancer cells, Fibroblasts |
| **Best for** | Tumor microenvironment, ascites bulk RNA-seq |
| **Download** | https://figshare.com/projects/Scaden/62834 |

---

## Using Pre-Built Datasets

Once downloaded, skip `scaden simulate` and go directly to `scaden process`:

```bash
# Download (example for PBMC)
# Visit https://figshare.com/projects/Scaden/62834 and download the .h5ad file

# Process directly with your bulk data
scaden process pbmc_training_data.h5ad my_bulk_expression.txt \
    --processed_path processed.h5ad

# Train
scaden train processed.h5ad --model_dir scaden_model/ --steps 5000

# Predict
scaden predict my_bulk_expression.txt --model_dir scaden_model/ \
    --outname scaden_predictions.txt
```

---

## Web Tool Pre-Built Datasets

The Scaden web tool at https://scaden.ims.bio includes pre-built training datasets for:
- Human PBMC
- Human Brain
- Human Pancreas

Upload your bulk expression file and download predictions without any local installation.

---

## Building Your Own Training Dataset

When no pre-built dataset matches your tissue, you must simulate from your own scRNA-seq data.

### Recommended scRNA-seq Sources

| Tissue | Database | Notes |
|--------|----------|-------|
| Any human tissue | [CellxGene Census](https://cellxgene.cziscience.com/) | Largest collection, standardized |
| Any human tissue | [Human Cell Atlas](https://www.humancellatlas.org/) | Curated, high quality |
| Brain | [Allen Brain Cell Atlas](https://portal.brain-map.org/) | Highly detailed cell types |
| Tumor | [TISCH](http://tisch.comp-genomics.org/) | Tumor microenvironment scRNA-seq |
| Blood/Immune | [10X Genomics datasets](https://www.10xgenomics.com/datasets) | PBMC, immune cells |
| Mouse | [MouseMine](https://www.mousemine.org/) | Mouse tissue scRNA-seq |

### Minimum Requirements for Custom Training Data

| Parameter | Minimum | Recommended |
|-----------|---------|-------------|
| Cells per dataset | 500 | 2,000+ |
| Cell types | 2 | 5–10 |
| Cells per cell type | 50 | 200+ |
| Simulated samples | 1,000 | 5,000–10,000 |

### Multi-Donor Strategy (Recommended)

For datasets with multiple donors, split by donor to capture inter-subject heterogeneity:

```
scrna_data/
├── donor1_counts.txt
├── donor1_celltypes.txt
├── donor2_counts.txt
├── donor2_celltypes.txt
├── donor3_counts.txt
└── donor3_celltypes.txt
```

```bash
scaden simulate --data scrna_data/ --pattern "*_counts.txt" -n 10000
```

Scaden generates training samples from each donor separately, then combines them. This is how the paper achieved CCC=0.98 on pancreas data (outperforming MuSiC's CCC=0.93).

### Mixing Multiple Datasets

You can mix scRNA-seq datasets from different protocols or labs — Scaden learns to be robust to batch effects:

```
scrna_data/
├── 10x_counts.txt          # 10X Chromium data
├── 10x_celltypes.txt
├── smartseq2_counts.txt    # Smart-seq2 data
└── smartseq2_celltypes.txt
```

This is a key advantage over GEP-based methods, which require careful batch correction before GEP construction.

---

## Cross-Species and Cross-Data-Type Usage

Scaden is uniquely robust to:

### Cross-Species Transfer
A model trained on **mouse brain** scRNA-seq can deconvolve **human brain** bulk RNA-seq:
- Paper result: CCC = 0.83 (mouse-trained → human ROSMAP data)
- Use when no human scRNA-seq reference is available for your tissue

### Cross-Data-Type Transfer
A model trained on **RNA-seq** simulated data can deconvolve **microarray** data:
- Paper result: CCC = 0.71 (RNA-seq trained → PBMC microarray)
- Comparable to CIBERSORT's microarray-optimized LM22 GEP (CCC = 0.72)

### Mixing Real and Simulated Training Data
Adding even a small number of real bulk samples with known fractions dramatically improves performance:
- Paper result: Adding 12 real PBMC samples (~2% of training data) increased CCC from 0.56 → 0.72
- Use when you have flow cytometry or other ground-truth composition data for a subset of samples
