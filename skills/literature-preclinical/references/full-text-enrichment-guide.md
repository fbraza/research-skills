# Full-Text Enrichment Guide

**Workflow:** literature-preclinical  
**Purpose:** Instructions for reading full-text papers to enrich the synthesis report beyond abstract-level extraction.

---

## Overview

Step 5 of the preclinical workflow involves reading the **full text** of top papers to extract richer experimental details that are not available in abstracts alone. This step is agent-guided (not automated by scripts) and produces the `## Full-Text Insights` section of the synthesis report.

**Why full-text matters:**
- Abstracts omit dosing, statistical details, and negative results
- Key mechanistic findings are often in Results/Discussion, not the abstract
- Cell line authentication, passage numbers, and model validation details are methods-only
- Combination experiments and synergy data are rarely summarized in abstracts

---

## Paper Selection Criteria

Select papers for full-text review using this priority order:

### Tier 1 — Must Read (up to 10 papers)
- Experiment type = **"both"** (in vitro + in vivo) — highest translational value
- Published in high-impact journals (Nature, Cell, Cancer Cell, PNAS, JCI, Cancer Research, Oncogene)
- Cited ≥ 20 times (check Google Scholar or PubMed)
- Most recent papers (last 2 years) for cutting-edge findings

### Tier 2 — Read if Time Permits (up to 20 more papers)
- Experiment type = **"in_vivo"** only — animal model data
- Papers with PDX or syngeneic models (most clinically relevant animal models)
- Papers reporting combination therapy with your target

### Tier 3 — Abstract Only (remaining papers)
- Experiment type = **"in_vitro"** only — cell line data
- Review papers, meta-analyses (useful for context but not primary data)
- Papers with low relevance scores (< 0.5)

**Default:** Review up to 30 papers total (Tier 1 + Tier 2). Adjust based on user preference.

---

## How to Access Full Text

### Option 1: PubMed Central (PMC) — Free
```python
import requests

def fetch_pmc_fulltext(pmid: str) -> str:
    """Fetch full text from PubMed Central if open access."""
    # Check if PMC full text is available
    url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    params = {"dbfrom": "pubmed", "db": "pmc", "id": pmid, "retmode": "json"}
    response = requests.get(url, params=params).json()
    
    pmc_ids = response.get("linksets", [{}])[0].get("linksetdbs", [{}])[0].get("links", [])
    if not pmc_ids:
        return None  # Not open access
    
    pmc_id = pmc_ids[0]
    fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    fetch_params = {"db": "pmc", "id": pmc_id, "rettype": "full", "retmode": "xml"}
    return requests.get(fetch_url, params=fetch_params).text
```

### Option 2: DOI-based fetch via WebFetch tool
Use the agent's `WebFetch` tool with the paper DOI:
```
WebFetch(url=f"https://doi.org/{doi}", prompt="Extract experimental details: cell lines used, assays performed, animal models, dosing, key quantitative findings, and conclusions.")
```

### Option 3: bioRxiv / PubMed abstract fallback
If full text is unavailable (paywalled), use the extended abstract and supplement information from PubMed:
```
https://pubmed.ncbi.nlm.nih.gov/{pmid}/
```

---

## What to Extract from Full Text

For each paper reviewed in full text, extract the following structured fields:

### Experimental Details

| Field | What to Look For |
|-------|-----------------|
| **Cell lines** | Exact names, ATCC numbers, passage numbers, authentication method |
| **In vitro assays** | Assay name, duration, readout, n replicates |
| **IC50 / EC50** | Concentration values with units and confidence intervals |
| **Animal model** | Strain, sex, age, tumor implantation method, n per group |
| **Dosing** | Drug dose, route, schedule, duration |
| **Primary endpoint** | Tumor volume, survival, body weight, biomarker |
| **Key quantitative finding** | % tumor reduction, fold change, p-value, survival benefit |
| **Combination partners** | Other drugs tested in combination |
| **Negative results** | What did NOT work (often omitted from abstracts) |
| **Mechanistic insight** | Pathway, biomarker, resistance mechanism described |

---

## Report Format for Full-Text Insights

Replace the `## Full-Text Insights` placeholder in `preclinical_synthesis_report.md` with the following structure for each paper:

```markdown
## Full-Text Insights

### Paper 1: [Title] ([Year])
**PMID:** [PMID] | **Journal:** [Journal] | **Experiment type:** both/in_vitro/in_vivo

**In Vitro:**
- Cell lines: [e.g., MCF-7, MDA-MB-231 (ATCC authenticated)]
- Assays: [e.g., MTT viability (72h), colony formation (14 days), flow cytometry apoptosis]
- Key finding: [e.g., IC50 = 45 nM in MCF-7; 78% reduction in colony formation at 100 nM]

**In Vivo:**
- Model: [e.g., MCF-7 xenograft in nude mice (n=8/group)]
- Dosing: [e.g., 10 mg/kg oral, daily × 21 days]
- Key finding: [e.g., 62% tumor volume reduction vs vehicle (p<0.01); no significant weight loss]

**Mechanistic insight:** [e.g., CDK4/6 inhibition caused G1 arrest via Rb dephosphorylation; synergy with fulvestrant via ER pathway suppression]

**Negative results:** [e.g., No effect in KRAS-mutant subline; resistance emerged after 4 weeks]

---

### Paper 2: [Title] ([Year])
...
```

---

## Synthesis Across Papers

After reading all full-text papers, add a synthesis section summarizing:

1. **Most common cell lines** — Which 3-5 cell lines appear most frequently?
2. **Most common animal models** — Xenograft vs syngeneic vs PDX? Which strains?
3. **Dose range** — What is the typical effective dose range across studies?
4. **In vitro → in vivo concordance** — Do in vitro findings translate to animal models?
5. **Key mechanistic themes** — What pathways/biomarkers are consistently reported?
6. **Gaps** — What experiments are missing? (e.g., no PDX data, no combination studies)

---

## Quality Flags

When reading full text, flag papers with these quality issues:

| Flag | Condition |
|------|-----------|
| ⚠️ No cell line authentication | Cell lines not authenticated (ATCC/STR profiling) |
| ⚠️ Small n | Animal groups n < 5 |
| ⚠️ No statistics | No p-values or confidence intervals reported |
| ⚠️ Single cell line | Only one cell line tested in vitro |
| ⚠️ Xenograft only | No syngeneic or PDX model (limits immune relevance) |
| ✅ High quality | Authenticated cells + n≥8 + statistics + multiple models |

---

## Time Estimates

| Papers | Estimated Time |
|--------|---------------|
| 10 papers (Tier 1 only) | ~30-45 minutes |
| 20 papers (Tier 1 + 2) | ~60-90 minutes |
| 30 papers (default) | ~90-120 minutes |

---

## References

- ARRIVE guidelines for in vivo study reporting: https://arriveguidelines.org/
- ATCC cell line authentication: https://www.atcc.org/
- PMC Open Access: https://www.ncbi.nlm.nih.gov/pmc/
- PubMed E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25499/
