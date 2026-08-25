import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { FilePlus, HeartPulse, Activity } from 'lucide-react';

const ScreeningPortal = ({ setPatientId }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    age: 50,
    sex: 1, // 1=Male, 0=Female
    resting_bp: 120,
    cholesterol: 200,
    fasting_blood_sugar: 0, // 0=False, 1=True
    max_heart_rate: 150
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: Number(value) }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post('http://127.0.0.1:8000/api/screen', formData);
      const newId = response.data.patient_idx;
      setPatientId(newId);
      // Wait for React to fetch the new patient data in App.jsx
      setTimeout(() => {
        navigate('/dashboard');
      }, 500);
    } catch (err) {
      console.error(err);
      alert('Error screening patient. Make sure backend is running.');
      setLoading(false);
    }
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
  };

  return (
    <motion.div initial="hidden" animate="visible" variants={cardVariants} style={{ maxWidth: '800px', margin: '0 auto', padding: '2rem 0' }}>
      <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 className="text-neon-cyan" style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>Real-Time Clinical Screening</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Enter patient vitals to generate a live Digital Twin and CAD risk assessment.</p>
      </div>

      <motion.form onSubmit={handleSubmit} className="glass-card" style={{ border: '1px solid rgba(0, 243, 255, 0.3)', padding: '2.5rem' }}>
        
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
          
          {/* Age */}
          <div>
            <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Age (Years)</label>
            <input 
              type="number" name="age" value={formData.age} onChange={handleChange} required min="20" max="100"
              style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '4px', outline: 'none' }}
            />
          </div>

          {/* Sex */}
          <div>
            <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Sex</label>
            <select 
              name="sex" value={formData.sex} onChange={handleChange}
              style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '4px', outline: 'none', appearance: 'none' }}
            >
              <option value={1} style={{ background: '#111' }}>Male</option>
              <option value={0} style={{ background: '#111' }}>Female</option>
            </select>
          </div>

          {/* Resting BP */}
          <div>
            <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Resting Blood Pressure (mmHg)</label>
            <input 
              type="number" name="resting_bp" value={formData.resting_bp} onChange={handleChange} required min="80" max="250"
              style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '4px', outline: 'none' }}
            />
          </div>

          {/* Cholesterol */}
          <div>
            <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Total Cholesterol (mg/dL)</label>
            <input 
              type="number" name="cholesterol" value={formData.cholesterol} onChange={handleChange} required min="100" max="600"
              style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '4px', outline: 'none' }}
            />
          </div>

          {/* Max HR */}
          <div>
            <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Maximum Heart Rate Achieved</label>
            <input 
              type="number" name="max_heart_rate" value={formData.max_heart_rate} onChange={handleChange} required min="60" max="220"
              style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '4px', outline: 'none' }}
            />
          </div>

          {/* Fasting Blood Sugar */}
          <div>
            <label style={{ display: 'block', color: 'var(--text-secondary)', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Fasting Blood Sugar &gt; 120 mg/dl</label>
            <select 
              name="fasting_blood_sugar" value={formData.fasting_blood_sugar} onChange={handleChange}
              style={{ width: '100%', padding: '0.75rem', background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.1)', color: 'white', borderRadius: '4px', outline: 'none', appearance: 'none' }}
            >
              <option value={0} style={{ background: '#111' }}>False (Normal)</option>
              <option value={1} style={{ background: '#111' }}>True (Elevated)</option>
            </select>
          </div>

        </div>

        {/* Info Banner */}
        <div style={{ background: 'rgba(255, 255, 255, 0.05)', padding: '1rem', borderRadius: '8px', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '2rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <Activity color="var(--neon-cyan)" size={24} style={{ flexShrink: 0 }} />
          <div>
            <strong>Automated Imputation:</strong> Complex clinical indicators such as Resting ECG, Chest Pain Type, and ST Slope have been defaulted to baseline (Normal/Asymptomatic) for rapid screening. A full cardiological workup is required for diagnostic accuracy.
          </div>
        </div>

        <button 
          type="submit" 
          disabled={loading}
          style={{ 
            width: '100%', 
            padding: '1rem', 
            background: loading ? 'rgba(0, 243, 255, 0.1)' : 'var(--neon-cyan)', 
            color: loading ? 'var(--neon-cyan)' : '#000', 
            border: 'none', 
            borderRadius: '4px', 
            fontSize: '1.1rem', 
            fontWeight: 'bold', 
            cursor: loading ? 'not-allowed' : 'pointer',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '0.5rem',
            transition: 'all 0.2s ease'
          }}
        >
          {loading ? (
            <>Initializing Digital Twin...</>
          ) : (
            <>
              <FilePlus size={20} />
              Run Clinical Screening
            </>
          )}
        </button>

      </motion.form>
    </motion.div>
  );
};

export default ScreeningPortal;
