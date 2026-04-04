# Literature Tools Bug Report

## Summary
Found **2 critical bugs** in the literature tools extension that are causing crashes.

## Bug #1: `fetch_fulltext` crashes with RegExp error

### Location
`pi-extensions/literature-tools.ts` lines 66-68

### Problem
The first three patterns in `PDF_PATTERNS` array are missing the `g` (global) flag, which is required when using `String.prototype.matchAll()`.

### Current code:
```javascript
const PDF_PATTERNS = [
	/<meta[^>]+name=["']citation_pdf_url["'][^>]+content=["']([^"']+)["']/i,  // ❌ Missing 'g' flag
	/<meta[^>]+property=["']og:pdf["'][^>]+content=["']([^"']+)["']/i,        // ❌ Missing 'g' flag
	/<meta[^>]+name=["']dc\.identifier["'][^>]+content=["']([^"']*\.pdf[^"']*)["']/i,  // ❌ Missing 'g' flag
	/<(?:iframe|embed|object)[^>]+(?:src|data)=["']([^"']+)["']/gi,           // ✓ Has 'g' flag
	...
];
```

### Error message:
```
TypeError: String.prototype.matchAll called with a non-global RegExp argument
    at String.matchAll (<anonymous>)
    at extractPdfCandidates (file:///Users/fbraza/Documents/research-skills/pi-extensions/literature-tools.ts:251:28)
```

### Fix:
Add the `g` flag to the first three patterns:
```javascript
const PDF_PATTERNS = [
	/<meta[^>]+name=["']citation_pdf_url["'][^>]+content=["']([^"']+)["']/gi,  // ✓ Fixed
	/<meta[^>]+property=["']og:pdf["'][^>]+content=["']([^"']+)["']/gi,        // ✓ Fixed
	/<meta[^>]+name=["']dc\.identifier["'][^>]+content=["']([^"']*\.pdf[^"']*)["']/gi,  // ✓ Fixed
	/<(?:iframe|embed|object)[^>]+(?:src|data)=["']([^"']+)["']/gi,
	...
];
```

## Bug #2: `semantic_scholar_search` rate limiting

### Problem
Getting HTTP 429 (Too Many Requests) from Semantic Scholar API.

### Error message:
```
Error: 429  for https://api.semanticscholar.org/graph/v1/paper/search?query=cancer&limit=1&...
```

### Root cause:
The code already supports Semantic Scholar API keys via the `SEMANTIC_SCHOLAR_API_KEY` environment variable (line 606), but:
1. Without an API key, rate limits are very strict (100 requests per 5 minutes)
2. No retry logic or exponential backoff
3. No user-friendly error message explaining the rate limit

### Fix needed:
- Add retry logic with exponential backoff for 429 errors
- Provide better error message suggesting to set `SEMANTIC_SCHOLAR_API_KEY`
- Add rate limiting between requests
- Document the environment variable in the tool description

### Current implementation (line 606):
```javascript
const response = await fetchJson<{ data?: any[] }>(
  url.toString(), 
  signal, 
  process.env.SEMANTIC_SCHOLAR_API_KEY ? { "x-api-key": process.env.SEMANTIC_SCHOLAR_API_KEY } : undefined
);
```

## Test Results

### ✅ Working:
- `pubmed_search` - Successfully retrieves papers
- `preprint_search` - Successfully retrieves preprints
- `fetch_fulltext` - ✅ **FIXED** (Bug #1 resolved by adding 'g' flag)

### ⚠️ Needs improvement:
- `semantic_scholar_search` - Rate limited without API key (Bug #2) - Works with `SEMANTIC_SCHOLAR_API_KEY` env var

## How to reproduce

Run the test script:
```bash
npm install @sinclair/typebox
node test-tool-invocation-v2.mjs
```

To fix Semantic Scholar rate limiting:
```bash
export SEMANTIC_SCHOLAR_API_KEY="your-api-key-here"
node test-tool-invocation-v2.mjs
```

Get a free Semantic Scholar API key at: https://www.semanticscholar.org/product/api

## Impact

These bugs prevent users from:
1. Fetching full-text PDFs of papers (critical functionality)
2. Searching Semantic Scholar (important literature source)

## Recommendations

1. **✅ DONE**: Add `g` flag to PDF_PATTERNS (Bug #1) - Fixed in commit
2. **Short-term**: Add better error handling for Semantic Scholar rate limits (Bug #2)
   - Provide user-friendly error message
   - Add retry logic with exponential backoff
   - Document `SEMANTIC_SCHOLAR_API_KEY` in tool description
3. **Long-term**: Implement proper rate limiting and retry logic for all external APIs

## Fixes applied

- ✅ Added `g` flag to first three PDF_PATTERNS (lines 66-68)
- ✅ `fetch_fulltext` now works correctly
