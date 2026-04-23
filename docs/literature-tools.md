# literature-tools

## Summary

`literature-tools` adds typed literature-retrieval tools for PubMed, preprints, Semantic Scholar, and PDF/full-text access.

## What it adds

- Tools:
  - `pubmed_search`
  - `preprint_search`
  - `semantic_scholar_search`
  - `fetch_fulltext`

## How it works

- `pubmed_search` uses NCBI E-utilities (`esearch` + `efetch`) and parses PubMed XML metadata
- `semantic_scholar_search` queries the Semantic Scholar Graph API
- `fetch_fulltext` follows a retrieval chain:
  1. PMC
  2. publisher OA landing pages
  3. bioRxiv / medRxiv PDF discovery via Semantic Scholar OA metadata
  4. Sci-Hub fallback

It also includes publisher-specific heuristics for common OA/PDF URL patterns.

## Usage

Use these tools when a skill or an agent needs typed, structured literature retrieval instead of generic web search.

## Examples

- `pubmed_search({ query: "TEAD inhibition mesothelioma", max_results: 10 })`
- `preprint_search({ query: "KRAS G12D pancreatic cancer", server: "biorxiv" })`
- `semantic_scholar_search({ query: "BRAF resistance melanoma", open_access_only: true })`
- `fetch_fulltext({ doi: "10.1038/s41586-023-12345-6", output_dir: "./results/pdfs" })`

## Files and state

- No persistent local state by default
- Optionally downloads PDFs to `output_dir`
- Uses environment variables when available for higher API limits

## Notes / caveats

- PubMed and Semantic Scholar rate limits still apply
- Publisher landing page parsing is heuristic and may require future host-specific refinements
- Sci-Hub is a last-resort fallback and should be treated as such
such
ub is a last-resort fallback and should be treated as such
