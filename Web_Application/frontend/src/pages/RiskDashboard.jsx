import React from 'react';
import { motion } from 'framer-motion';
import { ResponsiveBar } from '@nivo/bar';
import { AlertTriangle, Activity, CheckCircle, ShieldAlert } from 'lucide-react';

const RiskDashboard = ({ patientData }) => {
  if (!patientData) {
    return (
      <div style={{ textAlign: 'center', padding: '4rem' }}>
        <h2 className="text-neon-cyan">Loading Risk Data...</h2>
      </div>
    );
  }

  const { risk_state } = patientData;
  const currentRiskPct = (risk_state.current_risk * 100).toFixed(1);

  // Mocking the model breakdown for the visualization as requested in the baseline guide
  // (In a full implementation, these would come from a dedicated /api/risk endpoint)
  const mockLifestyleRisk = Math.max(0, risk_state.current_risk - 0.15);
  const mockBaselineClinical = Math.max(0, risk_state.current_risk - 0.05);
  const mockDiagnostic = Math.min(1, risk_state.current_risk + 0.02);

  const barData = [
    {
      model: 'Lifestyle',
      risk: parseFloat((mockLifestyleRisk * 100).toFixed(1)),
      min: parseFloat(((mockLifestyleRisk - 0.05) * 100).toFixed(1)),
      max: parseFloat(((mockLifestyleRisk + 0.05) * 100).toFixed(1))
    },
    {
      model: 'Baseline Clinical',
      risk: parseFloat((mockBaselineClinical * 100).toFixed(1)),
      min: parseFloat(((mockBaselineClinical - 0.04) * 100).toFixed(1)),
      max: parseFloat(((mockBaselineClinical + 0.04) * 100).toFixed(1))
    },
    {
      model: 'Diagnostic',
      risk: parseFloat((mockDiagnostic * 100).toFixed(1)),
      min: parseFloat(((mockDiagnostic - 0.03) * 100).toFixed(1)),
      max: parseFloat(((mockDiagnostic + 0.03) * 100).toFixed(1))
    },
    {
      model: 'Fusion (Final)',
      risk: parseFloat((risk_state.current_risk * 100).toFixed(1)),
      min: parseFloat((risk_state.risk_ci_lower * 100).toFixed(1)),
      max: parseFloat((risk_state.risk_ci_upper * 100).toFixed(1))
    }
  ];

  const cardVariants = {
    hidden: { opacity: 0, scale: 0.95 },
    visible: { opacity: 1, scale: 1, transition: { duration: 0.4 } }
  };

  return (
    <motion.div 
      initial="hidden" 
      animate="visible" 
      variants={{ visible: { transition: { staggerChildren: 0.1 } } }}
    >
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 className="text-neon-cyan">Risk Dashboard</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          Model-estimated risk across independent pathways.
        </p>
      </div>

      {/* Top Cards */}
      <div className="grid-3" style={{ marginBottom: '2rem' }}>
        <motion.div className="glass-card" variants={cardVariants} style={{ textAlign: 'center' }}>
          <div style={{ color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Final Digital Twin State</div>
          <div className={`text-neon-${risk_state.risk_band.includes('High') ? 'red' : 'green'}`} style={{ fontSize: '3rem', fontWeight: 'bold', lineHeight: 1 }}>
            {currentRiskPct}%
          </div>
          <div style={{ marginTop: '0.5rem', fontWeight: 'bold' }}>{risk_state.model_risk_band}</div>
        </motion.div>

        <motion.div className="glass-card" variants={cardVariants} style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <AlertTriangle color="var(--neon-cyan)" />
            <div style={{ fontWeight: 'bold' }}>Local Sensitivity Interval</div>
          </div>
          <div style={{ fontSize: '1.2rem', fontFamily: 'monospace' }}>
            [ {(risk_state.risk_ci_lower * 100).toFixed(1)}% - {(risk_state.risk_ci_upper * 100).toFixed(1)}% ]
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Feature perturbation bounds (Not bootstrap confidence)
          </div>
        </motion.div>

        <motion.div className="glass-card" variants={cardVariants} style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', border: '1px solid rgba(188, 19, 254, 0.3)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <ShieldAlert color="var(--neon-purple)" />
            <div style={{ fontWeight: 'bold' }}>Genetic Context</div>
          </div>
          <div style={{ fontSize: '1.2rem', color: 'var(--neon-purple)' }}>Population Index</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
            Neutral prior assumed. Does not constitute patient genetic risk.
          </div>
        </motion.div>
      </div>

      {/* Nivo Horizontal Bar Chart */}
      <motion.div className="glass-card" variants={cardVariants} style={{ height: '400px', paddingBottom: '3rem' }}>
        <h2 style={{ marginBottom: '1rem' }}>Risk Model Comparison</h2>
        <ResponsiveBar
          data={barData}
          keys={['risk']}
          indexBy="model"
          margin={{ top: 10, right: 130, bottom: 50, left: 120 }}
          padding={0.3}
          layout="horizontal"
          valueScale={{ type: 'linear', min: 0, max: 100 }}
          indexScale={{ type: 'band', round: true }}
          colors={['var(--neon-cyan)']}
          borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
          axisTop={null}
          axisRight={null}
          axisBottom={{
            tickSize: 5,
            tickPadding: 5,
            tickRotation: 0,
            legend: 'Estimated Risk (%)',
            legendPosition: 'middle',
            legendOffset: 32,
            tickValues: [0, 20, 40, 60, 80, 100]
          }}
          axisLeft={{
            tickSize: 5,
            tickPadding: 5,
            tickRotation: 0,
          }}
          theme={{
            axis: {
              ticks: { text: { fill: 'var(--text-secondary)' } },
              legend: { text: { fill: 'var(--text-secondary)' } }
            },
            grid: { line: { stroke: 'rgba(255,255,255,0.05)' } }
          }}
          enableGridY={false}
          enableGridX={true}
          labelSkipWidth={12}
          labelSkipHeight={12}
          labelTextColor="#000"
          animate={true}
          motionStiffness={90}
          motionDamping={15}
          tooltip={({ id, value, color, data }) => (
            <div style={{
              padding: '12px 16px',
              background: 'var(--surface-color)',
              backdropFilter: 'blur(10px)',
              border: '1px solid var(--border-color)',
              color: 'var(--text-primary)',
              borderRadius: '8px'
            }}>
              <strong>{data.model}</strong>
              <br />
              <span style={{ color: 'var(--neon-cyan)' }}>Risk: {value}%</span>
              <br />
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                Sensitivity: [{data.min}% - {data.max}%]
              </span>
            </div>
          )}
        />
      </motion.div>
    </motion.div>
  );
};

export default RiskDashboard;
