import os
import sys
import json
import pickle
import pandas as pd
import shap

def main():
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Missing arguments"}))
        sys.exit(1)
        
    patient_id = int(sys.argv[1])
    model_type = sys.argv[2]
    
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    OUTPUTS_DIR = os.path.join(BASE_DIR, "Production", "Outputs")
    
    PATIENT_STATES_PATH = os.path.join(OUTPUTS_DIR, "Digital_Twin", "patient_states.json")
    MODEL_LS_PATH = os.path.join(OUTPUTS_DIR, "Models", "lifestyle_pipeline.pkl")
    MODEL_CL_PATH = os.path.join(OUTPUTS_DIR, "Models", "clinical_pipeline.pkl")
    
    model_path = MODEL_LS_PATH if model_type == "lifestyle" else MODEL_CL_PATH
    
    try:
        with open(PATIENT_STATES_PATH, 'r') as f:
            patients = json.load(f)
            
        patient_features = None
        for p in patients:
            if p.get("patient_idx") == patient_id:
                patient_features = p.get("feature_state", {})
                break
                
        if not patient_features:
            print(json.dumps({"error": "Patient not found"}))
            sys.exit(1)
            
        with open(model_path, "rb") as f:
            pipeline = pickle.load(f)
            
        inner = pipeline.calibrated_classifiers_[0].estimator
        scaler = inner.named_steps['scaler']
        clf = inner.named_steps['clf']
        features_list = scaler.feature_names_in_.tolist()
        
        X_df = pd.DataFrame([patient_features])[features_list]
        X_scaled = scaler.transform(X_df)
        
        explainer = shap.TreeExplainer(clf)
        sv = explainer.shap_values(X_scaled)
        
        if isinstance(sv, list):
            sv = sv[1][0]
            ev = explainer.expected_value[1] if isinstance(explainer.expected_value, list) else explainer.expected_value
        else:
            sv = sv[0]
            ev = explainer.expected_value
            
        waterfall_data = [{"feature": fn, "shap_value": float(val)} for fn, val in zip(features_list, sv)]
        waterfall_data.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        
        print(json.dumps({
            "expected_value": float(ev) if ev is not None else 0.0,
            "attributions": waterfall_data
        }))
        
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
