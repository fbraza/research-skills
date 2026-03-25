---
id: scientific-writing
name: Scientific Writing & Interpretation
category: communication
short-description: Write and edit scientific manuscripts, grant applications, rebuttals, and biological interpretations with rigorous prose and verified citations.
detailed-description: Protocols for scientific writing across all major document types — paper analysis and critical review, grant applications (Specific Aims, Significance, Innovation, Approach), manuscripts (Introduction, Discussion, Abstract, figure legends), biological interpretation of computational results, hypothesis generation, novelty assessment, and reviewer rebuttal writing. Includes reporting guidelines (CONSORT, STROBE, PRISMA, TRIPOD, ARRIVE), scientific writing standards, and a two-stage outline-to-prose workflow. Every biological claim requires a verified citation.
starting-prompt: Help me write a scientific manuscript section with rigorous prose and verified citations . .
---

# Scientific Writing & Interpretation

Turn data into narrative and narrative into science. Protocols for manuscripts, grants, rebuttals, and biological interpretation.

## When to Use This Skill

**Use when:**
- ✅ Reading, reviewing, or critiquing a scientific paper (full analysis, not just summary)
- ✅ Writing or editing a grant application (Specific Aims, Significance, Innovation, Approach)
- ✅ Writing or editing a manuscript (Introduction, Discussion, Abstract, cover letter)
- ✅ Interpreting biological findings in scientific context
- ✅ Generating hypotheses from data or literature
- ✅ Assessing the novelty of a finding against existing literature
- ✅ Translating computational results into biological narrative
- ✅ Writing a rebuttal to reviewer comments
- ✅ Reviewing figure legends, methods sections, or supplementary notes

**Do not use for:**
- ❌ Running computational analyses — use appropriate analysis skills
- ❌ Generating figures — use `scientific-visualization`
- ❌ Retrieving citations — use `literature-review` (this skill synthesizes them)

## Paper Analysis Protocol

When given a paper to read, review, or analyze, follow this protocol. A paper analysis is not a summary — it is a critical evaluation.

### Step 1 — First read: understand the claim
- What is the central claim of this paper?
- What question does it address?
- What is the experimental approach?
- What are the key results?
- What do the authors conclude?

### Step 2 — Evidence assessment: does the data support the claim?
For each major conclusion:
- What figure or data supports this conclusion?
- Is the evidence direct or indirect?
- Is the sample size adequate for the claim?
- Are the controls appropriate?
- Is the effect size meaningful, not just statistically significant?
- Are there alternative explanations the authors did not consider?
- Are there confounders that were not controlled?

### Step 3 — Literature context: is this novel?
- Search for related work using the `literature-review` skill
- Has this been shown before in the same system?
- Does this confirm, extend, or contradict existing knowledge?
- What is the most important prior work this paper builds on?
- What is the most important prior work this paper ignores?

### Step 4 — Methodological critique
- Are the methods appropriate for the question?
- Are there known limitations of the methods used?
- Are the methods described in enough detail to reproduce?
- Are there better methods that should have been used?
- Are there missing experiments that would strengthen the conclusions?

### Step 5 — Synthesis and verdict
- What is the genuine contribution of this paper?
- What are the key strengths and weaknesses?
- What is the appropriate level of confidence in the conclusions?
- What follow-up experiments are needed?
- What is the clinical or translational relevance (if any)?

## Grant Writing Protocol

A grant is not a research report. It is an argument: *this question matters, nobody has answered it, we can answer it, and here is exactly how.*

### Specific Aims Page

The most important page. Reviewers decide here. One page — no exceptions.

**Structure:**
```
Paragraph 1 — The problem (2-3 sentences)
  What is the disease/phenomenon? Why does it matter?
  What is the scale of the problem? (epidemiology, unmet need)
  End with: "However, [the critical gap]."

Paragraph 2 — The gap and the opportunity (2-3 sentences)
  What is specifically unknown?
  Why has it not been answered before?
  What new tool/data/approach makes it answerable now?
  End with: "We hypothesize that [central hypothesis]."

Paragraph 3 — The approach (1-2 sentences)
  What is the overall strategy?
  What makes it feasible? (preliminary data reference)

Aims (3 aims, each 3-4 sentences):
  Aim 1: [Verb] [what] to [test/establish/determine] [specific hypothesis]
  Rationale: [why this aim, what it will show]
  Approach: [brief method]
  Expected outcome: [what success looks like]

Closing paragraph — Impact (2-3 sentences)
  What will this grant produce?
  How will it change the field?
  What does it enable next?
```

**Hard rules for Specific Aims:**
- The gap must be real and specific — not "X is poorly understood"
- The hypothesis must be falsifiable — not "we will study X"
- Each aim must be independently valuable — if Aim 1 fails, Aims 2 and 3 still matter
- Preliminary data must be referenced — reviewers need to believe it is feasible
- No jargon in the first paragraph — reviewers from adjacent fields read this too

### Significance Section
- Establish the importance with citations
- Quantify the unmet need (prevalence, mortality, economic burden)
- Describe current knowledge and identify the specific gap
- Explain why filling this gap matters

**Common mistakes:** Reviewing the entire field instead of establishing the gap. Using vague language: "poorly understood," "remains unclear." Replace with: "The mechanism by which X causes Y is unknown because..."

### Innovation Section
- State what is genuinely new — method, question, model system, or conceptual framework
- Distinguish incremental advance from paradigm shift (be honest)
- Explain why the innovation matters — what it enables that was not possible before

**Common mistakes:** Claiming innovation for using an existing method in a new disease. Overstating — reviewers know the field and will penalize overclaiming.

### Approach Section
- Begin each aim with a brief rationale (1-2 sentences)
- Describe experimental design clearly and specifically
- Include preliminary data supporting feasibility
- Address potential pitfalls and alternative approaches
- Include a timeline
- End with expected outcomes and interpretation

**Common mistakes:** Describing methods without explaining why they answer the question. Ignoring potential pitfalls. Proposing too much for the budget.

## Manuscript Writing Protocol

### Introduction
**Purpose:** Establish the gap and the question. Not a review of the field.

```
Paragraph 1 — The broad context (3-4 sentences)
Paragraph 2 — What is known (3-5 sentences, with citations)
Paragraph 3 — The gap (2-3 sentences)
Paragraph 4 — This study (2-3 sentences): what we did, found, and what it means
```

**Hard rules:** Gap must be stated explicitly. Last paragraph must state what the paper does and found. No results in the Introduction. Maximum 4-5 paragraphs.

### Discussion
**Purpose:** Interpret the results. Not repeat them.

```
Paragraph 1 — Summary of key findings (3-4 sentences)
Paragraphs 2-N — Interpretation (one paragraph per major finding)
  What does this mean mechanistically? How does it relate to prior work?
  What are the alternative interpretations?
Second-to-last paragraph — Limitations (be honest)
Last paragraph — Conclusions and future directions
```

**Hard rules:** Never start by repeating the Results. Every interpretation must be supported. Limitations must not be minimized. No new data in the Discussion.

### Abstract
**Purpose:** The paper for most readers. Must stand alone.

```
Background (2 sentences): What is the problem and gap?
Methods (2-3 sentences): What did we do?
Results (3-4 sentences): What did we find? (specific, with numbers)
Conclusions (1-2 sentences): What does it mean?
```

**Hard rules:** Every number must match the paper exactly. No citations. No undefined abbreviations. No claims not supported in the paper.

### Figure Legends
- First sentence: what the figure shows (not what it proves)
- Subsequent sentences: experimental details needed to interpret the figure
- Statistical test used, n per group, what error bars represent
- Abbreviations defined
- Scale bars for microscopy images

## Biological Interpretation Framework

When translating computational results into biological narrative:

### Level 1 — What happened?
- What changed? (genes up/down, pathways enriched, clusters separated)
- How big is the change? (effect size, not just significance)
- How consistent is it? (across samples, replicates, methods)

### Level 2 — What does it mean mechanistically?
- What biological process is being activated or suppressed?
- What cell type is doing this?
- What is the upstream trigger? What is the downstream consequence?

### Level 3 — What does it mean in context?
- Is this expected given the experimental condition?
- Is this consistent with the known biology?
- Is this a primary effect or a secondary consequence?
- Does this confirm, extend, or contradict prior knowledge?

### Level 4 — What does it mean for the hypothesis?
- Does this support the central hypothesis?
- Does this suggest a new hypothesis?
- What experiment would test this interpretation?

### Level 5 — What does it mean for the field?
- Is this finding novel?
- What is the clinical or translational relevance?
- What does it enable next?

## Reviewer Rebuttal Protocol

### Principles
- **Acknowledge before defending** — start by acknowledging the reviewer's concern
- **Never dismiss** — even if the reviewer is wrong, explain why respectfully
- **Never capitulate without reason** — if you disagree, explain why with evidence
- **Show the work** — if you did an additional experiment, show the result
- **Be specific** — vague responses ("we have clarified this") are not enough

### Structure for each comment:
```
Reviewer X, Comment Y:
[Quote the reviewer's comment]

Response:
[Acknowledge the concern]
[Explain what was done]
[Show the result or revised text]
[State where in the manuscript this is addressed]
```

### Common reviewer concerns:
- **"Sample size too small"** → Acknowledge, provide power calculation, note consistency with prior work
- **"Controls missing"** → Show if available. If not, acknowledge as limitation.
- **"Alternative explanation"** → Address directly. Rule out with existing data or acknowledge.
- **"Statistics inappropriate"** → Fix if wrong. If not, explain with citation.
- **"Overclaiming"** → Revise language. Show revised text.

## Reporting Guidelines

Apply the correct checklist when writing or reviewing a manuscript. Missing items = desk rejection risk.

| Guideline | Study type |
|---|---|
| **CONSORT** | Randomized controlled trials |
| **STROBE** | Observational studies (cohort, case-control, cross-sectional) |
| **PRISMA** | Systematic reviews and meta-analyses |
| **STARD** | Diagnostic accuracy studies |
| **TRIPOD** | Prediction model development or validation |
| **ARRIVE** | Animal research |
| **CARE** | Case reports |
| **SPIRIT** | Study protocols for clinical trials |
| **CHEERS** | Health economic evaluations |
| **SQUIRE** | Quality improvement studies |

**IMRAD section ownership:**
- **Introduction:** Establish the gap. End with specific objective/hypothesis.
- **Methods:** Detail enough for replication. Statistical methods with justification.
- **Results:** Findings only — no interpretation. Primary outcome first.
- **Discussion:** Interpret, compare to literature, acknowledge limitations. No new data.

## Scientific Writing Standards

### Precision
- "Increased" is vague. "Upregulated 2.3-fold (padj = 0.003)" is precise.
- "Associated with" is not "causes." Use the right verb.
- "Consistent with" is not "demonstrates." Use the right verb.
- "Suggests" is not "proves." Use the right verb.

### Clarity
- One idea per sentence. One argument per paragraph.
- The first sentence of each paragraph states the main point.
- No sentence should require re-reading to understand.

### Logical flow
- Every paragraph follows from the previous one.
- Every claim is supported before the next claim is made.
- The reader should never ask "why are you telling me this?"

### Hedging appropriately
- Match the language to the strength of the evidence. Always.
- Overconfident: "This demonstrates that X causes Y" → if correlational: "This suggests that X may contribute to Y"
- Underconfident: "It is possible that X might perhaps be involved" → if data is strong: "X regulates Y, as shown by..."

### Common writing errors to correct
- **Passive voice overuse** — use active voice when the agent matters
- **Nominalization** — "the activation of" → "activating"
- **Redundancy** — "in order to" → "to"; "due to the fact that" → "because"
- **Vague quantifiers** — "many," "several" → give the actual number
- **Unjustified superlatives** — "the first," "the most important" → only if verifiable
- **Tense inconsistency** — Methods in past tense; established facts in present tense
- **Undefined abbreviations** — define every abbreviation at first use

### Two-stage writing process
1. **Stage 1 — Outline:** Draft key points as a structured list (claims, evidence, flow). Get citations at this stage.
2. **Stage 2 — Prose:** Convert outline into full paragraphs. Never submit bullets as final text.

Fix the argument in stage 1; fix the language in stage 2.

## Hard Rules

### Scientific integrity
- **Never overstate the evidence** — match language to the strength of the data
- **Never present speculation as fact** — always flag uncertainty explicitly
- **Never write a biological claim without a verified citation**
- **Never fabricate citations, gene names, pathway names, or statistics**
- **Never present a single-study finding as established consensus**
- **Always distinguish correlation from causation**
- **Always distinguish human evidence from animal model evidence**

### Grant writing
- **The Specific Aims page is one page — no exceptions**
- **The gap must be real and specific**
- **The hypothesis must be falsifiable**
- **Each aim must be independently valuable**
- **Preliminary data must be referenced**
- **Potential pitfalls must be addressed**

### Manuscript writing
- **The Introduction establishes the gap — not reviews the field**
- **The Discussion interprets — not repeats the Results**
- **The Abstract must stand alone — every number must match the paper**
- **Limitations must be stated honestly — not minimized**

## Related Skills

**Use alongside:**
- `literature-review` — Find and verify citations for all biological claims
- `scientific-visualization` — Create publication-ready figures
- `scientific-audit` — Verify conclusions are supported by evidence

**Writes about results from:**
- All analysis skills that produce biological findings requiring interpretation
