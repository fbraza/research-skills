---
id: literature-review
name: Scientific Literature Review
category: literature
short-description: Systematic literature search, citation verification, evidence synthesis, and biological claim validation using PubMed, bioRxiv, Semantic Scholar, and biological databases.
detailed-description: Systematic protocol for finding, evaluating, and synthesizing scientific evidence. Use when any biological claim needs a citation, when conducting a literature review on a gene/pathway/disease/drug, when checking whether a finding is novel, when verifying gene names or database IDs, or when searching for preclinical or clinical evidence. Covers PubMed E-utilities API, bioRxiv/medRxiv API, Semantic Scholar API, GEO API, and 20+ biological databases. Includes retrieval protocol, verification protocol, evidence quality standards, and search strategy guidelines.
starting-prompt: Conduct a literature review on my research topic with verified citations and evidence synthesis . .
---

# Scientific Literature Review

Systematic search, evaluation, and synthesis of scientific evidence. Every biological claim gets a verified source. Every citation is real.

## When to Use This Skill

**Use when:**
- ✅ Any biological claim needs a citation
- ✅ Conducting a literature review on a gene, pathway, disease, or drug
- ✅ Finding papers relevant to a research question
- ✅ Checking whether a finding is novel or already published
- ✅ Verifying that a gene name, pathway, database ID, or drug name is real
- ✅ Looking up drug mechanisms, targets, or clinical status
- ✅ Checking database versions, release notes, or data provenance
- ✅ Searching for preclinical or clinical evidence for a hypothesis
- ✅ Checking if a dataset, tool, or method has known issues or retractions

**Do not use for:**
- ❌ Running computational analyses — use appropriate analysis skills
- ❌ Generating figures — use `scientific-visualization`
- ❌ Auditing outputs for errors — use `scientific-audit`

## Retrieval Protocol

### Step 1 — Identify the claim type

Before searching, classify what you are looking for:
- **Factual biological claim** (gene function, pathway membership, protein structure)
- **Epidemiological claim** (disease prevalence, risk factor, survival data)
- **Mechanistic claim** (drug mechanism, signaling pathway, molecular interaction)
- **Methodological claim** (tool performance, benchmark comparison)
- **Novelty check** (has this been published before?)
- **Verification** (is this gene name / database ID / pathway real?)

### Step 2 — Choose the right source

| Claim type | Primary source | Secondary source |
|---|---|---|
| Gene function | UniProt, NCBI Gene, GeneCards | PubMed review |
| Pathway membership | KEGG, Reactome, GO | MSigDB |
| Drug mechanism | ChEMBL, DrugBank, DailyMed | PubMed |
| Clinical evidence | PubMed (RCT, meta-analysis) | ClinicalTrials.gov |
| Disease genetics | GWAS Catalog, ClinVar, OMIM | DisGeNET |
| Protein structure | PDB, UniProt | AlphaFold DB |
| Cancer mutations | COSMIC, cBioPortal | TCGA papers |
| Gene expression | GTEx, Human Protein Atlas | GEO |
| Drug-target interaction | ChEMBL, BindingDB | PubChem |
| Novelty check | PubMed, bioRxiv, Google Scholar | Semantic Scholar |

### Step 3 — Search with quality filters

- Apply year filters for recent evidence
- Specify study type when appropriate (RCT, Meta-Analysis, Systematic Review)
- Prefer high-impact sources (NEJM, Nature, Science, Cell, PubMed systematic reviews)
- Restrict to human evidence when human-specific data is required
- Always retrieve and evaluate ≥ 5-10 papers for any substantive claim
- For preclinical target validation queries, use the `literature-preclinical` skill

### Step 4 — Evaluate and synthesize

For each retrieved paper:
- Note the study type (RCT, cohort, case-control, in vitro, in vivo, computational)
- Note the sample size (n=3 in vitro vs n=10,000 GWAS are not equivalent)
- Note the organism (mouse data ≠ human data)
- Note the year (older papers may be superseded)
- Check if the paper has been retracted or has an expression of concern
- Note if the finding has been independently replicated

### Step 5 — Format citations correctly

- Use inline numbered citations: `[N]` immediately after the relevant claim
- Multiple citations: `[1, 2, 3]` — not `[1][2][3]`
- Cite once per paragraph — do not repeat the same number
- Use `[[DATABASE:ID]]` badges for database record IDs (e.g., `[[UniProt:P04637]]`)

## Verification Protocol

### Gene name verification
1. Check HGNC (human) or MGI (mouse) for the official symbol
2. Check for common aliases and outdated symbols
3. Verify the gene exists in the stated organism
4. Note if the symbol is ambiguous across organisms

### Database ID verification
1. Attempt to retrieve the record from the database
2. Verify the record exists and matches the stated entity
3. Note the database version and access date
4. Flag if the ID format is inconsistent with the database convention

### Citation verification
1. Search PubMed for the stated PMID or DOI
2. Verify the title, authors, and journal match
3. Check the retraction database (Retraction Watch)
4. Note if the paper has corrections or expressions of concern

### Drug/compound verification
1. Check ChEMBL or PubChem for the compound name or ID
2. Verify the stated mechanism and targets
3. Check clinical status on ClinicalTrials.gov
4. Note approved indications vs investigational uses

## Evidence Quality Standards

### What to state as established:
- Findings replicated in multiple independent studies
- Findings supported by meta-analysis or systematic review
- Database annotations from curated, high-confidence sources
- Mechanistic findings with strong experimental support

### What to flag as preliminary:
- Single-study findings, even in high-impact journals
- Preprint findings not yet peer-reviewed
- Computational predictions without experimental validation
- Animal model findings not yet replicated in humans
- In vitro findings not yet validated in vivo

### What to refuse to state without qualification:
- Any claim supported only by a single source
- Any claim from a retracted paper
- Any claim that contradicts the weight of evidence
- Any causal claim from correlational data

## API Reference: PubMed E-utilities

### Search (ESearch)

```
Base URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi
Parameters:
  db=pubmed
  term=<query>
  retmax=<N>           # max results (default 20, max 10000)
  retstart=<N>         # pagination offset
  usehistory=y         # for large result sets
  sort=relevance       # or "pub_date", "first_author"
  datetype=pdat        # publication date filter
  mindate=YYYY/MM/DD
  maxdate=YYYY/MM/DD
```

### Fetch abstracts (EFetch)

```
Base URL: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi
Parameters:
  db=pubmed
  id=<PMID1,PMID2,...>  # comma-separated PMIDs
  rettype=abstract       # or "xml" for structured data
  retmode=text           # or "xml"
```

### PubMed advanced query syntax

**Field tags:**
- `[tiab]` — title or abstract
- `[mh]` — MeSH term (includes narrower terms automatically)
- `[majr]` — MeSH term as major topic only
- `[pt]` — publication type
- `[au]` — author
- `[dp]` — publication date
- `[la]` — language

**MeSH subheadings:**
- `/drug therapy`, `/immunology`, `/metabolism`, `/genetics`, `/surgery`
- Example: `lung transplantation[mh]/immunology`

**Publication type filters (`[pt]`):**
- `Randomized Controlled Trial`, `Meta-Analysis`, `Systematic Review`, `Review`, `Clinical Trial`, `Case Reports`, `Guideline`

**Date and availability:**
- Date range: `2020:2024[dp]`
- Free full text: `AND free full text[sb]`
- Has abstract: `AND hasabstract[text]`

**Example queries:**
```
# Systematic reviews on a topic with date range
<topic>[mh] AND systematic review[pt] AND 2018:2024[dp]

# Free full-text RCTs on a drug
<drug>[nm] AND <disease>[mh] AND randomized controlled trial[pt] AND free full text[sb]
```

**Rate limits:** 3 requests/sec without API key; 10/sec with NCBI API key.

### Programmatic batch access (Python)

```python
from Bio import Entrez
Entrez.email = "your@email.com"

handle = Entrez.esearch(db="pubmed", term="macrophage[mh] AND lung transplantation[mh]",
                        retmax=200, usehistory="y")
record = Entrez.read(handle)
pmids = record["IdList"]

# Fetch abstracts in batch
fetch_handle = Entrez.efetch(db="pubmed", id=",".join(pmids),
                              rettype="abstract", retmode="text")
abstracts = fetch_handle.read()
```

## API Reference: bioRxiv / medRxiv

### Content API (search by date range)

```
Base URL: https://api.biorxiv.org/details/{server}/{interval}/{cursor}

Parameters:
  server: "biorxiv" or "medrxiv"
  interval: YYYY-MM-DD/YYYY-MM-DD (start/end dates)
  cursor: integer offset for pagination (0, 30, 60, ...)

Example:
  https://api.biorxiv.org/details/biorxiv/2024-01-01/2024-06-30/0
```

Returns JSON with: doi, title, authors, abstract, date, category, jatsxml URL.

### Pagination
- Returns 30 results per call (max 100 with format=json parameter)
- Increment cursor by 30 for next page
- Continue until `messages[0].count` < 30

### Subject categories (bioRxiv)
`bioinformatics`, `genomics`, `cell-biology`, `immunology`, `systems-biology`, `pathology`, `neuroscience`, `genetics`, `molecular-biology`, `cancer-biology`, `biochemistry`, `developmental-biology`, `microbiology`, `pharmacology-and-toxicology`, `biophysics`, `plant-biology`, `ecology`, `evolutionary-biology`, `physiology`, `zoology`

**Always label bioRxiv/medRxiv results as:** `[PREPRINT — not peer-reviewed]`

## API Reference: Semantic Scholar

### Paper search

```
Base URL: https://api.semanticscholar.org/graph/v1/paper/search

Parameters:
  query=<search terms>
  limit=<N>             # max 100
  offset=<N>            # pagination
  fields=<field1,field2,...>
  year=<YYYY> or <YYYY-YYYY>
  fieldsOfStudy=<field>

Fields available:
  paperId, title, abstract, year, referenceCount, citationCount,
  authors, journal, publicationTypes, tldr, openAccessPdf, externalIds
```

### Paper details (by ID)

```
GET https://api.semanticscholar.org/graph/v1/paper/{paper_id}
  paper_id: S2 ID, DOI (DOI:10.xxx), PMID (PMID:12345), ArXiv ID, etc.
  ?fields=title,abstract,year,citationCount,references,citations
```

### Author search

```
GET https://api.semanticscholar.org/graph/v1/author/search?query=<name>
GET https://api.semanticscholar.org/graph/v1/author/{author_id}/papers
```

**Rate limits:** 100 requests/5 min (unauthenticated); higher with API key.

## API Reference: GEO (Gene Expression Omnibus)

### Search for datasets

```
# Via E-utilities (same as PubMed)
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&term=<query>

# GEO DataSets search
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=gds&term=<disease>[Description]+AND+gse[Entry+Type]
```

### Fetch dataset metadata

```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&id=<GDS_UID>
```

### Direct GEO series access

```
# Series matrix (expression data + metadata)
https://ftp.ncbi.nlm.nih.gov/geo/series/<GSEnnn>/<GSE_ID>/matrix/

# Soft format (detailed metadata)
https://ftp.ncbi.nlm.nih.gov/geo/series/<GSEnnn>/<GSE_ID>/soft/

# GEOquery in R (preferred)
library(GEOquery)
gse <- getGEO("GSE12345")
```

### NCBI SRA (Sequence Read Archive)

```
# Search SRA
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=sra&term=<query>

# SRA Run Selector (for downloading)
https://www.ncbi.nlm.nih.gov/Traces/study/?acc=<SRP_ID>
```

## Database Quick Reference

### Literature
| Database | URL | Use for |
|---|---|---|
| PubMed / MEDLINE | pubmed.ncbi.nlm.nih.gov | Primary peer-reviewed literature |
| bioRxiv / medRxiv | biorxiv.org / medrxiv.org | Preprints (flag as not peer-reviewed) |
| Semantic Scholar | semanticscholar.org | Citation network, paper recommendations |

### Gene & Protein
| Database | URL | Use for |
|---|---|---|
| UniProt | uniprot.org | Protein function, structure, interactions, variants |
| NCBI Gene | ncbi.nlm.nih.gov/gene | Gene function, expression, orthologs |
| GeneCards | genecards.org | Comprehensive gene summaries |
| Human Protein Atlas | proteinatlas.org | Tissue and cell expression |
| OMIM | omim.org | Genetic disease associations |

### Pathways & Ontologies
| Database | URL | Use for |
|---|---|---|
| KEGG | genome.jp/kegg | Metabolic and signaling pathways |
| Reactome | reactome.org | Curated biological pathways |
| Gene Ontology | geneontology.org | BP, MF, CC terms |
| MSigDB | gsea-msigdb.org | Curated gene sets for enrichment |

### Disease & Genetics
| Database | URL | Use for |
|---|---|---|
| GWAS Catalog | ebi.ac.uk/gwas | GWAS results |
| ClinVar | ncbi.nlm.nih.gov/clinvar | Clinical variant interpretations |
| COSMIC | cancer.sanger.ac.uk/cosmic | Cancer somatic mutations |
| DisGeNET | disgenet.org | Gene-disease associations |
| gnomAD | gnomad.broadinstitute.org | Population allele frequencies |

### Drugs & Compounds
| Database | URL | Use for |
|---|---|---|
| ChEMBL | ebi.ac.uk/chembl | Bioactive compounds and drug targets |
| PubChem | pubchem.ncbi.nlm.nih.gov | Chemical structures and bioassays |
| DrugBank | drugbank.com | Drug mechanisms and interactions |
| ClinicalTrials.gov | clinicaltrials.gov | Clinical trial status and results |

### Cancer & Expression
| Database | URL | Use for |
|---|---|---|
| cBioPortal | cbioportal.org | Cancer genomics data |
| GEO | ncbi.nlm.nih.gov/geo | Gene Expression Omnibus |
| GTEx | gtexportal.org | Tissue-specific gene expression |
| DepMap | depmap.org | Cancer dependency map |

## Hard Rules

- **Never fabricate a citation, PMID, DOI, paper title, or author name**
- **Never present a single-source claim as established consensus**
- **Always note when a finding is from a preprint vs peer-reviewed paper**
- **Always note publication year — old papers may be superseded**
- **Always cross-reference key claims across multiple sources**
- **Always flag retracted papers and expressions of concern**
- **Never state a biological claim without a source**
- **Never confuse database annotation confidence levels (curated vs predicted)**
- **Always distinguish human evidence from animal model evidence**
- **Always distinguish in vitro from in vivo evidence**
- **Always distinguish correlation from causation in cited studies**
- **Always include the access date for database records** (databases change)

## Related Skills

**Use alongside:**
- `literature-preclinical` — Structured preclinical evidence synthesis with experiment extraction
- `scientific-writing` — Synthesize literature into manuscripts, grants, and rebuttals
- `scientific-audit` — Verify that citations and claims in outputs are accurate

**Provides citations for:**
- All analysis skills that produce biological findings requiring literature context
