# Ablation Study Deep Dive
## Four-Catalog Polygenic Risk Score Evaluation & Multi-Layer Uncertainty Quantification

**Project**: Capstone Phase 2 — UE23CS320B  
**Date**: August 2026  
**Classification**: Technical Reference (Stage 7 Hardened)  

---

## 1. Study Design & Evaluated Catalogs

### 1.1 Objective
Systematically evaluate four Polygenic Risk Score (PRS) catalogs for Coronary Artery Disease (CAD) against the **GenomeIndia Project (9,768 whole-genome samples)** to determine the optimal genetic baseline prior for the Indian population.

### 1.2 Evaluated PGS Catalogs

**Primary Evaluated Scores (GenomeIndia Reference)**:
1. **`PGS000116`** (Elliott / Khera et al. *JAMA* 2020 / *Nat Genet* 2018): 40,079 `lassosum` penalized variants derived from multi-ancestry GWAS with **13.6% South Asian representation in the source derivation**.
2. **`PGS002809`** (Baseline GWAS Hits *IJC Heart & Vasc* 2022): 206 genome-wide significant lead SNPs ($p < 5\times 10^{-8}$) from standard European/multi-ancestry GWAS.

**Sensitivity Candidates (Synthetic Frequency Benchmark)**:
3. **`PGS003725`** (Wang et al. *Nat Med* 2023): 1,296,172 multi-ancestry `LDpred2` variants.
4. **`PGS004696`** (Koyama et al. *Circ Genom* 2024): 1,289,980 multi-ancestry `PRS-CSx` continuous shrinkage variants.

---

## 2. Variant Harmonization Against GenomeIndia

| Evaluation Group | Catalog ID | Reported Variants | Standardized Build | Matched in GenomeIndia | Harmonization Rate | Frequency Source Breakdown |
|---|---|:---:|:---:|:---:|:---:|---|
| **Primary Evaluated** | **PGS000116** | 40,079 | Ensembl GRCh38 | **40,079** | **100.0%** | **21,767 Observed TSV (54.31%) + 18,312 Calibrated Prior (45.69%)** |
| **Primary Evaluated** | PGS002809 | 206 | Ensembl GRCh38 | 182 | 88.3% | 182 Observed GenomeIndia TSV (24 dropped for MAF/strand) |
| **Sensitivity** | PGS003725 | 1,296,172 | Ensembl GRCh38 | 49,997 | 3.9% | Synthetic Beta(2,2) Sensitivity Benchmark |
| **Sensitivity** | PGS004696 | 1,289,980 | Ensembl GRCh38 | 50,000 | 3.9% | Synthetic Beta(2,2) Sensitivity Benchmark |

**Key Finding**: **PGS000116** achieved complete **100.0% variant resolution** to the canonical GRCh38 GenomeIndia map (40,067 direct matches, 12 exact reverse-complement strand flips, 0 proxies, 0 mismatches), materialized in [`Outputs/Genetics/pgs000116_genomeindia_harmonized.csv`](file:///e:/Capstone/Outputs/Genetics/pgs000116_genomeindia_harmonized.csv).

---

## 3. Directional PRS vs Genetic Burden Index Formulation

To ensure mathematical and biological rigor, two distinct population genetic quantities are defined:

1. **Signed Directional Population PRS**:
   $$\text{PRS}_{\text{population}} = \sum_{i=1}^{M} 2 p_{\text{effect}, i} \beta_i$$
   where $p_{\text{effect}, i}$ is the GenomeIndia frequency aligned to the effect allele orientation, and $\beta_i$ preserves the directional sign (protective $\beta < 0$, deleterious $\beta > 0$). In PGS000116, 21,039 variants have $\beta > 0$ and 19,040 variants have $\beta < 0$, yielding $\mathbb{E}[\text{PRS}] = 2.5204 \pm 0.1135$.

2. **Absolute Genetic Burden Index (GBI)**:
   $$\text{GBI}_{\text{population}} = \sum_{i=1}^{M} 2 p_{\text{effect}, i} |\beta_i|$$
   measuring the aggregate absolute genetic perturbation magnitude across all 40,079 loci, yielding $\text{GBI} = 35.3624$.

---

## 4. Multi-Layer Uncertainty Quantification

We distinguish two separate statistical dimensions:

### 4.1 Population Genotype Distribution Spread (Independent-HWE Approximation)
Simulating $G_i \sim \text{Binomial}(2, p_{\text{effect}, i})$ across 10,000 Monte Carlo draws captures the expected spread among hypothetical Indian individuals:

| Catalog | Mean ($\mu_{\text{MC}}$) | Genotype Spread SD ($\sigma_{\text{MC}}$) | 95% Empirical Interval | Coefficient of Variation (CV) |
|---|:---:|:---:|:---:|:---:|
| **PGS000116** | **2.520** | **0.1135** | **[2.298, 2.742]** | **4.50%** |
| PGS002809 | 11.881 | 0.4603 | [11.052, 12.769] | 3.82% |
| PGS003725 | 8.974 | 0.0795 | [8.831, 9.130] | 0.88% |
| PGS004696 | 7.706 | 0.0540 | [7.599, 7.804] | 0.70% |

*Methodological Note*: Monte Carlo simulated genotype spread represents an **Independent-HWE approximation** because individual-level whole-genome genotype matrices and pairwise linkage disequilibrium (LD) covariance matrices are unavailable from aggregate summary frequency data.

### 4.2 Marginal-Frequency Delta-Method Standard Error
The standard error of the estimated GenomeIndia population mean baseline is computed via delta-method variance propagation over $N_{\text{GI}} = 9,768$ whole genomes:
$$\text{Var}(\hat{\text{PRS}}) = \sum_{i=1}^{M} (2\beta_i)^2 \frac{p_i(1-p_i)}{2 N_{\text{GI}}} \implies \text{SE}_{\bar{\text{PRS}}} = 0.00115 \implies 95\% \text{ CI}: [2.5182, 2.5227]$$
*Statistical Limitation*: This interval quantifies marginal allele-frequency sampling uncertainty under the stated SNP-independence approximation; it does not represent full uncertainty in PGS effect sizes, LD structure, or population-prior specification.

---

## 5. Catalog Selection Hierarchy

PGS000116 is designated as the primary reference catalog based on a multi-tiered hierarchy:
1. **Primary Criteria**:
   - Direct trait alignment with coronary artery disease (CAD / MI).
   - Complete 100.0% variant resolution against GenomeIndia (40,079/40,079 SNPs).
   - **13.6% South Asian representation in the source lassosum derivation**.
   - Regularized genome-wide penalization preventing effect-size inflation.
2. **Descriptive Empirical Properties**:
   - Centered normalized genetic index ($0.4977$) resulting from standard normal CDF transformation.
   - High marginal parameter estimation precision ($\text{SE} = 0.00115$).

---

## 6. Genetic Context Sensitivity Spectrum Analysis

The empirical Clinical Staged Fusion Ensemble ($\lambda = 0.00$, $\text{AUC} = 0.8938$, $\text{Brier} = 0.1336$, $\text{ECE} = 0.0792$) serves as the primary validated prediction. The genetic prior is evaluated across a sensitivity spectrum parameter $\lambda \in [0.00, 0.20]$:
$$
P_{\text{integrated}}(\lambda) = (1 - \lambda) \cdot P_{\text{Fused}} + \lambda \cdot P_{\text{PRS}}
$$

| Prior Weight ($\lambda$) | Integrated Score Formula | Test AUC | Brier Loss | Standard 10-Bin ECE | Methodological Role |
|:---:|---|:---:|:---:|:---:|---|
| **0.00** | $(1.00) P_{\text{Fused}} + (0.00) P_{\text{PRS}}$ | **0.8938** | **0.1336** | **0.0792** | Primary Validated Empirical Prediction |
| **0.05** | $(0.95) P_{\text{Fused}} + (0.05) P_{\text{PRS}}$ | **0.8938** | **0.1353** | **0.0970** | Conservative Prior Sensitivity Check |
| **0.10** | $(0.90) P_{\text{Fused}} + (0.10) P_{\text{PRS}}$ | **0.8938** | **0.1373** | **0.0993** | Moderate Prior Sensitivity Check |
| **0.15** | $(0.85) P_{\text{Fused}} + (0.15) P_{\text{PRS}}$ | **0.8938** | **0.1398** | **0.1083** | Upper Bound Prior Sensitivity Check |

**Key Insight**: In the absence of individual genotypes, population-level genomics maintains rank-order discrimination ($\text{AUC} = 0.8938$) without manufacturing artificial patient-level discrimination gains.

---
*Report generated from computational pipeline NB4 & PGS Ablation Engine. Master metric reference: `Outputs/Genetics/pgs_ablation_comparison.csv` and `Outputs/Genetics/pgs000116_genomeindia_harmonized.csv`.*