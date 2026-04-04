# Example Datasets for WGCNA Analysis

This document lists publicly available datasets suitable for testing and
demonstrating the `coexpression-network` (WGCNA) workflow. All datasets
meet the minimum requirements: ≥15 samples, normalized expression data,
and at least one quantitative or categorical trait for module-trait correlation.

---

## Built-in Example Dataset (Default)

### Female Mouse Liver — Metabolic Traits
The default example dataset used by `load_example_wgcna_data()`.

| Property | Value |
|----------|-------|
| **Source** | Langfelder & Horvath (2008) WGCNA paper |
| **Organism** | *Mus musculus* (mouse) |
| **Tissue** | Liver |
| **Samples** | 135 female mice |
| **Genes** | ~3,600 (top variable) |
| **Traits** | Body weight, liver weight, blood glucose, insulin, triglycerides |
| **Access** | Built into WGCNA R package: `data(femData)` |
| **Why use it** | Classic WGCNA benchmark; well-characterized modules; fast runtime |

```r
library(WGCNA)
data(femData)  # Loads datExpr0 and traitData
```

---

## Human Datasets

### 1. TCGA-BRCA — Breast Cancer
| Property | Value |
|----------|-------|
| **GEO/Source** | TCGA via TCGAbiolinks or recount3 |
| **Organism** | *Homo sapiens* |
| **Tissue** | Breast tumor |
| **Samples** | ~1,100 (use subset of 100-200 for testing) |
| **Genes** | ~20,000 protein-coding |
| **Traits** | PAM50 subtype, ER/PR/HER2 status, survival, grade |
| **Access** | `BiocManager::install("TCGAbiolinks")` |
| **Why use it** | Large, well-annotated; known breast cancer modules (immune, proliferation) |
| **Note** | Subsample to 100-200 samples for reasonable runtime |

```r
library(TCGAbiolinks)
query <- GDCquery(project = "TCGA-BRCA",
                  data.category = "Transcriptome Profiling",
                  data.type = "Gene Expression Quantification",
                  workflow.type = "STAR - Counts")
```

### 2. GSE48350 — Human Brain Aging
| Property | Value |
|----------|-------|
| **GEO Accession** | GSE48350 |
| **Organism** | *Homo sapiens* |
| **Tissue** | Brain (multiple regions) |
| **Samples** | 173 |
| **Genes** | ~47,000 probes (Affymetrix) |
| **Traits** | Age, brain region, sex, PMI |
| **Access** | `GEOparse` (Python) or `GEOquery` (R) |
| **Why use it** | Classic aging/brain WGCNA; well-characterized age-related modules |

```r
library(GEOquery)
gse <- getGEO("GSE48350", GSEMatrix = TRUE)
```

### 3. GSE19804 — Lung Cancer vs Normal
| Property | Value |
|----------|-------|
| **GEO Accession** | GSE19804 |
| **Organism** | *Homo sapiens* |
| **Tissue** | Lung (tumor + adjacent normal) |
| **Samples** | 120 (60 tumor, 60 normal) |
| **Genes** | ~54,000 probes |
| **Traits** | Tumor vs normal, clinical stage, smoking status |
| **Access** | `GEOquery` |
| **Why use it** | Clear tumor/normal contrast; good for identifying cancer-associated modules |

### 4. GTEx — Multi-tissue Expression (via datalake)
| Property | Value |
|----------|-------|
| **Source** | GTEx v8 (download from https://gtexportal.org/home/datasets) |
| **Organism** | *Homo sapiens* |
| **Tissue** | 54 tissues available |
| **Samples** | 50-800 per tissue |
| **Genes** | ~56,000 |
| **Traits** | Age, sex, BMI, tissue type, RIN score |
| **Access** | Download from GTEx portal or use `GEOquery` for GEO-hosted subsets |
| **Why use it** | Large, multi-tissue; good for tissue-specific module discovery |
| **Recommended tissue** | Whole blood (N=670), skeletal muscle (N=706), or adipose (N=581) |

---

## Mouse Datasets

### 5. GSE60450 — Mouse Mammary Gland Development
| Property | Value |
|----------|-------|
| **GEO Accession** | GSE60450 |
| **Organism** | *Mus musculus* |
| **Tissue** | Mammary gland |
| **Samples** | 12 (basal vs luminal, 3 developmental stages) |
| **Genes** | ~27,000 |
| **Traits** | Cell type (basal/luminal), developmental stage |
| **Access** | `GEOquery` |
| **Note** | Small dataset (12 samples) — use only for quick testing, not robust WGCNA |

### 6. GSE132044 — Mouse Aging Atlas
| Property | Value |
|----------|-------|
| **GEO Accession** | GSE132044 |
| **Organism** | *Mus musculus* |
| **Tissue** | Multiple tissues |
| **Samples** | 200+ |
| **Genes** | ~20,000 |
| **Traits** | Age (3, 12, 24 months), tissue, sex |
| **Access** | `GEOquery` |
| **Why use it** | Good for age-related co-expression modules across tissues |

---

## Dataset Selection Guide

| Goal | Recommended Dataset |
|------|-------------------|
| Quick testing / learning | Female mouse liver (built-in) |
| Human cancer modules | TCGA-BRCA or GSE19804 |
| Brain/neurological | GSE48350 |
| Aging biology | GSE132044 or GSE48350 |
| Multi-tissue comparison | GTEx (datalake) |
| Immune modules | GTEx whole blood or TCGA |

## Minimum Requirements Reminder

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Samples | 15 | 30+ |
| Genes (after filtering) | 1,000 | 5,000–15,000 |
| Data type | Normalized (VST/rlog/TPM) | VST or rlog from DESeq2 |
| Traits | 1 | 3–5 quantitative or categorical |

**Do NOT use raw counts directly** — normalize first with DESeq2 VST or rlog.

---

## Loading Example Data

```r
# Built-in example (fastest)
source("scripts/load_example_data.R")
wgcna_data <- load_example_wgcna_data()
datExpr <- wgcna_data$datExpr  # 135 samples × 3,600 genes
meta     <- wgcna_data$meta    # Metabolic traits

# From GEO
library(GEOquery)
gse <- getGEO("GSE48350", GSEMatrix = TRUE)
expr_mat <- exprs(gse[[1]])
pheno    <- pData(gse[[1]])
```

---

## References

- Langfelder P, Horvath S (2008). WGCNA: an R package for weighted correlation network analysis. *BMC Bioinformatics* 9:559.
- GTEx Consortium (2020). The GTEx Consortium atlas of genetic regulatory effects across human tissues. *Science* 369:1318-1330.
- TCGA Research Network: https://www.cancer.gov/tcga
- GEO database: https://www.ncbi.nlm.nih.gov/geo/
