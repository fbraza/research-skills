# bioRxiv / medRxiv — Routine Quick-Reference

Quick-start for routine preprint searches. For all endpoints, full response schema, version tracking, or custom pagination → load `biorxiv_api_reference.md`.

## Content API (Search by Date Range)

```
https://api.biorxiv.org/details/{server}/{interval}/{cursor}
```

| Parameter | Value |
|---|---|
| `server` | `"biorxiv"` or `"medrxiv"` |
| `interval` | `YYYY-MM-DD/YYYY-MM-DD` (start/end) |
| `cursor` | Integer offset: `0`, `30`, `60`, … |

**Example:**
```
https://api.biorxiv.org/details/biorxiv/2024-01-01/2024-06-30/0
```

Returns JSON with: `doi`, `title`, `authors`, `abstract`, `date`, `category`, `jatsxml URL`, `version`, `license`, `published`.

## DOI Lookup

```
https://api.biorxiv.org/details/biorxiv/{doi}
```

**Example:**
```
https://api.biorxiv.org/details/biorxiv/10.1101/2024.01.15.123456
```

## Recent Publications (Last N Days)

```
https://api.biorxiv.org/pubs/biorxiv/{days_back}/{cursor}/json
```

**Example:** last 7 days:
```
https://api.biorxiv.org/pubs/biorxiv/7/0/json
```

Returns up to 100 results/page. Increment cursor by 100 for next page.

## Pagination

- `/details/` returns 30 results/page — increment cursor by 30
- `/pubs/` returns up to 100 results/page — increment cursor by 100
- Stop when `messages[0].count` < page size

## PDF Download URL

```
https://www.biorxiv.org/content/{doi}v{version}.full.pdf
```

**Example:**
```
https://www.biorxiv.org/content/10.1101/2024.01.15.123456v1.full.pdf
```

## Subject Categories (bioRxiv)

`animal-behavior-and-cognition`, `bioinformatics`, `biochemistry`, `bioengineering`, `biophysics`, `cancer-biology`, `cell-biology`, `clinical-trials`, `developmental-biology`, `ecology`, `epidemiology`, `evolutionary-biology`, `genetics`, `genomics`, `immunology`, `microbiology`, `molecular-biology`, `neuroscience`, `paleontology`, `pathology`, `pharmacology-and-toxicology`, `physiology`, `plant-biology`, `scientific-communication-and-education`, `synthetic-biology`, `systems-biology`, `zoology`

## Rate Limits

Add ≥ 0.5s delay between requests. Always label results as: `[PREPRINT — not peer-reviewed]`.
