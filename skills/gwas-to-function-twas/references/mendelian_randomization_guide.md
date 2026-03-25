# Mendelian Randomization Guide

**Workflow:** gwas-to-function-twas  
**Purpose:** MR principles, assumptions, methods, and interpretation for causal inference in TWAS-based target prioritization.

---

## Overview

Mendelian Randomization (MR) uses genetic variants as instrumental variables (IVs) to test whether a gene's expression causally influences a disease trait. In the TWAS context, MR provides a second layer of causal evidence beyond TWAS association, helping distinguish causal genes from those that are merely correlated with disease risk through LD.

**Key question MR answers:** "Does increasing/decreasing expression of gene X causally change disease risk?"

---

## Core Assumptions (Instrumental Variable)

MR is only valid when three assumptions hold for the genetic instruments (eQTLs):

| Assumption | Description | How to check |
|-----------|-------------|-------------|
| **Relevance** | eQTLs must strongly associate with gene expression | F-statistic > 10 (weak instrument test) |
| **Independence** | eQTLs must not associate with confounders | Check for pleiotropic variants (MR-Egger intercept) |
| **Exclusion restriction** | eQTLs affect disease only through gene expression | Sensitivity analyses (weighted median, MR-Egger) |

**Violation of any assumption invalidates causal inference.** Always run sensitivity analyses.

---

## Instrument Selection

### eQTL sources (in priority order)
1. **GTEx v8** — 54 tissues, MASHR model, available via PredictDB (https://predictdb.org/)
2. **eQTLGen** — whole blood, largest sample size (N=31,684), best for blood traits
3. **DICE** — immune cell types (monocytes, T cells, NK cells), best for immune traits
4. **GTEx v7** — older version, use only if v8 unavailable

### Instrument strength criteria
```python
# Minimum requirements for valid instruments
MIN_F_STATISTIC = 10       # Weak instrument threshold
MIN_INSTRUMENTS = 3        # Minimum number of independent eQTLs
MAX_R2_CLUMPING = 0.001    # LD clumping threshold (independent instruments)
CLUMPING_WINDOW_KB = 10000 # 10 Mb window for clumping
```

### LD clumping to get independent instruments
```bash
# Use PLINK to clump eQTLs for a gene
plink --bfile ld_reference \
      --clump eqtl_sumstats.txt \
      --clump-p1 5e-8 \
      --clump-r2 0.001 \
      --clump-kb 10000 \
      --out clumped_instruments
```

---

## MR Methods

The workflow implements four complementary MR methods. Use all four and compare:

### 1. Inverse Variance Weighted (IVW) — Primary method
```python
# Assumes all instruments are valid (no pleiotropy)
# Most powerful when assumption holds
beta_ivw = sum(beta_exposure * beta_outcome / se_outcome**2) / sum(beta_exposure**2 / se_outcome**2)
se_ivw = sqrt(1 / sum(beta_exposure**2 / se_outcome**2))
p_ivw = 2 * norm.sf(abs(beta_ivw / se_ivw))
```
**Use when:** Most instruments are valid, no evidence of pleiotropy.

### 2. MR-Egger — Pleiotropy-robust
```python
# Allows for directional pleiotropy (InSIDE assumption)
# Intercept ≠ 0 indicates pleiotropy
# Less powerful than IVW but robust to some violations
```
**Use when:** Concerned about directional pleiotropy. Check intercept p-value.

### 3. Weighted Median — Outlier-robust
```python
# Valid even if up to 50% of instruments are invalid
# More robust than IVW to outlier instruments
```
**Use when:** Some instruments may be pleiotropic but majority are valid.

### 4. Weighted Mode — Plurality valid
```python
# Valid when the plurality (not majority) of instruments are valid
# Most conservative method
```
**Use when:** High heterogeneity across instruments.

---

## Sensitivity Analyses

### Heterogeneity test (Cochran's Q)
```python
# High Q statistic (p < 0.05) suggests instrument heterogeneity / pleiotropy
Q = sum((beta_outcome - beta_ivw * beta_exposure)**2 / se_outcome**2)
# If Q is significant: use MR-Egger or weighted median instead of IVW
```

### MR-Egger intercept test
```python
# Intercept ≠ 0 indicates directional pleiotropy
# p < 0.05 for intercept = evidence of pleiotropy
if egger_intercept_pvalue < 0.05:
    print("WARNING: Directional pleiotropy detected. IVW results may be biased.")
    print("Use MR-Egger slope as primary estimate.")
```

### Leave-one-out analysis
```python
# Remove one instrument at a time and re-run IVW
# If result changes dramatically when one instrument is removed → that instrument is influential
for i, instrument in enumerate(instruments):
    subset = [j for j in range(len(instruments)) if j != i]
    beta_loo = run_ivw(instruments[subset])
    loo_results.append(beta_loo)
```

### Steiger filtering
```python
# Remove instruments that explain more variance in outcome than exposure
# These are likely pleiotropic
r2_exposure = 2 * maf * (1 - maf) * beta_exposure**2
r2_outcome = 2 * maf * (1 - maf) * beta_outcome**2
keep = r2_exposure > r2_outcome  # Keep only instruments where exposure r2 > outcome r2
```

---

## Interpreting Results

### Causal direction
```python
# Positive beta: higher gene expression → higher disease risk
# Negative beta: higher gene expression → lower disease risk (protective)

if beta_ivw > 0 and p_ivw < 0.05:
    direction = "INHIBIT"  # Reducing expression should reduce risk
elif beta_ivw < 0 and p_ivw < 0.05:
    direction = "ACTIVATE"  # Increasing expression should reduce risk
else:
    direction = "INCONCLUSIVE"
```

### Confidence levels

| Criteria | Confidence Level |
|----------|-----------------|
| IVW p < 0.05 + consistent direction across all 4 methods + no pleiotropy | **High** |
| IVW p < 0.05 + consistent in ≥ 2 methods + minor heterogeneity | **Medium** |
| IVW p < 0.05 but inconsistent across methods OR pleiotropy detected | **Low** |
| IVW p ≥ 0.05 | **Not significant** |

### Consistency with TWAS
```python
# MR and TWAS should agree on direction
twas_direction = "risk_increasing" if twas_z > 0 else "risk_decreasing"
mr_direction = "risk_increasing" if beta_ivw > 0 else "risk_decreasing"

if twas_direction == mr_direction:
    consistency = "CONSISTENT"  # Strong evidence
else:
    consistency = "INCONSISTENT"  # Investigate further
```

---

## Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| F-statistic < 10 | Weak instruments | Use more eQTLs, lower p-value threshold, or skip MR for this gene |
| Only 1-2 instruments | Sparse eQTL data | Cannot run MR-Egger (requires ≥ 3); use IVW only with caution |
| Egger intercept p < 0.05 | Directional pleiotropy | Use MR-Egger slope; flag as low confidence |
| Inconsistent direction across methods | Heterogeneous instruments | Run leave-one-out; identify and remove outlier instruments |
| No eQTLs in relevant tissue | Gene not expressed in tissue | Try alternative tissues; use whole blood (eQTLGen) as proxy |
| Palindromic SNPs (A/T or C/G) | Strand ambiguity | Remove palindromic SNPs with MAF > 0.42 |

---

## Output Format

The `mr_results/` directory contains:

| File | Description |
|------|-------------|
| `mr_results_all_methods.csv` | Beta, SE, p-value for all 4 methods per gene |
| `mr_sensitivity.csv` | Heterogeneity Q, Egger intercept, Steiger filtering results |
| `mr_loo_results.csv` | Leave-one-out analysis results |
| `mr_forest_plots/` | Forest plots per gene showing instrument effects |
| `mr_scatter_plots/` | Scatter plots (exposure vs outcome beta per instrument) |
| `mr_summary.xlsx` | Excel summary with confidence levels and therapeutic direction |

---

## Key References

- **MR principles:** Davey Smith G, Hemani G (2014). *Hum Mol Genet* 23:R89-R98. https://doi.org/10.1093/hmg/ddu328
- **MR-Egger:** Bowden J, et al. (2015). *Int J Epidemiol* 44:512-525.
- **Weighted median:** Bowden J, et al. (2016). *Genet Epidemiol* 40:304-314.
- **TwoSampleMR R package:** Hemani G, et al. (2018). *eLife* 7:e34408. https://doi.org/10.7554/eLife.34408
- **MR-Base:** https://www.mrbase.org/
- **IEU OpenGWAS:** https://gwas.mrcieu.ac.uk/
- **GTEx v8 eQTLs:** https://gtexportal.org/
- **eQTLGen:** https://www.eqtlgen.org/
