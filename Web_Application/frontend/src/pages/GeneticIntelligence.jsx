import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ResponsiveBar } from '@nivo/bar';
import { ResponsiveTreeMap } from '@nivo/treemap';
import { Dna, Pill, Network } from 'lucide-react';
import axios from 'axios';

const GeneticIntelligence = ({ patientData }) => {
  const [genes, setGenes] = useState(null);
  const [pathways, setPathways] = useState(null);
  const [pgx, setPgx] = useState(null);

  useEffect(() => {
    // Fetch Phase 2 Genetics Data
    axios.get('http://127.0.0.1:8000/api/genetics/genes').then(res => {
      // Get top 15 genes for visualization
      const topGenes = res.data.genes.slice(0, 15).map(g => ({
        gene: g.gene_symbol,
        contribution: g.gene_pct
      }));
      setGenes(topGenes.reverse()); // Reverse for bottom-up bar chart
    }).catch(console.error);

    axios.get('http://127.0.0.1:8000/api/genetics/pathways').then(res => {
      const pData = {
        name: 'Genetic Pathways',
        color: 'hsl(280, 100%, 50%)',
        children: res.data.pathways.map(p => ({
          name: p.pathway,
          value: p.pct_total_gbi
        }))
      };
      setPathways(pData);
    }).catch(console.error);

    axios.get('http://127.0.0.1:8000/api/genetics/pharmacogenomics').then(res => {
      setPgx(res.data.pgx);
    }).catch(console.error);

  }, []);

  if (!patientData || !genes || !pathways || !pgx) {
    return <div style={{ textAlign: 'center', padding: '4rem' }}><h2 className="text-neon-cyan">Loading Genetic Intelligence...</h2></div>;
  }

  const cardVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
  };

  return (
    <motion.div initial="hidden" animate="visible" variants={{ visible: { transition: { staggerChildren: 0.1 } } }}>
      <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
        <h1 className="text-neon-purple">Genetic Intelligence</h1>
        <p style={{ color: 'var(--text-secondary)' }}>
          PGS000116 Population Base Analysis (40,079 Variants)
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
        
        {/* Gene Intelligence Bar Chart */}
        <motion.div className="glass-card" variants={cardVariants} style={{ height: '400px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', flexShrink: 0 }}>
            <Dna color="var(--neon-purple)" />
            <h2 style={{ color: 'var(--neon-purple)' }}>Top Loci Contributions</h2>
          </div>
          <div style={{ flex: 1, minHeight: 0 }}>
            <ResponsiveBar
            data={genes}
            keys={['contribution']}
            indexBy="gene"
            margin={{ top: 10, right: 30, bottom: 50, left: 100 }}
            padding={0.3}
            layout="horizontal"
            colors={['var(--neon-purple)']}
            borderColor={{ from: 'color', modifiers: [['darker', 1.6]] }}
            axisBottom={{
              tickSize: 5,
              tickPadding: 5,
              tickRotation: 0,
              legend: 'Contribution (%)',
              legendPosition: 'middle',
              legendOffset: 32
            }}
            theme={{
              axis: { ticks: { text: { fill: 'var(--text-secondary)' } }, legend: { text: { fill: 'var(--text-secondary)' } } },
              grid: { line: { stroke: 'rgba(255,255,255,0.05)' } }
            }}
            tooltip={({ id, value, color, data }) => (
              <div style={{ padding: '12px', background: 'var(--surface-color)', border: '1px solid var(--border-color)' }}>
                <strong style={{ color: 'var(--neon-purple)' }}>{data.gene}</strong><br />
                <span>Contribution: {value}%</span>
              </div>
            )}
          />
          </div>
        </motion.div>

        {/* Pathway Treemap */}
        <motion.div className="glass-card" variants={cardVariants} style={{ height: '400px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', flexShrink: 0 }}>
            <Network color="var(--neon-cyan)" />
            <h2 style={{ color: 'var(--neon-cyan)' }}>Pathway Mapping</h2>
          </div>
          <div style={{ flex: 1, minHeight: 0 }}>
            <ResponsiveTreeMap
            data={pathways}
            identity="name"
            value="value"
            valueFormat=".2f"
            leavesOnly={true}
            innerPadding={3}
            margin={{ top: 10, right: 10, bottom: 10, left: 10 }}
            labelSkipSize={12}
            labelTextColor={{ from: 'color', modifiers: [ [ 'darker', 3 ] ] }}
            colors={{ scheme: 'purple_blue' }}
            borderColor={{ from: 'color', modifiers: [ [ 'darker', 0.1 ] ] }}
            tooltip={({ node }) => (
              <div style={{ padding: '12px', background: 'var(--surface-color)', border: '1px solid var(--border-color)' }}>
                <strong style={{ color: 'var(--neon-cyan)' }}>{node.data.name}</strong><br />
                <span>{node.formattedValue}% of GBI</span>
              </div>
            )}
            />
          </div>
        </motion.div>

      </div>

      {/* PGx Context Cards */}
      <motion.div variants={cardVariants}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
          <Pill color="var(--neon-red)" />
          <h2 style={{ color: 'var(--text-primary)' }}>Pharmacogenomic Evidence Context</h2>
        </div>
        <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
          *Strictly Population Knowledge Only. Does not constitute an individual treatment recommendation.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
          {pgx.map((item, idx) => (
            <div key={idx} className="glass-card" style={{ border: '1px solid rgba(255, 0, 60, 0.2)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--neon-purple)' }}>{item.gene_symbol}</div>
                <div style={{ background: 'rgba(255, 255, 255, 0.1)', padding: '0.2rem 0.5rem', borderRadius: '4px', fontSize: '0.8rem' }}>
                  {item.variants_in_pgs} Variants
                </div>
              </div>
              <div style={{ color: 'var(--neon-cyan)', fontSize: '0.9rem', marginBottom: '0.5rem' }}>{item.drug_class}</div>
              <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                <strong>Evidence:</strong> {item.evidence_framework} ({item.evidence_level})
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '1rem' }}>
                {item.clinical_guidance}
              </div>
            </div>
          ))}
        </div>
      </motion.div>
    </motion.div>
  );
};

export default GeneticIntelligence;
