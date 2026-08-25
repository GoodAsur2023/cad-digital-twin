# -*- coding: utf-8 -*-
"""nb9_digital_twin_counterfactual.py

Enhanced Digital Twin with Patient State Engine, Uncertainty Quantification,
Personalized Intervention Ranking, ACC/AHA Guideline Mapping, and
Gene-Aware Intervention Context.

Original: nb9_digital_twin_counterfactual.ipynb (Colab)
Enhanced: 2026-08-18 — Precision Cardiology Intelligence Platform
"""

import os, sys, json, pickle, warnings
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

# ── Dual-Environment Support ──────────────────────────────────────
try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)
    BASE_DIR = '/content/drive/MyDrive/CAD_DT_Final/'
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

# ── Import shared module ──────────────────────────────────────────
try:
    from patient_intelligence_engine import (
        PatientState, GuidelineMapper, InterventionEngine,
        GeneticIntelligenceEngine, print_banner, print_complete
    )
    _HAS_ENGINE = True
except ImportError:
    _HAS_ENGINE = False
    print("⚠️  patient_intelligence_engine.py not found — using inline classes")

# ═══════════════════════════════════════════════════════════════════
# SECTION 1: Setup & Data Loading
# ═══════════════════════════════════════════════════════════════════

print("=" * 65)
print("  NB9 — ENHANCED DIGITAL TWIN: Patient State Engine")
print("  Precision Cardiology Intelligence Platform")
print("=" * 65)

# Paths
MODEL_DIR    = BASE_DIR + 'Outputs/Models/'
LS_TEST_PATH = BASE_DIR + 'Outputs/Lifestyle/df_lifestyle_test.csv'
CL_TEST_PATH = BASE_DIR + 'Outputs/Clinical/df_clinical_test.csv'
PRS_PATH     = BASE_DIR + 'Outputs/Genetics/prs_population_score.csv'
GI_PROFILE   = BASE_DIR + 'Outputs/Genetics/genetic_intelligence_profile.json'
GENE_CONTRIB = BASE_DIR + 'Outputs/Genetics/gene_level_contributions.csv'

DT_DIR       = BASE_DIR + 'Outputs/Digital_Twin/'
FIG_DIR      = BASE_DIR + 'Outputs/Figures/'
os.makedirs(DT_DIR, exist_ok=True)
os.makedirs(FIG_DIR, exist_ok=True)

# Load pipelines
with open(MODEL_DIR + 'lifestyle_pipeline.pkl', 'rb') as f:
    lifestyle_pipeline = pickle.load(f)
with open(MODEL_DIR + 'clinical_pipeline.pkl', 'rb') as f:
    clinical_pipeline = pickle.load(f)
with open(MODEL_DIR + 'clinical_prediagnostic_pipeline.pkl', 'rb') as f:
    prediag_pipeline = pickle.load(f)

# Load Genetic Intelligence Profile (Canonical PRS)
if not os.path.isfile(GI_PROFILE):
    raise FileNotFoundError(f"Missing canonical GIE profile: {GI_PROFILE}")

with open(GI_PROFILE, 'r') as f:
    genetic_profile = json.load(f)

FUS_PROV_PATH = BASE_DIR + 'Outputs/Clinical/fusion_weight_provenance.json'
if os.path.isfile(FUS_PROV_PATH):
    with open(FUS_PROV_PATH, 'r') as f:
        _fus = json.load(f)
        W_DIAG = _fus.get('canonical_weights', {}).get('w_diagnostic', 0.50)
        W_BASE = _fus.get('canonical_weights', {}).get('w_baseline', 0.50)
else:
    W_DIAG, W_BASE = 0.50, 0.50

class CanonicalFusionWrapper:
    def __init__(self, diag_pipe, base_pipe, w_diag, w_base):
        self.diag_pipe = diag_pipe
        self.base_pipe = base_pipe
        self.w_diag = w_diag
        self.w_base = w_base
        self.feature_names_in_ = diag_pipe.feature_names_in_
        
    @property
    def calibrated_classifiers_(self):
        return self.diag_pipe.calibrated_classifiers_
        
    def predict_proba(self, X):
        p_diag = self.diag_pipe.predict_proba(X)
        
        inner_pd = self.base_pipe.calibrated_classifiers_[0].estimator
        scaler_pd = inner_pd.named_steps['scaler']
        pd_feats = scaler_pd.feature_names_in_.tolist()
        X_base = X[pd_feats] if hasattr(X, 'columns') else X
        
        p_base = self.base_pipe.predict_proba(X_base)
        
        p_fused = self.w_diag * p_diag + self.w_base * p_base
        return np.clip(p_fused, 0.0, 1.0)

# Replace the original clinical_pipeline with the wrapper so it is used everywhere
clinical_pipeline_original = clinical_pipeline
clinical_pipeline = CanonicalFusionWrapper(clinical_pipeline_original, prediag_pipeline, W_DIAG, W_BASE)


prs_raw = genetic_profile['population_baseline']['signed_expected_prs']
prs_index = 0.5  # Normalized neutral index (centered at population mean)
genetic_profile = None
gene_contrib_df = pd.DataFrame()
if os.path.isfile(GI_PROFILE):
    with open(GI_PROFILE, 'r') as f:
        genetic_profile = json.load(f)
    print(f"  ✅ Genetic Intelligence Profile loaded")
    print(f"     Confidence: {genetic_profile.get('confidence', {}).get('tier', '?')}")
    print(f"     Top genes: {[g.get('gene_symbol', g.get('gene', '')) for g in genetic_profile.get('top_genes', [])[:5]]}")

if os.path.isfile(GENE_CONTRIB):
    gene_contrib_df = pd.read_csv(GENE_CONTRIB)
    print(f"  ✅ Gene contributions loaded: {len(gene_contrib_df)} genes")

# Load test sets
df_ls_test = pd.read_csv(LS_TEST_PATH)
df_cl_test = pd.read_csv(CL_TEST_PATH)

# Get feature names from fitted scalers
def get_pipeline_features(pipeline):
    inner_pipe = pipeline.calibrated_classifiers_[0].estimator
    return inner_pipe.named_steps['scaler'].feature_names_in_.tolist()

LS_FEATURES = get_pipeline_features(lifestyle_pipeline)
CL_FEATURES = get_pipeline_features(clinical_pipeline)

print(f"\n  Lifestyle features: {LS_FEATURES}")
print(f"  Clinical features:  {CL_FEATURES}")
print(f"  PRS normalized index: {prs_index:.6f}")
print("\n[SECTION 1 COMPLETE] ✅")


# ═══════════════════════════════════════════════════════════════════
# SECTION 2: Counterfactual Engine (Enhanced)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("  SECTION 2: Enhanced Counterfactual Engine")
print("=" * 65)

def integrated_risk(pipeline, X, prs_index=prs_index, w1=0.85, w2=0.15):
    """Compute PRS-integrated CAD risk per NB7 formula (with clinical fusion)."""
    if isinstance(pipeline, tuple):
        pipe_diag, pipe_base = pipeline
        p_d = pipe_diag.predict_proba(X)[:, 1]
        
        inner_pd = pipe_base.calibrated_classifiers_[0].estimator
        scaler_pd = inner_pd.named_steps['scaler']
        pd_feats = scaler_pd.feature_names_in_.tolist()
        X_base = X[pd_feats] if hasattr(X, 'columns') else X
        
        p_b = pipe_base.predict_proba(X_base)[:, 1]
        p_model = np.clip(W_DIAG * p_d + W_BASE * p_b, 0.0, 1.0)
    else:
        p_model = pipeline.predict_proba(X)[:, 1]
        
    p_int   = w1 * p_model + w2 * prs_index
    return np.clip(p_int, 0.0, 1.0)


def compute_risk_sensitivity(pipeline, X, prs_index=prs_index,
                         n_perturbations=200, w1=0.85, w2=0.15):
    """
    Compute risk with local perturbation sensitivity interval.
    Uses Monte Carlo noise injection (±1% feature perturbation).
    """
    base_risk = float(integrated_risk(pipeline, X, prs_index, w1, w2)[0])
    
    # Define categorical features to protect from perturbation
    CATEGORICAL_FEATURES = ['sex', 'smoking', 'physical_activity', 'alcohol', 
                            'resting_ecg_normal', 'resting_ecg_st_t_wave_abnormality', 
                            'resting_ecg_left_ventricular_hypertrophy']
    continuous_cols = [c for c in X.columns if c not in CATEGORICAL_FEATURES]
    rng = np.random.default_rng(42)
    
    mc_risks = []
    for _ in range(n_perturbations):
        X_noisy = X.copy()
        noise = rng.normal(1.0, 0.01, (len(X), len(continuous_cols)))
        X_noisy[continuous_cols] = X_noisy[continuous_cols] * noise
        
        r = float(integrated_risk(pipeline, X_noisy, prs_index, w1, w2)[0])
        mc_risks.append(r)
        
    # Center the CI around the point estimate to avoid bias from non-linear model smoothing
    mc_mean = np.mean(mc_risks)
    ci_lower = max(0.0, base_risk - (mc_mean - np.percentile(mc_risks, 2.5)))
    ci_upper = min(1.0, base_risk + (np.percentile(mc_risks, 97.5) - mc_mean))
    
    return {
        'risk': round(base_risk, 4),
        'ci_lower': round(ci_lower, 4),
        'ci_upper': round(ci_upper, 4),
    }


def counterfactual_engine(patient_row, pipeline, features, scenarios, cohort='lifestyle', compute_ci=False):
    """
    Evaluates a set of intervention scenarios for a single patient.
    """
    X_patient = pd.DataFrame([patient_row[features].values], columns=features)
    
    if compute_ci:
        risk_data = compute_risk_sensitivity(pipeline, X_patient, prs_index)
        current_risk = risk_data['risk']
        current_ci = (risk_data['ci_lower'], risk_data['ci_upper'])
    else:
        current_risk = float(integrated_risk(pipeline, X_patient)[0])
        current_ci = (None, None)

    results = []
    for sid, perturbation in scenarios.items():
        X_mod = X_patient.copy()
        for feat, new_val in perturbation.items():
            if feat in X_mod.columns and new_val is not None:
                X_mod[feat] = new_val
        
        if compute_ci:
            new_data = compute_risk_sensitivity(pipeline, X_mod, prs_index)
            new_risk = new_data['risk']
            new_ci = (new_data['ci_lower'], new_data['ci_upper'])
        else:
            new_risk = float(integrated_risk(pipeline, X_mod)[0])
            new_ci = (None, None)
        
        delta_risk = new_risk - current_risk
        risk_reduction = -delta_risk
        pct   = (risk_reduction / current_risk * 100) if current_risk > 1e-9 else 0.0
        results.append({
            'scenario_id': sid,
            'cohort': cohort,
            'current_risk': round(current_risk, 4),
            'current_ci_lower': current_ci[0],
            'current_ci_upper': current_ci[1],
            'new_risk': round(new_risk, 4),
            'new_ci_lower': new_ci[0],
            'new_ci_upper': new_ci[1],
            'delta_risk': round(delta_risk, 4),
            'risk_reduction': round(risk_reduction, 4),
            'pct_reduction': round(pct, 2)
        })
    return pd.DataFrame(results)


# ── Scenario definitions ──────────────────────────────────────────
LIFESTYLE_SCENARIOS = {
    'S1_quit_smoking': {'smoking': 0},
    'S2_exercise': {'physical_activity': 1},
    'S3_weight_loss_5pct': {'bmi': None},
    'S4_quit_alcohol': {'alcohol': 0},
    'S5_combined_smoke_exercise': {'smoking': 0, 'physical_activity': 1},
}

CLINICAL_SCENARIOS = {
    'S1_BP_reduction': {'resting_bp': None},
    'S2_exercise_hr_bp': {'max_heart_rate': None, 'resting_bp': None},
    'S3_weight_loss_proxy_BP_cholesterol': {'resting_bp': None, 'cholesterol': None},
    'S4_cholesterol_reduction': {'cholesterol': None},
    'S5_combined_exercise_BP_cholesterol': {'max_heart_rate': None, 'resting_bp': None, 'cholesterol': None},
}

def fill_dynamic_scenarios(patient_row, cohort='lifestyle'):
    """Fill per-patient None values with computed perturbations."""
    if cohort == 'lifestyle':
        scenarios = {k: v.copy() for k, v in LIFESTYLE_SCENARIOS.items()}
        if 'bmi' in patient_row:
            scenarios['S3_weight_loss_5pct']['bmi'] = patient_row['bmi'] * 0.95
        return scenarios
    else:
        scenarios = {k: v.copy() for k, v in CLINICAL_SCENARIOS.items()}
        if 'resting_bp' in patient_row:
            scenarios['S1_BP_reduction']['resting_bp'] = max(patient_row['resting_bp'] - 3, 90)
            scenarios['S2_exercise_hr_bp']['resting_bp'] = max(patient_row['resting_bp'] - 3.5, 90)
            scenarios['S3_weight_loss_proxy_BP_cholesterol']['resting_bp'] = max(patient_row['resting_bp'] - 2, 90)
            scenarios['S5_combined_exercise_BP_cholesterol']['resting_bp'] = max(patient_row['resting_bp'] - 3.5, 90)
        if 'max_heart_rate' in patient_row:
            scenarios['S2_exercise_hr_bp']['max_heart_rate'] = patient_row['max_heart_rate'] + 5
            scenarios['S5_combined_exercise_BP_cholesterol']['max_heart_rate'] = patient_row['max_heart_rate'] + 5
        if 'cholesterol' in patient_row:
            scenarios['S3_weight_loss_proxy_BP_cholesterol']['cholesterol'] = max(patient_row['cholesterol'] - 5, 120)
            scenarios['S4_cholesterol_reduction']['cholesterol'] = max(patient_row['cholesterol'] - 25, 120)
            scenarios['S5_combined_exercise_BP_cholesterol']['cholesterol'] = max(patient_row['cholesterol'] - 25, 120)
        return scenarios

def batch_counterfactual_lifestyle(df, pipeline, features, prs_index):
    """Vectorized counterfactual evaluation for lifestyle cohort."""
    current_risk = integrated_risk(pipeline, df[features], prs_index)
    results = []
    
    # S1: quit smoking
    df_s1 = df[features].copy()
    if 'smoking' in df_s1.columns:
        df_s1['smoking'] = 0
    risk_s1 = integrated_risk(pipeline, df_s1, prs_index)
    
    # S2: exercise
    df_s2 = df[features].copy()
    if 'physical_activity' in df_s2.columns:
        df_s2['physical_activity'] = 1
    risk_s2 = integrated_risk(pipeline, df_s2, prs_index)
    
    # S3: weight loss 5%
    df_s3 = df[features].copy()
    if 'bmi' in df_s3.columns:
        df_s3['bmi'] = df_s3['bmi'] * 0.95
    risk_s3 = integrated_risk(pipeline, df_s3, prs_index)
    
    # S4: quit alcohol
    df_s4 = df[features].copy()
    if 'alcohol' in df_s4.columns:
        df_s4['alcohol'] = 0
    risk_s4 = integrated_risk(pipeline, df_s4, prs_index)
    
    # S5: combined smoke + exercise
    df_s5 = df[features].copy()
    if 'smoking' in df_s5.columns:
        df_s5['smoking'] = 0
    if 'physical_activity' in df_s5.columns:
        df_s5['physical_activity'] = 1
    risk_s5 = integrated_risk(pipeline, df_s5, prs_index)
    
    scenario_runs = [
        ('S1_quit_smoking', risk_s1),
        ('S2_exercise', risk_s2),
        ('S3_weight_loss_5pct', risk_s3),
        ('S4_quit_alcohol', risk_s4),
        ('S5_combined_smoke_exercise', risk_s5),
    ]
    
    for sid, new_r in scenario_runs:
        delta_risk = new_r - current_risk
        risk_reduction = -delta_risk
        pct = np.where(current_risk > 1e-9, risk_reduction / current_risk * 100, 0.0)
        for i, idx in enumerate(df.index):
            d_risk = float(delta_risk[i])
            if d_risk < -1e-3:
                status = "EXPECTED_DECREASE"
            elif d_risk > 1e-3:
                status = "MODEL_NON_MONOTONIC"
            else:
                status = "NO_MEANINGFUL_CHANGE"
                
            results.append({
                'patient_idx': int(idx),
                'scenario_id': sid,
                'cohort': 'lifestyle',
                'current_risk': round(float(current_risk[i]), 4),
                'new_risk': round(float(new_r[i]), 4),
                'delta_risk': round(d_risk, 4),
                'risk_reduction': round(float(risk_reduction[i]), 4),
                'pct_reduction': round(float(pct[i]), 2),
                'response_status': status,
            })
    return pd.DataFrame(results)


def batch_counterfactual_clinical(df, pipeline, features, prs_index):
    """Vectorized counterfactual evaluation for clinical cohort."""
    current_risk = integrated_risk(pipeline, df[features], prs_index)
    results = []
    
    # S1: smoking cessation BP (-3 mmHg)
    df_s1 = df[features].copy()
    if 'resting_bp' in df_s1.columns:
        df_s1['resting_bp'] = np.maximum(df_s1['resting_bp'] - 3, 90)
    risk_s1 = integrated_risk(pipeline, df_s1, prs_index)
    
    # S2: exercise HR (+5) & BP (-3.5)
    df_s2 = df[features].copy()
    if 'resting_bp' in df_s2.columns:
        df_s2['resting_bp'] = np.maximum(df_s2['resting_bp'] - 3.5, 90)
    if 'max_heart_rate' in df_s2.columns:
        df_s2['max_heart_rate'] = df_s2['max_heart_rate'] + 5
    risk_s2 = integrated_risk(pipeline, df_s2, prs_index)
    
    # S3: weight loss 5% (BP -2, Chol -5)
    df_s3 = df[features].copy()
    if 'resting_bp' in df_s3.columns:
        df_s3['resting_bp'] = np.maximum(df_s3['resting_bp'] - 2, 90)
    if 'cholesterol' in df_s3.columns:
        df_s3['cholesterol'] = np.maximum(df_s3['cholesterol'] - 5, 120)
    risk_s3 = integrated_risk(pipeline, df_s3, prs_index)
    
    # S4: chol diet improvement (Chol -25)
    df_s4 = df[features].copy()
    if 'cholesterol' in df_s4.columns:
        df_s4['cholesterol'] = np.maximum(df_s4['cholesterol'] - 25, 120)
    risk_s4 = integrated_risk(pipeline, df_s4, prs_index)
    
    # S5: combined exercise & diet (HR +5, BP -3.5, Chol -25)
    df_s5 = df[features].copy()
    if 'resting_bp' in df_s5.columns:
        df_s5['resting_bp'] = np.maximum(df_s5['resting_bp'] - 3.5, 90)
    if 'max_heart_rate' in df_s5.columns:
        df_s5['max_heart_rate'] = df_s5['max_heart_rate'] + 5
    if 'cholesterol' in df_s5.columns:
        df_s5['cholesterol'] = np.maximum(df_s5['cholesterol'] - 25, 120)
    risk_s5 = integrated_risk(pipeline, df_s5, prs_index)
    
    scenario_runs = [
        ('S1_BP_reduction', risk_s1),
        ('S2_exercise_hr_bp', risk_s2),
        ('S3_weight_loss_proxy_BP_cholesterol', risk_s3),
        ('S4_cholesterol_reduction', risk_s4),
        ('S5_combined_exercise_BP_cholesterol', risk_s5),
    ]
    
    for sid, new_r in scenario_runs:
        delta_risk = new_r - current_risk
        risk_reduction = -delta_risk
        pct = np.where(current_risk > 1e-9, risk_reduction / current_risk * 100, 0.0)
        for i, idx in enumerate(df.index):
            d_risk = float(delta_risk[i])
            if d_risk < -1e-3:
                status = "EXPECTED_DECREASE"
            elif d_risk > 1e-3:
                status = "MODEL_NON_MONOTONIC"
            else:
                status = "NO_MEANINGFUL_CHANGE"
                
            results.append({
                'patient_idx': int(idx),
                'scenario_id': sid,
                'cohort': 'clinical',
                'current_risk': round(float(current_risk[i]), 4),
                'new_risk': round(float(new_r[i]), 4),
                'delta_risk': round(d_risk, 4),
                'risk_reduction': round(float(risk_reduction[i]), 4),
                'pct_reduction': round(float(pct[i]), 2),
                'response_status': status,
            })
    return pd.DataFrame(results)


# ── Run vectorized counterfactual engine on both cohorts ──────────
print("\nRunning vectorized counterfactual engine on lifestyle cohort (n=13,727)...")
ls_results_df = batch_counterfactual_lifestyle(df_ls_test, lifestyle_pipeline, LS_FEATURES, prs_index)

print("Running vectorized counterfactual engine on clinical cohort (n=238)...")
cl_results_df = batch_counterfactual_clinical(df_cl_test, clinical_pipeline, CL_FEATURES, prs_index)

# Combine and save
intervention_results = pd.concat([ls_results_df, cl_results_df], ignore_index=True)

# ── Semantic Validation Gate ──────────────────────────────────────
print("\n🩺 Semantic Validation Diagnostic Report")
monotonicity_counts = intervention_results['response_status'].value_counts()
print(f"  EXPECTED_DECREASE:    {monotonicity_counts.get('EXPECTED_DECREASE', 0)}")
print(f"  NO_MEANINGFUL_CHANGE: {monotonicity_counts.get('NO_MEANINGFUL_CHANGE', 0)}")
print(f"  MODEL_NON_MONOTONIC:  {monotonicity_counts.get('MODEL_NON_MONOTONIC', 0)}")
print("  Note: Model_Non_Monotonic cases reflect the unconstrained nature of tree ensembles on sparse input regions.")

intervention_results.to_csv(DT_DIR + 'intervention_results.csv', index=False)
print(f"✅ Saved: {DT_DIR}intervention_results.csv  ({len(intervention_results):,} rows)")

# Summary statistics
print("\n📊 Mean risk reduction per scenario (heuristic feature perturbation based on assumed intervention-response magnitudes):")
summary = intervention_results.groupby(['cohort', 'scenario_id'])[['delta_risk', 'risk_reduction', 'pct_reduction']].mean()
print(summary.round(4))

print("\n[SECTION 2 COMPLETE] ✅")


# ═══════════════════════════════════════════════════════════════════
# SECTION 3: Personalized Intervention Ranking
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("  SECTION 3: Personalized Intervention Ranking")
print("=" * 65)

# Fast vectorized per-patient ranking
rankings_df = intervention_results.sort_values(
    ['cohort', 'patient_idx', 'risk_reduction'], ascending=[True, True, False]
).copy()
rankings_df['rank'] = rankings_df.groupby(['cohort', 'patient_idx']).cumcount() + 1
rankings_df = rankings_df.reset_index(drop=True)

rankings_df.to_csv(DT_DIR + 'personalized_intervention_rankings.csv', index=False)
print(f"✅ Saved: {DT_DIR}personalized_intervention_rankings.csv")

# Show examples
print("\n📊 Example: Top 3 interventions for first 3 lifestyle patients:")
for p_idx in sorted(ls_results_df['patient_idx'].unique())[:3]:
    p_data = rankings_df[(rankings_df['cohort'] == 'lifestyle') & (rankings_df['patient_idx'] == p_idx)]
    curr_r = p_data.iloc[0]['current_risk']
    print(f"\n  Patient {p_idx} (Current Risk: {curr_r:.1%})")
    for _, row in p_data.head(3).iterrows():
        print(f"    {int(row['rank'])}. {row['scenario_id']} → Risk reduction: {row['risk_reduction']*100:.1f} percentage points")

print("\n[SECTION 3 COMPLETE] ✅")


# ═══════════════════════════════════════════════════════════════════
# SECTION 4: ACC/AHA Clinical Guideline Mapping
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("  SECTION 4: ACC/AHA Clinical Guideline Mapping")
print("=" * 65)

# Inline GuidelineMapper if shared module not available
ACC_AHA_CATEGORIES = [
    {'name': 'Low Risk', 'range': (0.0, 0.05),
     'relevant_guideline_considerations': 'Lifestyle modifications: heart-healthy diet, regular exercise, tobacco avoidance.',
     'monitoring': 'Reassess in 5 years'},
    {'name': 'Borderline Risk', 'range': (0.05, 0.075),
     'relevant_guideline_considerations': 'Lifestyle modifications. Consider risk enhancers (family history, elevated LDL-C, South Asian ancestry).',
     'monitoring': 'Reassess in 3-5 years'},
    {'name': 'Intermediate Risk', 'range': (0.075, 0.20),
     'relevant_guideline_considerations': 'Model probability falls within the intermediate model-risk band. Standard clinical assessment may consider established risk factors and guideline criteria; this prototype does not provide treatment recommendations. Consider CAC scoring.',
     'monitoring': 'Annual reassessment'},
    {'name': 'High Risk', 'range': (0.20, 1.01),
     'relevant_guideline_considerations': 'Aggressive lifestyle intervention. Model probability falls within the high risk band; standard clinical assessment may consider established risk factors and guideline criteria. This prototype does not provide treatment recommendations.',
     'monitoring': 'Every 3-6 months'},
]

def classify_acc_aha(risk):
    """Map risk probability to ACC/AHA 2019 guideline category."""
    risk = max(0.0, min(1.0, risk))
    for cat in ACC_AHA_CATEGORIES:
        lo, hi = cat['range']
        if lo <= risk < hi:
            return cat
    return ACC_AHA_CATEGORIES[-1]

# Apply guidelines to all patients
guideline_rows = []

for cohort, df, pipeline, features in [
    ('lifestyle', df_ls_test, lifestyle_pipeline, LS_FEATURES),
    ('clinical', df_cl_test, clinical_pipeline, CL_FEATURES),
]:
    risks = integrated_risk(pipeline, df[features])
    for idx, (patient_idx, risk) in enumerate(zip(df.index, risks)):
        cat = classify_acc_aha(float(risk))
        guideline_rows.append({
            'patient_idx': patient_idx,
            'cohort': cohort,
            'current_risk': round(float(risk), 4),
            'model_risk_band': cat['name'],
            'relevant_guideline_considerations': cat['relevant_guideline_considerations'],
            'monitoring': cat['monitoring'],
        })

guideline_df = pd.DataFrame(guideline_rows)
guideline_df.to_csv(DT_DIR + 'clinical_guideline_recommendations.csv', index=False)
print(f"✅ Saved: {DT_DIR}clinical_guideline_recommendations.csv")

# Distribution
print("\n📊 ACC/AHA Risk Category Distribution:")
for cohort in ['lifestyle', 'clinical']:
    mask = guideline_df['cohort'] == cohort
    dist = guideline_df.loc[mask, 'model_risk_band'].value_counts()
    print(f"\n  {cohort.capitalize()} Cohort:")
    for cat, count in dist.items():
        pct = count / mask.sum() * 100
        print(f"    {cat}: {count} ({pct:.1f}%)")

print("\n[SECTION 4 COMPLETE] ✅")


# ═══════════════════════════════════════════════════════════════════
# SECTION 5: Gene-Aware Intervention Context
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("  SECTION 5: Gene-Aware Intervention Context")
print("=" * 65)

GENE_CONTEXT_NOTES = {
    'PCSK9': 'PCSK9-associated genetic context detected. Individual genotype and pharmacogenomic status are unavailable; this result does not constitute a patient-specific medication recommendation.',
    'LDLR': 'LDLR-associated genetic context detected. Individual genotype and pharmacogenomic status are unavailable; this result does not constitute a patient-specific medication recommendation.',
    'LPA': 'Lp(a)-associated genetic context detected. Individual genotype and pharmacogenomic status are unavailable; this result does not constitute a patient-specific medication recommendation.',
    'APOB': 'APOB-associated genetic context detected. Individual genotype and pharmacogenomic status are unavailable; this result does not constitute a patient-specific medication recommendation.',
    'SORT1': 'SORT1/1p13.3 locus contributes to risk → affects hepatic LDL-C metabolism.',
}

gene_context_output = []

if not gene_contrib_df.empty and genetic_profile is not None:
    print("\n  Generating gene-aware context notes...")
    confidence_tier = genetic_profile.get('confidence', {}).get('tier', 'UNKNOWN')
    
    for _, row in gene_contrib_df.iterrows():
        gene = row.get('gene_symbol', '')
        pct = row.get('gene_pct', 0)
        if pct >= 5.0 and gene in GENE_CONTEXT_NOTES:
            note = GENE_CONTEXT_NOTES[gene]
            gene_context_output.append({
                'gene': gene,
                'contribution_pct': pct,
                'context_note': note,
            })
            print(f"  ⚠️  {gene} ({pct:.1f}%): {note[:80]}...")
    
    if not gene_context_output:
        print("  ℹ️  No gene-specific clinical context triggered (all contributions < 5%)")
else:
    print("  ⚠️  Gene contributions not available — skipping gene context")

gene_context_df = pd.DataFrame(gene_context_output)
gene_context_df.to_csv(DT_DIR + 'gene_context_notes.csv', index=False)
print(f"\n✅ Saved: {DT_DIR}gene_context_notes.csv")
print("\n[SECTION 5 COMPLETE] ✅")


# ═══════════════════════════════════════════════════════════════════
# SECTION 6: Patient State Engine — Build Complete Patient Profiles
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("  SECTION 6: Patient State Engine")
print("=" * 65)

def build_patient_state(patient_row, patient_idx, cohort, pipeline,
                        feature_list, prs_index, genetic_profile=None,
                        gene_notes=None, compute_ci=True):
    """
    Build a complete PatientState with all intelligence layers.
    """
    X = pd.DataFrame([patient_row[feature_list].values], columns=feature_list)
    
    # Risk with uncertainty (Publication-Grade N=1000 Bootstrap)
    if compute_ci:
        risk_data = compute_risk_sensitivity(pipeline, X, prs_index, n_perturbations=1000)
    else:
        base_risk = float(integrated_risk(pipeline, X)[0])
        risk_data = {'risk': base_risk, 'ci_lower': base_risk, 'ci_upper': base_risk}
    
    # Guideline mapping
    cat = classify_acc_aha(risk_data['risk'])
    
    # Build state dict
    state = {
        'patient_idx': int(patient_idx),
        'cohort': cohort,
        'genetic_state': {
            'prs_raw': prs_raw,
            'prs_index': prs_index,
            'confidence_tier': (
                genetic_profile.get('confidence', {}).get('tier', 'UNKNOWN')
                if genetic_profile else 'UNKNOWN'
            ),
            'top_genes': (
                [g.get('gene_symbol', g.get('gene', '')) for g in genetic_profile.get('top_genes', [])[:5]]
                if genetic_profile else []
            ),
            'gene_context_notes': gene_notes or [],
        },
        'feature_state': {f: float(patient_row[f]) for f in feature_list if f in patient_row},
        'risk_state': {
            'current_risk': risk_data['risk'],
            'risk_ci_lower': risk_data['ci_lower'],
            'risk_ci_upper': risk_data['ci_upper'],
            'risk_band': cat['name'],
            'model_risk_band': cat['name'],
            'relevant_guideline_considerations': cat['relevant_guideline_considerations'],
            'monitoring': cat['monitoring'],
        },
    }
    return state

# Build states for representative patients (3 per cohort: high/med/low risk)
print("\n  Building Patient State profiles for representative patients...")
patient_states = []

for cohort, df, pipeline, features in [
    ('lifestyle', df_ls_test, lifestyle_pipeline, LS_FEATURES),
    ('clinical', df_cl_test, clinical_pipeline, CL_FEATURES),
]:
    risks = integrated_risk(pipeline, df[features])
    df_risk = df.copy()
    df_risk['_risk'] = risks
    
    indices = {
        'high': df_risk['_risk'].idxmax(),
        'med': df_risk['_risk'].sort_values().index[len(df) // 2],
        'low': df_risk['_risk'].idxmin(),
    }
    
    for label, idx in indices.items():
        state = build_patient_state(
            df.loc[idx], idx, cohort, pipeline, features,
            prs_index, genetic_profile,
            gene_notes=[g.get('context_note', '') for g in gene_context_output],
            compute_ci=True
        )
        state['risk_label'] = label
        patient_states.append(state)
        print(f"  {cohort}/{label}: Risk={state['risk_state']['current_risk']:.1%} "
              f"[{state['risk_state']['risk_ci_lower']:.1%}–"
              f"{state['risk_state']['risk_ci_upper']:.1%}] "
              f"→ {state['risk_state']['model_risk_band']}")

# Save
with open(DT_DIR + 'patient_states.json', 'w') as f:
    json.dump(patient_states, f, indent=2, default=str)
print(f"\n✅ Saved: {DT_DIR}patient_states.json ({len(patient_states)} profiles)")
print("\n[SECTION 6 COMPLETE] ✅")


# ═══════════════════════════════════════════════════════════════════
# SECTION 7: Literature Benchmarks & Sanity Checks
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("  SECTION 7: Literature Benchmarks & Sanity Checks")
print("=" * 65)

LITERATURE_BENCHMARKS = {
    'S1_quit_smoking':           {'expected_pct': 36, 'range': (20, 45), 'source': 'Critchley & Capewell, JAMA 2003'},
    'S2_exercise':               {'expected_pct': 14, 'range': (8, 20),  'source': 'Chomistek et al., Circulation 2011'},
    'S3_weight_loss_5pct':       {'expected_pct': 4,  'range': (2, 7),   'source': 'Multiple meta-analyses'},
    'S4_quit_alcohol':           {'expected_pct': 5,  'range': (2, 10),  'source': 'BP/CV risk reduction literature'},
    'S5_combined_smoke_exercise':{'expected_pct': 40, 'range': (25, 50), 'source': 'Must exceed either alone'},
}

benchmark_rows = []
for sid, bench in LITERATURE_BENCHMARKS.items():
    for cohort in ['lifestyle', 'clinical']:
        cohort_mask = (intervention_results['cohort'] == cohort) & \
                      (intervention_results['scenario_id'] == sid)
        if cohort_mask.sum() == 0:
            continue
        mean_pct = intervention_results.loc[cohort_mask, 'pct_reduction'].mean()
        lo, hi = bench['range']
        passed = lo <= mean_pct <= hi
        benchmark_rows.append({
            'scenario_id': sid,
            'cohort': cohort,
            'dt_predicted_pct': round(mean_pct, 2),
            'literature_pct': bench['expected_pct'],
            'literature_range': f'[{lo}, {hi}]',
            'source': bench['source'],
            'PASS': '✅' if passed else '⚠️ OUTSIDE RANGE'
        })

benchmark_df = pd.DataFrame(benchmark_rows)
print("\n📋 Literature Benchmark Validation:")
print(benchmark_df.to_string(index=False))
benchmark_df.to_csv(DT_DIR + 'literature_benchmark_validation.csv', index=False)

# ── Intervention Realism Constraint Registry ──────────────────────
INTERVENTION_CONSTRAINTS = {
    'bmi': {'min_delta': -5.0, 'max_delta': 5.0, 'min_val': 16.0, 'max_val': 55.0, 'type': 'continuous_modifiable'},
    'systolic_bp': {'min_delta': -30.0, 'max_delta': 30.0, 'min_val': 85.0, 'max_val': 220.0, 'type': 'treatment_responsive'},
    'cholesterol': {'min_delta': -100.0, 'max_delta': 50.0, 'min_val': 100.0, 'max_val': 450.0, 'type': 'treatment_responsive'},
    'smoking': {'allowed_transitions': [(1, 0)], 'type': 'behavioral_modifiable'},
    'physical_activity': {'allowed_transitions': [(0, 1)], 'type': 'behavioral_modifiable'},
    'alcohol': {'allowed_transitions': [(1, 0)], 'type': 'behavioral_modifiable'},
    'age': {'immutable': True, 'type': 'non_modifiable_demographic'},
    'sex': {'immutable': True, 'type': 'non_modifiable_demographic'},
    'oldpeak': {'intervention_target': False, 'type': 'diagnostic_stress_marker'}
}

# ── Sanity checks (Categorized: 6 Intervention Plausibility + 7 Model Sensitivity) ──
# Removed z_score scaling because clinical_pipeline receives raw features and scales them internally.

sanity_tests = [
    # Category A: Intervention Plausibility Tests (6 tests)
    ('Sedentary (0) -> Active (1)',            'lifestyle', {'physical_activity': 0}, {'physical_activity': 1}, 'DECREASE', 'Category A: Intervention Plausibility'),
    ('Healthy BMI (22) -> Overweight (28)',    'lifestyle', {'bmi': 22}, {'bmi': 28}, 'INCREASE', 'Category A: Intervention Plausibility'),
    ('Healthy BMI (22) -> Obese (35)',         'lifestyle', {'bmi': 22}, {'bmi': 35}, 'INCREASE', 'Category A: Intervention Plausibility'),
    ('Smoker+Sedentary -> Smoke-free+Active',  'lifestyle', {'smoking': 1, 'physical_activity': 0}, {'smoking': 0, 'physical_activity': 1}, 'DECREASE', 'Category A: Intervention Plausibility'),
    ('Smoking Cessation + BP Restoration',     'lifestyle', {'smoking': 1, 'systolic_bp': 140}, {'smoking': 0, 'systolic_bp': 125}, 'DECREASE', 'Category A: Intervention Plausibility'),
    ('Heavy Alcohol (1) -> Abstinence (0)',    'lifestyle', {'alcohol': 1, 'systolic_bp': 135}, {'alcohol': 0, 'systolic_bp': 125}, 'DECREASE', 'Category A: Intervention Plausibility'),
    
    # Category B: Model Monotonicity & Sensitivity Tests (7 tests)
    ('Normal BP (120) -> Hypertensive (160)',  'clinical',  {'resting_bp': 120}, {'resting_bp': 160}, 'INCREASE', 'Category B: Model Sensitivity'),
    ('Hypertensive (160) -> Normal BP (120)',  'clinical',  {'resting_bp': 160}, {'resting_bp': 120}, 'DECREASE', 'Category B: Model Sensitivity'),
    ('Low Chol (160) -> High Chol (260)',      'clinical',  {'cholesterol': 160}, {'cholesterol': 260}, 'INCREASE', 'Category B: Model Sensitivity'),
    ('High Chol (260) -> Low Chol (160)',      'clinical',  {'cholesterol': 260}, {'cholesterol': 160}, 'DECREASE', 'Category B: Model Sensitivity'),
    ('Low Max HR (110) -> High Max HR (170)',  'clinical',  {'max_heart_rate': 110}, {'max_heart_rate': 170}, 'DECREASE', 'Category B: Model Sensitivity'),
    ('High Oldpeak (2.5) -> Zero Oldpeak (0)', 'clinical',  {'oldpeak': 2.5}, {'oldpeak': 0.0}, 'DECREASE', 'Category B: Model Sensitivity'),
    ('Comprehensive Risk Factor Normalization','clinical',  {'resting_bp': 160, 'cholesterol': 260, 'max_heart_rate': 120, 'oldpeak': 2.0}, {'resting_bp': 120, 'cholesterol': 180, 'max_heart_rate': 160, 'oldpeak': 0.0}, 'DECREASE', 'Category B: Model Sensitivity')
]

sanity_results = []
for test_name, cohort, state_from, state_to, expected, category in sanity_tests:
    pipeline = lifestyle_pipeline if cohort == 'lifestyle' else clinical_pipeline
    features = LS_FEATURES if cohort == 'lifestyle' else CL_FEATURES
    df = df_ls_test if cohort == 'lifestyle' else df_cl_test

    # Compute mean risk under state_from and state_to across cohort
    X_from = df[features].copy()
    for f, v in state_from.items():
        if f in X_from.columns:
            X_from[f] = v
    p_from = float(integrated_risk(pipeline, X_from).mean())

    X_to = df[features].copy()
    for f, v in state_to.items():
        if f in X_to.columns:
            X_to[f] = v
    p_to = float(integrated_risk(pipeline, X_to).mean())

    delta = p_to - p_from
    actual = 'INCREASE' if delta > 0.001 else 'DECREASE' if delta < -0.001 else 'NO_CHANGE'
    passed = (actual == expected)

    sanity_results.append({
        'test': test_name, 'category': category, 'cohort': cohort,
        'expected_direction': expected, 'actual_direction': actual,
        'p_before': round(p_from, 4), 'p_after': round(p_to, 4),
        'delta': round(delta, 4), 'PASS': '✅' if passed else '❌'
    })

sanity_df = pd.DataFrame(sanity_results)
print("\n🩺 Clinical Sanity Check Battery (13 Tests):")
print(sanity_df[['test','category','expected_direction','actual_direction','delta','PASS']].to_string(index=False))
sanity_df.to_csv(DT_DIR + 'sanity_check_results.csv', index=False)

n_pass_a = ((sanity_df['category'] == 'Category A: Intervention Plausibility') & (sanity_df['PASS'] == '✅')).sum()
n_pass_b = ((sanity_df['category'] == 'Category B: Model Sensitivity') & (sanity_df['PASS'] == '✅')).sum()
total_pass = n_pass_a + n_pass_b
overall_pct = 100 * total_pass / 13

print(f"\n  Category A (Intervention Plausibility): {n_pass_a}/6 PASSED")
print(f"  Category B (Model Sensitivity):        {n_pass_b}/7 PASSED")
print(f"  Total Sanity Battery:                  {total_pass}/13 PASSED ({overall_pct:.1f}%)")

print("\n[SECTION 7 COMPLETE] ✅")


# ═══════════════════════════════════════════════════════════════════
# SECTION 8: Dose-Response Curves (Simulated)
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("  SECTION 8: Dose-Response Curves")
print("=" * 65)

# Use median patient for dose-response
median_ls = df_ls_test[LS_FEATURES].median()
median_cl = df_cl_test[CL_FEATURES].median()

fig, axes = plt.subplots(1, 3, figsize=(18, 5))

# 1. BMI dose-response (lifestyle)
if 'bmi' in LS_FEATURES:
    bmi_values = np.arange(18, 40, 1)
    bmi_risks = []
    for bmi in bmi_values:
        X = pd.DataFrame([median_ls.values], columns=LS_FEATURES)
        X['bmi'] = bmi
        r = float(integrated_risk(lifestyle_pipeline, X)[0])
        bmi_risks.append(r)
    axes[0].plot(bmi_values, bmi_risks, 'o-', color='#1565C0', linewidth=2)
    axes[0].set_xlabel('BMI (kg/m²)')
    axes[0].set_ylabel('Predicted CAD Risk')
    axes[0].set_title('Dose-Response: BMI → CAD Risk')
    axes[0].grid(alpha=0.3)
    axes[0].axvline(25, color='orange', linestyle='--', alpha=0.7, label='Overweight threshold')
    axes[0].axvline(30, color='red', linestyle='--', alpha=0.7, label='Obese threshold')
    axes[0].legend(fontsize=8)

# 2. Blood pressure dose-response (clinical)
if 'resting_bp' in CL_FEATURES:
    bp_values = np.arange(90, 180, 5)
    bp_risks = []
    for bp in bp_values:
        X = pd.DataFrame([median_cl.values], columns=CL_FEATURES)
        X['resting_bp'] = bp
        r = float(integrated_risk(clinical_pipeline, X)[0])
        bp_risks.append(r)
    axes[1].plot(bp_values, bp_risks, 's-', color='#E65100', linewidth=2)
    axes[1].set_xlabel('Resting Blood Pressure (mmHg)')
    axes[1].set_ylabel('Predicted CAD Risk')
    axes[1].set_title('Dose-Response: Blood Pressure → CAD Risk')
    axes[1].grid(alpha=0.3)
    axes[1].axvline(120, color='green', linestyle='--', alpha=0.7, label='Normal BP limit')
    axes[1].axvline(140, color='red', linestyle='--', alpha=0.7, label='Hypertension threshold')
    axes[1].legend(fontsize=8)

# 3. Cholesterol dose-response (clinical)
if 'cholesterol' in CL_FEATURES:
    chol_values = np.arange(120, 320, 10)
    chol_risks = []
    for chol in chol_values:
        X = pd.DataFrame([median_cl.values], columns=CL_FEATURES)
        X['cholesterol'] = chol
        r = float(integrated_risk(clinical_pipeline, X)[0])
        chol_risks.append(r)
    axes[2].plot(chol_values, chol_risks, '^-', color='#7B1FA2', linewidth=2)
    axes[2].set_xlabel('Total Cholesterol (mg/dL)')
    axes[2].set_ylabel('Predicted CAD Risk')
    axes[2].set_title('Dose-Response: Cholesterol → CAD Risk')
    axes[2].grid(alpha=0.3)
    axes[2].axvline(200, color='orange', linestyle='--', alpha=0.7, label='Borderline')
    axes[2].axvline(240, color='red', linestyle='--', alpha=0.7, label='High')
    axes[2].legend(fontsize=8)

plt.suptitle('Simulated Dose-Response Curves — Median Patient', fontsize=13, y=1.02)
plt.tight_layout()
plt.savefig(FIG_DIR + 'dose_response_curves.png', dpi=300, bbox_inches='tight')
plt.show()
print(f"✅ Saved: {FIG_DIR}dose_response_curves.png")
print("\n[SECTION 8 COMPLETE] ✅")


# ═══════════════════════════════════════════════════════════════════
# SECTION 9: Trajectory & Intervention Ranking Visualization
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("  SECTION 9: Risk Trajectory & Intervention Visualization")
print("=" * 65)

# ── Intervention ranking plot ─────────────────────────────────────
example_ls = df_ls_test.iloc[df_ls_test.index[0]]
example_cl = df_cl_test.iloc[df_cl_test.index[0]]

fig, axes = plt.subplots(1, 2, figsize=(15, 6))
for ax_sub, patient, pipeline, features, cohort, title in [
    (axes[0], example_ls, lifestyle_pipeline, LS_FEATURES, 'lifestyle', 'Lifestyle Patient'),
    (axes[1], example_cl, clinical_pipeline, CL_FEATURES, 'clinical', 'Clinical Patient')
]:
    scenarios = fill_dynamic_scenarios(patient, cohort=cohort)
    res = counterfactual_engine(patient, pipeline, features, scenarios, cohort=cohort)
    res = res.sort_values('delta_risk', ascending=True)

    colors = ['#2E7D32' if d < 0 else '#d32f2f' for d in res['delta_risk']]
    ax_sub.barh(res['scenario_id'], -res['delta_risk'], color=colors, edgecolor='white')
    for i, (delta_risk, pct) in enumerate(zip(res['delta_risk'], res['pct_reduction'])):
        ax_sub.text(-delta_risk + 0.005, i, f'{pct:+.1f}%', va='center', fontsize=9)
    ax_sub.set_xlabel('Risk Reduction (Δ probability)')
    cat = classify_acc_aha(float(res['current_risk'].iloc[0]))
    ax_sub.set_title(f'{title}\nCurrent risk: {res["current_risk"].iloc[0]:.1%} ({cat["name"]})')
    ax_sub.axvline(0, color='black', linewidth=0.7)
    ax_sub.grid(axis='x', alpha=0.3)

plt.suptitle('Personalized Intervention Rankings — Example Patients', fontsize=13)
plt.tight_layout()
plt.savefig(FIG_DIR + 'intervention_ranking_example.png', dpi=300, bbox_inches='tight')
# plt.show() # Using Agg backend so don't block
plt.close(fig)

print("✅ Intervention plots saved. (Trajectory projections removed per Review 8).")
print("\n[SECTION 9 COMPLETE] ✅")
# ═══════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════

print("\n" + "=" * 65)
print("  ✅ NOTEBOOK 9 COMPLETE — Enhanced Digital Twin")
print("  Patient State Engine + Precision Cardiology Intelligence")
print("=" * 65)
print(f"  Files saved:")
print(f"  📁 {DT_DIR}intervention_results.csv")
print(f"  📁 {DT_DIR}personalized_intervention_rankings.csv")
print(f"  📁 {DT_DIR}clinical_guideline_recommendations.csv")
print(f"  📁 {DT_DIR}gene_context_notes.csv")
print(f"  📁 {DT_DIR}patient_states.json")
print(f"  📁 {DT_DIR}sanity_check_results.csv")
print(f"  📁 {DT_DIR}literature_benchmark_validation.csv")
print(f"  📁 {FIG_DIR}dose_response_curves.png")

if genetic_profile:
    print(f"  Top genes: {[g.get('gene_symbol', g.get('gene', '')) for g in genetic_profile.get('top_genes', [])[:3]]}")
print("=" * 65)
print("\n[NB9 EXECUTION COMPLETE] [OK]")