# Literature Review: Transcriptomic Studies in Asthma

**Review date:** March 2026
**Focus:** Bulk RNA-seq, microarray, scRNA-seq, multi-omics; data availability for deconvolution and MOFA+ integration

---

## 1. Summary Table of Relevant Studies

| # | PMID | Year | First Author | Technology | Tissue/Sample | n (cases/controls) | Comparators | GEO/Accession | Key Findings |
|---|------|------|--------------|------------|---------------|---------------------|-------------|---------------|--------------|
| 1 | 19483109 | 2009 | Woodruff PG | Microarray | Bronchial epithelial brushings, BAL | 42 asthma / 28 controls | Asthma vs. healthy; Th2-high vs. Th2-low | GSE4302 | Defined Th2-high/Th2-low subphenotypes via CLCA1/POSTN/SERPINB2 3-gene signature |
| 2 | 24075231 | 2014 | Peters MC | Microarray/qPCR | Induced sputum | 37 asthma / 15 controls | Th2-high vs. Th2-low asthma | Not stated | Sputum IL-4/IL-5/IL-13 transcript levels stratify Th2 subtypes; 70% of asthmatics Th2-high |
| 3 | 24495433 | 2014 | Poole A | RNA-seq | Nasal airway brushings | 10+50 asthma / 10+50 controls | Asthma vs. healthy; Th2-high vs. Th2-low | Not stated | 90% overlap between nasal and bronchial transcriptomes; nasal brushings identify Th2-high subphenotype |
| 4 | 23314903 | 2013 | Yick CY | Bulk RNA-seq | Endobronchial biopsies | 4 asthma / 5 controls | Asthma vs. healthy | Not stated | 46 DEGs including pendrin, periostin, BCL2; first RNA-seq of bronchial biopsies in asthma |
| 5 | 27580351 | 2017 | Kuo CS | Microarray + GSVA | Bronchial biopsies + epithelial brushings | 107 moderate-severe asthma | 4 molecular subtypes | E-MTAB-5197 (ArrayExpress) | Four asthma subtypes; two Th2-high groups (Groups 1 and 3) with steroid non-response |
| 6 | 28179442 | 2017 | Kuo CS | Microarray (Affymetrix) | Induced sputum | 93 severe / 25 moderate / 21 controls | Severe vs. mild asthma vs. healthy | GSE76262 | Sputum Th2/non-Th2 molecular phenotypes; TAC1 (Th2-high) associated with more severe asthma |
| 7 | 28528200 | 2018 | Rossios C | Microarray + proteomics | Induced sputum | ~100+ severe asthma, mild-moderate, controls | Severe vs. mild; eosinophilic vs. neutrophilic | Not stated | IL-1RL1 upregulation in eosinophilic SA; NLRP3 inflammasome in neutrophilic SA |
| 8 | 27925796 | 2017 | Bigler J | Microarray (Affymetrix) | Whole blood | 399 severe / 99 moderate asthma / ~100 controls | Severe vs. moderate vs. healthy | GSE69683 | Whole blood transcript fingerprint for severe asthma; neutrophil and oxidative stress signatures |
| 9 | 29650561 | 2018 | Tsai YH | Microarray meta-analysis | Bronchial + nasal airway epithelium | 355 asthma / 193 controls (8 studies) | Asthma vs. healthy | Multiple | 1,273 DEGs; POSTN, CLCA1, MUC5AC, CHI3L1 consistently upregulated |
| 10 | 30962590 | 2019 | Altman MC | RNA-seq | Nasal + blood | 106 children (exacerbation-prone asthma) | Viral exacerbation vs. non-viral vs. non-exacerbation | GSE115770 | Core exacerbation modules; SMAD3 upregulated; T2/IFN ratio predicts exacerbation risk |
| 11 | 32640237 | 2020 | Jackson ND | scRNA-seq + population transcriptomics | ALI cultures + nasal brushings (695 children) | IL-13-treated vs. control; T2H vs. T2L children | T2-high vs. T2-low in vivo | GSE145013, GSE152004 | IL-13 induces pan-epithelial mucus metaplasia; all epithelial cell types affected |
| 12 | 32532832 | 2020 | Seumois G | scRNA-seq | PBMCs (allergen-reactive CD4+ T cells) | 6 asthma+HDM / 6 asthma−HDM / 6 control+HDM / 6 control−HDM | Asthmatic vs. allergic non-asthmatic | GSE146170 | IL-9-expressing Th2, ThIFNR, TregIFNR subsets in asthma; IL-9 reduced after immunotherapy |
| 13 | 33397719 | 2021 | Wang L | scRNA-seq | Lung (mouse: BALB/c) | 6 mice per group | Steroid-resistant HDM/LPS vs. control | Not stated | 20 immune subsets; ILC2s produce IL-4/IL-13 in steroid-resistant manner *(mouse model)* |
| 14 | 37146132 | 2023 | Alladina J | scRNA-seq | BAL + endobronchial brushings + blood monocytes | 4 AA + 4 AC + 5 HC (52,152 cells) | Allergic asthma vs. allergic control vs. healthy | GSE193816 | Pathogenic IL-9+ Th2 cells exclusive to asthmatic airways; DC2 and CCR2+ monocytes enriched |
| 15 | 34510493 | 2022 | Fricker M | Bulk RNA-seq + microarray | Sputum macrophages | 7 NA / 13 NNA (RNA-seq); 47 NA / 57 NNA (U-BIOPRED) | Neutrophilic vs. non-neutrophilic asthma | Not stated | Macrophage transcriptome altered in neutrophilic asthma; SLAMF7, DYSF, GPR183, CSF3 upregulated |
| 16 | 38262391 | 2024 | Zhan W | Bulk RNA-seq + scRNA-seq | Induced sputum | 18 EA / 15 EB / 28 HC (bulk); 3/2/3 (scRNA-seq) | Eosinophilic asthma vs. eosinophilic bronchitis vs. healthy | Not stated | FCN1+ macrophage activation unique to eosinophilic asthma; EREG, TGFBI, VEGFA upregulated |
| 17 | 39073027 | 2024 | Kermani NZ | Multi-omics (6 blocks) | Induced sputum | 57 severe / 15 mild-moderate / 13 healthy | Severe vs. mild vs. healthy; 5 omics-associated clusters | GSE76262 | 5 omics-associated clusters; OAC3 = eosinophilic Th2; OAC2/4 = neutrophilic + Moraxella/IL-22 |
| 18 | 35347136 | 2022 | Sajuthi SP | RNA-seq + TWAS + WGS | Nasal airway brushings | 434 asthma / 247 controls (GALA II) | Asthmatic vs. healthy; MUC5AC risk variant carriers | GSE152004 | 102 asthma TWAS genes; MUC5AC eQTL increases mucus secretory cell frequency 4.6-fold |
| 19 | 38806494 | 2024 | Szczesny B | RNA-seq + DNA methylation | Nasal epithelium | 253 asthma / 283 controls (CAAPA, 7 sites) | Asthma vs. healthy in African Diaspora populations | Not stated (CAAPA) | 389 DEGs; FN1 (fibronectin) top DEG; 3 axes: Th2, impaired wound healing, FKBP5 methylation |
| 20 | 39672815 | 2024 | Park K | scRNA-seq | PBMCs (blood) | 8 severe eosinophilic asthma (longitudinal 0/1/6 months) | Pre-biologic vs. 1-month vs. 6-month post-treatment | NCT05164939 | IL1B+ classical monocytes decrease; CD4+ T cell subset remodelling; marked changes only at 6 months |
| 21 | 38814679 | 2024 | Haruna NF | scRNA-seq + CITE-seq | Bone marrow + blood granulocytes | Severe / mild / healthy | Severe vs. mild vs. healthy | Not stated | Immature metamyelocyte neutrophils expand in severe asthma; IL-5 drives neutrophil-to-eosinophil differentiation |
| 22 | 40538440 | 2025 | Goss K | scRNA-seq | Circulating eosinophils (blood) | Severe / mild / healthy | Severe vs. mild vs. healthy | Not stated | 3 eosinophil gene expression states; IFN-α and IFN-γ pathway enrichment; CCR3 upregulated |
| 23 | 40684957 | 2025 | Jayavelu ND | scRNA-seq (10x Flex) + bulk RNA-seq | Nasal lavage | High-eosinophil vs. low-eosinophil asthma children | Eosinophil-high vs. low asthma phenotype | Not stated | 16-fold increase in eosinophil detection vs. standard methods; distinct granulocyte subpopulations |
| 24 | 40089475 | 2025 | Khan M | scRNA-seq + scATAC-seq | Lung CD4+ T cells (mouse) | HDM-challenged vs. PBS | pTh2 subsets in HDM asthma | Not stated | 2 proinflammatory pTh2 subsets; TSLP and TNFRSF drive pathogenic differentiation *(mouse model)* |
| 25 | 38351296 | 2024 | Yan Q | Bulk RNA-seq (bioinformatics) | Bronchial epithelium (GEO-derived) | Mild / moderate / severe vs. healthy | Severity gradient | GSE63142, GSE158752 | 10 hub neutrophilic genes (PTPRC, TLR2, MMP9, FCGR3B, CXCR1/2, S100A12) |
| 26 | Preprint | 2025 | Yan X | scRNA-seq | Induced sputum | 16 asthma / 8 non-asthmatic controls | Asthma vs. healthy | GSE270863 | 15 cell populations; ADAM12-SDC4, CCL22-CCR4 DC–T cell communication *(not yet peer-reviewed)* |
| 27 | 30815178 | 2018 | Kan M | Microarray + RNA-seq (integrated) | Multiple cell types | Multiple cohorts | Asthma vs. healthy | GSE65401, SRP033351 | RAVED pipeline; cell/tissue-specific and global asthma gene signatures |

---

## 2. Biological Themes Across Studies

### 2.1 The T2-High / T2-Low Axis — The Most Replicated Finding

The single most consistent transcriptomic finding across all tissue types and technologies is the **T2-high/T2-low endotype split** [1, 3, 5, 6, 9, 11, 18]. Approximately 50–70% of asthmatics are classified as T2-high depending on cohort severity.

**Core T2-high airway epithelial signature:** POSTN (periostin), CLCA1, SERPINB2, MUC5AC, FOXA3, SPDEF, and IL-13 response genes. This signature is detectable across bronchial epithelium [1], nasal epithelium [3, 11, 18], and sputum cells [2]. POSTN and CLCA1 are IL-13-regulated and predict corticosteroid response.

**Cell types driving T2-high disease** (converging across technologies): ILC2s, Th2 cells (especially the **IL-9+ Th2 subset** [14] and the **ThIFNR subset** [12]), eosinophils, mast cells, basophils, DC2 dendritic cells [14], and IL-13-remodelled basal/goblet epithelial cells [11].

**T2-low disease** (replicated but mechanistically heterogeneous): Characterised by neutrophilia, NLRP3 inflammasome activation, IL-1 receptor family upregulation [7], and in some clusters, Moraxella dysbiosis + IL-22 pathway activation [17].

### 2.2 Eosinophilic vs. Neutrophilic Endotypes

Multiple independent studies converge on a bimodal inflammatory axis [2, 6, 7, 15, 16, 17]:

**Eosinophilic asthma:**
- High sputum eosinophilia, IL1RL1/ST2 upregulation [7]
- FCN1+ macrophage activation (EREG, TGFBI, VEGFA) uniquely in eosinophilic asthma vs. eosinophilic bronchitis [16]
- Th2 gene modules, POSTN/CLCA1 positivity
- Responds to anti-IL-5 and anti-IL-4Rα biologics

**Neutrophilic asthma:**
- Macrophage transcriptomic reprogramming (SLAMF7, GPR183, CSF3) [15]
- NLRP3 inflammasome, CXCR1/CXCR2/S100A12/MMP9 neutrophil axis [25]
- Moraxella-associated microbiome dysbiosis [17], potential IL-22 pathway [17]
- Steroid-resistant

**Paucigranulocytic asthma:** Best lung function, minimal inflammation markers; mechanistically least characterised transcriptomically (OAC1 in U-BIOPRED [17]).

### 2.3 Airway Epithelium as the Sentinel Compartment

Across >15 studies, the airway epithelium (bronchial or nasal brushings) provides the most interpretable transcriptomic signal [1, 3, 4, 9, 11, 18, 25]:

- IL-13 induces a pan-epithelial mucus metaplasia programme converting all cell types (secretory, ciliated, goblet) to MUC5AC-high states [11]
- Nasal epithelium is an acceptable surrogate for bronchial epithelium: 90% gene overlap [3], similar DEG effect sizes [9]
- FOXA3 and SPDEF are TF hubs driving goblet metaplasia
- Epithelial MUC5AC:MUC5B ratio disrupted in T2-high disease [11]
- Mucociliary clearance failure downstream of IL-13-induced ER stress in ciliated cells [11]

### 2.4 Immune Cell-Specific Findings from scRNA-seq

scRNA-seq has resolved previously unresolvable cell heterogeneity:

- **T cells:** IL-9+ Th2 cells appear exclusively in asthmatic airways post-allergen challenge [14]; ThIFNR and TregIFNR subsets in blood of asthma patients without HDM allergy [12]; CD4+ T subset remodelling by biologics begins only after 6 months [20]
- **ILC2s:** Steroid-resistant IL-4/IL-13 production from ILC2s [13]; NMU-NMUR1 signalling drives inflammatory ILC2 responses
- **Eosinophils:** 3 transcriptional states; IFN pathway enrichment in asthmatic eosinophils [22]; mixed neutrophil-eosinophil precursors expand in severe asthma [21]; 16-fold improvement in eosinophil recovery using 10x Flex fixation [23]
- **Macrophages:** FCN1+ macrophages mark eosinophilic asthma specifically [16]; macrophage transcriptome reshaping defines neutrophilic asthma [15]
- **DC2 / CCR2+ monocytes:** Enriched in asthmatic airways post-allergen; form a Th2–DC–basal cell interactome [14]

### 2.5 Exacerbation Biology

Children with exacerbation-prone asthma show a nasal transcriptomic core exacerbation programme (SMAD3 upregulation, lymphocyte downregulation, mucus hypersecretion, eosinophil activation) common to both viral and non-viral triggers [10]. A high T2/IFN ratio at baseline predicts exacerbation risk better than FEV1 [10].

### 2.6 Multi-Omics Convergence in U-BIOPRED

The U-BIOPRED programme [5, 6, 7, 8, 17] has provided the most integrated picture of severe asthma to date. Integrating sputum microarray transcriptomics, SomaSCAN proteomics, shotgun proteomics, 16S microbiome, and metagenomic sequencing across the same 57 severe / 28 control subjects [17], five stable omics-associated clusters emerge. Multi-omics integration identifies more distinct phenotypes than any single modality alone.

---

## 3. Data Availability Assessment

### 3.1 Complete GEO/ArrayExpress Dataset Inventory

| Accession | n Samples | Groups | Technology | Platform | Sample Type | Deconvolution? | MOFA-eligible? |
|-----------|-----------|--------|------------|----------|-------------|----------------|----------------|
| GSE4302 | 70 | 42 asthma / 28 controls | Microarray | Affymetrix | Bronchial epithelial brushings | No (single cell type) | No |
| GSE76262 | 139 | 93 severe / 25 moderate / 21 controls | Microarray | Affymetrix HT HG-U133+ PM | Induced sputum cells | **YES** — bulk mixed cell type | Partial (transcriptomics only) |
| GSE69683 | 498 | ~399 severe / ~99 moderate / ~100 controls | Microarray | Affymetrix HT HG-U133+ PM | Whole blood | **YES** — deconvolution target | Partial |
| GSE115770 | 523 | 106 children, stratified by exacerbation | RNA-seq | GPL16791 | Nasal brushings | No (single cell type) | No |
| GSE152004 | 695 | 441 asthma / 254 controls | RNA-seq | GPL11154 | Nasal airway brushings | No (single cell type) | Partial (paired with genomics) |
| GSE85567 | 85 | Asthmatics vs. non-asthmatics | RNA-seq | GPL11154 | Airway epithelial cells | No (single cell type) | **YES — RNA-seq + methylation** |
| GSE146170 | 18 (50K cells) | 6 asthma+HDM / 6 asthma−HDM / 6 controls | scRNA-seq | Illumina | PBMCs (CD4+ T cells) | **YES** — scRNA-seq reference | scRNA-seq reference only |
| GSE145013 | ~20 donors | IL-13-treated vs. control + T2H/T2L in vivo | scRNA-seq + bulk | 10x Genomics + Illumina | ALI cultures + nasal brushings | **YES** — epithelial cell reference | No (limited n) |
| GSE193816 | 21 (52,152 cells) | 4 AA / 4 AC / 5 HC baseline + allergen | scRNA-seq | 10x Genomics | BAL + endobronchial brushings + blood | **YES** — airway scRNA-seq reference | No (n too small for MOFA) |
| GSE270863 | 24 (37,565 cells) | 16 asthma / 8 controls | scRNA-seq | 10x Genomics | Induced sputum | **YES** — sputum scRNA-seq reference | No (single modality) |
| GSE285752 | 1,535 total | Asthma vs. controls across 5 tissues | Microarray | Mixed | Whole blood (n=954), CD4+ T (n=411), macrophages (n=84), BAL (n=42), bronchial epithelium (n=44) | **YES** — multi-tissue bulk target | **YES** — if patients matched across tissues |
| GSE63142 | 155 | 72 mild-moderate / 56 severe / 27 controls | Microarray | GPL6480 | Bronchial epithelial brushings | No (single cell type) | No |
| E-MTAB-5197 | 107 | Moderate-severe asthma | Microarray | Affymetrix | Bronchial biopsies + brushings | No (single cell type) | No |

**Estimated total publicly accessible asthma patient samples:** Conservatively **>3,000 unique patients** spanning whole blood (~1,400+), airway epithelium (~700+), sputum (~300+), BAL/bronchial brushings (~150+), and T cell/PBMC fractions (~500+).

### 3.2 Recommended Deconvolution Pairs

| Bulk target | scRNA-seq reference | Tissue match | n (target) | Verdict |
|-------------|---------------------|--------------|------------|---------|
| GSE76262 (induced sputum) | GSE270863 (sputum scRNA-seq, 37K cells) | Excellent | 93 severe / 25 mod / 21 ctrl | **Best pair — highest priority** |
| GSE69683 (whole blood) | GSE146170 (CD4+ T cell scRNA-seq) | Good for T cells | 399 severe / 99 mod | Feasible |
| GSE285752 BAL + bronchial strata | GSE193816 (BAL + brushings scRNA-seq) | Excellent | 84 BAL + 44 bronchial | Best multi-tissue target |

> **Note:** The Human Lung Cell Atlas (~347,000 cells, uniLUNG) should be considered as a complementary broad reference for cell types not captured in asthma-specific datasets.

### 3.3 Datasets with ≥2 Omics Modalities on Same Samples (MOFA-eligible)

| Dataset / Study | Omics modalities | Sample type | n | Notes |
|-----------------|-----------------|-------------|---|-------|
| **U-BIOPRED sputum** (Kermani 2024, PMID 39073027) | Transcriptomics + SomaSCAN proteomics + shotgun proteomics + 16S microbiome + metagenomics | Induced sputum | 57 severe / 15 mild / 13 healthy | **6 data blocks — highest priority MOFA+ target; published analysis used SNF, not MOFA+** |
| GSE85567 + linked methylation | RNA-seq + DNA methylation (EPIC/450K) | Airway epithelial cells | 85 | Two modalities; genome-wide; MOFA-ready |
| CAAPA (Szczesny 2024, PMID 38806494) | RNA-seq + DNA methylation | Nasal epithelium | 536 (253 asthma / 283 controls) | Large n; multi-ethnic; requires CAAPA consortium data access |
| GSE285752 BRIDGE | Microarray expression across 5 tissues | Whole blood, CD4+ T, macrophages, BAL, bronchial | 1,535 total | Multi-tissue; **patient-level pairing across tissues must be verified before MOFA+** |

---

## 4. MOFA+ Feasibility Assessment

**Summary verdict: MOFA+ is technically feasible but has never been applied in any published asthma study.** The multi-omics work published to date has used Similarity Network Fusion (U-BIOPRED [17]) or separate modality analyses.

### Highest-Priority Target: U-BIOPRED Sputum Multi-Omics

The U-BIOPRED sputum dataset provides **6 omics blocks** on the same 85 subjects:
- Transcriptomics (microarray, available on GEO: GSE76262)
- SomaSCAN proteomics (~1,300 proteins)
- Shotgun proteomics (label-free)
- 16S rRNA microbiome profiling
- Shotgun metagenomics
- (Clinical metadata and spirometry)

A MOFA+ analysis of this dataset would:
1. Decompose shared latent factors across all modalities
2. Handle missing values across omics blocks (a key MOFA+ advantage)
3. Identify which omics layers contribute most to patient clustering
4. Provide biologically interpretable factor loadings across endotypes

The investigators' published SNF analysis identified 5 stable omics-associated clusters [17]. MOFA+ would yield an orthogonal and more interpretable decomposition — this is a de novo contribution to the field.

### Modality Availability Summary

| Modality | Publicly available? | Notes |
|----------|---------------------|-------|
| Transcriptomics (bulk) | YES | Multiple large GEO resources |
| Transcriptomics (scRNA-seq) | YES | GSE193816, GSE146170, GSE145013, GSE270863 |
| DNA methylation | YES (partial) | GSE85567, CAAPA; BRIDGE methylation pending |
| Proteomics (blood/sputum) | Within U-BIOPRED | SomaSCAN + shotgun; not on GEO; requires data access |
| Metabolomics | Limited | Available within U-BIOPRED and one Chinese sputum study |
| Microbiome (16S/shotgun) | Within U-BIOPRED | Co-located with transcriptomics on same samples |
| Genomics/GWAS | YES (separate) | CAAPA, GALA II, SARP; not typically co-submitted with RNA-seq |
| ATAC-seq / chromatin | Mouse only (Khan 2025) | No published human asthma paired ATAC-seq + RNA-seq |

---

## 5. Evidence Gaps

**Gap 1 — No matched blood + airway scRNA-seq from the same human patients.**
The Alladina 2023 study [14] collected BAL, bronchial brushings, and blood monocytes from the same individuals but did not perform scRNA-seq on all compartments simultaneously with matched depth. True multi-compartment scRNA-seq (blood PBMC + BAL + bronchial biopsy per patient, same time point) has not been published in human asthma.

**Gap 2 — No longitudinal multi-omics data in well-characterised human asthma.**
All current multi-omics datasets are cross-sectional. The Park 2024 study [20] is the only longitudinal scRNA-seq study, covering only 8 patients treated with biologics. No published longitudinal multi-omics datasets track molecular changes across exacerbations or treatment responses in the same patients.

**Gap 3 — No published human airway scRNA-seq + ATAC-seq from the same cells.**
Chromatin accessibility data in human asthma airways does not exist. The one multi-modal chromatin study [24] is mouse-based. TF activity and regulatory programme inference in human disease remains dependent on inference from RNA alone.

**Gap 4 — Eosinophil transcriptomics in tissue remains technically immature.**
Standard 10x Genomics scRNA-seq fails to capture granulocytes at biological frequencies. The recent 10x Flex fixation approach [23] represents a technical breakthrough but has only been applied to nasal lavage, not BAL or bronchial tissue.

**Gap 5 — Neutrophilic asthma is transcriptomically understudied.**
Despite neutrophilic asthma comprising ~40% of severe asthma and being steroid-refractory, no study has performed single-cell profiling of airway neutrophils in human neutrophilic asthma. Available data are indirect (macrophage bulk [15] and sputum bulk [17]).

**Gap 6 — MOFA+ has never been applied to existing multi-omics asthma data.**
The U-BIOPRED multi-omics dataset [17] was analysed with Similarity Network Fusion, not MOFA+. A MOFA+ analysis of U-BIOPRED sputum data (6 omics blocks) would be a novel contribution and is currently absent from the literature.

**Gap 7 — No paediatric vs. adult airway single-cell comparison.**
Childhood asthma and adult asthma likely have different cellular compositions and regulatory states, but no matched scRNA-seq datasets comparing children and adults on identical protocols exist.

**Gap 8 — No spatial transcriptomics of human asthmatic airways.**
No published spatial transcriptomics study of human asthmatic lung or bronchial tissue has been identified. This represents a major gap given the architectural importance of the airway mucosa.

---

## 6. Comparison with Kidney Operational Tolerance Literature

| Dimension | Kidney Operational Tolerance | Asthma |
|---|---|---|
| Total accessible patient samples | ~200–250 | **>3,000** |
| Bulk microarray/RNA-seq GEO datasets | ~8 | **>15 large datasets** |
| scRNA-seq studies (human) | 2 (n=4 and n=1 tolerant) | **8+ studies, up to 52K cells** |
| Multi-omics datasets (≥2 modalities) | 0 | **2–3 (U-BIOPRED, CAAPA, BRIDGE)** |
| MOFA+ applied | Never | **Never published — but feasible** |
| Spatial transcriptomics | Never | Never |
| Matched blood + tissue scRNA-seq | Never | Never (partial in Alladina 2023) |
| Core molecular signature | B-cell genes (IGKV1D-13, TCL1A, EBF1) | T2-high signature (POSTN, CLCA1, MUC5AC) |
| Most underexplored compartment | Graft biopsy | Neutrophilic asthma airways |

---

## 7. Full Citation List

[1] Woodruff PG et al. T-helper Type 2–driven Inflammation Defines Major Subphenotypes of Asthma. *Am J Respir Crit Care Med.* 2009. **PMID: 19483109.** GEO: GSE4302.

[2] Peters MC et al. Measures of gene expression in sputum cells can identify TH2-high and TH2-low subtypes of asthma. *J Allergy Clin Immunol.* 2014. **PMID: 24075231.**

[3] Poole A et al. Dissecting childhood asthma with nasal transcriptomics distinguishes subphenotypes of disease. *J Allergy Clin Immunol.* 2014. **PMID: 24495433.**

[4] Yick CY et al. Transcriptome sequencing (RNA-Seq) of human endobronchial biopsies: asthma versus controls. *Eur Respir J.* 2013. **PMID: 23314903.**

[5] Kuo CS et al. A Transcriptome-driven Analysis of Epithelial Brushings and Bronchial Biopsies to Define Asthma Phenotypes in U-BIOPRED. *Am J Respir Crit Care Med.* 2017. **PMID: 27580351.** ArrayExpress: E-MTAB-5197.

[6] U-BIOPRED sputum TAC study. *Am J Respir Crit Care Med.* 2017. **PMID: 28179442.** GEO: GSE76262.

[7] Rossios C et al. Sputum transcriptomics reveal upregulation of IL-1 receptor family members in patients with severe asthma. *J Allergy Clin Immunol.* 2018. **PMID: 28528200.**

[8] Bigler J et al. A Severe Asthma Disease Signature from Gene Expression Profiling of Peripheral Blood from U-BIOPRED Cohort Participants. *Am J Respir Crit Care Med.* 2017. **PMID: 27925796.** GEO: GSE69683.

[9] Tsai YH et al. Meta-analysis of airway epithelium gene expression in asthma. *Eur Respir J.* 2018. **PMID: 29650561.**

[10] Altman MC et al. Transcriptome networks identify mechanisms of viral and nonviral asthma exacerbations in children. *Nat Immunol.* 2019. **PMID: 30962590.** GEO: GSE115770.

[11] Jackson ND et al. Single-Cell and Population Transcriptomics Reveal Pan-epithelial Remodeling in Type 2-High Asthma. *Cell Rep.* 2020. **PMID: 32640237.** GEO: GSE145013, GSE152004.

[12] Seumois G et al. Single-cell transcriptomic analysis of allergen-specific T cells in allergy and asthma. *Sci Immunol.* 2020. **PMID: 32532832.** GEO: GSE146170.

[13] Wang L et al. Single-cell transcriptomic analysis reveals the immune landscape of lung in steroid-resistant asthma exacerbation. *Proc Natl Acad Sci U S A.* 2021. **PMID: 33397719.** *(Mouse model — BALB/c.)*

[14] Alladina J et al. A human model of asthma exacerbation reveals transcriptional programs and cell circuits specific to allergic asthma. *Sci Immunol.* 2023. **PMID: 37146132.** GEO: GSE193816.

[15] Fricker M et al. An altered sputum macrophage transcriptome contributes to the neutrophilic asthma endotype. *Allergy.* 2022. **PMID: 34510493.**

[16] Zhan W et al. Sputum Transcriptomics Reveals FCN1+ Macrophage Activation in Mild Eosinophilic Asthma Compared to Non-Asthmatic Eosinophilic Bronchitis. *Allergy Asthma Immunol Res.* 2024. **PMID: 38262391.**

[17] Kermani NZ et al. Endotypes of severe neutrophilic and eosinophilic asthma from multi-omics integration of U-BIOPRED sputum samples. *Clin Transl Med.* 2024. **PMID: 39073027.** GEO: GSE76262 (transcriptomics block).

[18] Sajuthi SP et al. Nasal airway transcriptome-wide association study of asthma reveals genetically driven mucus pathobiology. *Nat Commun.* 2022. **PMID: 35347136.** GEO: GSE152004.

[19] Szczesny B et al. Multi-omics in nasal epithelium reveals three axes of dysregulation for asthma risk in the African Diaspora populations. *Nat Commun.* 2024. **PMID: 38806494.**

[20] Park K et al. Single-cell RNA sequencing reveals transcriptional changes in circulating immune cells from patients with severe asthma induced by biologics. *Exp Mol Med.* 2024. **PMID: 39672815.**

[21] Haruna NF et al. scRNA-seq profiling of human granulocytes reveals expansion of developmentally flexible neutrophil precursors with mixed properties in asthma. *J Leukoc Biol.* 2024. **PMID: 38814679.**

[22] Goss K et al. Single-cell RNA-sequencing of circulating eosinophils from asthma patients reveals an inflammatory signature. *iScience.* 2025. **PMID: 40538440.**

[23] Jayavelu ND et al. Single-cell transcriptomic profiling of eosinophils and airway immune cells in childhood asthma. *J Allergy Clin Immunol.* 2025. **PMID: 40684957.**

[24] Khan M et al. Single-cell and chromatin accessibility profiling reveals regulatory programs of pathogenic Th2 cells in allergic asthma. *Nat Commun.* 2025. **PMID: 40089475.** *(Mouse model — C57BL/6.)*

[25] Yan Q et al. Bronchial epithelial transcriptomics and experimental validation reveal asthma severity-related neutrophilic signatures and potential treatments. *Commun Biol.* 2024. **PMID: 38351296.** Uses GEO: GSE63142, GSE158752.

[26] Yan X et al. Single-cell RNA Sequencing Analysis of Sputum Cell Transcriptomes Reveals Pathways and Communication Networks That Contribute to the Pathogenesis of Asthma. *bioRxiv.* 2025. **Preprint — not yet peer-reviewed.** GEO: GSE270863.

[27] Kan M et al. Integration of Transcriptomic Data Identifies Global and Cell-Specific Asthma-Related Gene Expression Signatures. *AMIA Annu Symp Proc.* 2018. **PMID: 30815178.** GEO: GSE65401.

---

*Generated by Aria — Scientific Research Collaborator. Created by Phylo.*
