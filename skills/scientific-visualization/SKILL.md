---
name: scientific-visualization
description: Standards and protocols for scientific visualization and reporting. Covers figure type specifications (volcano, heatmap, UMAP, KM curve, forest plot, ROC, enrichment plots, etc.), color standards (Okabe-Ito palette, colorblind accessibility), export standards (SVG + PNG, 300+ DPI), clinical figure standards (at-risk tables, PH violation warnings, CV AUC reporting), publication figure sizing (Nature/Science/Cell column widths), multi-panel composites, mandatory quality checks, report structure, PowerPoint, and LaTeX Beamer slides.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
starting-prompt: Create publication-ready visualizations of my analysis results with colorblind-friendly palettes.
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
- ❌ Searching literature — use `literature`
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

| Figure type | Python tool | R tool | Reference |
|---|---|---|---|
| Volcano plot | ultraplot | ggplot2 | `references/volcano_plot.md` |
| Heatmap | ultraplot | ComplexHeatmap | `references/heatmap.md` |
| UMAP / tSNE | ultraplot | ggplot2 | `references/umap_tsne.md` |
| PCA plot | ultraplot | ggplot2 | `references/pca_plot.md` |
| Enrichment dot plot | ultraplot | ggplot2 / enrichplot | `references/enrichment_dotplot.md` |
| Forest plot (HR/OR) | ultraplot | ggplot2 | `references/forest_plot.md` |
| Box / violin plot | ultraplot | ggplot2 + ggprism | `references/box_violin_plot.md` |
| Bar + error bars | ultraplot | ggplot2 | `references/histogram_error_bars.md` |
| Jitter / grouped plots | ultraplot | ggplot2 | `references/grouped_plots.md` |
| Kaplan-Meier | lifelines + ultraplot | survminer | — |
| ROC curve | sklearn + ultraplot | pROC | — |
| Calibration curve | sklearn + ultraplot | val.prob | — |
| Network | networkx + ultraplot | igraph | — |

## Visualization Standards

### Libraries

**Publication figures:**
- **Python:** ultraplot (primary) — a succinct matplotlib wrapper for publication-quality graphics
- **R:** ggplot2 + ggprism theme (primary), ComplexHeatmap for heatmaps

**Exploratory analysis (EDA):** Built-in plotting from scanpy, Seurat, or seaborn is fine. For final publication figures, always use ultraplot (Python) or ggplot2 (R).

**Style inspiration:** Before generating a figure, check `assets/` for user-provided reference images of preferred plot styles. Match the visual feel when possible.

### UltraPlot Conventions (Python)

UltraPlot is a matplotlib wrapper — the `ax` object inherits all matplotlib methods plus `ax.format()` for concise styling.

```python
import ultraplot as uplt
import matplotlib as mpl

# MANDATORY: preserve editable text in SVG (not individual glyphs)
mpl.rcParams['svg.fonttype'] = 'none'

# Publication RC defaults
uplt.rc.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica'],
    'font.size': 8,
    'axes.labelsize': 9,
    'xtick.labelsize': 7,
    'ytick.labelsize': 7,
    'axes.titlesize': 9,
})

# Single figure (no multi-panel — compose in Illustrator)
fig, ax = uplt.subplot(figsize=(3.5, 3))  # Nature single column

# Style with format() — NOT raw matplotlib calls
ax.format(
    xlabel='PC1 (45.2% variance)',
    ylabel='PC2 (12.1% variance)',
    title='PCA — Treatment vs Control',
)

# Save both formats
fig.savefig('./results/figure_name.svg', bbox_inches='tight')
fig.savefig('./results/figure_name.png', dpi=300, bbox_inches='tight')
```

**Key rules:**
- Always use `uplt.subplot()` for single figures — no `plt.subplots()` or gridspec
- Always use `ax.format()` for axis labels, titles, limits — not `ax.set_xlabel()` etc.
- Each plot is a standalone figure — no multi-panel composites (user assembles in Illustrator)
- Read the reference file for each plot type before implementing (see Tool Selection table above)

### Color Standards

**Always use colorblind-friendly palettes.** Never use red/green only. Never use rainbow/jet.

**Categorical palettes:**
```python
# Publication palette (default for embeddings and multi-category plots)
# Muted earthy tones — warm, distinguishable, Nature/Cell aesthetic
PUBLICATION_PALETTE = [
    '#3A5BA0', '#D4753C', '#5A8F5A', '#C44E52', '#8C6D31',
    '#7B5EA7', '#E8A838', '#46878F', '#B07AA1', '#86714D',
    '#4E9A9A', '#D98880', '#6B8E23', '#B8860B', '#708090',
    '#9B59B6', '#2E86C1', '#D35400', '#1ABC9C', '#8B4513',
]

# Okabe-Ito (fallback for accessibility-critical contexts)
OKABE_ITO = ['#E69F00', '#56B4E9', '#009E73', '#F0E442',
             '#0072B2', '#D55E00', '#CC79A7', '#000000']
```

**Sequential colormaps:**
- Gene expression / feature plots: `magma` (dark → orange → yellow)
- Generic continuous metrics: `viridis`

**Diverging colormaps:**
- Fold change, correlation: `RdBu_r` or `coolwarm` — always symmetric around zero

```r
# R categorical
library(RColorBrewer)
palette <- brewer.pal(8, "Set2")

# R diverging
scale_fill_gradient2(low = "blue", mid = "white", high = "red", midpoint = 0)
```

- Maximum 20 distinct colors for categorical data (publication palette) — use grouping if more needed
- For diverging data: blue-white-red or similar, symmetric around zero
- For sequential data: magma (expression) or viridis (generic)

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
- **SVG text preservation:** Always set `mpl.rcParams['svg.fonttype'] = 'none'` before saving. This ensures text is embedded as editable `<text>` elements in SVG — not converted to individual letter paths/glyphs. This is critical for downstream editing in Illustrator.
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

Typography is configured via `uplt.rc.update()` in the UltraPlot Conventions section above. Do not use raw `mpl.rcParams` for font settings — use ultraplot's RC system instead.

Axis labels: sentence case with units — `"Time (hours)"` not `"TIME (HOURS)"`.

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

### UMAP / tSNE / Embeddings
- **L-shaped axis stubs** only (no full frame, no ticks, no tick numbers) — embedding coordinates are arbitrary
- Point size auto-scales with cell count (more cells → smaller dots, fewer cells → larger dots)
- **Fully opaque** (`alpha=1.0`) with darkened edge contours on every point
- **Legend only** — no text labels on the plot, keep it clean
- Publication palette (muted earthy tones) by default
- Feature plots use `magma` colormap with "Min"/"Max" colorbar labels, gene name in *italics*
- n_neighbors (UMAP) or perplexity (tSNE) stated in caption
- See `references/umap_tsne.md` for full aesthetic rules and implementation

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
import matplotlib as mpl
mpl.rcParams['svg.fonttype'] = 'none'  # editable text in SVG
fig.savefig("./results/figure_name.svg", bbox_inches="tight")
fig.savefig("./results/figure_name.png", dpi=300, bbox_inches="tight")
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
- **Always set `mpl.rcParams['svg.fonttype'] = 'none'` before saving SVG — text must be editable, not individual letter paths**
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
- `literature` — Add citations to reports and figure captions

**Visualizes results from:**
- All analysis skills that produce data requiring visualization
