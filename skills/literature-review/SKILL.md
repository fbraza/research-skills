---
id: literature-review
name: Scientific Literature Review
category: literature
short-description: Systematic literature search, citation verification, evidence synthesis, and biological claim validation using PubMed, bioRxiv, medRxiv, and Semantic Scholar.
detailed-description: Systematic protocol for finding, evaluating, and synthesizing scientific evidence from published literature. Use when any biological claim needs a citation, when conducting a literature review on a gene/pathway/disease/drug, when checking whether a finding is novel or already published, or when searching for preclinical or clinical evidence for a hypothesis. Covers PubMed E-utilities API, bioRxiv/medRxiv API, Semantic Scholar API, and full-text PDF access. Includes retrieval protocol, verification protocol, evidence quality standards, search strategy guidelines, and literature-to-hypothesis synthesis.
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
- ✅ Looking up drug mechanisms, targets, or clinical status from published literature
- ✅ Searching for preclinical or clinical evidence for a hypothesis
- ✅ Checking if a dataset, tool, or method has known issues or retractions
- ✅ Downloading full-text PDFs for in-depth review

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
| Gene function | PubMed (reviews, primary literature) | Semantic Scholar |
| Pathway membership | PubMed (reviews, primary literature) | Semantic Scholar |
| Drug mechanism | PubMed (RCT, pharmacology papers) | Semantic Scholar |
| Clinical evidence | PubMed (RCT, meta-analysis, systematic review) | Semantic Scholar |
| Novelty check | PubMed, bioRxiv | Semantic Scholar |
| Recent preprints | bioRxiv (life sciences), medRxiv (clinical) | Semantic Scholar |
| Citation discovery | Semantic Scholar | PubMed ELink |

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
- Use `[[DATABASE:ID]]` badges for database record IDs (e.g., `[[PMID:12345678]]`)

## Verification Protocol

### Citation verification
1. Search PubMed for the stated PMID or DOI
2. Verify the title, authors, and journal match
3. Check the retraction database (Retraction Watch)
4. Note if the paper has corrections or expressions of concern

## Evidence Quality Standards

### What to state as established:
- Findings replicated in multiple independent studies
- Findings supported by meta-analysis or systematic review
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

## Literature-to-Hypothesis Synthesis

*This section distills implicit and explicit hypotheses from a collected paper set into structured, testable propositions. Activate this phase after retrieval and evidence evaluation are complete.*

### When to Use This Phase

- Gap analysis: identify which hypotheses in the literature are well-supported vs. under-tested
- Contradiction synthesis: multiple papers report conflicting findings — surface contradictions and propose resolution hypotheses
- Grant or proposal preparation: generate candidate hypotheses with evidence grades and validation plans
- Mechanism inference: papers describe correlations or associations — infer mechanistic if-then propositions
- Cross-domain synthesis: literature spans multiple fields — identify integrative hypotheses connecting domains

### Hypothesis Extraction Modes

**Explicit** — Papers state hypotheses directly:
`"We hypothesized that …"` / `"If X, then Y"` — extracted via pattern matching and LLM parsing.

**Implicit** — Conclusions or claims imply testable propositions:
- `"X is associated with Y"` → `"If X varies, then Y varies"`
- `"X inhibits Y"` → `"If X is present, then Y activity decreases"`

**Mechanistic** — Inferred causal chains:
- `"X upregulates Y, which promotes Z"` → `"If X is inhibited, then Z decreases via Y"`

### If-Then Formalization & Falsifiability

Every hypothesis is cast in standard form:

> **If** [condition or intervention] **then** [expected outcome] **because** [mechanism or rationale].

Reject hypotheses that are:
- Vague or tautological ("X affects Y somehow")
- Not testable with available technology
- Insufficiently scoped (no population, species, or context specified)

| Criterion | Description |
|---|---|
| Falsifiable | Clear condition under which the hypothesis would be refuted |
| Specific | Includes measurable variables |
| Scoped | Specifies population, cell type, species, context |
| Mechanistic | Includes "because" or pathway rationale when possible |
| Evidence-grounded | Tied to at least one source; not purely speculative |

Assign a **strength score** (Strong / Moderate / Weak) based on directness of evidence and number of supporting sources.

### Evidence Synthesis

For each hypothesis, build an evidence table:

| Source | Finding | Supports / Contradicts | Study Type | Notes |
|---|---|---|---|---|
| PMID X | Key finding excerpt | Supports | in vitro | Sample size n=3 |

Grade evidence by quality: RCT > cohort > case-control > in vitro; multiple independent replications > single study.

Mark:
- **Consensus**: high agreement across sources
- **Controversial**: conflicting findings with no resolution
- **Gap**: hypothesis with weak or no direct evidence

### Contradiction Analysis

1. **Detect** — pairs of papers with incompatible claims (e.g., "X increases Y" vs. "X decreases Y")
2. **Reconcile** — propose resolution hypotheses: *"If the effect of X on Y depends on Z (cell type, dose, stage), then both findings could be correct."*
3. **Prioritize** — flag high-impact contradictions (frequently cited, central to the field) for resolution

Build a **Contradiction Matrix**:

| Hypothesis | Source A | Source B | Resolution Hypothesis |
|---|---|---|---|
| H1: If MET amplification... | PMID A | PMID B | If EGFR resistance depends on co-mutations... |

### Experimental Validation Suggestions

For each hypothesis, propose concrete experiments:

| Element | Content |
|---|---|
| Validation type | Direct test, replication, extension, or refutation |
| Design | Intervention, control, outcome, sample size, key confounders |
| Feasibility | Low / Medium / High (based on common lab resources) |
| Falsification criterion | What result would refute the hypothesis |
| Priority | Ranked by impact × feasibility |

Reference protocols.io or standard methods when applicable (e.g., CRISPR knockout protocol for gene X).

### Structured Report Output

When synthesis is the deliverable, emit a Markdown report:

```markdown
# Literature-to-Hypothesis Report: [Topic]

## Executive Summary
- N hypotheses extracted
- M contradictions identified
- Top 3 validation priorities

## 1. Hypotheses

### H1: [If-then statement]
- **Scope:** [cell type, species, context]
- **Strength:** Strong / Moderate / Weak
- **Supporting evidence:** [table]
- **Contradicting evidence:** [table or "None identified"]
- **Validation suggestion:** [experiment design]
- **Falsification criterion:** [what would refute]

### H2: ...

## 2. Contradiction Matrix
| Hypothesis | Source A | Source B | Resolution Hypothesis |
|---|---|---|---|

## 3. Validation Roadmap
| Priority | Hypothesis | Experiment | Feasibility |
|---|---|---|---|

## 4. Source Papers
- [PMID] Author. Title. Journal. Year.

## 5. Appendix: Evidence Excerpts
[Key quotes supporting/contradicting each hypothesis]
```

Export format: Markdown (default), HTML, or JSON for programmatic use. Citation style: APA, Vancouver, or Nature — verify via a citation manager.

## Hard Rules

- **Never fabricate a citation, PMID, DOI, paper title, or author name**
- **Never present a single-source claim as established consensus**
- **Always note when a finding is from a preprint vs peer-reviewed paper**
- **Always note publication year — old papers may be superseded**
- **Always cross-reference key claims across multiple sources**
- **Always flag retracted papers and expressions of concern**
- **Never state a biological claim without a source**
- **Always distinguish human evidence from animal model evidence**
- **Always distinguish in vitro from in vivo evidence**
- **Always distinguish correlation from causation in cited studies**
- **Always check institutional access and open-access sources before using Sci-Hub**

## API Reference: PubMed E-utilities

> **Load reference:** `references/pubmed_routine.md` — quick-start for routine searches (≤200 PMIDs, common field tags).
> For batch operations, history server, or all 9 endpoints → `references/pubmed_api_reference.md`.
> For advanced search syntax (proximity operators, wildcards, MeSH subheadings) → `references/pubmed_search_syntax.md`.
> For query templates by research scenario → `references/pubmed_common_queries.md`.

### Core Endpoints (Routine)

| Endpoint | Purpose | When to use |
|---|---|---|
| `esearch.fcgi` | Search and retrieve PMIDs | Every PubMed search |
| `efetch.fcgi` | Download full records / abstracts | Retrieving paper details |
| `esummary.fcgi` | Get document summaries (title, authors, journal) | Quick metadata checks |
| `epost.fcgi` | Upload UIDs for batch processing | Processing > 200 PMIDs |
| `elink.fcgi` | Find related articles, cross-database links | Citation discovery |
| `ecitmatch.cgi` | Match partial citations to PMIDs | Verifying incomplete references |

## API Reference: bioRxiv / medRxiv

> **Load reference:** `references/biorxiv_routine.md` — quick-start for routine searches (date range, DOI lookup, recent pubs).
> For all endpoints, full response schema, version tracking, or custom pagination → `references/biorxiv_api_reference.md`.
> The `biorxiv_search.py` script in `scripts/` implements the full search client used in `biorxiv_api_reference.md`.

### Content API (Search by Date Range)

```
https://api.biorxiv.org/details/{server}/{interval}/{cursor}
```

| Parameter | Value |
|---|---|
| `server` | `"biorxiv"` or `"medrxiv"` |
| `interval` | `YYYY-MM-DD/YYYY-MM-DD` (start/end) |
| `cursor` | Integer offset: `0`, `30`, `60`, … |

Returns JSON with: `doi`, `title`, `authors`, `abstract`, `date`, `category`, `jatsxml URL`, `version`, `license`, `published`.

### DOI Lookup

```
https://api.biorxiv.org/details/biorxiv/{doi}
```

### Pagination

- `/details/` returns 30 results/page — increment cursor by 30
- `/pubs/` returns up to 100 results/page — increment cursor by 100
- Stop when `messages[0].count` < page size

### PDF Download URL

```
https://www.biorxiv.org/content/{doi}v{version}.full.pdf
```

**Always label bioRxiv/medRxiv results as:** `[PREPRINT — not peer-reviewed]`.

## API Reference: Semantic Scholar

> **Load reference:** `references/semanticscholar_routine.md` — quick-start for paper search, lookup, and author search.
> For citation network analysis or bulk queries → consult the full Semantic Scholar API documentation.

### Paper Search

```
GET https://api.semanticscholar.org/graph/v1/paper/search
```

| Parameter | Value |
|---|---|
| `query` | Search terms |
| `limit` | Max results (default 10, max 100) |
| `fields` | Comma-separated fields to return |

Useful fields: `title`, `abstract`, `year`, `citationCount`, `openAccessPdf`, `externalIds`.

### Paper Details (by ID)

```
GET https://api.semanticscholar.org/graph/v1/paper/{paper_id}
```

`paper_id` accepts: S2 ID, DOI (`DOI:10.xxx`), PMID (`PMID:12345`), ArXiv ID.

**Rate limits:** 100 requests/5 min (unauthenticated); higher with API key.

## Full-Text Access: Sci-Hub PDF Resolver

> **Load reference:** `references/scihub_routine.md` — CLI usage, output codes, Python API.
> **Always check institutional access and open-access sources first** (PubMed Central, publisher OA, bioRxiv). Use Sci-Hub only as a last resort.

**Script:** `scripts/scihub_pdf_resolver.py` — zero-dependency Python script.

### Usage

```bash
python scripts/scihub_pdf_resolver.py "10.1038/s41586-024-07000-0"
```

### Output Codes

| Output | Meaning |
|---|---|
| Prints a URL | Direct PDF link, ready to download |
| `NOT_FOUND` | Sci-Hub does not have this paper. Check for `OA_LINK <url>` for open-access alternatives. |
| `MIRROR_ERROR` | Sci-Hub mirrors could not be reached reliably |
| `INVALID_INPUT` | The DOI is malformed |

**Exit codes:** `0` = found, `1` = not found, `2` = mirror error, `3` = invalid input.

## Database Quick Reference

> This skill covers only publication databases. For non-publication databases (UniProt, KEGG, ChEMBL, ClinVar, etc.), use the appropriate domain-specific skill.

### Literature
| Database | URL | Use for |
|---|---|---|
| PubMed / MEDLINE | pubmed.ncbi.nlm.nih.gov | Primary peer-reviewed literature |
| bioRxiv / medRxiv | biorxiv.org / medrxiv.org | Preprints (label as `[PREPRINT — not peer-reviewed]`) |
| Semantic Scholar | semanticscholar.org | Citation network, paper recommendations |

## Related Skills

**Use alongside:**
- `literature-preclinical` — Structured preclinical evidence synthesis with experiment extraction; complementary to Phase 3 when moving from hypothesis to in vivo validation planning
- `scientific-writing` — Synthesize literature into manuscripts, grants, and rebuttals
- `scientific-audit` — Verify that citations and claims in outputs are accurate

**Provides citations for:**
- `scientific-writing` — manuscripts, grants, and rebuttals
- `literature-preclinical` — preclinical evidence synthesis
- `scientific-audit` — verifying citations and claims in outputs
- All analysis and domain skills that need published evidence to support biological, clinical, or methodological claims
