# {{ cookiecutter.project_name }}

Computational biology project scaffolded on Dagster for local-first execution.

This repository's convention is to start **all** computational work here, including EDA. Notebook-first workflows are not used.

## What this template gives you

- Dagster project metadata for `dg`
- canonical `raw / processed / analysis / results` data layering
- thin asset wrappers around reusable domain logic
- IO managers for DataFrames, AnnData, and figures
- a place for self-contained R scripts executed via Dagster Pipes
- starter tests and local quality tooling

## Important

This is a **starter scaffold**, not a complete scientific workflow.
Replace the placeholder assets and pure functions with logic adapted from the target computational skill.

## Quickstart

```bash
make sync
make hooks
make check-defs
make dev
```

If you prefer running tools directly, the `Makefile` wraps `uv run` commands so manual virtualenv activation is not required.

The Dagster UI runs locally, typically at:

- http://localhost:3000

## First adaptation steps

1. Put immutable source files in `data/raw/`
2. Read the target computational skill's `SKILL.md` and scripts
3. Map the workflow to `raw`, `processed`, `analysis`, `results`
4. Replace the generic `lib/` functions with study-specific logic
5. Replace the example assets with real domain assets
6. Add meaningful `@asset_check` functions
7. Validate with `make check-defs`

## Common commands

```bash
make fmt
make lint
make typecheck
make test
make quality
make clean
```

## Local execution model

- `raw/` = ingested canonical inputs
- `processed/` = cleaned and transformed intermediates
- `analysis/` = substantive computational outputs
- `results/` = exported tables and figures

## Python / R interoperability

Keep the dependency graph in Python assets.
Execute R with Dagster Pipes from `src/{{ cookiecutter.package_name }}/R/`.
Use explicit file-based exchange between languages.

## Default input assumption

The starter pipeline expects a CSV file at:

`data/raw/input.csv`

If you use a different input type or location, update `RawInputConfig` and the `raw` asset accordingly.
