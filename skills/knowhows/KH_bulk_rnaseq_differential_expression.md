# Best practices for RNA-seq Differential Expression Analysis

**Knowhow ID:** KH_bulk_rnaseq_differential_expression
**Category:** Transcriptomics
**Version:** 1.0
**Last Updated:** January 2025
**Description:** Best practices on differential expression analysis for bulk RNA-seq data.
**Keywords:** RNA-seq, differential expression, DESeq2, padj, FDR, fold change

---

### Critical: Use Adjusted P-values for DEG Filtering

**ALWAYS use adjusted p-values (padj/FDR) for filtering significant genes, NEVER raw p-values.**

In RNA-seq analysis, thousands of genes are tested simultaneously. Raw p-values must be adjusted (e.g., using Benjamini-Hochberg FDR) to control false discovery rate.

**Standard DEG filtering (Python):**
```python
# CORRECT - Use adjusted p-values
significant_degs = results[
    (results['padj'] <= 0.05) &                    # Adjusted p-value
    (abs(results['log2FoldChange']) >= 0.5)     # Fold change (inclusive)
]
```

**For R DESeq2:**
```r
# CORRECT - Use padj column
sig_genes <- subset(res, padj <= 0.05 & abs(log2FoldChange) >= 0.5)
```

---

### Terminology

- "Statistically significant DEGs" = genes passing **adjusted p-value** threshold
- "p < 0.05" in DEG context typically means **padj < 0.05** unless explicitly stated as "raw p-value"
- Use inclusive inequalities (`>=`, `<=`) unless the question explicitly uses strict inequalities (`>`, `<`)
