import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ResponsiveBar } from '@nivo/bar';
import { ShieldAlert, Fingerprint } from 'lucide-react';
import axios from 'axios';

const Explainability = ({ patientData }) => {
  const [shapData, setShapData] = useState(null);
  useEffect(() => {
    if (patientData) {
      setShapData(null);
      axios.get(`http://127.0.0.1:8000/api/explainability/shap/${patientData.patient_idx}?model_type=${patientData.cohort}`)
        .then(res => setShapData(res.data))
        .catch(console.error);
    }
  }, [patientData]);

  if (!patientData || !shapData) {
    return <div style={{ textAlign: 'center', padding: '4rem' }}><h2 className="text-neon-cyan">Loading SHAP Explainer Engine...</h2></div>;
  }

  // Format data for Nivo Bar (acting as a Waterfall chart)
  const barData = shapData.attributions.slice(0, 10).map(attr => ({
    feature: attr.feature,
    value: attr.shap_value,
    color: attr.shap_value > 0 ? 'var(--neon-red)' : 'var(--neon-green)' // Red for risk increase, Green for decrease
  })).reverse(); // Reverse for bottom-up horizontal bar

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
  };

  return (
    <motion.div initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.1 } } }}>
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 className="text-neon-cyan">Model Explainability (SHAP)</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Canonical Clinical Model Feature Attributions
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '2rem' }}>
        
        {/* SHAP Waterfall Chart (Nivo Bar) */}
        <motion.div className="glass-card" variants={cardVariants} style={{ height: '550px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2>Local Feature Importance</h2>
            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Source: {patientData.cohort.toUpperCase()} Cohort
            </div>
          </div>
          
          <div style={{ flex: 1 }}>
            <ResponsiveBar
              data={barData}
            keys={['value']}
            indexBy="feature"
            margin={{ top: 10, right: 30, bottom: 50, left: 150 }}
            padding={0.3}
            layout="horizontal"
            colors={({ data }) => data.color}
            axisBottom={{
              tickSize: 5,
              tickPadding: 5,
              tickRotation: 0,
              legend: 'SHAP Value (Impact on Model Output)',
              legendPosition: 'middle',
              legendOffset: 32
            }}
            theme={{
              axis: { ticks: { text: { fill: 'var(--text-secondary)' } }, legend: { text: { fill: 'var(--text-secondary)' } } },
              grid: { line: { stroke: 'rgba(255,255,255,0.05)' } }
            }}
            tooltip={({ id, value, color, data }) => (
              <div style={{ padding: '12px', background: 'var(--surface-color)', border: '1px solid var(--border-color)', borderRadius: '8px' }}>
                <strong style={{ color: 'var(--text-primary)' }}>{data.feature}</strong><br />
                <span style={{ color: value > 0 ? 'var(--neon-red)' : 'var(--neon-green)' }}>
                  Impact: {value > 0 ? '+' : ''}{value.toFixed(3)}
                </span>
              </div>
            )}
            enableGridY={false}
            enableGridX={true}
            enableLabel={false}
          />
          </div>
        </motion.div>

        {/* Genetic Context Strict Separation Box */}
        <motion.div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          <motion.div className="glass-card" variants={cardVariants} style={{ border: '1px solid rgba(188, 19, 254, 0.4)', textAlign: 'center' }}>
            <Fingerprint color="var(--neon-purple)" size={40} style={{ margin: '0 auto 1rem auto' }} />
            <h3 style={{ color: 'var(--neon-purple)', marginBottom: '0.5rem' }}>Population Genetic Context</h3>
            <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Genetic Intelligence is maintained separately from clinical feature attributions to prevent deterministic interpretation of polygenic liability.
            </div>
            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '4px', fontSize: '0.8rem' }}>
              <strong>Genetic SHAP Percentage:</strong> <em>Suppressed by Rule</em>
            </div>
          </motion.div>

          <motion.div className="glass-card" variants={cardVariants} style={{ background: 'rgba(255, 0, 60, 0.05)', border: '1px solid rgba(255, 0, 60, 0.2)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <ShieldAlert color="var(--neon-red)" size={20} />
              <div style={{ fontWeight: 'bold', color: 'var(--neon-red)' }}>Interpretation Warning</div>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
              SHAP values represent the feature's additive contribution to the model's prediction for this specific patient in log-odds space. They are not causal effect sizes.
            </div>
          </motion.div>

        </motion.div>

      </div>
    </motion.div>
  );
};

export default Explainability;
