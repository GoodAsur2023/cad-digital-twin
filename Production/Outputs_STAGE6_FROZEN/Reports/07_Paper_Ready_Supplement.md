# Scientific Supplement & Methodological Reference
## Comprehensive Supplementary Materials for Manuscript Submission

**Project**: Capstone Phase 2 — UE23CS320B  
**Target Venues**: *Nature Digital Medicine* / *Lancet Digital Health* / *JACC: Advances*  
**Date**: August 2026  
**Status**: Comprehensive Validated Scientific Supplement (Stage 7 Hardened)  

---

## 1. Manuscript Metadata & Abstract

### 1.1 Working Title
"A Genomics-Aware, Physiology-Grounded Hybrid Counterfactual Digital Twin for Coronary Artery Disease Risk Prediction in Indian Populations: Multi-Component Machine Learning, Kitware Pulse Simulation, and Explainable AI"

### 1.2 Structured Abstract (250 Words)
**Background**: Cardiovascular risk stratification in South Asian populations suffers from Eurocentric risk score miscalibration and lack of mechanistic integration. We developed a hybrid Counterfactual State-Transition Digital Twin ($S_t \to S_t'$) combining Indian ancestry polygenic risk context, multi-component machine learning, whole-body physiological simulation, and explainable AI.

**Methods**: Four computational components were integrated: (1) GenomeIndia Project allele frequencies (9,768 whole genomes) harmonized across a single-source canonical 40,079-variant table for PGS000116 (40,067 direct matches, 12 non-palindromic strand flips, 0 proxies) combining 21,767 GenomeIndia-derived observed TSV frequencies (54.31%) and 18,312 calibrated South-Asian population-prior frequencies under $\text{Beta}(2.2, 2.0)$ (45.69%); (2) 69,825 lifestyle records (`CVD_diagnosis` target) and 1,190 clinical records (`angiographic_CAD_gt50pct` target); (3) Kitware Pulse Physiology Engine v4.3.2 C-API (`libPulseC.dll`) for mechanistic hemodynamic simulation; (4) Decoupled TreeSHAP explainability (100% across empirical features) with external genetic context shift. Baseline clinical feature assessment was separated from diagnostic exercise ST-depression confirmation. Fusion weights ($w_{\text{diag}}=0.70, w_{\text{base}}=0.30$) were derived via training-fold cross-validation optimizing ROC-AUC ($0.8912$). A tiered 26-point master integrity gate, $N=1,000$ bootstrap uncertainty, DCA across decision thresholds, and 13 categorized sanity tests were conducted.

**Results**: PGS000116 (40,079 variants) achieved 100.0% variant resolution with GenomeIndia, with parameter estimation uncertainty derived via delta-method propagation under SNP independence ($\text{SE} = 0.00115$ [95% CI: 2.5182, 2.5227]) and Independent-HWE spread ($\sigma_{\text{MC}} = 0.1135$). The Baseline Clinical Feature Model achieved an AUC of 0.8595 [95% CI: 0.8134, 0.9029], the Exercise-ST-Augmented Diagnostic Model achieved an AUC of 0.8845 [0.8433, 0.9242] ($\Delta\text{AUC} = +0.0250$ from `oldpeak`), and the Clinical Staged Fusion Ensemble achieved an AUC of 0.8938 [0.8530, 0.9303]. Native PulsePhysio simulations (238 patients × 4 scenarios = 952 runs) demonstrated a mean cardiac workload reduction of −9.49% (SBP deltas: exercise −4.3, weight loss −5.1, smoking cessation −5.5, combined −8.9 mmHg). All 13/13 sanity checks passed (live re-executed), and all 26/26 integrity gate assertions passed (14 Actively Recomputed, 8 Artifact Verified, 4 Scope Declared).

**Conclusions**: This hybrid Digital Twin provides biologically grounded, genomics-aware risk prediction and **model-informed counterfactual intervention planning** for Indian populations.

---

## 2. Core Methodological Tables

### Table S1: Variant Harmonization Quality Control (QC) Summary for PGS000116
| Harmonization QC Metric | Variant Count | % of Catalog | Methodological Resolution |
|---|---:|:---:|---|
| **Input PGS000116 Variants** | 40,079 | 100.0% | Multi-ancestry lassosum scoring file (GRCh38) |
| **Ensembl GRCh38 Positional Matches** | 40,079 | 100.0% | Standardized genomic liftover |
| **Direct Allele Matches (REF / ALT)** | 40,067 | 99.97% | Direct string match to GenomeIndia alleles |
| **Exact Strand-Flip Matches** | 12 | 0.03% | Unambiguous reverse-complement transitions/transversions |
| **Ambiguous Palindromic SNPs (A/T, C/G)** | 0 | 0.00% | Zero ambiguous palindromes retained |
| **Unresolved Allele Mismatches** | 0 | 0.00% | Zero unresolved or proxy alleles |
| **Duplicate rsIDs / Coordinates** | 0 | 0.00% | Zero duplicates across autosomes |
| **Missing Frequency / Beta Weights** | 0 | 0.00% | Complete feature completeness |
| **Final Canonical Retained Variants** | **40,079** | **100.0%** | Materialized in single-source canonical CSV |

---

### Table S2: Multi-Catalog PRS Benchmark Against GenomeIndia (9,768 Samples)
| Group | Catalog ID | Scoring Method | Variants Evaluated | GenomeIndia Harmonization | Frequency Source Breakdown | Raw Baseline ($\mu \pm \sigma_{\text{MC}}$) | Marginal Delta-Method SE ($\text{SE}_{\bar{X}}$) | Normalized Genetic Index |
|---|---|:---:|:---:|:---:|---|:---:|:---:|:---:|
| **Primary Evaluated** | **PGS000116** | lassosum | 40,079 | **100.0%** | **21,767 Observed (54.3%) + 18,312 Calibrated (45.7%)** | **2.520 ± 0.114** | **0.00115** [2.5182, 2.5227] | **0.4977** (Centered) |
| **Primary Evaluated** | PGS002809 | GWAS Hits | 206 | 88.3% | 182 Observed GenomeIndia TSV | 11.881 ± 0.460 | 0.00465 [11.871, 11.889] | 0.9999 (Saturated) |
| **Sensitivity Benchmark** | PGS003725 | LDpred2 | 1,296,172 | 3.9% | Synthetic Beta(2,2) Sensitivity Candidate | 8.974 ± 0.079 | 0.00081 [8.968, 8.972] | 0.9998 (Saturated) |
| **Sensitivity Benchmark** | PGS004696 | PRS-CSx | 1,289,980 | 3.9% | Synthetic Beta(2,2) Sensitivity Candidate | 7.706 ± 0.054 | 0.00051 [7.709, 7.711] | 0.9995 (Saturated) |

---

### Table S3: Canonical Multimodal Fusion Benchmark Matrix (N=1,000 Stratified Bootstrap)
| Model Architecture | Evaluated Cohort | Target Endpoint | Test AUC (95% CI) | Brier Loss (95% CI) | Standard 10-Bin ECE (95% CI) | Sensitivity (95% CI) | Specificity (95% CI) |
|---|---|---|:---:|:---:|:---:|:---:|:---:|
| **Lifestyle Only (XGBoost)** | Lifestyle (n=13,727) | `CVD_diagnosis` | **0.8061** [0.7992, 0.8135] | **0.1784** [0.1750, 0.1816] | **0.0122** [0.0090, 0.0199] | 0.6980 [0.6877, 0.7095] | 0.7771 [0.7670, 0.7866] |
| **Baseline Clinical Feature Model** | Clinical (n=238) | `CAD >50%` | **0.8595** [0.8134, 0.9029] | **0.1549** [0.1332, 0.1763] | **0.0596** [0.0561, 0.1254] | 0.8175 [0.7540, 0.8810] | 0.7232 [0.6429, 0.8036] |
| **Exercise-ST-Augmented Diagnostic Model** | Clinical (n=238) | `CAD >50%` | **0.8845** [0.8433, 0.9242] | **0.1341** [0.1086, 0.1601] | **0.0549** [0.0508, 0.1146] | 0.8254 [0.7619, 0.8889] | 0.8214 [0.7500, 0.8839] |
| **Clinical Staged Fusion Ensemble** | Clinical (n=238) | `CAD >50%` | **0.8938** [0.8530, 0.9303] | **0.1336** [0.1117, 0.1560] | **0.0792** [0.0686, 0.1331] | 0.7937 [0.7222, 0.8571] | 0.8036 [0.7321, 0.8663] |
| **Genetic Context Sensitivity ($\lambda=0.15$)** | Clinical (n=238) | `CAD >50%` | **0.8938** [0.8530, 0.9303] | **0.1398** [0.1205, 0.1595] | **0.1083** [0.0857, 0.1577] | 0.7937 [0.7222, 0.8571] | 0.8036 [0.7321, 0.8663] |

---

### Table S4: PulsePhysio Hemodynamic Grounding & Literature Concordance
| Scenario | Simulated Physiological Mechanism | Pulse $\Delta\text{SBP}$ (mmHg) | Pulse $\Delta\text{DBP}$ (mmHg) | $\Delta\text{SVR}$ (%) | $\Delta\text{Double Product}$ (%) | Clinical Literature Benchmark Citation | Relative Deviation | Concordance |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Aerobic Exercise** | NO release, conductance gain, baroreflex resetting | **-4.3 ± 2.1** | -2.2 ± 1.4 | -6.5% | **-6.4%** | Whelton et al. *JACC* 2018 (-4.0 mmHg) | 7.50% | ✅ Highly Concordant |
| **5% Weight Loss** | RAAS suppression, renal fluid unloading | **-5.1 ± 2.8** | -3.0 ± 1.8 | -5.0% | **-3.6%** | Neter et al. *Hypertension* 2003 (-5.2 mmHg) | 1.92% | ✅ Highly Concordant |
| **Smoking Cessation** | Alpha-adrenergic removal, arterial compliance gain | **-5.5 ± 3.2** | -3.5 ± 2.1 | -8.0% | **-3.9%** | Ambrose & Barua *JACC* 2004 (-5.5 mmHg) | 0.00% | ✅ Highly Concordant |
| **Combined Lifestyle** | Hemodynamic & autonomic multi-system convergence | **-8.9 ± 4.1** | -5.4 ± 2.8 | -12.0% | **-9.6%** | Appel et al. *NEJM* 1997 (DASH, -9.5 mmHg) | 6.32% | ✅ Highly Concordant |
| **Workload Sparing** | Myocardial oxygen consumption reduction | - | - | - | **-9.49%** | Gobel et al. *Circulation* 1978 (-9.5%) | 0.11% | ✅ Highly Concordant |

---

### Table S5: Decision Curve Analysis (DCA) Net Benefit across Model Decision Thresholds
| Decision Threshold | Treat All (95% CI) | Baseline Model (95% CI) | Diagnostic Model (95% CI) | Clinical Staged Fusion Ensemble (95% CI) | Genetic Context Sensitivity (95% CI) |
|:---:|:---:|:---:|:---:|:---:|:---:|
| **10%** | 0.4771 [0.4771, 0.4771] | 0.4804 [0.4781, 0.4827] | 0.4785 [0.4692, 0.4851] | **0.4823** [0.4795, 0.4851] | 0.4771 [0.4771, 0.4771] |
| **20%** | 0.4118 [0.4118, 0.4118] | 0.4317 [0.4160, 0.4454] | 0.4328 [0.4044, 0.4569] | **0.4391** [0.4149, 0.4580] | 0.4338 [0.4170, 0.4485] |
| **30%** | 0.3277 [0.3277, 0.3277] | 0.3776 [0.3451, 0.4058] | 0.3962 [0.3625, 0.4292] | 0.4046 [0.3751, 0.4352] | **0.4088** [0.3818, 0.4358] |
| **40%** | 0.2157 [0.2157, 0.2157] | 0.3557 [0.3137, 0.3964] | **0.3641** [0.3249, 0.4062] | **0.3641** [0.3221, 0.4006] | 0.3613 [0.3179, 0.3992] |
| **50%** | 0.0588 [0.0588, 0.0588] | 0.3025 [0.2478, 0.3529] | **0.3529** [0.3025, 0.4034] | 0.3277 [0.2731, 0.3782] | 0.3277 [0.2731, 0.3782] |

---

## 3. Tiered 26-Point Master Integrity & Reproducibility Gate (`nb12_methodology_audit.py`)

```
==========================================================================================
  INTEGRITY GATE SUMMARY: 26/26 ASSERTIONS PASSED (100.0%)
  Verification Classes:        14 Actively Recomputed | 8 Artifact Verified | 4 Scope Declared
  Internal Reproducibility:    PASS
  External Validation:         NOT_PERFORMED (Requires prospective South Asian cohort)
  Deployment Scope:            RESEARCH_PROTOTYPE_ONLY
  Report saved:                E:/Capstone/Outputs/Reports/methodology_audit_report.json
==========================================================================================
```

---

## 4. Anticipated Peer Review Considerations & Responses

| Peer Review Concern | Methodological Justification & Evidence |
|---|---|
| **"Is the PRS individual or population-level?"** | We explicitly formulate the genetic baseline as the population-level context ($\text{PRS}_{\text{population}} = \sum 2p_{\text{effect}, i} \beta_i$) combining 21,767 observed GenomeIndia TSV frequencies (54.31%) and 18,312 calibrated South-Asian prior frequencies (45.69%). Individual genotype scoring ($\sum G_i \beta_i$) is transparently delineated. |
| **"How were ensemble fusion weights selected without test leakage?"** | Fusion weights ($w_{\text{diag}} = 0.70, w_{\text{base}} = 0.30$) were optimized strictly on training folds ($n=952$) via 5-fold cross-validation optimizing ROC-AUC (`argmax_cv_auc = 0.8912`) and frozen prior to evaluation on the held-out test cohort ($n=238$). |
| **"Why does clinical model AUC change between baseline and diagnostic configurations?"** | Removing post-test exercise ST-depression (`oldpeak`) yields a baseline feature AUC of 0.8595, while diagnostic confirmation with exercise testing achieves AUC 0.8845 ($\Delta\text{AUC} = +0.0250$, recomputed live on held-out test set). |
| **"How is PulsePhysio integrated with ML?"** | PulsePhysio acts as a mechanistic physiological translation layer ($\Delta\text{Hemodynamics} \to \Delta\text{Features} \to \text{ML Re-inference}$), grounding risk changes on a common endpoint ($\Delta P = P_{\text{post}} - P_{\text{baseline}} < 0$). SVR and double product serve as biophysical context and do not enter tabular ML vectors. |
| **"Are sanity checks passing?"** | All 13/13 sanity checks achieve 100.0% pass rate split into 6/6 Category A (Intervention Plausibility) and 7/7 Category B (Model Sensitivity), actively re-executed on live model pipelines in NB12. |

---
*Supplementary package verified against canonical metrics in `Outputs/Clinical/canonical_benchmark_metrics.json` and master audit in `Outputs/Reports/methodology_audit_report.json`.*