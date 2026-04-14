---
name: dagster-bio-pipeline-scaffold
description: Scaffold or refactor computational biology projects into the canonical Dagster architecture used in this repository. Use when creating a new pipeline, converting a legacy `main.py` or `main.R` workflow, standardizing Python/R project layout, or adapting an existing computational skill into an asset-based project with local UI, checkpointing, and data quality checks.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
starting-prompt: Scaffold or refactor the project into the canonical Dagster-based pipeline structure, mapping the workflow into raw/processed/analysis/results assets and keeping domain logic separate from orchestration.
---

# Dagster Bio Pipeline Scaffold

Operational skill for creating or refactoring computational projects into the standard Dagster architecture.

This is an **engineering skill**, not a domain-analysis skill.

## When to Use This Skill

Use this skill when the user wants to:
- create a new computational project
- refactor an existing project with poor structure
- standardize a project across Python and R
- add checkpointing, lineage, and rerunability
- get a consistent raw → processed → analysis → results layout
- create a starter scaffold or cookiecutter
- start exploratory data analysis inside the same durable project structure

Typical triggers:
- “Set up a robust project structure”
- “Turn this workflow into a pipeline”
- “Refactor this `main.py` / notebook into something maintainable”
- “Use Dagster locally for this bioinformatics project”
- “Make my R and Python tools follow the same structure”

## Do Not Use This Skill For

- a tiny one-off utility script when the user explicitly wants only that utility
- a single-step analysis with no meaningful checkpoints
- purely methodological scientific decisions without any project-structure work

Note: in this repository, exploratory work still starts from the scaffold. Notebooks are not the standard interface.

## Mandatory Inputs / Context

Before scaffolding, gather or infer:
- project name and package/module name
- target computational skill(s) to adapt
- input data types and expected outputs
- whether R is involved
- the restart-worthy stages of the workflow
- major study-specific parameters that should become config

## Mandatory Pre-Reading

Before using this skill, read:
1. `skills/knowhows/KH_dagster_pipeline_architecture.md`
2. the target computational skill's `SKILL.md`
3. the target computational skill's `scripts/` and references

## Source of Truth

Use these layers of authority in order:
1. **Template:** `templates/cookiecutter-dagster-bio-pipeline/`
2. **This skill:** operational procedure
3. **Know-how:** rationale and architecture principles
4. **AGENTS.md:** global policy and triggers

If they ever disagree, prefer the template for exact file layout and this skill for implementation procedure.

## High-Level Procedure

### Step 1 — Articulate the workflow in plain language

Before writing code, write down:
- what the pipeline stages are
- what each stage consumes
- what each stage produces
- which stages are worth restarting independently
- where quality checks should attach

If you cannot explain the workflow cleanly, re-read the target skill.

### Step 2 — Map the workflow to the four layers

Use:
- `raw` for ingestion
- `processed` for preparation
- `analysis` for substantive computation
- `results` for deliverables

Do **not** force domain semantics into folder names.
The four-layer model is intentionally generic.

### Step 3 — Scaffold from the cookiecutter template

Template path:

`templates/cookiecutter-dagster-bio-pipeline/`

Instantiate it as the project base, then adapt it to the specific domain workflow.

The scaffold provides:
- `pyproject.toml` with `uv` + `tool.dg`
- `definitions.py`
- `defs/assets/`
- `defs/checks.py`
- `defs/resources.py`
- IO managers
- `lib/` for pure logic
- optional R folder layout
- tests and local development defaults

### Step 4 — Move domain logic into `lib/` or `R/`

#### Python logic
- extract or adapt computational functions into `src/<package>/lib/`
- keep these functions pure where possible
- avoid Dagster imports in `lib/`

#### R logic
- put self-contained scripts in `src/<package>/R/`
- read inputs from explicit paths
- write outputs to explicit paths
- use `{reticulate}` + `dagster_pipes` if the R script is executed by Dagster

### Step 5 — Wire assets in `defs/assets/`

Assets should be thin wrappers that:
- declare dependencies
- attach config and resource usage
- call `lib/` functions or launch R scripts
- return objects handled by IO managers

Asset granularity rule:

> One asset per restart-worthy checkpoint, not one asset per helper call.

### Step 6 — Attach quality checks

Add `@asset_check` where the asset has clear invariants.

Good check targets:
- non-empty tables
- expected columns present
- no invalid values
- shape not collapsed unexpectedly
- required annotations available
- outputs produced where expected

Use the `scientific-audit` skill at major methodological or interpretive checkpoints.

### Step 7 — Configure resources and persistence

Use `defs/resources.py` to register shared resources such as:
- `dataframe_io`
- `anndata_io`
- `figure_io`
- `pipes_subprocess_client`

Persistence rules:
- pipeline code returns objects
- IO managers serialize them
- raw user inputs may be placed in `data/raw/`
- pipeline-managed outputs should not be written ad hoc throughout the repo

### Step 8 — Verify the project locally

Minimum verification sequence:
1. `uv sync`
2. `dg check defs`
3. `dg dev`
4. materialize the first asset
5. materialize the next dependent asset
6. confirm stored artifacts appear in the expected layer
7. confirm checks run and report usefully

### Step 9 — Iterate asset by asset

Do not scaffold the whole analytical universe and assume it works.
Build incrementally:
- ingestion
- first processed checkpoint
- first analytical stage
- final deliverables

Commit each working stage before adding the next.

## Canonical Conventions

### Project structure roles

- `lib/` = reusable domain logic
- `defs/assets/` = Dagster wiring
- `defs/checks.py` = asset quality checks
- `defs/resources.py` = resources and IO managers
- `io_managers/` = serialization strategy
- `R/` = external R computation scripts
- `data/` = pipeline storage layers

### Naming conventions

Prefer state-based names:
- `raw_counts`
- `qc_filtered_adata`
- `normalized_counts`
- `deseq2_results`
- `marker_table`
- `umap_figure`

Avoid:
- `step1`
- `final_output`
- `run_pipeline`
- `tmp`

### Dagster conventions

- use `key_prefix` for `raw`, `processed`, `analysis`, `results`
- use `group_name` for visual grouping by subdomain
- use `code_version` for meaningful stages
- keep asset functions thin
- keep config in Dagster `Config` classes, not magic constants

## Python/R Interoperability Standard

R execution pattern:
- Python asset declares dependencies
- Python launches `Rscript` via `PipesSubprocessClient`
- env vars pass paths and config
- R script reports logs and metadata back through `dagster_pipes`

Do not use in-memory Python↔R exchange as the standard pipeline boundary.

## Anti-Patterns

Do not:
- import skill scripts directly into the project
- bury all logic inside a single `@asset`
- put Dagster imports inside pure library code
- manually write intermediate files all over the repo
- couple assets to notebook state
- treat a throwaway exploratory notebook as a finished project scaffold
- convert a legacy script line-by-line without rethinking stage boundaries

## Deliverables Expected From This Skill

When this skill is used successfully, the project should end up with:
- a canonical Dagster-oriented directory structure
- workflow stages mapped to `raw/processed/analysis/results`
- pure computational logic separated from orchestration
- asset checks at meaningful checkpoints
- a clear local execution path via `dg dev`
- R integration handled via Pipes if needed

## Practical Checklist

- [ ] Read Dagster architecture know-how
- [ ] Read target computational skill
- [ ] Articulate stage boundaries in plain language
- [ ] Map stages to four layers
- [ ] Scaffold from template
- [ ] Move pure logic into `lib/` or `R/`
- [ ] Wire thin assets
- [ ] Register IO managers and resources
- [ ] Add asset checks
- [ ] Validate with `dg check defs`
- [ ] Run locally with `dg dev`
- [ ] Confirm output paths and layer placement

## Template Location

The executable scaffold for this skill lives at:

`templates/cookiecutter-dagster-bio-pipeline/`
