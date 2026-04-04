---
name: scientific-audit
description: Systematic 359-check audit protocol across 10 categories for verifying scientific analysis outputs. Use after data loading, after each major analytical step (DEG, clustering, enrichment, modeling), and before presenting any final results. Covers numerical consistency, statistical integrity, biological plausibility, logical coherence, hallucination detection, reproducibility, data integrity, visualization integrity, ethical compliance, and LLM-specific failure modes. Returns a structured verdict (PASS / REVIEW / FAIL) with actionable findings.
allowed-tools: Read, Glob, Grep
starting-prompt: Audit the analysis results for errors, inconsistencies, and hallucinations before presenting to the user.
---

# Scientific Audit Protocol

Forensic audit of analytical outputs, code, figures, and results. Identifies errors before they propagate into conclusions, publications, or decisions.

## When to Use This Skill

**Use after:**
- ✅ Data loading or preprocessing (verify counts, dimensions, transformations)
- ✅ Each major analytical step (DEG, clustering, enrichment, modeling, integration)
- ✅ Before presenting any final results to the user
- ✅ When something in the output "feels off"
- ✅ When verifying gene names, statistics, or figure-table consistency
- ✅ When a result seems surprisingly clean, significant, or convenient

**Do not use for:**
- ❌ Running or fixing analyses — this protocol identifies issues, it does not fix them
- ❌ Suggesting alternative methods — flag the issue, the analyst chooses the fix
- ❌ Literature retrieval or database queries

**Invocation frequency:** Every 2-3 analytical steps. Mandatory, not optional.

## How to Use

### Step 1 — Determine focus area

If a specific focus is provided (e.g., "statistical integrity", "figure-table consistency"), prioritize that category and expand depth there. A focused audit is NOT an excuse to skip other categories — always run the full checklist.

If no focus area is provided, run a full audit across all 10 categories.

### Step 2 — Gather materials

Collect all relevant outputs from the analysis step:
- Code that was executed
- Console output and warnings
- Generated files (CSVs, RDS objects, figures)
- Any summary statistics printed

### Step 3 — Run the 10-category audit

Work through ALL 10 categories below. Mark each as: `checked` | `partially checked` | `not applicable`.

### Step 4 — Deliver the verdict

Use the structured report format in the [Output Format](#output-format) section.

## Audit Categories

### Category 1 — Numerical Consistency (34 checks)

*Do the numbers actually add up?*

- [ ] DEG counts in summary tables match volcano plots or bar charts
- [ ] Sample sizes in the analysis match what was loaded from the file
- [ ] Fold changes are in the expected direction (upregulated = positive log2FC)
- [ ] Percentages sum to approximately 100%
- [ ] P-values are strictly between 0 and 1
- [ ] Adjusted p-values are ≤ their corresponding raw p-values
- [ ] Correlation coefficients are between -1 and 1
- [ ] Axis ranges on plots are consistent with the actual data range
- [ ] Heatmap color scales are symmetric around zero for diverging data
- [ ] Number of rows in output tables matches the stated filtered gene/feature count
- [ ] Subset size + excluded size = original total (no silent data loss)
- [ ] Log2 fold changes are consistent with the raw mean expression values shown
- [ ] Confidence intervals are consistent with the reported effect size and sample size
- [ ] After a merge/join, the row count changed only as expected
- [ ] Counts are integers (not floats) when integer counts are expected
- [ ] No negative counts where only non-negative values are valid
- [ ] No infinite values (Inf, -Inf) in numeric columns
- [ ] No NaN/NA values in columns that should be complete
- [ ] Mean values fall within the observed min-max range
- [ ] Standard deviations are non-negative
- [ ] UMAP/tSNE coordinates have a plausible spread (not all collapsed to a single point)
- [ ] Eigenvalues from PCA are non-negative and in descending order
- [ ] Variance explained by PCA components sums to ≤ 100%
- [ ] Z-scores are centered near 0 with SD near 1 after standardization
- [ ] TPM/FPKM values sum to approximately 1,000,000 per sample
- [ ] CPM values sum to approximately 1,000,000 per sample
- [ ] Library sizes are consistent across samples (flag extreme outliers)
- [ ] Number of detected genes per cell/sample is within expected range for the assay
- [ ] Cluster sizes are reported correctly (sum = total cells/samples)
- [ ] AUC values are between 0 and 1
- [ ] Hazard ratios are positive
- [ ] Odds ratios are positive
- [ ] R-squared values are between 0 and 1
- [ ] Distance/similarity matrices are symmetric

### Category 2 — Statistical Integrity (49 checks)

*Was the right test used, correctly, on the right data?*

- [ ] `padj` or `FDR` was used for significance thresholds — NOT raw `pvalue`
- [ ] The correct multiple testing correction was applied (BH, Bonferroni, etc.)
- [ ] Normalization was applied BEFORE clustering or dimensionality reduction
- [ ] Batch effects were acknowledged and/or corrected
- [ ] Error bars are labeled as SD, SEM, or CI — and the label is present on the figure
- [ ] The correct statistical test was used for the data type and distribution
- [ ] For survival analysis: censoring was handled correctly
- [ ] Test assumptions were verified (normality for t-test, independence, proportional hazards for Cox)
- [ ] For paired data: a paired test was used
- [ ] For repeated measures: within-subject correlation was accounted for
- [ ] Variance homogeneity was checked before using tests that assume it (e.g., ANOVA)
- [ ] The reference group/intercept was correctly specified in the model
- [ ] Covariates that should have been included were included (age, sex, batch)
- [ ] Covariates that should NOT have been included were excluded (collider bias)
- [ ] For GSEA: the ranking metric was appropriate for the biological question
- [ ] For enrichment: the background gene set was correctly defined
- [ ] The model was not overfitted (parameters vs sample size ratio is reasonable)
- [ ] Independence of samples was verified (no technical replicates treated as biological)
- [ ] Pseudoreplicates were not used inappropriately (pseudobulk for single-cell DE)
- [ ] The correct dispersion estimation method was used for the sample size
- [ ] LFC shrinkage was applied for DESeq2 results when appropriate
- [ ] Pre-filtering of low-count genes was performed before DESeq2/edgeR
- [ ] The design formula was correctly specified (e.g., ~ batch + condition)
- [ ] Interaction terms were included when testing interaction effects
- [ ] Wald test vs LRT was used appropriately in DESeq2
- [ ] The correct GLM family was used (negative binomial for counts, not Gaussian)
- [ ] The test was two-tailed when directionality was not pre-specified
- [ ] Effect size was reported alongside the p-value
- [ ] Statistical power was considered given the sample size
- [ ] The FDR threshold was appropriate for the discovery context (0.05 vs 0.1 vs 0.25)
- [ ] The log2FC threshold was biologically meaningful (not just 0)
- [ ] Outlier samples were identified and their effect on results was assessed
- [ ] Cook's distance or leverage was checked for influential observations
- [ ] For GWAS: the inflation factor (lambda) was checked
- [ ] For GSEA: the leading edge subset was reported for significant hits
- [ ] NES (normalized enrichment score) was used instead of raw ES
- [ ] Minimum gene set size was appropriate for enrichment analysis
- [ ] Permutation number was sufficient for GSEA (≥ 1000)
- [ ] Gene set redundancy was addressed in enrichment results
- [ ] Directionality of GSEA (activated vs suppressed) was correctly interpreted
- [ ] The correct contrast matrix was used for multi-group comparisons
- [ ] Dunnett vs Tukey correction was used appropriately for multiple comparisons
- [ ] Bonferroni correction was not overly conservative given the correlation structure
- [ ] Inclusive inequalities used for thresholds (padj ≤ 0.05, not padj < 0.05)

### Category 3 — Biological Plausibility (39 checks)

*Does the biology make sense?*

- [ ] Gene symbols are valid for the stated organism (human = HGNC, mouse = MGI)
- [ ] Expression values are in a plausible range for the assay type
- [ ] Pathway enrichment results make sense given the biological context
- [ ] Cell type annotations are consistent with known marker genes
- [ ] Drug-target interactions are biologically plausible
- [ ] Top DEGs are not suspiciously generic (ribosomal, mitochondrial, housekeeping dominating)
- [ ] Mitochondrial or ribosomal genes are not dominating results (suggests QC failure)
- [ ] Directionality of regulation is biologically coherent
- [ ] Cell cycle genes are not dominating single-cell clusters (suggests regression needed)
- [ ] The organism and genome build are consistent throughout the pipeline
- [ ] For drug data: IC50 units are consistent (nM vs µM confusion is common)
- [ ] Sex-linked genes (XIST, RPS4Y1) are consistent with reported sample sex
- [ ] Tissue-specific marker genes are expressed in the correct tissue
- [ ] Top variable genes are biologically meaningful (not just technical noise)
- [ ] Pseudotime trajectories are biologically coherent (start = progenitor, end = mature)
- [ ] Ligand-receptor pairs are co-expressed in the right cell types
- [ ] Identified eQTLs are in cis or trans — consistent with the analysis design
- [ ] Detected metabolites are consistent with the tissue and condition
- [ ] Protein-protein interactions in the network are supported by experimental evidence
- [ ] Identified TF binding motifs are consistent with the TF's known preference
- [ ] Chromatin accessibility peaks are in expected genomic regions
- [ ] Allele frequencies of variants are consistent with the population studied
- [ ] Pathway hits are consistent across multiple enrichment methods (ORA and GSEA agree)
- [ ] Gene ontology terms are at an appropriate level of specificity

### Category 4 — Logical Coherence (46 checks)

*Does the pipeline do what it claims to do?*

- [ ] The correct comparison was made (e.g., treatment vs control, not reversed)
- [ ] No samples, genes, or observations were silently dropped without logging
- [ ] Input files are what they claim to be (right organism, assay, condition)
- [ ] The stated conclusion follows from the data shown
- [ ] All referenced files are present and non-empty
- [ ] Errors or warnings in tool outputs were not silently ignored
- [ ] The analysis direction was consistent throughout the pipeline
- [ ] Sample labels were verified against metadata before analysis
- [ ] No duplicate sample IDs are present in the input data
- [ ] The correct genome annotation version was used consistently
- [ ] The analysis was run on the correct subset
- [ ] Filters were applied at the correct stage
- [ ] Assumptions about data format were verified (rows = genes, columns = samples)
- [ ] The final output file is from the last run, not a cached or stale file
- [ ] The correct reference genome was used for the species studied
- [ ] The GTF/GFF annotation file version was matched to the genome build
- [ ] Ambient RNA contamination was removed before downstream analysis
- [ ] Doublet removal was performed before clustering
- [ ] The correct normalization was applied for the downstream task
- [ ] Highly variable gene selection was performed on normalized (not raw) counts
- [ ] PCA was performed on the correct matrix (HVGs only, not all genes)
- [ ] The neighbor graph was computed before UMAP/clustering
- [ ] The resolution parameter for Leiden/Louvain was documented
- [ ] Pseudobulk aggregation was performed per donor, not per cell
- [ ] The correct contrast direction was used in limma
- [ ] TMM normalization was applied before edgeR analysis
- [ ] Voom transformation was applied before limma on count data
- [ ] The correct gene ID type was used throughout (Ensembl vs Entrez vs Symbol)
- [ ] ID conversion was performed without many-to-many mapping issues
- [ ] The correct species database was used for annotation
- [ ] The correct BED file format was used (0-based vs 1-based coordinates)
- [ ] Peak calling was performed with the correct input/control sample
- [ ] Motif enrichment was performed against the correct background

### Category 5 — Hallucination Detection (30 checks)

*Was everything that was described actually computed?*

- [ ] Gene names, protein IDs, or database accessions were not invented
- [ ] Paper titles, authors, or DOIs were not fabricated
- [ ] Results were not described without actual computation backing them
- [ ] Database query results were not assumed without verification
- [ ] Tool call errors were not treated as successes
- [ ] All referenced file paths actually exist
- [ ] Statistics reported (mean, median, n) appear in the actual output
- [ ] Biological claims were made with citations, not stated as assumed facts
- [ ] Tool outputs were not summarized in a way that contradicts the raw output
- [ ] Significant results were not reported from a step that returned zero hits
- [ ] Figures were described as showing what they actually show
- [ ] Methods described as used were not actually skipped
- [ ] Sample sizes were not inflated relative to what was actually loaded
- [ ] Gene set names were not invented
- [ ] Database version numbers were not fabricated
- [ ] Tool parameter values stated were actually used in the code
- [ ] Intermediate results described have a corresponding code cell
- [ ] Cell types were not annotated without marker gene evidence
- [ ] Drug names or compound IDs were not invented
- [ ] Clinical trial IDs or NCT numbers were not fabricated
- [ ] Genome coordinates stated were actually computed
- [ ] Pathway names stated exist in KEGG/Reactome/GO
- [ ] Mutation nomenclature was stated with verification
- [ ] Allele frequencies were stated with database lookup, not assumed
- [ ] Structural predictions were not described as experimental structures
- [ ] Model performance metrics were stated with actual model evaluation
- [ ] Cross-validation results were described with actual CV being performed
- [ ] Figures described as "showing significant differences" had a statistical test run
- [ ] Results from a previous session were not presented as current results
- [ ] Assumptions about the data were not stated as verified facts

### Category 6 — Reproducibility & Traceability (25 checks)

*Can this analysis be re-run and verified?*

- [ ] Random seeds are set for all stochastic methods
- [ ] Software versions are logged
- [ ] All input file paths and parameters are recorded
- [ ] The analysis can be re-run from scratch given the logged steps
- [ ] All parameters are explicitly stated — no hidden defaults assumed
- [ ] No manual steps were performed outside the logged pipeline
- [ ] Intermediate files are saved at key checkpoints
- [ ] All imported libraries are explicitly listed with versions
- [ ] All downloaded reference files are versioned and checksummed
- [ ] All API calls use versioned endpoints (not 'latest')
- [ ] All database query dates are recorded (databases change over time)
- [ ] The hardware/compute environment is documented
- [ ] All thresholds and cutoffs are explicitly documented with justification
- [ ] All filtering steps are documented with the number of features removed
- [ ] The full sample metadata table is saved alongside the results
- [ ] All color palettes and plot parameters are documented for figure reproducibility
- [ ] The full session info (R sessionInfo() or Python sys.version) is saved
- [ ] There is a clear entry point to reproduce the full analysis from raw data

### Category 7 — Data Integrity & Provenance (33 checks)

*Is the right data, in the right form, from the right source?*

- [ ] The raw data source was verified (correct GEO accession, TCGA cohort, file version)
- [ ] The data is the correct assay type for the analysis
- [ ] Units of measurement were verified and are consistent throughout
- [ ] The genome/transcriptome reference version is documented
- [ ] Data transformations were not applied twice (double log, double normalization)
- [ ] The data was not already normalized when normalization was applied again
- [ ] Missing values (NaN, NA, NULL, 0) were handled explicitly and consistently
- [ ] The distinction between "zero expression" and "missing data" was preserved
- [ ] Samples were not excluded post-hoc without documentation
- [ ] The file format was verified programmatically (not just by extension)
- [ ] The correct sample type was used (tumor vs normal, primary vs metastatic)
- [ ] The correct data level was used (raw counts vs normalized vs processed)
- [ ] Batch/plate information was preserved in the metadata
- [ ] The data is from the correct tissue/cell type for the biological question
- [ ] The data is not from a retracted or flagged dataset
- [ ] Spike-in normalization was used correctly when spike-ins were present
- [ ] UMI saturation level was acceptable for the sequencing depth
- [ ] Mapping rate was acceptable (>60% RNA-seq, >80% ChIP-seq)
- [ ] Duplication rate was within acceptable range
- [ ] GC content bias was assessed and corrected if necessary
- [ ] Strand specificity was correctly identified and applied

### Category 8 — Visualization Integrity (40 checks)

*Does the figure actually show what it claims to show?*

- [ ] Axis labels are present, correct, and include units
- [ ] Legends are present and unambiguous
- [ ] Color scale is appropriate for the data type (diverging for fold change, sequential for expression)
- [ ] Axes are not truncated in a way that exaggerates or minimizes effect sizes
- [ ] Figure title is consistent with the analysis performed
- [ ] Sample sizes (n=) are reported on the figure or caption
- [ ] For box plots: what the box, whiskers, and points represent is defined
- [ ] For heatmaps: the clustering method and distance metric are stated
- [ ] For UMAP/tSNE: perplexity/n_neighbors parameters are reported
- [ ] No figures are duplicated across conditions that should be different
- [ ] Figure resolution is sufficient for the detail shown
- [ ] The y-axis starts at zero when showing absolute values
- [ ] The aspect ratio is not distorting the data
- [ ] Colors are distinguishable for colorblind viewers
- [ ] Font size is legible at the intended display size
- [ ] Overlapping data points are visible (jitter, transparency, or beeswarm)
- [ ] Statistical significance indicators (*, **, ***) are defined in the legend
- [ ] Comparison brackets connect the correct groups
- [ ] Volcano plot threshold lines are consistent with stated cutoffs
- [ ] PCA plot shows correct variance explained on each axis label
- [ ] Dendrogram orientation is consistent with the heatmap
- [ ] Cluster labels on UMAP are consistent with the cluster colors
- [ ] Trajectory/pseudotime color scale shows the correct direction
- [ ] Dot sizes in dot plots are proportional to the stated metric
- [ ] Bubble chart area (not radius) is proportional to the value
- [ ] Kaplan-Meier plot shows the correct at-risk table
- [ ] ROC curve starts at (0,0) and ends at (1,1)
- [ ] Facet labels in multi-panel figures are correct
- [ ] Figure is saved at sufficient DPI (≥ 300 DPI for raster)
- [ ] All subfigure panels are labeled (A, B, C...) for composite figures
- [ ] Axes on comparative plots are on the same scale
- [ ] Log scale is clearly indicated when used on axes
- [ ] Negative values are not plotted on log-scale axes

### Category 9 — Ethical & Compliance Flags (21 checks)

*Are there any ethical, legal, or scientific integrity concerns?*

- [ ] Human data privacy requirements are respected (no patient IDs in outputs)
- [ ] Data use agreements are honored
- [ ] AI-generated results are not presented as experimentally validated
- [ ] No claims of causality were made from purely correlational data
- [ ] No identifiable patient data is present in output files
- [ ] IRB/ethics approval was documented for human subject data
- [ ] The data sharing agreement was checked for publication restrictions
- [ ] No results were generated from a dataset with known consent violations
- [ ] Results presented as novel are not already published
- [ ] Negative results were not suppressed (publication bias check)
- [ ] Subgroup analyses were labeled as pre-specified or post-hoc
- [ ] No endpoints were changed after data collection (outcome switching)
- [ ] Statistical methods were not chosen after seeing the data (p-hacking)
- [ ] No samples were excluded after seeing their effect on results (cherry-picking)

### Category 10 — LLM-Specific Failure Modes (30 checks)

*Did the AI make a mistake that a human analyst would not?*

- [ ] Gene symbols were not confused with similar-looking symbols (CD8A vs CD8B)
- [ ] Outdated gene nomenclature was not used
- [ ] Human and mouse gene capitalization conventions were not confused (GAPDH vs Gapdh)
- [ ] No tool parameter was hallucinated that does not exist
- [ ] No deprecated function or API endpoint was used
- [ ] 0-based and 1-based genomic coordinate systems were not confused
- [ ] Rows and columns in matrix operations were not confused
- [ ] The function was not applied to the wrong axis (axis=0 vs axis=1)
- [ ] log2 and natural log transformations were not confused
- [ ] Log fold change and fold change were not confused (2^LFC vs LFC)
- [ ] Upregulated and downregulated gene lists were not swapped
- [ ] The numerator and denominator of a ratio were not confused
- [ ] The reference and alternative allele were not confused
- [ ] The case and control groups were not confused
- [ ] The training and test sets were not confused
- [ ] Correlation was not confused with causation in the interpretation
- [ ] The significance of a borderline result was not overstated
- [ ] Warning messages that indicate real problems were not ignored
- [ ] A variable name from a previous cell was not reused with a different meaning
- [ ] A cached result was not silently used instead of recomputing
- [ ] A figure that was never generated was not described
- [ ] Placeholder values (e.g., 0.05, n=10) were verified to match the actual data
- [ ] Code that runs without error but produces biologically wrong results was checked
- [ ] The direction of effect in a regression coefficient was not confused
- [ ] OR > 1 (risk factor) was not confused with OR < 1 (protective factor)
- [ ] HR > 1 (worse survival) was not confused with HR < 1 (better survival)
- [ ] Negative gene effect scores (essential) were not confused with positive (non-essential) in DepMap

## Output Format

Always return a structured audit report in this format:

```
## Scientific Audit Report

**Verdict**: [PASS | REVIEW | FAIL]
**Focus area**: [stated focus, or "Full audit"]
**Analysis audited**: [brief description]
**Timestamp**: [date/time]

---

### Critical Issues (must fix before proceeding)
These issues invalidate the current results and must be resolved.

1. [Category name] — [Issue title]
   Evidence: [exact quote or reference from the trace]
   Impact: [what this breaks]
   Suggested fix: [brief guidance]

(or "None identified")

---

### Warnings (should address before publication)
These issues may affect interpretation or reproducibility.

1. [Category name] — [Warning title]
   Evidence: [exact quote or reference from the trace]
   Impact: [what this affects]

(or "None identified")

---

### Suggestions (consider addressing)
These are best practice improvements that do not affect validity.

1. [Category name] — [Suggestion title]

(or "None")

---

### Audit Coverage Summary

| Category | Status | Issues Found |
|---|---|---|
| 1. Numerical Consistency | checked / partially checked / not applicable | N critical, N warnings |
| 2. Statistical Integrity | checked / partially checked / not applicable | N critical, N warnings |
| 3. Biological Plausibility | checked / partially checked / not applicable | N critical, N warnings |
| 4. Logical Coherence | checked / partially checked / not applicable | N critical, N warnings |
| 5. Hallucination Detection | checked / partially checked / not applicable | N critical, N warnings |
| 6. Reproducibility & Traceability | checked / partially checked / not applicable | N critical, N warnings |
| 7. Data Integrity & Provenance | checked / partially checked / not applicable | N critical, N warnings |
| 8. Visualization Integrity | checked / partially checked / not applicable | N critical, N warnings |
| 9. Ethical & Compliance Flags | checked / partially checked / not applicable | N critical, N warnings |
| 10. LLM-Specific Failure Modes | checked / partially checked / not applicable | N critical, N warnings |

**Total**: N critical issues, N warnings, N suggestions

---

### Blind Spots & Caveats
[Any limitations of this audit — what could not be checked and why]
```

## Verdicts

| Verdict | Meaning | Action Required |
|---|---|---|
| **PASS** | No critical issues found. Warnings and suggestions noted but analysis can proceed. | Proceed. Address warnings before publication. |
| **REVIEW** | One or more warnings require human judgment before proceeding. | Flag to user. Get explicit approval to continue. |
| **FAIL** | One or more critical issues found. Results are invalid until resolved. | STOP. Do not present results. Fix issues and re-run. |

## Hard Rules

- **A FAIL verdict means results are not presented to the user under any circumstances**
- **A REVIEW verdict means the user is explicitly informed before results are shown**
- **"Probably fine" and "verified correct" are not the same thing**
- **A focused audit is not an excuse to skip other categories**
- **Suspiciously clean results (p=0.049, perfectly separated clusters) deserve extra scrutiny**
- **This protocol does NOT run code, modify files, query databases, or suggest alternative analyses**
- **It reads, audits, and reports — nothing more**

## Related Skills

**Use this skill after running:**
- `bulk-rnaseq-counts-to-de-deseq2` — audit DE results
- `functional-enrichment-from-degs` — audit enrichment results
- `scrnaseq-scanpy-core-analysis` / `scrnaseq-seurat-core-analysis` — audit single-cell outputs
- `multi-omics-integration` — audit MOFA+ or integration results
- `survival-analysis-clinical` — audit clinical analysis outputs
- Any analysis skill that produces quantitative results
