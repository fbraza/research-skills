# Agents → Skills Migration Plan

> Created: 2026-03-25
> Status: DRAFT — awaiting review and approval before execution

---

## Context

The `.claude/agents/` folder contains 9 agent persona files originally written for Claude Code's subagent system. In Hermes, the tool names and invocation patterns are different. The domain knowledge in these agents is valuable, but the "persona" wrapper is not. This plan migrates the useful knowledge into skills and removes the agents folder.

---

## Current State: 9 Agents

| Agent | Lines | What it does |
|---|---|---|
| the-analyst | 471 | Core computation engine, runs all code |
| the-librarian | 348 | Literature search, citation verification |
| the-scholar | 663 | Scientific writing, interpretation, grants |
| the-storyteller | 847 | Visualization, figures, reports |
| the-reviewer | 627 | Forensic audit of all outputs (359 checks) |
| the-architect | 499 | Experimental design, power analysis |
| the-navigator | 409 | Multi-omics integration guidance |
| the-clinician | 462 | Clinical analysis (survival, MR, biomarkers) |
| the-strategist | 305 | Planning, task decomposition |

---

## Assessment Per Agent

### Convert to NEW skills (4 agents → 4 new skills)

1. **THE LIBRARIAN → `literature-review` skill**
   - Extract: retrieval protocol, verification protocol, search strategy, evidence quality standards
   - ADD: PubMed E-utils API reference
   - ADD: bioRxiv/medRxiv API reference
   - ADD: GEO/SRA API reference
   - ADD: Semantic Scholar API reference
   - ADD: search strategy scripts
   - This REPLACES the-librarian.md

2. **THE SCHOLAR → `scientific-writing` skill**
   - Extract: paper analysis protocol, grant writing protocol, manuscript writing protocol, rebuttal protocol
   - ADD: reporting guidelines reference (CONSORT, STROBE, PRISMA, etc.)
   - This REPLACES the-scholar.md

3. **THE STORYTELLER → `scientific-visualization` skill**
   - Extract: figure standards, clinical figure standards, quality check protocol
   - ADD: colorblind palette references
   - ADD: template plotting scripts (Python + R)
   - This REPLACES the-storyteller.md

4. **THE REVIEWER → `scientific-audit` skill**
   - Extract: full 359-check audit protocol across 10 categories
   - Preserve: verdict system (PASS / REVIEW / FAIL), structured output format
   - This is the most unique and valuable agent — preserve it faithfully
   - This REPLACES the-reviewer.md

### Merge into EXISTING skills (2 agents)

5. **THE NAVIGATOR → merge into `multi-omics-integration` skill**
   - Already have this skill with scripts and references
   - Add: method selection decision trees, integration strategy guidance

6. **THE ARCHITECT → merge into `experimental-design-statistics` skill**
   - Already have this skill with scripts and references
   - Add: verdict system (APPROVED / CONDITIONAL / REJECTED), confound detection checklist

### Not needed as skills (3 agents)

7. **THE STRATEGIST → drop**
   - Generic planning behavior already handled by CLAUDE.md instructions
   - No domain-specific knowledge worth preserving as a standalone skill

8. **THE ANALYST → drop**
   - "Run code correctly" is baseline agent behavior
   - Specific rules (use padj not pvalue, set seeds, etc.) already live in knowhow guides

9. **THE CLINICIAN → drop**
   - Already fully covered by existing skills:
     - `survival-analysis-clinical`
     - `disease-progression-longitudinal`
     - `lasso-biomarker-panel`
     - `mendelian-randomization-twosamplemr`
     - `clinicaltrials-landscape`
     - `polygenic-risk-score-prs-catalog`
   - The clinician is essentially a dispatcher to skills that already exist

---

## Execution Plan

### Phase 1: Create new skills from agents

- [ ] Create `literature-review` skill (from the-librarian.md + new API references)
- [ ] Create `scientific-writing` skill (from the-scholar.md + reporting guidelines)
- [ ] Create `scientific-visualization` skill (from the-storyteller.md + templates)
- [ ] Create `scientific-audit` skill (from the-reviewer.md — faithful preservation)

### Phase 2: Merge agent knowledge into existing skills

- [ ] Patch `multi-omics-integration` — add Navigator's method selection decision trees
- [ ] Patch `experimental-design-statistics` — add Architect's verdict system + confound checklist

### Phase 3: Clean up

- [ ] Delete entire `.claude/agents/` folder (all value migrated)
- [ ] Update `CLAUDE.md`:
  - Remove "The Subagent Family" section
  - Update Decision Framework to reference skills instead of agents
  - Keep core behavioral principles (those are good)

---

## Key Principle

**Agents are personas. Skills are knowledge.** Hermes doesn't need personas — it needs the knowledge those personas were carrying.

---

## Also pending (from earlier audit)

There are 15 dead-end references across 10 skills (files mentioned in SKILL.md that don't exist on disk). These should be cleaned up as a separate task. See session from 2026-03-25 for the full list.
