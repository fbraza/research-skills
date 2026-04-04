---
name: scientific-writing
description: Protocols for three core scientific document types — original research papers (Introduction, Methods, Results, Discussion, Abstract, rebuttals), literature reviews (narrative and thematic synthesis), and grant applications (Specific Aims, Significance, Innovation, Approach). Includes biological interpretation frameworks, scientific writing standards, and a two-stage outline-to-prose workflow. Every biological claim requires a verified citation.
allowed-tools: Read, Write, Edit, WebFetch, WebSearch, mcp__claude_ai_PubMed__search_articles, mcp__claude_ai_PubMed__get_article_metadata, mcp__claude_ai_PubMed__lookup_article_by_citation
starting-prompt: Help me write a scientific document with rigorous prose and verified citations.
---

# Scientific Writing & Interpretation

Turn data into narrative and narrative into science. Protocols for original research papers, literature reviews, and grant applications.

## When to Use This Skill

**Use when:**
- ✅ Writing or editing an original research paper (Introduction, Methods, Results, Discussion, Abstract, figure legends)
- ✅ Writing a literature review (narrative synthesis, thematic organization, critical appraisal)
- ✅ Writing or editing a grant application (Specific Aims, Significance, Innovation, Approach)
- ✅ Interpreting biological findings in scientific context
- ✅ Generating hypotheses from data or literature
- ✅ Assessing the novelty of a finding against existing literature
- ✅ Writing a rebuttal to reviewer comments
- ✅ Analyzing or critically reviewing a paper

**Do not use for:**
- ❌ Running computational analyses — use appropriate analysis skills
- ❌ Generating figures — use `scientific-visualization`
- ❌ Retrieving and searching citations — use `literature-review` (this skill synthesizes them)

---

## Document Type 1 — Original Research Paper

### Paper Analysis Protocol

When given a paper to read, review, or analyze, follow this protocol. A paper analysis is not a summary — it is a critical evaluation.

**Step 1 — First read: understand the claim**
- What is the central claim of this paper?
- What question does it address?
- What is the experimental approach?
- What are the key results?
- What do the authors conclude?

**Step 2 — Evidence assessment: does the data support the claim?**
For each major conclusion:
- What figure or data supports this conclusion?
- Is the evidence direct or indirect?
- Is the sample size adequate for the claim?
- Are the controls appropriate?
- Is the effect size meaningful, not just statistically significant?
- Are there alternative explanations the authors did not consider?
- Are there confounders that were not controlled?

**Step 3 — Literature context: is this novel?**
- Search for related work using the `literature-review` skill
- Has this been shown before in the same system?
- Does this confirm, extend, or contradict existing knowledge?
- What is the most important prior work this paper builds on?
- What is the most important prior work this paper ignores?

**Step 4 — Methodological critique**
- Are the methods appropriate for the question?
- Are there known limitations of the methods used?
- Are the methods described in enough detail to reproduce?
- Are there missing experiments that would strengthen the conclusions?

**Step 5 — Synthesis and verdict**
- What is the genuine contribution of this paper?
- What are the key strengths and weaknesses?
- What is the appropriate level of confidence in the conclusions?
- What follow-up experiments are needed?
- What is the clinical or translational relevance (if any)?

---

### Manuscript Writing Protocol

#### Introduction
**Purpose:** Establish the gap and the question. Not a review of the field.

```
Paragraph 1 — The broad context (3-4 sentences)
Paragraph 2 — What is known (3-5 sentences, with citations)
Paragraph 3 — The gap (2-3 sentences)
Paragraph 4 — This study (2-3 sentences): what we did, found, and what it means
```

**Hard rules:** Gap must be stated explicitly. Last paragraph must state what the paper does and found. No results in the Introduction. Maximum 4-5 paragraphs.

#### Methods
**Purpose:** Enable replication. Every methodological choice must be justifiable.

- Describe in enough detail for an expert to reproduce
- Statistical methods with justification
- Use past tense throughout
- Reagents, instruments, and software with version numbers where relevant

#### Results
**Purpose:** Present findings — no interpretation.

- Primary outcome first
- Data with effect sizes and statistics (not just p-values)
- No discussion of meaning — save for Discussion
- Each paragraph = one finding, with the supporting figure/table

#### Discussion
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

#### Abstract
**Purpose:** The paper for most readers. Must stand alone.

```
Background (2 sentences): What is the problem and gap?
Methods (2-3 sentences): What did we do?
Results (3-4 sentences): What did we find? (specific, with numbers)
Conclusions (1-2 sentences): What does it mean?
```

**Hard rules:** Every number must match the paper exactly. No citations. No undefined abbreviations. No claims not supported in the paper.

#### Figure Legends
- First sentence: what the figure shows (not what it proves)
- Subsequent sentences: experimental details needed to interpret the figure
- Statistical test used, n per group, what error bars represent
- Abbreviations defined
- Scale bars for microscopy images

---

### Reviewer Rebuttal Protocol

**Principles:**
- **Acknowledge before defending** — start by acknowledging the reviewer's concern
- **Never dismiss** — even if the reviewer is wrong, explain why respectfully
- **Never capitulate without reason** — if you disagree, explain why with evidence
- **Show the work** — if you did an additional experiment, show the result
- **Be specific** — vague responses ("we have clarified this") are not enough

**Structure for each comment:**
```
Reviewer X, Comment Y:
[Quote the reviewer's comment]

Response:
[Acknowledge the concern]
[Explain what was done]
[Show the result or revised text]
[State where in the manuscript this is addressed]
```

**Common reviewer concerns:**
- **"Sample size too small"** → Acknowledge, provide power calculation, note consistency with prior work
- **"Controls missing"** → Show if available. If not, acknowledge as limitation.
- **"Alternative explanation"** → Address directly. Rule out with existing data or acknowledge.
- **"Statistics inappropriate"** → Fix if wrong. If not, explain with citation.
- **"Overclaiming"** → Revise language. Show revised text.

---

## Document Type 2 — Literature Review

A literature review is not a list of papers. It is a synthesis: an argument about what the field knows, where it disagrees, and what remains unresolved.

### Types of Literature Reviews

| Type | Purpose |
|---|---|
| **Narrative review** | Synthesizes a body of evidence around a topic or question; author-curated |
| **Scoping review** | Maps the extent and nature of the evidence; identifies gaps |
| **Mini-review** | Focused synthesis for a specific question; shorter, more targeted |
| **Perspective/Opinion** | Argues a position, often with supporting literature |

### Structure Protocol

#### Title and Abstract
- Title should signal the scope: "The role of X in Y" or "X in the context of Y: a review"
- Abstract: background → scope → key themes covered → conclusions

#### Introduction
```
Paragraph 1 — Why this topic matters now (clinical, biological, or conceptual relevance)
Paragraph 2 — What is known and what is contested
Paragraph 3 — Scope and objective of this review: what question does it address?
```

#### Body — Thematic Organization (preferred over chronological)
- Organize by conceptual themes, not by publication date or by paper
- Each section = one theme or sub-question
- Within each section:
  1. State the consensus (with citations)
  2. Note the evidence supporting it
  3. Flag contradictions, caveats, or context-dependence
  4. State what remains unresolved

**Hard rule:** Never write a paragraph per paper. Synthesize across papers around a point.

#### Synthesis and Perspectives
- What does the body of evidence collectively show?
- Where are the key unresolved questions?
- What are the methodological limitations across the field?
- What future directions are most needed?

#### Conclusion
- 1-2 paragraphs
- Restate the key take-home messages
- No new information — only synthesis of what was covered

### Critical Appraisal Within a Review
For each body of evidence cited, consider:
- Consistency across studies (are findings reproducible?)
- Study design quality (mechanistic vs. associative; human vs. animal)
- Sample sizes and effect sizes — not just whether results are significant
- Confounders or limitations specific to the model system

### Common Literature Review Mistakes
- **Describing papers instead of synthesizing them** — the reader wants to know what the field shows, not what each paper found
- **Omitting contradictory evidence** — selectively citing only supporting papers is a bias
- **Claiming consensus where none exists** — flag genuine controversy
- **Losing the thread** — every section should connect back to the central question

---

## Document Type 3 — Grant Writing

A grant is a layered argument, not a research plan. Each section makes the same argument from a different angle: the problem matters (Significance), only you can answer it (Innovation), and here is exactly how (Approach). A reviewer who reads only the opening page should already understand the question, the gap, the hypothesis, and the deliverable.

### Abstract / Project Summary

The abstract is the grant compressed to one paragraph. Write it last; treat it as the grant's argument in miniature.

```
[Problem + scale]: X is [clinical/biological importance]. Despite [existing approaches],
  [the fundamental failure/gap] persists.
[Preliminary anchor]: We have shown that [finding that motivates the proposal].
[Central hypothesis]: Based on these findings, we hypothesize that [falsifiable, mechanistic hypothesis].
[Central objective]: The central objective of this proposal is to [specific goal].
[Aim preview]: In Aim 1, we will [brief]. In Aim 2, we will [brief]. In Aim 3, we will [brief].
[Impact]: Overall, [approach] aims to [broader contribution to field].
```

**Hard rules:**
- The hypothesis must appear explicitly — not implied
- Every aim must be previewed in one sentence
- The impact statement must name what the grant will *produce*, not what it will *study*

---

### Specific Aims / Objectives Page

**The most important page. Reviewers make their funding decision here. One page — no exceptions.**

```
Opening paragraph (150-200 words):
  Sentence 1-2: Why this problem matters (clinical/biological importance, scale)
  Sentence 3: "Despite [existing approaches], [the fundamental problem] persists" — the gap
  Sentence 4-5: "We recently demonstrated that..." — anchor in your own preliminary data
  Sentence 6: "Based on these findings, we hypothesize that [central, falsifiable hypothesis]"
  Sentence 7: "The central objective of this proposal is to [specific goal]"
  Sentence 8: "These studies will [concrete impact on field]"

Aims (3 aims, each ~80-120 words):
  [Aim title]: "To [active verb] [what] [in which model/cohort/system]"
  [Gap]: What remains unknown that this aim addresses (1 sentence, specific)
  [Approach]: What you will do and how (2-3 sentences, specific enough to be credible)
  [Deliverable]: "Completion of this aim will [specific, tangible output]"
```

**Hard rules for each aim:**
- Title starts with an active infinitive verb: "To define...", "To identify...", "To determine..."
- The gap is real and specific — not "poorly understood" but "it remains unclear whether X because Y"
- The deliverable is concrete: not "we will understand X" but "this aim will generate a list of [X] that [enables Y]"
- Each aim is independently valuable — if Aim 1 fails, Aims 2 and 3 still matter
- Aims are logically connected: outputs of Aim 1 feed Aim 2, but each stands alone

**Hard rules for the opening paragraph:**
- No jargon in the first two sentences — adjacent-field reviewers read this
- The gap follows: "Despite [strength of field], [specific failure/unknown] persists"
- The hypothesis must appear in the opening paragraph — not on page 3
- Preliminary data must be referenced — reviewers need to believe the approach is feasible

---

### Significance / Context Section

**Purpose:** Convince the reviewer that the question is worth funding. Not a literature review — a structured argument for why this specific gap matters now.

**Use numbered, bold-titled subsections. Each title must be a declarative claim, not a label:**

```
Wrong:  "1. Background on [pathogen/disease]"
Right:  "1. [Disease X] is the leading cause of Y, yet all interventions have failed"

Wrong:  "2. Preliminary data"
Right:  "2. A new framework that explains why prior approaches have failed"
```

**Subsection architecture:**
1. Clinical/biological importance: scale, morbidity, burden, why it matters *now*
2. What your own prior work has already shown — frames the proposal as a logical extension, not speculation
3. Why existing models/approaches are insufficient to answer the question
4. Why your model/approach/population is uniquely suited
5. What the grant will produce and its downstream impact

**Citation strategy:**
- Cite to establish scope (epidemiology, burden) — these facts need authority
- Cite to mark the boundary of prior knowledge: "X has been shown [cit]; however, whether Y occurs remains unknown"
- Do NOT cite to catalog the literature — every citation must serve the argument

**Common mistakes:**
- Reviewing the field instead of building an argument
- Vague gaps: "X remains poorly understood" → Replace with: "whether X occurs in [specific context] is unknown because [specific barrier]"
- Gap that doesn't match your aims — the gap must be exactly what your objectives address

---

### Innovation Section

**Purpose:** Prove that you — specifically you — can answer this question, and that answering it represents a genuine advance.

**Use numbered, bold-titled subsections, one per type of innovation:**

```
1. Technical innovation — new model, method, or tool that enables the study
2. Conceptual innovation — new framework, reframing of the question, or mechanistic model
3. Innovation in application — how your approach advances the specific field
```

**For each innovation:**
- State what is new
- Explain why it was not possible before (what barrier does it overcome?)
- Integrate a figure showing proof of concept — not as illustration, but as evidence

**Hard rules:**
- Distinguish incremental advance from paradigm shift — be honest; reviewers know the field
- Do not claim innovation for using an existing method in a new disease unless the barrier to that application was itself a conceptual contribution
- Each innovation must connect directly to a specific aim

---

### Approach / Work Plan Section

**Purpose:** Show exactly how you will answer each aim. Not a methods section — a logical argument supported by experiments.

**Structure for each aim:**

```
[Aim title — repeated as section header]

Rationale (1-2 paragraphs):
  Why is this aim necessary? What does prior work establish?
  What specific aspect remains unknown that this aim will address?
  Reference relevant preliminary data inline.

[Optional] Sub-hypothesis:
  "We hypothesize that [X] because [mechanistic reasoning]"

Approach (organized in logical sub-sections):
  Each sub-experiment introduced as:
    "To [test whether / determine / identify] X, we will [method]"
  Preliminary data integrated inline:
    "We have already shown that [X] (Fig. Y), which establishes [Z]"
  Decision points explicit:
    "Samples/conditions meeting [criterion] will be advanced to [next step]"

Expected outcomes and interpretation:
  What results are expected and what they will mean
  What alternative results are possible and how they will be interpreted

Potential challenges and alternative strategies:
  Name specific, credible challenges — not generic ones
  For each challenge: specific alternative approach
  Where relevant: show how other aims provide corroboration

Aim completion statement (final sentence):
  "Completion of this aim will [specific, tangible deliverable]"
```

**Preliminary data rules:**
- Preliminary data is not optional — it is the credibility of the proposal
- It must prove: (a) the model/approach works, (b) the hypothesis is plausible, (c) you have already begun
- Introduce as evidence of concept: "We showed proof of principle by [X] (Fig. Y)"
- Never present preliminary data as background — it is evidence for feasibility

**Pitfalls rules:**
- Pitfalls demonstrate expertise, not weakness — a grant with no anticipated pitfalls signals naivety
- Each pitfall must be specific: not "the experiments might fail" but "if [specific scenario], then [specific consequence], which we will address by [specific alternative]"
- Pitfalls can be turned into strengths: "If we observe [unexpected result], this would suggest [alternative hypothesis], which we will test by [additional experiment]"

**Statistics:**
- Include a statistics section at the end of the Approach
- Name specific tests for specific comparisons
- Address sample size and power

---

### Cross-Section Architecture

The same argument runs through every section — each makes the case from a different angle:

| Section | The argument it makes |
|---|---|
| **Abstract** | The full argument compressed: problem → gap → hypothesis → aims → impact |
| **Aims page** | The argument as a one-page pitch: why it matters, what you'll do, what it will produce |
| **Significance** | Why the question is worth funding: scale, gap, your prior positioning |
| **Innovation** | Why you specifically can answer it: technical + conceptual advances |
| **Approach** | Exactly how, with evidence of feasibility and risk management |

**The aims page is not a table of contents — it is the argument itself.** A reviewer who reads only the aims page should be convinced the project is worth funding.

---

### Structural Principles (Universal — ANR / ERC / NIH)

These principles hold regardless of section naming in any specific funding scheme:

1. **The hypothesis appears on page 1** — not buried in the approach
2. **Bold subsection titles are claims, not labels** — make the argument in the title itself
3. **Preliminary data is the foundation of credibility** — reference it in every section, not just Approach
4. **Deliverables are concrete and specific** — name what the aim will produce, not what it will study
5. **Aims are logically connected but independently defensible** — show the dependency chain, but each aim stands alone
6. **Pitfalls show expertise** — acknowledge specific risks, provide specific alternatives
7. **Human/translational relevance threads throughout** — connect mechanism to disease to clinical implication in every section
8. **Statistics are named, not implied** — specific tests, sample sizes, power considerations

---

## Biological Interpretation Framework

When translating computational or experimental results into biological narrative:

**Level 1 — What happened?**
- What changed? (genes up/down, pathways enriched, clusters separated)
- How big is the change? (effect size, not just significance)
- How consistent is it? (across samples, replicates, methods)

**Level 2 — What does it mean mechanistically?**
- What biological process is being activated or suppressed?
- What cell type is doing this?
- What is the upstream trigger? What is the downstream consequence?

**Level 3 — What does it mean in context?**
- Is this expected given the experimental condition?
- Is this consistent with the known biology?
- Is this a primary effect or a secondary consequence?
- Does this confirm, extend, or contradict prior knowledge?

**Level 4 — What does it mean for the hypothesis?**
- Does this support the central hypothesis?
- Does this suggest a new hypothesis?
- What experiment would test this interpretation?

**Level 5 — What does it mean for the field?**
- Is this finding novel?
- What is the clinical or translational relevance?
- What does it enable next?

---

## Writing Philosophy

### Epistemological Stance
- Treat unknowns as productive questions, not gaps to apologize for — elevate them to research agendas
- Calibrate epistemic commitment precisely: *suggest* < *likely* < *propose* < *demonstrate*. Never claim more than the evidence warrants
- Distinguish three levels explicitly: correlation → mechanism → principle. Never conflate them
- Challenge consensus through reframing, not refutation — propose a framework large enough to encompass both the consensus and the contradiction
- Always distinguish human from animal evidence, correlation from causation, observation from interpretation

### Argumentation Architecture
- Build arguments dialectically: thesis (consensus) → antithesis (what it cannot explain) → synthesis (new framework)
- Move from specific observations → general principles → evolutionary/design meaning — never stop at the molecular level
- Identify the question behind the question: reframe surface questions ("which signals drive differentiation?") into deeper ones ("what information must the system extract?")
- Propose frameworks and taxonomies that make phenomena intelligible through principle, not just describable through detail
- Sustain intellectual tension rather than prematurely resolving it — unresolved questions engage the reader

### Voice and Authority
- Be simultaneously authoritative and exploratory: assert frameworks boldly, but mark their epistemic status honestly
- Position the reader as a collaborative investigator, not a passive recipient
- Use rhetorical questions strategically to signal productive uncertainty and frame research agendas
- Introduce precise neologisms when existing vocabulary is inadequate — but mark them as provisional
- Prefer verbs that emphasize interpretation: *suggest*, *propose*, *reveal*, *account for*, *elaborate* — not *prove*, *demonstrate*, *confirm*

### Precision and Language
- "Increased" is vague. "Upregulated 2.3-fold (padj = 0.003)" is precise
- "Associated with" ≠ "causes." "Consistent with" ≠ "demonstrates." Use the right verb
- One idea per sentence. One argument per paragraph. The first sentence states the main point
- Use analogies to ground abstraction in recognizable logic (control theory, ecological systems, sensory integration)
- Transitions must be conceptually explicit, not superficial: not "furthermore" but "However, this creates a new problem" or "This transforms the question from X to Y"
- Avoid nominalization: "the activation of" → "activating"; "in order to" → "to"; "due to the fact that" → "because"
- Avoid vague quantifiers: "many," "several" → give the actual number
- Tense: Methods in past tense; established facts in present tense; define all abbreviations at first use

### Two-Stage Writing Process
1. **Stage 1 — Outline:** Draft the argument as a structured list: claims, evidence, logical flow. Identify citations at this stage. Fix the logic here.
2. **Stage 2 — Prose:** Convert into full paragraphs. Never submit bullets as final text. Fix the language here.

Fix the argument in stage 1; fix the language in stage 2.

---

## Document-Specific Style

### Literature Reviews

**Architecture:**
- Use problem–framework–research agenda structure, not chronological or purely thematic organization
- Open with a productive contradiction or definitional crisis: establish that the existing framework is *incomplete*, not wrong
- Order sections by increasing abstraction — establish empirical ground before introducing conceptual novelty
- Close by proposing a research agenda or catalog of principles, not a summary of what was covered

**Opening paragraph:**
- Signal the field is at an inflection point: existing framework explains much but not all
- Use "However" to introduce productive tension — not to dismiss, but to reveal incompleteness
- Template: "[Field X] has been built on [established pillars]. However, [phenomenon Y] cannot be explained by the current framework."

**Body:**
- Synthesize across papers around a conceptual strand — never describe papers one by one
- When studies disagree, identify the deeper assumption generating the conflict, then propose a framework that transcends it
- Use citations to establish precedent and extend it, or to mark the boundary of knowledge — not to list authorities
- Introduce frameworks, taxonomies, and categories that make phenomena intelligible through principle
- Use analogies to make abstract principles tangible: control circuits, ecological systems, social organization

**Closing:**
- Do not summarize what was covered — position the field at a new vantage point
- Frame remaining unknowns as a structured research agenda
- Connect the mechanisms reviewed to their adaptive logic and evolutionary meaning

---

### Original Research Papers

**Abstract:**
- Open with a problem statement (disease context, mechanistic gap, or paradox) — not a field review
- Use "Here we show/find" as the pivot from context to finding
- State the central finding as a mechanism or principle, with specificity
- Close with a broader implication (functional, evolutionary, or conceptual) — not a restatement of the finding

**Introduction:**
- Open with a broad mechanistic principle, foundational definition, or context — NOT "X is poorly understood"
- Funnel in 4–6 logical steps from broad context to the specific gap
- State the gap precisely: "remains unknown," "has not been established," or frame it as a paradox
- Justify the hypothesis mechanistically before stating it (numbered reasons or logical inference from prior steps)
- State the hypothesis explicitly: "We hypothesized that..."
- Introduce the paper: "Here we show..." or "In this study we..."

**Results:**
- Subsection titles: mechanistic statements ("X regulates Y through Z") or observational statements ("X controls Y") — not questions
- Open each section with experimental rationale: "To test whether X..." or "On the basis of these results, we reasoned..."
- Connect experiments with logic, not sequence: teleological ("To dissect the mechanism, we...") or causal inference ("These data suggested that... We therefore asked...")
- State conclusions directly: "These data indicate that X is integrin-independent" — not vague summaries
- Flag surprising findings explicitly: "Surprisingly, we found that..."
- Summarize multi-experiment blocks: "Together, these findings demonstrate that..."

**Discussion:**
- Open by reframing findings in broader conceptual context (high-impact journals) OR restating key findings concisely (specialist journals) — NOT by repeating individual results
- Structure: key finding → integration with prior literature → paradox or contrast → mechanism → broader principle → future directions
- Handle prior literature through contrast and integration: "In contrast to...", "This extends...", "This resolves the paradox that..."
- Reframe limitations as context-dependent distinctions where possible; acknowledge explicitly where not
- Close by positioning the finding within a broader biological or evolutionary framework

---

### Grants

- The grant is an argument: the question matters, no one has answered it, you can answer it now
- The gap must be a genuine intellectual crisis — not "X is poorly understood" but "the mechanism by which X causes Y is unknown because no tool existed to test it until now"
- The hypothesis must be falsifiable and arrive with mechanistic justification, as in a research paper introduction
- Structure aims at escalating abstraction: molecular → cellular → physiological/organismal
- Preliminary data functions like a results introduction: what you found, why it is surprising, what it demands to explain
- The impact statement follows the review closing structure: mechanism → principle → therapeutic implication

---

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
- **The aims/objectives page is one page — no exceptions**
- **The hypothesis appears on page 1 — not buried in the approach**
- **The gap must be specific: not "poorly understood" but "unknown because [barrier]"**
- **Each aim title starts with an active verb and ends with a concrete deliverable**
- **Each aim is independently valuable — if Aim 1 fails, Aims 2 and 3 still matter**
- **Preliminary data is not optional — it proves feasibility, not just interest**
- **Bold subsection titles in Significance and Innovation must be declarative claims, not labels**
- **Pitfalls must be specific, with specific alternatives — not generic acknowledgments**

### Manuscript writing
- **The Introduction establishes the gap — not reviews the field**
- **The Discussion interprets — not repeats the Results**
- **The Abstract must stand alone — every number must match the paper**
- **Limitations must be stated honestly — not minimized**

### Literature review
- **Synthesize across papers — never describe papers one by one**
- **Include contradictory evidence — selective citation is a bias**
- **Flag genuine controversy — do not claim consensus where none exists**

---

## Related Skills

**Use alongside:**
- `literature-review` — Find and verify citations for all biological claims
- `scientific-visualization` — Create publication-ready figures
- `scientific-audit` — Verify conclusions are supported by evidence

**Writes about results from:**
- All analysis skills that produce biological findings requiring interpretation
