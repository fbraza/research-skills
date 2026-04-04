# Integration Method Selection Framework

Reference guide for choosing the right multi-omics integration strategy. Read this before any integration analysis.

## Pre-Integration Protocol (Mandatory)

Before any integration analysis, assess:

### Data Inventory
- [ ] What omics layers are available?
- [ ] How many samples per layer?
- [ ] Are samples the same across layers, or partially overlapping?
- [ ] What is the missing data rate per layer?
- [ ] What is the data type per layer? (continuous counts, binary, proportions, etc.)
- [ ] What is the biological unit? (bulk tissue, single cell, patient, cell line)
- [ ] Are there known batch effects within or across layers?
- [ ] What genome build / reference version was used per layer?
- [ ] Are feature IDs consistent across layers? (Ensembl vs Symbol vs Entrez)

### Quality Gate
Before integration, verify per layer:
- [ ] QC has been performed
- [ ] Batch effects within each layer have been assessed
- [ ] Outlier samples have been identified and handled
- [ ] Feature filtering has been applied (low-variance, low-count features removed)
- [ ] Data has been appropriately normalized for the integration method
- [ ] Sample IDs are consistent and verified across all layers

**If QC has not been performed on any layer: stop and run QC first.**

## Decision Tree

```
How many omics layers?
├── 1 layer → Not multi-omics. Use single-omics analysis skill.
└── 2+ layers
    │
    ├── Same samples across all layers?
    │   ├── YES (complete data) → MOFA+, DIABLO, or concatenation
    │   └── NO (partial overlap) → MOFA+ (handles missing data natively)
    │
    ├── What is the primary question?
    │   ├── Unsupervised: find shared variation → MOFA+
    │   ├── Supervised: predict outcome → DIABLO (mixOmics)
    │   ├── Co-expression: find gene modules → WGCNA (coexpression-network skill)
    │   ├── Regulatory: find upstream drivers → upstream-regulator-analysis skill
    │   ├── Genetic: variant → molecular phenotype → eQTL/pQTL mapping
    │   ├── Single-cell multi-modal → WNN (Seurat), MultiVI (scVI-tools)
    │   ├── Bulk + single-cell → Deconvolution (MuSiC, DWLS, BayesPrism)
    │   └── Spatial + single-cell → cell2location or Tangram
    │
    └── What is the data type?
        ├── All continuous → MOFA+ (Gaussian likelihood)
        ├── Mixed (binary mutations + continuous) → MOFA+ (mixed likelihoods)
        ├── Count data → MOFA+ (Poisson) or normalize first
        └── Proportions (methylation) → MOFA+ (Beta) or M-value transform
```

## Method Reference Table

| Method | Use case | Skill |
|---|---|---|
| MOFA+ factor analysis | Unsupervised shared variation, missing data, patient stratification | `multi-omics-integration` |
| WGCNA co-expression modules | Co-expression modules, hub genes, trait correlation | `coexpression-network` |
| Upstream regulator analysis | Identify TFs driving DE results | `upstream-regulator-analysis` |
| Spatial + single-cell mapping | Reference mapping for spatial data | `spatial-transcriptomics` |
| DIABLO (mixOmics) | Supervised multi-omics classification | Manual workflow |
| WNN / MultiVI | scRNA + ATAC, RNA + protein | Manual workflow |
| totalVI | CITE-seq RNA + surface protein | Manual workflow |
| MuSiC / BayesPrism / DWLS | Bulk deconvolution with single-cell reference | Manual workflow |
| cell2location / Tangram | Spatial + single-cell reference mapping | Manual workflow |
| coloc / SMR | GWAS + eQTL colocalization | Manual workflow |
| ComBat / Harmony | Cross-cohort batch harmonization | Manual workflow |

## Data Harmonization Standards

### Feature ID Harmonization
- Convert all features to a consistent ID type (Ensembl or Symbol — never mix)
- Handle many-to-many mappings explicitly (log IDs lost in conversion)
- Aggregate duplicate IDs (sum counts, mean expression) — never silently drop

### Sample ID Verification
- Verify sample overlap across all layers before integration
- Log samples present in some layers but not others
- Never assume sample IDs are consistent — always verify programmatically

### Missing Data Assessment
- Assess missing data rate per layer before integration
- Flag any layer with >50% missing data — consider excluding

### Normalization Before Integration

| Layer | Recommended normalization for MOFA+ |
|---|---|
| RNA-seq counts | VST or log1p(CPM) |
| Proteomics (LFQ) | Log2 + median centering |
| Methylation (beta values) | M-values (logit transform) |
| ATAC-seq | Log1p(CPM) or binarize |
| Mutations (binary) | No transformation (Bernoulli likelihood) |
| Drug response (IC50) | Log10 transform |
| Metabolomics | Log2 + Pareto scaling |

## Integration Quality Control

### MOFA+ QC
- [ ] Variance explained per factor per view is interpretable (not all in one view)
- [ ] Factors are not highly correlated with each other (|r| < 0.3)
- [ ] Top factors correlate with known biological covariates (positive control)
- [ ] ELBO converged during training
- [ ] No single factor explains > 80% of variance in all views (suggests artifact)
- [ ] Factor scores are not driven by a single outlier sample

### WGCNA QC
- [ ] Scale-free topology R² > 0.85 at chosen soft power
- [ ] Module sizes are biologically reasonable
- [ ] Grey module (unassigned genes) is < 20% of total
- [ ] Module eigengenes are not highly correlated (|r| < 0.7)
- [ ] Hub genes are biologically plausible
- [ ] Module-trait correlations are not driven by outlier samples

### Deconvolution QC
- [ ] Estimated cell type proportions sum to ~1 per sample
- [ ] No cell type has negative estimated proportion
- [ ] Estimated proportions are biologically plausible for the tissue
- [ ] Reference cell types cover the major populations in the bulk data

### Cross-Cohort Harmonization QC
- [ ] PCA before and after correction shows batch effect removal
- [ ] Biological signal is preserved after correction
- [ ] No overcorrection (biological variation removed along with batch)
- [ ] Silhouette score for condition improves after correction

## Biological Interpretation Framework

### From MOFA+ Factors to Biology
```
Factor identified
     │
     ├── What views does it explain? (variance decomposition)
     │   ├── Multiple views → shared cross-omics signal (most interesting)
     │   └── One view → layer-specific variation (may be technical)
     │
     ├── What covariates does it correlate with?
     │   ├── Disease status → disease-associated factor
     │   ├── Treatment → treatment response factor
     │   └── Batch → technical factor (flag, do not over-interpret)
     │
     ├── What are the top-weighted features per view?
     │   ├── RNA: pathway enrichment on top genes
     │   ├── Methylation: genomic context of top CpGs
     │   └── Mutations: known driver genes?
     │
     └── Biological narrative:
         "Factor 3 explains 35% of RNA variance and 28% of methylation
          variance, correlates with disease stage (r=0.72), and top RNA
          features are enriched for EMT pathways."
```

## Hard Rules

- **Never integrate data without first verifying sample ID consistency across layers**
- **Never use ComBat-corrected data as input to DESeq2 or edgeR** — use batch as covariate
- **Never treat cells from the same donor as independent samples**
- **Never concatenate omics layers without normalization**
- **Never interpret a MOFA factor that correlates with batch as biological signal**
- **Never run WGCNA on raw counts** — normalize first
- **Never run WGCNA on fewer than 15 samples**
- **Never integrate more layers than the sample size can support**
- **Always log samples and features lost at every harmonization step**
- **Always verify biological signal is preserved after batch correction**
- **Always report missing data rates per layer before integration**
- **Always interpret integration results in biological context**
