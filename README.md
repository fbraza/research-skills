# Academic pi tools

This repository contains:
- a Pi extension package in [`pi-extensions/`](./pi-extensions)
- a library of academic/bioinformatics skills kept in this repo as source content

## Install the Pi extension package

```bash
pi install git:github.com/fbraza/research-skills
```

After installation, Pi will load the flat-file extensions declared in [`package.json`](./package.json).

## Update the Pi extension package

```bash
pi update
```

## Skills in this repository

The following skills are present in [`skills/`](./skills) as source/reference content:

* [`/ananse-grn`](./skills/ananse-grn) - Infer gene regulatory programs with ANANSE-focused workflows.
* [`/bulk-omics-clustering`](./skills/bulk-omics-clustering) - Cluster bulk omics samples with normalization-first best practices.
* [`/bulk-rnaseq-counts-to-de-deseq2`](./skills/bulk-rnaseq-counts-to-de-deseq2) - Run bulk RNA-seq differential expression from counts with DESeq2.
* [`/cell-cell-communication`](./skills/cell-cell-communication) - Analyze ligand-receptor signaling and cell-cell communication patterns.
* [`/cellbender`](./skills/cellbender) - Clean droplet-based single-cell data with CellBender workflows.
* [`/chip-atlas-diff-analysis`](./skills/chip-atlas-diff-analysis) - Use ChIP-Atlas for differential binding and enrichment-style analyses.
* [`/chip-atlas-peak-enrichment`](./skills/chip-atlas-peak-enrichment) - Test genomic regions for ChIP-Atlas peak enrichment.
* [`/chip-atlas-target-genes`](./skills/chip-atlas-target-genes) - Retrieve and prioritize target genes from ChIP-Atlas evidence.
* [`/clinicaltrials-landscape`](./skills/clinicaltrials-landscape) - Map the clinical trial landscape for a disease, target, or modality.
* [`/coexpression-network`](./skills/coexpression-network) - Build and interpret co-expression networks such as WGCNA-style analyses.
* [`/decode-deconvolution`](./skills/decode-deconvolution) - Perform DECODE-based cell type deconvolution workflows.
* [`/disease-progression-longitudinal`](./skills/disease-progression-longitudinal) - Model longitudinal disease progression and repeated-measures trajectories.
* [`/experimental-design-statistics`](./skills/experimental-design-statistics) - Review study design, statistical assumptions, and analysis readiness.
* [`/functional-enrichment-from-degs`](./skills/functional-enrichment-from-degs) - Run ORA/GSEA-style functional enrichment from DEG results.
* [`/genetic-variant-annotation`](./skills/genetic-variant-annotation) - Annotate and prioritize genetic variants with external knowledge bases.
* [`/grn-pyscenic`](./skills/grn-pyscenic) - Infer regulons and gene regulatory networks with pySCENIC.
* [`/gwas-to-function-twas`](./skills/gwas-to-function-twas) - Connect GWAS signals to genes and function via TWAS-style workflows.
* [`/knowhows`](./skills/knowhows) - Reusable methodological guidance and best-practice know-how references.
* [`/lasso-biomarker-panel`](./skills/lasso-biomarker-panel) - Discover compact biomarker panels with LASSO/elastic-net style modeling.
* [`/mendelian-randomization-twosamplemr`](./skills/mendelian-randomization-twosamplemr) - Run two-sample Mendelian randomization analyses.
* [`/multi-omics-integration`](./skills/multi-omics-integration) - Integrate multiple omics layers with method-selection guidance.
* [`/pcr-primer-design`](./skills/pcr-primer-design) - Design and assess PCR primers with quality-control checks.
* [`/polygenic-risk-score-prs-catalog`](./skills/polygenic-risk-score-prs-catalog) - Work with PRS Catalog-derived polygenic risk score workflows.
* [`/pooled-crispr-screens`](./skills/pooled-crispr-screens) - Analyze pooled CRISPR screening data and hits.
* [`/proteomics-diff-exp`](./skills/proteomics-diff-exp) - Perform differential protein expression analysis for proteomics datasets.
* [`/scaden-deconvolution`](./skills/scaden-deconvolution) - Run Scaden-based transcriptomic deconvolution.
* [`/scientific-audit`](./skills/scientific-audit) - Audit analysis steps for methodological and reporting correctness.
* [`/scientific-visualization`](./skills/scientific-visualization) - Create publication-oriented scientific figures and visual outputs.
* [`/scientific-writing`](./skills/scientific-writing) - Draft and revise papers, grants, rebuttals, and scientific prose.
* [`/scrna-trajectory-inference`](./skills/scrna-trajectory-inference) - Infer single-cell trajectories, pseudotime, and lineage structure.
* [`/scrnaseq-scanpy-core-analysis`](./skills/scrnaseq-scanpy-core-analysis) - Run core single-cell RNA-seq analysis in Python with Scanpy.
* [`/scrnaseq-seurat-core-analysis`](./skills/scrnaseq-seurat-core-analysis) - Run core single-cell RNA-seq analysis in R with Seurat.
* [`/scvi-tools-scrna`](./skills/scvi-tools-scrna) - Use scvi-tools models for advanced single-cell RNA-seq workflows.
* [`/scvi-tools-spatial`](./skills/scvi-tools-spatial) - Apply scvi-tools methods to spatial transcriptomics problems.
* [`/spatial-transcriptomics`](./skills/spatial-transcriptomics) - Analyze spatial transcriptomics data end to end.
* [`/survival-analysis-clinical`](./skills/survival-analysis-clinical) - Perform survival and clinical outcome analyses.
* [`/upstream-regulator-analysis`](./skills/upstream-regulator-analysis) - Identify candidate upstream regulators driving observed signatures.

## Extensions

| Extension | Purpose | Docs |
|---|---|---|
| Extension | Purpose | Docs |
|---|---|---|
| `audit-enforcer` | Run scientific audits, parse findings, and sync them into todos | [`docs/audit-enforcer.md`](./docs/audit-enforcer.md) |
| `context` | Show loaded extensions, skills, context files, and usage stats | [`docs/context.md`](./docs/context.md) |
| `init-academic-agent` | Download or update project `AGENTS.md` from GitHub | [`docs/init-academic-agent.md`](./docs/init-academic-agent.md) |
| `literature-tools` | Typed literature search and PDF retrieval tools | [`docs/literature-tools.md`](./docs/literature-tools.md) |
| `manager` | Install, update, and remove skills from the repository cache | [`docs/manager.md`](./docs/manager.md) |
| `multi-edit` | Enhanced replacement for the built-in `edit` tool | [`docs/multi-edit.md`](./docs/multi-edit.md) |
| `prompt-editor` | Manage reusable prompt modes and switch quickly | [`docs/prompt-editor.md`](./docs/prompt-editor.md) |
| `session-breakdown` | Visualize recent Pi session activity, tokens, and cost | [`docs/session-breakdown.md`](./docs/session-breakdown.md) |
| `todos` | File-based todo storage with a tool and TUI manager | [`docs/todos.md`](./docs/todos.md) |
| `whimsical` | Random playful working messages during turns | [`docs/whimsical.md`](./docs/whimsical.md) |

## Context

* [`agent-context/AGENTS.md`](./agent-context/AGENTS.md) - Project rules, workflow policy, and scientific guardrails.
