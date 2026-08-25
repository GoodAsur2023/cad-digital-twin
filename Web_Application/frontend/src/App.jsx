import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, NavLink, useLocation } from 'react-router-dom';
import axios from 'axios';
import { motion } from 'framer-motion';
import { Activity, HeartPulse, Dna, LayoutDashboard, User, BarChart3, Fingerprint, FilePlus } from 'lucide-react';
import './index.css';
import PatientProfile from './pages/PatientProfile';
import RiskDashboard from './pages/RiskDashboard';
import IntegratedTwin from './pages/IntegratedTwin';
import GeneticIntelligence from './pages/GeneticIntelligence';
import Explainability from './pages/Explainability';
import ScreeningPortal from './pages/ScreeningPortal';

const NavItem = ({ to, icon: Icon, label, color, shadowColor }) => (
  <NavLink 
    to={to} 
    style={({ isActive }) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
      color: isActive ? color : 'var(--text-secondary)',
      textDecoration: 'none',
      fontWeight: 500,
      textShadow: isActive ? `0 0 8px ${shadowColor}` : 'none',
      borderBottom: isActive ? `2px solid ${color}` : '2px solid transparent',
      paddingBottom: '4px',
      transition: 'all 0.2s ease'
    })}
  >
    <Icon size={20} />
    <span>{label}</span>
  </NavLink>
);

const App = () => {
  const [patientData, setPatientData] = useState(null);
  const [patientId, setPatientId] = useState(4248);
  const [inputVal, setInputVal] = useState("4248");

  useEffect(() => {
    axios.get(`http://127.0.0.1:8000/api/patient/${patientId}`)
      .then(res => setPatientData(res.data))
      .catch(err => {
         console.error('Backend offline or patient not found.', err);
         alert(`Patient #${patientId} not found in database. Try another ID.`);
      });
  }, [patientId]);

  return (
    <Router>
      <nav>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <HeartPulse color="#00f3ff" size={28} />
          <h2 style={{ margin: 0 }} className="text-neon-cyan">CAD Digital Twin</h2>
        </div>
        
        <div className="nav-links" style={{ display: 'flex', gap: '1.5rem', alignItems: 'center' }}>
          <NavItem to="/" icon={User} label="Patient" color="#00f3ff" shadowColor="rgba(0, 243, 255, 0.5)" />
          <NavItem to="/dashboard" icon={BarChart3} label="Dashboard" color="#ffcc00" shadowColor="rgba(255, 204, 0, 0.5)" />
          <NavItem to="/integrated-twin" icon={Activity} label="Integrated Twin" color="#00ff66" shadowColor="rgba(0, 255, 102, 0.5)" />
          <NavItem to="/genetics" icon={Dna} label="Genetics" color="#bc13fe" shadowColor="rgba(188, 19, 254, 0.5)" />
          <NavItem to="/explainability" icon={Fingerprint} label="Explainability" color="#ff9900" shadowColor="rgba(255, 153, 0, 0.5)" />
          <NavItem to="/screen" icon={FilePlus} label="Screen New" color="#ff3366" shadowColor="rgba(255, 51, 102, 0.5)" />
        </div>
        
        <div className="patient-header">
          {patientData ? (
            <>
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Patient ID (Enter to load)</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span style={{ fontWeight: 'bold' }}>#</span>
                  <input 
                    type="number" 
                    value={inputVal}
                    onChange={(e) => setInputVal(e.target.value)}
                    onBlur={() => setPatientId(Number(inputVal))}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') setPatientId(Number(inputVal));
                    }}
                    style={{
                      background: 'rgba(255,255,255,0.1)',
                      border: '1px solid rgba(255,255,255,0.2)',
                      color: 'white',
                      width: '70px',
                      borderRadius: '4px',
                      padding: '2px 6px',
                      fontWeight: 'bold',
                      outline: 'none'
                    }}
                  />
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Model Risk</div>
                <div className="text-neon-red" style={{ fontWeight: 'bold' }}>
                  {(patientData.risk_state.current_risk * 100).toFixed(1)}%
                </div>
              </div>
              <div className="patient-header-badge">
                {patientData.risk_state.model_risk_band}
              </div>
            </>
          ) : (
            <div style={{ color: 'var(--text-secondary)' }}>Loading Context...</div>
          )}
        </div>
      </nav>

      <div className="container">
        {/* Research Warning Banner */}
        <div style={{ 
          background: 'rgba(255, 204, 0, 0.1)', 
          border: '1px solid rgba(255, 204, 0, 0.3)',
          color: '#ffcc00',
          padding: '0.75rem',
          borderRadius: '8px',
          marginBottom: '2rem',
          textAlign: 'center',
          fontSize: '0.9rem'
        }}>
          <strong>Research Prototype</strong> - Model outputs are for research and demonstration only and are not clinical diagnoses, treatment recommendations, or estimates of causal treatment effects.
        </div>

        <Routes>
          <Route path="/" element={<PatientProfile patientData={patientData} />} />
          <Route path="/dashboard" element={<RiskDashboard patientData={patientData} />} />
          <Route path="/integrated-twin" element={<IntegratedTwin patientData={patientData} />} />
          <Route path="/genetics" element={<GeneticIntelligence patientData={patientData} />} />
          <Route path="/explainability" element={<Explainability patientData={patientData} />} />
          <Route path="/screen" element={<ScreeningPortal setPatientId={setPatientId} />} />
        </Routes>
      </div>
    </Router>
  );
};

export default App;
