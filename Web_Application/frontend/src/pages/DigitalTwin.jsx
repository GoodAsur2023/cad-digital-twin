import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Activity, TrendingDown, Target } from 'lucide-react';
import axios from 'axios';

const DigitalTwin = ({ patientData }) => {
  const [interventions, setInterventions] = useState(null);
  const [selectedTags, setSelectedTags] = useState([]);

  useEffect(() => {
    if (patientData) {
      axios.get(`http://127.0.0.1:8000/api/interventions/${patientData.patient_idx}`)
        .then(res => {
          if (res.data.interventions && res.data.interventions.length > 0) {
            setInterventions(res.data.interventions);
            // Default select the first atomic one
            const firstAtomic = res.data.interventions.find(i => i.scenario_id && i.scenario_id.match(/^S[1-4]_/));
            setSelectedTags(firstAtomic ? [firstAtomic.scenario_id] : [res.data.interventions[0].scenario_id]);
          } else {
            // Mock if backend doesn't have the explicit patient interventions
            const mockInt = [
              { intervention_type: 'Exercise', risk_reduction: 0.057, monotonic_flag: 1, post_risk: patientData.risk_state.current_risk - 0.057 },
              { intervention_type: 'Weight Loss', risk_reduction: 0.042, monotonic_flag: 1, post_risk: patientData.risk_state.current_risk - 0.042 },
              { intervention_type: 'Smoking Cessation', risk_reduction: 0.021, monotonic_flag: 1, post_risk: patientData.risk_state.current_risk - 0.021 },
              { intervention_type: 'Cholesterol Diet', risk_reduction: -0.005, monotonic_flag: 0, post_risk: patientData.risk_state.current_risk + 0.005 }
            ];
            setInterventions(mockInt);
            setSelectedTags(['Exercise']);
          }
        })
        .catch(err => console.error(err));
    }
  }, [patientData]);

  if (!patientData || !interventions) {
    return <div style={{ textAlign: 'center', padding: '4rem' }}><h2 className="text-neon-cyan">Loading Counterfactual Engine...</h2></div>;
  }

  const { risk_state } = patientData;
  const baseRisk = risk_state.current_risk * 100;

  // Base Atomic Interventions
  const DIGITAL_TWIN_BASE_TAGS = [
    { id: 'S1_BP_reduction', label: 'BP Medication' },
    { id: 'S2_exercise_hr_bp', label: 'Exercise Protocol' },
    { id: 'S3_weight_loss_proxy_BP_cholesterol', label: 'Weight Loss 5%' },
    { id: 'S4_cholesterol_reduction', label: 'Statin Therapy' },
    { id: 'Exercise', label: 'Exercise' },
    { id: 'Weight Loss', label: 'Weight Loss' },
    { id: 'Smoking Cessation', label: 'Smoking Cessation' },
    { id: 'Cholesterol Diet', label: 'Cholesterol Diet' }
  ];

  // Only show checkboxes for atomic interventions that exist in the payload
  const availableTags = DIGITAL_TWIN_BASE_TAGS.filter(tag => 
    interventions.some(i => i.scenario_id === tag.id || i.intervention_type === tag.id)
  );

  // Combinatorial Map
  const MULTI_MAP = {
    'S1_BP_reduction,S2_exercise_hr_bp,S4_cholesterol_reduction': 'S5_combined_exercise_BP_cholesterol'
  };

  const comboKey = [...selectedTags].sort().join(',');
  let targetScenarioId = null;
  let isUnsupportedCombo = false;

  if (selectedTags.length === 1) {
    targetScenarioId = selectedTags[0];
  } else if (selectedTags.length > 1) {
    targetScenarioId = MULTI_MAP[comboKey];
    if (!targetScenarioId) isUnsupportedCombo = true;
  }

  const activeIntervention = targetScenarioId 
    ? interventions.find(i => i.scenario_id === targetScenarioId || i.intervention_type === targetScenarioId) 
    : null;

  if (targetScenarioId && !activeIntervention) {
    isUnsupportedCombo = true;
  }

  const toggleTag = (tagId) => {
    setSelectedTags(prev => 
      prev.includes(tagId) ? prev.filter(t => t !== tagId) : [...prev, tagId]
    );
  };

  const getInterventionName = (intv) => {
    if (intv.intervention_type) return intv.intervention_type;
    return intv.scenario_id.replace(/^S\d+_/, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  const isExpected = (intv) => {
    if (intv.monotonic_flag !== undefined) return intv.monotonic_flag === 1;
    return intv.response_status === 'EXPECTED_DECREASE';
  };

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
  };

  return (
    <motion.div initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.1 } } }}>
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 className="text-neon-cyan">Counterfactual Engine</h1>
        <p style={{ color: 'var(--text-secondary)' }}>S_t → S_t' Intervention Simulator</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px 1fr', gap: '2rem', alignItems: 'flex-start' }}>
        
        {/* State T (Baseline) */}
        <motion.div className="glass-card" variants={cardVariants} style={{ minHeight: '300px', display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ textAlign: 'center', marginBottom: '2rem' }}>Patient State (S_t)</h2>
          <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '4rem', fontWeight: 'bold', color: 'rgba(255,255,255,0.5)', lineHeight: 1 }}>
                {baseRisk.toFixed(1)}%
              </div>
              <div style={{ color: 'var(--text-secondary)', marginTop: '1rem' }}>Baseline Estimated Risk</div>
            </div>
          </div>
        </motion.div>

        {/* Intervention Selector (Center) */}
        <motion.div variants={cardVariants} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ textAlign: 'center', color: 'var(--neon-cyan)', fontWeight: 'bold', marginBottom: '0.5rem' }}>Select Interventions (Multi-Select)</div>
          
          {availableTags.map(tag => {
            const isSelected = selectedTags.includes(tag.id);
            return (
              <div 
                key={tag.id}
                onClick={() => toggleTag(tag.id)}
                style={{
                  background: isSelected ? 'rgba(0, 243, 255, 0.1)' : 'var(--surface-color)',
                  border: `1px solid ${isSelected ? 'var(--neon-cyan)' : 'var(--border-color)'}`,
                  padding: '1rem',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  textAlign: 'center',
                  transition: 'all 0.2s ease',
                  backdropFilter: 'var(--glass-blur)'
                }}
              >
                <div style={{ fontWeight: 'bold', color: isSelected ? 'var(--neon-cyan)' : 'var(--text-primary)' }}>
                  {isSelected ? '✓ ' : ''}{tag.label}
                </div>
              </div>
            );
          })}
        </motion.div>

        {/* State T' (Counterfactual) */}
        <motion.div className="glass-card" variants={cardVariants} style={{ minHeight: '300px', display: 'flex', flexDirection: 'column', border: '1px solid rgba(0, 243, 255, 0.3)' }}>
          <h2 style={{ textAlign: 'center', marginBottom: '2rem', color: 'var(--neon-cyan)' }}>Counterfactual (S_t')</h2>
          
          {selectedTags.length === 0 ? (
            <div style={{ textAlign: 'center', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
              Select an intervention to compute counterfactual risk.
            </div>
          ) : isUnsupportedCombo ? (
            <div style={{ textAlign: 'center', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--neon-red)', padding: '1rem', background: 'rgba(255,0,0,0.1)', borderRadius: '8px' }}>
              <div>
                <strong>Unsupported Combination</strong><br/><br/>
                This specific multi-intervention combination was not pre-computed by the ML pipeline.
              </div>
            </div>
          ) : activeIntervention ? (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1, flexDirection: 'column' }}>
              <div style={{ textAlign: 'center' }}>
                <motion.div 
                  key={activeIntervention.scenario_id || activeIntervention.intervention_type} 
                  initial={{ scale: 0.8, opacity: 0 }} 
                  animate={{ scale: 1, opacity: 1 }} 
                  style={{ fontSize: '4rem', fontWeight: 'bold', color: 'var(--neon-cyan)', lineHeight: 1 }}
                >
                  {((activeIntervention.new_risk !== undefined ? activeIntervention.new_risk : activeIntervention.post_risk) * 100).toFixed(1)}%
                </motion.div>
                <div style={{ color: 'var(--text-secondary)', marginTop: '1rem' }}>Simulated Risk ({getInterventionName(activeIntervention)})</div>
                
                {!isExpected(activeIntervention) && (
                  <div style={{ color: 'var(--neon-red)', fontSize: '0.8rem', marginTop: '0.5rem' }}>Model Non-Monotonic</div>
                )}
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '2rem', background: 'rgba(0, 255, 102, 0.1)', padding: '0.5rem 1rem', borderRadius: '20px' }}>
                <TrendingDown color="var(--neon-green)" size={20} />
                <div style={{ color: 'var(--neon-green)', fontWeight: 'bold' }}>
                  {((activeIntervention.delta_risk !== undefined ? activeIntervention.delta_risk : -activeIntervention.risk_reduction) * 100) > 0 ? '-' : '+'}
                  {Math.abs((activeIntervention.delta_risk !== undefined ? activeIntervention.delta_risk : -activeIntervention.risk_reduction) * 100).toFixed(1)} pp
                </div>
              </div>
            </div>
          ) : null}
        </motion.div>
      </div>
      
      <motion.div variants={cardVariants} style={{ textAlign: 'center', marginTop: '3rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
        <Target size={16} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '0.5rem' }}/>
        Model-based counterfactual simulation — not a causal treatment effect.
      </motion.div>
    </motion.div>
  );
};

export default DigitalTwin;
