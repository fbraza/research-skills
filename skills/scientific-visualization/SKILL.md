---
id: scientific-visualization
name: Scientific Visualization & Reporting
category: communication
short-description: Create publication-ready figures, structured reports, and presentations with colorblind-friendly palettes, mandatory quality checks, and journal-specific formatting.
detailed-description: Standards and protocols for scientific visualization and reporting. Covers figure type specifications (volcano, heatmap, UMAP, KM curve, forest plot, ROC, enrichment plots, etc.), color standards (Okabe-Ito palette, colorblind accessibility), export standards (SVG + PNG, 300+ DPI), clinical figure standards (at-risk tables, PH violation warnings, CV AUC reporting), publication figure sizing (Nature/Science/Cell column widths), multi-panel composites, mandatory quality checks, report structure, PowerPoint, and LaTeX Beamer slides.
starting-prompt: Create publication-ready visualizations of my analysis results with colorblind-friendly palettes . .
---

# Scientific Visualization & Reporting

Publication-ready figures, structured reports, and scientific presentations. How science is presented is part of the science.

## When to Use This Skill

**Use when:**
- ✅ Generating any visualization (volcano plot, heatmap, UMAP, KM curve, etc.)
- ✅ Creating a final report or summary document
- ✅ Building a PowerPoint or Beamer presentation
- ✅ Verifying figure quality after generation
- ✅ Formatting tables for publication
- ✅ Creating composite multi-panel figures
- ✅ Checking that a figure actually shows what it claims to show

**Do not use for:**
- ❌ Running statistical analyses — use appropriate analysis skills
- ❌ Searching literature — use `literature-review`
- ❌ Auditing outputs for errors — use `scientific-audit`

**Key principle:** A misleading figure is a scientific integrity problem. A figure nobody can read is a result nobody will use.

## Pre-Visualization Protocol

Before creating any figure, verify:

1. **What is being plotted?** (DEGs, clusters, survival, enrichment, etc.)
2. **What is the message?** (What should the reader take away?)
3. **What is the appropriate plot type?**
4. **User preferences?** (format, palette, size, journal requirements)
5. **If no preferences:** use defaults (SVG + PNG, colorblind-friendly, 300 DPI)

### Tool Selection

| Figure type | Primary tool | Notes |
|---|---|---|
| Volcano plot | seaborn + matplotlib | Use adjustText for labels |
| Heatmap | ComplexHeatmap (R) or seaborn | ComplexHeatmap for complex annotations |
| UMAP / tSNE | scanpy.pl or seaborn | Include cluster labels |
| Kaplan-Meier | survminer (R) or lifelines (Python) | At-risk table mandatory |
| Forest plot (HR/OR) | ggplot2 (R) or matplotlib | Log-scale x-axis; reference line at 1.0 |
| ROC curve | pROC (R) or sklearn + matplotlib | Start (0,0), end (1,1); AUC in legend |
| Calibration curve | val.prob (R) or sklearn | Diagonal reference; Hosmer-Lemeshow p |
| Enrichment dot plot | clusterProfiler / enrichplot (R) | Dot size = gene count |
| Box/violin plot | ggplot2 + ggprism or seaborn | Include individual points |
| PCA plot | matplotlib or ggplot2 | % variance on axes |
| Network | igraph or networkx | Node size = degree or importance |
| Multi-panel composite | matplotlib subplots or patchwork (R) | Label panels A, B, C... |

## Visualization Standards

### Libraries (defaults)
- **Python:** seaborn + matplotlib (primary), plotnine for grammar-of-graphics
- **R:** ggplot2 + ggprism theme (primary), ComplexHeatmap for heatmaps
- **Heatmaps:** ComplexHeatmap (R) preferred for complex biological heatmaps

### Color Standards

**Always use colorblind-friendly palettes.** Never use red/green only. Never use rainbow/jet.

**Recommended palettes:**
```python
# Okabe-Ito (preferred for categorical data)
okabe_ito = ['#E69F00', '#56B4E9', '#009E73', '#F0E442',
             '#0072B2', '#D55E00', '#CC79A7', '#000000']

# Diverging (fold change, correlation): "RdBu_r" or "coolwarm"
# Sequential (expression, p-value): "viridis", "magma", "plasma"
```

```r
# R categorical
library(RColorBrewer)
palette <- brewer.pal(8, "Set2")

# R diverging
scale_fill_gradient2(low = "blue", mid = "white", high = "red", midpoint = 0)
```

- Maximum 12 distinct colors for categorical data — use grouping if more needed
- For diverging data: blue-white-red or similar, symmetric around zero
- For sequential data: viridis family

### Text and Labels
- **No overlapping labels** — use `adjustText` (Python) or `ggrepel` (R)
- Font size: minimum 8pt for axis labels, 10pt for titles, at publication size
- Axis labels must include units where applicable
- Legend must be present and unambiguous
- Statistical significance: define *, **, *** in the legend or caption
- Sample sizes (n=) must appear on figure or caption

### Axes and Scales
- Never truncate a y-axis to exaggerate effect sizes
- Always start y-axis at 0 for absolute values (bar charts, counts)
- Log scales must be clearly labeled
- Negative values cannot be plotted on log-scale axes — use symlog if needed
- Axes on comparative plots must be on the same scale
- Aspect ratio must not distort the data

### Export Standards
- **Default:** Save in both SVG (vector) and PNG (raster)
- **Resolution:** Minimum 300 DPI for PNG; 600 DPI for publication
- **Never use JPEG** for scientific data figures — lossy compression corrupts data
- **Naming:** Descriptive filenames with version suffixes (`volcano_plot_v1.svg`)
- **Location:** Always save to `./results/` or appropriate subfolder

### Publication Figure Sizing

| Journal | Single column | Double column |
|---|---|---|
| Nature | 89 mm (3.5 in) | 183 mm (7.2 in) |
| Science | 55 mm (2.2 in) | 175 mm (6.9 in) |
| Cell | 85 mm (3.35 in) | 178 mm (7.0 in) |

When journal is unspecified: default to Nature sizing.

### Typography at Print Size
```python
import matplotlib as mpl
mpl.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica'],
    'font.size': 8,
    'axes.labelsize': 9,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'axes.titlesize': 9,
})
```

Axis labels: sentence case with units — `"Time (hours)"` not `"TIME (HOURS)"`.

### Multi-Panel Figures
```python
from string import ascii_uppercase
import matplotlib.pyplot as plt

fig = plt.figure(figsize=(7.2, 4))  # Nature double column
gs = fig.add_gridspec(2, 2, hspace=0.4, wspace=0.35)
axes = [fig.add_subplot(gs[i, j]) for i in range(2) for j in range(2)]

for idx, ax in enumerate(axes):
    ax.text(-0.15, 1.05, ascii_uppercase[idx],
            transform=ax.transAxes, fontsize=10,
            fontweight='bold', va='top', ha='right')
```

## Figure Type Specifications

### Volcano Plot
- x-axis: log2FoldChange (labeled)
- y-axis: -log10(padj) (labeled)
- Threshold lines: vertical (log2FC cutoff) + horizontal (padj cutoff)
- Color: significant up (red/orange), significant down (blue), NS (grey)
- Labels: top N genes by significance (use adjustText/ggrepel)
- Legend: color categories defined
- Title: comparison name

### Heatmap
- Row/column clustering method stated in caption
- Distance metric stated in caption
- Color scale: diverging for fold change, sequential for expression
- Color scale symmetric around 0 for fold change
- Row/column annotations if applicable
- Scale bar present

### UMAP / tSNE
- Axes labeled (UMAP1, UMAP2 or tSNE1, tSNE2)
- n_neighbors (UMAP) or perplexity (tSNE) stated in caption
- Cluster labels on plot (not just in legend)
- Colorblind-friendly categorical palette

### Box / Violin Plot
- Individual data points shown (jitter or strip)
- Median line visible
- What box/whiskers represent defined in caption
- Statistical comparison brackets with significance labels
- Sample sizes (n=) per group

### PCA Plot
- x-axis: PC1 (X% variance explained)
- y-axis: PC2 (Y% variance explained)
- Points colored by condition/batch/sample
- Sample labels if n is small (use adjustText/ggrepel)

## Clinical Figure Standards

Clinical figures have stricter requirements because they inform patient outcome inferences.

### Kaplan-Meier Curve
- x-axis: time with units explicitly labeled
- y-axis: "Survival Probability", range [0, 1]
- **At-risk table: MANDATORY** below the plot, one row per group
- Confidence intervals: shaded bands or dashed lines (95% CI)
- Censoring marks: tick marks on each curve at censored timepoints
- Log-rank p-value on plot
- Legend: group names + N events / N total
- Median survival: only if KM crosses 50%; otherwise state "Not reached"
- **PH violation warning:** if Schoenfeld global p < 0.05, add caption note

### Forest Plot (HR/OR)
- x-axis: HR or OR on **log scale** (not linear)
- Reference line at 1.0 (vertical dashed line)
- Confidence intervals: horizontal lines through each point
- Variable names: left column, readable
- HR (95% CI) and p-value: right column
- **PH violation warning** if applicable
- **EPV warning** if events per variable < 10

### ROC Curve
- x-axis: 1 - Specificity, range [0, 1]
- y-axis: Sensitivity, range [0, 1]
- Diagonal reference line (random classifier)
- Starts at (0,0), ends at (1,1) — always verify
- **Report CV AUC** (not final model AUC) with 95% CI
- Discovery vs validation curves distinguished if both present

### Biomarker Stability Plot
- x-axis: selection frequency [0, 1]
- y-axis: feature names (sorted by frequency, descending)
- Threshold line at stability cutoff (e.g., 80%)
- Coefficient direction shown (positive vs negative)
- Maximum 30 features

### MR Scatter Plot
- x-axis: SNP-exposure beta; y-axis: SNP-outcome beta
- Error bars: SE on both axes
- Regression lines: one per MR method (IVW, MR-Egger, WM, WMode)
- SNP labels with rsID (ggrepel for top SNPs only)
- **Funnel plot as mandatory companion figure**

## Mandatory Quality Check

**Every figure must pass this check before delivery. No exceptions.**

### Step 1 — Save the figure
```python
fig.savefig("./results/figure_name.png", dpi=300, bbox_inches="tight")
fig.savefig("./results/figure_name.svg", bbox_inches="tight")
```

### Step 2 — Verify figure quality
Inspect the saved figure. Verify:
- Is the figure blank or empty?
- Are axis labels present and readable?
- Is the legend present and unambiguous?
- Are the data points/bars/lines visible?
- Is the color scale appropriate?
- Are there any rendering artifacts?
- Does the figure show what it claims to show?

### Step 3 — Act on the result
- **Passes:** Proceed to delivery
- **Blank, clipped, or unreadable:** Regenerate immediately. Do not deliver.
- **Minor issues (small font, legend overlap):** Fix and re-check.
- **Shows something different from intended:** Flag the issue. Do not deliver.

## Report Standards

### When to create a report
Create a markdown report (`./results/report_<title>.md`) ONLY when:
- User explicitly requests a report
- Task involves multiple complex analyses needing structured documentation
- Results are substantial enough to warrant a standalone document

**Do NOT create reports for** simple queries, single analyses, or quick lookups.

### Report structure
```markdown
# [Analysis Title]

## Summary
[2-3 sentence executive summary]

## Methods
[Tools, versions, parameters, thresholds]

## Results
### [Section 1]
[Findings with inline citations]
[Figure: figure_name.png]

## Key Figures
- figure_1.png — [description]

## Output Files
- results.csv — [description]
```

### PowerPoint standards (only when explicitly requested)
- Use python-pptx for programmatic slide creation
- Maximum 5-6 bullets per slide
- Include key figures as images
- Title slide + content slides + summary slide

### LaTeX Beamer slides (only when explicitly requested)
- Default theme: Metropolis (modern, minimal, conference-ready)
- Okabe-Ito palette for colorblind safety
- One main idea per slide, maximum 5 bullets
- Figures as PDF/SVG (vector) or PNG ≥ 300 DPI
- Narrative arc: Hook → Context/Gap → Approach → Results → Implications

## Hard Rules

- **Run figure quality check on every figure before delivering — no exceptions**
- **If a figure is blank, clipped, or unreadable — regenerate before continuing**
- **Never truncate a y-axis to exaggerate effect sizes**
- **Never use a rainbow/jet color scale**
- **Never use red/green only color encoding**
- **Bubble chart area (not radius) must be proportional to the value**
- **Log scales must be clearly labeled**
- **Always save figures in both SVG and PNG unless user specifies otherwise**
- **Always save to `./results/`**
- **Never deliver a figure that has not passed the quality check**
- **Never create a report for a simple query**
- **Never create a PowerPoint unless explicitly requested**
- **Every figure must have axis labels, a legend, and a title**
- **Sample sizes (n=) must appear on figure or caption**

### Clinical Figure Hard Rules
- **Never deliver a KM curve without an at-risk table**
- **Never report median survival when upper CI = NA** — state "Not reached"
- **Never use a linear x-axis for a forest plot** — must be log scale
- **Never omit the reference line at 1.0 on a forest plot**
- **Never report final model AUC on a ROC curve** — report CV AUC
- **Always add PH violation warning when Schoenfeld p < 0.05**
- **Always add EPV warning when EPV < 10**
- **Always include data access date on clinical trial landscape figures**
- **Always show all four MR method lines on a scatter plot**
- **Always generate a funnel plot as companion to every MR scatter plot**

## Related Skills

**Use alongside:**
- `scientific-writing` — Write figure legends, methods sections, and reports
- `scientific-audit` — Verify figure-table consistency and visualization integrity
- `literature-review` — Add citations to reports and figure captions

**Visualizes results from:**
- All analysis skills that produce data requiring visualization
