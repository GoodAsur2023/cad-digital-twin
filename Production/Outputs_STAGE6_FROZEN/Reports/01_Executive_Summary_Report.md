# Executive Summary Report
## India-Specific Coronary Artery Disease Digital Twin: Multi-Component Risk Prediction with Genomics, Physiology, and Explainable AI

**Project**: Capstone Phase 2 — UE23CS320B  
**Date**: August 2026  
**Classification**: For Advisors & Reviewers (Stage 7 Hardened)  

---

## 1. Project Overview

This project delivers a **hybrid Counterfactual State-Transition Digital Twin ($S_t \to S_t'$) for Coronary Artery Disease (CAD) risk assessment and model-informed counterfactual intervention planning** tailored to the Indian population. The system couples four computational intelligence components:

| Component | Computational Foundation | Clinical & Methodological Role |
|---|---|---|
| **Genomics** | Polygenic Risk Scores (Canonical PGS000116 evaluated against GenomeIndia) | Population-level genetic context ($\text{PRS}_{\text{population}} = \sum 2p_{\text{effect}, i} \beta_i$) & Genetic Burden Index ($\text{GBI} = \sum 2p_{\text{effect}, i} |\beta_i|$) |
| **Machine Learning** | Calibrated Gradient Boosting (XGBoost / GradientBoosting) | Baseline clinical feature assessment & exercise-ST-augmented diagnostic risk evaluation |
| **Mechanistic Physiology** | Kitware Pulse Physiology Engine v4.3.2 C-API (`libPulseC.dll`) | Whole-body multi-organ hemodynamic simulation & physiological grounding |
| **Explainability & Decision Support** | TreeSHAP + Decoupled Prior Shift + ACC/AHA Decision Context | Feature attribution & patient-specific model-informed counterfactual intervention ranking |

**Cohorts**: 69,825 lifestyle records (development cohort, target: binary CVD diagnosis) + 1,190 clinical records (Cleveland, Hungarian, and Statlog cohorts, target: angiographic CAD $>50\%$ stenosis)  
**Genomics Single Source of Truth**: Canonical PGS000116 scoring file (40,079 variants: 40,067 direct matches, 12 strand flips, 0 proxies) combining **21,767 GenomeIndia-derived observed TSV frequencies (54.31%)** and **18,312 calibrated South-Asian population-prior frequencies under $\text{Beta}(\alpha=2.2, \beta=2.0)$ (45.69%)** for variants lacking direct TSV coverage.  
**Physiological Simulations**: 238 CAD patients × 4 lifestyle/clinical scenarios = 952 native Pulse v4.3.2 whole-body simulations  

---

## 2. Key Methodological Findings & Results

### 2.1 Multi-Catalog Polygenic Risk Score Evaluation
| PGS Catalog | Method | Variants Evaluated | GenomeIndia Harmonization | Frequency Source Breakdown | Population Genotype Spread ($\mu \pm \sigma_{\text{MC}}$) | Marginal Delta-Method SE ($\text{SE}_{\bar{X}}$) | Normalized Genetic Index |
|---|---|---|---|---|---|---|---|
| **PGS000116** (Khera / Elliott et al.) | lassosum | 40,079 | **100.0%** (40,079/40,079) | **21,767 Observed TSV (54.3%) + 18,312 Calibrated Prior (45.7%)** | **2.52 ± 0.11** ($\text{CV} = 4.5\%$) | **0.00115** [2.5182, 2.5227] | **0.4977** (Centered by construction) |
| PGS002809 (Baseline GWAS) | Significant Hits | 206 | 88.3% (182/206) | GenomeIndia Matched chr1–22 | 11.88 ± 0.46 ($\text{CV} = 3.82\%$) | 0.00465 [11.871, 11.889] | 0.9999 (Saturated) |
| PGS003725 (Wang et al.) | LDpred2 | 1,296,172 | 3.9% (49,997/1.3M) | Synthetic Beta(2,2) Sensitivity Candidate | 8.97 ± 0.08 ($\text{CV} = 0.88\%$) | 0.00081 [8.968, 8.972] | 0.9998 (Saturated) |
| PGS004696 (Koyama et al.) | PRS-CSx | 1,289,980 | 3.9% (50,000/1.3M) | Synthetic Beta(2,2) Sensitivity Candidate | 7.71 ± 0.05 ($\text{CV} = 0.70\%$) | 0.00051 [7.709, 7.711] | 0.9995 (Saturated) |

**Key Finding**: **PGS000116** is the single source of truth for the Indian population baseline: it achieves complete 100% variant resolution against GenomeIndia, accounts for **13.6% South Asian representation in the source lassosum derivation**, and produces a centered normalized genetic index ($0.4977$). Marginal-frequency parameter estimation uncertainty ($\text{SE}=0.00115$, 95% CI: $[2.5182, 2.5227]$) is derived via delta-method propagation over $N=9,768$ individuals under a stated SNP-independence approximation; this interval quantifies marginal allele-frequency sampling uncertainty under the stated SNP-independence approximation and does not represent full uncertainty in PGS effect sizes, LD structure, or population-prior specification. The Monte Carlo spread ($\sigma_{\text{MC}}=0.1135$) characterizes inter-individual variability under an Independent-HWE approximation.

### 2.2 Canonical Model Performance Matrix (N=1,000 Stratified Bootstrap)
| Model Architecture | Evaluated Cohort | Target Endpoint | Test AUC (95% CI) | Brier Loss (95% CI) | Standard 10-Bin ECE (95% CI) | Clinical Intended Role |
|---|---|---|:---:|:---:|:---:|---|
| **Lifestyle Only (XGBoost)** | Lifestyle (n=13,727) | `CVD_diagnosis` | **0.8061** [0.7992, 0.8135] | **0.1784** [0.1750, 0.1816] | **0.0122** [0.0090, 0.0199] | Routine population behavioral & metabolic risk screening |
| **Baseline Clinical Feature Model** | Clinical (n=238) | `CAD >50%` | **0.8595** [0.8134, 0.9029] | **0.1549** [0.1332, 0.1763] | **0.0596** [0.0561, 0.1254] | Baseline clinical feature assessment excluding exercise ST-depression |
| **Exercise-ST-Augmented Diagnostic Model** | Clinical (n=238) | `CAD >50%` | **0.8845** [0.8433, 0.9242] | **0.1341** [0.1086, 0.1601] | **0.0549** [0.0508, 0.1146] | Diagnostic risk assessment augmented with exercise ST-depression |
| **Clinical Staged Fusion Ensemble** | Clinical (n=238) | `CAD >50%` | **0.8938** [0.8530, 0.9303] | **0.1336** [0.1117, 0.1560] | **0.0792** [0.0686, 0.1331] | Primary validated predictive model combining baseline + exercise data |
| **Genetic Context Sensitivity ($\lambda=0.15$)** | Clinical (n=238) | `CAD >50%` | **0.8938** [0.8530, 0.9303] | **0.1398** [0.1205, 0.1595] | **0.1083** [0.0857, 0.1577] | Sensitivity evaluation demonstrating rank-invariance under genetic prior shift |

**Key Finding**: The **Clinical Staged Fusion Ensemble** ($0.70 P_{\text{diag}} + 0.30 P_{\text{base}}$, weights selected via training-fold CV argmax ROC-AUC $= 0.8912$) achieves superior predictive discrimination ($\text{AUC} = 0.8938, \text{Brier} = 0.1336$). The population genetic layer provides ancestry context and biological pathway stratification; because the population prior is constant across ungenotyped individuals, it maintains rank-invariant discrimination without manufacturing artificial patient-level predictive claims.

### 2.3 Decision Curve Analysis (DCA) Net Benefit across Model Decision Thresholds
| Decision Threshold | Treat All (95% CI) | Baseline Model (95% CI) | Diagnostic Model (95% CI) | Clinical Staged Fusion Ensemble (95% CI) | Genetic Context Sensitivity (95% CI) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **10%** | 0.4771 [0.4771, 0.4771] | 0.4804 [0.4781, 0.4827] | 0.4785 [0.4692, 0.4851] | **0.4823** [0.4795, 0.4851] | 0.4771 [0.4771, 0.4771] |
| **20%** | 0.4118 [0.4118, 0.4118] | 0.4317 [0.4160, 0.4454] | 0.4328 [0.4044, 0.4569] | **0.4391** [0.4149, 0.4580] | 0.4338 [0.4170, 0.4485] |
| **30%** | 0.3277 [0.3277, 0.3277] | 0.3776 [0.3451, 0.4058] | 0.3962 [0.3625, 0.4292] | 0.4046 [0.3751, 0.4352] | **0.4088** [0.3818, 0.4358] |
| **40%** | 0.2157 [0.2157, 0.2157] | 0.3557 [0.3137, 0.3964] | **0.3641** [0.3249, 0.4062] | **0.3641** [0.3221, 0.4006] | 0.3613 [0.3179, 0.3992] |
| **50%** | 0.0588 [0.0588, 0.0588] | 0.3025 [0.2478, 0.3529] | **0.3529** [0.3025, 0.4034] | 0.3277 [0.2731, 0.3782] | 0.3277 [0.2731, 0.3782] |

*Methodological Note*: Net benefit thresholds are evaluated for the model's binary CAD endpoint and should not be interpreted as validated guideline risk thresholds for 10-year ASCVD events.

### 2.4 Decoupled Explainability Layer
- **TreeSHAP Feature Attribution**: **100% computed across empirical features** (Clinical: **82.3%**, Lifestyle: **13.3%**).
- **Genetic Context**: Decoupled from TreeSHAP and applied as an external prior probability shift ($\Delta P_{\text{gen}}$).
- **Actionability Classification**: Clinical domain represents treatment-responsive targets; lifestyle represents prescriptive behavioral targets; genomics represents non-modifiable population background.

### 2.5 PulsePhysio Mechanistic Physiological Grounding
- **238 patients** simulated across **4 multi-organ intervention scenarios** (952 native Pulse v4.3.2 C-API simulations).
- **Mean Cardiac Workload Sparing**: **−9.49%** (rate-pressure double product reduction).
- **Hemodynamic Shifts**: Exercise −4.3 mmHg SBP, Weight Loss −5.1 mmHg SBP, Smoking Cessation −5.5 mmHg SBP, Combined −8.9 mmHg SBP.
- **Canonical Sign Convention**: All risk reductions are unified as $\Delta P = P_{\text{post}} - P_{\text{baseline}} < 0$ (Combined scenario: $\Delta P = -0.0302$, i.e. 3.02 percentage point risk reduction).
- **Feature Vector Policy**: SVR and rate-pressure double product do not enter the tabular ML feature vector; they serve as biophysical context.

### 2.6 Digital Twin Validation & Sanity Check Battery
- **13/13 (100.0%) Sanity Checks PASSED (Live Re-Executed)**:
  - **Category A (Intervention Plausibility)**: 6/6 PASSED (Smoking cessation, physical activity, alcohol abstinence, BMI changes, SBP reduction).
  - **Category B (Model Sensitivity)**: 7/7 PASSED (Max HR variations, oldpeak ST-depression shifts, comprehensive multi-factor normalization).
- **Intervention Realism Constraints**: Hard boundary registry actively rejects invalid single-step transitions (e.g. max 5 kg/m² BMI delta, immutable age/sex).
- **Non-Causal Counterfactual Disclaimer**: Intervention rankings are model-based counterfactual simulations and are not estimates of causal treatment effects or clinical prescriptions.

### 2.7 Gene-Level Architecture on Primary Catalog (PGS000116)
- **40,079 variants** materialized in [`Outputs/Genetics/pgs000116_genomeindia_harmonized.csv`](file:///e:/Capstone/Outputs/Genetics/pgs000116_genomeindia_harmonized.csv): 40,067 direct allele matches, 12 exact strand-flip matches, 0 proxies.
- **Curated Loci vs Background**: 39 curated CVD candidate loci represent **4.40%** of total Genetic Burden Index ($\text{GBI} = 35.3624$), while genome-wide polygenic background accounts for **95.60%**.
- **Top Curated CVD Loci**: CDKN2B-AS1 (20.48% of annotated signal, 9p21.3), LPA (15.23%), SORT1 (5.68%), PHACTR1 (5.11%), LPL (4.84%), APOE (4.53%), LDLR (3.80%), ADAMTS7 (3.46%), IL6R (3.24%), PCSK9 (3.19%), HMGCR (2.96%).
- **Pathway Contribution Analysis**: Lipid Metabolism (2.13% of total GBI, 428 SNPs), Cell Cycle / 9p21.3 (0.90%, 61 SNPs), Vascular Remodeling (0.66%, 199 SNPs), Inflammation/Immune (0.32%, 107 SNPs).
- **Evidence-Graded Pharmacogenomics**: Categorized into formal CPIC Level A guidelines (SLCO1B1, CYP2C19, HMGCR) and AHA/ACC/FH clinical guidelines (PCSK9, LPA, LDLR). Explicit scope flag declared: `requires_individual_genotype: true`, `status: "population_knowledge_only"`.

---

## 3. Methodological Rigor & Master Integrity Gate

The automated 26-point methodology integrity gate (`nb12_methodology_audit.py`) validated a **26/26 (100.0%) PASS rate** across three explicit verification tiers:
- **14 Actively Recomputed Checks** (Signed PRS, GBI, delta-method SE, live gene/pathway aggregations, live baseline vs diagnostic AUC evaluation, staged fusion AUC 0.8938, ECE 0.0792, DCA net benefit, 4-case sign test, production constraint rejection, live Category A intervention battery, live Category B model sensitivity battery, literature deviations $<15\%$).
- **8 Artifact Verified Checks** (Cohort sample counts, 40,079-variant table structure, catalog hierarchy, PGx evidence table, PGx availability flag, fusion provenance JSON, benchmark schema, Pulse simulation outputs).
- **4 Scope Declared Checks** (Decoupled explainability semantics, target definition compatibility, counterfactual state-transition scope, internal reproducibility PASS vs external validation NOT_PERFORMED).

---
*Report generated from computational pipeline NB1–NB12. All values verified against canonical metrics in `Outputs/Clinical/canonical_benchmark_metrics.json` and `Outputs/Genetics/pgs000116_genomeindia_harmonized.csv`.*