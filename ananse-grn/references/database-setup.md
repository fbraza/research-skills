# ANANSE Database and Reference Data Setup

This guide covers all reference data required to run ANANSE, including genome installation, REMAP model download, motif databases, and example data.

---

## 1. Genome Installation (Required)

ANANSE requires a genome FASTA and matching gene annotation. The easiest way is via `genomepy`.

### Install via genomepy (recommended)

```bash
conda activate ananse

# Human (hg38) — most common
genomepy install hg38 --annotation

# Human (GRCh38/Ensembl)
genomepy install GRCh38.p13 --provider Ensembl --annotation

# Mouse (mm10)
genomepy install mm10 --annotation

# Mouse (GRCm39)
genomepy install GRCm39 --provider Ensembl --annotation

# Zebrafish
genomepy install GRCz11 --provider Ensembl --annotation

# Rat
genomepy install Rnor_6.0 --provider Ensembl --annotation
```

After installation, use the genome name directly in ANANSE commands: `-g hg38`

### Use an existing genome FASTA

If you already have a genome FASTA and annotation:

```bash
# Register with genomepy (optional but enables auto gene symbol conversion)
genomepy install -p local /path/to/genome.fa \
    --Local-path-to-annotation /path/to/annotation.gtf

# Or specify directly in ANANSE commands:
ananse binding -g /path/to/genome.fa ...
ananse network binding.h5 -g /path/to/genome.fa -a /path/to/annotation.bed ...
```

**Requirements for manual genome:**
- FASTA file (chromosome names must match BAM files)
- Gene annotation in BED12 format (for `ananse network`)
- Gene names must be HGNC symbols (human/mouse) or match your motif database

---

## 2. REMAP Model (hg38 only — strongly recommended)

The REMAP model significantly improves TF binding prediction accuracy for human data by incorporating average ChIP-seq signal from thousands of REMAP experiments.

**Performance improvement (PR AUC from paper):**
- ATAC-seq only: ~0.28
- ATAC + H3K27ac: ~0.38
- ATAC + H3K27ac + REMAP: ~0.45

### Download

```bash
DATA_DIR=/path/to/data   # Set to your preferred location
mkdir -p $DATA_DIR/ANANSE.REMAP.model.v1.0
cd $DATA_DIR/ANANSE.REMAP.model.v1.0

wget https://zenodo.org/record/4768075/files/ANANSE.REMAP.model.v1.0.tgz
tar xvzf ANANSE.REMAP.model.v1.0.tgz
rm ANANSE.REMAP.model.v1.0.tgz

# Verify download
ls -lh $DATA_DIR/ANANSE.REMAP.model.v1.0/
```

**Expected size:** ~2 GB after extraction

### Usage

```bash
ananse binding \
    -A sample_ATAC.bam \
    -R $DATA_DIR/ANANSE.REMAP.model.v1.0/ \
    -o sample.binding
```

---

## 3. Motif Database

### Default database (human and mouse — no action needed)

ANANSE ships with `gimme.vertebrate.v5.0`, a non-redundant clustered database of vertebrate TF motifs from CIS-BP and other sources. This works out-of-the-box for human (HGNC symbols) and mouse (MGI symbols).

### For other species: generate a custom motif database

```bash
conda activate ananse

# Zebrafish (GRCz11)
gimme motif2factors --new-reference GRCz11 --outdir zebrafish_motifs

# Rat (Rnor_6.0)
gimme motif2factors --new-reference Rnor_6.0 --outdir rat_motifs

# Drosophila (dm6)
gimme motif2factors --new-reference dm6 --outdir drosophila_motifs
```

This generates:
- `zebrafish_motifs/gimme.vertebrate.v5.0.pfm` — Motif PFM file
- `zebrafish_motifs/gimme.vertebrate.v5.0.motif2factors.txt` — TF-to-motif mapping

Use in ANANSE:
```bash
ananse binding \
    -A ATAC.bam \
    -g GRCz11 \
    -r peaks.narrowPeak \
    -p zebrafish_motifs/gimme.vertebrate.v5.0.pfm \
    -o binding_output
```

### Alternative motif databases (GimmeMotifs built-in)

```bash
# List available databases
gimme motif2factors --list

# Use JASPAR2020 instead of default
ananse binding -A ATAC.bam -p JASPAR2020_vertebrates -o binding_output
```

---

## 4. Enhancer Regions

### For hg38 with REMAP model
No action needed — REMAP provides default enhancer regions.

### For hg38 without REMAP: ENCODE cCREs

```bash
# Download ENCODE candidate cis-Regulatory Elements (cCREs) for hg38
wget https://api.wenglab.org/screen_v13/fdownloads/GRCh38-ccREs.bed -O encode_ccres_hg38.bed

# Use in binding
ananse binding -A ATAC.bam -r encode_ccres_hg38.bed -o binding_output
```

### For mm10: ENCODE cCREs

```bash
wget https://api.wenglab.org/screen_v13/fdownloads/mm10-ccREs.bed -O encode_ccres_mm10.bed
```

### From your own ATAC-seq peaks (recommended)

Always use the **union of peaks from all conditions** to ensure consistent regions:

```bash
# Call peaks with MACS2 (per sample)
macs2 callpeak \
    -t sample_ATAC.bam \
    -f BAMPE \
    --nomodel \
    --shift -100 \
    --extsize 200 \
    --keep-dup all \
    -n sample_ATAC \
    --outdir peaks/

# Create union of all peaks
cat peaks/*.narrowPeak | \
    sort -k1,1 -k2,2n | \
    bedtools merge > union_peaks.bed

# Use in binding
ananse binding -A ATAC.bam -r union_peaks.bed -o binding_output
```

---

## 5. Example Data (Official Tutorial)

Download the official ANANSE example data (fibroblast → heart transition):

```bash
# Download example data
wget https://zenodo.org/record/4769814/files/ANANSE_example_data.tgz
tar xvzf ANANSE_example_data.tgz
rm ANANSE_example_data.tgz

# Expected structure:
# ANANSE_example_data/
# ├── ATAC/
# │   ├── fibroblast_ATAC_rep1.bam + .bai
# │   ├── fibroblast_ATAC_rep2.bam + .bai
# │   ├── heart_ATAC_rep1.bam + .bai
# │   └── heart_ATAC_rep2.bam + .bai
# ├── H3K27ac/
# │   ├── fibroblast_H3K27ac_rep1.bam
# │   ├── heart_H3K27ac_rep1.bam + .bai
# ├── RNAseq/
# │   ├── fibroblast_rep1_TPM.txt
# │   ├── fibroblast_rep2_TPM.txt
# │   ├── heart_rep1_TPM.txt
# │   ├── heart_rep2_TPM.txt
# │   └── fibroblast2heart_degenes.csv
# └── README.txt
```

---

## 6. Storage Requirements

| Resource | Size | Notes |
|---|---|---|
| hg38 genome (genomepy) | ~3 GB | FASTA + annotation |
| REMAP model | ~2 GB | hg38 only |
| ATAC-seq BAMs | 1–5 GB each | Depends on sequencing depth |
| H3K27ac BAMs | 1–3 GB each | — |
| binding.h5 output | 0.5–2 GB | Per condition |
| network.tsv output | 0.5–1 GB | Per condition |
| Example data | ~500 MB | Downsampled BAMs |

**Recommended free disk space:** ≥50 GB per analysis

---

## 7. Verifying Your Setup

```bash
conda activate ananse

# Check ANANSE version
ananse --version

# Check genomepy
genomepy --version

# Check genome is installed
genomepy search hg38

# Check REMAP model
ls /path/to/ANANSE.REMAP.model.v1.0/

# Test binding on a small region (quick sanity check)
ananse binding \
    -A ANANSE_example_data/ATAC/fibroblast_ATAC_rep1.bam \
    -R ANANSE.REMAP.model.v1.0/ \
    -o test_binding \
    -n 2
# Should complete in ~5-10 min and produce test_binding/binding.h5
```
