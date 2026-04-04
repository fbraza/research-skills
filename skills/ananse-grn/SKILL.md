---
name: ananse-grn
description: ANANSE (ANalysis Algorithm for Networks Specified by Enhancers) infers enhancer-based gene regulatory networks (GRNs) from paired bulk ATAC-seq and RNA-seq data, and identifies key transcription factors (TFs) driving transitions between two biological conditions. It predicts TF binding from chromatin accessibility and motif scores, builds condition-specific GRNs, and ranks TFs by their influence on the transcriptional difference between source and target states. Use when you have paired bulk ATAC-seq + RNA-seq across 2+ conditions and want to identify master regulatory TFs. Works natively on bulk data with as few as 1 sample per condition. Requires ~16GB RAM for the network step. No GPU needed.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
starting-prompt: Infer gene regulatory networks and identify key transcription factors from my paired bulk ATAC-seq and RNA-seq data.
---

# ANANSE: Enhancer-Based Gene Regulatory Network Inference

Infer enhancer-driven GRNs and identify key transcription factors from paired bulk ATAC-seq and RNA-seq data using ANANSE.

## When to Use This Skill

Use ANANSE when you need to:
- ✅ **Identify master TFs** driving a biological transition (treatment vs. control, differentiation, timepoints)
- ✅ **Build condition-specific GRNs** from bulk paired ATAC-seq + RNA-seq
- ✅ **Work with small N** — ANANSE works with as few as 1 sample per condition (unlike co-expression methods)
- ✅ **Enhancer-resolution** TF-target inference (not just promoter-based)
- ✅ **Predict trans-differentiation factors** for cell reprogramming experiments

**Don't use this skill for:**
- ❌ RNA-seq only (no ATAC-seq) → Use `functional-enrichment-from-degs` or `upstream-regulator-analysis`
- ❌ Single-cell data → Use `grn-pyscenic` (SCENIC+) instead
- ❌ Co-expression modules → Use `coexpression-network` (WGCNA)
- ❌ Non-paired data (ATAC and RNA from different samples) → Results will be unreliable

**Key Concept:** ANANSE integrates TF motif scores, chromatin accessibility (ATAC-seq), and gene expression (RNA-seq) to predict which TFs are bound at active enhancers and regulate target genes. The influence score ranks TFs by how much their regulatory program explains the transcriptional difference between two conditions.

**The ANANSE Pipeline:**
1. **`ananse binding`**: Predict TF binding probabilities at enhancers from ATAC-seq + motifs
2. **`ananse network`**: Build a condition-specific GRN (TF → gene interaction scores)
3. **`ananse influence`**: Rank TFs by their influence on the source → target transition
4. **`ananse plot`**: Visualize top TFs as dotplot and GRN network figure

## Quick Start

**Fastest way to test the workflow (~30 min with example data):**

```python
# Step 1: Download example data and set up
from scripts.load_example_data import setup_example_data
paths = setup_example_data(output_dir="ananse_example")

# Step 2: Run complete workflow (fibroblast → heart)
from scripts.run_full_workflow import run_full_ananse_workflow
results = run_full_ananse_workflow(
    source_atac_bams=paths['source_atac'],
    source_rna_tpm=paths['source_rna'],
    target_atac_bams=paths['target_atac'],
    target_rna_tpm=paths['target_rna'],
    degenes_file=paths['degenes'],
    output_dir="ananse_results",
    genome="hg38",
    remap_dir=paths['remap_model'],
    n_cores=8
)

# Step 3: Plot results
from scripts.plot_results import plot_influence_results
plot_influence_results(
    influence_file=results['influence_file'],
    diffnetwork_file=results['diffnetwork_file'],
    output_dir="ananse_results/plots",
    n_tfs=20
)
```

**Expected output:** Top 20 TFs ranked by influence score, dotplot + GRN network figure.

**Note:** Requires ANANSE conda environment and REMAP model download first (see Installation).

## Installation

### Required Software

| Software | Version | License | Commercial Use | Installation |
|----------|---------|---------|----------------|--------------|
| ANANSE | ≥0.4.0 | MIT | ✅ Permitted | `conda create -n ananse ananse` |
| GimmeMotifs | ≥0.17 | MIT | ✅ Permitted | Installed with ANANSE |
| genomepy | ≥0.14 | MIT | ✅ Permitted | Installed with ANANSE |
| samtools | ≥1.12 | MIT | ✅ Permitted | Installed with ANANSE |

**Minimum system requirements:**
- RAM: 16 GB (32 GB recommended)
- CPU: 4 cores (8 recommended)
- Disk: 50 GB free (genome + REMAP model + intermediate files)
- OS: Linux or macOS (Windows via WSL2)
- No GPU required

### Install ANANSE (conda — recommended)

```bash
# Add channels (once only)
conda config --add channels bioconda
conda config --add channels conda-forge

# Create dedicated environment
conda create -n ananse ananse

# Activate before every use
conda activate ananse
```

### Install genome (required)

```bash
conda activate ananse

# Human (hg38) — most common
genomepy install hg38 --annotation

# Mouse (mm10)
genomepy install mm10 --annotation

# Other species (example: zebrafish)
genomepy install GRCz11 --provider Ensembl --annotation
```

### Download REMAP model (hg38 only — strongly recommended)

Significantly improves binding prediction accuracy by incorporating average ChIP-seq signal from REMAP. Only available for hg38.

```bash
DATA_DIR=/path/to/data
mkdir -p $DATA_DIR/ANANSE.REMAP.model.v1.0
cd $DATA_DIR/ANANSE.REMAP.model.v1.0
wget https://zenodo.org/record/4768075/files/ANANSE.REMAP.model.v1.0.tgz
tar xvzf ANANSE.REMAP.model.v1.0.tgz
rm ANANSE.REMAP.model.v1.0.tgz
```

### For non-human/mouse species: generate motif database

```bash
conda activate ananse
gimme motif2factors --new-reference GRCz11 --outdir zebrafish_motifs
```

**See [references/database-setup.md](references/database-setup.md) for full setup instructions including example data download.**

## Inputs

### Required Input Files

1. **ATAC-seq data** (per condition, one of):
   - Sorted, indexed BAM file(s): `sample_ATAC_rep1.bam`, `sample_ATAC_rep1.bam.bai`
   - Counts table (TSV): peaks × samples with raw read counts

2. **RNA-seq expression** (per condition, one of):
   - Salmon `quant.sf` or kallisto `abundances.tsv` (TPM column)
   - Counts table (TSV): genes × samples with TPM values

3. **Differential expression** (for `ananse influence`):
   - DESeq2 output TSV with columns: `gene`, `log2FoldChange`, `padj`
   - `log2FoldChange` must be **positive for genes upregulated in the TARGET condition**

4. **Genome**: hg38 (built-in) or custom FASTA + BED12 annotation

5. **Enhancer regions** (optional for hg38 with REMAP; required otherwise):
   - BED or narrowPeak file(s) from MACS2 ATAC-seq peak calling

### Optional: H3K27ac ChIP-seq

Adding H3K27ac BAMs improves binding prediction (PR AUC ~0.28 ATAC-only vs ~0.38 with both).

### Data Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| Samples per condition | 1 | 2–3 replicates |
| ATAC-seq depth | 20M reads | 40M+ reads |
| RNA-seq depth | 10M reads | 30M+ reads |
| Peak calling | MACS2 narrowPeak | MACS2 with `--shift -100 --extsize 200 --nomodel` |
| BAM files | Sorted + indexed | Duplicates marked/removed |

## Outputs

### Files Generated

**Binding prediction:**
- `source.binding/binding.h5` — TF binding probabilities per enhancer (HDF5, one per condition)

**GRN networks:**
- `source.network.tsv` — TF → gene interaction scores for source condition
- `target.network.tsv` — TF → gene interaction scores for target condition

**Influence results:**
- `influence.tsv` — TFs ranked by influence score (0–1)
- `influence_diffnetwork.tsv` — Differential GRN edges (required for plotting)

**Visualizations:**
- `plots/influence_dotplot.pdf` — Top TFs ranked by influence score
- `plots/grn_network.pdf` — GRN of top TF interactions

**Exported tables:**
- `results/top_tfs.csv` — Top TFs with influence scores and expression changes
- `results/network_source.csv` — Full source GRN (human-readable)
- `results/network_target.csv` — Full target GRN (human-readable)

## Clarification Questions

**Before running, confirm:**

1. **Input Files** (ASK THIS FIRST):
   - Do you have paired ATAC-seq and RNA-seq for at least 2 conditions?
   - Are BAM files sorted and indexed?
   - What format is your RNA-seq expression data (Salmon quant.sf, kallisto, counts table)?
   - **Or use example data?** Use `load_example_data.py` for fibroblast→heart (~30 min test)

2. **Species?**
   - Human (hg38) — best supported, REMAP model available
   - Mouse (mm10) — supported, no REMAP model
   - Other — requires custom motif database generation

3. **Do you have H3K27ac ChIP-seq?**
   - Yes → Provide BAMs alongside ATAC-seq for better accuracy
   - No → ATAC-seq alone works well

4. **Comparison direction?**
   - Which condition is the SOURCE (baseline/control/timepoint 0)?
   - Which condition is the TARGET (treated/differentiated/timepoint N)?
   - Confirm: `log2FoldChange` in DESeq2 output is positive for genes upregulated in TARGET

5. **Genome?**
   - hg38 → Use REMAP model for best accuracy
   - Other → Confirm genomepy genome name or provide FASTA + BED12

## Standard Workflow

🚨 **MANDATORY: USE SCRIPTS EXACTLY AS SHOWN - DO NOT WRITE INLINE SHELL COMMANDS** 🚨

**Step 1 — Set up and load data:**
```python
# Option A: Use example data (fibroblast → heart)
from scripts.load_example_data import setup_example_data
paths = setup_example_data(output_dir="ananse_example")

# Option B: Use your own data
paths = {
    'source_atac': ['source_ATAC_rep1.bam', 'source_ATAC_rep2.bam'],
    'source_h3k27ac': ['source_H3K27ac_rep1.bam'],   # optional
    'source_rna': ['source_rep1_TPM.txt', 'source_rep2_TPM.txt'],
    'target_atac': ['target_ATAC_rep1.bam', 'target_ATAC_rep2.bam'],
    'target_h3k27ac': ['target_H3K27ac_rep1.bam'],   # optional
    'target_rna': ['target_rep1_TPM.txt', 'target_rep2_TPM.txt'],
    'degenes': 'deseq2_source_vs_target.tsv',
    'remap_model': '/path/to/ANANSE.REMAP.model.v1.0'
}
```

**Step 2 — Run TF binding prediction (per condition):**
```python
from scripts.run_binding import run_ananse_binding
run_ananse_binding(
    atac_bams=paths['source_atac'],
    h3k27ac_bams=paths.get('source_h3k27ac'),   # None if not available
    output_dir="source.binding",
    genome="hg38",
    remap_dir=paths.get('remap_model'),
    n_cores=8
)
run_ananse_binding(
    atac_bams=paths['target_atac'],
    h3k27ac_bams=paths.get('target_h3k27ac'),
    output_dir="target.binding",
    genome="hg38",
    remap_dir=paths.get('remap_model'),
    n_cores=8
)
```
**✅ VERIFICATION:** You should see `"✓ ananse binding completed: source.binding/binding.h5"` and `"✓ ananse binding completed: target.binding/binding.h5"`

**Step 3 — Infer GRNs (per condition):**
```python
from scripts.run_network import run_ananse_network
run_ananse_network(
    binding_h5="source.binding/binding.h5",
    expression_files=paths['source_rna'],
    output_file="source.network.tsv",
    genome="hg38",
    n_cores=8
)
run_ananse_network(
    binding_h5="target.binding/binding.h5",
    expression_files=paths['target_rna'],
    output_file="target.network.tsv",
    genome="hg38",
    n_cores=8
)
```
**⚠️ Memory warning:** This step requires ~12–15 GB RAM. Ensure sufficient memory before running.

**✅ VERIFICATION:** You should see `"✓ ananse network completed: source.network.tsv"` and `"✓ ananse network completed: target.network.tsv"`

**Step 4 — Calculate influence scores:**
```python
from scripts.run_influence import run_ananse_influence
run_ananse_influence(
    source_network="source.network.tsv",
    target_network="target.network.tsv",
    degenes_file=paths['degenes'],
    output_file="influence.tsv",
    n_edges=100000,
    padj_cutoff=0.05,
    n_cores=8
)
```
**✅ VERIFICATION:** You should see `"✓ ananse influence completed: influence.tsv"` and `"✓ ananse influence completed: influence_diffnetwork.tsv"`

**Step 5 — Plot and export results:**
```python
from scripts.plot_results import plot_influence_results
from scripts.export_results import export_ananse_results

plot_influence_results(
    influence_file="influence.tsv",
    diffnetwork_file="influence_diffnetwork.tsv",
    output_dir="plots",
    n_tfs=20
)

export_ananse_results(
    influence_file="influence.tsv",
    source_network="source.network.tsv",
    target_network="target.network.tsv",
    output_dir="results"
)
```
**✅ VERIFICATION:** You should see `"=== ANANSE Export Complete ==="` with list of output files.

⚠️ **CRITICAL — DO NOT:**
- ❌ **Write inline `subprocess` calls to ananse commands** → Use the scripts
- ❌ **Skip the binding step** and go directly to network → binding.h5 is required
- ❌ **Use H3K27ac peaks as `--regions`** → Too broad; use ATAC peaks or ENCODE cCREs
- ❌ **Swap source/target direction** → Verify log2FC sign in DESeq2 file before running
- ❌ **Run network step without checking RAM** → Will crash silently if <12 GB available

**⚠️ IF SCRIPTS FAIL — Script Failure Hierarchy:**
1. **Fix and Retry (90%)** — Install missing package, check BAM indexing, re-run script
2. **Modify Script (5%)** — Edit the script file itself, document changes
3. **Use as Reference (4%)** — Read script, adapt approach, cite source
4. **Write from Scratch (1%)** — Only if genuinely impossible, explain why

**NEVER skip directly to writing inline code without trying the script first.**

## Decision Points

### Decision 1: ATAC-only vs ATAC + H3K27ac

**When:** Before running `ananse binding`

| Data available | PR AUC (paper benchmark) | Recommendation |
|---|---|---|
| ATAC-seq only | ~0.28 | Use `-A` only |
| H3K27ac only | ~0.25 | Use `-H` with external regions |
| ATAC + H3K27ac | ~0.38 | **Best — use both** |
| ATAC + H3K27ac + REMAP (hg38) | ~0.45 | **Best for human** |

### Decision 2: Enhancer regions source

**When:** Before running `ananse binding` for non-hg38 or without REMAP

| Option | When to use |
|---|---|
| REMAP model (`-R`) | hg38 only — best accuracy |
| Your ATAC peaks (union) | Any genome — use union of all conditions |
| ENCODE cCREs | hg38/mm10 — good alternative to REMAP |
| Custom BED | Any genome — if you have curated enhancer set |

**See [references/cli-reference.md](references/cli-reference.md) for `--regions` parameter details.**

### Decision 3: Number of edges for influence

**When:** Running `ananse influence`

| `-i` value | Use case |
|---|---|
| 100,000 (default) | Standard — robust for most analyses |
| 500,000 | Sparse results with default — try if top TFs seem unexpected |
| 1,000,000 | Not recommended — performance decreases |

**See [references/interpretation-guide.md](references/interpretation-guide.md) for guidance on evaluating results.**

## Common Issues

| Error | Cause | Solution |
|---|---|---|
| `binding.h5 not found` | Binding step failed silently | Check ANANSE conda env is active; check BAM files are indexed |
| Empty or tiny network | Gene symbol mismatch | Ensure expression file uses HGNC symbols; use genomepy for auto-conversion |
| Unexpected top TFs | Wrong log2FC direction | Verify log2FC is **positive for TARGET upregulated genes** |
| OOM crash in network step | Insufficient RAM | Ensure ≥16 GB free RAM; close other processes; use `-n 1` |
| `No regions found` | Missing `--regions` for non-hg38 | Provide ATAC narrowPeak file(s) with `-r` |
| `Gene annotation error` | Genome not installed via genomepy | Run `genomepy install hg38 --annotation` |
| `TF not in results` | TF lacks motif in database | Check with `ananse view binding.h5 -lt`; use `--jaccard-cutoff 0.2` |
| `padj NaN` in influence | NA values in DESeq2 output | Filter `padj` NA rows before passing to influence |
| No diffnetwork file | Forgot `-f` flag | Re-run influence with `-f` / `--full-output` flag |
| Poor binding prediction | No REMAP model (hg38) | Download and use `-R ANANSE.REMAP.model.v1.0/` |

**See [references/troubleshooting.md](references/troubleshooting.md) for detailed solutions.**

## Interpreting Results

### Influence score (`influence.tsv`)

| Column | Description |
|---|---|
| `factor` | TF name (HGNC symbol) |
| `influence_score` | 0–1; **higher = more important** for the transition |
| `tf_expression_score` | TF expression change (source → target) |
| `target_score` | How well TF targets explain expression differences |

**What to expect:**
- Top 4–10 TFs typically capture most validated regulatory factors (paper benchmark: 57% recovery in top 4)
- TFs with high influence but low expression change may be pioneer factors
- Cross-reference top TFs with known biology of your system

**See [references/interpretation-guide.md](references/interpretation-guide.md) for detailed guidance.**

## Experimental Design Considerations

### Multi-condition experiments (>2 conditions)

Run pairwise comparisons. `binding` and `network` steps only need to run **once per condition** — reuse outputs across comparisons.

For a time-course T0 → T6 → T24:
```
# Run binding + network once per timepoint
ananse binding ... -o T0.binding
ananse binding ... -o T6.binding
ananse binding ... -o T24.binding
ananse network T0.binding/binding.h5 ... -o T0.network.tsv
ananse network T6.binding/binding.h5 ... -o T6.network.tsv
ananse network T24.binding/binding.h5 ... -o T24.network.tsv

# Run influence for each pairwise comparison
ananse influence -s T0.network.tsv -t T6.network.tsv  ...
ananse influence -s T0.network.tsv -t T24.network.tsv ...
ananse influence -s T6.network.tsv -t T24.network.tsv ...
```

### Peak calling recommendations

```bash
# ATAC-seq peak calling with MACS2
macs2 callpeak \
    -t sample_ATAC.bam \
    -f BAMPE \
    --nomodel \
    --shift -100 \
    --extsize 200 \
    --keep-dup all \
    -n sample_ATAC \
    --outdir peaks/

# Always use UNION of peaks across all conditions for --regions
cat condition1_peaks.narrowPeak condition2_peaks.narrowPeak | \
    sort -k1,1 -k2,2n | \
    bedtools merge > union_peaks.bed
```

## Suggested Next Steps

After completing ANANSE analysis:

1. **Validate top TFs**: Cross-reference with ChIP-seq data, literature, or perturbation experiments
2. **Functional enrichment of TF targets**: Use `functional-enrichment-from-degs` on target genes of top TFs
3. **Upstream regulator analysis**: Use `upstream-regulator-analysis` to complement ANANSE results
4. **Differential expression context**: Overlay influence scores with DESeq2 results
5. **scANANSE**: If you have single-cell data, use the scANANSE extension for cell-cluster-level GRNs

## Related Skills

- **grn-pyscenic** — Alternative: single-cell GRN inference (requires scRNA-seq, 500+ cells)
- **functional-enrichment-from-degs** — Downstream: pathway analysis of TF target genes
- **upstream-regulator-analysis** — Complementary: TF activity from expression data alone
- **bulk-rnaseq-counts-to-de-deseq2** — Upstream: generate the DESeq2 file needed for `ananse influence`
- **coexpression-network** — Alternative: co-expression modules (requires ≥15 samples)

## References

- Xu Q, Georgiou G, Frölich S, van der Sande M, Veenstra GJC, Zhou H, van Heeringen SJ. ANANSE: an enhancer network-based computational approach for predicting key transcription factors in cell fate determination. *Nucleic Acids Research* 2021;49(14):7966–7985. [doi:10.1093/nar/gkab598](https://doi.org/10.1093/nar/gkab598)
- Heuts BMH et al. Identification of transcription factors dictating blood cell development using a bidirectional transcription network-based computational framework. *Scientific Reports* 2022;12:1–12. [doi:10.1038/s41598-022-21148-w](https://doi.org/10.1038/s41598-022-21148-w) *(CAGE-seq extension)*
- ANANSE documentation: https://anansepy.readthedocs.io/en/master/
- ANANSE GitHub: https://github.com/vanheeringen-lab/ANANSE

**Detailed references:**
- [references/cli-reference.md](references/cli-reference.md) — Full command-line parameter reference
- [references/database-setup.md](references/database-setup.md) — Genome and REMAP model setup
- [references/troubleshooting.md](references/troubleshooting.md) — Comprehensive error solutions
- [references/interpretation-guide.md](references/interpretation-guide.md) — Result interpretation and validation

**Scripts:**
- [scripts/load_example_data.py](scripts/load_example_data.py) — Download and set up example data
- [scripts/run_binding.py](scripts/run_binding.py) — `ananse binding` wrapper with validation
- [scripts/run_network.py](scripts/run_network.py) — `ananse network` wrapper with RAM check
- [scripts/run_influence.py](scripts/run_influence.py) — `ananse influence` wrapper
- [scripts/run_full_workflow.py](scripts/run_full_workflow.py) — End-to-end pipeline runner
- [scripts/plot_results.py](scripts/plot_results.py) — Influence dotplot and GRN visualization
- [scripts/export_results.py](scripts/export_results.py) — Export all results to CSV/TSV
