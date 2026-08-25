import React from 'react';
import { motion } from 'framer-motion';
import { User, Activity, Dna, Heart } from 'lucide-react';

const PatientProfile = ({ patientData }) => {
  if (!patientData) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem' }}>
        <h2 className="text-neon-cyan">Loading Patient State...</h2>
      </div>
    );
  }

  const { feature_state, genetic_state } = patientData;

  // Helper to format values
  const formatVal = (val) => typeof val === 'number' && !Number.isInteger(val) ? val.toFixed(1) : val;

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
  };

  return (
    <motion.div 
      initial="hidden" 
      animate="visible" 
      variants={{ visible: { transition: { staggerChildren: 0.1 } } }}
    >
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 className="text-neon-cyan">Initialize Patient State (S_t)</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Construct the patient's baseline clinical, lifestyle, and genetic context.
        </p>
      </div>

      <div className="grid-3">
        {/* Demographics & Clinical */}
        <motion.div className="glass-card" variants={cardVariants}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
            <User color="var(--neon-cyan)" />
            <h2 style={{ margin: 0 }}>Clinical State</h2>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Age</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{formatVal(feature_state.age)}</div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Sex</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                {feature_state.gender !== undefined ? (feature_state.gender === 1 ? 'Male' : 'Female') : (feature_state.sex === 1 ? 'Male' : 'Female')}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Systolic BP</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{feature_state.systolic_bp || feature_state.resting_bp} <span style={{fontSize: '0.8rem', fontWeight: 'normal'}}>mmHg</span></div>
            </div>
            {feature_state.diastolic_bp && (
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Diastolic BP</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{feature_state.diastolic_bp} <span style={{fontSize: '0.8rem', fontWeight: 'normal'}}>mmHg</span></div>
              </div>
            )}
            {feature_state.cholesterol && (
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Cholesterol</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{feature_state.cholesterol} <span style={{fontSize: '0.8rem', fontWeight: 'normal'}}>mg/dL</span></div>
              </div>
            )}
            {feature_state.max_heart_rate && (
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Max HR</div>
                <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{feature_state.max_heart_rate} <span style={{fontSize: '0.8rem', fontWeight: 'normal'}}>bpm</span></div>
              </div>
            )}
          </div>
        </motion.div>

        {/* Lifestyle */}
        <motion.div className="glass-card" variants={cardVariants}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
            <Activity color="var(--neon-green)" />
            <h2 style={{ margin: 0 }}>Lifestyle State</h2>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>BMI</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                {feature_state.bmi ? formatVal(feature_state.bmi) : 'N/A'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Smoking Status</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                {feature_state.smoking === 1 ? <span className="text-neon-red">Active</span> : <span className="text-neon-green">Non-smoker</span>}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Alcohol</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                {feature_state.alcohol === 1 ? 'Yes' : 'No'}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Physical Activity</div>
              <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                {feature_state.physical_activity === 1 ? <span className="text-neon-green">Active</span> : <span className="text-neon-red">Sedentary</span>}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Genetic Context */}
        <motion.div className="glass-card" variants={cardVariants} style={{ border: '1px solid rgba(188, 19, 254, 0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
            <Dna color="var(--neon-purple)" />
            <h2 style={{ margin: 0 }}>Genetic Context</h2>
          </div>
          
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Population Base</div>
            <div style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>GenomeIndia Context</div>
          </div>
          
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Polygenic Score</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: 'var(--neon-purple)' }}>PGS000116</div>
            </div>
            <div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Variant Count</div>
              <div style={{ fontSize: '1.1rem', fontWeight: 'bold' }}>40,079</div>
            </div>
          </div>

          <div style={{ background: 'rgba(0,0,0,0.3)', padding: '1rem', borderRadius: '8px', borderLeft: '3px solid var(--neon-purple)' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Individual Genotype</div>
            <div style={{ fontSize: '0.9rem', fontWeight: 'bold' }}>UNAVAILABLE</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
              Population-level genetic context only. Not for clinical diagnosis.
            </div>
          </div>
        </motion.div>
      </div>

      <motion.div variants={cardVariants} style={{ textAlign: 'center', marginTop: '3rem' }}>
        <button style={{ 
          fontSize: '1.2rem', 
          padding: '1rem 3rem', 
          background: 'rgba(0, 243, 255, 0.1)',
          textTransform: 'uppercase',
          letterSpacing: '2px'
        }}>
          Lock Patient State
        </button>
      </motion.div>
    </motion.div>
  );
};

export default PatientProfile;
