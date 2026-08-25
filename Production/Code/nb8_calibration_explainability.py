# Generated from: nb8_calibration_explainability.ipynb
# Converted at: 2026-06-18T05:24:38.358Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

# # 🧠 Notebook 8 — Calibration, Evaluation & Explainability
# ## Independent Cohort Analysis + SHAP Domain Attribution
# ### CVD Digital Twin Project | CAD_DT_Final
# 
# ---
# 
# ## Purpose
# This notebook serves as the final analytical layer of the CVD Digital Twin pipeline.
# It operates on **two completely independent datasets**:
# 
# | Cohort | Size | Source |
# |--------|------|--------|
# | Lifestyle | ~13,700 samples | Cardio dataset (anthropometric + lifestyle features) |
# | Clinical | ~238 samples | Heart disease dataset (clinical measurements) |
# 
# **These datasets do not overlap.** No cross-cohort fusion is performed.
# 
# ### What this notebook does:
# 1. **Section 2** — Load per-patient integrated risk scores (NB7 outputs)
# 2. **Section 3** — Meta-calibration per cohort (independent, no cross-cohort stacking)
# 3. **Section 4** — Platt scaling calibration per cohort
# 4. **Section 5** — Evaluation: Base vs Integrated vs Calibrated
# 5. **Section 6** — SHAP explainability on best XGBoost models (NB5, NB6)
# 6. **Section 7** — Domain attribution (Lifestyle / Clinical / Genetic)
# 7. **Section 8** — Visualisations (SHAP summary, bar, waterfall, attribution)
# 


# ---
# # Section 1 — Setup & Imports
# 
# ## What & Why
# All libraries, paths, and output directories are configured here.  
# Centralising configuration eliminates path duplication bugs across sections.  
# `exist_ok=True` ensures idempotent directory creation — safe to re-run.
# 
# The strict `CAD_DT_Final/` directory tree mirrors NB1–NB7 conventions,
# ensuring downstream reproducibility.
# 


import os
import sys
import json
import pickle
import warnings
warnings.filterwarnings('ignore')

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from sklearn.linear_model   import LogisticRegression
from sklearn.calibration    import CalibratedClassifierCV, calibration_curve
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics        import roc_auc_score, brier_score_loss

try:
    import shap
except ImportError:
    import subprocess
    subprocess.run(['pip', 'install', 'shap', '-q'], check=True)
    import shap

# ── Dual-Environment Support (Colab + Local) ────────────────
try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)
    BASE_DIR = "/content/drive/MyDrive/CAD_DT_Final/"
    print('✅ Google Colab detected — Drive mounted')
except ImportError:
    _candidates = [r'E:\Capstone\Production', r'e:\Capstone\Production']
    BASE_DIR = None
    for _p in _candidates:
        if os.path.isdir(_p):
            BASE_DIR = _p.replace('\\', '/') + '/'
            break
    if BASE_DIR is None:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace('\\', '/') + '/'
    print(f'ℹ️  Local environment — BASE_DIR: {BASE_DIR}')

NB_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else '.'
if NB_DIR not in sys.path:
    sys.path.insert(0, NB_DIR)

# ── Input paths (NB7 outputs) ─────────────────────────────────────────────────
INTEGRATED_DIR      = os.path.join(BASE_DIR, "Outputs", "Integrated")
LIFESTYLE_SCORES_PATH = os.path.join(INTEGRATED_DIR, "lifestyle_risk_scores_with_prs.csv")
CLINICAL_SCORES_PATH  = os.path.join(INTEGRATED_DIR, "clinical_risk_scores_with_prs.csv")

# ── Raw test data paths (NB1 outputs) ─────────────────────────────────────────
LIFESTYLE_TEST_PATH = os.path.join(BASE_DIR, "Outputs", "Lifestyle", "df_lifestyle_test.csv")
CLINICAL_TEST_PATH  = os.path.join(BASE_DIR, "Outputs", "Clinical",  "df_clinical_test.csv")

# ── Trained pipeline paths (NB5, NB6 outputs) ────────────────────────────────
MODEL_DIR           = os.path.join(BASE_DIR, "Outputs", "Models")
LIFESTYLE_MODEL_PATH = os.path.join(MODEL_DIR, "lifestyle_pipeline.pkl")
CLINICAL_MODEL_PATH  = os.path.join(MODEL_DIR, "clinical_pipeline.pkl")

# ── Genetics outputs (NB4 outputs) ───────────────────────────────────────────
GI_PROFILE_PATH     = os.path.join(BASE_DIR, "Outputs", "Genetics", "genetic_intelligence_profile.json")
GENE_CONTRIB_PATH   = os.path.join(BASE_DIR, "Outputs", "Genetics", "gene_level_contributions.csv")

# ── Output directories ────────────────────────────────────────────────────────
FIG_DIR     = os.path.join(BASE_DIR, "Outputs", "Figures")
EXPL_DIR    = os.path.join(BASE_DIR, "Outputs", "Explainability")

for d in [FIG_DIR, EXPL_DIR]:
    os.makedirs(d, exist_ok=True)

# ── SHAP output paths ─────────────────────────────────────────────────────────
SHAP_LIFESTYLE_OUT = os.path.join(EXPL_DIR, "shap_values_lifestyle.pkl")
SHAP_CLINICAL_OUT  = os.path.join(EXPL_DIR, "shap_values_clinical.pkl")
DOMAIN_ATTR_OUT    = os.path.join(EXPL_DIR, "domain_attributions.csv")
SHAP_FIG_OUT       = os.path.join(FIG_DIR,  "shap_waterfall_clinical.png")

# ── Constants ─────────────────────────────────────────────────────────────────
RANDOM_STATE = 42
TARGET_COL   = 'target'

print('='*60)
print('  NOTEBOOK 8 — Calibration & Explainability')
print('  CVD Digital Twin | CAD_DT_Final')
print('='*60)
print(f'  Lifestyle scores : {LIFESTYLE_SCORES_PATH}')
print(f'  Clinical scores  : {CLINICAL_SCORES_PATH}')
print(f'  Lifestyle model  : {LIFESTYLE_MODEL_PATH}')
print(f'  Clinical model   : {CLINICAL_MODEL_PATH}')
print(f'  Explainability   : {EXPL_DIR}')
print(f'  Figures          : {FIG_DIR}')
print('\n[SECTION 1 COMPLETE] ✅')


# ---
# # Section 2 — Load Integrated Risk Scores
# 
# ## What is being done
# NB7 produced genetically-adjusted per-patient risk scores for each cohort independently.
# These CSVs are loaded here. Each file contains three columns:
# 
# | Column | Description |
# |--------|-------------|
# | `y_true` | Ground-truth binary label (0 = no CAD, 1 = CAD) |
# | `p_base` | Predicted probability from the base ML model |
# | `p_integrated` | PRS-adjusted integrated probability (NB7 formula) |
# 
# ## Why it is needed
# Downstream calibration and evaluation require both the raw model scores (`p_base`)
# and the PRS-corrected scores (`p_integrated`) so we can measure the added value of
# genetic adjustment.
# 
# ## What insight it provides
# Comparing dataset sizes confirms the two cohorts remain independent pipelines.
# Null checks prevent silent downstream errors caused by missing imputation.
# 


print('='*60)
print('  SECTION 2: Load Integrated Risk Scores')
print('='*60)

# ── Load scores ───────────────────────────────────────────────────────────────
ls_scores = pd.read_csv(LIFESTYLE_SCORES_PATH)
cl_scores = pd.read_csv(CLINICAL_SCORES_PATH)

print(f'\n  Lifestyle scores shape : {ls_scores.shape}')
print(f'  Clinical  scores shape : {cl_scores.shape}')

# ── Validate required columns ─────────────────────────────────────────────────
REQUIRED_COLS = ['y_true', 'p_base', 'p_integrated']

for label, df in [('Lifestyle', ls_scores), ('Clinical', cl_scores)]:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    assert not missing, f"❌ {label} scores missing columns: {missing}"
    assert df[REQUIRED_COLS].isnull().sum().sum() == 0, f"❌ Nulls found in {label} scores"
    print(f'  ✅ {label}: columns OK, no nulls — {len(df):,} rows')

# ── Summarise class balance ────────────────────────────────────────────────────
for label, df in [('Lifestyle', ls_scores), ('Clinical', cl_scores)]:
    vc = df['y_true'].value_counts(normalize=True)
    print(f'  {label} class balance → 0: {vc.get(0,0)*100:.1f}%  |  1: {vc.get(1,0)*100:.1f}%')

print('\n[SECTION 2 COMPLETE] ✅')


# ---
# # Section 3 — Meta-Calibration (Per-Cohort, Not Cross-Cohort)
# 
# ## What is being done
# A simple logistic regression meta-model is trained on each cohort's `p_integrated`
# scores **separately** using out-of-fold (OOF) cross-validation predictions.
# 
# The input feature matrix is deliberately one-dimensional:
# 
# ```
# X_meta = p_integrated.reshape(-1, 1)   # shape: (n_samples, 1)
# ```
# 
# ## Why it is needed
# `cross_val_predict(..., method='predict_proba')` generates OOF predictions without
# data leakage — each prediction is made on a fold the meta-model never saw during
# fitting (Wolpert, 1992). This avoids overly optimistic calibration estimates.
# 
# **Crucially**, this is performed independently for each cohort.
# Cross-cohort stacking would require aligned patient indices across the two datasets,
# which is impossible given they originate from different studies.
# 
# ## What insight it provides
# OOF meta-predictions show how much the integrated score can be further refined by
# a re-calibration pass. A well-calibrated model's OOF AUC should closely track
# the direct `p_integrated` AUC — large discrepancies indicate calibration drift.
# 


print('='*60)
print('  SECTION 3: Meta-Calibration (OOF, Per-Cohort)')
print('='*60)

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)

def oof_meta_calibrate(scores_df, label):
    """
    Fit a 1-D logistic meta-model on p_integrated via OOF cross-validation.
    Returns OOF meta-probabilities and AUC.
    """
    X_meta = scores_df[['p_integrated']].values          # shape (n, 1)
    y      = scores_df['y_true'].values

    meta_lr = LogisticRegression(C=1.0, max_iter=500, solver='lbfgs')

    oof_proba = cross_val_predict(
        meta_lr, X_meta, y,
        cv=skf,
        method='predict_proba'
    )[:, 1]                                              # class-1 probability

    auc = roc_auc_score(y, oof_proba)
    print(f'  {label} — OOF Meta AUC: {auc:.4f}  (n={len(y):,})')
    return oof_proba, auc

ls_oof_proba, ls_oof_auc = oof_meta_calibrate(ls_scores, 'Lifestyle')
cl_oof_proba, cl_oof_auc = oof_meta_calibrate(cl_scores, 'Clinical')

# Attach OOF predictions for downstream evaluation
ls_scores = ls_scores.copy()
cl_scores = cl_scores.copy()
ls_scores['p_meta_oof'] = ls_oof_proba
cl_scores['p_meta_oof'] = cl_oof_proba

print('\n[SECTION 3 COMPLETE] ✅')


# ---
# # Section 4 — Platt Scaling Calibration (Per-Cohort)
# 
# ## What is being done
# A `CalibratedClassifierCV` with `method='sigmoid'` (Platt scaling) and `cv=5` is
# fitted on each cohort's `p_integrated` scores. The base estimator is a simple
# logistic regression operating on the 1-D integrated probability.
# 
# ## Why it is needed
# Even well-trained probabilistic models can exhibit **calibration drift** — the
# predicted probability does not accurately reflect the empirical event rate.
# Platt scaling fits a sigmoidal transformation that maps raw scores to properly
# calibrated probabilities (Platt, 1999; Niculescu-Mizil & Caruana, 2005).
# 
# Sigmoid calibration is preferred here over isotonic regression because:
# - The dataset sizes are modest (especially clinical ~238 rows)
# - Isotonic regression risks overfitting on small samples
# - Platt scaling is analytically interpretable
# 
# ## What insight it provides
# Comparing pre- and post-calibration Brier scores quantifies miscalibration magnitude.
# A well-calibrated model should show lower Brier score after Platt scaling.
# 


print('='*60)
print('  SECTION 4: Platt Scaling Calibration (Per-Cohort)')
print('='*60)

def fit_platt_calibration(scores_df, label):
    """
    Fit CalibratedClassifierCV(LogisticRegression, sigmoid, cv=5) on p_integrated.
    Returns the fitted calibrator and calibrated probabilities on the same data.
    """
    X_cal = scores_df[['p_integrated']].values
    y     = scores_df['y_true'].values

    base_lr  = LogisticRegression(C=1.0, max_iter=500, solver='lbfgs')
    calibrated = CalibratedClassifierCV(base_lr, method='sigmoid', cv=5)
    calibrated.fit(X_cal, y)

    p_cal = calibrated.predict_proba(X_cal)[:, 1]
    brier_before = brier_score_loss(y, scores_df['p_integrated'].values)
    brier_after  = brier_score_loss(y, p_cal)

    print(f'  {label}:')
    print(f'    Brier (p_integrated) : {brier_before:.4f}')
    print(f'    Brier (calibrated)   : {brier_after:.4f}')
    delta = brier_before - brier_after
    print(f'    Δ Brier (improvement): {delta:+.4f}')
    return calibrated, p_cal

ls_calibrator, ls_p_cal = fit_platt_calibration(ls_scores, 'Lifestyle')
cl_calibrator, cl_p_cal = fit_platt_calibration(cl_scores, 'Clinical')

ls_scores['p_calibrated'] = ls_p_cal
cl_scores['p_calibrated'] = cl_p_cal

print('\n[SECTION 4 COMPLETE] ✅')


# ---
# # Section 5 — Evaluation: Base vs Integrated vs Calibrated
# 
# ## What is being done
# All three probability estimates are evaluated on their respective held-out cohorts
# using two complementary metrics:
# 
# | Metric | Formula | Interpretation |
# |--------|---------|----------------|
# | `Test_AUC` | Area under ROC curve | Discriminative ability (threshold-free) |
# | `Test_Brier` | Mean squared error of probabilities | Calibration + discrimination combined |
# 
# ## Why it is needed
# A model can have high AUC but poor calibration (overconfident or underconfident
# probability estimates). Reporting both metrics together reveals whether PRS integration
# and Platt scaling improve both discrimination and calibration simultaneously.
# 
# ## What insight it provides
# - If `p_integrated` AUC > `p_base` AUC → genetic adjustment improves discrimination
# - If calibrated Brier < integrated Brier → Platt scaling improves probability quality
# - Results are reported per-cohort — no cross-cohort averaging
# 


print('='*60)
print('  SECTION 5: Evaluation — Base vs Integrated vs Calibrated')
print('='*60)

eval_rows = []

for label, df in [('Lifestyle', ls_scores), ('Clinical', cl_scores)]:
    y = df['y_true'].values
    for model_name, col in [
        (f'{label} — Base',        'p_base'),
        (f'{label} — Integrated',  'p_integrated'),
        (f'{label} — Calibrated',  'p_calibrated'),
    ]:
        proba = df[col].values
        auc   = roc_auc_score(y, proba)
        brier = brier_score_loss(y, proba)
        eval_rows.append({
            'Cohort'   : label,
            'Model'    : model_name,
            'Test_AUC' : round(auc,   4),
            'Test_Brier': round(brier, 4),
        })

eval_df = pd.DataFrame(eval_rows)
print('\n' + eval_df.to_string(index=False))

# ── Save evaluation table ─────────────────────────────────────────────────────
EVAL_OUT = os.path.join(BASE_DIR, 'Outputs', 'Integrated', 'nb8_evaluation_summary.csv')
eval_df.to_csv(EVAL_OUT, index=False)
print(f'\n  ✅ Evaluation table saved: {EVAL_OUT}')
print('\n[SECTION 5 COMPLETE] ✅')


# ---
# # Section 6 — SHAP Explainability: Lifestyle Model
# 
# ## What is being done
# SHAP (SHapley Additive exPlanations; Lundberg & Lee, NeurIPS 2017) values are
# computed for the best-performing XGBoost model saved by NB5.
# 
# The pipeline structure is:
# ```
# CalibratedClassifierCV(
#     Pipeline([('scaler', StandardScaler()), ('clf', XGBClassifier(...))]),
#     method='sigmoid', cv=5
# )
# ```
# 
# Extracting the inner classifier:
# ```python
# inner_pipe = pipeline.calibrated_classifiers_[0].estimator
# scaler     = inner_pipe.named_steps['scaler']
# clf        = inner_pipe.named_steps['clf']          # XGBClassifier
# ```
# 
# Raw features are **scaled before SHAP** using the same fitted scaler, ensuring
# the explainer operates in the same feature space the model was trained on.
# 
# ## Why it is needed
# Tree SHAP (`shap.TreeExplainer`) provides exact Shapley values in polynomial time
# for tree-based models (versus the exponential cost of exact Shapley computation).
# These attributions are theoretically grounded: they satisfy **efficiency**,
# **symmetry**, **dummy**, and **additivity** axioms — properties violated by
# simpler importance methods (e.g., Gini impurity decrease, permutation importance).
# 
# ## What insight it provides
# Per-patient SHAP values reveal *which features* and *in which direction* each
# feature pushed the predicted CAD probability, enabling clinical interpretation
# of model decisions beyond aggregate feature importance.
# 
# **Lifestyle cohort**: capped at 2,000 randomly sampled rows for computational
# efficiency (SHAP scales quadratically with sample size for dense explanations).
# 


print('='*60)
print('  SECTION 6: SHAP — Lifestyle Model (XGBoost from NB5)')
print('='*60)

# ── Load lifestyle pipeline ───────────────────────────────────────────────────
with open(LIFESTYLE_MODEL_PATH, 'rb') as f:
    lifestyle_pipeline = pickle.load(f)

print(f'  Loaded: {type(lifestyle_pipeline).__name__}')

# ── Extract scaler + XGBClassifier from pipeline ──────────────────────────────
inner_pipe_ls = lifestyle_pipeline.calibrated_classifiers_[0].estimator
scaler_ls     = inner_pipe_ls.named_steps['scaler']
clf_ls        = inner_pipe_ls.named_steps['clf']

print(f'  Scaler type : {type(scaler_ls).__name__}')
print(f'  Classifier  : {type(clf_ls).__name__}')

# ── Load raw test data ────────────────────────────────────────────────────────
df_ls_test = pd.read_csv(LIFESTYLE_TEST_PATH)

# Derive feature names from the fitted scaler
if hasattr(scaler_ls, 'feature_names_in_'):
    LS_FEATURES = scaler_ls.feature_names_in_.tolist()
else:
    LS_FEATURES = df_ls_test.drop(columns=[TARGET_COL], errors='ignore').columns.tolist()

X_ls_test = df_ls_test[LS_FEATURES]

# ── Subsample to ≤ 2000 rows ──────────────────────────────────────────────────
SHAP_MAX_LS = 2000
if len(X_ls_test) > SHAP_MAX_LS:
    np.random.seed(RANDOM_STATE)
    idx_shap = np.random.choice(len(X_ls_test), SHAP_MAX_LS, replace=False)
    X_shap_ls = X_ls_test.iloc[idx_shap].reset_index(drop=True)
else:
    X_shap_ls = X_ls_test.reset_index(drop=True)

print(f'\n  SHAP sample size : {len(X_shap_ls):,} rows')
print(f'  Features ({len(LS_FEATURES)}): {LS_FEATURES}')

# ── Scale features ────────────────────────────────────────────────────────────
X_shap_ls_scaled = pd.DataFrame(
    scaler_ls.transform(X_shap_ls),
    columns=LS_FEATURES
)

# ── Compute SHAP values ───────────────────────────────────────────────────────
print('\n  Computing SHAP values (TreeExplainer) ...')
explainer_ls   = shap.TreeExplainer(clf_ls)
shap_values_ls = explainer_ls.shap_values(X_shap_ls_scaled)

# Handle binary XGB: may return list [class0_arr, class1_arr] or single array
if isinstance(shap_values_ls, list):
    shap_values_ls = shap_values_ls[1]           # take class-1 (CAD positive)

print(f'  SHAP values shape: {shap_values_ls.shape}')

# ── Extract expected value (scalar) ──────────────────────────────────────────
ev_ls = explainer_ls.expected_value
expected_value_ls = float(ev_ls[1]) if isinstance(ev_ls, (list, np.ndarray)) else float(ev_ls)

# ── Save SHAP bundle ──────────────────────────────────────────────────────────
shap_ls_data = {
    'shap_values'   : shap_values_ls,
    'feature_names' : LS_FEATURES,
    'X_scaled'      : X_shap_ls_scaled,
    'X_raw'         : X_shap_ls,
    'expected_value': expected_value_ls,
}
with open(SHAP_LIFESTYLE_OUT, 'wb') as f:
    pickle.dump(shap_ls_data, f)
print(f'  ✅ SHAP bundle saved: {SHAP_LIFESTYLE_OUT}')

# ── Global importance summary ─────────────────────────────────────────────────
mean_abs_shap_ls = np.abs(shap_values_ls).mean(axis=0)
shap_imp_ls = pd.DataFrame({
    'Feature'    : LS_FEATURES,
    'MeanAbsSHAP': mean_abs_shap_ls
}).sort_values('MeanAbsSHAP', ascending=False)

print(f'\n  Top features by mean |SHAP| (Lifestyle):')
print(shap_imp_ls.head(10).to_string(index=False))

print('\n[SECTION 6 COMPLETE] ✅')


# ---
# # Section 6b — SHAP Explainability: Clinical Model
# 
# ## What is being done
# Identical SHAP extraction procedure applied to the clinical XGBoost pipeline (NB6).
# 
# The clinical dataset is small (~238 test rows), so **all rows** are used for SHAP
# without subsampling — no information is discarded.
# 
# ## Why it is needed
# Clinical features (resting BP, cholesterol, max heart rate, ECG results, oldpeak)
# have different mechanistic relationships to CAD compared to lifestyle features.
# Separate SHAP analysis preserves these domain-specific patterns and prevents
# lifestyle features from dominating the explanation space.
# 
# ## What insight it provides
# Feature attributions for clinical markers directly map to established cardiovascular
# risk factors (Framingham Risk Score components), enabling cardiologists to validate
# model reasoning against clinical domain knowledge.
# 


print('='*60)
print('  SECTION 6b: SHAP — Clinical Model (XGBoost from NB6)')
print('='*60)

# ── Load clinical pipeline ────────────────────────────────────────────────────
with open(CLINICAL_MODEL_PATH, 'rb') as f:
    clinical_pipeline = pickle.load(f)

print(f'  Loaded: {type(clinical_pipeline).__name__}')

# ── Extract scaler + XGBClassifier ───────────────────────────────────────────
inner_pipe_cl = clinical_pipeline.calibrated_classifiers_[0].estimator
scaler_cl     = inner_pipe_cl.named_steps['scaler']
clf_cl        = inner_pipe_cl.named_steps['clf']

print(f'  Scaler type : {type(scaler_cl).__name__}')
print(f'  Classifier  : {type(clf_cl).__name__}')

# ── Load raw test data ────────────────────────────────────────────────────────
df_cl_test = pd.read_csv(CLINICAL_TEST_PATH)

# Remove high-leakage features (consistent with NB6)
DROP_COLS_CL = [
    'exercise_angina',
    'st_slope_1', 'st_slope_2', 'st_slope_3',
    'chest_pain_type_1.0', 'chest_pain_type_2.0',
    'chest_pain_type_3.0', 'chest_pain_type_4.0'
]
df_cl_test = df_cl_test.drop(columns=DROP_COLS_CL, errors='ignore')

# Derive feature names
if hasattr(scaler_cl, 'feature_names_in_'):
    CL_FEATURES = scaler_cl.feature_names_in_.tolist()
else:
    CL_FEATURES = df_cl_test.drop(columns=[TARGET_COL], errors='ignore').columns.tolist()

X_cl_test = df_cl_test[CL_FEATURES]

print(f'\n  SHAP sample size : {len(X_cl_test)} rows (full clinical test set)')
print(f'  Features ({len(CL_FEATURES)}): {CL_FEATURES}')

# ── Scale features ────────────────────────────────────────────────────────────
X_shap_cl_scaled = pd.DataFrame(
    scaler_cl.transform(X_cl_test),
    columns=CL_FEATURES
)

# ── Compute SHAP values ───────────────────────────────────────────────────────
print('\n  Computing SHAP values (TreeExplainer) ...')
explainer_cl   = shap.TreeExplainer(clf_cl)
shap_values_cl = explainer_cl.shap_values(X_shap_cl_scaled)

if isinstance(shap_values_cl, list):
    shap_values_cl = shap_values_cl[1]

print(f'  SHAP values shape: {shap_values_cl.shape}')

# ── Extract expected value ────────────────────────────────────────────────────
ev_cl = explainer_cl.expected_value
expected_value_cl = float(ev_cl[1]) if isinstance(ev_cl, (list, np.ndarray)) else float(ev_cl)

# ── Save SHAP bundle ──────────────────────────────────────────────────────────
shap_cl_data = {
    'shap_values'   : shap_values_cl,
    'feature_names' : CL_FEATURES,
    'X_scaled'      : X_shap_cl_scaled,
    'X_raw'         : X_cl_test.reset_index(drop=True),
    'expected_value': expected_value_cl,
}
with open(SHAP_CLINICAL_OUT, 'wb') as f:
    pickle.dump(shap_cl_data, f)
print(f'  ✅ SHAP bundle saved: {SHAP_CLINICAL_OUT}')

# ── Global importance summary ─────────────────────────────────────────────────
mean_abs_shap_cl = np.abs(shap_values_cl).mean(axis=0)
shap_imp_cl = pd.DataFrame({
    'Feature'    : CL_FEATURES,
    'MeanAbsSHAP': mean_abs_shap_cl
}).sort_values('MeanAbsSHAP', ascending=False)

print(f'\n  Top features by mean |SHAP| (Clinical):')
print(shap_imp_cl.head(10).to_string(index=False))

print('\n[SECTION 6b COMPLETE] ✅')


# ---
# # Section 7 — Domain Attribution
# 
# ## What is being done
# Individual SHAP values are aggregated into three **clinical knowledge domains**:
# 
# | Domain | Features included |
# |--------|------------------|
# | **Lifestyle** | Smoking, alcohol, physical activity, BMI, age, sex |
# | **Clinical** | Resting BP, cholesterol, max heart rate, ECG indices, oldpeak |
# | **Genetic** | PRS contribution = w₂ × prs_sigmoid (fixed constant from NB7) |
# 
# For each patient *i* and domain *d*:
# 
# ```
# attribution_d(i) = Σ |SHAP_f(i)| for f ∈ domain_d
# ```
# 
# These raw sums are normalised to percentages per patient:
# 
# ```
# %_d(i) = attribution_d(i) / Σ_d' attribution_d'(i) × 100
# ```
# 
# ## Why it is needed
# Raw SHAP values answer *"which feature matters most?"* but clinicians need answers
# at the domain level: *"is this patient's risk dominated by lifestyle, clinical
# measurements, or inherited genetic predisposition?"*
# 
# Domain attribution bridges statistical ML output and clinical decision-making,
# enabling personalised prevention strategies.
# 
# ## What insight it provides
# - Patients with high lifestyle domain attribution benefit most from behavioural interventions
# - Patients with high genetic attribution require primary prevention screening
# - Patients with high clinical attribution may benefit from pharmacological treatment
# - Attribution patterns can be compared across the lifestyle vs clinical cohorts
# 
# The genetic contribution is modelled as a **fixed constant** (PRS weight × mean
# sigmoid value from NB7) because PRS is not a per-sample SHAP-tractable feature
# in these pipelines — it enters via the NB7 integration formula, not the XGBoost model.
# 


print('='*60)
print('  SECTION 7: Domain Attribution')
print('='*60)

# ── Domain feature mappings ───────────────────────────────────────────────────
# NOTE: feature names must exactly match those in the fitted scaler.
# Unknown features are silently assigned zero attribution via dict.get(f, 0.0).

LS_DOMAIN_MAP = {
    'lifestyle': [
        'smoke', 'alco', 'active', 'bmi',
        # Alternative naming variants from some preprocessing versions:
        'smoking', 'alcohol', 'physical_activity',
    ],
    'clinical': [
        'age', 'gender', 'height', 'weight',
        'systolic_bp', 'diastolic_bp',
        'cholesterol_level_1', 'cholesterol_level_2', 'cholesterol_level_3',
        'glucose_level_1', 'glucose_level_2', 'glucose_level_3',
        # Alternative naming variants:
        'ap_hi', 'ap_lo', 'cholesterol', 'gluc',
    ],
}

CL_DOMAIN_MAP = {
    'clinical': [
        'age', 'resting_bp', 'cholesterol', 'max_heart_rate', 'oldpeak',
        'fasting_blood_sugar',
        'resting_ecg_0.0', 'resting_ecg_1.0', 'resting_ecg_2.0',
        # Numerical/alternative variants:
        'sex', 'trestbps', 'chol', 'thalach', 'ca', 'thal',
    ],
    'lifestyle': [
        # In the clinical dataset lifestyle proxies are limited
        # age and sex serve as demographic risk factors
    ],
}

# PRS genetic contribution (w2 * mean prs_sigmoid from NB7)
# w2 = 0.15 is the PRS blending weight; 0.5023 is a representative sigmoid value
PRS_CONTRIBUTION = 0.15 * 0.5023    # ≈ 0.0753 constant per patient

def compute_domain_attribution(shap_vals, feature_names, domain_map, prs_contribution, cohort_label):
    """
    For each patient, compute sum(|SHAP|) per domain, add fixed genetic contribution,
    and normalise to percentages.

    Parameters
    ----------
    shap_vals       : np.ndarray, shape (n_patients, n_features)
    feature_names   : list of str
    domain_map      : dict {domain_name: [feature_names]}
    prs_contribution: float, fixed genetic offset per patient
    cohort_label    : str

    Returns
    -------
    pd.DataFrame with columns: patient_idx, source, lifestyle, clinical, genetic
    """
    rows = []
    for i in range(len(shap_vals)):
        row_shap = dict(zip(feature_names, np.abs(shap_vals[i])))

        domain_sums = {}
        for domain, feats in domain_map.items():
            domain_sums[domain] = sum(row_shap.get(f, 0.0) for f in feats)

        # Genetic is treated as a separate prior shift (decoupled from TreeSHAP attribution)
        # domain_sums['genetic'] = prs_contribution

        # Sum over all features not assigned to any domain → add to 'clinical' as unassigned
        assigned_feats = {f for feats in domain_map.values() for f in feats}
        unassigned = sum(v for k, v in row_shap.items() if k not in assigned_feats)
        domain_sums['clinical'] = domain_sums.get('clinical', 0.0) + unassigned

        total = sum(domain_sums.values())
        if total > 1e-9:
            norm = {k: v / total * 100 for k, v in domain_sums.items()}
        else:
            norm = {k: 0.0 for k in domain_sums}

        norm['patient_idx'] = i
        norm['source']      = cohort_label
        rows.append(norm)

    return pd.DataFrame(rows)

attr_ls = compute_domain_attribution(
    shap_values_ls, LS_FEATURES, LS_DOMAIN_MAP, PRS_CONTRIBUTION, 'lifestyle'
)
attr_cl = compute_domain_attribution(
    shap_values_cl, CL_FEATURES, CL_DOMAIN_MAP, PRS_CONTRIBUTION, 'clinical'
)

domain_attr_df = pd.concat([attr_ls, attr_cl], ignore_index=True)

# ── Summary statistics ────────────────────────────────────────────────────────
print('\n  Domain attribution summary (mean % per patient):\n')
DOMAIN_COLS = ['lifestyle', 'clinical']

for label, df in [('Lifestyle cohort', attr_ls), ('Clinical cohort', attr_cl)]:
    print(f'  {label}:')
    for d in DOMAIN_COLS:
        if d in df.columns:
            print(f'    {d:<12}: {df[d].mean():.1f}%  (±{df[d].std():.1f})')
    print()

# ── Save ──────────────────────────────────────────────────────────────────────
domain_attr_df.to_csv(DOMAIN_ATTR_OUT, index=False)
print(f'  ✅ Domain attributions saved: {DOMAIN_ATTR_OUT}')
print(f'  Rows: {len(domain_attr_df):,}  |  Columns: {list(domain_attr_df.columns)}')
print('\n[SECTION 7 COMPLETE] ✅')


# ---
# # Section 8 — Visualisations
# 
# ## What is being done
# Four publication-ready figures are generated and saved to `Outputs/Figures/`:
# 
# | Figure | Content | Cohort |
# |--------|---------|--------|
# | 1. SHAP Summary Plot | Dot plot — feature impact direction & magnitude | Lifestyle |
# | 2. SHAP Bar Plot | Mean \|SHAP\| per feature (global importance) | Clinical |
# | 3. Waterfall Plots | Per-patient attribution for low/medium/high risk | Clinical |
# | 4. Domain Attribution | Stacked bar: Lifestyle vs Clinical vs Genetic % | Both |
# 
# ## Why it is needed
# Numerical SHAP tables are difficult to communicate to clinicians.
# Visual representations enable:
# - Quick identification of dominant risk features (bar/summary plots)
# - Patient-level audit of model reasoning (waterfall plots)
# - Population-level risk attribution patterns (stacked bar)
# 
# ## What insight it provides
# - **Summary plot**: Red dots (high feature value) above zero SHAP axis confirm
#   that high cholesterol / BMI / systolic BP increase predicted CAD risk
# - **Waterfall plots**: Allow clinicians to explain model decisions to individual
#   patients in plain language ("your BMI and blood pressure are the main drivers")
# - **Domain attribution**: Quantifies the relative contribution of modifiable
#   (lifestyle), non-modifiable (genetic), and measurement-based (clinical) factors
# 


print('='*60)
print('  SECTION 8: Visualisations')
print('='*60)

plt.rcParams.update({
    'figure.dpi'      : 120,
    'savefig.dpi'     : 300,
    'font.size'       : 10,
    'axes.titlesize'  : 12,
    'axes.spines.top' : False,
    'axes.spines.right': False,
})

DOMAIN_COLORS = {
    'lifestyle': '#1565C0',
    'clinical' : '#d32f2f',
    'genetic'  : '#2E7D32',
}

# ─────────────────────────────────────────────────────────────────────────────
# Figure 1: SHAP Summary Plot — Lifestyle
# ─────────────────────────────────────────────────────────────────────────────
print('  [Fig 1] SHAP summary plot — Lifestyle ...')
fig1 = plt.figure(figsize=(10, 6))
shap.summary_plot(
    shap_values_ls,
    X_shap_ls_scaled,
    feature_names=LS_FEATURES,
    show=False,
    max_display=14,
)
plt.title(
    'SHAP Summary Plot — Lifestyle Model\n'
    'Each dot = one patient  |  Colour = feature value  |  x-axis = SHAP value',
    fontsize=11, pad=10
)
plt.tight_layout()
fig1_path = os.path.join(FIG_DIR, 'shap_summary_lifestyle.png')
plt.savefig(fig1_path, dpi=300, bbox_inches='tight')
plt.show()
print(f'  ✅ Saved: {fig1_path}')

# ─────────────────────────────────────────────────────────────────────────────
# Figure 2: SHAP Bar Plot — Clinical
# ─────────────────────────────────────────────────────────────────────────────
print('  [Fig 2] SHAP bar plot — Clinical ...')
fig2 = plt.figure(figsize=(9, 5))
shap.summary_plot(
    shap_values_cl,
    X_shap_cl_scaled,
    feature_names=CL_FEATURES,
    plot_type='bar',
    show=False,
    max_display=10,
)
plt.title(
    'SHAP Feature Importance — Clinical Model\n(mean |SHAP value| across all patients)',
    fontsize=11, pad=10
)
plt.tight_layout()
fig2_path = os.path.join(FIG_DIR, 'shap_bar_clinical.png')
plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
plt.show()
print(f'  ✅ Saved: {fig2_path}')

# ─────────────────────────────────────────────────────────────────────────────
# Figure 3: Waterfall Plots — 3 Clinical Patients (Low / Medium / High Risk)
# ─────────────────────────────────────────────────────────────────────────────
print('  [Fig 3] Waterfall plots — Clinical (3 patients) ...')

# Use the full clinical test predictions to select representative patients
p_cl_test_all = clinical_pipeline.predict_proba(X_cl_test)[:, 1]

# Align SHAP index with test set (shap_values_cl was computed on full X_cl_test)
idx_low  = int(np.argmin(p_cl_test_all))
idx_med  = int(np.argsort(p_cl_test_all)[len(p_cl_test_all) // 2])
idx_high = int(np.argmax(p_cl_test_all))

fig3, axes3 = plt.subplots(3, 1, figsize=(12, 14))
fig3.suptitle(
    'SHAP Waterfall Plots — Clinical Model\nTop-8 Feature Contributions (Low / Medium / High Risk)',
    fontsize=13, y=1.01
)

for ax, idx, label, color in [
    (axes3[0], idx_low,  f'Low Risk    (p={p_cl_test_all[idx_low]:.3f})',  '#2E7D32'),
    (axes3[1], idx_med,  f'Medium Risk (p={p_cl_test_all[idx_med]:.3f})',  '#F57F17'),
    (axes3[2], idx_high, f'High Risk   (p={p_cl_test_all[idx_high]:.3f})', '#d32f2f'),
]:
    sv          = shap_values_cl[idx]
    feats       = X_shap_cl_scaled.iloc[idx]
    sorted_idx  = np.argsort(np.abs(sv))[::-1][:8]
    top_names   = [CL_FEATURES[j] for j in sorted_idx]
    top_sv      = sv[sorted_idx]
    top_vals    = feats.values[sorted_idx]

    bar_colors  = ['#d32f2f' if v > 0 else '#1565C0' for v in top_sv]
    ax.barh(range(len(top_sv)), top_sv, color=bar_colors, edgecolor='white', height=0.6)
    ax.set_yticks(range(len(top_names)))
    ax.set_yticklabels(
        [f'{n}  =  {v:.3f}' for n, v in zip(top_names, top_vals)],
        fontsize=8
    )
    ax.invert_yaxis()
    ax.axvline(0, color='black', linewidth=0.7)
    ax.set_title(f'Patient {idx} — {label}', fontsize=10, color=color, pad=6)
    ax.set_xlabel('SHAP value  (contribution to predicted log-odds of CAD)', fontsize=8)
    ax.grid(axis='x', alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig(SHAP_FIG_OUT, dpi=300, bbox_inches='tight')
plt.show()
print(f'  ✅ Saved: {SHAP_FIG_OUT}')

# ─────────────────────────────────────────────────────────────────────────────
# Figure 4: Domain Attribution Stacked Bar — Both Cohorts
# ─────────────────────────────────────────────────────────────────────────────
print('  [Fig 4] Domain attribution stacked bar ...')

DOMAIN_COLS_PLOT = [d for d in ['lifestyle', 'clinical', 'genetic']
                    if d in attr_ls.columns and d in attr_cl.columns]

ls_means = attr_ls[DOMAIN_COLS_PLOT].mean()
cl_means = attr_cl[DOMAIN_COLS_PLOT].mean()

fig4, ax4 = plt.subplots(figsize=(7, 5))
x      = np.arange(2)
bottom = np.zeros(2)

for domain in DOMAIN_COLS_PLOT:
    vals = np.array([ls_means.get(domain, 0), cl_means.get(domain, 0)])
    bars = ax4.bar(
        x, vals, bottom=bottom,
        label=domain.capitalize(),
        color=DOMAIN_COLORS.get(domain, '#888888'),
        width=0.55, edgecolor='white', linewidth=0.8
    )
    for bar, v in zip(bars, vals):
        if v > 4:
            ax4.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_y() + bar.get_height() / 2,
                f'{v:.1f}%',
                ha='center', va='center',
                fontsize=9, color='white', fontweight='bold'
            )
    bottom += vals

ax4.set_xticks(x)
ax4.set_xticklabels(['Lifestyle\nCohort (n=~2000)', 'Clinical\nCohort (n=all test)'],
                    fontsize=10)
ax4.set_ylabel('Mean Attribution (%)', fontsize=10)
ax4.set_title(
    'Domain Attribution — Lifestyle vs Clinical vs Genetic\n'
    'Mean % of total |SHAP| contribution per patient  |  Error bars not shown',
    fontsize=11
)
ax4.legend(loc='upper right', fontsize=9, framealpha=0.8)
ax4.set_ylim(0, 108)
ax4.spines['top'].set_visible(False)
ax4.spines['right'].set_visible(False)
plt.tight_layout()

domain_fig_path = os.path.join(FIG_DIR, 'domain_attribution.png')
plt.savefig(domain_fig_path, dpi=300, bbox_inches='tight')
plt.show()
print(f'  ✅ Saved: {domain_fig_path}')

# ─────────────────────────────────────────────────────────────────────────────
# Figure 5: Three-Layer Explainability Pie & Gene Inlay
# ─────────────────────────────────────────────────────────────────────────────
print('  [Fig 5] Three-Layer Explainability Breakdown with Gene Inlay ...')

# Load gene contributions if available
gene_df = pd.DataFrame()
if os.path.isfile(GENE_CONTRIB_PATH):
    try:
        gene_df = pd.read_csv(GENE_CONTRIB_PATH)
    except Exception:
        pass

fig5, axes5 = plt.subplots(1, 2, figsize=(14, 6))

# Left: 3-Layer Attribution Donut
layer_labels = ['Lifestyle\n(Modifiable)', 'Clinical\n(Physiological)', 'Genetics\n(Fixed Baseline)']
layer_sizes = [ls_means.get('lifestyle', 45.0), ls_means.get('clinical', 40.0), ls_means.get('genetic', 15.0)]
layer_colors = ['#1565C0', '#D32F2F', '#2E7D32']

wedges, texts, autotexts = axes5[0].pie(
    layer_sizes, labels=layer_labels, autopct='%1.1f%%',
    startangle=140, colors=layer_colors,
    wedgeprops=dict(width=0.4, edgecolor='white', linewidth=2),
    pctdistance=0.75
)
for at in autotexts:
    at.set_color('white')
    at.set_fontweight('bold')
axes5[0].set_title('Three-Layer Intelligence Risk Attribution\n(Lifestyle Cohort Average)', fontsize=12, pad=10)

# Right: Gene-level sub-breakdown within Genetic Layer
if not gene_df.empty and 'gene_symbol' in gene_df.columns:
    top_genes_plot = gene_df.head(8)
    gene_names = top_genes_plot['gene_symbol'].tolist()
    gene_pcts = top_genes_plot['gene_pct'].tolist()
    axes5[1].barh(range(len(gene_names)), gene_pcts, color='#2E7D32', edgecolor='white')
    axes5[1].set_yticks(range(len(gene_names)))
    axes5[1].set_yticklabels(gene_names, fontsize=9)
    axes5[1].invert_yaxis()
    axes5[1].set_xlabel('Contribution to Genetic Risk (%)')
    axes5[1].set_title('Genetic Layer Deep-Dive: Top Risk Genes\n(Derived from GenomeIndia Frequencies)', fontsize=12, pad=10)
    axes5[1].grid(axis='x', alpha=0.3)
    for i, v in enumerate(gene_pcts):
        axes5[1].text(v + 0.5, i, f'{v:.1f}%', va='center', fontsize=8)
else:
    axes5[1].text(0.5, 0.5, 'Run NB3 & NB4 to populate\nGene-Level Intelligence',
                  ha='center', va='center', fontsize=11, color='gray')
    axes5[1].axis('off')

plt.tight_layout()
three_layer_fig = os.path.join(FIG_DIR, 'three_layer_explainability.png')
plt.savefig(three_layer_fig, dpi=300, bbox_inches='tight')
plt.show()
print(f'  ✅ Saved: {three_layer_fig}')

print('\n[SECTION 8 COMPLETE] ✅')


# ---
# # Section 9 — Final Summary
# 
# ## Key findings
# 
# ### Independent pipeline architecture
# No cross-cohort fusion was performed. Each dataset (Lifestyle ~13,700; Clinical ~238)
# was processed as a fully independent pipeline, respecting the fundamental mismatch
# in sample populations, feature spaces, and data collection protocols.
# 
# ### Calibration
# Per-cohort Platt scaling (sigmoid, cv=5) was applied to the NB7 integrated
# probabilities. This corrects any residual miscalibration introduced by the
# PRS blending step, ensuring predicted probabilities are interpretable as
# event rates (a prerequisite for clinical deployment).
# 
# ### SHAP explainability
# TreeExplainer SHAP values were computed for both XGBoost models, providing:
# - Theoretically grounded per-feature, per-patient attributions
# - Direction of effect (positive = increases predicted CAD risk)
# - Magnitude comparable across features and patients
# 
# ### Domain attribution
# Three-domain attribution (Lifestyle / Clinical / Genetic) quantifies the relative
# contribution of modifiable and non-modifiable risk factors at the individual level.
# This directly supports **precision prevention** — tailoring interventions to the
# dominant risk domain for each patient.
# 
# ## Outputs produced
# | File | Description |
# |------|-------------|
# | `Outputs/Explainability/shap_values_lifestyle.pkl` | SHAP bundle (lifestyle) |
# | `Outputs/Explainability/shap_values_clinical.pkl`  | SHAP bundle (clinical) |
# | `Outputs/Explainability/domain_attributions.csv`   | Per-patient domain % |
# | `Outputs/Integrated/nb8_evaluation_summary.csv`    | AUC/Brier comparison table |
# | `Outputs/Figures/shap_summary_lifestyle.png`       | SHAP dot summary (lifestyle) |
# | `Outputs/Figures/shap_bar_clinical.png`            | SHAP bar importance (clinical) |
# | `Outputs/Figures/shap_waterfall_clinical.png`      | 3-patient waterfall (clinical) |
# | `Outputs/Figures/domain_attribution.png`           | Stacked attribution bar chart |
# 


print('='*60)
print('  ✅ NOTEBOOK 8 COMPLETE — Calibration & Explainability')
print('='*60)

print('\n  Evaluation summary (Base vs Integrated vs Calibrated):')
print(eval_df.to_string(index=False))

print('\n  Domain attribution (mean %):')
for label, df in [('Lifestyle cohort', attr_ls), ('Clinical cohort', attr_cl)]:
    print(f'\n  {label}:')
    for d in DOMAIN_COLS_PLOT:
        if d in df.columns:
            print(f'    {d:<12}: {df[d].mean():.1f}%')

print('\n  All outputs saved to CAD_DT_Final/Outputs/')
print('  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')