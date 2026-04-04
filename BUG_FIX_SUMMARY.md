# Literature Tools Debug Summary

## Issues Found and Fixed

### ✅ Bug #1: `fetch_fulltext` Crash - FIXED
**Problem**: The tool was crashing with:
```
TypeError: String.prototype.matchAll called with a non-global RegExp argument
```

**Root cause**: First three regex patterns in `PDF_PATTERNS` array were missing the `g` (global) flag required by `matchAll()`.

**Fix applied**: Added `g` flag to patterns at lines 66-68 in `pi-extensions/literature-tools.ts`

**Status**: ✅ **FIXED** - Tool now successfully retrieves PDFs

### ⚠️ Bug #2: `semantic_scholar_search` Rate Limiting
**Problem**: Getting HTTP 429 errors when searching without API key

**Root cause**: 
- Semantic Scholar has strict rate limits (100 requests/5 min) without API key
- The code already supports `SEMANTIC_SCHOLAR_API_KEY` environment variable
- No retry logic or user-friendly error messages

**Status**: ⚠️ **Needs improvement** - Works with API key, but needs better error handling

**Workaround**: Set environment variable:
```bash
export SEMANTIC_SCHOLAR_API_KEY="your-api-key-here"
```
Get free API key: https://www.semanticscholar.org/product/api

## Test Results

### ✅ Working (3/4):
- `pubmed_search` - Successfully retrieves papers from PubMed
- `preprint_search` - Successfully retrieves preprints from bioRxiv/medRxiv
- `fetch_fulltext` - ✅ **FIXED** - Successfully retrieves PDFs

### ⚠️ Rate Limited (1/4):
- `semantic_scholar_search` - Requires API key for reliable use

## Files Modified
- `pi-extensions/literature-tools.ts` - Fixed PDF_PATTERNS regex flags

## Dependencies Installed
- `@sinclair/typebox` - Required for schema validation

## How to Test

1. Install dependencies:
```bash
npm install @sinclair/typebox
```

2. Run test script:
```bash
node test-tool-invocation-v2.mjs
```

3. (Optional) Set Semantic Scholar API key for full testing:
```bash
export SEMANTIC_SCHOLAR_API_KEY="your-key"
node test-tool-invocation-v2.mjs
```

## Next Steps

1. **Immediate**: Bug #1 is fixed, tools are usable
2. **Short-term**: Add better error messages for Semantic Scholar rate limits
3. **Long-term**: Implement retry logic and rate limiting for all APIs

## Detailed Bug Report
See `LITERATURE_TOOLS_BUG_REPORT.md` for complete technical details.
