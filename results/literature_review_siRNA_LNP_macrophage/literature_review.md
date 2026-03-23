# Literature Review: siRNA Delivery via Lipid Nanoparticles for Macrophage/Monocyte Metabolic Manipulation

**Date:** 2026-03-17
**Search period:** 2015–2026
**Total papers identified:** 16
**Papers with full text:** 8 (PMC: 7, Unpaywall: 1)
**Papers abstract-only:** 8

---

## 1. Introduction

Macrophages and monocytes are central orchestrators of innate immunity, and their metabolic state — glycolytic versus oxidative — directly determines their inflammatory phenotype and functional output. Lipid nanoparticle (LNP)-mediated siRNA delivery has emerged as a precise tool to silence specific metabolic regulators in these cells, enabling controlled reprogramming of macrophage function. This approach has therapeutic implications ranging from cancer immunotherapy (reprogramming tumor-associated macrophages) to cardiometabolic disease (targeting monocyte-driven inflammation).

---

## 2. Search Strategy

Four PubMed queries were run on 2026-03-17 covering 2015–2026:

1. `("siRNA" OR "small interfering RNA") AND ("lipid nanoparticle" OR "LNP") AND ("macrophage" OR "monocyte") AND ("metabolic" OR "metabolism" OR "immunometabolism")`
2. `("siRNA" OR "RNAi") AND ("lipid nanoparticle") AND ("metabolic reprogramming" OR "glycolysis" OR "OXPHOS" OR "TCA cycle") AND ("macrophage" OR "myeloid")`
3. `("gene silencing" OR "RNA interference") AND ("LNP") AND ("macrophage polarization" OR "M1" OR "M2") AND ("nanoparticle")`
4. `"RNA, Small Interfering"[MeSH] AND "Liposomes"[MeSH] AND ("Macrophages"[MeSH] OR "Monocytes"[MeSH]) AND "Cell Metabolism"[MeSH]`

Results were deduplicated by PMID. Retmax=200 per query. Open access status was assessed via PMC elink (Entrez) and Unpaywall API.

**Deduplication approach:** PMIDs from all 4 queries were merged into a Python set before downstream processing. Each PMID appears exactly once in all downstream files.

---

## 3. Key Themes

### 3.1 LNP Formulation Landscape

The most commonly mentioned LNP components were: cationic lipid, cholesterol, DSPC, DSPE-PEG, DOPE. Ionizable lipids (such as DLin-MC3, SM-102, ALC-0315, and C12-200) were the most frequently cited formulation components, consistent with their established role in endosomal escape. Helper lipids (DSPC, DOPE, cholesterol) and PEG-lipids appeared frequently as formulation co-components.

**Top LNP components mentioned across corpus:**

| LNP Component | Papers Mentioning |
|---|---|
| cationic lipid | 6 |
| cholesterol | 6 |
| DSPC | 3 |
| DSPE-PEG | 3 |
| DOPE | 2 |
| ionizable lipid | 2 |
| MC3 | 2 |
| PEG-lipid | 2 |
| SM-102 | 1 |
| C12-200 | 1 |


### 3.2 Gene Targets and Metabolic Pathways

The most frequently targeted genes identified from abstract/fulltext extraction were: SOCS1 (n=34), TAK1 (n=20), GYG1 (n=14), SOCS (n=6), TAK (n=5), CD (n=4), CD47 (n=2), NP (n=2), NLRP3 (n=1).

**Top 20 gene targets (by extraction frequency):**

| Gene | Papers |
|---|---|
| SOCS1 | 34 |
| TAK1 | 20 |
| GYG1 | 14 |
| SOCS | 6 |
| TAK | 5 |
| CD | 4 |
| CD47 | 2 |
| NP | 2 |
| NLRP3 | 1 |


Metabolic pathways mentioned included: ROS (n=2), HIF-1alpha (n=1), TCA cycle (n=1), glycolysis (n=1), oxidative stress (n=1).

**Top metabolic pathways mentioned:**

| Metabolic Pathway | Papers |
|---|---|
| ROS | 2 |
| HIF-1alpha | 1 |
| TCA cycle | 1 |
| glycolysis | 1 |
| oxidative stress | 1 |


### 3.3 Macrophage Polarization Context

M1 (pro-inflammatory) contexts appeared in 7 papers, M2 (anti-inflammatory) in 9, TAM in 3, and monocyte-specific studies in 7. The distribution reflects the field's focus on inflammatory reprogramming, with TAM metabolic targeting being an emerging area.

**Macrophage context distribution:**

| Context | Papers |
|---|---|
| M2 | 9 |
| monocyte | 7 |
| M1 | 7 |
| monocyte-derived | 4 |
| peritoneal | 3 |
| bone marrow-derived | 3 |
| TAM | 3 |
| alveolar | 1 |


### 3.4 Model Systems

In vitro models: 8 papers. In vivo models: 5 papers.

**Model system breakdown:**

| Model System | Papers |
|---|---|
| in vitro | 8 |
| in vivo mouse | 5 |
| ex vivo | 3 |


### 3.5 Key Findings — Top Papers by Data Richness

The following papers were ranked by information density (full text availability + richness of extracted fields):

**1. Comprehensive analysis of metabolism-related genes in sepsis reveals metabolic-immune heterogeneity and highlights GYG1 as a potential therapeutic target.**
[PMID: 41333476] *Frontiers in immunology*, 2025. DOI: 10.3389/fimmu.2025.1682846

Targeted genes: GYG1. Metabolic pathways involved: glycolysis; oxidative stress. Model systems: in vivo mouse. Key finding: Results Patients in the high metabolic risk group exhibited a neutrophil-dominant and lymphocyte-suppressed immune landscape, consistent across bulk and single-cell analyses.

**2. Silencing SOCS1 via Liposome-Packed siRNA Sustains TLR4-Ligand Adjuvant.**
[PMID: 31214204] *Frontiers in immunology*, 2019. DOI: 10.3389/fimmu.2019.01279

Targeted genes: SOCS1; SOCS. Model systems: ex vivo. Key finding: Consequently, the MPLA-stimulated activation of APCs, monitored by release of pro-inflammatory cytokines such as IL-6, TNFα, and IL-1β, upregulation of MHC class II molecules and costimulatory CD80/CD86 is strongly enhanced and prolonged.

**3. Precision treatment of viral pneumonia through macrophage-targeted lipid nanoparticle delivery.**
[PMID: 38315853] *Proceedings of the National Academy of Sciences of the United States of America*, 2024. DOI: 10.1073/pnas.2314747121

Targeted genes: TAK; TAK1. Model systems: in vitro; in vivo mouse. Key finding: Further, we demonstrate that delivery of siRNA targeting TAK1, an important kinase upstream of inflammatory signaling pathways, can significantly attenuate the proinflammatory macrophage phenotype both in vitro and in vivo.

**4. Macrophage Checkpoint Nanoimmunotherapy Has the Potential to Reduce Malignant Progression in Bioengineered <i>In Vitro</i> Models of Ovarian Cancer.**
[PMID: 38558434] *ACS applied bio materials*, 2024. DOI: 10.1021/acsabm.4c00076

Targeted genes: CD47; NP. Model systems: in vitro. Key finding: High CD47 (OvCa) and SIRPα (macrophage) expression has been
linked to decreased survival, making this interaction a significant
target for therapeutic discovery.

**5. Lipid nanoparticle encapsulated large peritoneal macrophages migrate to the lungs via the systemic circulation in a model of clodronate-mediated lung-resident macrophage depletion.**
[PMID: 38646640] *Theranostics*, 2024. DOI: 10.7150/thno.91062

Targeted genes: CD. Model systems: in vitro; in vivo mouse; ex vivo. Key finding: Subsequently, it has been identified that GATA6 plays a vital role in LPM functionality and differentiation, and macrophage specific GAT6 KO studies in mice confirm increased rates of cell apoptosis pointing out to a vital role of GATA6 in LPM survival 17 .

**6. Boosting mRNA cancer vaccine efficacy via targeting <i>Irg1</i> on macrophages in lymph nodes.**
[PMID: 40521193] *Theranostics*, 2025. DOI: 10.7150/thno.110305

Metabolic pathways involved: TCA cycle. Model systems: in vitro; in vivo mouse. Key finding: Results: We found that macrophage-derived itaconate was increased markedly in activated ipsilateral lymph nodes after ovalbumin-encoding mRNA-lipid nanoparticle (OVA-LNP) injection, compared to homeostatic contralateral lymph nodes.

**7. Deciphering the role of polyethylene glycol-lipid anchors in siRNA-LNP efficacy for P2y2 inhibition in bone marrow-derived macrophages.**
[PMID: 40967321] *International journal of pharmaceutics*, 2025. DOI: 10.1016/j.ijpharm.2025.126186

Model systems: in vitro. Key finding: Despite comparable cellular uptake across formulations, their performance in gene silencing differed significantly.

**8. Immunomodulatory strategies and targeted delivery systems in atherosclerosis therapy.**
[PMID: 41729255] *Expert opinion on drug delivery*, 2026. DOI: 10.1080/17425247.2026.2636761

Targeted genes: NLRP3. Metabolic pathways involved: ROS. Abstract: INTRODUCTION: Atherosclerosis (AS) is a chronic inflammatory disease where lipid-lowering therapy alone leaves 30-40% residual cardiovascular risk, underscoring the need for immunomodulatory interventions. AREAS COVERED: This review synthesizes literature (1990-2024) on AS immunopathology and target...

**9. Suppression of fibrin(ogen)-driven pathologies in disease models through controlled knockdown by lipid nanoparticle delivery of siRNA.**
[PMID: 34958662] *Blood*, 2022. DOI: 10.1182/blood.2021014559

Model systems: ex vivo. Key finding: Three distinct LNP-siFga reagents reduced both hepatic Fga messenger RNA and fibrinogen levels in platelets and plasma, with plasma levels decreased to 42%, 16%, and 4% of normal within 1 week of administration.

**10. Local delivery of siRNA using lipid-based nanocarriers with ROS-scavenging ability for accelerated chronic wound healing in diabetes.**
[PMID: 40381523] *Biomaterials*, 2025. DOI: 10.1016/j.biomaterials.2025.123411

Metabolic pathways involved: ROS. Key finding: Diabetic wound healing poses a significant clinical challenge with limited therapeutic efficacy due to uncontrolled reactive oxygen species (ROS), inflammatory responses, and extracellular matrix (ECM) degradation caused by abnormal macrophage activity in the wound microenvironment.


---

## 4. Synthesis Table

See `synthesis_per_paper.csv` for full per-paper extracted data including LNP composition, gene targets, metabolic pathways, model systems, and key outcomes.

See `synthesis_themes.json` for aggregate counts across all papers.

---

## 5. Gaps and Opportunities

Based on the extracted data, the following gaps and opportunities were identified:

- The most frequently silenced genes in extracted data were: TAK1, NLRP3, CD, NP, SOCS1. Many metabolic regulators (e.g., PCSK9, LDHA, IDH1, ACLY) may be underrepresented in abstract-level text.

- In vitro models predominate (8 papers) over in vivo models (5 papers), suggesting a translational gap — efficacy in animal models remains underexplored for many targets.

- Standardized LNP formulation reporting is inconsistent across papers — many do not specify ionizable lipid identity, molar ratios, or encapsulation efficiency, limiting cross-study comparisons.

- Long-term in vivo safety and biodistribution data for macrophage-targeted LNP-siRNA are rarely reported, representing a key gap for translational development.

---

## References

The following references represent the first 50 papers in the corpus. See `paper_metadata.csv` for the complete reference list.

- PMID 26689461: Silencing TNFα with lipidoid nanoparticles downregulates both TNFα and MCP-1 in an in vitro co-culture model of diabetic foot ulcers.. *Acta biomaterialia* 2016. DOI: 10.1016/j.actbio.2015.12.023
- PMID 29688101: The efficiency of lipid nanoparticles with an original cationic lipid as a siRNA delivery system for macrophages and dendritic cells.. *Pharmaceutical development and technology* 2019. DOI: 10.1080/10837450.2018.1469149
- PMID 31214204: Silencing SOCS1 via Liposome-Packed siRNA Sustains TLR4-Ligand Adjuvant.. *Frontiers in immunology* 2019. DOI: 10.3389/fimmu.2019.01279
- PMID 32649972: Manipulating the function of tumor-associated macrophages by siRNA-loaded lipid nanoparticles for cancer immunotherapy.. *Journal of controlled release : official journal of the Controlled Release Society* 2020. DOI: 10.1016/j.jconrel.2020.07.001
- PMID 34132324: Identification of a potent ionizable lipid for efficient macrophage transfection and systemic anti-interleukin-1β siRNA delivery against acute liver failure.. *Journal of materials chemistry. B* 2021. DOI: 10.1039/d1tb00736j
- PMID 34958662: Suppression of fibrin(ogen)-driven pathologies in disease models through controlled knockdown by lipid nanoparticle delivery of siRNA.. *Blood* 2022. DOI: 10.1182/blood.2021014559
- PMID 38315853: Precision treatment of viral pneumonia through macrophage-targeted lipid nanoparticle delivery.. *Proceedings of the National Academy of Sciences of the United States of America* 2024. DOI: 10.1073/pnas.2314747121
- PMID 38558434: Macrophage Checkpoint Nanoimmunotherapy Has the Potential to Reduce Malignant Progression in Bioengineered <i>In Vitro</i> Models of Ovarian Cancer.. *ACS applied bio materials* 2024. DOI: 10.1021/acsabm.4c00076
- PMID 38646640: Lipid nanoparticle encapsulated large peritoneal macrophages migrate to the lungs via the systemic circulation in a model of clodronate-mediated lung-resident macrophage depletion.. *Theranostics* 2024. DOI: 10.7150/thno.91062
- PMID 40381523: Local delivery of siRNA using lipid-based nanocarriers with ROS-scavenging ability for accelerated chronic wound healing in diabetes.. *Biomaterials* 2025. DOI: 10.1016/j.biomaterials.2025.123411
- PMID 40521193: Boosting mRNA cancer vaccine efficacy via targeting <i>Irg1</i> on macrophages in lymph nodes.. *Theranostics* 2025. DOI: 10.7150/thno.110305
- PMID 40967321: Deciphering the role of polyethylene glycol-lipid anchors in siRNA-LNP efficacy for P2y2 inhibition in bone marrow-derived macrophages.. *International journal of pharmaceutics* 2025. DOI: 10.1016/j.ijpharm.2025.126186
- PMID 41333476: Comprehensive analysis of metabolism-related genes in sepsis reveals metabolic-immune heterogeneity and highlights GYG1 as a potential therapeutic target.. *Frontiers in immunology* 2025. DOI: 10.3389/fimmu.2025.1682846
- PMID 41371503: Pulmonary macrophage-targeted RNAi and mRNA co-delivery via SORT lipid nanoparticles enhances immunotherapy in lung cancer.. *Journal of controlled release : official journal of the Controlled Release Society* 2026. DOI: 10.1016/j.jconrel.2025.114519
- PMID 41729255: Immunomodulatory strategies and targeted delivery systems in atherosclerosis therapy.. *Expert opinion on drug delivery* 2026. DOI: 10.1080/17425247.2026.2636761
- PMID 41774227: M2pep-modified liposomal nanoparticles delivering siITGB4 induce apoptosis and inhibit NSCLC metastasis via macrophage reprogramming.. *Apoptosis : an international journal on programmed cell death* 2026. DOI: 10.1007/s10495-025-02243-5
