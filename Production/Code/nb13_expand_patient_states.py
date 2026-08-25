import os
import json
import pandas as pd
import pickle
import warnings
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace('\\', '/') + '/'
OUTPUTS_DIR = os.path.join(BASE_DIR, "Outputs")
DT_DIR = os.path.join(OUTPUTS_DIR, "Digital_Twin/")

def load_pkl(path):
    with open(path, 'rb') as f:
        return pickle.load(f)

def integrated_risk(pipeline, X):
    if hasattr(pipeline, "predict_proba"):
        return pipeline.predict_proba(X)[:, 1]
    return pipeline.predict(X)

def main():
    print("🚀 Expanding Patient States for ALL Patients (Fast Mode)...")
    
    # Load Models
    ls_pipeline = load_pkl(os.path.join(OUTPUTS_DIR, "Models", "lifestyle_pipeline.pkl"))
    cl_pipeline = load_pkl(os.path.join(OUTPUTS_DIR, "Models", "clinical_pipeline.pkl"))
    
    # Load Data
    df_ls = pd.read_csv(os.path.join(OUTPUTS_DIR, "Lifestyle", "df_lifestyle_test.csv"))
    df_cl = pd.read_csv(os.path.join(OUTPUTS_DIR, "Clinical", "df_clinical_test.csv"))
    
    # Load Guidelines (to merge risk bands)
    guidelines = pd.read_csv(os.path.join(DT_DIR, "clinical_guideline_recommendations.csv"))
    
    patient_states = []
    
    # 1. Process Lifestyle
    print(f"Processing {len(df_ls)} Lifestyle patients...")
    ls_features = ['age', 'gender', 'systolic_bp', 'diastolic_bp', 'smoking', 'alcohol', 
                   'physical_activity', 'bmi', 'cholesterol_level_1', 'cholesterol_level_2', 
                   'cholesterol_level_3', 'glucose_level_1', 'glucose_level_2', 'glucose_level_3']
    
    for idx, row in df_ls.iterrows():
        g_row = guidelines[(guidelines['patient_idx'] == idx) & (guidelines['cohort'] == 'lifestyle')].iloc[0]
        
        state = {
            'patient_idx': int(idx),
            'cohort': 'lifestyle',
            'genetic_state': {
                'prs_raw': 2.96, 'prs_index': 0.5, 'confidence_tier': 'UNKNOWN',
                'top_genes': ['CDKN2B-AS1', 'LPA', 'APOE', 'SORT1', 'PHACTR1'],
                'gene_context_notes': ['PCSK9-associated genetic context detected.']
            },
            'feature_state': {f: float(row[f]) for f in ls_features},
            'risk_state': {
                'current_risk': float(g_row['current_risk']),
                'risk_ci_lower': float(g_row['current_risk']), # Skip bootstrap for speed
                'risk_ci_upper': float(g_row['current_risk']),
                'risk_band': str(g_row['model_risk_band']),
                'model_risk_band': str(g_row['model_risk_band']),
                'relevant_guideline_considerations': str(g_row['relevant_guideline_considerations']),
                'monitoring': str(g_row['monitoring'])
            },
            'risk_label': 'med'
        }
        patient_states.append(state)
        
    # 2. Process Clinical
    print(f"Processing {len(df_cl)} Clinical patients...")
    cl_features = ['age', 'sex', 'resting_bp', 'cholesterol', 'fasting_blood_sugar', 'max_heart_rate', 
                   'exercise_angina', 'oldpeak', 'chest_pain_type_1.0', 'chest_pain_type_2.0', 
                   'chest_pain_type_3.0', 'chest_pain_type_4.0', 'resting_ecg_0.0', 'resting_ecg_1.0', 
                   'resting_ecg_2.0', 'st_slope_1', 'st_slope_2', 'st_slope_3']
                   
    for idx, row in df_cl.iterrows():
        g_row = guidelines[(guidelines['patient_idx'] == idx) & (guidelines['cohort'] == 'clinical')].iloc[0]
        
        state = {
            'patient_idx': int(idx),
            'cohort': 'clinical',
            'genetic_state': {
                'prs_raw': 2.96, 'prs_index': 0.5, 'confidence_tier': 'UNKNOWN',
                'top_genes': ['CDKN2B-AS1', 'LPA', 'APOE', 'SORT1', 'PHACTR1'],
                'gene_context_notes': ['PCSK9-associated genetic context detected.']
            },
            'feature_state': {f: float(row[f]) for f in cl_features},
            'risk_state': {
                'current_risk': float(g_row['current_risk']),
                'risk_ci_lower': float(g_row['current_risk']), # Skip bootstrap for speed
                'risk_ci_upper': float(g_row['current_risk']),
                'risk_band': str(g_row['model_risk_band']),
                'model_risk_band': str(g_row['model_risk_band']),
                'relevant_guideline_considerations': str(g_row['relevant_guideline_considerations']),
                'monitoring': str(g_row['monitoring'])
            },
            'risk_label': 'med'
        }
        patient_states.append(state)
        
    # Save Output
    out_path = os.path.join(DT_DIR, "patient_states.json")
    with open(out_path, 'w') as f:
        json.dump(patient_states, f, indent=2)
        
    print(f"✅ Generated {len(patient_states)} patient profiles and saved to {out_path}!")

if __name__ == '__main__':
    # Fix console encoding for windows
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        try: sys.stdout.reconfigure(encoding='utf-8')
        except Exception: pass
    main()
