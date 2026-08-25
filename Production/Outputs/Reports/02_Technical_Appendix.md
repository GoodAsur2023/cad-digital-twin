# Technical Appendix
## India-Specific CAD Digital Twin: Full Computational Pipeline Documentation

**Project**: Capstone Phase 2 — UE23CS320B  
**Date**: August 2026  
**Classification**: Technical Reference (Stage 7 Hardened)  

---

## A. Data Sources & Preprocessing

### A.1 Cohort Descriptions & Provenance

| Dataset | N | Features | Target Variable | Clinical / Methodological Role |
|---|---|---|---|---|
| **Lifestyle Development Cohort** | 69,825 | 14 | `CVD_diagnosis` (binary) | Methodology development & population lifestyle risk modeling |
| **Clinical Diagnostic Cohort** | 1,190 | 10–18 | `angiographic_CAD_gt50pct` (>50% stenosis) | Baseline clinical feature assessment & exercise-ST-augmented diagnostic ensemble |
| **GenomeIndia Project (GI)** | 9,768 | Summary Stats | Population Allele Frequencies ($p_{\text{effect}, i}$) | Indian population-specific genetic baseline context |
| **Canonical PGS000116 Score** | 40,079 | Variant-level | Log Odds Ratios ($\beta_i$) | Genome-wide CAD polygenic scoring & gene/pathway mapping |

### A.2 Preprocessing Pipeline (NB1–NB3)

**Lifestyle Pipeline (NB1)**:
- Missing value imputation: median (continuous), mode (categorical).
- Outlier capping: IQR $\times 1.5$ boundaries.
- Feature engineering: BMI, pulse pressure, risk factor count.
- Stratified 80/20 train/test split ($n_{\text{train}} = 54,898, n_{\text{test}} = 13,727$).

**Clinical Pipeline (NB2)**:
- Missing value imputation: **Iterative Chained-Equation Imputation (IterativeImputer, max_iter=10)** for continuous features (`cholesterol`, `resting_bp`), and **Most-Frequent Mode Imputation** for categorical feature (`st_slope`).
- Outlier policy: Training-fold IQR $\times 1.5$ capping for continuous biomarkers. Negative `oldpeak` values are retained as observed in source recordings without alteration.
- Categorical one-hot encoding for multiclass features (`chest_pain_type`, `resting_ecg`, `st_slope`).
- Standardization: `StandardScaler` fitted strictly on training folds inside cross-validation pipelines.
- Stratified 80/20 train/test split ($n_{\text{train}} = 952, n_{\text{test}} = 238$).
- Saved unprocessed test snapshot (`df_clinical_test_raw.csv`) for physiological counterfactual re-inference in original clinical units.

**Genomics Pipeline (NB3)**:
- Liftover: Standardized to Ensembl GRCh38.
- Variant Harmonization & Allele Orientation: Targeted chromosome-level matching against GenomeIndia whole-genome release (9,768 samples), strand orientation validation (40,067 direct REF/ALT matches, 12 non-palindromic reverse-complement strand flips, 0 proxies, 0 mismatches).
- Frequency Source Breakdown: **21,767 GenomeIndia-derived observed TSV frequencies (54.31%)** and **18,312 calibrated South-Asian population-prior frequencies under $\text{Beta}(\alpha=2.2, \beta=2.0)$ (45.69%)** for variants lacking direct TSV coverage.
- Exported Single Source of Truth: [`Outputs/Genetics/pgs000116_genomeindia_harmonized.csv`](file:///e:/Capstone/Outputs/Genetics/pgs000116_genomeindia_harmonized.csv) (40,079 rows).

---

## B. Polygenic Risk Score Formulation & Ablation (NB4, Ablation Engine)

### B.1 Population-Level vs Individual-Level PRS Semantics

In the absence of individual patient whole-genome microarrays for the clinical cohort, the genetic risk baseline is formulated via two complementary metrics:

1. **Signed Directional Population PRS**:
   $$\text{PRS}_{\text{population}} = \sum_{i=1}^{M} 2 p_{\text{effect}, i} \beta_i$$
   where $p_{\text{effect}, i}$ is the GenomeIndia frequency aligned to the effect allele orientation, and $\beta_i$ is the GWAS effect size ($\mathbb{E}[\text{PRS}] = 2.5204 \pm 0.1135$).

2. **Absolute Genetic Burden Index (GBI)**:
   $$\text{GBI}_{\text{population}} = \sum_{i=1}^{M} 2 p_{\text{effect}, i} |\beta_i|$$
   measuring the aggregate absolute genetic perturbation magnitude across all 40,079 loci ($\text{GBI} = 35.3624$).

This is strictly distinguished from individual-level dosage scoring ($\text{PRS}_{\text{individual}} = \sum G_i \beta_i$).

### B.2 Multi-Catalog Benchmark & Uncertainty Quantification

| Catalog | Trait & Method | Evaluated Variants | Harmonization Rate | Frequency Source | MC Mean ($\mu$) | Genotype Spread ($\sigma_{\text{MC}}$) | Marginal Delta-Method SE ($\text{SE}_{\bar{X}}$) | Normalized Genetic Index |
|---|---|---|---|---|---|---|---|---|
| **PGS000116** | CAD (lassosum) | 40,079 | **100.0%** | GenomeIndia Observed & Calibrated | **2.520** | **0.114** ($\text{CV}=4.5\%$) | **0.00115** [2.5182, 2.5227] | **0.4977** (Centered) |
| PGS002809 | CAD (GWAS Hits) | 206 | 88.3% | GenomeIndia Matched chr1–22 | 11.881 | 0.460 ($\text{CV}=3.82\%$) | 0.00465 [11.871, 11.889] | 0.9999 (Saturated) |
| PGS003725 | CAD (LDpred2) | 1,296,172 | 3.9% | Synthetic Beta(2,2) Sensitivity | 8.974 | 0.079 ($\text{CV}=0.88\%$) | 0.00081 [8.968, 8.972] | 0.9998 (Saturated) |
| PGS004696 | CAD (PRS-CSx) | 1,289,980 | 3.9% | Synthetic Beta(2,2) Sensitivity | 7.706 | 0.054 ($\text{CV}=0.70\%$) | 0.00051 [7.709, 7.711] | 0.9995 (Saturated) |

**Statistical Clarifications**:
- **Marginal-Frequency Delta-Method SE**: Computed over $N=9,768$ individuals: $\text{Var}(\hat{\text{PRS}}) = \sum (2\beta_i)^2 \frac{p_i(1-p_i)}{2N} \implies \text{SE} = 0.00115$ (95% CI: $[2.5182, 2.5227]$). This interval quantifies marginal allele-frequency sampling uncertainty under the stated SNP-independence approximation; it does not represent full uncertainty in PGS effect sizes, LD structure, or population-prior specification.
- **Inter-Individual Genotype Spread**: Characterized by Monte Carlo sampling under an **Independent-HWE approximation** ($\sigma_{\text{MC}} = 0.1135$).

### B.3 Relative Genetic Index & Sensitivity Spectrum

Normalized relative genetic index:
$$
z = \frac{\text{PRS}_{\text{raw}} - \mu_{\text{MC}}}{\sigma_{\text{MC}}}, \quad P_{\text{PRS}} = \sigma(z)
$$
For a population-mean Indian individual, $z \approx 0 \implies P_{\text{PRS}} = 0.4977 \approx 0.50$ (centered by construction).
Prior-informed probability integration evaluates the influence of the genetic prior across a sensitivity parameter $\lambda$:
$$
P_{\text{integrated}}(\lambda) = (1 - \lambda) \cdot P_{\text{Fused}} + \lambda \cdot P_{\text{PRS}}
$$

| Prior Weight ($\lambda$) | Integrated Model | Test AUC | Brier Loss | Standard 10-Bin ECE | Methodological Interpretation |
|:---:|---|:---:|:---:|:---:|---|
| **0.00** | $(1.00) P_{\text{Fused}} + (0.00) P_{\text{PRS}}$ | **0.8938** | **0.1336** | **0.0792** | Primary Validated Empirical Prediction |
| **0.05** | $(0.95) P_{\text{Fused}} + (0.05) P_{\text{PRS}}$ | **0.8938** | **0.1353** | **0.0970** | Conservative Genetic Sensitivity Check |
| **0.10** | $(0.90) P_{\text{Fused}} + (0.10) P_{\text{PRS}}$ | **0.8938** | **0.1373** | **0.0993** | Moderate Prior Sensitivity Check |
| **0.15** | $(0.85) P_{\text{Fused}} + (0.15) P_{\text{PRS}}$ | **0.8938** | **0.1398** | **0.1083** | Upper Bound Prior Sensitivity Check |

---

## C. Model Training & Anti-Leakage Audit (NB5–NB6, NB12)

### C.1 Lifestyle Model (NB5)
- **Algorithm**: XGBoost (`XGBClassifier`) with Optuna hyperparameter optimization.
- **Calibrator**: `CalibratedClassifierCV(method='sigmoid', cv=5)`.
- **Features (14)**: `age`, `gender`, `systolic_bp`, `diastolic_bp`, `smoking`, `alcohol`, `physical_activity`, `bmi`, `cholesterol_level_1-3`, `glucose_level_1-3`.
- **Performance**: Test AUC = **0.8061** [0.7992, 0.8135], Brier Loss = **0.1784** [0.1750, 0.1816], Standard 10-bin ECE = **0.0122** [0.0090, 0.0199].

### C.2 Clinical Models: Baseline vs Exercise-ST-Augmented Diagnostic (NB6, NB12)
1. **Baseline Clinical Feature Model (9 features)**:
   - Features: `age`, `sex`, `resting_bp`, `cholesterol`, `fasting_blood_sugar`, `max_heart_rate`, `resting_ecg_0.0`, `resting_ecg_1.0`, `resting_ecg_2.0`.
   - Algorithm: `GradientBoostingClassifier` with 5-fold CV sigmoid calibration.
   - Role: Baseline clinical feature evaluation excluding exercise-induced ST-depression marker.
   - Performance: Test AUC = **0.8595** [0.8134, 0.9029], Brier Loss = **0.1549** [0.1332, 0.1763], ECE = **0.0596** [0.0561, 0.1254].
2. **Exercise-ST-Augmented Diagnostic Model (10 features)**:
   - Features: Same 9 baseline features + exercise ST-depression (`oldpeak`).
   - Algorithm: `XGBClassifier` with 5-fold CV sigmoid calibration.
   - Role: Diagnostic risk assessment augmented with exercise treadmill ECG data.
   - Performance: Test AUC = **0.8845** [0.8433, 0.9242], Brier Loss = **0.1341** [0.1086, 0.1601], ECE = **0.0549** [0.0508, 0.1146].
   - Ischemia Marker Gain: $\Delta\text{AUC} = +0.0250$ from adding `oldpeak` (live recomputed on held-out test set).
3. **Clinical Staged Fusion Ensemble**:
   - Optimal weights ($w_{\text{diag}} = 0.70, w_{\text{baseline}} = 0.30$) derived strictly via training-fold 5-fold cross-validation optimizing `roc_auc` (`selection_rule: argmax_cv_auc = 0.8912`) and frozen prior to test evaluation (`test_used_for_tuning = False`).
   - Performance: Test AUC = **0.8938** [0.8530, 0.9303], Brier Loss = **0.1336** [0.1117, 0.1560], ECE = **0.0792** [0.0686, 0.1331].

---

## D. Explainability & Actionability Classification (NB8)

### D.1 TreeSHAP Decomposition
TreeSHAP exact attribution on the clinical test set:
- Top Risk Drivers: `oldpeak` (Mean $|SHAP| = 0.260$), `max_heart_rate` ($0.222$), `sex` ($0.190$), `age` ($0.114$), `fasting_blood_sugar` ($0.117$), `resting_bp` ($0.095$), `cholesterol` ($0.053$).

### D.2 Decoupled Attribution Summary
- **Empirical Feature Attribution**: **100% computed across empirical features** (Clinical Domain: **82.3%**, Lifestyle Domain: **13.3%**).
- **Genetic Context Layer**: Decoupled from TreeSHAP and applied as an external prior probability shift ($\Delta P_{\text{gen}}$).

---

## E. Digital Twin Counterfactuals & Categorized Sanity Battery (NB9, NB12 Live)

### E.1 Categorized Sanity Check Battery (13/13 PASS Live Re-Executed)

| Test # | Category | Perturbation Scenario | Cohort | Expected Shift | Observed Shift ($\Delta P$) | Status |
|:---:|:---:|---|:---:|:---:|:---:|:---:|
| 1 | Category A | Sedentary (0) $\to$ Active (1) | Lifestyle | DECREASE | -0.0365 | ✅ PASS |
| 2 | Category A | Healthy BMI (22) $\to$ Overweight (28) | Lifestyle | INCREASE | +0.0509 | ✅ PASS |
| 3 | Category A | Healthy BMI (22) $\to$ Obese (35) | Lifestyle | INCREASE | +0.0821 | ✅ PASS |
| 4 | Category A | Smoker+Sedentary $\to$ Smoke-free+Active | Lifestyle | DECREASE | -0.0097 | ✅ PASS |
| 5 | Category A | Smoking Cessation + BP Restoration | Lifestyle | DECREASE | -0.3341 | ✅ PASS |
| 6 | Category A | Heavy Alcohol (1) $\to$ Abstinence (0) | Lifestyle | DECREASE | -0.1869 | ✅ PASS |
| 7 | Category B | Normal BP (120) $\to$ Hypertensive (160) | Clinical | INCREASE | +0.0804 | ✅ PASS |
| 8 | Category B | Hypertensive (160) $\to$ Normal BP (120) | Clinical | DECREASE | -0.0804 | ✅ PASS |
| 9 | Category B | Low Chol (160) $\to$ High Chol (260) | Clinical | INCREASE | +0.0453 | ✅ PASS |
| 10 | Category B | High Chol (260) $\to$ Low Chol (160) | Clinical | DECREASE | -0.0453 | ✅ PASS |
| 11 | Category B | Low Max HR (110) $\to$ High Max HR (170) | Clinical | DECREASE | -0.2217 | ✅ PASS |
| 12 | Category B | High Oldpeak (2.5) $\to$ Zero Oldpeak (0) | Clinical | DECREASE | -0.2214 | ✅ PASS |
| 13 | Category B | Comprehensive Risk Factor Normalization | Clinical | DECREASE | -0.6232 | ✅ PASS |

*Methodological Note*: Category A evaluates behavioral and clinical intervention plausibility; Category B evaluates mathematical model sensitivity and monotonicity. Intervention rankings are model-informed counterfactual simulations and are not estimates of causal treatment effects or clinical prescriptions.

---

## F. PulsePhysio Mechanistic Hemodynamic Grounding (NB10)

- **Engine Version**: Kitware Pulse Physiology Engine v4.3.2 (`libPulseC.dll` C-API).
- **Cohort**: 238 CAD patients $\times$ 4 intervention scenarios = 952 native whole-body simulations.
- **Workload Sparing**: Mean rate-pressure double product reduction = **-9.49%**.
- **Hemodynamic Shifts & Canonical Sign Convention ($\Delta P < 0$)**:
  - `exercise_aerobic`: $\Delta\text{SBP} = -4.3\text{ mmHg}, \Delta\text{HR} = -3.2\text{ bpm}, \Delta P = -0.0057$.
  - `weight_loss_5pct`: $\Delta\text{SBP} = -5.1\text{ mmHg}, \Delta\text{MAP} = -3.7\text{ mmHg}, \Delta P = -0.0062$.
  - `smoking_cessation`: $\Delta\text{SBP} = -5.5\text{ mmHg}, \Delta\text{SVR} = -8.0\%, \Delta P = -0.0185$.
  - `combined_exercise_diet`: $\Delta\text{SBP} = -8.9\text{ mmHg}, \Delta\text{SVR} = -12.0\%, \Delta P = -0.0302$ (a 3.02 percentage point risk reduction).
- **Feature Translation Policy**: SVR and rate-pressure double product do not enter the ML prediction feature vector; they serve as biophysical context.

---

## G. Genetic Intelligence Engine (GIE) on Primary Catalog PGS000116

- **Canonical Table**: [`Outputs/Genetics/pgs000116_genomeindia_harmonized.csv`](file:///e:/Capstone/Outputs/Genetics/pgs000116_genomeindia_harmonized.csv) (40,079 rows).
- **Top Curated CVD Loci**: CDKN2B-AS1 (20.48% of annotated signal, 9p21.3), LPA (15.23%), SORT1 (5.68%), PHACTR1 (5.11%), LPL (4.84%), APOE (4.53%), LDLR (3.80%), ADAMTS7 (3.46%), IL6R (3.24%), PCSK9 (3.19%), HMGCR (2.96%).
- **Pathway Contribution Analysis**: Lipid Metabolism (2.13% of total GBI), Cell Cycle / 9p21.3 (0.90%), Vascular Remodeling (0.66%), Inflammation/Immune (0.32%), Pharmacogenomics (0.04%), Genome-Wide Background (95.60%).
- **Pharmacogenomics Guidelines**:
  - **CPIC Level A**: SLCO1B1 (statin myopathy), CYP2C19 (clopidogrel resistance), HMGCR (statin response).
  - **AHA/ACC Guidelines**: PCSK9 (PCSK9 inhibitor eligibility).
  - **Scope Metadata**: `requires_individual_genotype: true`, `patient_genotype_available: false`, `clinical_status: "population_knowledge_only"`.

---

## H. Tiered 26-Point Master Integrity & Reproducibility Gate (`nb12_methodology_audit.py`)

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
All 26 predefined internal methodological integrity checks passed across the three formal verification tiers with live computational execution.

---
*Technical appendix generated from computational pipeline NB1–NB12. Master metric reference: `Outputs/Clinical/canonical_benchmark_metrics.json` and `Outputs/Genetics/pgs000116_genomeindia_harmonized.csv`.*