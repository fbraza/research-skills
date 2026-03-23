---
id: cellxgene-census
name: CZ CELLxGENE Census
description: >
  Query the CZ CELLxGENE Census (61M+ cells) programmatically to retrieve single-cell
  expression data by cell type, tissue, or disease. Use when you need reference atlas
  data, cross-tissue macrophage comparisons, or population-scale queries. Best paired
  with the scrnaseq-scanpy-core-analysis skill for downstream analysis.
  Trigger phrases: "CELLxGENE", "cell atlas query", "reference atlas single-cell",
  "macrophage expression across tissues", "lung single-cell reference",
  "query Census", "cross-tissue single-cell comparison".
category: single-cell
short-description: "Query 61M+ cells from the CZ CELLxGENE Census by cell type, tissue, or disease."
detailed-description: "Python API (cellxgene-census package) for programmatic access to the CZ CELLxGENE Census — the largest curated single-cell atlas. Supports metadata exploration, small-to-medium AnnData queries, out-of-core large-scale processing, and Scanpy integration. Key use cases: reference atlas comparisons, cross-tissue macrophage biology, lung cell type inventories, and training ML models on single-cell data."
---

# CZ CELLxGENE Census

Access 61M+ curated single-cell RNA-seq cells from CZ CELLxGENE Discover.
Use for reference atlas queries and cross-tissue comparisons — not for analyzing your own data
(use scrnaseq-scanpy-core-analysis for that).

## When to Use This Skill

- Query macrophage or other immune cell expression across tissues (lung, liver, blood, etc.)
- Build a reference context for your own scRNA-seq data
- Identify available public datasets for a disease or tissue of interest
- Compare marker gene expression across cell types at atlas scale
- Cross-tissue analysis of a gene of interest

**Do NOT use for:** Analyzing your own data — use `scrnaseq-scanpy-core-analysis` instead.

## Installation

```bash
pip install cellxgene-census
```

## Core Patterns

### Open Census (always use context manager)

```python
import cellxgene_census

# Always specify version for reproducibility
with cellxgene_census.open_soma(census_version="2023-07-25") as census:
    # work here

# Latest stable (less reproducible)
with cellxgene_census.open_soma() as census:
    # work here
```

### Step 1 — Explore before querying (always do this first)

```python
with cellxgene_census.open_soma() as census:
    # Count cells matching your filter before loading expression data
    metadata = cellxgene_census.get_obs(
        census, "homo_sapiens",
        value_filter="tissue_general == 'lung' and is_primary_data == True",
        column_names=["cell_type", "disease", "donor_id"]
    )
    print(f"Found {len(metadata):,} cells")
    print(metadata["cell_type"].value_counts().head(20))
```

**Rule:** Always include `is_primary_data == True` to avoid duplicate cells.

### Step 2 — Query expression data (< 100k cells)

```python
with cellxgene_census.open_soma() as census:
    adata = cellxgene_census.get_anndata(
        census=census,
        organism="Homo sapiens",
        obs_value_filter=(
            "cell_type == 'macrophage' and "
            "tissue_general == 'lung' and "
            "is_primary_data == True"
        ),
        var_value_filter="feature_name in ['CD68', 'MRC1', 'CCL2', 'SPP1', 'TREM2']",
        obs_column_names=["cell_type", "tissue_general", "disease", "donor_id"],
    )
```

### Step 3 — Large queries (> 100k cells, out-of-core)

```python
import tiledbsoma as soma

with cellxgene_census.open_soma() as census:
    query = census["census_data"]["homo_sapiens"].axis_query(
        measurement_name="RNA",
        obs_query=soma.AxisQuery(
            value_filter="cell_type == 'macrophage' and is_primary_data == True"
        ),
        var_query=soma.AxisQuery(
            value_filter="feature_name in ['CD68', 'MRC1', 'CCL2']"
        )
    )

    # Iterate in chunks — never loads all data at once
    sum_values = 0.0
    n_obs = 0
    for batch in query.X("raw").tables():
        values = batch["soma_data"].to_numpy()
        sum_values += values.sum()
        n_obs += len(values)
```

### Integration with Scanpy

```python
import scanpy as sc

with cellxgene_census.open_soma() as census:
    adata = cellxgene_census.get_anndata(
        census=census,
        organism="Homo sapiens",
        obs_value_filter=(
            "cell_type == 'macrophage' and "
            "tissue_general in ['lung', 'liver'] and "
            "is_primary_data == True"
        ),
    )

# Standard Scanpy preprocessing
sc.pp.normalize_total(adata, target_sum=1e4)
sc.pp.log1p(adata)
sc.pp.highly_variable_genes(adata, n_top_genes=2000)
sc.pp.pca(adata)
sc.pp.neighbors(adata)
sc.tl.umap(adata)
sc.pl.umap(adata, color=["cell_type", "tissue_general", "disease"])
```

## Key Metadata Fields for Filtering

| Field | Examples |
|-------|----------|
| `cell_type` | `'macrophage'`, `'T cell'`, `'B cell'` |
| `tissue_general` | `'lung'`, `'liver'`, `'immune system'` |
| `tissue` | `'peripheral blood mononuclear cell'` |
| `disease` | `'COVID-19'`, `'normal'` |
| `donor_id` | unique donor identifier |
| `assay` | `"10x 3' v3"`, `'Smart-seq2'` |
| `is_primary_data` | `True` (always filter for this) |

## Best Practices

1. Always `is_primary_data == True` — avoids duplicate cell counting
2. Explore metadata before loading expression — check cell counts first
3. Pin `census_version` for reproducibility
4. Use `var_value_filter` to restrict to genes of interest — reduces transfer time
5. > 100k cells → use `axis_query()` out-of-core pattern
6. Prefer `tissue_general` for cross-tissue analysis, `tissue` for specific tissues

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Duplicate cells | Add `is_primary_data == True` |
| Memory error on large query | Use `axis_query()` iterator |
| Gene not found | Check spelling (case-sensitive); try Ensembl ID |
| Version inconsistency | Pin `census_version` explicitly |

## References

- [census_schema.md](references/census_schema.md) — Full metadata field catalog and filter syntax
- [common_patterns.md](references/common_patterns.md) — Extended code patterns for all query types
- CZ CELLxGENE Census: https://chanzuckerberg.github.io/cellxgene-census/
