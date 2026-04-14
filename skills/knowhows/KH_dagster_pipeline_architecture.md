# Dagster pipeline architecture for computational projects

**Knowhow ID:** KH_dagster_pipeline_architecture
**Category:** Pipeline Architecture
**Version:** 1.0
**Last Updated:** April 2026
**Short Description:** Architectural standard for building local-first computational biology projects with Dagster, including Python/R interoperability, asset layering, IO management, and project scaffolding.
**Keywords:** dagster, pipeline architecture, assets, bioinformatics, R integration, dagster pipes, project structure, data lineage

---

## Why this know-how exists

Computational projects need more than scripts with conventions. They need:
- explicit lineage between steps
- rerunnable checkpoints
- a local UI to inspect and re-execute work
- data quality checks attached to pipeline stages
- one project structure across Python-only, R-only, and mixed pipelines

Dagster is the standard framework for those cases.

This guide is not a domain workflow. It is the engineering architecture used to host domain workflows from the skills in this repository.

---

## When to use Dagster

Use the canonical Dagster architecture when the project is:
- multi-step
- expected to be rerun
- expected to evolve over time
- producing intermediate checkpoints that matter
- mixing Python and R
- large enough that failure recovery and lineage matter
- intended to be understandable by someone other than the original author
- exploratory but still part of a real project that should remain structured over time

### Dagster is usually worth it for
- end-to-end omics analyses
- research project scaffolds
- pipelines with raw → processed → analysis → results stages
- pipelines where one step may fail after expensive preprocessing
- pipelines where you want a visual DAG and selective reruns

### Cases where Dagster would often be considered heavy in the abstract
- a one-off helper script
- a tiny format conversion utility
- a single-function analysis with no meaningful checkpoints

In this repository, however, the practical standard is simpler:

> if the work is part of a computational project, start from the scaffold.

That includes EDA. Notebook-first workflows are not the standard here. The only routine exception is an explicitly requested one-off utility script.

---

## Core principles

### 1. Assets are the contracts

Each meaningful pipeline stage is a Dagster asset.

An asset should represent a checkpoint you care about:
- load raw counts
- QC-filter the object
- normalize the matrix
- run differential expression
- export a table or figure

A good rule:

> If this step fails, would I want to rerun from here instead of from the beginning?

If yes, it should likely be an asset.

### 2. Use the four-layer model everywhere

Every computational project maps its outputs into four layers:

```text
raw        ingestion of external inputs
processed  preparation and transformation
analysis   core computation
results    user-facing deliverables
```

This model is intentionally generic. It works for transcriptomics, clinical modeling, variant analysis, enrichment, network inference, and any other computational skill.

### 3. Separate orchestration from domain logic

Keep business logic separate from Dagster wiring.

- `lib/` contains pure computational functions
- `defs/assets/` contains thin `@asset` wrappers
- `defs/resources.py` wires IO managers and shared resources
- `defs/checks.py` defines asset quality checks

This keeps the analytical logic testable and portable.

### 4. IO managers own persistence

Pipeline code should not manually scatter writes across the filesystem.

Instead:
- assets return objects
- IO managers serialize them
- storage paths follow the asset key
- the pipeline stays resumable and inspectable

Users may place immutable source files in `data/raw/`, but pipeline-managed outputs should be written by IO managers.

### 5. R interoperability is file-based and explicit

Python and R do **not** exchange large bioinformatics objects in memory.

Use:
- Dagster asset in Python to declare dependencies
- `PipesSubprocessClient` to launch `Rscript`
- environment variables for config and file paths
- CSV, parquet, h5ad, or other explicit file contracts between stages

Avoid in-memory Python↔R bridges for pipeline stages. They are fragile, memory-hungry, and undermine checkpointing.

### 6. Quality checks are first-class

`@asset_check` is the engineering counterpart to scientific auditing.

Use asset checks for properties such as:
- object not empty
- required columns present
- no impossible values
- expected dimensions retained
- no NaN in a stage that should be complete

Use the `scientific-audit` skill at major methodological or interpretive checkpoints.

### 7. Local-first execution

The standard is local execution with Dagster OSS.

Use:
- `dg check defs` to validate the project wiring
- `dg dev` to inspect the graph and materialize assets

Cloud deployment is not required for the architecture to be useful.

---

## Canonical project topology

```text
my-analysis/
├── pyproject.toml
├── .pre-commit-config.yaml
├── .python-version
├── src/
│   └── my_analysis/
│       ├── __init__.py
│       ├── definitions.py
│       ├── defs/
│       │   ├── __init__.py
│       │   ├── assets/
│       │   │   ├── raw.py
│       │   │   ├── processed.py
│       │   │   ├── analysis.py
│       │   │   └── results.py
│       │   ├── checks.py
│       │   ├── config.py
│       │   └── resources.py
│       ├── io_managers/
│       │   ├── anndata.py
│       │   ├── dataframe.py
│       │   └── figure.py
│       ├── lib/
│       │   ├── qc.py
│       │   └── analysis.py
│       └── R/
│           └── ...
├── data/
│   ├── raw/
│   ├── processed/
│   ├── analysis/
│   └── results/
└── tests/
```

The exact executable scaffold lives in:

`templates/cookiecutter-dagster-bio-pipeline/`

That template, not prose, should be the operational source of truth for the on-disk structure.

---

## Asset layering and naming guidance

### Layer assignment

- `raw/*` for ingested canonical inputs inside the pipeline
- `processed/*` for cleaned, filtered, normalized, transformed intermediates
- `analysis/*` for substantive analytical outputs
- `results/*` for exported tables, figures, reports

### Naming guidance

Prefer names that describe state, not actions:
- `raw_counts`
- `qc_filtered_adata`
- `normalized_counts`
- `deseq2_results`
- `umap_figure`

Avoid vague names like:
- `step1`
- `output_final`
- `run_analysis`
- `tmp_data`

### Asset granularity

Too coarse:
- one asset for the whole pipeline

Too fine:
- one asset per helper function call

Good granularity:
- one asset per restart-worthy stage

---

## Storage conventions

Default persistence should be type-aware.

### Recommended defaults

| Object type | Preferred format | Notes |
|---|---|---|
| `pandas.DataFrame` | parquet | fast, typed, good Python/R interoperability |
| Result tables for users | parquet + CSV export | parquet for pipeline, CSV for convenience |
| `AnnData` | h5ad | standard scverse checkpoint format |
| Figures | PNG + SVG | PNG for quick use, SVG for publication editing |
| R tabular exchange | CSV or parquet | easiest cross-language contract |

### Practical rule

Choose file formats that are:
- inspectable
- stable
- cross-language where needed
- appropriate for object size

Do not optimize prematurely for in-memory exchange.

---

## R integration standard

### Use Dagster Pipes

The standard R execution pattern is:
1. Python `@asset` defines dependencies
2. Python launches `Rscript` with `PipesSubprocessClient`
3. environment variables pass input paths, output paths, and config
4. R script uses `reticulate` to import `dagster_pipes`
5. R reports logs, metadata, and checks back to Dagster

### Why this is the standard

- keeps one DAG for Python and R
- keeps R native for R-only tools such as DESeq2, edgeR, limma, Seurat, CellChat
- avoids fragile in-process conversion of large objects
- preserves checkpointing and rerunability

### R script rules

- self-contained
- reads explicit inputs
- writes explicit outputs
- no hidden working-directory assumptions
- no implicit dependence on notebook state

---

## Quality strategy: asset checks + scientific audit

These are complementary, not competing.

### Asset checks answer
- is this artifact structurally valid?
- did the stage produce something non-empty and sane?
- are key invariants preserved?

### Scientific audit answers
- was the method appropriate?
- does the interpretation make sense?
- are the statistical claims defensible?
- are there hallucinations or incoherences?

Use both.

---

## Migration strategy from legacy `main.py` or `main.R`

When refactoring an existing scripted workflow:

1. list the existing stages in plain language
2. identify restart-worthy checkpoints
3. map them to the four layers
4. extract reusable functions into `lib/` or self-contained R scripts
5. wrap each checkpoint as an asset
6. move persistence into IO managers
7. add asset checks at meaningful stages
8. verify with `dg check defs` and `dg dev`

Do not port line-by-line without rethinking the stage boundaries.

---

## Anti-patterns

Avoid these patterns:
- importing project logic directly from a skill's `scripts/` directory
- keeping all logic inside one massive `@asset`
- placing Dagster-specific logic inside reusable `lib/` functions
- manually writing ad hoc files throughout `data/`
- mixing raw inputs and processed outputs in the same folder
- using in-memory Python↔R conversion as a pipeline boundary
- making every helper function its own asset
- skipping quality checks because the UI already shows materializations

---

## Recommended workflow

For new or refactored reusable pipelines:
1. read this know-how
2. load the `dagster-bio-pipeline-scaffold` skill
3. scaffold from `templates/cookiecutter-dagster-bio-pipeline/`
4. read the target computational skill
5. adapt the workflow into assets and pure functions
6. add checks
7. validate with `dg check defs`
8. iterate locally with `dg dev`

---

## Bottom line

Use Dagster as the standard architecture for reusable computational pipelines.
Keep AGENTS.md short and authoritative.
Keep architecture rationale in this know-how.
Keep implementation procedure in the dedicated pipeline skill.
Keep the actual on-disk structure in the cookiecutter template.
