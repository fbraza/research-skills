# ANANSE Troubleshooting Guide

---

## Installation Issues

### `conda create -n ananse ananse` fails

**Cause:** Channel conflict or outdated conda.

**Solution:**
```bash
# Update conda first
conda update conda

# Try with strict channel priority
conda create -n ananse ananse -c bioconda -c conda-forge --strict-channel-priority

# Alternative: use mamba (faster solver)
conda install mamba -n base -c conda-forge
mamba create -n ananse ananse
```

### `pip install` fails with dependency conflicts

**Solution:**
```bash
# Install in a fresh virtual environment
python -m venv ananse_env
source ananse_env/bin/activate
pip install git+https://github.com/vanheeringen-lab/ANANSE
```

### `genomepy install` fails

**Cause:** Network issue or provider unavailable.

**Solution:**
```bash
# Try a different provider
genomepy install hg38 --provider NCBI --annotation

# Or download manually and register
genomepy install -p local /path/to/hg38.fa \
    --Local-path-to-annotation /path/to/hg38.gtf
```

---

## `ananse binding` Issues

### `binding.h5` not created / binding step fails silently

**Cause:** ANANSE conda environment not active, or BAM files not indexed.

**Checklist:**
```bash
# 1. Activate environment
conda activate ananse

# 2. Check BAM files are sorted and indexed
samtools quickcheck sample_ATAC.bam
ls sample_ATAC.bam.bai   # Must exist

# 3. If not indexed:
samtools sort -o sample_ATAC_sorted.bam sample_ATAC.bam
samtools index sample_ATAC_sorted.bam

# 4. Check genome is installed
genomepy search hg38
```

### `No regions found` error

**Cause:** Missing `--regions` for non-hg38 genome, or wrong file path.

**Solution:**
```bash
# Provide your ATAC peaks
ananse binding -A ATAC.bam -g mm10 -r peaks.narrowPeak -o binding_output

# Or use ENCODE cCREs
ananse binding -A ATAC.bam -g mm10 \
    -r encode_ccres_mm10.bed -o binding_output
```

### Very slow binding step

**Cause:** Single-threaded or large peak set.

**Solution:**
```bash
# Increase cores
ananse binding -A ATAC.bam -R REMAP/ -o binding/ -n 16

# Precompute motif scores (saves time on reruns)
gimme scan -Tz --gc -g hg38 union_peaks.narrowPeak > motif_scores.tsv
ananse binding -A ATAC.bam --pfmscorefile motif_scores.tsv -o binding/
```

### Poor binding prediction quality

**Cause:** Not using REMAP model (hg38), or using H3K27ac peaks as regions.

**Solution:**
```bash
# Use REMAP model (hg38 only)
ananse binding -A ATAC.bam -R /path/to/ANANSE.REMAP.model.v1.0/ -o binding/

# Never use H3K27ac peaks as --regions (too broad)
# Use ATAC peaks or ENCODE cCREs instead
```

---

## `ananse network` Issues

### Out-of-memory (OOM) crash

**Cause:** Insufficient RAM. This step requires ~12–15 GB for human.

**Solutions:**
```bash
# 1. Check available RAM before running
free -h

# 2. Use fewer cores (reduces memory overhead)
ananse network binding.h5 -e TPM.txt -n 1 -o network.tsv

# 3. Close other memory-intensive processes

# 4. If on HPC, request more memory
#SBATCH --mem=32G
```

### Empty or very small network (few TF-gene pairs)

**Cause:** Gene symbol mismatch between expression file and motif database.

**Diagnosis:**
```bash
# Check what TFs are in the binding file
ananse view binding.h5 -lt | head -20

# Check gene names in your expression file
head -5 expression_TPM.txt
```

**Solution:**
```bash
# Use genomepy genome for automatic symbol conversion
ananse network binding.h5 -e TPM.txt -g hg38 -o network.tsv

# If using custom genome, ensure gene names are HGNC symbols
# Check: gene names in expression file must match TF names in binding.h5
```

### `Gene annotation error` / `BED file not found`

**Cause:** Genome not installed via genomepy, or missing annotation.

**Solution:**
```bash
# Install genome with annotation
genomepy install hg38 --annotation

# Or provide annotation manually
ananse network binding.h5 -e TPM.txt \
    -g /path/to/genome.fa \
    -a /path/to/annotation.bed \
    -o network.tsv
```

### Network step very slow

**Cause:** Single-threaded or large genome.

**Solution:**
```bash
# Increase cores (but watch RAM — each core uses ~2-3 GB)
ananse network binding.h5 -e TPM.txt -n 8 -o network.tsv
```

---

## `ananse influence` Issues

### Unexpected or nonsensical top TFs

**Cause #1:** Wrong `log2FoldChange` direction — most common error.

**Diagnosis:**
```bash
# Check: are the top TFs known to be active in the SOURCE (not target)?
# If yes, your log2FC direction is inverted.
head -5 degenes.tsv
```

**Solution:**
```bash
# Fix: negate log2FoldChange if direction is wrong
python -c "
import pandas as pd
df = pd.read_csv('degenes.tsv', sep='\t')
df['log2FoldChange'] = -df['log2FoldChange']  # Invert direction
df.to_csv('degenes_corrected.tsv', sep='\t', index=False)
"
```

**Cause #2:** Source and target networks swapped.

**Solution:** Ensure `-s` is the baseline/control and `-t` is the treated/differentiated condition.

### `padj NaN` error / influence step fails

**Cause:** NA values in `padj` column of DESeq2 output (common for low-count genes).

**Solution:**
```bash
python -c "
import pandas as pd
df = pd.read_csv('deseq2_results.tsv', sep='\t')
df = df.dropna(subset=['padj'])
df.to_csv('degenes_filtered.tsv', sep='\t', index=False)
print(f'Kept {len(df)} genes after removing NA padj')
"
```

### No diffnetwork file generated

**Cause:** Forgot `-f` / `--full-output` flag.

**Solution:**
```bash
# Re-run with -f flag
ananse influence \
    -s source.network.tsv \
    -t target.network.tsv \
    -d degenes.tsv \
    -o influence.tsv \
    -f -n 8
```

### Very few TFs in results

**Cause:** Too few DE genes passing the `padj` cutoff, or too few edges.

**Solution:**
```bash
# Relax padj cutoff
ananse influence -s source.network.tsv -t target.network.tsv \
    -d degenes.tsv -j 0.1 -o influence.tsv -f

# Increase number of edges
ananse influence -s source.network.tsv -t target.network.tsv \
    -d degenes.tsv -i 500000 -o influence.tsv -f
```

### TF of interest missing from results

**Cause:** TF lacks a motif in the database, or TF is not expressed.

**Diagnosis:**
```bash
# Check if TF is in binding file
ananse view binding.h5 -lt | grep -i "MYOD1"

# Check if TF is expressed
grep "MYOD1" expression_TPM.txt
```

**Solution:**
```bash
# Use jaccard-cutoff to allow related TF models
ananse binding -A ATAC.bam --jaccard-cutoff 0.2 -o binding/

# Or check if TF name differs (e.g., MYOD1 vs MyoD)
ananse view binding.h5 -lt | grep -i "myo"
```

---

## `ananse plot` Issues

### Plot not generated / empty plot

**Cause:** Missing diffnetwork file (forgot `-f` in influence step).

**Solution:**
```bash
# Re-run influence with -f
ananse influence ... -f -o influence.tsv

# Then plot
ananse plot influence.tsv -d influence_diffnetwork.tsv -o plots/
```

### GRN figure is too cluttered

**Solution:**
```bash
# Reduce number of TFs
ananse plot influence.tsv -d influence_diffnetwork.tsv --n-tfs 10 -o plots/

# Set minimum edge weight
ananse plot influence.tsv -d influence_diffnetwork.tsv --edge-min 0.1 -o plots/
```

---

## General Debugging Tips

### Check ANANSE version
```bash
conda activate ananse
ananse --version
```

### Run with verbose output
```bash
# Add -v or check stderr
ananse binding -A ATAC.bam -o binding/ -n 4 2>&1 | tee binding.log
```

### Verify output files exist and are non-empty
```bash
ls -lh source.binding/binding.h5
ls -lh source.network.tsv
ls -lh influence.tsv
ls -lh influence_diffnetwork.tsv
```

### Check binding.h5 contents
```bash
ananse view binding.h5 -n 5    # Preview
ananse view binding.h5 -lt     # List TFs
ananse view binding.h5 -lr     # List regions
```

### Memory monitoring during network step
```bash
# In a separate terminal, monitor memory usage
watch -n 5 free -h
# Or
top -p $(pgrep -f "ananse network")
```
