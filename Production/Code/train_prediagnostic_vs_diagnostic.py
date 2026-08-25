# -*- coding: utf-8 -*-
"""train_prediagnostic_vs_diagnostic.py
Clinical Feature Ablation Audit & Baseline vs Diagnostic Models
Precision Cardiology Intelligence Platform | CAD_DT_Final
"""

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
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, brier_score_loss, roc_curve
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.pipeline import Pipeline

BASE_DIR = r"E:/Capstone/Production/"
CLINICAL_DIR = os.path.join(BASE_DIR, "Outputs/Clinical/")
MODELS_DIR = os.path.join(BASE_DIR, "Outputs/Models/")
FIGURES_DIR = os.path.join(BASE_DIR, "Outputs/Figures/")

for d in [CLINICAL_DIR, MODELS_DIR, FIGURES_DIR]:
    os.makedirs(d, exist_ok=True)

# Load preprocessed clinical data
df_cl_train = pd.read_csv(os.path.join(CLINICAL_DIR, "df_clinical_train.csv"))
df_cl_test = pd.read_csv(os.path.join(CLINICAL_DIR, "df_clinical_test.csv"))

# Load existing diagnostic pipeline
with open(os.path.join(MODELS_DIR, "clinical_pipeline.pkl"), 'rb') as f:
    cal_diag = pickle.load(f)

inner_diag = cal_diag.calibrated_classifiers_[0].estimator
scaler_diag = inner_diag.named_steps['scaler']
DIAG_FEATURES = list(scaler_diag.feature_names_in_)

# Baseline clinical features (removes stress-test 'oldpeak')
BASELINE_FEATURES = [f for f in DIAG_FEATURES if f != 'oldpeak']

print("=" * 65)
print("  CLINICAL FEATURE ABLATION AUDIT: BASELINE VS DIAGNOSTIC")
print("=" * 65)
print(f"  Full Diagnostic Feature Set ({len(DIAG_FEATURES)}): {DIAG_FEATURES}")
print(f"  Baseline Feature Set ({len(BASELINE_FEATURES)}): {BASELINE_FEATURES}")

X_train_diag = df_cl_train[DIAG_FEATURES]
X_test_diag = df_cl_test[DIAG_FEATURES]
y_train = df_cl_train['target'].values
y_test = df_cl_test['target'].values

X_train_base = df_cl_train[BASELINE_FEATURES]
X_test_base = df_cl_test[BASELINE_FEATURES]

# Train Baseline Clinical Pipeline
best_params_base = {
    'n_estimators': 150,
    'max_depth': 3,
    'learning_rate': 0.05,
    'subsample': 0.8,
    'random_state': 42
}

pipe_base = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', GradientBoostingClassifier(**best_params_base))
])

cal_base = CalibratedClassifierCV(estimator=pipe_base, method='sigmoid', cv=5)
cal_base.fit(X_train_base, y_train)

# Predictions
p_test_diag = cal_diag.predict_proba(X_test_diag)[:, 1]
p_test_base = cal_base.predict_proba(X_test_base)[:, 1]

auc_diag = roc_auc_score(y_test, p_test_diag)
brier_diag = brier_score_loss(y_test, p_test_diag)

auc_base = roc_auc_score(y_test, p_test_base)
brier_base = brier_score_loss(y_test, p_test_base)

print("\n📊 Model Comparison Results:")
print(f"  1. Full Diagnostic Clinical Model (10 Features with exercise oldpeak):")
print(f"     Test AUC:   {auc_diag:.4f}")
print(f"     Brier Loss: {brier_diag:.4f}")
print(f"\n  2. Baseline Clinical Model (9 Features without exercise oldpeak):")
print(f"     Test AUC:   {auc_base:.4f}")
print(f"     Brier Loss: {brier_base:.4f}")
print(f"     Discrimination Gain from Oldpeak: ΔAUC = {auc_diag - auc_base:+.4f}")

# Save Baseline Pipeline
base_model_path = os.path.join(MODELS_DIR, "clinical_prediagnostic_pipeline.pkl")
with open(base_model_path, 'wb') as f:
    pickle.dump(cal_base, f)
print(f"\nSaved baseline pipeline: {base_model_path}")

# Export Metrics JSON
metrics = {
    'diagnostic_model': {
        'model_name': 'Diagnostic Clinical Model (XGBoost)',
        'features': DIAG_FEATURES,
        'n_features': len(DIAG_FEATURES),
        'test_auc': round(float(auc_diag), 4),
        'test_brier': round(float(brier_diag), 4),
        'clinical_role': 'Diagnostic confirmation utilizing exercise-induced ST-depression (oldpeak)'
    },
    'baseline_model': {
        'model_name': 'Baseline Clinical Model (GradientBoosting)',
        'features': BASELINE_FEATURES,
        'n_features': len(BASELINE_FEATURES),
        'test_auc': round(float(auc_base), 4),
        'test_brier': round(float(brier_base), 4),
        'clinical_role': 'Routine clinical intake assessment without exercise ST-depression marker'
    },
    'comparison': {
        'delta_auc': round(float(auc_diag - auc_base), 4),
        'delta_brier': round(float(brier_diag - brier_base), 4),
        'methodological_insight': f'Adding exercise-induced ST-depression information improves test discrimination by ΔAUC = {auc_diag - auc_base:+.4f} (AUC {auc_base:.4f} -> {auc_diag:.4f}), validating the staged clinical ensemble hierarchy.'
    }
}

metrics_path = os.path.join(CLINICAL_DIR, "prediagnostic_vs_diagnostic_metrics.json")
with open(metrics_path, 'w') as f:
    json.dump(metrics, f, indent=2)
print(f"Saved comparison metrics: {metrics_path}")

# Plot Comparative ROC Curves
fpr_diag, tpr_diag, _ = roc_curve(y_test, p_test_diag)
fpr_base, tpr_base, _ = roc_curve(y_test, p_test_base)

plt.figure(figsize=(8, 6), dpi=300)
plt.plot(fpr_diag, tpr_diag, color='#1976D2', lw=2.5, label=f'Diagnostic Model (AUC = {auc_diag:.4f})')
plt.plot(fpr_base, tpr_base, color='#388E3C', lw=2.5, linestyle='--', label=f'Baseline Clinical (AUC = {auc_base:.4f})')
plt.plot([0, 1], [0, 1], color='#757575', linestyle=':', lw=1.5, label='Chance (AUC = 0.5000)')
plt.xlim([-0.02, 1.02])
plt.ylim([-0.02, 1.02])
plt.xlabel('False Positive Rate (1 - Specificity)', fontsize=12, fontweight='bold')
plt.ylabel('True Positive Rate (Sensitivity)', fontsize=12, fontweight='bold')
plt.title('Clinical Model: Diagnostic vs Baseline Discrimination', fontsize=13, fontweight='bold')
plt.legend(loc='lower right', frameon=True, facecolor='white', framealpha=0.95, fontsize=11)
plt.grid(True, alpha=0.3)
plt.tight_layout()

fig_path = os.path.join(FIGURES_DIR, "prediagnostic_vs_diagnostic_roc.png")
plt.savefig(fig_path)
plt.close()
print(f"Saved ROC figure: {fig_path}")
print("\n[CLINICAL FEATURE ABLATION AUDIT COMPLETE] [OK]")
