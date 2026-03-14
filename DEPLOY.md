# Aria — Deployment Guide

## File Structure

Drop these files into your Claude Code project root:

```
your-project/
├── CLAUDE.md                          ← Aria's main identity and instructions
└── .claude/
    └── agents/
        ├── the-analyst.md             ← Computation + database queries
        ├── the-librarian.md           ← Literature + citations
        ├── the-strategist.md          ← Planning + user alignment
        ├── the-auditor.md             ← Forensic audit (358 checks)
        ├── the-storyteller.md         ← Figures + reports
        ├── the-architect.md           ← Experimental design + power analysis
        ├── the-navigator.md           ← Multi-omics integration + harmonization
        └── the-clinician.md           ← Clinical analysis + translational interpretation
```

## Subagent Summary

| Subagent | Role | Key trigger |
|---|---|---|
| **The Analyst** | Runs all code, queries all databases | Any computation or data analysis |
| **The Librarian** | Finds papers, verifies claims, provides citations | Any biological claim needing a source |
| **The Strategist** | Creates plans, asks clarifying questions, handles blockers | Any multi-step task or ambiguous methodology |
| **The Auditor** | 358-check forensic audit of all outputs | After every major analytical step (mandatory) |
| **The Storyteller** | Publication-ready figures, reports, quality checks | Any visualization or report request |
| **The Architect** | Experimental design, power analysis, study design review | Any new experiment, sample size question, or design review |
| **The Navigator** | Multi-omics integration, cross-modality harmonization | Any analysis requiring 2+ omics layers |
| **The Clinician** | Clinical analysis, survival modeling, translational interpretation | Any question about patient outcomes, biomarkers, or clinical context |

## File Sizes

| File | Size | Lines |
|---|---|---|
| CLAUDE.md | ~40K chars | ~1,010 lines |
| the-analyst.md | 12,286 chars | 315 lines |
| the-librarian.md | 11,496 chars | 283 lines |
| the-strategist.md | 12,087 chars | 314 lines |
| the-auditor.md | 33,494 chars | 610 lines |
| the-storyteller.md | 26,141 chars | 670 lines |
| the-architect.md | 30,270 chars | ~780 lines |
| the-navigator.md | 29,474 chars | ~760 lines |
| the-clinician.md | ~29K chars | ~740 lines |
| **Total** | **~224K chars** | **~5,482 lines** |

## How Subagents Are Invoked

In Claude Code, Aria (the orchestrator) invokes subagents like this:

```
Use the the-analyst subagent to run differential expression analysis
on the count matrix at /mnt/results/counts.csv using DESeq2.
Focus on the treatment vs control comparison.
```

```
Use the the-auditor subagent to audit the DESeq2 results.
Focus on: statistical integrity and figure-table consistency.
```

```
Use the the-librarian subagent to find papers supporting the role
of TP53 in colorectal cancer. Retrieve at least 10 papers.
Filter for human studies published after 2018.
```

```
Use the the-strategist subagent to create a plan for a full
single-cell RNA-seq analysis. The user has not specified the
normalization method or batch correction approach — ask first.
```

```
Use the the-storyteller subagent to generate a volcano plot
from the DESeq2 results at /mnt/results/deseq2_results.csv.
Label the top 20 significant genes. Export SVG and PNG.
```

```
Use the the-architect subagent to review the experimental design
for this RNA-seq study. The user has n=3 per group, samples were
processed in two batches, and all control samples are in batch 1.
Focus on: batch confounding and sample size adequacy.
```

```
Use the the-architect subagent to calculate the required sample size
for a bulk RNA-seq experiment. Target: 80% power to detect 1.5-fold
changes. Assay: human PBMC. No pilot data available.
```

```
Use the the-navigator subagent to integrate RNA-seq and proteomics
data from the same 45 patients using MOFA+. The data matrices are
at /mnt/results/rna_matrix.csv and /mnt/results/protein_matrix.csv.
Metadata is at /mnt/results/metadata.csv. Use 15 factors.
```

```
Use the the-navigator subagent to build a WGCNA co-expression network
from the VST-normalized expression matrix at /mnt/results/vst_counts.csv.
Correlate modules with disease severity and treatment response.
Identify hub genes in the top correlated modules.
```

```
Use the the-navigator subagent to identify upstream transcription factors
driving the DESeq2 results at /mnt/results/deseq2_results.csv.
Genome: hg38. Focus on the top 15 TFs.
```

```
Use the the-clinician subagent to run a Cox proportional hazards analysis
on the clinical data at /mnt/results/clinical.csv.
Time column: OS_days. Event column: OS_event (1=death, 0=censored).
Stratify by molecular subtype. Include age and stage as covariates.
Use median split for risk stratification.
```

```
Use the the-clinician subagent to discover a biomarker panel predicting
treatment response from the expression matrix at /mnt/results/expression.csv
and metadata at /mnt/results/metadata.csv.
Outcome column: response (1=responder, 0=non-responder).
Use elastic net (alpha=0.5). Report CV AUC and stability scores.
```

```
Use the the-clinician subagent to run a two-sample Mendelian randomization
analysis. Exposure: BMI (OpenGWAS ID: ieu-a-2). Outcome: type 2 diabetes
(OpenGWAS ID: ieu-a-26). Use default p-value threshold (5e-8).
Report all four MR methods and sensitivity analyses.
```

```
Use the the-clinician subagent to map the clinical trial landscape for
inflammatory bowel disease. Use the pre-built IBD config.
Highlight the Anti-IL-23 mechanism class. Include all active trials.
```

```
Use the the-clinician subagent to translate the DESeq2 results at
/mnt/results/deseq2_results.csv into clinical context.
Disease: non-small cell lung cancer. Focus on: druggable targets,
existing clinical trials, and evidence level assessment.
```

## Coordination Flow

```
New experiment or dataset
     │
     ▼
The Architect ── design review ──► REJECTED? ──► fix design first
     │ APPROVED / CONDITIONAL
     ▼
The Strategist ── ambiguous? ──► AskUserQuestion
     │
     ▼ (plan approved)
     │
     ├── Single omics ──────────► The Analyst ── runs analysis
     │
     ├── Multi-omics ──────────► The Navigator ── selects method
     │                                 │           ── harmonizes data
     │                                 │           ── runs integration
     │                                 ▼
     │                           The Analyst ── downstream analyses
     │
     └── Clinical question ────► The Clinician ── survival / progression
                                       │           ── biomarker panels
                                       │           ── MR / causal inference
                                       │           ── trial landscape
                                       │           ── translational interpretation
                                       ▼
                                 The Analyst ── risk scores / stratification
     │
     │ every 2-3 steps
     ▼
The Auditor ── reviews outputs
     │
     ▼ (PASS/REVIEW)
The Librarian ── retrieves citations
     │
     ▼
The Storyteller ── generates figures/reports
     │
     ▼
Aria delivers results to user
```

### Subagent Positions in the Family
- **The Architect** speaks *before* the experiment — design integrity
- **The Navigator** speaks *between* the layers — integration intelligence
- **The Clinician** speaks *at the bedside* — translational intelligence
- **The Auditor** speaks *after* the analysis — result integrity
- Together they form the scientific rigor backbone of the system.

## Created by Phylo
*Aria and her subagent family — built for scientists who take their work seriously.*
