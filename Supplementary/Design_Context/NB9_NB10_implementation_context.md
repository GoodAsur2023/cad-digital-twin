# CAD Digital Twin — NB9 & NB10 Implementation Context
**Document Purpose:** Everything needed to implement NB9 (Digital Twin Counterfactual Engine) and NB10 (PulsePhysio Integration) without re-reading NB1–NB5.
**Source:** Synthesized from actual notebook code in NB1–NB5 + CAD_final_pipeline_v2.pdf blueprint.

---

## 0. Critical Deviations from Blueprint (Read First)

These are places where the actual implementation DIFFERS from what the blueprint originally specified. Ignoring these will cause errors in NB9/NB10.

| Blueprint Spec | Actual NB1–NB5 Implementation | Impact on NB9/NB10 |
|---|---|---|
| NB1 saves a `lifestyle_scaler.pkl` | **Scaler NOT saved in NB1** — scaling was moved inside the NB5 pipeline | NB9 must NOT look for a separate scaler; the pipeline handles it internally |
| NB5 saves `lifestyle_best_model.pkl` | **Saved as `lifestyle_pipeline.pkl`** (includes scaler inside) | NB9 loads `lifestyle_pipeline.pkl`, NOT `lifestyle_best_model.pkl` |
| Pipeline wrapping | Model is `CalibratedClassifierCV(Pipeline([StandardScaler, clf]), method='sigmoid', cv=5)` | Call `.predict_proba(X_raw)[:, 1]` on RAW (unscaled) input |
| Age in days | **Age is already in decimal years** in Cardio_Data.csv (no conversion done) | Do NOT apply any day→year conversion in NB9 |
| NB4 PRS output key `sigmoid_prs` | **Not present** — actual keys are: `prs_raw`, `prs_mean_mc`, `ci_lower`, `ci_upper`, `n_snps` | NB7 integration must compute `sigmoid(prs_raw)` manually |
| 70k split: 70/15/15 | **Actual split: 80% train / 20% test** (no validation set in NB1) | ~54,906 train rows, ~13,727 test rows |
| 1190 split: 70/15/15 | **Actual split: 80% train / 20% test** (no validation set in NB2) | ~952 train rows, ~238 test rows |

---

## 1. Directory Structure (Google Drive)

```
BASE_DIR = "/content/drive/MyDrive/CAD_DT_Final/"

CAD_DT_Final/
├── Data/
│   └── Raw/
│       ├── Cardio_Data.csv
│       ├── heart_statlog_cleveland_hungary_final.csv
│       ├── pgs_catalog_2809.tsv
│       └── Genome_India/
│           ├── GI_9768_CBR-NIBMG_JointCall_AF_chr1.tsv
│           └── ... (chr2 through chr22)
├── Outputs/
│   ├── Lifestyle/
│   │   ├── df_lifestyle_train.csv
│   │   └── df_lifestyle_test.csv
│   ├── Clinical/
│   │   ├── df_clinical_train.csv
│   │   ├── df_clinical_test.csv
│   │   ├── df_clinical_test_raw.csv         ← KEY for NB10 (unscaled mmHg/mg/dL values)
│   │   ├── clinical_scaler.pkl
│   │   └── clinical_imputer.pkl
│   ├── Genetics/
│   │   ├── harmonized_genetic_map.csv
│   │   ├── dropped_snps_audit_log.csv
│   │   ├── prs_population_score.csv
│   │   ├── per_snp_contribution.csv
│   │   └── prs_feature_vector.pkl
│   ├── Models/
│   │   ├── lifestyle_pipeline.pkl            ← PRIMARY model for NB9 (lifestyle features)
│   │   ├── lifestyle_model_results.csv
│   │   ├── lifestyle_feature_importance.csv
│   │   ├── clinical_pipeline.pkl             ← From NB6 (clinical features) — not yet uploaded
│   │   └── clinical_model_results.csv        ← From NB6
│   ├── Integrated/                           ← From NB7 (not yet uploaded)
│   │   ├── lifestyle_risk_scores_with_pgs.csv
│   │   ├── clinical_risk_scores_with_pgs.csv
│   │   └── risk_stratification_bands.csv
│   ├── Fusion/                               ← From NB8 (not yet uploaded)
│   │   ├── fusion_meta_learner.pkl
│   │   └── fusion_calibrated_model.pkl
│   ├── DigitalTwin/                          ← NB9 writes here (create if missing)
│   │   ├── intervention_results.csv
│   │   └── sanity_check_results.csv
│   ├── Pulse/                                ← NB10 writes here (create if missing)
│   │   ├── pulse_haemodynamic_deltas.csv
│   │   └── pulse_updated_risk_scores.csv
│   └── Figures/
│       ├── trajectory_visualization.png      ← NB9 output
│       ├── intervention_ranking_example.png  ← NB9 output
│       └── pulse_vs_ml_delta_comparison.png  ← NB10 output
```

---

## 2. Lifestyle Dataset Feature Schema (NB1 → NB5)

### 2.1 Raw Cardio_Data.csv column names → renamed in NB1

| Original Column | Renamed To | Notes |
|---|---|---|
| `age` | `age` | Already in decimal years (NOT days; NB1 confirmed this) |
| `gender` | `gender` | Encoded: `'f'`→0, `'m'`→1 |
| `height` | `height_cm` | Dropped after BMI computation |
| `weight` | `weight_kg` | Dropped after BMI computation |
| `ap_hi` | `systolic_bp` | Continuous mmHg |
| `ap_lo` | `diastolic_bp` | Continuous mmHg |
| `cholesterol` | `cholesterol_level` | Ordinal 1/2/3 → OHE'd (see below) |
| `gluc` | `glucose_level` | Ordinal 1/2/3 → OHE'd (see below) |
| `smoke` | `smoking` | Binary 0/1 |
| `alco` | `alcohol` | Binary 0/1 |
| `active` | `physical_activity` | Binary 0/1 |
| `target` | `target` | Binary 0/1 |

### 2.2 Feature Engineering Applied in NB1

- **BMI**: `bmi = weight_kg / (height_cm / 100)^2` → added as new feature
- **height_cm and weight_kg**: Dropped after BMI creation
- **bmi_category**: Created for EDA only, dropped before model training
- **OHE**: `cholesterol_level` (values 1,2,3) and `glucose_level` (values 1,2,3) one-hot encoded with `drop_first=False`

### 2.3 Final Feature Columns (15 features entering NB5 pipeline)

```python
LIFESTYLE_FEATURE_COLS = [
    'age',                     # continuous, decimal years
    'gender',                  # binary: 0=female, 1=male
    'systolic_bp',             # continuous, mmHg
    'diastolic_bp',            # continuous, mmHg
    'bmi',                     # continuous, kg/m²
    'smoking',                 # binary: 0=non-smoker, 1=smoker
    'alcohol',                 # binary: 0=no, 1=yes
    'physical_activity',       # binary: 0=inactive, 1=active
    'cholesterol_level_1',     # OHE: normal (original value 1)
    'cholesterol_level_2',     # OHE: above normal (original value 2)
    'cholesterol_level_3',     # OHE: well above normal (original value 3)
    'glucose_level_1',         # OHE: normal
    'glucose_level_2',         # OHE: above normal
    'glucose_level_3',         # OHE: well above normal
]
# NOTE: 'age_quintile' is mentioned in NB5 documentation but was NOT
# created in NB1 code. If present in actual CSV, include it. If not, use 14 features.
# Always verify with: pd.read_csv(TEST_PATH).columns.tolist()
```

### 2.4 Outlier Removal Applied in NB1

Rows removed (NOT capped) for:
- `systolic_bp` > 250 or < 70 mmHg
- `diastolic_bp` > 150 or < 40 mmHg
- `diastolic_bp` >= `systolic_bp`
- `height_cm` < 100 or > 220 cm
- `weight_kg` < 30 or > 200 kg

Final dataset: ~68,600 rows (≈98% of original 70,000).

### 2.5 Class Balance (Lifestyle)

Near 50/50 split — SMOTE was NOT applied (imbalance ratio < 1.5:1).

---

## 3. Clinical Dataset Feature Schema (NB2 → NB6)

### 3.1 Source

`heart_statlog_cleveland_hungary_final.csv` — 1,190 rows from 5 UCI sources.
**Do NOT** merge separate Cleveland/Hungarian files; 573+95 rows already present.
`ca` and `thal` columns intentionally absent (>90% missing at source).

### 3.2 Column Renaming in NB2

| Original | Renamed To | Type | Notes |
|---|---|---|---|
| `age` | `age` | continuous | years |
| `sex` | `sex` | binary | 0=female, 1=male (consistent with lifestyle `gender`) |
| `chest pain type` | `chest_pain_type` | ordinal | 1=typical, 2=atypical, 3=non-anginal, 4=asymptomatic → OHE'd |
| `resting bp s` | `resting_bp` | continuous | mmHg — sentinel 0 replaced with NaN, MICE imputed |
| `cholesterol` | `cholesterol` | continuous | mg/dL — sentinel 0 replaced with NaN, MICE imputed |
| `fasting blood sugar` | `fasting_blood_sugar` | binary | 0: FBS≤120, 1: FBS>120 |
| `resting ecg` | `resting_ecg` | ordinal | 0=normal, 1=ST-T abnormality, 2=LV hypertrophy → OHE'd |
| `max heart rate` | `max_heart_rate` | continuous | bpm |
| `exercise angina` | `exercise_angina` | binary | 0=no, 1=yes |
| `oldpeak` | `oldpeak` | continuous | ST depression; NEGATIVE VALUES ARE VALID (ST elevation) |
| `ST slope` | `st_slope` | ordinal | 0=unknown (sentinel NaN), 1=upsloping, 2=flat, 3=downsloping → OHE'd |
| `target` | `target` | binary | 0=no disease, 1=disease |

### 3.3 Missing Value Handling (NB2)

- `cholesterol == 0`: 172 rows → converted to NaN (physiologically impossible)
- `resting_bp == 0`: 1 row → converted to NaN
- `st_slope == 0`: 1 row → converted to NaN (encoded as "unknown")
- All missing values imputed using **MICE** (`IterativeImputer`, max_iter=10, random_state=42)
- MICE fit on X_train ONLY; same fitted imputer applied to X_test (no leakage)

### 3.4 IQR Clipping (NB2) — Applied to Train Bounds Only

Columns clipped: `cholesterol`, `resting_bp`, `max_heart_rate`, `oldpeak`
Formula: [Q1 − 1.5×IQR, Q3 + 1.5×IQR] from X_train statistics applied to both splits.

### 3.5 OHE Columns (NB2)

```python
ENCODE_COLS = ['chest_pain_type', 'resting_ecg', 'st_slope']
# drop_first=False → all dummy columns retained
# chest_pain_type: 4 dummies (values 1,2,3,4)
# resting_ecg: 3 dummies (values 0,1,2)
# st_slope: 3 dummies (values 1,2,3 — value 0 was NaN'd and imputed away)
```

### 3.6 Final Clinical Feature Columns (after OHE, ~19 features)

```python
CLINICAL_FEATURE_COLS = [
    'age', 'sex', 'resting_bp', 'cholesterol', 'fasting_blood_sugar',
    'max_heart_rate', 'exercise_angina', 'oldpeak',
    'chest_pain_type_1', 'chest_pain_type_2', 'chest_pain_type_3', 'chest_pain_type_4',
    'resting_ecg_0', 'resting_ecg_1', 'resting_ecg_2',
    'st_slope_1', 'st_slope_2', 'st_slope_3'
]
# NOTE: Always verify exact column names and order from:
# pd.read_csv(CLINICAL_TRAIN_PATH).columns.tolist()
```

### 3.7 `df_clinical_test_raw.csv` — Critical for NB10

This file is the ONLY version of clinical data with original mmHg/mg/dL values (pre-MICE, pre-scaling, pre-OHE).
**Saved BEFORE any imputation or scaling in NB2.**

```python
# df_clinical_test_raw.csv columns (12 columns):
RAW_CLINICAL_COLS = [
    'age', 'sex', 'chest_pain_type', 'resting_bp', 'cholesterol',
    'fasting_blood_sugar', 'resting_ecg', 'max_heart_rate',
    'exercise_angina', 'oldpeak', 'st_slope', 'target'
]
# resting_bp here is the ORIGINAL mmHg value (may have NaN from sentinel-zero replacement)
# cholesterol here is the ORIGINAL mg/dL value (may have NaN)
# These NaNs in df_clinical_test_raw are expected — do NOT treat as errors
```

### 3.8 StandardScaler (NB2)

NB2 DOES apply StandardScaler (fit on X_train, transform both splits).
`clinical_scaler.pkl` is saved at: `Outputs/Clinical/clinical_scaler.pkl`
To reconstruct raw clinical features from scaled output: `scaler.inverse_transform(X_scaled)`

---

## 4. Genetics / PRS Layer (NB3 → NB4)

### 4.1 Harmonized Genetic Map (NB3 output)

File: `Outputs/Genetics/harmonized_genetic_map.csv`

```python
HARMONIZED_MAP_COLS = [
    'rsID',                           # e.g., 'rs11591147'
    'chromosome',                     # integer 1–22
    'position_grch',                  # GRCh38 base-pair position
    'effect_allele',                  # risk-increasing allele (uppercase)
    'effect_weight_beta',             # log-odds coefficient from GWAS
    'gi_reference_allele',            # REF allele in GenomeIndia VCF
    'gi_alternate_allele',            # ALT allele in GenomeIndia VCF
    'gi_alt_allele_frequency',        # raw ALT frequency from GenomeIndia
    'indian_ancestry_risk_allele_freq' # aligned frequency for risk allele
]
# ~182 rows retained after palindromic SNP filter + MAF filter
# snp_status column may also be present: 'matched', 'complemented', 'excluded'
```

### 4.2 PRS Computation (NB4)

**Formula:**
```
per_snp_contribution[j] = 2 × indian_ancestry_risk_allele_freq[j] × effect_weight_beta[j]
population_PRS = sum(per_snp_contribution)   # typically in range 8–15 for 182 SNPs
```

### 4.3 PRS Feature Vector (NB4 output)

File: `Outputs/Genetics/prs_feature_vector.pkl`
Type: Python `dict`

```python
prs_feature_vector = {
    'prs_raw':    float,  # point-estimate PRS (sum of 2×p×beta)
    'prs_mean_mc': float, # mean of 10,000 Monte Carlo simulations
    'ci_lower':   float,  # 2.5th percentile of MC distribution
    'ci_upper':   float,  # 97.5th percentile of MC distribution
    'n_snps':     int,    # number of SNPs used (typically 182)
}
# IMPORTANT: 'sigmoid_prs' key does NOT exist — compute it manually when needed
# sigmoid(x) = 1 / (1 + exp(-x))
```

File: `Outputs/Genetics/prs_population_score.csv`
CSV with 1 row, columns: `prs_raw`, `prs_mean_mc`, `ci_lower`, `ci_upper`, `n_snps`

### 4.4 How PRS is Used Downstream (NB7 Integration Formula)

The PRS is integrated via a weighted combination (from blueprint NB7):
```python
import scipy.special
p_integrated = w1 * p_model + w2 * scipy.special.expit(prs_raw)
# w1 = 0.85, w2 = 0.15 (defaults; w1 + w2 = 1)
# expit() == sigmoid()
```

This is a FIXED SCALAR applied equally to all patients (population-level offset, not individual genotyping).

---

## 5. Model Objects (NB5 → NB9)

### 5.1 Lifestyle Model Object

File: `Outputs/Models/lifestyle_pipeline.pkl`
Type: `CalibratedClassifierCV(Pipeline([('scaler', StandardScaler()), ('clf', BestClf)]), method='sigmoid', cv=5)`

```python
import pickle
with open("Outputs/Models/lifestyle_pipeline.pkl", 'rb') as f:
    lifestyle_pipeline = pickle.load(f)

# CORRECT usage — pass RAW (unscaled) lifestyle features:
y_proba = lifestyle_pipeline.predict_proba(X_raw)[:, 1]

# DO NOT manually scale X before passing to this pipeline.
# The StandardScaler is embedded as the first step in the Pipeline
# inside CalibratedClassifierCV, so it handles scaling internally.
```

**Which model was selected?** Best by test-set AUC from: Logistic Regression, Random Forest, XGBoost, SGD Classifier.
XGBoost was expected to perform best (~AUC 0.78–0.82). Check `lifestyle_model_results.csv` to confirm.

### 5.2 Clinical Model Object (NB6 — expected structure)

File: `Outputs/Models/clinical_pipeline.pkl` (or `clinical_best_model.pkl`)
Type: Same pattern — `CalibratedClassifierCV(Pipeline([StandardScaler, clf]))`

```python
# IMPORTANT: Clinical model input is SCALED (NB2 applies StandardScaler separately)
# Two possible approaches depending on NB6 implementation:
# Option A: Pipeline includes its own StandardScaler → pass raw features
# Option B: Pipeline expects pre-scaled input → scale with clinical_scaler.pkl first
# CHECK NB6 notebook implementation to confirm which pattern was used
```

### 5.3 Feature Importance (Lifestyle, from NB5)

Top features by AUC contribution (expected order from clinical literature):
1. `systolic_bp` (strongest modifiable CVD predictor — SPRINT 2015)
2. `age`
3. `diastolic_bp` or `cholesterol_level_3`
4. `bmi`
5. `physical_activity` / `smoking`

If `systolic_bp` is NOT in top 3, flag as a preprocessing anomaly.

---

## 6. NB9 — Digital Twin Counterfactual Engine

### 6.1 Inputs Required by NB9

```python
# ── From NB8 (primary — must exist before running NB9) ──────
FUSION_MODEL_PATH  = BASE_DIR + "Outputs/Fusion/fusion_calibrated_model.pkl"
# fallback if NB8 not yet run:
LIFESTYLE_MODEL    = BASE_DIR + "Outputs/Models/lifestyle_pipeline.pkl"
CLINICAL_MODEL     = BASE_DIR + "Outputs/Clinical/clinical_pipeline.pkl"  # from NB6

# ── From NB4 ────────────────────────────────────────────────
PRS_VECTOR_PATH    = BASE_DIR + "Outputs/Genetics/prs_feature_vector.pkl"

# ── From NB1 ────────────────────────────────────────────────
LIFESTYLE_TEST_PATH = BASE_DIR + "Outputs/Lifestyle/df_lifestyle_test.csv"

# ── From NB2 ────────────────────────────────────────────────
CLINICAL_TEST_RAW   = BASE_DIR + "Outputs/Clinical/df_clinical_test_raw.csv"
```

### 6.2 Counterfactual Engine Core Logic

```python
def run_counterfactual(X_patient_raw, pipeline, interventions):
    """
    X_patient_raw: pd.DataFrame (1 row), raw (unscaled) feature values
    pipeline: trained pipeline with .predict_proba()
    interventions: list of (scenario_id, feature_dict) tuples
    """
    current_risk = pipeline.predict_proba(X_patient_raw)[0, 1]
    results = []
    for scenario_id, feature_changes in interventions:
        X_modified = X_patient_raw.copy()
        for feat, new_val in feature_changes.items():
            X_modified[feat] = new_val
        new_risk = pipeline.predict_proba(X_modified)[0, 1]
        delta = current_risk - new_risk
        pct_reduction = (delta / current_risk * 100) if current_risk > 0 else 0
        results.append({
            'scenario': scenario_id,
            'current_risk': current_risk,
            'new_risk': new_risk,
            'absolute_delta': delta,
            'pct_reduction': pct_reduction,
        })
    return pd.DataFrame(results).sort_values('absolute_delta', ascending=False)
```

### 6.3 Five Intervention Scenarios (Blueprint Spec)

```python
# All perturbations are on LIFESTYLE feature space (from NB1 column names)
INTERVENTION_SCENARIOS = {
    'S1': {
        'name': 'Quit Smoking',
        'features': {'smoking': 0},
        'expected_reduction_range': (20, 45),   # % relative, from Critchley & Capewell 2003
        'published_effect': '~36% relative CAD risk reduction',
        'source': 'Critchley & Capewell, JAMA 2003',
    },
    'S2': {
        'name': 'Increase Physical Activity',
        'features': {'physical_activity': 1},  # only applied if patient is inactive (physical_activity==0)
        'expected_reduction_range': (8, 20),
        'published_effect': '~14% CAD risk reduction',
        'source': 'Chomistek et al., Circulation 2011',
    },
    'S3': {
        'name': 'Lose 5% Body Weight',
        # BMI reduced by 5% of its current value
        # Must be computed per-patient: new_bmi = current_bmi * 0.95
        'features': 'dynamic_bmi_reduction',   # flag for special handling
        'bmi_multiplier': 0.95,
        'expected_reduction_range': (2, 7),
        'published_effect': '~3-5% CAD risk reduction',
        'source': 'Multiple meta-analyses',
    },
    'S4': {
        'name': 'Reduce Alcohol',
        'features': {'alcohol': 0},            # only applied if patient is drinker (alcohol==1)
        'expected_reduction_range': (2, 10),
        'published_effect': 'Modest BP and CV risk reduction',
        'source': 'AHA Guidelines',
    },
    'S5': {
        'name': 'Combined: Quit Smoking + Exercise',
        'features': {'smoking': 0, 'physical_activity': 1},
        'expected_reduction_range': None,       # must exceed either S1 or S2 alone
        'published_effect': '>36% combined (additive minimum)',
        'source': 'Multiple sources',
    },
}
# NOTE: S3 is dynamic — must compute new_bmi = patient_bmi * 0.95 at runtime
# NOTE: S2/S4 should only perturb if baseline is inactive/drinking; verify first
```

### 6.4 Trajectory Visualisation (Simulated Projection)

**This is NOT a trained temporal model. Frame explicitly as "simulated projection" in all outputs.**

```python
# Framingham 10-year risk age-progression approximation:
# Risk increases ~1.5-2x per 10 years of age, all else equal.
# Use published Framingham lifetime risk hazard ratios (Anderson et al., 1991):
# age 35-44: base × 1.0
# age 45-54: base × 1.5
# age 55-64: base × 2.2
# age 65-74: base × 3.0

# Trajectory simulation steps:
# 1. Get current_age and current_risk for patient
# 2. Project "no change" trajectory: apply age-hazard multiplier for +5 and +10 years
# 3. Apply combined_counterfactual_delta (best intervention) to create "intervention" trajectory
# 4. Plot two diverging curves with threshold lines at 7.5% and 10%
CLINICAL_THRESHOLD_LOW  = 0.075  # 7.5% 10-year risk
CLINICAL_THRESHOLD_HIGH = 0.100  # 10% 10-year risk (ACC/AHA threshold for statin initiation)
```

### 6.5 Sanity Check Battery (All 20+ Must Pass)

NB9 must run ALL of these and record pass/fail in `outputs/DigitalTwin/sanity_check_results.csv`:

```python
SANITY_CHECKS = [
    # Format: (description, feature_column, from_val, to_val, expected_direction)
    ('Smoker → non-smoker', 'smoking', 1, 0, 'decrease'),
    ('Sedentary → active', 'physical_activity', 0, 1, 'decrease'),
    ('Healthy BMI → obese', 'bmi', 22.0, 32.0, 'increase'),
    ('Normal BP → hypertensive (clinical)', 'resting_bp', 120, 160, 'increase'),      # clinical model
    ('Normal cholesterol → high (clinical)', 'cholesterol', 160, 240, 'increase'),    # clinical model
    ('FBS normal → diabetic (clinical)', 'fasting_blood_sugar', 0, 1, 'increase'),    # clinical model
    ('Low PRS → high PRS', 'prs_integration_weight', 0.05, 0.40, 'increase'),
    ('Combined S1+S2 vs S1 alone', 'S5_vs_S1', None, None, 'S5_greater'),
    ('Combined S1+S2 vs S2 alone', 'S5_vs_S2', None, None, 'S5_greater'),
    ('Age +10 years, same features', 'age', 45, 55, 'increase'),
    ('Quit drinking', 'alcohol', 1, 0, 'decrease'),
    ('Male vs female, same features', 'gender', 1, 0, 'differ'),
    ('Normal glucose → high glucose', 'glucose_level', 1, 3, 'increase'),            # lifestyle OHE
    ('Max HR low → high (clinical)', 'max_heart_rate', 100, 170, 'decrease'),        # lower risk
    ('Exercise angina no → yes (clinical)', 'exercise_angina', 0, 1, 'increase'),
    ('ST slope upsloping → downsloping', 'st_slope_3', 0, 1, 'increase'),            # clinical OHE
    ('Oldpeak low → high (clinical)', 'oldpeak', 0.0, 3.0, 'increase'),
    ('Non-drinker + non-smoker → best lifestyle', 'combined_healthy', None, None, 'lowest_risk'),
    ('No intervention on already-healthy patient', 'all_zeros', None, None, 'minimal_delta'),
    ('BMI normal → underweight', 'bmi', 25.0, 15.0, 'possible_increase_or_decrease'),  # non-monotone
]
# "differ" means male > female expected (male has higher baseline CAD risk in literature)
# Run each check on ≥5 test patients; record direction match as pass/fail
```

### 6.6 Output Files for NB9

```
Outputs/DigitalTwin/
├── intervention_results.csv        # Per-patient × scenario risk deltas
│   columns: patient_id, scenario, current_risk, new_risk, absolute_delta, pct_reduction
├── sanity_check_results.csv        # 20+ sanity checks × pass/fail
│   columns: check_name, feature_changed, from_val, to_val, expected_dir, actual_dir, passed
└── Figures/
    ├── trajectory_visualization.png
    └── intervention_ranking_example.png
```

### 6.7 Clinical Literature Benchmarks for DT Validation

| Intervention | Published Range | Your Prediction Must Fall In |
|---|---|---|
| Quit smoking | 20–45% relative reduction | Critchley & Capewell, JAMA 2003 |
| Exercise (150 min/wk) | 8–20% relative reduction | Chomistek et al., Circulation 2011 |
| 5% weight loss | 2–7% relative reduction | Multiple meta-analyses |
| Mediterranean diet | 15–40% CVD reduction | PREDIMED, NEJM 2013 |
| Combined smoking + exercise | > either alone | Multiple sources |

If your predicted reductions fall OUTSIDE these ranges, this is a red flag that the model is either:
(a) under-powered for binary lifestyle features, or
(b) the PRS integration is dominating the probability signal.

---

## 7. NB10 — PulsePhysio Integration (Conditional)

**Execute NB10 ONLY IF the project scope requires a physiological simulator. If ML-only DT (NB9) is accepted, skip NB10 entirely.**

### 7.1 Inputs Required by NB10

```python
# Primary input for Pulse initialization:
CLINICAL_TEST_RAW   = BASE_DIR + "Outputs/Clinical/df_clinical_test_raw.csv"
# This has ORIGINAL mmHg/mg/dL values (pre-imputation, pre-scaling)
# Key columns for Pulse: age, sex, resting_bp, max_heart_rate, cholesterol, oldpeak

# Fusion model for risk re-computation:
FUSION_MODEL_PATH   = BASE_DIR + "Outputs/Fusion/fusion_calibrated_model.pkl"
```

### 7.2 Pulse Patient Initialization Fields

```python
# Extract from df_clinical_test_raw.csv:
def initialize_pulse_patient(row):
    """
    row: one row of df_clinical_test_raw
    Returns: dict of Pulse initialization parameters
    """
    systolic  = row['resting_bp']        # mmHg systolic (note: this is resting_bp from dataset)
    # IMPORTANT: The 1190 dataset only has ONE blood pressure column ('resting_bp' = systolic).
    # Diastolic is NOT available in the clinical dataset.
    # Estimate diastolic as: diastolic ≈ 0.67 × systolic (rough approximation)
    # Or use 80 mmHg as population default if resting_bp > 120
    diastolic = systolic * 0.67          # APPROXIMATE — flag in paper
    map_val   = (2 * diastolic + systolic) / 3  # mean arterial pressure

    return {
        'age':        row['age'],         # years
        'sex':        row['sex'],         # 0=female, 1=male
        'systolic_bp': systolic,          # mmHg
        'diastolic_bp': diastolic,        # mmHg (estimated)
        'map':        map_val,            # mean arterial pressure
        'max_hr':     row['max_heart_rate'],  # bpm
        'cholesterol': row['cholesterol'],    # mg/dL (may be NaN — use 200 as default)
    }
```

### 7.3 PulsePhysio Intervention Scenarios

```python
# Pulse can simulate these haemodynamic responses:
PULSE_SCENARIOS = {
    'exercise_aerobic': {
        'mechanism': 'ExerciseAction + chronic cardiac adaptation',
        'pulse_output': {'resting_bp': 'decreases', 'max_heart_rate': 'improves_capacity'},
        'maps_to_ml_feature': {'resting_bp': 'resting_bp', 'max_heart_rate': 'max_heart_rate'},
        'published_validation': 'Cornelissen & Smart, JAHA 2013: ~3.5 mmHg systolic reduction',
        'expected_bp_reduction': 3.5,  # mmHg systolic, 90-day aerobic training
    },
    'weight_loss_5pct': {
        'mechanism': 'Body composition parameters modification',
        'pulse_output': {'map': 'decreases', 'cardiac_workload': 'reduces'},
        'maps_to_ml_feature': {'resting_bp': 'resting_bp'},
        'expected_bp_reduction': 4.0,  # mmHg systolic
    },
    'smoking_cessation': {
        'mechanism': 'Increase vascular compliance',
        'pulse_output': {'map': 'decreases', 'pulse_pressure': 'decreases'},
        'maps_to_ml_feature': {'resting_bp': 'resting_bp'},
        'expected_bp_reduction': 5.0,  # mmHg systolic (within 1 year)
    },
}
# Pulse CANNOT simulate: cholesterol changes from diet, glucose/HbA1c changes
# These remain ML-only counterfactuals even when Pulse is active
```

### 7.4 Pulse → ML Feature Vector Mapping

After Pulse simulation produces new haemodynamic values, map back to ML features:

```python
def update_clinical_feature_vector(X_clinical_scaled, new_haemodynamics, clinical_scaler):
    """
    X_clinical_scaled: np.array, shape (1, n_features), currently scaled
    new_haemodynamics: dict with new {resting_bp, max_heart_rate} values
    clinical_scaler: fitted StandardScaler from NB2
    """
    # 1. Inverse transform to get back raw values
    X_raw = clinical_scaler.inverse_transform(X_clinical_scaled)

    # 2. Find column indices
    # MUST match NB2 column order exactly — check clinical_scaler.feature_names_in_
    col_names = clinical_scaler.feature_names_in_.tolist()

    # 3. Update BP if Pulse changed it
    if 'resting_bp' in new_haemodynamics:
        idx = col_names.index('resting_bp')
        X_raw[0, idx] = new_haemodynamics['resting_bp']

    if 'max_heart_rate' in new_haemodynamics:
        idx = col_names.index('max_heart_rate')
        X_raw[0, idx] = new_haemodynamics['max_heart_rate']

    # 4. Re-scale
    X_updated_scaled = clinical_scaler.transform(X_raw)
    return X_updated_scaled
```

### 7.5 NB10 Validation Requirement

**Compare Pulse-derived risk delta against ML-only delta for the same patients:**
- If Pulse exercise scenario reduces systolic BP by ~3.5 mmHg → close to Cornelissen & Smart, JAHA 2013 → Pulse validated
- If Pulse delta and ML-only delta agree within ±5% relative → ML-only approach is vindicated as valid without Pulse
- This comparison goes in the paper as supporting evidence for ML DT validity

### 7.6 Output Files for NB10

```
Outputs/Pulse/
├── pulse_haemodynamic_deltas.csv
│   columns: patient_id, scenario, baseline_sbp, new_sbp, sbp_delta,
│            baseline_hr, new_hr, hr_delta
├── pulse_updated_risk_scores.csv
│   columns: patient_id, scenario, ml_only_risk_delta, pulse_grounded_risk_delta,
│            agreement_within_5pct
└── Figures/
    └── pulse_vs_ml_delta_comparison.png
```

---

## 8. What NB6, NB7, NB8 Are Expected to Produce

These notebooks have NOT been uploaded yet but NB9/NB10 depend on their outputs. If NB9 is run before NB8 is complete, fall back to individual model predictions.

### NB6 Expected Outputs

```
Outputs/Models/
├── clinical_pipeline.pkl         # CalibratedClassifierCV(Pipeline([scaler, clf]))
└── clinical_model_results.csv    # AUC, Brier, etc. per model
# clinical_feature_importance.csv
```

Key NB6 differences from NB5:
- GridSearchCV on top 2 CV models (overfit risk with N≈952 training rows)
- `class_weight='balanced'` may be used instead of SMOTE
- If train AUC − test AUC > 0.08, stronger regularization applied
- Same 6-model zoo as NB5

### NB7 Actual Outputs (Genetic Risk Integration)

> ⚠️ **FILE NAME DEVIATION:** Output files use `_with_prs` NOT `_with_pgs`:

```
Outputs/Integrated/
├── lifestyle_risk_scores_with_prs.csv   # columns: y_true, p_base, p_integrated, band_base, band_integrated, source
├── clinical_risk_scores_with_prs.csv    # same columns
├── risk_stratification_bands.csv        # band distribution summary per cohort
Outputs/Figures/
├── risk_stratification_plot.png
├── calibration_curve_integrated.png
└── violin_plot_integrated.png
```

**NB7 actual integration formula:**
```python
# DO NOT Z-normalize PRS — preserve population-level signal
prs_sigmoid = 1.0 / (1.0 + np.exp(-prs_raw))   # ≈ 1.0 (saturated — expected)
p_integrated = 0.85 * p_model + 0.15 * prs_sigmoid
# Since prs_sigmoid ≈ 1.0: p_integrated ≈ 0.85 × p_model + 0.15
# Acts as a uniform +0.15 upward calibration shift for ALL patients
# AUC is PRESERVED (rank-based metric), Brier score may increase slightly
```

**Why sigmoid(prs_raw) ≈ 1.0 and this is by design:**
`prs_raw ≈ 11.88` (sum over 182 SNPs). `sigmoid(11.88) ≈ 1.0 − 6.9e-6`. This is not a bug — it
encodes that the Indian population has a systematically elevated genetic CAD baseline.
Z-normalising would remove this population signal. NB7 explicitly chose to preserve it.

**Feature name extraction from pipeline (used in NB7, also needed in NB9):**
```python
def get_pipeline_features(pipeline):
    inner_pipe = pipeline.calibrated_classifiers_[0].estimator
    scaler = inner_pipe.named_steps['scaler']
    if hasattr(scaler, 'feature_names_in_'):
        return scaler.feature_names_in_.tolist()
    raise ValueError('Scaler has no feature_names_in_. Refit with DataFrame input.')
```

Risk bands: Low (<0.25), Moderate (0.25–0.50), High (0.50–0.75), Very High (≥0.75)
w2 sensitivity range: 0.05 to 0.40 (step 0.05)

### NB8 Actual Outputs (Calibration + Explainability — NO Cross-Cohort Fusion)

> ⚠️ **CRITICAL DEVIATION FROM BLUEPRINT:** NB8 does NOT produce `fusion_meta_learner.pkl`
> or `fusion_calibrated_model.pkl`. The actual implementation chose **independent per-cohort
> calibration** because the two datasets have zero patient overlap and incompatible feature spaces.
> Cross-cohort stacking was explicitly ruled out in the NB8 code.

```
Outputs/Integrated/
└── nb8_evaluation_summary.csv       # AUC/Brier: Base vs Integrated vs Calibrated per cohort

Outputs/Explainability/
├── shap_values_lifestyle.pkl         # SHAP bundle dict: keys below
├── shap_values_clinical.pkl          # SHAP bundle dict: keys below
└── domain_attributions.csv          # Lifestyle%/Clinical%/Genetic% per patient

Outputs/Figures/
├── shap_summary_lifestyle.png        # Beeswarm dot plot (lifestyle cohort)
├── shap_bar_clinical.png             # Bar plot of mean |SHAP| (clinical)
├── shap_waterfall_clinical.png       # 3-patient waterfall (low/medium/high risk)
└── domain_attribution.png            # Stacked bar: lifestyle vs clinical vs genetic %
```

**SHAP bundle structure** (same for lifestyle and clinical):
```python
shap_bundle = {
    'shap_values'   : np.ndarray,   # shape (n_patients, n_features)
    'feature_names' : list[str],
    'X_scaled'      : pd.DataFrame, # features after StandardScaler transform
    'X_raw'         : pd.DataFrame, # features before scaling
    'expected_value': float,        # SHAP base value
}
```

**NB8 calibration approach (per-cohort, not cross-cohort):**
- Step 1: OOF meta-calibration — `LogisticRegression` on `p_integrated` alone (1-D input), using `cross_val_predict` with `StratifiedKFold(5)` → produces `p_meta_oof`
- Step 2: Platt scaling — `CalibratedClassifierCV(LogisticRegression, method='sigmoid', cv=5)` fit on `p_integrated` → produces `p_calibrated`
- Neither calibrator is saved as a `.pkl` in NB8; they are computed at inference time

**NB9 DOES NOT RECEIVE a fusion model.** Instead NB9 must:
1. Load the two independent pipelines (`lifestyle_pipeline.pkl`, `clinical_pipeline.pkl`)
2. Apply the NB7 integration formula directly: `p = 0.85 × p_model + 0.15 × sigmoid(prs_raw)`
3. Run counterfactuals on each cohort separately

---

## 9. PRS Integration Details for NB9 (Actual NB7 Formula)

> ⚠️ The original context doc noted a Z-normalised sigmoid. **NB7 does NOT Z-normalise.**
> The actual formula uses `sigmoid(prs_raw)` directly, which saturates near 1.0 by design.

```python
import numpy as np
import pickle

with open(PRS_VECTOR, 'rb') as f:
    prs_vec = pickle.load(f)

prs_raw = prs_vec['prs_raw']

# Actual NB7 formula — DO NOT Z-score the PRS:
prs_sigmoid = 1.0 / (1.0 + np.exp(-prs_raw))   # will be ≈ 1.0; this is correct

W1 = 0.85
W2 = 0.15

def integrate_prs(p_model, prs_sig=prs_sigmoid, w1=W1, w2=W2):
    """
    Apply NB7 PRS integration formula.
    p_model : float or np.ndarray — model predicted probability before PRS
    Returns : PRS-integrated probability, clipped to [0, 1]
    """
    return float(np.clip(w1 * p_model + w2 * prs_sig, 0.0, 1.0))
```

**What this means in practice for NB9 counterfactuals:**
- `prs_sigmoid ≈ 1.0`, so `p_integrated ≈ 0.85 × p_model + 0.15`
- The PRS term is a constant offset for ALL patients — it does not change per-scenario
- When computing counterfactual risk delta:
  `delta = p_integrated(base) - p_integrated(modified)`
         `= 0.85 × p_model(base) + 0.15 - (0.85 × p_model(modified) + 0.15)`
         `= 0.85 × (p_model(base) - p_model(modified))`
- **The PRS term cancels out completely in the delta.** All risk reduction is driven by ML model alone.
- This is scientifically correct: PRS is a population-level constant; only the modifiable features change.

---

## 10. Complete Path Constants for NB9/NB10

```python
import os

BASE_DIR = "/content/drive/MyDrive/CAD_DT_Final/"

# ── Inputs from upstream notebooks ──────────────────────────────
LIFESTYLE_TRAIN  = BASE_DIR + "Outputs/Lifestyle/df_lifestyle_train.csv"
LIFESTYLE_TEST   = BASE_DIR + "Outputs/Lifestyle/df_lifestyle_test.csv"
CLINICAL_TRAIN   = BASE_DIR + "Outputs/Clinical/df_clinical_train.csv"
CLINICAL_TEST    = BASE_DIR + "Outputs/Clinical/df_clinical_test.csv"
CLINICAL_TEST_RAW= BASE_DIR + "Outputs/Clinical/df_clinical_test_raw.csv"     # NB10
CLINICAL_SCALER  = BASE_DIR + "Outputs/Clinical/clinical_scaler.pkl"          # NB10
CLINICAL_IMPUTER = BASE_DIR + "Outputs/Clinical/clinical_imputer.pkl"

LIFESTYLE_MODEL  = BASE_DIR + "Outputs/Models/lifestyle_pipeline.pkl"         # NB5
CLINICAL_MODEL   = BASE_DIR + "Outputs/Models/clinical_pipeline.pkl"          # NB6

PRS_VECTOR       = BASE_DIR + "Outputs/Genetics/prs_feature_vector.pkl"       # NB4
PRS_SCORE_CSV    = BASE_DIR + "Outputs/Genetics/prs_population_score.csv"     # NB4
PER_SNP_CSV      = BASE_DIR + "Outputs/Genetics/per_snp_contribution.csv"     # NB4

# ── NB7 outputs (NOTE: _with_prs NOT _with_pgs) ─────────────────
LS_SCORES_PATH   = BASE_DIR + "Outputs/Integrated/lifestyle_risk_scores_with_prs.csv"
CL_SCORES_PATH   = BASE_DIR + "Outputs/Integrated/clinical_risk_scores_with_prs.csv"
BANDS_PATH       = BASE_DIR + "Outputs/Integrated/risk_stratification_bands.csv"

# ── NB8 outputs (per-cohort calibration, NO fusion model) ───────
NB8_EVAL_CSV     = BASE_DIR + "Outputs/Integrated/nb8_evaluation_summary.csv"
SHAP_LS_PKL      = BASE_DIR + "Outputs/Explainability/shap_values_lifestyle.pkl"
SHAP_CL_PKL      = BASE_DIR + "Outputs/Explainability/shap_values_clinical.pkl"
DOMAIN_ATTR_CSV  = BASE_DIR + "Outputs/Explainability/domain_attributions.csv"

# NOTE: There is NO fusion_calibrated_model.pkl from NB8
# NB9 uses lifestyle_pipeline.pkl + clinical_pipeline.pkl + PRS formula directly

# ── NB9 outputs ─────────────────────────────────────────────────
DT_DIR           = BASE_DIR + "Outputs/DigitalTwin/"
INTERVENTION_OUT = DT_DIR + "intervention_results.csv"
SANITY_OUT       = DT_DIR + "sanity_check_results.csv"
TRAJ_FIG         = BASE_DIR + "Outputs/Figures/trajectory_visualization.png"
INTERV_FIG       = BASE_DIR + "Outputs/Figures/intervention_ranking_example.png"

# ── NB10 outputs ─────────────────────────────────────────────────
PULSE_DIR        = BASE_DIR + "Outputs/Pulse/"
PULSE_HEMO_OUT   = PULSE_DIR + "pulse_haemodynamic_deltas.csv"
PULSE_RISK_OUT   = PULSE_DIR + "pulse_updated_risk_scores.csv"
PULSE_COMP_FIG   = BASE_DIR + "Outputs/Figures/pulse_vs_ml_delta_comparison.png"

# ── Create output directories ────────────────────────────────────
for d in [DT_DIR, PULSE_DIR]:
    os.makedirs(d, exist_ok=True)

RANDOM_STATE = 42
```

---

## 11. Known Issues / Watch-outs for NB9/NB10

### 11.1 Feature Column Name Verification (CRITICAL)

Before writing ANY perturbation code, verify exact column names:
```python
import pandas as pd
df_lifestyle = pd.read_csv(LIFESTYLE_TEST)
df_clinical  = pd.read_csv(CLINICAL_TEST)
print("Lifestyle cols:", df_lifestyle.columns.tolist())
print("Clinical cols:", df_clinical.columns.tolist())
# Ensure 'smoking', 'alcohol', 'physical_activity', 'bmi' are present in lifestyle
# Ensure 'resting_bp', 'cholesterol', 'max_heart_rate' are in clinical (scaled versions)
```

### 11.2 Binary Lifestyle Features Limit DT Precision

The blueprint acknowledges this limitation explicitly. In the paper, state:
> "Due to data availability constraints, lifestyle factors in the training dataset are represented as binary indicators rather than continuous measures; this limits the granularity of intervention dose-response estimation."

Implication for NB9: Don't simulate pack-year or drink-per-week gradations — the model can only represent 0/1 states.

### 11.3 OHE Columns Cannot Be Directly Perturbed

`cholesterol_level` in the lifestyle dataset is OHE'd into `cholesterol_level_1`, `_2`, `_3`. To simulate "cholesterol reduction" in the LIFESTYLE model:
```python
# To simulate moving from 'well above normal' (category 3) to 'normal' (category 1):
X_modified['cholesterol_level_1'] = 1
X_modified['cholesterol_level_2'] = 0
X_modified['cholesterol_level_3'] = 0
# Always ensure exactly ONE of the OHE group is 1 and the others are 0
```

### 11.4 PRS Is a Fixed Population Scalar

The PRS does not change across patients because it represents population-level expected genetic risk, NOT individual genotyping. Do NOT try to perturb PRS across scenarios — it is always held fixed. The only valid PRS "scenario" is varying w2 (NB7 sensitivity analysis).

### 11.5 Diastolic BP Missing from Clinical Dataset

The 1190-patient clinical dataset only records SYSTOLIC blood pressure as `resting_bp`. There is no separate diastolic BP column. For NB10 Pulse initialization, diastolic must be estimated (≈0.67 × systolic) or a population default used. State this limitation in the paper.

### 11.6 `df_clinical_test_raw.csv` May Have NaN Values

These NaNs are from the sentinel-zero replacement in NB2 (before MICE imputation). NB10 must handle them:
```python
df_raw = pd.read_csv(CLINICAL_TEST_RAW)
# Fill NaN cholesterol with population median (~200 mg/dL) for Pulse initialization
df_raw['cholesterol'] = df_raw['cholesterol'].fillna(200)
df_raw['resting_bp']  = df_raw['resting_bp'].fillna(120)
```

### 11.7 NB5 Model Output File Name

The blueprint spec says `lifestyle_best_model.pkl` but NB5 actually saves as `lifestyle_pipeline.pkl`. Always use `lifestyle_pipeline.pkl`.

### 11.8 SHAP Computation Time Warning

If NB9 computes SHAP values for the digital twin explainability layer, sample 2,000–5,000 test patients maximum to avoid timeout:
```python
X_shap_sample = X_test.sample(n=min(2000, len(X_test)), random_state=42)
```

---

## 12. Paper Framing — Exact Language for NB9/NB10 Outputs

From blueprint — use EXACTLY these phrases in NB9/NB10 print outputs, docstrings, and any figures:

| Correct Phrase | NEVER Say |
|---|---|
| "Counterfactual intervention analysis" | "Causal" (without MR machinery) |
| "Simulated risk projection" | "Time-based trajectory model" |
| "Feature perturbation and re-inference" | "Simulate" (when meaning: perturb features) |
| "Associational risk attribution" | "Our PRS represents individual genetic risk" |
| "What-if estimation" | "Physiological simulation" (for ML-only DT) |
| "Population-level polygenic risk calibration" | "Individual PRS" |

### Justification paragraph for ML-only Digital Twin (use verbatim in NB9 markdown cell):

> "We implement a personalised digital twin as a patient-specific probabilistic risk model coupled with a counterfactual intervention engine. The twin maintains a dynamic representation of each patient's risk state as a function of their genetic, lifestyle, and clinical profile, and enables what-if simulation of lifestyle interventions by propagating feature-level perturbations through the learned risk model. This approach follows the ML-based digital twin paradigm established in Subramanian et al. (2020) and is appropriate for our goal of risk projection and intervention simulation rather than organ-level physiological modelling."

---

## 13. Execution Checklist Before Running NB9

- [ ] NB1 complete: `df_lifestyle_test.csv` exists
- [ ] NB2 complete: `df_clinical_test.csv` AND `df_clinical_test_raw.csv` both exist
- [ ] NB4 complete: `prs_feature_vector.pkl` exists with keys `prs_raw`, `prs_mean_mc`
- [ ] NB5 complete: `lifestyle_pipeline.pkl` exists and `predict_proba` returns shape (N, 2)
- [ ] NB6 complete: `clinical_pipeline.pkl` exists
- [ ] NB7 complete: `lifestyle_risk_scores_with_prs.csv` exists (NOT `_with_pgs`)
- [ ] NB7 complete: `clinical_risk_scores_with_prs.csv` exists
- [ ] NB8 complete: `domain_attributions.csv` exists (NB8 does NOT produce a fusion model pkl)
- [ ] Verify lifestyle feature columns by: `pd.read_csv(LIFESTYLE_TEST).columns.tolist()`
- [ ] Verify `smoking`, `alcohol`, `physical_activity`, `bmi` are in lifestyle test CSV
- [ ] Verify clinical feature columns via: `get_pipeline_features(clinical_pipeline)`
- [ ] Confirm `exercise_angina`, `st_slope_*`, `chest_pain_type_*` are ABSENT from clinical model input

## 13b. Execution Checklist Before Running NB10

- [ ] NB9 complete (NB10 runs concurrently with NB9 per blueprint, but logically after)
- [ ] NB2 complete: `df_clinical_test_raw.csv` exists
- [ ] NB2 complete: `clinical_scaler.pkl` exists
- [ ] NB6 complete: `clinical_pipeline.pkl` exists (NB10 uses clinical pipeline for risk re-scoring)
- [ ] NB4 complete: `prs_feature_vector.pkl` exists (for PRS integration in re-scored probabilities)
- [ ] PulsePhysio Python package installed and accessible
- [ ] Scope confirmation: NB10 adds 2–3 weeks; confirm with supervisor before proceeding

---

## 14. NB6 — Clinical Model Training (Actual Implementation Details)

### 14.1 Key Differences From NB5 (Critical for NB9/NB10)

| Aspect | NB5 (Lifestyle) | NB6 (Clinical) |
|---|---|---|
| Dataset size | ~54,906 train rows | ~952 train rows |
| Models trained | LR, RF, XGBoost, SGD (4 models) | LR, RF, XGBoost, Gradient Boosting (4 models) |
| Imbalance handling | SMOTE if ratio > 1.5 | `class_weight='balanced'` throughout |
| Regularisation | Default | Stronger: LR C=0.1, RF max_depth=6 min_samples_leaf=8, XGB reg_lambda=2.0 |
| GridSearchCV | NOT applied | Applied to top-2 CV models |
| Overfitting flag | train-test AUC gap > 0.08 | train-test AUC gap > 0.08 |
| Output pkl name | `lifestyle_pipeline.pkl` | `clinical_pipeline.pkl` |

### 14.2 High-Leakage Features DROPPED in NB6 (CRITICAL)

NB6 explicitly drops the following features from BOTH X_train and X_test before any modelling:

```python
DROP_COLS = [
    'exercise_angina',          # too directly diagnostic
    'st_slope_1', 'st_slope_2', 'st_slope_3',     # post-stress ECG — too leaky
    'chest_pain_type_1.0',      # NOTE: .0 float suffix in column names
    'chest_pain_type_2.0',
    'chest_pain_type_3.0',
    'chest_pain_type_4.0'
]
X_train = X_train.drop(columns=DROP_COLS, errors='ignore')
X_test  = X_test.drop(columns=DROP_COLS, errors='ignore')
```

> ⚠️ **OHE column float suffix issue:** The `chest_pain_type` OHE columns in `df_clinical_test.csv`
> appear with float suffixes (`.0`) — e.g. `chest_pain_type_1.0` NOT `chest_pain_type_1`.
> This is because `pd.get_dummies` preserves the dtype of the original column (int→float in some
> pandas versions). Always check actual column names with `df.columns.tolist()` before matching.

### 14.3 Actual Clinical Feature Columns After DROP_COLS

```python
# After dropping high-leakage features, approximately 10 features remain:
CLINICAL_FEATURE_COLS_NB6 = [
    'age',                  # continuous
    'sex',                  # binary 0=female, 1=male
    'resting_bp',           # continuous mmHg (MICE-imputed)
    'cholesterol',          # continuous mg/dL (MICE-imputed)
    'fasting_blood_sugar',  # binary
    'max_heart_rate',       # continuous bpm
    'oldpeak',              # continuous (can be negative — valid)
    'resting_ecg_0.0',      # OHE (value 0 = normal)  — NOTE float suffix
    'resting_ecg_1.0',      # OHE (value 1 = ST-T abnormality)
    'resting_ecg_2.0',      # OHE (value 2 = LV hypertrophy)
]
# ALWAYS confirm with: get_pipeline_features(clinical_pipeline)
# The scaler.feature_names_in_ is the authoritative source
```

### 14.4 Clinical Model Hyperparameters (NB6 Definitions)

```python
pos_weight = float(train_counts[0] / train_counts[1])  # for XGBoost scale_pos_weight

BASE_MODELS_NB6 = {
    'Logistic Regression': Pipeline([('scaler', StandardScaler()),
        ('clf', LogisticRegression(C=0.1, max_iter=2000, solver='lbfgs',
                                   class_weight='balanced', random_state=42))]),
    'Random Forest': Pipeline([('scaler', StandardScaler()),
        ('clf', RandomForestClassifier(n_estimators=300, max_depth=6,
                                       min_samples_leaf=8,
                                       class_weight='balanced', random_state=42))]),
    'XGBoost': Pipeline([('scaler', StandardScaler()),
        ('clf', XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=3,
                              subsample=0.8, colsample_bytree=0.8,
                              reg_lambda=2.0, scale_pos_weight=pos_weight,
                              tree_method='hist', eval_metric='logloss',
                              random_state=42))]),
    'Gradient Boosting': Pipeline([('scaler', StandardScaler()),
        ('clf', GradientBoostingClassifier(n_estimators=200, learning_rate=0.05,
                                           max_depth=3, min_samples_leaf=8,
                                           subsample=0.8, random_state=42))]),
}
# Each pipeline is then wrapped: CalibratedClassifierCV(pipeline, method='sigmoid', cv=5)
```

### 14.5 GridSearchCV Parameter Grids (NB6)

```python
PARAM_GRIDS_NB6 = {
    'Logistic Regression': {'clf__C': [0.01, 0.05, 0.1, 0.5, 1.0]},
    'Random Forest': {
        'clf__max_depth'       : [4, 6, 8],
        'clf__min_samples_leaf': [4, 8, 16],
    },
    'XGBoost': {
        'clf__max_depth'    : [3, 4],
        'clf__learning_rate': [0.03, 0.05, 0.1],
        'clf__reg_lambda'   : [1.0, 2.0, 5.0],
    },
    'Gradient Boosting': {
        'clf__max_depth'       : [2, 3],
        'clf__min_samples_leaf': [8, 16],
        'clf__learning_rate'   : [0.03, 0.05],
    },
}
# GridSearch scoring: 'roc_auc', StratifiedKFold(5), refit=True
# Applied only to top-2 CV models
```

### 14.6 NB6 Output Files

```
Outputs/Models/
├── clinical_pipeline.pkl              # CalibratedClassifierCV(Pipeline([SS, best_clf]))
├── clinical_model_results.csv         # CV+test results with overfitting flags
└── clinical_feature_importance.csv    # Gini/coefficient/permutation by best model
Outputs/Figures/
├── clinical_roc_curves.png
├── clinical_confusion_matrix.png
└── clinical_calibration.png
```

### 14.7 NB6 Loading Pattern for NB9

```python
import pickle

with open(CLINICAL_MODEL, 'rb') as f:
    clinical_pipeline = pickle.load(f)

# CORRECT — pass RAW (unscaled) features with DROP_COLS already removed:
# DO NOT drop columns at inference time if they were dropped during training.
# The scaler inside the pipeline was fit WITHOUT those columns.
# Use get_pipeline_features() to confirm exactly which columns are expected.

inner_pipe = clinical_pipeline.calibrated_classifiers_[0].estimator
expected_cols = inner_pipe.named_steps['scaler'].feature_names_in_.tolist()
# expected_cols ≈ ['age', 'sex', 'resting_bp', 'cholesterol', 'fasting_blood_sugar',
#                  'max_heart_rate', 'oldpeak', 'resting_ecg_0.0', 'resting_ecg_1.0',
#                  'resting_ecg_2.0']

X_clinical_raw = df_clinical_test[expected_cols]
p_clinical = clinical_pipeline.predict_proba(X_clinical_raw)[:, 1]
```

---

## 15. NB7 — Genetic Risk Integration (Actual Implementation Details)

### 15.1 What NB7 Actually Does (Confirmed from Code)

NB7 is straightforward: it generates base model predictions, applies the PRS offset formula,
bands patients into risk tiers, and produces figures. It does NOT retrain any model.

```python
# Exact NB7 workflow:
# 1. Load prs_population_score.csv → extract prs_raw, prs_mean_mc, ci_lower, ci_upper, n_snps
# 2. Load lifestyle_pipeline.pkl + clinical_pipeline.pkl
# 3. Extract feature lists from each pipeline's internal scaler (feature_names_in_)
# 4. Generate base probabilities: p_lifestyle_base, p_clinical_base
# 5. Compute prs_sigmoid = sigmoid(prs_raw)  [≈ 1.0, intentionally unsaturated-guard skipped]
# 6. p_integrated = 0.85 * p_model + 0.15 * prs_sigmoid
# 7. p_integrated = np.clip(p_integrated, 0.0, 1.0)
# 8. Assign risk bands using pd.cut()
# 9. Compare AUC/Brier base vs integrated
# 10. Produce violin, calibration curve, risk band bar chart figures
```

### 15.2 NB7 Output CSV Schema

`lifestyle_risk_scores_with_prs.csv` and `clinical_risk_scores_with_prs.csv`:
```python
# Columns in each output CSV:
NB7_SCORE_COLS = [
    'y_true',           # ground truth (0/1)
    'p_base',           # raw model probability (before PRS)
    'p_integrated',     # after PRS integration: 0.85*p_base + 0.15*prs_sigmoid
    'band_base',        # 'Low'/'Moderate'/'High'/'Very High' — based on p_base
    'band_integrated',  # 'Low'/'Moderate'/'High'/'Very High' — based on p_integrated
    'source',           # 'lifestyle' or 'clinical'
]
```

`risk_stratification_bands.csv`:
```python
# Summary table — band × model × type breakdown:
BANDS_COLS = ['Band', 'n', 'pct', 'cad_prev', 'mean_prob', 'model', 'type']
# 'type' is 'p_base' or 'p_integrated'
# 'cad_prev' is % of patients in that band who actually have CAD (sanity check)
```

### 15.3 Sensitivity Analysis Output (NB7)

Saved figure only — `nb7_sensitivity_analysis.png`. No CSV.
w2 values tested: 0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40
Expected result: AUC is flat across all w2 values (population-level PRS doesn't discriminate).

### 15.4 NB7 Important Findings for NB9 Counterfactuals

Since `prs_sigmoid ≈ 1.0` and is fixed across all patients:
- **Counterfactual risk delta cancels the PRS term**:
  `delta = p_integrated(X_base) - p_integrated(X_modified)`
         `= 0.85*(p_base - p_modified) + 0.15*(prs_sigmoid - prs_sigmoid)`
         `= 0.85*(p_base - p_modified)`
- NB9 can work with either `p_base` or `p_integrated` — the relative rankings and deltas are identical
- Report `p_integrated` as the displayed "current risk" since this is the genetically-calibrated figure
- Use `p_base` from model when computing the counterfactual delta, then scale by 0.85

---

## 16. NB8 — Calibration, Evaluation & Explainability (Actual Implementation Details)

### 16.1 What NB8 Definitively DOES and DOES NOT Do

| Does | Does NOT |
|---|---|
| Per-cohort Platt calibration of `p_integrated` | Cross-cohort stacking/fusion |
| OOF meta-calibration per cohort | Save a fusion model pkl |
| SHAP for lifestyle (XGB, 2000 rows sampled) | SHAP for clinical on subsample (uses full ~238 rows) |
| Domain attribution (3 domains) | Any retraining |
| Save SHAP bundles as pkl | Save Platt calibrators as pkl |

### 16.2 NB8 Calibration Approach in Detail

```python
# Step 1: OOF meta-calibration (1-D input: p_integrated)
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict

meta_lr   = LogisticRegression(C=1.0, max_iter=500, solver='lbfgs')
oof_proba = cross_val_predict(meta_lr, p_integrated.reshape(-1, 1), y_true,
                              cv=StratifiedKFold(5, shuffle=True, random_state=42),
                              method='predict_proba')[:, 1]
# → produces ls_scores['p_meta_oof'] and cl_scores['p_meta_oof']

# Step 2: Platt scaling (sigmoid, cv=5, also 1-D input)
from sklearn.calibration import CalibratedClassifierCV
calibrated = CalibratedClassifierCV(
    LogisticRegression(C=1.0, max_iter=500, solver='lbfgs'),
    method='sigmoid', cv=5
)
calibrated.fit(p_integrated.reshape(-1, 1), y_true)
p_calibrated = calibrated.predict_proba(p_integrated.reshape(-1, 1))[:, 1]
# → produces ls_scores['p_calibrated'] and cl_scores['p_calibrated']
# → calibrated objects (ls_calibrator, cl_calibrator) are NOT saved to disk
```

### 16.3 SHAP Extraction Pattern (NB8) — For NB9 Reuse

```python
import pickle, shap
import numpy as np
import pandas as pd

# Load pipeline and extract inner XGB
with open(LIFESTYLE_MODEL, 'rb') as f:
    ls_pipeline = pickle.load(f)

inner_pipe = ls_pipeline.calibrated_classifiers_[0].estimator
scaler_ls  = inner_pipe.named_steps['scaler']
clf_ls     = inner_pipe.named_steps['clf']       # XGBClassifier or best model

# Scale X_raw before SHAP (SHAP uses the trained model's feature space)
X_shap_scaled = pd.DataFrame(scaler_ls.transform(X_raw), columns=LS_FEATURES)

# Compute SHAP
explainer    = shap.TreeExplainer(clf_ls)
shap_values  = explainer.shap_values(X_shap_scaled)
if isinstance(shap_values, list):
    shap_values = shap_values[1]   # class-1 (CAD positive)

expected_val = explainer.expected_value
if isinstance(expected_val, (list, np.ndarray)):
    expected_val = float(expected_val[1])
```

### 16.4 Domain Attribution Schema (NB8)

```python
# domain_attributions.csv columns:
DOMAIN_ATTR_COLS = ['patient_idx', 'source', 'lifestyle', 'clinical', 'genetic']
# 'source': 'lifestyle' or 'clinical'
# lifestyle/clinical/genetic: percentage of total |SHAP| per patient (sums to ~100%)

# Genetic contribution is a FIXED CONSTANT (not per-patient SHAP):
PRS_CONTRIBUTION = 0.15 * 0.5023   # ≈ 0.0753 — w2 × approximate prs_sigmoid
# (NB8 uses a representative mean value, not exact sigmoid(prs_raw) which is ≈ 1.0)
# This is a modelling simplification — the "genetic" domain shows a small but nonzero share
```

### 16.5 NB8 Feature Domain Maps (Exact from Code)

```python
# Lifestyle cohort domain map:
LS_DOMAIN_MAP = {
    'lifestyle': [
        'smoke', 'alco', 'active', 'bmi',
        'smoking', 'alcohol', 'physical_activity',   # alternate names accepted
    ],
    'clinical': [
        'age', 'gender', 'height', 'weight',
        'systolic_bp', 'diastolic_bp',
        'cholesterol_level_1', 'cholesterol_level_2', 'cholesterol_level_3',
        'glucose_level_1', 'glucose_level_2', 'glucose_level_3',
        'ap_hi', 'ap_lo', 'cholesterol', 'gluc',     # alternate names accepted
    ],
}
# Note: Any feature not in either domain list is assigned to 'clinical' (catch-all)

# Clinical cohort domain map:
CL_DOMAIN_MAP = {
    'clinical': [
        'age', 'resting_bp', 'cholesterol', 'max_heart_rate', 'oldpeak',
        'fasting_blood_sugar',
        'resting_ecg_0.0', 'resting_ecg_1.0', 'resting_ecg_2.0',
        'sex', 'trestbps', 'chol', 'thalach', 'ca', 'thal',  # alternate names
    ],
    'lifestyle': [],  # empty — no lifestyle features in clinical cohort
}
```

### 16.6 NB8 Evaluation Table Schema

`Outputs/Integrated/nb8_evaluation_summary.csv`:
```python
NB8_EVAL_COLS = ['Cohort', 'Model', 'Test_AUC', 'Test_Brier']
# Model values: 'Lifestyle — Base', 'Lifestyle — Integrated', 'Lifestyle — Calibrated',
#               'Clinical — Base',  'Clinical — Integrated',  'Clinical — Calibrated'
```

### 16.7 NB8 Figures Produced

```
Outputs/Figures/
├── shap_summary_lifestyle.png     # Beeswarm dot plot (lifestyle, 2000 rows sampled)
├── shap_bar_clinical.png          # Bar chart mean |SHAP| (clinical, full test set)
├── shap_waterfall_clinical.png    # 3-patient waterfall (low/medium/high risk by p_clinical)
└── domain_attribution.png         # Stacked bar: lifestyle% vs clinical% vs genetic% per cohort
```

### 16.8 What NB9 Inherits from NB8 (Practical Summary)

NB9 does NOT need to reload any NB8 outputs for the core counterfactual engine. What NB9 CAN use from NB8:

1. **`shap_values_lifestyle.pkl`** — for per-patient feature attribution alongside intervention rankings
2. **`domain_attributions.csv`** — to annotate which domain dominates each patient's risk
3. **`nb8_evaluation_summary.csv`** — to report final AUC/Brier for the calibrated model in validation

NB9 core inference pattern (combining all upstream notebooks):
```python
import pickle, numpy as np, pandas as pd

# Load models
with open(LIFESTYLE_MODEL, 'rb') as f: ls_pipe = pickle.load(f)
with open(CLINICAL_MODEL,  'rb') as f: cl_pipe = pickle.load(f)
with open(PRS_VECTOR,      'rb') as f: prs_vec = pickle.load(f)

prs_sigmoid = 1.0 / (1.0 + np.exp(-prs_vec['prs_raw']))  # ≈ 1.0
W1, W2 = 0.85, 0.15

# Get exact feature lists from fitted scalers
ls_features = ls_pipe.calibrated_classifiers_[0].estimator.named_steps['scaler'].feature_names_in_.tolist()
cl_features = cl_pipe.calibrated_classifiers_[0].estimator.named_steps['scaler'].feature_names_in_.tolist()

def predict_integrated(pipeline, X_raw, features, prs_sig=prs_sigmoid, w1=W1, w2=W2):
    """Full NB7-style integrated prediction for a patient or batch."""
    X = X_raw[features] if isinstance(X_raw, pd.DataFrame) else X_raw
    p_base = pipeline.predict_proba(X)[:, 1]
    p_int  = np.clip(w1 * p_base + w2 * prs_sig, 0.0, 1.0)
    return p_base, p_int

# For lifestyle counterfactuals:
p_base_ls, p_int_ls = predict_integrated(ls_pipe, X_ls_raw, ls_features)

# For clinical counterfactuals:
p_base_cl, p_int_cl = predict_integrated(cl_pipe, X_cl_raw, cl_features)
```

---

## 17. Updated Deviations Table (NB6–NB8 Additional Findings)

Supplement to Section 0 in the original document.

| Original Expectation | Actual NB6–NB8 Implementation | Impact on NB9 |
|---|---|---|
| NB8 produces `fusion_calibrated_model.pkl` | NB8 does NOT — per-cohort Platt calibration only; no pkl saved | NB9 loads individual pipelines, not a fusion model |
| NB7 outputs `_with_pgs.csv` | NB7 outputs `_with_prs.csv` | Load correct file name |
| PRS integration uses `sigmoid(prs_z)` | Uses `sigmoid(prs_raw)` directly ≈ 1.0 | Counterfactual delta is 0.85× model delta; PRS term cancels |
| All 19 clinical features fed to clinical model | 7–10 features after dropping `exercise_angina`, `st_slope_*`, `chest_pain_type_*` | NB9 must NOT include dropped features in perturbations |
| `chest_pain_type` OHE → `chest_pain_type_1` | Actual column names: `chest_pain_type_1.0` (float suffix) | Match exact names from `scaler.feature_names_in_` |
| NB6 trains 6 models (like NB5) | NB6 trains 4 models: LR, RF, XGBoost, GradientBoosting | SGD and KNN dropped; use 4-model zoo |
| SHAP uses calibrated probabilities | SHAP uses inner XGB (extracted from pipeline), NOT predict_proba | Ensure scaler is applied before `explainer.shap_values()` |
| NB7 Z-normalises PRS before sigmoid | NB7 does NOT normalise — passes `prs_raw` directly to `sigmoid()` | Expect `prs_sigmoid ≈ 1.0`; delta calculations unaffected |
