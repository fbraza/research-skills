# Cookiecutter: Dagster Bio Pipeline

Cookiecutter template for the canonical local-first Dagster project structure used in this repository.

## Purpose

Use this template to scaffold computational biology projects that need:
- explicit raw / processed / analysis / results layers
- local Dagster UI via `dg dev`
- checkpointed intermediates
- Python and optional R interoperability
- separation between domain logic and orchestration

## Generate a project

From the repository root:

```bash
uvx cookiecutter templates/cookiecutter-dagster-bio-pipeline
```

Or with an installed cookiecutter:

```bash
cookiecutter templates/cookiecutter-dagster-bio-pipeline
```

## After generation

1. `cd <project>`
2. `make sync`
3. `make hooks`
4. Place immutable inputs in `data/raw/`
5. Adapt the placeholder assets and `lib/` functions to your target skill
6. Run `make check-defs`
7. Run `make dev`

## Notes

- The generated project contains a **generic starter pipeline**, not a domain-specific workflow.
- Replace the placeholder assets with logic adapted from the target skill.
- For mixed Python/R pipelines, keep the dependency graph in Python and execute R through Dagster Pipes.
- The template is the executable source of truth for on-disk structure; the know-how and skill explain how to use it.
