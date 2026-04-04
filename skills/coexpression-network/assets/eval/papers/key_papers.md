# Key Papers — Weighted Gene Co-expression Network Analysis (WGCNA)

Annotated bibliography of essential publications for understanding, implementing,
and interpreting WGCNA analyses.

---

## Foundational Methods Papers

### 1. WGCNA Original Method
**Zhang B, Horvath S (2005).** A general framework for weighted gene co-expression network analysis.
*Statistical Applications in Genetics and Molecular Biology* 4(1): Article 17.
DOI: [10.2202/1544-6115.1128](https://doi.org/10.2202/1544-6115.1128)

**Why read it:** Introduces the core mathematical framework — soft thresholding, adjacency matrix,
topological overlap measure (TOM), and module detection. Essential for understanding *why* WGCNA
uses a power function rather than hard thresholding.

**Key concepts introduced:**
- Soft thresholding power β (scale-free topology criterion)
- Topological Overlap Matrix (TOM) as a robust similarity measure
- Module eigengene as a representative of module expression

---

### 2. WGCNA R Package
**Langfelder P, Horvath S (2008).** WGCNA: an R package for weighted correlation network analysis.
*BMC Bioinformatics* 9:559.
DOI: [10.1186/1471-2105-9-559](https://doi.org/10.1186/1471-2105-9-559)

**Why read it:** The primary citation for the WGCNA R package. Describes the complete workflow
from expression data to module-trait correlations. Use this as the primary reference when citing
WGCNA in publications.

**Key concepts introduced:**
- Complete R workflow implementation
- Module-trait correlation analysis
- Hub gene identification (kME = module membership)
- Female mouse liver dataset (the standard benchmark)

---

### 3. Dynamic Tree Cut
**Langfelder P, Zhang B, Horvath S (2008).** Defining clusters from a hierarchical cluster tree:
the Dynamic Tree Cut package for R.
*Bioinformatics* 24(5):719-720.
DOI: [10.1093/bioinformatics/btm563](https://doi.org/10.1093/bioinformatics/btm563)

**Why read it:** Describes the `dynamicTreeCut` algorithm used by WGCNA for module detection.
Explains why dynamic cutting outperforms fixed-height cutting for biological data.

---

### 4. Consensus WGCNA
**Langfelder P, Horvath S (2007).** Eigengene networks for studying the relationships between
co-expression modules.
*BMC Systems Biology* 1:54.
DOI: [10.1186/1752-0509-1-54](https://doi.org/10.1186/1752-0509-1-54)

**Why read it:** Introduces consensus WGCNA for comparing networks across multiple datasets or
conditions. Essential for multi-dataset analyses (e.g., comparing tumor vs normal, or multiple
tissues).

---

## Biological Applications

### 5. Brain Co-expression Networks
**Oldham MC, et al. (2008).** Functional organization of the transcriptome in human brain.
*Nature Neuroscience* 11:1271-1282.
DOI: [10.1038/nn.2207](https://doi.org/10.1038/nn.2207)

**Why read it:** Landmark application of WGCNA to human brain transcriptomics. Identified
neuron-specific and oligodendrocyte-specific modules. Demonstrates how to interpret modules
biologically using cell-type marker enrichment.

---

### 6. Cancer Co-expression Networks
**Ciriello G, et al. (2013).** Emerging landscape of oncogenic signatures across human cancers.
*Nature Genetics* 45:1127-1133.
DOI: [10.1038/ng.2762](https://doi.org/10.1038/ng.2762)

**Why read it:** Large-scale application across TCGA cancer types. Shows how co-expression
modules relate to cancer subtypes, driver mutations, and clinical outcomes.

---

### 7. Immune Cell Co-expression
**Chaussabel D, et al. (2008).** A modular analysis framework for blood genomics studies:
application to systemic lupus erythematosus.
*Immunity* 29(1):150-164.
DOI: [10.1016/j.immuni.2008.05.012](https://doi.org/10.1016/j.immuni.2008.05.012)

**Why read it:** Demonstrates blood transcriptomics module analysis for immune diseases.
Introduces the concept of "modular transcriptional repertoire" — relevant for any immune
co-expression analysis.

---

## Statistical & Methodological Advances

### 8. Soft Thresholding Power Selection
**Horvath S (2011).** *Weighted Network Analysis: Applications in Genomics and Systems Biology.*
Springer. ISBN: 978-1-4419-8818-8.

**Why read it:** The definitive textbook on WGCNA. Chapter 4 covers soft thresholding power
selection in depth. Chapter 12 covers module preservation statistics.

---

### 9. Module Preservation Statistics
**Langfelder P, Luo R, Oldham MC, Horvath S (2011).** Is my network module preserved and
reproducible?
*PLoS Computational Biology* 7(1):e1001057.
DOI: [10.1371/journal.pcbi.1001057](https://doi.org/10.1371/journal.pcbi.1001057)

**Why read it:** Introduces `modulePreservation()` — essential for validating that modules
found in a discovery dataset replicate in an independent validation dataset. Use Zsummary > 10
as the threshold for strong preservation.

**Key statistics:**
- Zsummary > 10: strongly preserved
- Zsummary 2–10: moderately preserved
- Zsummary < 2: not preserved

---

### 10. WGCNA vs Other Network Methods
**Kumari S, et al. (2012).** Evaluation of gene association methods for coexpression network
construction and biological knowledge discovery.
*PLoS ONE* 7(11):e50411.
DOI: [10.1371/journal.pone.0050411](https://doi.org/10.1371/journal.pone.0050411)

**Why read it:** Benchmarks WGCNA against mutual information (ARACNE, CLR) and other methods.
Shows WGCNA performs well for identifying biologically meaningful modules, especially with
moderate sample sizes.

---

## Practical Guides

### 11. WGCNA Tutorial (Official)
**Langfelder P, Horvath S.** WGCNA package tutorials.
https://horvath.genetics.ucla.edu/html/CoexpressionNetwork/Rpackages/WGCNA/Tutorials/

**Why read it:** Step-by-step R tutorials from the package authors. Covers:
- Tutorial I: Network construction and module detection
- Tutorial II: Relating modules to external information
- Tutorial III: Interfacing with other data

---

### 12. Common Pitfalls
**Parsana P, et al. (2019).** Addressing confounding artifacts in reconstruction of gene
co-expression networks.
*Genome Biology* 20:94.
DOI: [10.1186/s13059-019-1700-9](https://doi.org/10.1186/s13059-019-1700-9)

**Why read it:** Identifies how technical artifacts (batch effects, cell composition) can
create spurious co-expression modules. Recommends removing known confounders before WGCNA.

---

## Quick Reference: Which Paper to Cite

| Situation | Cite |
|-----------|------|
| Using WGCNA R package | Langfelder & Horvath (2008) BMC Bioinformatics |
| Describing the method | Zhang & Horvath (2005) Stat Appl Genet Mol Biol |
| Module preservation analysis | Langfelder et al. (2011) PLoS Comput Biol |
| Consensus WGCNA | Langfelder & Horvath (2007) BMC Syst Biol |
| Dynamic tree cut | Langfelder et al. (2008) Bioinformatics |
| Brain application | Oldham et al. (2008) Nat Neurosci |
