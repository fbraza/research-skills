# DECODE Datasets Guide

All datasets used in the DECODE paper are publicly available. This guide provides access links, descriptions, and how each was used.

---

## Scenario 1: Cross-Donor Transcriptomics (Human Lung)

**Dataset:** Vieira Braga et al. (2019) *Nature Medicine* — Human lung single-cell atlas

| Property | Value |
|---|---|
| Cells | 12,971 |
| Features | 3,346 HVGs |
| Cell types | 4 (Type 2 alveolar, Luminal Macrophages, Fibroblasts, Dendritic cells) |
| Noise type | Neutrophils |
| Train donor | 296C (female) |
| Test donor | 302C (male) |

**Access:** https://www.covid19cellatlas.org/index.healthy.html#publication

**Download:**
```python
# Data is in Scanpy h5ad format with CellType and Donor annotations
# HVGs are pre-annotated in adata.var['highly_variable']
import scanpy as sc
adata = sc.read_h5ad('lung_data.h5ad')
train_data = adata[adata.obs['Donor'] == '296C']
test_data  = adata[adata.obs['Donor'] == '302C']
```

---

## Scenario 2: Cross-Disease Transcriptomics (Human Breast Cancer)

**Dataset:** Wu et al. (2021) *Nature Genetics* — Human breast cancer single-cell atlas

| Property | Value |
|---|---|
| Cells | 100,064 |
| Features | 2,525 HVGs |
| Cell types | 6 (B cells, T cells, CAFs, Myeloid, Endothelial, PVL) |
| Train donor | CID3586 (ER-positive) |
| Test donor | CID3921 (ER-negative) |

**Access:** GEO database, Dataset ID: GSE176078

```bash
# Download from GEO
wget "https://www.ncbi.nlm.nih.gov/geo/download/?acc=GSE176078&format=file"
```

---

## Scenario 3: Cross-Health State Proteomics (Human Breast)

**Dataset:** Gray et al. (2022) *Developmental Cell* — Human breast atlas (CyTOF)

| Property | Value |
|---|---|
| Cells | 751,970 |
| Features | 34 protein features |
| Cell types | 6 (Alveolar, Hormone-sensing, Basal, Fibroblast, Vascular lymphatic, Immune) |
| Train donor | B1H35 (premenopausal) |
| Test donor | B1H32 (postmenopausal) |

**Access:** Mendeley Data — https://doi.org/10.17632/vs8m5gkyfn.1

---

## Scenario 4: Cross-Dataset

### Murine Cell Line Proteomics

**Datasets:** Woo et al. (2021) *Nature Communications* + Dou et al. (2019) *Analytical Chemistry*

| Property | Value |
|---|---|
| Cell lines | RAW 264.7 (macrophage), C10 (airway epithelial), SVEC (endothelial) |
| Features | 762 overlapping proteins |
| Train | Woo et al. (108 cells, 1,437 proteins) |
| Test | Dou et al. (72 cells, 1,032 proteins) |

**Access:**
- Woo et al.: MassIVE accession MSV000086809
- Dou et al.: MassIVE accession MSV000084110

### Mouse Islet Transcriptomics

**Dataset:** GSE211799 (Oppenländer et al. + Tritschler et al.)

| Property | Value |
|---|---|
| Features | 2,558 HVGs (from 31,706 total) |
| Train donor | VSG_MUC13634 |
| Test donor | STZ_G1 |

**Access:** GEO accession GSE211799

---

## Scenario 5: Spatial Transcriptomics

### STARmap (Mouse Visual Cortex)

| Property | Value |
|---|---|
| Technology | STARmap |
| Cells/Spots | 1,523 cells → 189 spots (750µm × 750µm grid) |
| Features | 882 transcriptomic features |
| Cell types | 12 |
| Reference | Allen Brain Atlas Smart-seq2 (14,249 cells, 34,042 features) |

**Access:**
- STARmap data: https://github.com/QuKunLab/SpatialBenchmarking/tree/main/FigureData/Figure4/Dataset10_STARmap/Rawdata
- Smart-seq2 reference: https://drive.google.com/drive/folders/1pHmE9cg_tMcouV1LFJFtbyBJNp7oQo9J

### Slide-seqV2 (Mouse Hippocampus)

| Property | Value |
|---|---|
| Technology | Slide-seqV2 |
| Spots | 1,892 (100µm × 100µm grid) |
| Features | 17,733 |
| Cell types | 14 |

**Access:**
```python
import squidpy as sq
adata = sq.datasets.slideseqv2()
```

---

## Scenario 6: Large Number of Cell Types (Human Retina)

**Dataset:** Cowan et al. (2020) *Cell* — Human retina single-cell atlas

| Property | Value |
|---|---|
| Train | Fovea (34,723 cells) |
| Test | Periphery (19,768 cells) |
| Features | 3,789 HVGs |
| Cell types | 17 |

**Access:** CellxGene — https://cellxgene.cziscience.com/collections/2f4c738f-e2f3-4553-9db2-0582a38ea4dc

---

## Scenario 7: Real Tissue Deconvolution (PBMC)

Three peripheral blood datasets with ground-truth cell compositions:

| Dataset | Samples | Cell types | Source |
|---|---|---|---|
| Monaco | ~29 | 6 (Monocytes, CD4 T, CD8 T, NK, B, Unknown) | Monaco et al. (2019) *Cell Reports* |
| Newman | ~22 | 6 | Newman et al. (2015) *Nature Methods* |
| SDY67 | ~20 | 6 | Zimmermann et al. (2016) *PLoS ONE* |

**Access:** Via TAPE tutorials — https://sctape.readthedocs.io/datasets/#pbmc-datasets

---

## Metabolomics Datasets

### Mouse Bone Marrow Metabolomics

| Property | Value |
|---|---|
| Cells | 1,428 |
| Features | 107 metabolites |
| Cell types | 5 (GMP, B, T, Myeloid, Erythroid) |
| Noise type | HSC (hematopoietic stem cells) |
| Split | 50/50 train/test per cell type |

**Access:** Metabolomics Workbench — https://www.metabolomicsworkbench.org/data/DRCCMetadata.php?Mode=Project&ProjectID=PR001858

```python
# After download, merge HSC subtypes:
adata.obs['CellType'] = adata.obs['CellType'].replace({
    'HSC (catulin+)': 'HSC', 'HSC (catulin-)': 'HSC'
})
```

### Mouse Liver Metabolomics

| Property | Value |
|---|---|
| Cells | 724 |
| Features | 244 metabolites |
| Cell types | 3 (Hepatocytes, Endothelial, Kupffer) |

**Access:** https://github.com/yuanzhiyuan/SEAM/tree/master/SEAM/data/raw_tar

### Human Colorectal Cancer Metabolomics

| Property | Value |
|---|---|
| Cells | 57,078 |
| Features | 112 metabolites |
| Cell types | 5 (Cancer, Fibroblasts, B, Myeloid, T) |
| Train | Mismatch repair-deficient samples |
| Test | Conventional colorectal cancer samples |

**Access:** Nunes et al. (2024) *Nature Methods* — source data

---

## Cell State Datasets

### Monocyte Pseudotime (Transcriptomics)

| Property | Value |
|---|---|
| Cells | 10,846 |
| Features | 2,000 HVGs |
| States | 10 pseudotime bins (0–1 discretized) |

**Access:** Zenodo — https://doi.org/10.5281/zenodo.15682763

### Melanoma Drug Response (Metabolomics + Proteomics)

| Property | Value |
|---|---|
| Cells | 674 |
| Features | 20 proteins/metabolites |
| States | 4 (Day 0, 1, 3, 5 of BRAF inhibitor treatment) |

**Access:** Su et al. (2020) *Nature Communications* source data — https://www.nature.com/articles/s41467-020-15956-9#Sec32

### Cell Cycle Proteomics (Monocytes + Melanoma)

| Property | Value |
|---|---|
| Cells | 1,573 |
| Features | 39 differential proteins |
| States | 3 (G1, S, G2 phases) |

**Access:** Slavov Laboratory — https://scp.slavovlab.net/Leduc_et_al_2022

---

## PBMC CITE-seq (Cross-Omics Consistency)

| Property | Value |
|---|---|
| Cells | 43,791 |
| Transcriptomic features | 1,101 HVGs (from 20,568) |
| Proteomic features | 205 surface proteins |
| Cell types | 5 (CD4 T, CD8 T, B, NK, Myeloid) |
| Train donor | HS1 |
| Test donor | HS5 |

**Access:** GEO — Dataset ID GSE253721

---

## Multi-Omics Cohort Datasets

### Breast Cancer Multi-Omics (238 samples)

| Omics | Samples | GEO/Access |
|---|---|---|
| Transcriptomics | ~194 | GSE245467, GSE184869, GSE161865 |
| Proteomics | ~44 | PDC000120 (Proteomics Data Commons) |

Groups: Nonmetastatic (n=99), Metastatic (n=45), Brain metastasis (n=94)
Reference: Wu et al. (2021) *Nature Genetics* (GSE176078)

### Mouse Liver Multi-Omics (285 samples)

| Omics | Samples | Access |
|---|---|---|
| Transcriptomics | ~270 | GSE196941, GSE200356, GSE222550, GSE243906, GSE253217, GSE256501, GSE267916, GSE269058 |
| Proteomics | ~10 | MassIVE MSV000092153 |
| Metabolomics | ~5 | Ghazalpour et al. (2014) *Mol Syst Biol* |

Groups: Chow (n=208), HFD (n=63), HFD+TLC (n=4), NASH (n=6), WDA (n=4)
