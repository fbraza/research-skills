# ANANSE Command-Line Reference

Complete reference for all ANANSE commands, parameters, and usage patterns.

---

## Overview

A full ANANSE analysis consists of 3–4 sequential steps:

```
ananse binding   →   ananse network   →   ananse influence   →   ananse plot
(per condition)      (per condition)       (pairwise)             (visualization)
```

`ananse view` is an optional utility for inspecting binding output.

---

## `ananse binding`

Predicts TF binding probabilities at enhancer regions by combining TF motif scores with ATAC-seq and/or H3K27ac ChIP-seq signal.

### Full syntax

```bash
ananse binding \
    [-A BAM [BAM ...]] \
    [-H BAM [BAM ...]] \
    [-g GENOME] \
    [-r REGIONS [REGIONS ...]] \
    [-p PFM_FILE] \
    [-R REMAP_DIR] \
    [-o OUTPUT_DIR] \
    [-c COLUMNS [COLUMNS ...]] \
    [--pfmscorefile FILE] \
    [-t TF [TF ...]] \
    [--jaccard-cutoff FLOAT] \
    [-n INT]
```

### Parameters

| Parameter | Short | Description | Default |
|---|---|---|---|
| `--atac-bams` | `-A` | ATAC-seq BAM(s) or counts table TSV | — |
| `--histone-bams` | `-H` | H3K27ac ChIP-seq BAM(s) or counts table TSV | — |
| `--genome` | `-g` | Genome name (genomepy) or FASTA path | `hg38` |
| `--regions` | `-r` | Enhancer regions BED/narrowPeak file(s) | REMAP default (hg38) |
| `--pfmfile` | `-p` | Motif PFM file | `gimme.vertebrate.v5.0` |
| `--reference` | `-R` | REMAP model directory (hg38 only) | — |
| `--outdir` | `-o` | Output directory | `./ANANSE_binding` |
| `--columns` | `-c` | Column names to extract from counts table | all |
| `--pfmscorefile` | — | Precomputed motif scores (speeds up reruns) | — |
| `--tfs` | `-t` | Filter to specific TFs | all |
| `--jaccard-cutoff` | — | Min motif similarity for model sharing | `0.1` |
| `--ncore` | `-n` | Number of CPU cores | `1` |

### Usage examples

#### hg38 with REMAP model (best accuracy)
```bash
ananse binding \
    -A source_ATAC_rep1.bam source_ATAC_rep2.bam \
    -H source_H3K27ac_rep1.bam \
    -R /data/ANANSE.REMAP.model.v1.0/ \
    -o source.binding \
    -n 8
```

#### hg38 ATAC-only (no H3K27ac)
```bash
ananse binding \
    -A source_ATAC_rep1.bam source_ATAC_rep2.bam \
    -r source_peaks.narrowPeak target_peaks.narrowPeak \
    -o source.binding \
    -n 8
```

#### Non-human genome (e.g., mouse mm10)
```bash
ananse binding \
    -A ATAC_rep1.bam ATAC_rep2.bam \
    -H H3K27ac_rep1.bam \
    -g mm10 \
    -r union_peaks.narrowPeak \
    -o source.binding \
    -n 8
```

#### Using counts tables instead of BAMs
```bash
ananse binding \
    -A atac_counts.tsv \
    -H h3k27ac_counts.tsv \
    -c source_rep1 source_rep2 \
    -R /data/ANANSE.REMAP.model.v1.0/ \
    -o source.binding \
    -n 8
```

#### Precompute motif scores (saves time on reruns with same regions)
```bash
# Precompute once
gimme scan -Tz --gc -g hg38 union_peaks.narrowPeak > motif_scores.tsv

# Use in binding
ananse binding \
    -A source_ATAC_rep1.bam \
    --pfmscorefile motif_scores.tsv \
    -o source.binding \
    -n 8
```

#### Use ENCODE cCREs as regions (alternative to REMAP)
```bash
ananse binding \
    -A source_ATAC_rep1.bam \
    -r https://api.wenglab.org/screen_v13/fdownloads/GRCh38-ccREs.bed \
    -o source.binding \
    -n 8
```

### Output

- `binding/binding.h5` — HDF5 file with TF binding probabilities per enhancer
- `binding/merged_peaks.bed` — Merged peak regions used (if multiple region files provided)

### Notes on `--regions`

- For hg38 with REMAP model: not needed (REMAP provides default regions)
- For hg38 without REMAP: provide your ATAC peaks or ENCODE cCREs
- For other genomes: always required
- **Always use the UNION of peaks from all conditions** — this ensures consistent regions across comparisons
- Do NOT use H3K27ac peaks as regions — too broad for motif scanning

---

## `ananse network`

Builds a condition-specific GRN by computing TF–gene interaction scores from binding predictions and expression data.

**⚠️ Memory requirement: ~12–15 GB RAM for human genome.**

### Full syntax

```bash
ananse network \
    BINDING_H5 \
    [-e EXPRESSION [EXPRESSION ...]] \
    [-g GENOME] \
    [-a ANNOTATION] \
    [-o OUTPUT_FILE] \
    [-t TF [TF ...]] \
    [-r REGIONS] \
    [-c COLUMN] \
    [-f] \
    [--include-promoter | --exclude-promoter] \
    [--include-enhancer | --exclude-enhancer] \
    [-n INT]
```

### Parameters

| Parameter | Short | Description | Default |
|---|---|---|---|
| `FILE` (positional) | — | `binding.h5` from `ananse binding` | required |
| `--expression` | `-e` | Expression file(s) in TPM | — |
| `--genome` | `-g` | Genome name or FASTA | `hg38` |
| `--annotation` | `-a` | Gene annotation BED12 (if not using genomepy) | — |
| `--outfile` | `-o` | Output network TSV file | `./ANANSE_network.tsv` |
| `--tfs` | `-t` | Filter to specific TFs | all |
| `--regions` | `-r` | Filter to specific regions | all |
| `--columns` | `-c` | Column name(s) from expression table | `tpm` |
| `--full-output` | `-f` | Export all 4 score components | off |
| `--include-promoter` | — | Include peaks ≤ TSS ± 2kb | included |
| `--exclude-promoter` | — | Exclude peaks ≤ TSS ± 2kb | — |
| `--include-enhancer` | — | Include peaks > TSS ± 2kb | included |
| `--exclude-enhancer` | — | Exclude peaks > TSS ± 2kb | — |
| `--ncore` | `-n` | Number of CPU cores | `1` |

### Usage examples

#### Standard (hg38, Salmon TPM files)
```bash
ananse network \
    source.binding/binding.h5 \
    -e source_rep1_TPM.txt source_rep2_TPM.txt \
    -g hg38 \
    -n 8 \
    -o source.network.tsv
```

#### Using a counts table for expression
```bash
ananse network \
    source.binding/binding.h5 \
    -e tpm_counts_table.tsv \
    -c source_rep1 source_rep2 \
    -g hg38 \
    -n 8 \
    -o source.network.tsv
```

#### Full output (all 4 score components)
```bash
ananse network \
    source.binding/binding.h5 \
    -e source_rep1_TPM.txt \
    -g hg38 \
    -f \
    -o source.network.tsv
```

#### Non-human genome with custom annotation
```bash
ananse network \
    source.binding/binding.h5 \
    -e source_TPM.txt \
    -g /path/to/genome.fa \
    -a /path/to/annotation.bed \
    -n 8 \
    -o source.network.tsv
```

### Output

- `network.tsv` — Tab-separated TF → gene interaction scores
  - Columns: `tf`, `target`, `prob` (interaction score 0–1)
  - With `-f`: additional columns `wb`, `tf_act`, `tf_expr`, `tg_expr`

### How the interaction score is computed

The `prob` score is the mean rank aggregation of four components:
1. **TF–gene binding score**: Sum of TF binding probabilities in enhancers within 100 kb of TSS, weighted by distance
2. **TF activity**: Motif activity from ridge regression on ATAC/H3K27ac signal
3. **TF expression**: TPM of the TF (ranked)
4. **Target gene expression**: TPM of the target gene (ranked)

---

## `ananse influence`

Calculates influence scores for TFs driving the transition from source → target condition.

### Full syntax

```bash
ananse influence \
    -t TARGET_NETWORK \
    -d DEGENES_FILE \
    [-s SOURCE_NETWORK] \
    [-o OUTPUT_FILE] \
    [-f] \
    [-a ANNOTATION] \
    [-i INT] \
    [-j FLOAT] \
    [-c COLUMN] \
    [-n INT]
```

### Parameters

| Parameter | Short | Description | Default |
|---|---|---|---|
| `--target` | `-t` | Target condition network TSV | required |
| `--degenes` | `-d` | DESeq2 differential expression file | required |
| `--source` | `-s` | Source condition network TSV | — |
| `--outfile` | `-o` | Output influence TSV | `./ANANSE_influence.tsv` |
| `--full-output` | `-f` | Export diffnetwork file (needed for plotting) | off |
| `--annotation` | `-a` | Gene annotation for symbol conversion | — |
| `--edges` | `-i` | Number of top edges to use | `100000` |
| `--padj` | `-j` | Adjusted p-value cutoff for DE genes | `0.05` |
| `--GRNsort-column` | `-c` | Column to sort GRN for top interactions | `prob` |
| `--ncore` | `-n` | Number of CPU cores | `1` |

### Usage examples

#### Standard pairwise comparison
```bash
ananse influence \
    -s source.network.tsv \
    -t target.network.tsv \
    -d deseq2_source_vs_target.tsv \
    -o source2target.influence.tsv \
    -f \
    -n 8
```

#### With more edges (if default results seem sparse)
```bash
ananse influence \
    -s source.network.tsv \
    -t target.network.tsv \
    -d deseq2_source_vs_target.tsv \
    -o source2target.influence.tsv \
    -i 500000 \
    -f \
    -n 8
```

#### Target-only (no source network)
```bash
ananse influence \
    -t target.network.tsv \
    -d deseq2_source_vs_target.tsv \
    -o target_only.influence.tsv \
    -f
```

### DESeq2 input file format

The file must be tab-separated with these exact columns:

```
gene          log2FoldChange    padj
ANPEP         7.44              0.001
CD24          -8.44             0.0
COL1A2        8.27              0.012
```

**Critical:** `log2FoldChange` must be **positive for genes upregulated in the TARGET condition**.

If your DESeq2 output has different column names, rename them:
```python
import pandas as pd
df = pd.read_csv("deseq2_results.csv")
df = df.rename(columns={'gene_name': 'gene', 'log2FC': 'log2FoldChange', 'adj_pval': 'padj'})
df = df.dropna(subset=['padj'])  # Remove NA padj rows
df.to_csv("degenes_for_ananse.tsv", sep='\t', index=False)
```

### Output

- `influence.tsv` — TFs ranked by influence score
- `influence_diffnetwork.tsv` — Differential GRN edges (only with `-f`)

---

## `ananse plot`

Generates a dotplot and GRN network figure from influence results.

### Full syntax

```bash
ananse plot \
    INFLUENCE_FILE \
    [-d DIFFNETWORK_FILE] \
    [-o OUTPUT_DIR] \
    [--edge-info COLUMN] \
    [--edge-min FLOAT] \
    [--node-placement ALGORITHM] \
    [--n-tfs INT] \
    [-c COLORMAP] \
    [-f] \
    [-t FILETYPE]
```

### Parameters

| Parameter | Description | Default |
|---|---|---|
| `FILE` (positional) | `influence.tsv` from `ananse influence` | required |
| `-d` | Diffnetwork file (from `ananse influence -f`) | — |
| `-o` | Output directory | `./ANANSE_plot` |
| `--n-tfs` | Number of top TFs to plot | `20` |
| `--edge-info` | Column for edge weights in GRN | `weight` |
| `--edge-min` | Minimum edge weight for GRN display | — |
| `--node-placement` | Graph layout algorithm | `neato` |
| `-c` | Matplotlib colormap | — |
| `-f` | Full output mode (for full diffnetwork) | off |
| `-t` | Output file type: `pdf`, `png`, `svg` | `pdf` |

### Usage examples

#### Standard plot
```bash
ananse plot \
    influence.tsv \
    -d influence_diffnetwork.tsv \
    -o plots/ \
    --n-tfs 20 \
    -t pdf
```

#### PNG output with custom TF count
```bash
ananse plot \
    influence.tsv \
    -d influence_diffnetwork.tsv \
    -o plots/ \
    --n-tfs 15 \
    -t png
```

---

## `ananse view`

Inspect the contents of a `binding.h5` file. Useful for QC and debugging.

### Usage examples

```bash
# List all TFs in the binding file
ananse view binding.h5 -lt

# List all regions
ananse view binding.h5 -lr

# Preview first 10 regions and TFs
ananse view binding.h5 -n 10

# Extract binding probabilities for specific TFs (long format)
ananse view binding.h5 -t TP53 TP63 FOXA1 -F long -o tp53_binding.tsv

# Export full binding matrix (warning: large file)
ananse view binding.h5 -o full_binding.tsv
```

### Parameters

| Parameter | Description | Default |
|---|---|---|
| `FILE` (positional) | `binding.h5` from `ananse binding` | required |
| `-o` | Output TSV file | stdout |
| `-t` | TF(s) to display | all |
| `-r` | Region(s) to display | all |
| `-F` | Format: `wide` or `long` | `wide` |
| `-n` | Number of regions/TFs to display | all |
| `-lr` | List regions | — |
| `-lt` | List TFs | — |

---

## Complete Pipeline Example

```bash
conda activate ananse

# 1. Binding (run once per condition)
ananse binding \
    -H ANANSE_example_data/H3K27ac/fibroblast*bam \
    -A ANANSE_example_data/ATAC/fibroblast*bam \
    -R ANANSE.REMAP.model.v1.0/ \
    -o fibroblast.binding -n 8

ananse binding \
    -H ANANSE_example_data/H3K27ac/heart*bam \
    -A ANANSE_example_data/ATAC/heart*bam \
    -R ANANSE.REMAP.model.v1.0/ \
    -o heart.binding -n 8

# 2. Network (run once per condition)
ananse network fibroblast.binding/binding.h5 \
    -e ANANSE_example_data/RNAseq/fibroblast*TPM.txt \
    -g hg38 -n 8 -o fibroblast.network.tsv

ananse network heart.binding/binding.h5 \
    -e ANANSE_example_data/RNAseq/heart*TPM.txt \
    -g hg38 -n 8 -o heart.network.tsv

# 3. Influence (pairwise)
ananse influence \
    -s fibroblast.network.tsv \
    -t heart.network.tsv \
    -d ANANSE_example_data/RNAseq/fibroblast2heart_degenes.csv \
    -o fibroblast2heart.influence.tsv \
    -f -n 8

# 4. Plot
ananse plot fibroblast2heart.influence.tsv \
    -d fibroblast2heart.influence_diffnetwork.tsv \
    -o plots/ --n-tfs 20 -t pdf
```
