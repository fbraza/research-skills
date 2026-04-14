.PHONY: help sync hooks fmt lint typecheck test check-defs dev quality clean

help:
	@echo "Available targets:"
	@echo "  make sync        - install/update dependencies with uv"
	@echo "  make hooks       - install pre-commit hooks"
	@echo "  make fmt         - format code with ruff"
	@echo "  make lint        - lint code with ruff"
	@echo "  make typecheck   - run mypy"
	@echo "  make test        - run pytest"
	@echo "  make check-defs  - validate Dagster definitions"
	@echo "  make quality     - run lint + typecheck + test + check-defs"
	@echo "  make clean       - remove caches, Dagster state, and derived outputs"
	@echo "  make dev         - start the local Dagster UI"

sync:
	uv sync --group dev

hooks:
	uv run pre-commit install

fmt:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check .

typecheck:
	uv run mypy src tests

test:
	uv run pytest

check-defs:
	uv run dg check defs

quality: lint typecheck test check-defs

clean:
	find . -type d \( -name '__pycache__' -o -name '.pytest_cache' -o -name '.mypy_cache' -o -name '.ruff_cache' -o -name '.dagster' \) -prune -exec rm -rf {} +
	find . -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
	find data/processed -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +
	find data/analysis -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +
	find data/results/figures -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +
	find data/results/tables -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +

dev:
	uv run dg dev
