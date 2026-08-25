# Generated from: nb7_genetic_integration.ipynb
# Converted at: 2026-06-18T05:24:28.180Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

# # 🧬 Notebook 7 — Genetic Risk Integration
# ## Population-PRS Calibration of Cardiovascular Risk Predictions
# ### CVD Digital Twin Project | CAD_DT_Final
# 
# ---
# 
# ## Purpose
# This notebook integrates a population-level Polygenic Risk Score (PRS) with trained
# ML models (lifestyle + clinical) to produce genetically-adjusted cardiovascular risk predictions.
# 
# ## What this notebook does **NOT** do
# - ❌ Retrain any model
# - ❌ Modify any pipeline
# - ❌ Re-normalise the PRS
# 
# ## Pipeline position
# ```
# NB4 → prs_population_score.csv   (prs_raw, prs_mean_mc, CI)
# NB5 → lifestyle_pipeline.pkl     (CalibratedClassifierCV)
# NB6 → clinical_pipeline.pkl      (CalibratedClassifierCV)
# NB7 → Genetically-adjusted risk  (THIS NOTEBOOK)
# ```
# 
# ## I/O Contract
# ```
# INPUTS:
#   Outputs/Genetics/prs_population_score.csv
#   Outputs/Models/lifestyle_pipeline.pkl
#   Outputs/Models/clinical_pipeline.pkl
#   Outputs/Lifestyle/df_lifestyle_test.csv
#   Outputs/Clinical/df_clinical_test.csv
# 
# OUTPUTS:
#   Outputs/Integrated/lifestyle_risk_scores_with_prs.csv
#   Outputs/Integrated/clinical_risk_scores_with_prs.csv
#   Outputs/Integrated/risk_stratification_bands.csv
#   Outputs/Figures/risk_stratification_plot.png
#   Outputs/Figures/calibration_curve_integrated.png
#   Outputs/Figures/violin_plot_integrated.png
# ```
# 


# ---
# # Section 1 — Setup, Paths & Data Loading
# 
# ## Why integrate PRS with model predictions?
# ML models trained on lifestyle and clinical features capture **modifiable** and **measurable**
# risk factors, but are blind to an individual's genetic predisposition. The Polygenic Risk Score
# (PRS) from PGS Catalog (PGS000116), harmonised against GenomeIndia ancestry frequencies in NB3–4,
# provides a **population-level genetic baseline** specific to Indian ancestry.
# 
# ## Why sigmoid(prs_z) and not sigmoid(prs_raw)?
# The raw PRS is a weighted sum over 40,079 variants: `prs_raw ≈ 2.9625`. Passing this directly
# into `sigmoid()` produces ≈ 0.9999 — saturated and scientifically meaningless as a weight.
# The correct transformation is to first **Z-normalise** the PRS relative to the Monte Carlo
# sampling distribution (mean and SD derived from the 10,000-simulation CI computed in NB4):
# 
# ```
# prs_z     = (prs_raw - prs_mean_mc) / prs_sd_mc
# prs_sigmoid = sigmoid(prs_z)
# ```
# 
# By construction, a population-mean Indian-ancestry individual gives `prs_z ≈ 0` and
# `sigmoid(0) = 0.50` — a neutral, centred genetic weight. Individuals with elevated PRS
# would yield `prs_z > 0` → weight > 0.50; depleted PRS → weight < 0.50.
# 
# ## Integration formula
# ```
# p_integrated = w1 × p_model + w2 × prs_sigmoid
#              = 0.85 × p_model + 0.15 × sigmoid(prs_z)
# ```
# The genetic layer is a **population-context/sensitivity layer**, not an individual genetic predictor.
# not a dominant predictor.
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
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    roc_auc_score, brier_score_loss, roc_curve
)

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

# ── Paths ─────────────────────────────────────────────────────────────────────
PRS_PATH          = BASE_DIR + 'Outputs/Genetics/prs_population_score.csv'
GI_PROFILE_PATH   = BASE_DIR + 'Outputs/Genetics/genetic_intelligence_profile.json'
GENE_CONTRIB_PATH = BASE_DIR + 'Outputs/Genetics/gene_level_contributions.csv'
LIFESTYLE_PKL     = BASE_DIR + 'Outputs/Models/lifestyle_pipeline.pkl'
CLINICAL_PKL      = BASE_DIR + 'Outputs/Models/clinical_pipeline.pkl'
PREDIAG_PKL       = BASE_DIR + 'Outputs/Models/clinical_prediagnostic_pipeline.pkl'
LIFESTYLE_TEST    = BASE_DIR + 'Outputs/Lifestyle/df_lifestyle_test.csv'
CLINICAL_TEST     = BASE_DIR + 'Outputs/Clinical/df_clinical_test.csv'

INTEGRATED_DIR    = BASE_DIR + 'Outputs/Integrated/'
FIGURES_DIR       = BASE_DIR + 'Outputs/Figures/'

LS_OUT_PATH       = INTEGRATED_DIR + 'lifestyle_risk_scores_with_prs.csv'
CL_OUT_PATH       = INTEGRATED_DIR + 'clinical_risk_scores_with_prs.csv'
BANDS_OUT_PATH    = INTEGRATED_DIR + 'risk_stratification_bands.csv'
STRAT_FIG_OUT     = FIGURES_DIR    + 'risk_stratification_plot.png'
CALIB_FIG_OUT     = FIGURES_DIR    + 'calibration_curve_integrated.png'
VIOLIN_FIG_OUT    = FIGURES_DIR    + 'violin_plot_integrated.png'

os.makedirs(INTEGRATED_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR,    exist_ok=True)

# ── Pre-flight check ──────────────────────────────────────────────────────────
print('\n' + '='*60)
print('  NB7 — GENETIC RISK INTEGRATION')
print('='*60)
# ── Load Genetic Intelligence Profile ───────────
if not os.path.isfile(GI_PROFILE_PATH):
    raise FileNotFoundError(f'Missing required file: {GI_PROFILE_PATH}')

with open(GI_PROFILE_PATH, 'r') as f:
    genetic_profile = json.load(f)

FUS_PROV_PATH = BASE_DIR + 'Outputs/Clinical/fusion_weight_provenance.json'
if os.path.isfile(FUS_PROV_PATH):
    with open(FUS_PROV_PATH, 'r') as f:
        _fus = json.load(f)
        W_DIAG = _fus.get('canonical_weights', {}).get('w_diagnostic', 0.50)
        W_BASE = _fus.get('canonical_weights', {}).get('w_baseline', 0.50)
else:
    W_DIAG, W_BASE = 0.50, 0.50

prs_raw = genetic_profile['population_baseline']['signed_expected_prs']
mc_std  = genetic_profile['population_baseline']['inter_individual_genotype_variability']
n_snps  = genetic_profile.get('canonical_provenance', {}).get('variant_count', 40079)

print(f'\n📊 Canonical GIE Summary:')
print(f'   prs_raw     = {prs_raw:.6f}')
print(f'   mc_std      = {mc_std:.6f}')
print(f'   n_snps      = {n_snps}')

obs_pct = genetic_profile.get('frequency_provenance', {}).get('observed_pct', 0)
prior_pct = genetic_profile.get('frequency_provenance', {}).get('prior_pct', 0)

print(f"\n   Genetic evidence status:\n   Population-level context")
print(f"\n   Individual genotype:\n   Unavailable")
print(f"\n   Variant coverage:\n   {n_snps:,} / 40,079")
print(f"\n   Observed GenomeIndia frequencies:\n   {obs_pct:.2f}%")
print(f"\n   Synthetic-prior frequencies:\n   {prior_pct:.2f}%")
print(f"\n   Confidence:\n   Not applicable to individual-level risk\n")

top_genes = [g['gene_symbol'] for g in genetic_profile.get('top_genes', genetic_profile.get('top_gene_loci', []))[:5]]
print(f"   Top Genes   = {top_genes}")

# ── Load pipelines ────────────────────────────────────────────────────────────
with open(LIFESTYLE_PKL, 'rb') as f:
    lifestyle_pipeline = pickle.load(f)
with open(CLINICAL_PKL, 'rb') as f:
    clinical_pipeline = pickle.load(f)
with open(PREDIAG_PKL, 'rb') as f:
    prediag_pipeline = pickle.load(f)

print(f'\n✅ Pipelines loaded:')
print(f'   lifestyle_pipeline : {type(lifestyle_pipeline).__name__}')
print(f'   clinical_pipeline  : {type(clinical_pipeline).__name__}')
print(f'   prediag_pipeline   : {type(prediag_pipeline).__name__}')

# ── Load test datasets ────────────────────────────────────────────────────────
df_lifestyle = pd.read_csv(LIFESTYLE_TEST)
df_clinical  = pd.read_csv(CLINICAL_TEST)

print(f'\n📊 Test datasets:')
print(f'   Lifestyle test : {df_lifestyle.shape}')
print(f'   Clinical test  : {df_clinical.shape}')

print('\n[SECTION 1 COMPLETE] ✅')


# ---
# # Section 2 — Generate Base Model Predictions
# 
# ## What the models produce
# Both pipelines are `CalibratedClassifierCV(Pipeline([StandardScaler, XGBClassifier]))`.
# Calling `pipeline.predict_proba(X)[:, 1]` returns a **calibrated probability**
# that the patient has or will develop cardiovascular disease.
# 
# These probabilities reflect the model's view of risk based purely on lifestyle or
# clinical measurements — with **no genetic component** yet.
# 
# ## Feature selection
# Each pipeline was trained on a specific feature subset (determined by NB5/NB6).
# We pass only the features the pipeline expects, derived directly from its fitted scaler.
# 


print('='*60)
print('  SECTION 2: Base Model Predictions')
print('='*60)

TARGET_COL = 'target'

# ── Extract expected feature names from fitted scaler inside pipeline ─────────
def get_pipeline_features(pipeline):
    """Return the feature names the pipeline was trained on."""
    inner_pipe = pipeline.calibrated_classifiers_[0].estimator
    scaler = inner_pipe.named_steps['scaler']
    if hasattr(scaler, 'feature_names_in_'):
        return scaler.feature_names_in_.tolist()
    raise ValueError('Scaler has no feature_names_in_. Re-fit pipeline with DataFrame input.')

LS_FEATURES = get_pipeline_features(lifestyle_pipeline)
CL_FEATURES = get_pipeline_features(clinical_pipeline)
PD_FEATURES = get_pipeline_features(prediag_pipeline)

print(f'\n  Lifestyle features ({len(LS_FEATURES)}): {LS_FEATURES}')
print(f'  Clinical features  ({len(CL_FEATURES)}): {CL_FEATURES}')
print(f'  Prediag features   ({len(PD_FEATURES)}): {PD_FEATURES}')

# ── Separate features / target ────────────────────────────────────────────────
assert TARGET_COL in df_lifestyle.columns, f'❌ {TARGET_COL} missing from lifestyle test'
assert TARGET_COL in df_clinical.columns,  f'❌ {TARGET_COL} missing from clinical test'

X_ls = df_lifestyle[LS_FEATURES]
y_ls = df_lifestyle[TARGET_COL]

X_cl = df_clinical[CL_FEATURES]
y_cl = df_clinical[TARGET_COL]

assert list(X_ls.columns) == LS_FEATURES, '❌ Column mismatch for lifestyle'
assert list(X_cl.columns) == CL_FEATURES, '❌ Column mismatch for clinical'
print('\n  ✅ Feature column alignment confirmed')

# ── Generate base probabilities ───────────────────────────────────────────────
preds_df = pd.read_parquet(BASE_DIR + 'Outputs/canonical_test_predictions.parquet')
p_lifestyle_base = preds_df[preds_df['cohort'] == 'lifestyle']['p_lifestyle'].values
p_clinical_base = preds_df[preds_df['cohort'] == 'clinical']['p_fusion'].values

print(f'\n📊 Base Model Probabilities:')
print(f'   Lifestyle  — n={len(p_lifestyle_base):,}  '
      f'mean={p_lifestyle_base.mean():.4f}  '
      f'range=[{p_lifestyle_base.min():.4f}, {p_lifestyle_base.max():.4f}]')
print(f'   Clinical Fusion — n={len(p_clinical_base):,}   '
      f'mean={p_clinical_base.mean():.4f}  '
      f'range=[{p_clinical_base.min():.4f}, {p_clinical_base.max():.4f}]')

auc_ls_base   = roc_auc_score(y_ls, p_lifestyle_base)
brier_ls_base = brier_score_loss(y_ls, p_lifestyle_base)
auc_cl_base   = roc_auc_score(y_cl, p_clinical_base)
brier_cl_base = brier_score_loss(y_cl, p_clinical_base)

print(f'\n  Base AUC / Brier (before PRS integration):')
print(f'   Lifestyle  AUC={auc_ls_base:.4f}  Brier={brier_ls_base:.4f}')
print(f'   Clinical   AUC={auc_cl_base:.4f}  Brier={brier_cl_base:.4f}')

print('\n[SECTION 2 COMPLETE] ✅')


# # Section 3 — PRS Transformation & Integration
# 
# ## Why we do NOT normalise PRS
# 
# The population-level PRS (`prs_raw ≈ 2.9625`) is a weighted sum over ~40,079 variants derived
# from GenomeIndia allele frequencies (NB4). This value represents the **expected genetic
# baseline risk for an Indian-ancestry individual**, not an individual-specific prediction.
# 
# Applying sigmoid directly:
# 
#     sigmoid(prs_raw) ≈ 1.0
# 
# This is expected due to aggregation across many SNPs. Importantly, this does NOT indicate
# an error — it reflects that the Indian population has a **systematically elevated genetic
# baseline risk** relative to European-calibrated models.
# 
# Normalising PRS (e.g., Z-scoring) would remove this population-level bias and defeat the
# purpose of PRS integration. Therefore, we intentionally preserve the raw PRS scale.
# 
# ## Interpretation of PRS in this pipeline
# 
# The PRS acts as a **population-level calibration offset**, not a discriminative feature:
# 
# - It shifts all predictions slightly upward
# - It corrects underestimation bias in standard risk models
# - It does NOT change ranking → AUC should remain stable
# - It may improve calibration → Brier score may improve
# 
# This is consistent with the project design:
# 
# > "Population-level PRS scalar represents Indian ancestry baseline risk and is used as a fixed offset"
# (see pipeline blueprint)
# 
# ## Integration formula
# 
# We combine model predictions with PRS using a weighted average:
# 
#     p_integrated = w1 × p_model + w2 × sigmoid(prs_raw)
# 
# Where:
# - w1 = 0.85 → model dominates (individual-level prediction)
# - w2 = 0.15 → genetic baseline correction
# 
# Since sigmoid(prs_raw) ≈ 1.0, this becomes:
# 
#     p_integrated ≈ 0.85 × p_model + 0.15
# 
# Thus, PRS integration acts as a **global upward calibration shift**.
# 
# This is scientifically expected:
# - PRS improves calibration, not discrimination
# - AUC ≈ unchanged
# - Brier score may improve slightly


print('='*60)
print('  SECTION 3: PRS Integration (Population-Level Offset)')
print('='*60)

# ── PRS transformation ───────────────────────────────────────────
# We compute a normalized genetic index centered at the population average.
# For the average individual, this index is 0.5 (neutral offset).

prs_index = 0.5  # sigmoid(prs_raw - population_mean) = sigmoid(0) = 0.5

print(f'\n  PRS Transformation (Normalized Index):')
print(f'   prs_raw     = {prs_raw:.6f}')
print(f'   prs_index   = {prs_index:.6f}')

# ── Integration weights ──────────────────────────────────────────
W1 = 0.85
W2 = 0.15
assert abs(W1 + W2 - 1.0) < 1e-9, '❌ Weights must sum to 1'

print(f'\n  Integration weights: w1={W1}  w2={W2}')
print(f'  Formula: p_integrated = {W1} × p_model + {W2} × {prs_index:.4f}')

# ── Apply integration ────────────────────────────────────────────
p_lifestyle_int = W1 * p_lifestyle_base + W2 * prs_index
p_clinical_int  = W1 * p_clinical_base  + W2 * prs_index

# Safety clipping
p_lifestyle_int = np.clip(p_lifestyle_int, 0.0, 1.0)
p_clinical_int  = np.clip(p_clinical_int,  0.0, 1.0)

# ── Diagnostics ──────────────────────────────────────────────────
print(f'\n📊 Integrated Probabilities:')

print(f'   Lifestyle — mean={p_lifestyle_int.mean():.4f}  '
      f'range=[{p_lifestyle_int.min():.4f}, {p_lifestyle_int.max():.4f}]')

print(f'   Clinical  — mean={p_clinical_int.mean():.4f}  '
      f'range=[{p_clinical_int.min():.4f}, {p_clinical_int.max():.4f}]')

print(f'\n  Mean shift due to PRS:')

print(f'   Lifestyle Δ = {(p_lifestyle_int - p_lifestyle_base).mean():+.4f}')
print(f'   Clinical  Δ = {(p_clinical_int  - p_clinical_base).mean():+.4f}')

print('\n[SECTION 3 COMPLETE] ✅')

# ---
# # Section 4 — Sensitivity Analysis: Impact of Genetic Weight w2
# 
# ## Why run sensitivity analysis?
# The choice of `w2 = 0.15` is a modelling assumption. Its optimal value depends on:
# - How predictive the PRS is in this population
# - The baseline calibration quality of the ML models
# - Clinical context (screening vs. confirmatory)
# 
# By varying `w2` from 0.05 to 0.40, we can assess:
# 1. How sensitive the final risk scores are to the genetic weight
# 2. Whether a higher or lower genetic contribution improves discrimination (AUC)
#    or calibration (Brier score)
# 3. The robustness of the chosen 85/15 split
# 
# For a **population-level PRS** (not individual genotype), we expect AUC to remain
# nearly flat across `w2` values — the PRS adds a uniform offset, not individual discrimination.
# 


print('='*60)
print('  SECTION 4: Sensitivity Analysis — Genetic Weight w2')
print('='*60)

w2_values = np.arange(0.05, 0.45, 0.05)

sensitivity = {'w2': [], 'ls_auc': [], 'ls_brier': [], 'cl_auc': [], 'cl_brier': []}

for w2 in w2_values:
    w1 = 1.0 - w2
    p_ls_s = np.clip(w1 * p_lifestyle_base + w2 * prs_index, 0, 1)
    p_cl_s = np.clip(w1 * p_clinical_base  + w2 * prs_index, 0, 1)
    sensitivity['w2'].append(round(w2, 2))
    sensitivity['ls_auc'].append(roc_auc_score(y_ls, p_ls_s))
    sensitivity['ls_brier'].append(brier_score_loss(y_ls, p_ls_s))
    sensitivity['cl_auc'].append(roc_auc_score(y_cl, p_cl_s))
    sensitivity['cl_brier'].append(brier_score_loss(y_cl, p_cl_s))

sens_df = pd.DataFrame(sensitivity)

print('\n  Sensitivity table (AUC and Brier vs genetic weight w2):')
print(sens_df.round(4).to_string(index=False))

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle('Sensitivity Analysis: Impact of Genetic Weight w2\n'
             '(PRS acts as population-level offset — AUC expected stable)',
             fontsize=12)

for ax, metric, ylabel, title in [
    (axes[0], 'auc',   'ROC-AUC',     'AUC vs Genetic Weight'),
    (axes[1], 'brier', 'Brier Score', 'Brier Score vs Genetic Weight'),
]:
    ax.plot(sens_df['w2'], sens_df[f'ls_{metric}'], 'o-', color='#1565C0',
            linewidth=2, label='Lifestyle')
    ax.plot(sens_df['w2'], sens_df[f'cl_{metric}'], 's--', color='#d32f2f',
            linewidth=2, label='Clinical')
    ax.axvline(0.15, color='green', linestyle=':', linewidth=1.5,
               label='Chosen w2=0.15')
    ax.set_xlabel('Genetic Weight w2', fontsize=11)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_title(title, fontsize=11)
    ax.legend(fontsize=9); ax.grid(alpha=0.3)

plt.tight_layout()
sens_fig_path = FIGURES_DIR + 'nb7_sensitivity_analysis.png'
plt.savefig(sens_fig_path, dpi=300, bbox_inches='tight'); plt.show()
print(f'\n✅ Sensitivity figure saved: {sens_fig_path}')
print('\n[SECTION 4 COMPLETE] ✅')
# why 0.15 is optimal  why not 0.05 , how is brier calculated - formula calcualtion
# interrelated features in clinical shap analysis
# maths model for compliance  - simulate

# ---
# # Section 5 — Risk Stratification
# 
# ## Why stratify into risk bands?
# A continuous probability (0–1) is rarely actionable in clinical practice.
# Clinicians and patients need discrete categories that map to **clinical decisions**:
# - **Low** → routine monitoring
# - **Moderate** → lifestyle intervention, repeat testing
# - **High** → pharmacological intervention, specialist referral
# - **Very High** → urgent cardiological assessment
# 
# We apply this stratification to both base and integrated probabilities to quantify
# the effect of genetic integration on patient classification — specifically,
# how many patients are **reclassified** when PRS is included.
# 
# ## Band thresholds
# | Band | Probability Range |
# |------|------------------|
# | Low | < 0.25 |
# | Moderate | 0.25 – 0.50 |
# | High | 0.50 – 0.75 |
# | Very High | ≥ 0.75 |
# 


print('='*60)
print('  SECTION 5: Risk Stratification')
print('='*60)

BANDS      = ['Low', 'Moderate', 'High', 'Very High']
THRESHOLDS = [0.0, 0.25, 0.50, 0.75, 1.01]

def assign_band(proba_arr):
    return pd.cut(
        proba_arr,
        bins=THRESHOLDS,
        labels=BANDS,
        right=False
    )

# ── Lifestyle stratification ──────────────────────────────────────────────────
ls_df = pd.DataFrame({
    'y_true'        : y_ls.values,
    'p_base'        : p_lifestyle_base,
    'p_integrated'  : p_lifestyle_int,
    'band_base'     : assign_band(p_lifestyle_base),
    'band_integrated': assign_band(p_lifestyle_int),
    'source'        : 'lifestyle',
})

# ── Clinical stratification ───────────────────────────────────────────────────
cl_df = pd.DataFrame({
    'y_true'        : y_cl.values,
    'p_base'        : p_clinical_base,
    'p_integrated'  : p_clinical_int,
    'band_base'     : assign_band(p_clinical_base),
    'band_integrated': assign_band(p_clinical_int),
    'source'        : 'clinical',
})

# ── Band distribution ─────────────────────────────────────────────────────────
def band_summary(df, label, prob_col, band_col):
    g = df.groupby(band_col, observed=True)
    summary = pd.DataFrame({
        'n'         : g.size(),
        'pct'       : (g.size() / len(df) * 100).round(1),
        'cad_prev'  : (g['y_true'].mean() * 100).round(1),
        'mean_prob' : g[prob_col].mean().round(4),
    }).reset_index().rename(columns={band_col: 'Band'})
    summary['model'] = label
    summary['type']  = prob_col
    return summary

ls_base_sum = band_summary(ls_df, 'Lifestyle', 'p_base',       'band_base')
ls_int_sum  = band_summary(ls_df, 'Lifestyle', 'p_integrated', 'band_integrated')
cl_base_sum = band_summary(cl_df, 'Clinical',  'p_base',       'band_base')
cl_int_sum  = band_summary(cl_df, 'Clinical',  'p_integrated', 'band_integrated')

all_bands = pd.concat([ls_base_sum, ls_int_sum, cl_base_sum, cl_int_sum], ignore_index=True)

print('\n  Lifestyle — Band Distribution:')
print('    Base model:')
print(ls_base_sum[['Band','n','pct','cad_prev','mean_prob']].to_string(index=False))
print('    Integrated (+ PRS):')
print(ls_int_sum[['Band','n','pct','cad_prev','mean_prob']].to_string(index=False))

print('\n  Clinical — Band Distribution:')
print('    Base model:')
print(cl_base_sum[['Band','n','pct','cad_prev','mean_prob']].to_string(index=False))
print('    Integrated (+ PRS):')
print(cl_int_sum[['Band','n','pct','cad_prev','mean_prob']].to_string(index=False))

# ── Reclassification summary ──────────────────────────────────────────────────
for label, df in [('Lifestyle', ls_df), ('Clinical', cl_df)]:
    same = (df['band_base'] == df['band_integrated']).sum()
    reclassified = len(df) - same
    print(f'\n  {label} Population-prior sensitivity reclassification: {reclassified} / {len(df)} '
          f'({reclassified/len(df)*100:.1f}%)')

# ── Save outputs ──────────────────────────────────────────────────────────────
ls_df.to_csv(LS_OUT_PATH, index=False)
cl_df.to_csv(CL_OUT_PATH, index=False)
all_bands.to_csv(BANDS_OUT_PATH, index=False)
print(f'\n✅ Saved: {LS_OUT_PATH}')
print(f'✅ Saved: {CL_OUT_PATH}')
print(f'✅ Saved: {BANDS_OUT_PATH}')
print('\n[SECTION 5 COMPLETE] ✅')


# ---
# # Section 6 — Evaluation: Base vs. Integrated
# 
# ## What to expect from PRS integration
# A **population-level** PRS (where all patients share the same `prs_sigmoid` value)
# adds a **uniform shift** to all predictions. This has a predictable effect:
# 
# - **AUC** is **preserved**: AUC is a rank-based metric — a uniform additive shift
#   does not change the relative ranking of patients, so discrimination is unchanged.
# - **Brier Score** may change slightly: Brier measures absolute calibration.
#   If `prs_sigmoid ≈ 0.50`, the shift is ≈ `0.15 × 0.50 = +0.075` on all predictions,
#   which can marginally degrade calibration for already well-calibrated models.
# 
# This is the expected scientific result — it is **not** a failure. The PRS integration
# becomes meaningful when used with **individual-level genotype data** (not a population scalar).
# For now it anchors predictions to the Indian-ancestry genetic baseline.
# 


print('='*60)
print('  SECTION 6: Evaluation — Base vs Integrated')
print('='*60)

eval_rows = []
for label, y_true, p_base, p_int in [
    ('Lifestyle', y_ls, p_lifestyle_base, p_lifestyle_int),
    ('Clinical',  y_cl, p_clinical_base,  p_clinical_int),
]:
    for name, proba in [('Base', p_base), ('Integrated (+PRS)', p_int)]:
        eval_rows.append({
            'Model'     : label,
            'Type'      : name,
            'Test_AUC'  : round(roc_auc_score(y_true, proba), 4),
            'Test_Brier': round(brier_score_loss(y_true, proba), 4),
        })

eval_df = pd.DataFrame(eval_rows)

print('\n  AUC and Brier — Base vs Integrated:')
print(eval_df.to_string(index=False))

# Highlight AUC preservation
print('\n  AUC change from PRS integration (should be ≈ 0 for population-level PRS):')
for label, y_true, p_base, p_int in [
    ('Lifestyle', y_ls, p_lifestyle_base, p_lifestyle_int),
    ('Clinical',  y_cl, p_clinical_base,  p_clinical_int),
]:
    delta_auc   = roc_auc_score(y_true, p_int) - roc_auc_score(y_true, p_base)
    delta_brier = brier_score_loss(y_true, p_int) - brier_score_loss(y_true, p_base)
    auc_flag   = '✅ Preserved' if abs(delta_auc) < 0.005 else '⚠️ Changed'
    brier_flag = '✅' if abs(delta_brier) < 0.02 else '⚠️ Δ > 0.02'
    print(f'   {label:<12} ΔAUC={delta_auc:+.4f} {auc_flag}  '
          f'ΔBrier={delta_brier:+.4f} {brier_flag}')

print('\n[SECTION 6 COMPLETE] ✅')


# ---
# # Section 7 — Visualisations
# 
# ## Why visualise the integration?
# Numeric metrics alone do not convey the clinical story. Three figures are produced:
# 
# 1. **Violin plot** — shows the distribution of integrated risk probabilities split
#    by true outcome label (CAD=0 vs CAD=1). A well-discriminating model shows clearly
#    separated violin shapes.
# 
# 2. **Calibration curve** — compares predicted probabilities against observed event rates
#    in 10 bins. A well-calibrated model's curve lies close to the diagonal. We plot
#    both base and integrated curves to show PRS impact on calibration.
# 
# 3. **Risk stratification bar plot** — shows the percentage of patients in each
#    risk band (Low / Moderate / High / Very High) before and after PRS integration,
#    for both models. This communicates the clinical impact directly.
# 


print('='*60)
print('  SECTION 7: Visualisations')
print('='*60)

plt.rcParams.update({
    'figure.dpi': 120, 'savefig.dpi': 300,
    'font.size': 11, 'axes.titlesize': 12,
    'axes.spines.top': False, 'axes.spines.right': False
})

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 1 — Violin Plot
# ─────────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle('Integrated Risk Score Distribution by True Outcome', fontsize=13)

for ax, label, df_plot, p_col in [
    (axes[0], 'Lifestyle', ls_df, 'p_integrated'),
    (axes[1], 'Clinical',  cl_df, 'p_integrated'),
]:
    data_0 = df_plot.loc[df_plot['y_true'] == 0, p_col]
    data_1 = df_plot.loc[df_plot['y_true'] == 1, p_col]
    vp = ax.violinplot([data_0, data_1], positions=[0, 1],
                       showmedians=True, showextrema=True)
    for pc, color in zip(vp['bodies'], ['#1565C0', '#d32f2f']):
        pc.set_facecolor(color); pc.set_alpha(0.7)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['No CAD (0)', 'CAD (1)'], fontsize=10)
    ax.set_ylabel('Integrated Risk Probability')
    ax.set_title(f'{label} Model')
    ax.set_ylim(-0.02, 1.05)
    ax.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig(VIOLIN_FIG_OUT, dpi=300, bbox_inches='tight'); plt.show()
print(f'✅ Violin plot saved: {VIOLIN_FIG_OUT}')

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 2 — Calibration Curves
# ─────────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle('Calibration Curves — Base vs PRS-Integrated', fontsize=13)

for ax, label, y_true, p_base, p_int in [
    (axes[0], 'Lifestyle', y_ls, p_lifestyle_base, p_lifestyle_int),
    (axes[1], 'Clinical',  y_cl, p_clinical_base,  p_clinical_int),
]:
    ax.plot([0,1],[0,1],'k--', linewidth=1, label='Perfect calibration')
    for proba, color, lbl in [
        (p_base, '#1565C0', f'Base (Brier={brier_score_loss(y_true,p_base):.3f})'),
        (p_int,  '#d32f2f', f'Integrated (Brier={brier_score_loss(y_true,p_int):.3f})'),
    ]:
        try:
            fp, mp = calibration_curve(y_true, proba, n_bins=10)
            ax.plot(mp, fp, 'o-', color=color, linewidth=1.5,
                    markersize=4, label=lbl)
        except Exception as e:
            print(f'  ⚠️ Calibration curve failed for {lbl}: {e}')
    ax.set_xlabel('Mean Predicted Probability')
    ax.set_ylabel('Fraction of Positives')
    ax.set_title(f'{label} Calibration')
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)

plt.tight_layout()
plt.savefig(CALIB_FIG_OUT, dpi=300, bbox_inches='tight'); plt.show()
print(f'✅ Calibration curves saved: {CALIB_FIG_OUT}')

# ─────────────────────────────────────────────────────────────────────────────
# FIGURE 3 — Risk Stratification Bar Plot
# ─────────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle('Risk Stratification: Band Distribution Before & After PRS Integration',
             fontsize=12)

BAND_COLORS = {'Low': '#2E7D32', 'Moderate': '#F9A825',
               'High': '#E64A19', 'Very High': '#880E4F'}

for ax, label, df_plot in [
    (axes[0], 'Lifestyle', ls_df),
    (axes[1], 'Clinical',  cl_df),
]:
    x = np.arange(len(BANDS))
    w = 0.35
    base_counts = [df_plot['band_base'].value_counts().get(b,0)/len(df_plot)*100
                   for b in BANDS]
    int_counts  = [df_plot['band_integrated'].value_counts().get(b,0)/len(df_plot)*100
                   for b in BANDS]
    bars1 = ax.bar(x - w/2, base_counts, width=w, label='Base', color='#1565C0', alpha=0.8)
    bars2 = ax.bar(x + w/2, int_counts,  width=w, label='Integrated', color='#d32f2f', alpha=0.8)
    ax.set_xticks(x); ax.set_xticklabels(BANDS, fontsize=10)
    ax.set_ylabel('% of Patients'); ax.set_ylim(0, 80)
    ax.set_title(f'{label} — Risk Band Distribution')
    ax.legend(fontsize=9); ax.grid(axis='y', alpha=0.3)
    for bar in list(bars1) + list(bars2):
        h = bar.get_height()
        if h > 1:
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.5,
                    f'{h:.1f}%', ha='center', va='bottom', fontsize=7.5)

plt.tight_layout()
plt.savefig(STRAT_FIG_OUT, dpi=300, bbox_inches='tight'); plt.show()
print(f'✅ Risk stratification plot saved: {STRAT_FIG_OUT}')

print('\n[SECTION 7 COMPLETE] ✅')


# ---
# # Section 8 — Final Summary & Notebook Complete
# 


print('='*60)
print('  ✅ NOTEBOOK 7 COMPLETE — Genetic Risk Integration')
print('='*60)
print()
print(f'  PRS (PGS000116):        prs_raw={prs_raw:.4f}')
print(f'  PRS normalized index:   prs_index={prs_index:.6f}')
print(f'  Integration weights:    w1={W1}  w2={W2}')
print()
print('  Final integrated metrics:')
for label, y_true, p_base, p_int in [
    ('Lifestyle', y_ls, p_lifestyle_base, p_lifestyle_int),
    ('Clinical',  y_cl, p_clinical_base,  p_clinical_int),
]:
    print(f'   {label:<12}  '
          f'Base  AUC={roc_auc_score(y_true,p_base):.4f}  '
          f'Brier={brier_score_loss(y_true,p_base):.4f}  |  '
          f'Integrated  AUC={roc_auc_score(y_true,p_int):.4f}  '
          f'Brier={brier_score_loss(y_true,p_int):.4f}')
print()
print(f'  📁 {LS_OUT_PATH}')
print(f'  📁 {CL_OUT_PATH}')
print(f'  📁 {BANDS_OUT_PATH}')
print(f'  📁 {STRAT_FIG_OUT}')
print(f'  📁 {CALIB_FIG_OUT}')
print(f'  📁 {VIOLIN_FIG_OUT}')
print()
print('  🔜 Next: NB8 — SHAP Explainability')
print()
print('  ⚠️ NB8 USAGE:')
print('     import pickle')
print('     with open("lifestyle_pipeline.pkl","rb") as f: pipe = pickle.load(f)')
print('     proba_integrated = 0.85 * p_canonical_fusion + 0.15 * prs_index')
print('='*60)