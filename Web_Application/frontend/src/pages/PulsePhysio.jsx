import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ResponsiveRadar } from '@nivo/radar';
import { Heart, Activity, AlertTriangle } from 'lucide-react';
import axios from 'axios';

const PulsePhysio = ({ patientData }) => {
  const [pulseScenarios, setPulseScenarios] = useState(null);
  const [selectedTags, setSelectedTags] = useState([]);

  useEffect(() => {
    if (patientData) {
      axios.get(`http://127.0.0.1:8000/api/pulse/${patientData.patient_idx}`)
        .then(res => {
          if (res.data.pulse_data && res.data.pulse_data.length > 0) {
            setPulseScenarios(res.data.pulse_data);
            setSelectedTags([res.data.pulse_data[0].scenario]);
          } else {
            // Patient doesn't have pulse data (likely from Lifestyle cohort)
            setPulseScenarios([]);
            setSelectedTags([]);
          }
        })
        .catch(err => console.error(err));
    }
  }, [patientData]);

  const PULSE_BASE_TAGS = [
    { id: 'exercise_aerobic', label: 'Exercise Aerobic' },
    { id: 'weight_loss_5pct', label: 'Weight Loss 5%' },
    { id: 'smoking_cessation', label: 'Smoking Cessation' }
  ];

  const MULTI_MAP = {
    'exercise_aerobic,weight_loss_5pct': 'combined_exercise_diet'
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

  const selectedScenario = pulseScenarios && targetScenarioId
    ? pulseScenarios.find(p => p.scenario === targetScenarioId || p.scenario_id === targetScenarioId)
    : null;

  if (targetScenarioId && !selectedScenario) {
    isUnsupportedCombo = true;
  }

  const toggleTag = (tagId) => {
    setSelectedTags(prev => 
      prev.includes(tagId) ? prev.filter(t => t !== tagId) : [...prev, tagId]
    );
  };

  if (!patientData || pulseScenarios === null) {
    return <div style={{ textAlign: 'center', padding: '4rem' }}><h2 className="text-neon-cyan">Processing Physiology Engine...</h2></div>;
  }

  // If no data is available for this patient (e.g. Lifestyle cohort)
  if (pulseScenarios.length === 0) {
    return (
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ textAlign: 'center', padding: '4rem' }}>
        <AlertTriangle size={64} color="var(--neon-purple)" style={{ marginBottom: '1rem' }} />
        <h2 style={{ color: 'var(--text-primary)' }}>Hemodynamic Data Unavailable</h2>
        <p style={{ color: 'var(--text-secondary)', maxWidth: '600px', margin: '0 auto', lineHeight: 1.6 }}>
          The Kitware Pulse Physiology Engine requires deep clinical telemetry (e.g., continuous blood pressure, heart rate) which is not available in the broad Lifestyle screening cohort.
          <br /><br />
          To run dynamic hemodynamic counterfactual simulations, please switch to a patient from the Clinical cohort (e.g., Patient ID <strong>126</strong>, <strong>73</strong>, or <strong>145</strong>).
        </p>
      </motion.div>
    );
  }

  const pulseData = selectedScenario;
  
  // Safe numeric conversion functions
  const safeNum = (val, fallback) => {
    const num = Number(val);
    return isNaN(num) ? fallback : num;
  };

  const SBP_base = safeNum(pulseData?.sbp_baseline, 135);
  const SBP_post = safeNum(pulseData?.sbp_simulated, 125);
  const DBP_base = safeNum(pulseData?.dbp_baseline, 85);
  const DBP_post = safeNum(pulseData?.dbp_simulated, 80);
  
  // Workload (Double Product)
  const Workload_base = safeNum(pulseData?.double_product_baseline, 10125);
  const Workload_post = safeNum(pulseData?.double_product_simulated, 8500);
  
  // HR (Derived from patient features or default 75, plus max_hr_delta)
  const rawMaxHr = patientData?.feature_state?.max_heart_rate;
  const HR_base = (rawMaxHr && !isNaN(Number(rawMaxHr))) ? Math.round(Number(rawMaxHr) * 0.6) : 75;
  const HR_post = HR_base + safeNum(pulseData?.max_hr_delta, 0);

  // SVR (Derived from default 1100 and pct_change)
  const SVR_base = 1100;
  const SVR_post = pulseData?.svr_pct_change !== undefined ? Math.round(SVR_base * (1 + (safeNum(pulseData?.svr_pct_change, 0) / 100))) : 1050;

  // Normalize data for the Radar chart
  const radarData = [
    { metric: 'HR', Baseline: Math.max(0, HR_base), Counterfactual: Math.max(0, HR_post) },
    { metric: 'SBP', Baseline: Math.max(0, SBP_base), Counterfactual: Math.max(0, SBP_post) },
    { metric: 'DBP', Baseline: Math.max(0, DBP_base), Counterfactual: Math.max(0, DBP_post) },
    { metric: 'SVR', Baseline: Math.max(0, SVR_base / 10), Counterfactual: Math.max(0, SVR_post / 10) }, 
    { metric: 'Workload', Baseline: Math.max(0, Workload_base / 100), Counterfactual: Math.max(0, Workload_post / 100) } 
  ];

  // Heart beat animation speed based on HR (safeguard against Infinity/NaN)
  let beatDuration = 60 / (HR_post || 70); 
  if (isNaN(beatDuration) || beatDuration < 0.2 || beatDuration > 5) beatDuration = 0.8;

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
  };

  const getScenarioName = (id) => {
    if (!id) return "Simulation";
    return id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  };

  return (
    <motion.div initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.1 } } }}>
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 className="text-neon-cyan">PulsePhysio Cardiovascular Engine</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Dynamic hemodynamic simulation (Baseline vs Counterfactual)</p>
      </div>

      {/* Intervention Selector */}
      <motion.div variants={cardVariants} style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '2rem' }}>
        <div style={{ width: '100%', textAlign: 'center', color: 'var(--neon-cyan)', fontWeight: 'bold', marginBottom: '0.5rem' }}>Select Interventions (Multi-Select)</div>
        {PULSE_BASE_TAGS.map(tag => {
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

      {selectedTags.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--text-secondary)' }}>
          Select an intervention to run the simulation.
        </div>
      ) : isUnsupportedCombo ? (
        <div style={{ textAlign: 'center', padding: '4rem', color: 'var(--neon-red)', background: 'rgba(255,0,0,0.1)', borderRadius: '8px', margin: '0 auto', maxWidth: '600px' }}>
          <strong>Unsupported Combination</strong><br/><br/>
          This specific multi-intervention combination was not pre-computed by the Physics Engine.
        </div>
      ) : pulseData ? (
        <>
          {/* Mechanism of Action Explanation Panel */}
          <motion.div className="glass-card" variants={cardVariants} style={{ marginBottom: '2rem', padding: '1.5rem', borderLeft: '4px solid var(--neon-purple)', background: 'linear-gradient(90deg, rgba(176, 38, 255, 0.1) 0%, transparent 100%)' }}>
            <h3 style={{ color: 'var(--neon-purple)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Activity size={20} /> Mechanism of Action
            </h3>
            <p style={{ color: 'var(--text-primary)', fontSize: '1.1rem', lineHeight: 1.6, marginBottom: '1rem' }}>
              {pulseData.mechanism || "Targeted physiological adaptation."}
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '2rem', fontSize: '0.9rem', color: 'var(--text-secondary)', padding: '1rem', background: 'rgba(0,0,0,0.2)', borderRadius: '8px' }}>
              <div style={{ flex: 1, minWidth: '250px' }}>
                <span style={{ color: 'var(--neon-cyan)' }}>Simulated Pathway:</span><br/>
                {pulseData.source || "Pulse Engine Framework"}
              </div>
              <div style={{ flex: 1, minWidth: '250px' }}>
                <span style={{ color: 'var(--neon-green)' }}>Clinical Translation:</span><br/>
                This intervention reduces the double product (cardiac workload) by <strong>{Math.abs(pulseData.double_product_pct_reduction || 0)}%</strong>, mechanically lowering myocardial oxygen demand and shear stress on coronary endothelium—which directly correlates with the machine learning model's predicted drop in CAD risk.
              </div>
            </div>
          </motion.div>

          <div className="grid-3" style={{ marginBottom: '2rem' }}>
        
        {/* Animated Heart Engine */}
        <motion.div className="glass-card" variants={cardVariants} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '350px' }}>
          <h2 style={{ marginBottom: '2rem', color: 'var(--neon-red)' }}>Physiological State</h2>
          
          <motion.div 
            animate={{ scale: [1, 1.2, 1] }} 
            transition={{ repeat: Infinity, duration: beatDuration, ease: "easeInOut" }}
            style={{ 
              background: 'radial-gradient(circle, rgba(255,0,60,0.2) 0%, transparent 70%)',
              padding: '3rem',
              borderRadius: '50%'
            }}
          >
            <Heart size={80} color="var(--neon-red)" fill="var(--neon-red)" />
          </motion.div>
          
          <div style={{ marginTop: '2rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{HR_post.toFixed(1)} <span style={{fontSize: '1rem', color: 'var(--text-secondary)'}}>BPM</span></div>
            <div style={{ fontSize: '0.9rem', color: 'var(--neon-cyan)' }}>Simulated Post-Intervention Heart Rate</div>
          </div>
        </motion.div>

        {/* Nivo Radar Chart */}
        <motion.div className="glass-card" variants={cardVariants} style={{ gridColumn: 'span 2', height: '350px' }}>
          <h2 style={{ marginBottom: '1rem', textAlign: 'center' }}>Hemodynamic Radar Profile</h2>
          <ResponsiveRadar
            data={radarData}
            keys={['Baseline', 'Counterfactual']}
            indexBy="metric"
            valueFormat=">-.2f"
            margin={{ top: 40, right: 80, bottom: 40, left: 80 }}
            borderColor={{ from: 'color' }}
            gridLabelOffset={20}
            dotSize={8}
            dotColor={{ theme: 'background' }}
            dotBorderWidth={2}
            colors={['rgba(255, 255, 255, 0.4)', 'var(--neon-cyan)']}
            blendMode="screen"
            motionConfig="wobbly"
            theme={{
              axis: { ticks: { text: { fill: 'var(--text-primary)' } } },
              grid: { line: { stroke: 'rgba(255,255,255,0.1)' } },
              dots: { text: { fill: 'var(--text-primary)' } }
            }}
            legends={[
              {
                anchor: 'top-left',
                direction: 'column',
                translateX: -50,
                translateY: -20,
                itemWidth: 80,
                itemHeight: 20,
                itemTextColor: 'var(--text-secondary)',
                symbolSize: 12,
                symbolShape: 'circle',
                effects: [
                  {
                    on: 'hover',
                    style: { itemTextColor: 'var(--neon-cyan)' }
                  }
                ]
              }
            ]}
          />
        </motion.div>
      </div>

      {/* Hemodynamic Gauges List */}
      <motion.div className="grid-3" variants={cardVariants}>
        {[
          { label: 'Systolic BP', base: SBP_base, post: SBP_post, unit: 'mmHg' },
          { label: 'Diastolic BP', base: DBP_base, post: DBP_post, unit: 'mmHg' },
          { label: 'Vascular Resistance', base: SVR_base, post: SVR_post, unit: 'dyn.s/cm5' }
        ].map((item, idx) => {
          const delta = item.post - item.base;
          const isImprovement = delta <= 0;
          return (
            <div key={idx} className="glass-card" style={{ textAlign: 'center' }}>
              <div style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>{item.label}</div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '1rem' }}>
                <div style={{ fontSize: '1.2rem', color: 'rgba(255,255,255,0.5)' }}>{item.base.toFixed(1)}</div>
                <Activity size={16} color="var(--neon-purple)" />
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>{item.post.toFixed(1)}</div>
              </div>
              <div style={{ marginTop: '0.5rem', fontSize: '0.9rem', color: isImprovement ? 'var(--neon-green)' : 'var(--neon-red)' }}>
                {delta > 0 ? '+' : ''}{delta.toFixed(1)} {item.unit}
              </div>
            </div>
          );
        })}
      </motion.div>
        </>
      ) : null}
    </motion.div>
  );
};

export default PulsePhysio;
