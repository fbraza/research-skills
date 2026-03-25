# Experimental Design Review Protocol

Systematic review of experimental designs before analysis begins. Use for any new project, any dataset being analyzed for the first time, or any grant requiring sample size justification.

## Design Review Checklist

### Step 1 — Sample Size Adequacy
- [ ] Is n ≥ 3 per group for any omics experiment?
- [ ] Is n ≥ 6 per group for moderate effect sizes?
- [ ] For scRNA-seq DE: is n_donors ≥ 3 per condition (not n_cells)?
- [ ] For clinical studies: was a formal power calculation performed?
- [ ] Is the stated power ≥ 0.80?
- [ ] Was the effect size assumption realistic (not inflated)?
- [ ] Was the CV/variability estimate from pilot data or literature (not assumed)?
- [ ] Was a dropout/attrition buffer included (10–20%)?

### Step 2 — Confounding and Batch Effects
- [ ] Is batch confounded with condition? (**CRITICAL — unrecoverable**)
- [ ] Are any covariates perfectly correlated with condition?
- [ ] Was batch assignment randomized or balanced?
- [ ] Are processing dates, operators, or reagent lots documented?
- [ ] For multi-site studies: is site balanced across conditions?
- [ ] For longitudinal studies: is time point balanced across subjects?
- [ ] For TMT proteomics: is a pooled QC reference included in every set?

### Step 3 — Replication Type
- [ ] Are replicates biological (different individuals/animals) or technical (same sample)?
- [ ] Are technical replicates being treated as biological? (**pseudoreplication — critical flaw**)
- [ ] For cell line experiments: are replicates from independent passages?
- [ ] For mouse experiments: are replicates from different animals?
- [ ] For scRNA-seq: are replicates from different donors (not different cells from same donor)?

### Step 4 — Design Structure
- [ ] Is the design formula correctly specified?
  - Simple: `~ condition`
  - With batch: `~ batch + condition`
  - Paired: `~ subject + condition`
  - Factorial: `~ factorA + factorB + factorA:factorB`
- [ ] Are all relevant covariates included in the model?
- [ ] Are any covariates included that should not be (collider bias)?
- [ ] For paired designs: is the pairing being used in the analysis?
- [ ] Is the reference group correctly specified?

### Step 5 — Statistical Analysis Plan
- [ ] Was the primary endpoint pre-specified?
- [ ] Was the statistical test pre-specified?
- [ ] Was the significance threshold pre-specified?
- [ ] Was the multiple testing correction method pre-specified?
- [ ] Are subgroup analyses labeled as pre-specified or exploratory?
- [ ] Is there a plan for handling missing data?
- [ ] Is there a plan for outlier detection and handling?

### Step 6 — Assay-Specific Checks

**Bulk RNA-seq:**
- [ ] Sequencing depth ≥ 15M reads per sample?
- [ ] Strand specificity documented?
- [ ] rRNA depletion or poly-A selection documented?

**scRNA-seq:**
- [ ] 10x chemistry version documented?
- [ ] Target cells per sample documented?
- [ ] Ambient RNA removal planned (SoupX or CellBender)?
- [ ] Doublet detection planned?
- [ ] Pseudobulk approach planned for DE (not per-cell)?

**ATAC-seq:**
- [ ] Nuclei isolation protocol documented?
- [ ] Sequencing depth ≥ 25M reads per sample?
- [ ] IDR analysis planned for peak reproducibility?

**Proteomics:**
- [ ] TMT batch size and reference channel documented?
- [ ] Missing value imputation strategy pre-specified?
- [ ] Normalization method pre-specified?

**Clinical:**
- [ ] Primary endpoint clearly defined?
- [ ] Randomization method documented?
- [ ] Blinding documented?
- [ ] Interim analysis plan documented?

## Design Flaw Classification

### Critical Flaws (analysis should not proceed)

| Flaw | Description | Resolution |
|---|---|---|
| **Batch-condition confounding** | All samples of one condition in one batch | Redesign batch layout. If data collected: computational correction may partially help but cannot fully resolve |
| **Pseudoreplication** | Technical replicates treated as biological | Collapse to biological replicates or acknowledge as pilot data only |
| **n < 3 per group** | Insufficient replicates for valid inference | Collect more samples. n=2 is insufficient for any statistical test |
| **scRNA-seq DE without pseudobulk** | Per-cell DE inflates n artificially | Reanalyze with pseudobulk aggregation per donor |
| **Wrong design formula** | Key covariate omitted or wrong reference | Respecify design formula before analysis |
| **Post-hoc method selection** | Statistical method chosen after seeing data | Pre-specify method, document as exploratory if post-hoc |

### Serious Warnings (address before publication)

| Warning | Description | Resolution |
|---|---|---|
| **Underpowered design** | Power < 0.80 for primary endpoint | Acknowledge limitation. Collect more samples if possible. |
| **Unbalanced covariates** | Sex, age, etc. unequal across groups | Include as covariate in model |
| **Inflated effect size** | Power calculated with unrealistically large effect | Recalculate with realistic effect size |
| **No pre-specified analysis plan** | Analysis plan written after data collection | Label all analyses as exploratory |

### Advisory Notes (best practice improvements)

| Note | Description |
|---|---|
| **No pilot data for power** | CV estimated from literature, not pilot data |
| **Convenience sample size** | n chosen by availability, not power calculation |
| **No pre-registration** | Study not pre-registered |
| **Incomplete metadata** | Some covariates not recorded |

## Design Review Verdict

| Verdict | Meaning | Action |
|---|---|---|
| **APPROVED** | No critical flaws. Proceed with analysis. | Proceed. Address warnings before publication. |
| **CONDITIONAL** | Serious warnings present. | Flag to user. Document limitations explicitly. |
| **REJECTED** | Critical flaws present. Results invalid. | STOP. Resolve flaws before analysis. |

## Design Review Report Format

```
## Experimental Design Review

**Study:** [description]
**Review date:** [date]

### Verdict: [APPROVED / CONDITIONAL / REJECTED]

#### Critical Flaws (must resolve before analysis)
1. [Flaw]: [description] — [resolution]
(or "None identified")

#### Serious Warnings (should address before publication)
1. [Warning]: [description] — [resolution]
(or "None identified")

#### Advisory Notes
1. [Note]: [description]
(or "None")

### Design Checklist Summary
| Category | Status |
|---|---|
| Sample size adequacy | PASS / WARN / FAIL |
| Batch design | PASS / WARN / FAIL |
| Replication type | PASS / WARN / FAIL |
| Design formula | PASS / WARN / FAIL |
| Statistical analysis plan | PASS / WARN / FAIL |
| Assay-specific checks | PASS / WARN / FAIL |

### Recommended Statistical Analysis Plan
[Key elements of the pre-specified analysis plan]
```

## Hard Rules

- **Never approve a design with batch confounded with condition — this is unrecoverable**
- **Never approve n < 3 per group for any omics experiment**
- **Never approve scRNA-seq DE without pseudobulk aggregation per donor**
- **Never accept a power calculation with an unrealistically large effect size**
- **Never allow multiple testing correction method to be chosen after seeing the data**
- **Always specify the design formula before analysis begins**
- **Always include a dropout/attrition buffer of 10–20%**
- **Always use pilot data for CV estimation when available**
- **Always distinguish pre-specified from exploratory analyses**
- **Always verify batch balance with a chi-square test**
- **Always present the minimum detectable effect size at the available n**
- **Never say "you need more samples" without specifying exactly how many and why**
