import os
import json
import pickle
import pandas as pd
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Paths to the frozen outputs
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUTS_DIR = os.path.join(BASE_DIR, "Production", "Outputs")

PATIENT_STATES_PATH = os.path.join(OUTPUTS_DIR, "Digital_Twin", "patient_states.json")
PULSE_DELTAS_PATH = os.path.join(OUTPUTS_DIR, "Pulse", "pulse_haemodynamic_deltas.csv")
ARCHETYPE_PULSE_PATH = os.path.join(OUTPUTS_DIR, "Pulse", "archetype_matched_pulse.csv")
INTERVENTION_RANKINGS_PATH = os.path.join(OUTPUTS_DIR, "Digital_Twin", "personalized_intervention_rankings.csv")

# Phase 2 Paths
GENE_CONTRIB_PATH = os.path.join(OUTPUTS_DIR, "Genetics", "gene_level_contributions.csv")
PATHWAY_CONTRIB_PATH = os.path.join(OUTPUTS_DIR, "Genetics", "pgs000116_pathway_contributions.csv")
PGX_PATH = os.path.join(OUTPUTS_DIR, "Genetics", "pgs000116_pharmacogenomics.csv")

MODEL_LS_PATH = os.path.join(OUTPUTS_DIR, "Models", "lifestyle_pipeline.pkl")
MODEL_CL_PATH = os.path.join(OUTPUTS_DIR, "Models", "clinical_pipeline.pkl")

app = FastAPI(title="CAD Digital Twin API")

# Allow CORS for local React development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, 'r') as f:
        return json.load(f)

def load_csv_as_dict(path):
    if not os.path.exists(path):
        return []
    df = pd.read_csv(path)
    return df.to_dict(orient="records")

@app.get("/")
def read_root():
    return {"status": "CAD Digital Twin Backend Online"}

# --- PHASE 1 ENDPOINTS ---

@app.get("/api/patients")
def get_all_patients():
    patients = load_json(PATIENT_STATES_PATH)
    return {"patients": patients}

@app.get("/api/patient/{patient_id}")
def get_patient(patient_id: int):
    patients = load_json(PATIENT_STATES_PATH)
    # IDs 0-237 exist in both cohorts. Prioritize Clinical natively.
    clinical_match = next((p for p in patients if p.get("patient_idx") == patient_id and p.get("cohort") == "clinical"), None)
    if clinical_match:
        return clinical_match
        
    lifestyle_match = next((p for p in patients if p.get("patient_idx") == patient_id and p.get("cohort") == "lifestyle"), None)
    if lifestyle_match:
        return lifestyle_match
        
    raise HTTPException(status_code=404, detail="Patient not found")

@app.get("/api/pulse/{patient_id}")
def get_pulse_data(patient_id: int):
    # Figure out which cohort this patient belongs to (same logic as get_patient)
    patients = load_json(PATIENT_STATES_PATH)
    patient = next((p for p in patients if p.get("patient_idx") == patient_id and p.get("cohort") == "clinical"), None)
    if not patient:
        patient = next((p for p in patients if p.get("patient_idx") == patient_id and p.get("cohort") == "lifestyle"), None)
        
    if not patient:
        return {"pulse_data": []}
        
    if patient["cohort"] == "clinical":
        deltas = load_csv_as_dict(PULSE_DELTAS_PATH)
        patient_deltas = [d for d in deltas if d.get("patient_id") == patient_id]
        for p in patient_deltas:
            p['data_source'] = 'measured'
        return {"pulse_data": patient_deltas}
    else:
        archetypes = load_csv_as_dict(ARCHETYPE_PULSE_PATH)
        patient_archetypes = [a for a in archetypes if a.get("patient_id") == patient_id]
        return {"pulse_data": patient_archetypes}

@app.get("/api/interventions/{patient_id}")
def get_interventions(patient_id: int):
    # Figure out which cohort this patient belongs to
    patients = load_json(PATIENT_STATES_PATH)
    patient = next((p for p in patients if p.get("patient_idx") == patient_id and p.get("cohort") == "clinical"), None)
    if not patient:
        patient = next((p for p in patients if p.get("patient_idx") == patient_id and p.get("cohort") == "lifestyle"), None)
        
    if not patient:
        return {"interventions": []}
        
    interventions = load_csv_as_dict(INTERVENTION_RANKINGS_PATH)
    # CRITICAL: Filter by BOTH patient_idx AND cohort to avoid collisions!
    patient_ints = [i for i in interventions if i.get("patient_idx") == patient_id and i.get("cohort") == patient["cohort"]]
    return {"interventions": patient_ints}

# --- PHASE 2 ENDPOINTS ---

@app.get("/api/genetics/genes")
def get_gene_contributions():
    return {"genes": load_csv_as_dict(GENE_CONTRIB_PATH)}

@app.get("/api/genetics/pathways")
def get_pathway_contributions():
    return {"pathways": load_csv_as_dict(PATHWAY_CONTRIB_PATH)}

@app.get("/api/genetics/pharmacogenomics")
def get_pgx_context():
    return {"pgx": load_csv_as_dict(PGX_PATH)}

import subprocess

@app.get("/api/explainability/shap/{patient_id}")
async def get_shap_values(patient_id: int, model_type: str = "clinical"):
    """Dynamically computes local SHAP values using an isolated subprocess to prevent OpenMP deadlocks on Windows"""
    try:
        script_path = os.path.join(os.path.dirname(__file__), "compute_shap.py")
        result = subprocess.run(
            ["python", script_path, str(patient_id), model_type],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Subprocess error: {result.stderr}")
            
        data = json.loads(result.stdout)
        if "error" in data:
            raise HTTPException(status_code=500, detail=data["error"])
            
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error computing SHAP: {e}")


class ScreeningRequest(BaseModel):
    age: float
    sex: float
    resting_bp: float
    cholesterol: float
    fasting_blood_sugar: float
    max_heart_rate: float

@app.post("/api/screen")
def screen_patient(req: ScreeningRequest):
    # Load model
    with open(MODEL_CL_PATH, 'rb') as f:
        pipeline = pickle.load(f)
        
    features = {
        'age': req.age,
        'sex': req.sex,
        'resting_bp': req.resting_bp,
        'cholesterol': req.cholesterol,
        'fasting_blood_sugar': req.fasting_blood_sugar,
        'max_heart_rate': req.max_heart_rate,
        'exercise_angina': 0.0,
        'oldpeak': 0.0,
        'chest_pain_type_1.0': 0.0,
        'chest_pain_type_2.0': 0.0,
        'chest_pain_type_3.0': 0.0,
        'chest_pain_type_4.0': 1.0,
        'resting_ecg_0.0': 0.0,
        'resting_ecg_1.0': 1.0,
        'resting_ecg_2.0': 0.0,
        'st_slope_1': 0.0,
        'st_slope_2': 1.0,
        'st_slope_3': 0.0,
    }
    
    df_base = pd.DataFrame([features])
    base_risk = float(pipeline.predict_proba(df_base)[0][1])
    
    df_cl_path = os.path.join(OUTPUTS_DIR, "Clinical", "df_clinical_test.csv")
    df_cl = pd.read_csv(df_cl_path)
    new_id = len(df_cl)
    
    df_base['target'] = 1 if base_risk > 0.5 else 0
    df_base.to_csv(df_cl_path, mode='a', header=False, index=False)
    
    interventions = [
        {"scenario": "S1_BP_reduction", "bp_delta": -15, "chol_delta": 0, "hr_delta": 0},
        {"scenario": "S4_cholesterol_reduction", "bp_delta": 0, "chol_delta": -40, "hr_delta": 0},
        {"scenario": "S2_exercise_hr_bp", "bp_delta": -5, "chol_delta": 0, "hr_delta": 15},
        {"scenario": "Combined", "bp_delta": -15, "chol_delta": -40, "hr_delta": 15},
    ]
    
    intervention_rows = []
    for intr in interventions:
        df_sim = df_base.copy()
        df_sim['resting_bp'] += intr['bp_delta']
        df_sim['cholesterol'] += intr['chol_delta']
        df_sim['max_heart_rate'] += intr['hr_delta']
        
        sim_risk = float(pipeline.predict_proba(df_sim.drop(columns=['target']))[0][1])
        reduction = base_risk - sim_risk
        
        intervention_rows.append({
            "patient_idx": new_id,
            "cohort": "clinical",
            "scenario": intr["scenario"],
            "baseline_risk": base_risk,
            "simulated_risk": sim_risk,
            "risk_reduction": reduction
        })
        
    df_ints = pd.DataFrame(intervention_rows)
    df_ints.to_csv(INTERVENTION_RANKINGS_PATH, mode='a', header=False, index=False)
    
    band = "Low"
    if base_risk >= 0.20: band = "High"
    elif base_risk >= 0.075: band = "Intermediate"
    elif base_risk >= 0.05: band = "Borderline"
        
    states = []
    if os.path.exists(PATIENT_STATES_PATH):
        with open(PATIENT_STATES_PATH, 'r') as f:
            states = json.load(f)
            
    new_state = {
        "patient_idx": new_id,
        "cohort": "clinical",
        "predicted_risk": base_risk,
        "risk_band": band,
        "clinical_features": features,
        "lifestyle_features": None
    }
    states.append(new_state)
    with open(PATIENT_STATES_PATH, 'w') as f:
        json.dump(states, f, indent=2)
        
    return {"patient_idx": new_id, "message": "Patient screened successfully"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
