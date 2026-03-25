# Preclinical Search Guide

**Workflow:** literature-preclinical  
**Purpose:** Consensus API search strategies, query construction, and API parameters for retrieving preclinical studies.

---

## Overview

The `search_preclinical()` function queries the **Consensus API** (consensus.app) to retrieve peer-reviewed preclinical studies. Consensus uses semantic search over a curated corpus of scientific papers, making it more effective than keyword-only searches for biomedical literature.

---

## API Access

### Authentication
```bash
export CONSENSUS_API_KEY="your_key_here"
```
- Get a key at: https://consensus.app/home/api/
- The key must be set as an environment variable before running any search script
- Rate limit: varies by plan (script handles retries with exponential backoff)

### Base URL
```
https://consensus.app/api/papers/search/
```

### Key Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `query` | string | Natural language search query | required |
| `filters.year_min` | int | Earliest publication year | current_year - years |
| `filters.year_max` | int | Latest publication year | current_year |
| `size` | int | Number of results to return (max: 50 per call) | 50 |
| `fields` | list | Fields to return (title, abstract, authors, doi, year, journal) | all |

---

## Query Construction

### Best Practices

**1. Use natural language, not boolean syntax**
Consensus uses semantic search — natural language queries outperform keyword strings.

```python
# GOOD — natural language
query = "CDK4/6 inhibition in triple-negative breast cancer preclinical studies"

# LESS EFFECTIVE — keyword string
query = "CDK4/6 AND breast cancer AND in vitro"
```

**2. Include the target name + disease + study type**
```python
query = f"{target} in {disease} preclinical studies"
# e.g., "BRAF inhibition in melanoma preclinical studies"
```

**3. Try alternative target names if results are sparse**
```python
alternative_queries = [
    f"{target} {disease}",
    f"{target} inhibitor {disease}",
    f"{target} knockdown {disease}",
    f"{target} knockout {disease} mouse model",
]
```

**4. Common target name variations to try**

| Target | Alternatives |
|--------|-------------|
| CDK4/6 | CDK4, CDK6, cyclin-dependent kinase 4 |
| PD-L1 | CD274, B7-H1, programmed death ligand 1 |
| KRAS | KRAS G12C, KRAS G12D, RAS |
| HER2 | ERBB2, neu, HER-2 |
| BRAF | BRAF V600E, B-Raf |

---

## Filtering for Preclinical Studies

The Consensus API does not have a dedicated "preclinical" filter. The `search_preclinical()` script applies post-retrieval filtering to exclude clinical studies:

### Exclusion keywords (applied to title + abstract)
```python
CLINICAL_EXCLUSION_TERMS = [
    "clinical trial", "phase I", "phase II", "phase III", "phase 1", "phase 2", "phase 3",
    "randomized controlled", "patients", "cohort study", "case report",
    "human subjects", "clinical study", "retrospective study"
]
```

### Inclusion signals (boost preclinical relevance)
```python
PRECLINICAL_INCLUSION_TERMS = [
    "cell line", "in vitro", "in vivo", "mouse model", "xenograft",
    "syngeneic", "PDX", "patient-derived", "knockout", "knockdown",
    "siRNA", "shRNA", "CRISPR", "transgenic", "murine"
]
```

---

## Pagination and Result Limits

- **API max per call:** 50 results
- **Recommended max:** 50 results (default) — sufficient for most targets
- **For comprehensive searches:** Run multiple queries with different phrasings and deduplicate by DOI/PMID

```python
# Deduplication by DOI
results_combined = pd.concat([results_query1, results_query2])
results_deduped = results_combined.drop_duplicates(subset=["doi"])
```

---

## Output Fields

Each retrieved paper includes:

| Field | Description |
|-------|-------------|
| `title` | Paper title |
| `abstract` | Full abstract text |
| `authors` | Author list |
| `year` | Publication year |
| `journal` | Journal name |
| `doi` | Digital Object Identifier |
| `pmid` | PubMed ID (when available) |
| `url` | Consensus paper URL |
| `relevance_score` | Semantic relevance score (0–1) |

---

## Troubleshooting Search Issues

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| 0 results | Query too specific | Broaden query, try alternative target names |
| All clinical papers | Disease term too broad | Add "preclinical", "in vitro", or "mouse model" to query |
| Irrelevant papers | Target name ambiguous | Use full gene name + disease context |
| Rate limit (429) | Too many requests | Script handles with exponential backoff; wait 60s and retry |
| Low relevance scores | Niche target | Try Consensus web UI to test query phrasing manually |

---

## Alternative: PubMed E-utilities

If Consensus API is unavailable, use PubMed E-utilities (free, no key required):

```python
import requests

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def search_pubmed(query, max_results=50, years=5):
    from datetime import datetime
    year_min = datetime.now().year - years
    
    # Step 1: Get PMIDs
    search_url = f"{BASE_URL}esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": f"{query} AND ({year_min}:{datetime.now().year}[pdat])",
        "retmax": max_results,
        "retmode": "json",
        "sort": "relevance"
    }
    pmids = requests.get(search_url, params=params).json()["esearchresult"]["idlist"]
    
    # Step 2: Fetch abstracts
    fetch_url = f"{BASE_URL}efetch.fcgi"
    fetch_params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "rettype": "abstract",
        "retmode": "xml"
    }
    return requests.get(fetch_url, params=fetch_params).text
```

**PubMed query syntax for preclinical studies:**
```
"CDK4/6"[Title/Abstract] AND "breast cancer"[Title/Abstract] 
AND ("in vitro"[Title/Abstract] OR "mouse model"[Title/Abstract] OR "xenograft"[Title/Abstract])
NOT "clinical trial"[Publication Type]
```

---

## References

- Consensus API documentation: https://consensus.app/home/api/
- PubMed E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25499/
- PubMed query syntax: https://pubmed.ncbi.nlm.nih.gov/help/
