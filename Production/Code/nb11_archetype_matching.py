import os
import sys
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.neighbors import NearestNeighbors
import json

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace('\\', '/') + '/'

def main():
    print("Starting Archetype Matching Pipeline")
    
    # Paths
    lifestyle_path = os.path.join(BASE_DIR, 'Outputs/Lifestyle/df_lifestyle_test.csv')
    clinical_path = os.path.join(BASE_DIR, 'Outputs/Clinical/df_clinical_test.csv')
    pulse_path = os.path.join(BASE_DIR, 'Outputs/Pulse/pulse_haemodynamic_deltas.csv')
    out_csv = os.path.join(BASE_DIR, 'Outputs/Pulse/archetype_matched_pulse.csv')
    out_json = os.path.join(BASE_DIR, 'Outputs/Pulse/archetype_matching_report.json')
    
    # 1. Load Data
    print("Loading data...")
    df_l = pd.read_csv(lifestyle_path)
    df_c = pd.read_csv(clinical_path)
    df_p = pd.read_csv(pulse_path)
    
    print(f"Lifestyle patients: {len(df_l)}")
    print(f"Clinical patients: {len(df_c)}")
    print(f"Pulse rows: {len(df_p)}")
    
    # 2. Extract Shared Features
    # Lifestyle: age, gender, systolic_bp
    # Clinical: age, sex, resting_bp
    X_l = df_l[['age', 'gender', 'systolic_bp']].copy()
    X_l.columns = ['age', 'sex', 'bp'] # Align names
    
    X_c = df_c[['age', 'sex', 'resting_bp']].copy()
    X_c.columns = ['age', 'sex', 'bp'] # Align names
    
    # 3. Normalize
    # We fit the scaler on the clinical cohort so the space is defined by the archetype pool
    scaler = MinMaxScaler()
    X_c_scaled = scaler.fit_transform(X_c)
    X_l_scaled = scaler.transform(X_l)
    
    # 4. K-Nearest Neighbors
    print("Computing k-NN distances...")
    knn = NearestNeighbors(n_neighbors=1, metric='euclidean')
    knn.fit(X_c_scaled)
    
    distances, indices = knn.kneighbors(X_l_scaled)
    distances = distances.flatten()
    indices = indices.flatten()
    
    # 5. Thresholding
    threshold = np.percentile(distances, 95)
    print(f"95th percentile distance threshold: {threshold:.4f}")
    
    # Create mapping dataframe
    map_df = pd.DataFrame({
        'lifestyle_id': df_l.index,
        'clinical_id': indices,
        'distance': distances
    })
    map_df['is_low_confidence'] = map_df['distance'] > threshold
    
    print(f"Low confidence matches: {map_df['is_low_confidence'].sum()} / {len(map_df)}")
    
    # 6. Map Pulse Data
    print("Mapping Pulse profiles to Lifestyle patients...")
    # df_p has patient_id corresponding to df_c index (0 to 237)
    
    # Merge map_df with df_p on clinical_id == patient_id
    mapped_pulse = pd.merge(map_df, df_p, left_on='clinical_id', right_on='patient_id', how='left')
    
    # Rename columns to form the final borrowed dataset
    # We drop the old clinical patient_id and use lifestyle_id as the new patient_id
    mapped_pulse.drop(columns=['patient_id'], inplace=True)
    mapped_pulse.rename(columns={'lifestyle_id': 'patient_id'}, inplace=True)
    
    # Add metadata columns
    mapped_pulse['data_source'] = 'archetype_match'
    mapped_pulse.rename(columns={'clinical_id': 'archetype_source_id'}, inplace=True)
    
    # Reorder columns to match original pulse + new metadata
    original_cols = list(df_p.columns)
    original_cols.remove('patient_id')
    final_cols = ['patient_id', 'data_source', 'archetype_source_id', 'distance', 'is_low_confidence'] + original_cols
    mapped_pulse = mapped_pulse[final_cols]
    
    # 7. Save
    print("Saving outputs...")
    mapped_pulse.to_csv(out_csv, index=False)
    
    report = {
        'total_lifestyle_patients': len(df_l),
        'total_clinical_archetypes': len(df_c),
        'mean_distance': float(np.mean(distances)),
        'median_distance': float(np.median(distances)),
        'threshold_95th': float(threshold),
        'low_confidence_count': int(map_df['is_low_confidence'].sum()),
        'total_mapped_pulse_rows': len(mapped_pulse)
    }
    
    with open(out_json, 'w') as f:
        json.dump(report, f, indent=2)
        
    print(f"✅ Success. Output saved to {out_csv}")
    print(f"Mapped {len(mapped_pulse)} rows for {len(df_l)} patients.")

if __name__ == '__main__':
    main()
