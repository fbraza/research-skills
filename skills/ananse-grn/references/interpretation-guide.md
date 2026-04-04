# ANANSE Result Interpretation Guide

---

## Understanding the Influence Score

The influence score is the primary output of ANANSE. It ranks TFs by how much their regulatory program explains the transcriptional difference between source and target conditions.

### Score components

For each TF, the influence score integrates:

1. **Differential network activity**: How much the TF's regulatory edges differ between source and target GRNs
2. **Network propagation**: Influence propagated through up to 3 edges in the differential GRN
3. **Target gene expression changes**: Whether the TF's predicted targets are differentially expressed

### Score range and interpretation

| Influence score | Interpretation |
|---|---|
| > 0.8 | Very high — likely a master regulator of the transition |
| 0.5–0.8 | High — important regulatory role |
| 0.2–0.5 | Moderate — contributing factor |
| < 0.2 | Low — limited regulatory role in this transition |

**Key insight from the paper:** The top 4–10 TFs by influence score recover ~57% of experimentally validated trans-differentiation factors. Focus your validation efforts on the top 10–20 TFs.

---

## Influence Output File (`influence.tsv`)

### Column descriptions

| Column | Description |
|---|---|
| `factor` | TF name (HGNC symbol) |
| `influence_score` | Final influence score (0–1); higher = more important |
| `tf_expression_score` | TF expression change (source → target); positive = upregulated in target |
| `target_score` | How well TF's targets explain the expression differences |
| `n_targets` | Number of target genes in the differential network |

### With `--full-output` flag, additional columns:

| Column | Description |
|---|---|
| `wb_diff` | Binding score difference (target − source) |
| `tf_act_diff` | TF activity difference |
| `tf_expr_diff` | TF expression difference |
| `tg_expr_diff` | Mean target gene expression difference |

---

## Interpreting Top TFs

### What to expect

- **Known master regulators** of the target cell type/condition should appear in the top 10
- **Pioneer factors** (e.g., FOXA1, GATA3) may rank high even with modest expression changes — they remodel chromatin
- **Housekeeping TFs** (e.g., SP1, KLF4) appearing at the very top may indicate a data quality issue

### Patterns to look for

**High influence + high expression change:**
→ Classic master regulator — TF is both upregulated and drives target gene expression

**High influence + low expression change:**
→ Possible pioneer factor or post-translational regulation — TF activity changes without large mRNA change

**Low influence + high expression change:**
→ TF is differentially expressed but not a major network driver — may be a downstream effector

**All top TFs are housekeeping factors:**
→ Warning sign — check expression normalization, peak quality, or log2FC direction

---

## Network Output File (`network.tsv`)

### Column descriptions

| Column | Description |
|---|---|
| `tf` | Transcription factor name |
| `target` | Target gene name |
| `prob` | Interaction score (0–1); higher = stronger predicted interaction |

### How to use the network

```python
import pandas as pd

# Load network
network = pd.read_csv("target.network.tsv", sep='\t')

# Get top targets for a specific TF
tf_targets = network[network['tf'] == 'GATA4'].sort_values('prob', ascending=False)
print(tf_targets.head(20))

# Get top TFs for a specific gene
gene_regulators = network[network['target'] == 'MYH7'].sort_values('prob', ascending=False)
print(gene_regulators.head(10))

# Filter to high-confidence interactions
high_conf = network[network['prob'] > 0.5]
print(f"High-confidence interactions: {len(high_conf)}")
```

---

## Validating Results

### Biological validation approaches

1. **Literature check**: Are top TFs known regulators of the target cell type/condition?
2. **ChIP-seq overlap**: Do predicted TF binding sites overlap with published ChIP-seq peaks?
3. **Perturbation experiments**: Knock out/overexpress top TFs and check if target gene expression changes
4. **Motif enrichment**: Run HOMER or MEME on ATAC peaks and compare enriched motifs with top TFs

### Computational validation

```python
import pandas as pd

# Load influence results
influence = pd.read_csv("influence.tsv", sep='\t')
top_tfs = influence.nlargest(20, 'influence_score')

# Compare with known TFs from literature
known_tfs = ['GATA4', 'MEF2C', 'TBX5', 'HAND2', 'MYOCD']  # Example: cardiac TFs
recovered = [tf for tf in known_tfs if tf in top_tfs['factor'].values]
print(f"Recovered {len(recovered)}/{len(known_tfs)} known TFs in top 20")
print(f"Recovered: {recovered}")

# Check rank of known TFs
for tf in known_tfs:
    rank = influence[influence['factor'] == tf].index
    if len(rank) > 0:
        print(f"{tf}: rank {rank[0]+1} / {len(influence)}")
```

---

## Differential GRN Analysis

The `influence_diffnetwork.tsv` file contains the differential GRN edges used to compute influence scores.

### Exploring the differential network

```python
import pandas as pd
import networkx as nx

# Load diffnetwork
diffnet = pd.read_csv("influence_diffnetwork.tsv", sep='\t')

# Build networkx graph for top TFs
top_tfs = ['GATA4', 'MEF2C', 'TBX5']
subnet = diffnet[diffnet['tf'].isin(top_tfs)]

G = nx.from_pandas_edgelist(subnet, source='tf', target='target', edge_attr='weight')
print(f"Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}")

# Find shared targets between top TFs
tf1_targets = set(diffnet[diffnet['tf'] == 'GATA4']['target'])
tf2_targets = set(diffnet[diffnet['tf'] == 'MEF2C']['target'])
shared = tf1_targets & tf2_targets
print(f"Shared targets between GATA4 and MEF2C: {len(shared)}")
```

---

## Multi-Condition Comparison

When running ANANSE on multiple pairwise comparisons (e.g., time-course), compare influence scores across comparisons:

```python
import pandas as pd

# Load multiple influence results
t0_t6 = pd.read_csv("T0_T6.influence.tsv", sep='\t').rename(columns={'influence_score': 'T0_T6'})
t0_t24 = pd.read_csv("T0_T24.influence.tsv", sep='\t').rename(columns={'influence_score': 'T0_T24'})
t6_t24 = pd.read_csv("T6_T24.influence.tsv", sep='\t').rename(columns={'influence_score': 'T6_T24'})

# Merge
merged = t0_t6[['factor', 'T0_T6']].merge(
    t0_t24[['factor', 'T0_T24']], on='factor'
).merge(
    t6_t24[['factor', 'T6_T24']], on='factor'
)

# TFs consistently high across all comparisons = sustained regulators
merged['mean_influence'] = merged[['T0_T6', 'T0_T24', 'T6_T24']].mean(axis=1)
print(merged.sort_values('mean_influence', ascending=False).head(10))

# TFs high only at early timepoint = early response regulators
early_specific = merged[(merged['T0_T6'] > 0.5) & (merged['T6_T24'] < 0.2)]
print(f"\nEarly-specific TFs: {early_specific['factor'].tolist()}")
```

---

## Common Result Patterns and Their Meaning

| Pattern | Likely explanation | Action |
|---|---|---|
| Top TFs are known master regulators | ✅ Analysis working correctly | Validate top 5–10 experimentally |
| Top TFs are all housekeeping factors (SP1, KLF4, etc.) | Data quality issue or wrong direction | Check log2FC direction; check peak quality |
| Very few TFs with high scores (<5 above 0.5) | Subtle transition or low DE gene count | Relax padj cutoff; increase edges to 500k |
| Many TFs with similar scores | Broad regulatory rewiring | Focus on top 10; check if transition is complex |
| Known TF missing from top results | TF lacks motif or is post-translationally regulated | Check `ananse view -lt`; consider complementary methods |
| Influence score and expression change disagree | TF acts through chromatin remodeling | Investigate as pioneer factor |
