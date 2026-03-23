---
id: biorxiv-database
name: bioRxiv Preprint Database
description: >
  Use this skill when searching for life sciences preprints on bioRxiv by keywords,
  authors, date ranges, or subject categories. Trigger phrases: "recent preprints",
  "bioRxiv search", "preprint on [topic]", "latest papers on [topic]", "track author
  preprints", "has this been published on bioRxiv". Primary tool for The Librarian when
  preprint coverage is needed. Covers immunology, genomics, cell biology, bioinformatics,
  and all major life sciences categories. Always flag results as preprints (not peer-reviewed).
category: literature
short-description: "Search bioRxiv for life sciences preprints by keyword, author, date, or category."
detailed-description: "Python-based client for the bioRxiv API. Searches preprints by keywords (title/abstract), author name, DOI lookup, or date range. Returns structured JSON with title, abstract, authors, DOI, category, and PDF URL. Supports all bioRxiv subject categories including immunology, genomics, cell-biology, bioinformatics, and systems-biology. Use when PubMed coverage is insufficient for very recent findings or when tracking cutting-edge methods not yet peer-reviewed."
---

# bioRxiv Preprint Database

Search and retrieve life sciences preprints from bioRxiv via its public API.
Always used by The Librarian — never presented as peer-reviewed evidence.

## When to Use This Skill

- Searching for **very recent findings** (last 6-24 months) not yet in PubMed
- Tracking **emerging methods** (new scRNA-seq tools, statistical methods, computational workflows)
- Monitoring **specific authors** for recent work
- Conducting **systematic preprint reviews** alongside PubMed searches
- Retrieving a specific preprint by DOI

**Do NOT use for:** Verified, peer-reviewed evidence claims. Always pair with PubMed.
**Always flag:** Results from this skill are preprints — not peer-reviewed.

## Installation

```bash
pip install requests
```

No API key required.

## Core Usage

### Keyword search

```bash
python scripts/biorxiv_search.py \
  --keywords "macrophage polarization" "lung transplantation" \
  --start-date 2024-01-01 \
  --end-date 2025-03-01 \
  --category immunology \
  --output results.json
```

### Author search

```bash
python scripts/biorxiv_search.py \
  --author "Loupy" \
  --days-back 365 \
  --output loupy_preprints.json
```

### DOI lookup

```bash
python scripts/biorxiv_search.py \
  --doi "10.1101/2024.01.15.123456" \
  --output paper.json
```

### Recent papers in a category

```bash
python scripts/biorxiv_search.py \
  --category immunology \
  --days-back 30 \
  --output recent_immunology.json
```

## Python API

```python
from scripts.biorxiv_search import BioRxivSearcher

searcher = BioRxivSearcher(verbose=True)

# Keyword search
results = searcher.search_by_keywords(
    keywords=["EVLP", "macrophage"],
    start_date="2023-01-01",
    end_date="2025-03-01",
    category="immunology"
)

# Format results
for paper in results[:5]:
    formatted = searcher.format_result(paper, include_abstract=True)
    print(formatted)
```

## Subject Categories Relevant to Your Work

| Category | Use for |
|----------|---------|
| `immunology` | Macrophage biology, transplant immunology, innate immunity |
| `cell-biology` | Cell signaling, organelles, cell death |
| `genomics` | Single-cell genomics, bulk RNA-seq methods |
| `bioinformatics` | New computational tools and pipelines |
| `systems-biology` | Network analysis, multi-omics |
| `pathology` | Disease mechanisms, histopathology |
| `physiology` | Organ function, EVLP physiology |
| `molecular-biology` | Gene regulation, epigenetics |

## Output Format

```json
{
  "doi": "10.1101/2024.01.15.123456",
  "title": "...",
  "authors": "Smith J, Doe J",
  "date": "2024-01-15",
  "category": "immunology",
  "abstract": "...",
  "pdf_url": "https://www.biorxiv.org/content/.../full.pdf",
  "html_url": "https://www.biorxiv.org/content/..."
}
```

## Integration with The Librarian

The Librarian uses this skill when:
1. A user asks about very recent findings in an area
2. PubMed returns insufficient recent results
3. Conducting a systematic review that should include preprints
4. Checking if a result has been published as a preprint before peer review

**Always cross-reference** preprint findings with PubMed. Preprint results must be
labeled `[PREPRINT — not peer-reviewed]` in any output.

## Best Practices

- Use `--category` filter to reduce noise — always apply when domain is clear
- Combine with PubMed searches — bioRxiv covers recent, PubMed covers validated
- Cache results to JSON to avoid repeated API calls
- Rate limit: script auto-applies 0.5s delays between requests
- Max ~300 results per query; use date ranges to paginate for larger sets

## References

- API reference: [references/api_reference.md](references/api_reference.md)
- bioRxiv API: https://api.biorxiv.org/
