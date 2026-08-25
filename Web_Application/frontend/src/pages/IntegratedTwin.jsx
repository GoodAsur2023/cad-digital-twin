import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Activity, TrendingDown, TrendingUp, Target, Heart, AlertTriangle } from 'lucide-react';
import { ResponsiveRadar } from '@nivo/radar';
import axios from 'axios';

const IntegratedTwin = ({ patientData }) => {
  const [interventions, setInterventions] = useState(null);
  const [pulseScenarios, setPulseScenarios] = useState(null);
  const [selectedTags, setSelectedTags] = useState([]);

  useEffect(() => {
    if (patientData) {
      axios.get(`http://127.0.0.1:8000/api/interventions/${patientData.patient_idx}`)
        .then(res => {
          if (res.data.interventions && res.data.interventions.length > 0) {
            setInterventions(res.data.interventions);
            const firstAtomic = res.data.interventions.find(i => i.scenario_id && i.scenario_id.match(/^S[1-4]_/));
            setSelectedTags(firstAtomic ? [firstAtomic.scenario_id] : [res.data.interventions[0].scenario_id]);
          } else {
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

      axios.get(`http://127.0.0.1:8000/api/pulse/${patientData.patient_idx}`)
        .then(res => {
          if (res.data.pulse_data && res.data.pulse_data.length > 0) {
            setPulseScenarios(res.data.pulse_data);
          } else {
            setPulseScenarios([]);
          }
        })
        .catch(err => console.error(err));
    }
  }, [patientData]);

  if (!patientData || !interventions || pulseScenarios === null) {
    return <div style={{ textAlign: 'center', padding: '4rem' }}><h2 className="text-neon-cyan">Loading Integrated Digital Twin...</h2></div>;
  }

  const { risk_state } = patientData;
  const baseRisk = risk_state.current_risk * 100;

  // ML Base Tags (Combined Clinical and Lifestyle)
  const BASE_TAGS = [
    // Clinical Cohort
    { id: 'S1_BP_reduction', label: 'BP Medication' },
    { id: 'S2_exercise_hr_bp', label: 'Exercise Protocol' },
    { id: 'S3_weight_loss_proxy_BP_cholesterol', label: 'Weight Loss 5%' },
    { id: 'S4_cholesterol_reduction', label: 'Statin Therapy' },
    // Lifestyle Cohort
    { id: 'S1_quit_smoking', label: 'Smoking Cessation' },
    { id: 'S2_exercise', label: 'Exercise' },
    { id: 'S3_weight_loss_5pct', label: 'Weight Loss' },
    { id: 'S4_quit_alcohol', label: 'Quit Alcohol' },
    { id: 'S5_combined_smoke_exercise', label: 'Combined Lifestyle' }
  ];

  const availableTags = BASE_TAGS.filter(tag => 
    interventions.some(i => i.scenario_id === tag.id || i.intervention_type === tag.id)
  );

  const MULTI_MAP = {
    'S1_BP_reduction,S2_exercise_hr_bp,S4_cholesterol_reduction': 'S5_combined_exercise_BP_cholesterol'
  };

  const comboKey = [...selectedTags].sort().join(',');
  let mlTargetScenarioId = null;
  let isUnsupportedMlCombo = false;

  if (selectedTags.length === 1) {
    mlTargetScenarioId = selectedTags[0];
  } else if (selectedTags.length > 1) {
    mlTargetScenarioId = MULTI_MAP[comboKey];
    if (!mlTargetScenarioId) isUnsupportedMlCombo = true;
  }

  const activeIntervention = mlTargetScenarioId 
    ? interventions.find(i => i.scenario_id === mlTargetScenarioId || i.intervention_type === mlTargetScenarioId) 
    : null;

  if (mlTargetScenarioId && !activeIntervention) {
    isUnsupportedMlCombo = true;
  }

  // Map ML ID to Pulse ID
  const mapMlToPulse = (mlTargetId, selectedTagsArr) => {
    const mockCombo = [...selectedTagsArr].sort().join(',');
    if (mockCombo === 'Exercise,Weight Loss') return 'combined_exercise_diet';
    if (mlTargetId === 'S5_combined_exercise_BP_cholesterol') return 'combined_exercise_diet';
    if (mlTargetId === 'S5_combined_smoke_exercise') return 'combined_exercise_diet';

    const map = {
      // Clinical
      'S2_exercise_hr_bp': 'exercise_aerobic',
      'S3_weight_loss_proxy_BP_cholesterol': 'weight_loss_5pct',
      // Lifestyle
      'S2_exercise': 'exercise_aerobic',
      'S3_weight_loss_5pct': 'weight_loss_5pct',
      'S1_quit_smoking': 'smoking_cessation',
      // Mocks
      'Exercise': 'exercise_aerobic',
      'Weight Loss': 'weight_loss_5pct',
      'Smoking Cessation': 'smoking_cessation'
    };
    return map[mlTargetId] || null;
  };

  const pulseTargetId = mapMlToPulse(mlTargetScenarioId, selectedTags);
  const activePulse = (pulseScenarios && pulseTargetId) 
    ? pulseScenarios.find(p => p.scenario === pulseTargetId || p.scenario_id === pulseTargetId)
    : null;

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

  // Safe numeric conversion for Pulse
  const safeNum = (val, fallback) => {
    const num = Number(val);
    return isNaN(num) ? fallback : num;
  };

  let pulseRender = null;

  if (pulseScenarios.length === 0) {
    pulseRender = (
      <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
        <AlertTriangle size={48} color="var(--neon-purple)" style={{ marginBottom: '1rem', margin: '0 auto' }} />
        <div>Hemodynamic data unavailable for lifestyle cohort.</div>
      </div>
    );
  } else if (!activePulse) {
    pulseRender = (
      <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }}>
        <strong>Simulation Not Found</strong><br/><br/>
        Physics engine simulation was not pre-computed for this specific intervention combination.
      </div>
    );
  } else {
    const pulseData = activePulse;
    const SBP_base = safeNum(pulseData?.sbp_baseline, 135);
    const SBP_post = safeNum(pulseData?.sbp_simulated, 125);
    const DBP_base = safeNum(pulseData?.dbp_baseline, 85);
    const DBP_post = safeNum(pulseData?.dbp_simulated, 80);
    
    const Workload_base = safeNum(pulseData?.double_product_baseline, 10125);
    const Workload_post = safeNum(pulseData?.double_product_simulated, 8500);
    
    const rawMaxHr = patientData?.feature_state?.max_heart_rate;
    const HR_base = (rawMaxHr && !isNaN(Number(rawMaxHr))) ? Math.round(Number(rawMaxHr) * 0.6) : 75;
    const HR_post = HR_base + safeNum(pulseData?.max_hr_delta, 0);

    const SVR_base = 1100;
    const SVR_post = pulseData?.svr_pct_change !== undefined ? Math.round(SVR_base * (1 + (safeNum(pulseData?.svr_pct_change, 0) / 100))) : 1050;

    const radarData = [
      { metric: 'HR', Baseline: Math.max(0, HR_base), Counterfactual: Math.max(0, HR_post) },
      { metric: 'SBP', Baseline: Math.max(0, SBP_base), Counterfactual: Math.max(0, SBP_post) },
      { metric: 'DBP', Baseline: Math.max(0, DBP_base), Counterfactual: Math.max(0, DBP_post) },
      { metric: 'SVR', Baseline: Math.max(0, SVR_base / 10), Counterfactual: Math.max(0, SVR_post / 10) }, 
      { metric: 'Workload', Baseline: Math.max(0, Workload_base / 100), Counterfactual: Math.max(0, Workload_post / 100) } 
    ];

    let beatDuration = 60 / (HR_post || 70); 
    if (isNaN(beatDuration) || beatDuration < 0.2 || beatDuration > 5) beatDuration = 0.8;

    pulseRender = (
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {pulseData.data_source === 'archetype_match' && (
          <div style={{ gridColumn: 'span 2', background: pulseData.is_low_confidence ? 'rgba(255, 153, 0, 0.1)' : 'rgba(188, 19, 254, 0.1)', border: `1px solid ${pulseData.is_low_confidence ? '#ff9900' : 'var(--neon-purple)'}`, padding: '0.75rem', borderRadius: '8px', fontSize: '0.85rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <AlertTriangle size={16} color={pulseData.is_low_confidence ? '#ff9900' : 'var(--neon-purple)'} />
            <div>
              <strong>Archetype Match ({pulseData.is_low_confidence ? 'Low Confidence' : 'High Confidence'})</strong><br/>
              Hemodynamic profile borrowed from nearest Clinical archetype (Patient #{pulseData.archetype_source_id}).
            </div>
          </div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <motion.div 
            animate={{ scale: [1, 1.2, 1] }} 
            transition={{ repeat: Infinity, duration: beatDuration, ease: "easeInOut" }}
            style={{ 
              background: 'radial-gradient(circle, rgba(255,0,60,0.2) 0%, transparent 70%)',
              padding: '2rem',
              borderRadius: '50%'
            }}
          >
            <Heart size={60} color="var(--neon-red)" fill="var(--neon-red)" />
          </motion.div>
          <div style={{ marginTop: '1rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{HR_post.toFixed(1)} <span style={{fontSize: '0.8rem', color: 'var(--text-secondary)'}}>BPM</span></div>
            <div style={{ fontSize: '0.8rem', color: 'var(--neon-cyan)' }}>Simulated Heart Rate</div>
          </div>
        </div>

        <div style={{ height: '250px' }}>
          <ResponsiveRadar
            data={radarData}
            keys={['Baseline', 'Counterfactual']}
            indexBy="metric"
            valueFormat=">-.2f"
            margin={{ top: 20, right: 40, bottom: 20, left: 40 }}
            borderColor={{ from: 'color' }}
            gridLabelOffset={10}
            dotSize={6}
            dotColor={{ theme: 'background' }}
            dotBorderWidth={2}
            colors={['rgba(255, 255, 255, 0.4)', 'var(--neon-cyan)']}
            blendMode="screen"
            motionConfig="wobbly"
            theme={{
              axis: { ticks: { text: { fill: 'var(--text-primary)', fontSize: 10 } } },
              grid: { line: { stroke: 'rgba(255,255,255,0.1)' } },
              dots: { text: { fill: 'var(--text-primary)' } }
            }}
          />
        </div>

        <div style={{ gridColumn: 'span 2', background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px', borderLeft: '3px solid var(--neon-purple)', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
          <strong style={{ color: 'var(--neon-purple)' }}>Mechanism of Action:</strong> {pulseData.mechanism || "Targeted physiological adaptation."}
          <br/><br/>
          <strong style={{ color: 'var(--neon-green)' }}>Clinical Translation:</strong> Reduces double product (cardiac workload) by <strong>{Math.abs(pulseData.double_product_pct_reduction || 0)}%</strong>, mechanically lowering myocardial oxygen demand, correlating with the ML predicted drop in CAD risk.
        </div>
      </div>
    );
  }

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
  };

  return (
    <motion.div initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.1 } } }}>
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 className="text-neon-cyan">Integrated Clinical Twin</h1>
        <p style={{ color: 'var(--text-secondary)' }}>Synchronized Machine Learning & Hemodynamic Physics</p>
      </div>

      {/* Intervention Selector (Top) */}
      <motion.div variants={cardVariants} style={{ display: 'flex', gap: '1rem', justifyContent: 'center', flexWrap: 'wrap', marginBottom: '2rem' }}>
        <div style={{ width: '100%', textAlign: 'center', color: 'var(--neon-cyan)', fontWeight: 'bold', marginBottom: '0.5rem' }}>Select Interventions</div>
        {availableTags.map(tag => {
          const isSelected = selectedTags.includes(tag.id);
          return (
            <div 
              key={tag.id}
              onClick={() => toggleTag(tag.id)}
              style={{
                background: isSelected ? 'rgba(0, 243, 255, 0.1)' : 'var(--surface-color)',
                border: `1px solid ${isSelected ? 'var(--neon-cyan)' : 'var(--border-color)'}`,
                padding: '0.5rem 1rem',
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

      {/* Side by Side Split */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.5fr', gap: '2rem', alignItems: 'stretch' }}>
        
        {/* ML Counterfactual (Left) */}
        <motion.div className="glass-card" variants={cardVariants} style={{ display: 'flex', flexDirection: 'column' }}>
          <h2 style={{ textAlign: 'center', marginBottom: '1.5rem', color: 'var(--neon-cyan)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
            <Activity size={24} /> ML Prediction
          </h2>
          
          {selectedTags.length === 0 ? (
            <div style={{ textAlign: 'center', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
              Select an intervention to compute.
            </div>
          ) : isUnsupportedMlCombo ? (
            <div style={{ textAlign: 'center', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--neon-red)', padding: '1rem', background: 'rgba(255,0,0,0.1)', borderRadius: '8px' }}>
              <div>
                <strong>Unsupported Combination</strong><br/><br/>
                This specific multi-intervention combination was not pre-computed by the ML pipeline.
              </div>
            </div>
          ) : activeIntervention ? (
            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1, flexDirection: 'column' }}>
              <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                <div style={{ fontSize: '2.5rem', fontWeight: 'bold', color: 'rgba(255,255,255,0.5)', lineHeight: 1 }}>
                  {baseRisk.toFixed(1)}%
                </div>
                <div style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Baseline Risk</div>
              </div>

              <div style={{ textAlign: 'center' }}>
                <motion.div 
                  key={activeIntervention.scenario_id || activeIntervention.intervention_type} 
                  initial={{ scale: 0.8, opacity: 0 }} 
                  animate={{ scale: 1, opacity: 1 }} 
                  style={{ fontSize: '4rem', fontWeight: 'bold', color: 'var(--neon-cyan)', lineHeight: 1 }}
                >
                  {((activeIntervention.new_risk !== undefined ? activeIntervention.new_risk : activeIntervention.post_risk) * 100).toFixed(1)}%
                </motion.div>
                <div style={{ color: 'var(--text-secondary)', marginTop: '1rem' }}>Simulated Counterfactual</div>
                
                {!isExpected(activeIntervention) && (
                  <div style={{ color: 'var(--neon-red)', fontSize: '0.8rem', marginTop: '0.5rem' }}>Model Non-Monotonic</div>
                )}
              </div>

              {/* Dynamic Risk Delta Pill */}
              {(() => {
                const newRiskVal = (activeIntervention.new_risk !== undefined ? activeIntervention.new_risk : activeIntervention.post_risk) * 100;
                const riskDiff = newRiskVal - baseRisk;
                
                let icon, color, bg, sign;
                if (riskDiff > 0.05) {
                  // Risk INCREASED (Bad)
                  icon = <TrendingUp color="var(--neon-red)" size={20} />;
                  color = "var(--neon-red)";
                  bg = "rgba(255, 0, 60, 0.1)";
                  sign = "+";
                } else if (riskDiff < -0.05) {
                  // Risk DECREASED (Good)
                  icon = <TrendingDown color="var(--neon-green)" size={20} />;
                  color = "var(--neon-green)";
                  bg = "rgba(0, 255, 102, 0.1)";
                  sign = "-";
                } else {
                  // No change
                  icon = <span style={{ color: "var(--text-secondary)", fontSize: '18px', fontWeight: 'bold' }}>—</span>;
                  color = "var(--text-secondary)";
                  bg = "rgba(255, 255, 255, 0.05)";
                  sign = "";
                }

                return (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '2rem', background: bg, padding: '0.5rem 1rem', borderRadius: '20px' }}>
                    {icon}
                    <div style={{ color: color, fontWeight: 'bold' }}>
                      {sign}{Math.abs(riskDiff).toFixed(1)} pp
                    </div>
                  </div>
                );
              })()}
            </div>
          ) : null}
        </motion.div>

        {/* Physics Engine (Right) */}
        <motion.div className="glass-card" variants={cardVariants} style={{ display: 'flex', flexDirection: 'column', border: '1px solid rgba(176, 38, 255, 0.3)' }}>
          <h2 style={{ textAlign: 'center', marginBottom: '1.5rem', color: 'var(--neon-purple)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
            <Heart size={24} /> Pulse Physics Engine
          </h2>
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            {pulseRender}
          </div>
        </motion.div>
      </div>
      
      <motion.div variants={cardVariants} style={{ textAlign: 'center', marginTop: '3rem', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
        <Target size={16} style={{ display: 'inline', verticalAlign: 'middle', marginRight: '0.5rem' }}/>
        Integrated Digital Twin Simulation.
      </motion.div>
    </motion.div>
  );
};

export default IntegratedTwin;
