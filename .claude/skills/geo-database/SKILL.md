---
id: geo-database
name: GEO Database
description: >
  Access NCBI GEO for public gene expression and genomics data. Search datasets,
  download series (GSE/GSM), retrieve expression matrices and raw supplementary files,
  and feed data directly into bulk RNA-seq or scRNA-seq analysis workflows.
  Primary use case: read a paper → extract GEO accession → download raw data →
  recapitulate the analysis.
  Trigger phrases: "download GEO data", "GEO accession", "GSE", "public RNA-seq dataset",
  "reproduce published analysis", "download expression data from paper",
  "series matrix", "GEOparse", "NCBI GEO".
category: databases
short-description: "Search and download GEO datasets (GSE/GSM) via GEOparse + E-utilities."
detailed-description: "GEOparse + Biopython E-utilities for programmatic GEO access. Supports dataset search by keyword/accession, metadata extraction, series matrix download, supplementary file retrieval (count matrices, h5 files). Key workflow: paper → GEO accession → download → feed to bulk-rnaseq-counts-to-de-deseq2 or scrnaseq-scanpy-core-analysis."
---

# GEO Database

Search and download public transcriptomics data from NCBI GEO (264,000+ studies, 8M+ samples).

## When to Use This Skill

- Extracting a GEO accession number from a paper and downloading the data
- Searching for public datasets on a topic (macrophage polarization, lung transplantation, EVLP, etc.)
- Downloading raw count matrices or processed expression files for reanalysis
- Batch downloading multiple GSEs for meta-analysis
- Retrieving sample metadata to understand experimental design before analysis

## Installation

```bash
pip install GEOparse biopython pandas numpy
```

Set NCBI email (required):
```python
from Bio import Entrez
Entrez.email = "your.email@institution.org"
# Optional API key for 10 req/s (vs 3 req/s):
# Entrez.api_key = "your_api_key"
```

---

## Core Workflow: Paper → GEO → Analysis

### Step 1 — Extract accession from paper and inspect

```python
import GEOparse

# Download and parse a GEO Series (caches to destdir)
gse = GEOparse.get_GEO(geo="GSE123456", destdir="./data")

# Inspect study metadata
print(gse.metadata['title'][0])
print(gse.metadata['summary'][0])
print(gse.metadata['overall_design'][0])

# List samples and their characteristics
for gsm_name, gsm in gse.gsms.items():
    print(f"{gsm_name}: {gsm.metadata['title'][0]}")
    chars = gsm.metadata.get('characteristics_ch1', [])
    for c in chars:
        print(f"  {c}")

# List platforms
for gpl_name, gpl in gse.gpls.items():
    print(f"Platform: {gpl_name} — {gpl.metadata['title'][0]}")
    print(f"Organism: {gpl.metadata['organism'][0]}")
```

### Step 2a — Get expression matrix (microarray / processed bulk)

```python
# Fastest: series matrix file (genes × samples)
expression_df = gse.pivot_samples('VALUE')
print(f"Matrix shape: {expression_df.shape}")  # probes × samples

# IMPORTANT: Check if values are log-transformed
print(f"Value range: {expression_df.min().min():.1f} – {expression_df.max().max():.1f}")
# If max >> 100: likely raw signal, needs log2 transform
# If max ~15-20: likely already log2-transformed
```

**Warning:** Never run DESeq2 on normalized/log-transformed microarray values — use limma-voom instead. For proper bulk RNA-seq DE, always prefer raw count matrices (Step 2b).

### Step 2b — Download supplementary files (raw counts, h5, h5ad)

```python
# List available supplementary files first
for gsm_name, gsm in gse.gsms.items():
    suppl = gsm.metadata.get('supplementary_file', [])
    for f in suppl:
        print(f"{gsm_name}: {f}")

# Download all supplementary files for the series
gse.download_supplementary_files(
    directory="./data/GSE123456_suppl",
    download_sra=False  # True only if you need raw FASTQ via SRA
)
```

For scRNA-seq datasets, supplementary files are typically:
- `*_filtered_feature_bc_matrix.h5` — 10x Chromium output (use with Scanpy)
- `*_raw_counts.csv.gz` or `*_counts.txt.gz` — raw count matrices
- `*.h5ad` — pre-processed AnnData objects

**After download, route to the correct analysis skill:**
- Raw counts (bulk) → `bulk-rnaseq-counts-to-de-deseq2`
- 10x h5 / count matrix (scRNA-seq) → `scrnaseq-scanpy-core-analysis`
- Processed microarray → limma-voom (not DESeq2)

### Step 3 — Search GEO for datasets on a topic

```python
from Bio import Entrez
import time

Entrez.email = "your.email@institution.org"

def search_geo(query, retmax=20):
    """Search GEO DataSets."""
    handle = Entrez.esearch(db="gds", term=query, retmax=retmax, usehistory="y")
    results = Entrez.read(handle)
    handle.close()
    return results

def fetch_geo_summaries(id_list):
    """Fetch dataset summaries."""
    ids = ",".join(id_list)
    handle = Entrez.esummary(db="gds", id=ids)
    summaries = Entrez.read(handle)
    handle.close()
    return summaries

# Example searches
results = search_geo("macrophage polarization[All Fields] AND Homo sapiens[Organism] AND RNA-seq[DataSet Type]")
print(f"Found {results['Count']} datasets")

# Get summaries for top results
summaries = fetch_geo_summaries(results['IdList'][:10])
for s in summaries:
    print(f"GSE{s.get('GSE', 'N/A')}: {s.get('title', 'N/A')} — {s.get('n_samples', '?')} samples")
    time.sleep(0.34)  # Respect NCBI rate limits
```

**Useful search field tags:**
- `[All Fields]` — keyword anywhere
- `[Organism]` — e.g. `Homo sapiens[Organism]`
- `[DataSet Type]` — `RNA-seq[DataSet Type]` or `expression profiling by array[DataSet Type]`
- `[Publication Date]` — e.g. `2022:2025[Publication Date]`
- `[Author]` — e.g. `Loupy[Author]`

### Step 4 — Batch download multiple datasets

```python
import GEOparse

def batch_download_geo(gse_list, destdir="./data/geo"):
    """Download and summarize multiple GEO series."""
    import os
    os.makedirs(destdir, exist_ok=True)
    summaries = {}

    for gse_id in gse_list:
        try:
            gse = GEOparse.get_GEO(geo=gse_id, destdir=destdir)
            summaries[gse_id] = {
                'title': gse.metadata.get('title', ['N/A'])[0],
                'organism': gse.metadata.get('organism', ['N/A'])[0],
                'n_samples': len(gse.gsms),
                'platform': list(gse.gpls.keys())[0] if gse.gpls else 'N/A',
            }
            print(f"✓ {gse_id}: {summaries[gse_id]['title']} ({summaries[gse_id]['n_samples']} samples)")
        except Exception as e:
            print(f"✗ {gse_id}: {e}")
            summaries[gse_id] = {'error': str(e)}

    return summaries

# Example
gse_list = ["GSE100001", "GSE100002", "GSE100003"]
summaries = batch_download_geo(gse_list)
```

---

## Key Concepts

| Term | Meaning |
|------|---------|
| GSE | Series — a complete experiment |
| GSM | Sample — a single biological replicate |
| GPL | Platform — the array or sequencing platform |
| Series matrix | Tab-delimited expression matrix (fastest to download) |
| SOFT | Text format with metadata + data |
| Supplementary files | Raw counts, h5 files, etc. |

## Common Pitfalls

| Pitfall | Fix |
|---------|-----|
| Applying DESeq2 to normalized microarray values | Check value range; use limma-voom for arrays |
| Running DE on processed/log-transformed counts | Always prefer raw supplementary count matrices |
| Probe IDs instead of gene symbols | Map via platform annotation (`gpl.table`) |
| Batch effects across studies | Always check sample metadata; apply Harmony/ComBat |
| Duplicate samples in meta-analysis | Verify GSM IDs are unique across GSEs |
| NCBI rate limit errors | Add `time.sleep(0.34)` between E-utility calls |

## Data Quality Rules (mandatory)

- **Always inspect metadata** before downloading expression data — check organism, platform, sample labels
- **Always check value range** of expression matrix — determine if log-transformed or raw
- **Never apply DESeq2 to non-count data** — verify data type before routing to DE workflow
- **Always log sample count and dataset title** when downloading for traceability
- **Always invoke The Reviewer** after data loading to verify integrity

## References

- [geo_reference.md](references/geo_reference.md) — E-utilities API specs, SOFT format, FTP structure
- GEOparse docs: https://geoparse.readthedocs.io/
- NCBI GEO: https://www.ncbi.nlm.nih.gov/geo/
- E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25501/
