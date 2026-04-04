# Academic pi tools

This repository contains:
- a Pi extension package in [`pi-extensions/`](./pi-extensions)
- a library of academic/bioinformatics skills kept in this repo as source content

## Pi package behavior

The published Pi package currently exposes **extensions only** via [`package.json`](./package.json):

- Pi loads flat TypeScript extension files matching `./pi-extensions/*.ts`
- this branch adds the `literature-tools` extension for typed literature retrieval
- `literature-tools` registers `pubmed_search`, `preprint_search`, `semantic_scholar_search`, and `fetch_fulltext`
- the skill directories in this repository are **not** declared in the package manifest, so those skills are **not installed automatically** when the package is installed with Pi

This is intentional: the package is meant to ship the Pi extensions without auto-installing the full skill library.

## Included extensions

### audit-enforcer

The package includes [`pi-extensions/audit-enforcer.ts`](./pi-extensions/audit-enforcer.ts), a flat-file extension for scientific audit follow-up.

It adds:
- `/audit` — asks Pi to run the `scientific-audit` skill on the current analysis
- auto-installs `scientific-audit` via the manager extension cache if the skill is missing locally
- `/audit-resolve` — marks selected audit todos as resolved
- audit result parsing for `PASS`, `REVIEW`, and `FAIL`
- sync of audit findings into the todo storage under `.pi/todos`
- a footer status showing the latest audit state and open audit todo count

### init-academic-agent

The package includes [`pi-extensions/init-academic-agent.ts`](./pi-extensions/init-academic-agent.ts), a flat-file extension that downloads or updates a project `AGENTS.md` from GitHub.

Examples:
- `/init-academic-agent`
- `/init-academic-agent fbraza/research-skills`
- `/init-academic-agent fbraza/research-skills agent-context/AGENTS.md`
- `/init-academic-agent --force`

### literature-tools

This branch adds a `literature-tools` Pi extension implemented as a flat file at [`pi-extensions/literature-tools.ts`](./pi-extensions/literature-tools.ts).

It provides typed custom tools for literature workflows:
- `pubmed_search`
- `preprint_search`
- `semantic_scholar_search`
- `fetch_fulltext`

These tools back the unified [`/literature`](./skills/literature) skill and are explicitly listed in that skill's `allowed-tools` frontmatter.

## Install the Pi extension package

```bash
pi install git:github.com/fbraza/research-skills
```

After installation, Pi will load the flat-file extensions declared in [`package.json`](./package.json).

## Quick extension checks

After reloading Pi, you can verify these extensions quickly:
- run `/audit` and confirm Pi either queues a `scientific-audit` run immediately or offers to install the missing `scientific-audit` skill first
- run `/audit-resolve` and confirm open audit todos can be selected and closed
- run `/init-academic-agent` in a git repo and confirm it creates or updates `AGENTS.md`

## Example literature workflow

Once the package is loaded, the unified [`/literature`](./skills/literature) skill can use the typed extension tools directly.

Example prompts:
- `/literature Find recent papers on TEAD inhibition in mesothelioma and summarise the strongest evidence.`
- `/literature Review preclinical evidence for KRAS G12D inhibition in pancreatic cancer.`
- `/literature Retrieve full text for DOI 10.1038/s41586-023-12345-6 and note the access route used.`

## Verification checklist for literature-tools

After reloading Pi, verify the integration with this quick checklist:
- run a `/literature ...` prompt
- confirm the session shows calls to `pubmed_search`, `semantic_scholar_search`, `preprint_search`, or `fetch_fulltext`
- confirm the model does not default to generic `WebSearch` / `WebFetch` when a typed literature tool is appropriate
- confirm `fetch_fulltext` reports the access route (`pmc`, `publisher_oa`, `biorxiv`, `scihub`, or `not_found`)
- if testing via package install, confirm `package.json` has loaded the flat-file extensions from `./pi-extensions/*.ts`

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
* [`/literature`](./skills/literature) - Unified scientific literature review, preclinical evidence extraction, citation verification, and full-text retrieval.
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

## Context

* [`agent-context/AGENTS.md`](./agent-context/AGENTS.md) - Project rules, workflow policy, and scientific guardrails.

## Notes

- If you want Pi to auto-install the skill library as well, add a `skills` entry back to the `pi` manifest in [`package.json`](./package.json).
- As currently configured, installing this package through Pi installs only the extension resources from [`pi-extensions/`](./pi-extensions).
