"""
patient_intelligence_engine.py
═══════════════════════════════════════════════════════════════════
Shared Intelligence Module for the CVD Digital Twin Project

This module provides reusable components shared across NB3–NB9:
  • GIDBClient          — GI-DB API wrapper (rate-limited, cached)
  • EnsemblVEPClient    — Ensembl VEP REST API wrapper (fallback)
  • GeneticIntelligenceEngine — gene-level PRS, confidence, annotation
  • PatientState        — structured patient representation
  • InterventionEngine  — counterfactuals + uncertainty
  • GuidelineMapper     — ACC/AHA risk band mapper

Works in both Google Colab and local Windows environments.
═══════════════════════════════════════════════════════════════════
"""

import os
import sys
import json
import time
import pickle
import hashlib
import warnings
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# ═══════════════════════════════════════════════════════════════════
# ENVIRONMENT DETECTION
# ═══════════════════════════════════════════════════════════════════

def detect_environment():
    """Detect whether running in Google Colab or local."""
    try:
        from google.colab import drive  # noqa: F401
        return 'colab'
    except ImportError:
        return 'local'

def get_base_dir():
    """Return the base directory depending on environment."""
    env = detect_environment()
    if env == 'colab':
        from google.colab import drive
        drive.mount('/content/drive', force_remount=False)
        return '/content/drive/MyDrive/CAD_DT_Final/'
    else:
        # Local Windows path
        candidates = [
            r'E:\Capstone',
            r'e:\Capstone',
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ]
        for p in candidates:
            if os.path.isdir(p):
                return p.replace('\\', '/') + '/'
        raise FileNotFoundError(
            "Cannot detect project root. Set BASE_DIR manually."
        )

def get_paths(base_dir=None):
    """Return a dict of all standard project paths."""
    if base_dir is None:
        base_dir = get_base_dir()
    base = base_dir.rstrip('/') + '/'
    paths = {
        'BASE_DIR':        base,
        'RAW_DIR':         base + 'Data/Raw/',
        'GI_DIR':          base + 'Data/Raw/Genome_India/',
        'OUTPUTS_DIR':     base + 'Outputs/',
        'GENETICS_DIR':    base + 'Outputs/Genetics/',
        'MODELS_DIR':      base + 'Outputs/Models/',
        'INTEGRATED_DIR':  base + 'Outputs/Integrated/',
        'LIFESTYLE_DIR':   base + 'Outputs/Lifestyle/',
        'CLINICAL_DIR':    base + 'Outputs/Clinical/',
        'FIGURES_DIR':     base + 'Outputs/Figures/',
        'EXPL_DIR':        base + 'Outputs/Explainability/',
        'DT_DIR':          base + 'Outputs/Digital_Twin/',
        # Key files
        'PGS_PATH':        base + 'Data/Raw/pgs_catalog_2809.tsv',
        'HARMONIZED_MAP':  base + 'Outputs/Genetics/harmonized_genetic_map.csv',
        'PRS_SCORE':       base + 'Outputs/Genetics/prs_population_score.csv',
        'PER_SNP':         base + 'Outputs/Genetics/per_snp_contribution.csv',
        'PRS_VECTOR':      base + 'Outputs/Genetics/prs_feature_vector.pkl',
        'GI_PROFILE':      base + 'Outputs/Genetics/genetic_intelligence_profile.json',
        'GENE_CONTRIB':    base + 'Outputs/Genetics/gene_level_contributions.csv',
        'LS_PIPELINE':     base + 'Outputs/Models/lifestyle_pipeline.pkl',
        'CL_PIPELINE':     base + 'Outputs/Models/clinical_pipeline.pkl',
        'LS_TEST':         base + 'Outputs/Lifestyle/df_lifestyle_test.csv',
        'CL_TEST':         base + 'Outputs/Clinical/df_clinical_test.csv',
        'LS_SCORES':       base + 'Outputs/Integrated/lifestyle_risk_scores_with_prs.csv',
        'CL_SCORES':       base + 'Outputs/Integrated/clinical_risk_scores_with_prs.csv',
        'API_CACHE':       base + 'Outputs/Genetics/.api_cache.json',
    }
    # Create output dirs
    for key in ['GENETICS_DIR', 'MODELS_DIR', 'INTEGRATED_DIR', 'FIGURES_DIR',
                'EXPL_DIR', 'DT_DIR', 'LIFESTYLE_DIR', 'CLINICAL_DIR']:
        os.makedirs(paths[key], exist_ok=True)
    return paths


# ═══════════════════════════════════════════════════════════════════
# GI-DB API CLIENT
# ═══════════════════════════════════════════════════════════════════

class GIDBClient:
    """
    Client for the Genome India Database (GI-DB) REST API.
    
    Rate limits: 30 requests/min, max 20 locations/request (each ≤100kb),
    max 5 genes/request, max 5000 variants returned.
    """
    BASE_URL = "https://gidb.igib.res.in/api/query.php"
    
    def __init__(self, cache_path=None):
        self.cache_path = cache_path
        self._cache = {}
        self._last_request_time = 0
        self._min_interval = 2.1  # ~28 req/min (under 30 limit)
        if cache_path and os.path.isfile(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    self._cache = json.load(f)
                print(f"  📦 GI-DB cache loaded: {len(self._cache)} entries")
            except Exception:
                self._cache = {}
    
    def _save_cache(self):
        if self.cache_path:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, 'w') as f:
                json.dump(self._cache, f)
    
    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()
    
    def _make_key(self, payload):
        return hashlib.md5(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    
    def query_locations(self, locations: List[str]) -> Dict:
        """
        Query GI-DB by genomic location(s).
        Automatically batches into groups of 20.
        Each location format: "chrN:start-end" (max 100kb span).
        """
        import requests
        
        all_results = {}
        batch_size = 20
        
        for i in range(0, len(locations), batch_size):
            batch = locations[i:i + batch_size]
            payload = {"type": "location", "locations": batch}
            cache_key = self._make_key(payload)
            
            if cache_key in self._cache:
                all_results.update(self._cache[cache_key])
                continue
            
            self._rate_limit()
            try:
                resp = requests.post(self.BASE_URL, json=payload, timeout=30)
                if resp.status_code == 429:
                    print("  ⏳ Rate limited — waiting 60s...")
                    time.sleep(60)
                    resp = requests.post(self.BASE_URL, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", {})
                self._cache[cache_key] = results
                all_results.update(results)
            except Exception as e:
                print(f"  ⚠️ GI-DB API error for batch {i//batch_size}: {e}")
                continue
        
        self._save_cache()
        return all_results
    
    def query_genes(self, genes: List[str]) -> Dict:
        """
        Query GI-DB by gene symbol(s).
        Automatically batches into groups of 5.
        """
        import requests
        
        all_results = {}
        batch_size = 5
        
        for i in range(0, len(genes), batch_size):
            batch = genes[i:i + batch_size]
            payload = {"type": "gene", "genes": batch}
            cache_key = self._make_key(payload)
            
            if cache_key in self._cache:
                all_results.update(self._cache[cache_key])
                continue
            
            self._rate_limit()
            try:
                resp = requests.post(self.BASE_URL, json=payload, timeout=30)
                if resp.status_code == 429:
                    print("  ⏳ Rate limited — waiting 60s...")
                    time.sleep(60)
                    resp = requests.post(self.BASE_URL, json=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                results = data.get("results", {})
                self._cache[cache_key] = results
                all_results.update(results)
            except Exception as e:
                print(f"  ⚠️ GI-DB API error for genes {batch}: {e}")
                continue
        
        self._save_cache()
        return all_results
    
    def query_variant_by_position(self, chrom: str, position: int,
                                   window: int = 5) -> Optional[Dict]:
        """
        Query a single variant by chromosomal position ± window.
        Returns the first variant matching the exact position, or None.
        """
        loc = f"chr{chrom}:{max(1, position - window)}-{position + window}"
        results = self.query_locations([loc])
        
        for region_key, region_data in results.items():
            variants = region_data.get("variants", [])
            for v in variants:
                if int(v.get("POS", 0)) == position:
                    return v
        return None


# ═══════════════════════════════════════════════════════════════════
# ENSEMBL VEP CLIENT (Fallback)
# ═══════════════════════════════════════════════════════════════════

class EnsemblVEPClient:
    """
    Fallback variant annotation using Ensembl VEP REST API.
    Rate limit: 15 requests/second (Ensembl documented limit).
    """
    BASE_URL = "https://rest.ensembl.org"
    
    def __init__(self):
        self._last_request_time = 0
        self._min_interval = 0.07  # ~14 req/sec
    
    def _rate_limit(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        self._last_request_time = time.time()
    
    def vep_region_batch(self, variants: List[Dict]) -> List[Dict]:
        """
        Submit a batch of variants to Ensembl VEP POST endpoint.
        Each variant: {"chr": "1", "pos": 55030366, "ref": "T", "alt": "C"}
        Max 200 variants per request.
        Returns list of VEP annotation results.
        """
        import requests
        
        # Format for VEP POST
        vep_input = []
        for v in variants:
            vep_input.append(
                f"{v['chr']} {v['pos']} . {v['ref']} {v['alt']} . . ."
            )
        
        results = []
        batch_size = 200
        
        for i in range(0, len(vep_input), batch_size):
            batch = vep_input[i:i + batch_size]
            self._rate_limit()
            try:
                resp = requests.post(
                    f"{self.BASE_URL}/vep/homo_sapiens/region",
                    headers={"Content-Type": "application/json",
                             "Accept": "application/json"},
                    json={"variants": batch},
                    timeout=60
                )
                if resp.ok:
                    results.extend(resp.json())
                else:
                    print(f"  ⚠️ Ensembl VEP error: {resp.status_code}")
            except Exception as e:
                print(f"  ⚠️ Ensembl VEP request failed: {e}")
        
        return results


# ═══════════════════════════════════════════════════════════════════
# FUNCTIONAL IMPACT MAPPING
# ═══════════════════════════════════════════════════════════════════

# Consequence → functional impact weight mapping
# Based on standard variant effect severity hierarchy
CONSEQUENCE_WEIGHTS = {
    # HIGH impact
    'transcript_ablation': 1.5,
    'splice_acceptor_variant': 1.4,
    'splice_donor_variant': 1.4,
    'stop_gained': 1.4,
    'frameshift_variant': 1.3,
    'stop_lost': 1.3,
    'start_lost': 1.3,
    # MODERATE impact
    'missense_variant': 1.1,
    'inframe_insertion': 1.05,
    'inframe_deletion': 1.05,
    'protein_altering_variant': 1.05,
    # LOW impact
    'splice_region_variant': 0.95,
    'synonymous_variant': 0.9,
    'stop_retained_variant': 0.9,
    # MODIFIER impact
    '5_prime_UTR_variant': 0.85,
    '3_prime_UTR_variant': 0.85,
    'non_coding_transcript_exon_variant': 0.85,
    'intron_variant': 0.8,
    'upstream_gene_variant': 0.8,
    'downstream_gene_variant': 0.8,
    'intergenic_variant': 0.75,
    'regulatory_region_variant': 0.85,
    'TF_binding_site_variant': 0.9,
}

IMPACT_LEVELS = {
    'HIGH': 1.3,
    'MODERATE': 1.1,
    'LOW': 0.9,
    'MODIFIER': 0.8,
}

def get_functional_weight(consequence_str: str, impact_str: str = '') -> float:
    """
    Map a consequence type string to a functional weight.
    Falls back to impact level, then to 1.0 (neutral).
    """
    if consequence_str and isinstance(consequence_str, str):
        # Take the most severe consequence if multiple
        consequences = [c.strip() for c in consequence_str.split(',')]
        weights = [CONSEQUENCE_WEIGHTS.get(c, None) for c in consequences]
        weights = [w for w in weights if w is not None]
        if weights:
            return max(weights)  # Most severe
    
    # Fallback to impact level
    if impact_str and isinstance(impact_str, str):
        return IMPACT_LEVELS.get(impact_str.upper(), 1.0)
    
    return 1.0  # Neutral default


# ═══════════════════════════════════════════════════════════════════
# GENETIC INTELLIGENCE ENGINE
# ═══════════════════════════════════════════════════════════════════

class GeneticIntelligenceEngine:
    """
    Transforms a scalar PRS into a rich Genetic Intelligence Profile.
    
    Inputs:
      - Enhanced harmonized_genetic_map.csv (with gene, consequence, ClinVar)
      - prs_population_score.csv
    
    Outputs:
      - Gene-level contributions
      - Variant confidence score
      - Genetic Intelligence Profile (JSON)
    """
    
    def __init__(self, harmonized_path: str, prs_path: str):
        self.harmonized_df = pd.read_csv(harmonized_path)
        self.prs_df = pd.read_csv(prs_path)
        self.prs_raw = float(self.prs_df['prs_raw'].values[0])
        self.n_snps = int(self.prs_df['n_snps'].values[0])
        
        # Compute per-SNP contribution if not present
        if 'prs_contribution' not in self.harmonized_df.columns:
            p = self.harmonized_df['indian_ancestry_risk_allele_freq'].values
            b = self.harmonized_df['effect_weight_beta'].values
            self.harmonized_df['prs_contribution'] = 2.0 * p * b
    
    def compute_gene_contributions(self) -> pd.DataFrame:
        """Aggregate PRS contributions by gene."""
        if 'gene_symbol' not in self.harmonized_df.columns:
            print("  ⚠️ gene_symbol column missing — skipping gene aggregation")
            return pd.DataFrame()
        
        df = self.harmonized_df.copy()
        df['gene_symbol'] = df['gene_symbol'].fillna('INTERGENIC')
        
        gene_df = (
            df.groupby('gene_symbol')
            .agg(
                n_snps=('rsID', 'count'),
                gene_prs=('prs_contribution', 'sum'),
                avg_beta=('effect_weight_beta', 'mean'),
                avg_freq=('indian_ancestry_risk_allele_freq', 'mean'),
            )
            .reset_index()
        )
        gene_df['gene_pct'] = (gene_df['gene_prs'] / self.prs_raw * 100).round(2)
        gene_df = gene_df.sort_values('gene_prs', ascending=False).reset_index(drop=True)
        return gene_df
    
    def compute_confidence(self) -> Dict:
        """Compute variant matching and annotation confidence."""
        total = self.n_snps
        matched = len(self.harmonized_df)
        match_rate = matched / total if total > 0 else 0
        
        has_gene = (
            self.harmonized_df['gene_symbol'].notna().sum()
            if 'gene_symbol' in self.harmonized_df.columns else 0
        )
        has_consequence = (
            self.harmonized_df['consequence_type'].notna().sum()
            if 'consequence_type' in self.harmonized_df.columns else 0
        )
        has_clinvar = (
            self.harmonized_df['clinvar_significance'].notna().sum()
            if 'clinvar_significance' in self.harmonized_df.columns else 0
        )
        
        annotation_rate = has_gene / matched if matched > 0 else 0
        consequence_rate = has_consequence / matched if matched > 0 else 0
        clinvar_rate = has_clinvar / matched if matched > 0 else 0
        
        # Composite confidence (weighted)
        composite = (
            0.50 * match_rate +
            0.25 * annotation_rate +
            0.15 * consequence_rate +
            0.10 * min(clinvar_rate * 5, 1.0)  # ClinVar is sparse, scale up
        )
        
        if composite >= 0.90:
            tier = 'HIGH'
        elif composite >= 0.70:
            tier = 'MEDIUM'
        else:
            tier = 'LOW'
        
        return {
            'variant_match_rate': round(match_rate, 4),
            'gene_annotation_rate': round(annotation_rate, 4),
            'consequence_annotation_rate': round(consequence_rate, 4),
            'clinvar_annotation_rate': round(clinvar_rate, 4),
            'composite_confidence': round(composite, 4),
            'tier': tier,
            'n_matched': matched,
            'n_total_pgs': total,
        }
    
    def compute_annotation_summary(self) -> Dict:
        """Summarize consequence types and ClinVar categories."""
        summary = {}
        
        if 'consequence_type' in self.harmonized_df.columns:
            cons_counts = (
                self.harmonized_df['consequence_type']
                .fillna('unknown')
                .value_counts()
                .to_dict()
            )
            summary['consequence_distribution'] = cons_counts
        
        if 'clinvar_significance' in self.harmonized_df.columns:
            clin_counts = (
                self.harmonized_df['clinvar_significance']
                .dropna()
                .value_counts()
                .to_dict()
            )
            summary['clinvar_distribution'] = clin_counts
        
        if 'impact_level' in self.harmonized_df.columns:
            impact_counts = (
                self.harmonized_df['impact_level']
                .fillna('UNKNOWN')
                .value_counts()
                .to_dict()
            )
            summary['impact_distribution'] = impact_counts
        
        return summary
    
    def build_profile(self) -> Dict:
        """Build the complete Genetic Intelligence Profile."""
        gene_df = self.compute_gene_contributions()
        confidence = self.compute_confidence()
        annotation = self.compute_annotation_summary()
        
        # Top genes
        top_genes = []
        if not gene_df.empty:
            for _, row in gene_df.head(10).iterrows():
                top_genes.append({
                    'gene': row['gene_symbol'],
                    'n_snps': int(row['n_snps']),
                    'contribution_prs': round(float(row['gene_prs']), 6),
                    'contribution_pct': float(row['gene_pct']),
                })
        
        # Top variants
        top_variants = []
        top_v = self.harmonized_df.nlargest(10, 'prs_contribution')
        for _, row in top_v.iterrows():
            entry = {
                'rsID': row['rsID'],
                'chromosome': str(row['chromosome']),
                'position': int(row['position_grch']),
                'effect_allele': row['effect_allele'],
                'beta': round(float(row['effect_weight_beta']), 6),
                'indian_freq': round(float(row['indian_ancestry_risk_allele_freq']), 6),
                'prs_contribution': round(float(row['prs_contribution']), 6),
            }
            if 'gene_symbol' in row and pd.notna(row.get('gene_symbol')):
                entry['gene'] = row['gene_symbol']
            if 'consequence_type' in row and pd.notna(row.get('consequence_type')):
                entry['consequence'] = row['consequence_type']
            top_variants.append(entry)
        
        profile = {
            'overall_prs': round(self.prs_raw, 6),
            'prs_percentile': 'population_mean',
            'n_snps_used': self.n_snps,
            'n_snps_harmonized': len(self.harmonized_df),
            'confidence': confidence,
            'top_genes': top_genes,
            'top_variants': top_variants,
            'population_context': 'Indian (GenomeIndia N=9768)',
            'pgs_catalog_id': 'PGS002809',
            'annotation_summary': annotation,
        }
        
        return profile
    
    def save_profile(self, output_path: str):
        """Build and save the Genetic Intelligence Profile to JSON."""
        profile = self.build_profile()
        with open(output_path, 'w') as f:
            json.dump(profile, f, indent=2, default=str)
        print(f"  ✅ Genetic Intelligence Profile saved: {output_path}")
        return profile


# ═══════════════════════════════════════════════════════════════════
# PATIENT STATE
# ═══════════════════════════════════════════════════════════════════

@dataclass
class PatientState:
    """
    Structured representation of a patient's multi-domain state.
    Used by the Patient State Engine in NB9.
    """
    # Identity
    patient_idx: int = -1
    cohort: str = ''
    
    # Genetic State
    genetic_state: Dict = field(default_factory=lambda: {
        'prs_raw': 0.0,
        'prs_sigmoid': 0.0,
        'confidence_tier': 'UNKNOWN',
        'top_genes': [],
        'gene_context_notes': [],
    })
    
    # Lifestyle State
    lifestyle_state: Dict = field(default_factory=dict)
    
    # Clinical State
    clinical_state: Dict = field(default_factory=dict)
    
    # Risk State
    risk_state: Dict = field(default_factory=lambda: {
        'current_risk': 0.0,
        'risk_ci_lower': 0.0,
        'risk_ci_upper': 0.0,
        'risk_band': 'Unknown',
        'acc_aha_category': '',
        'guideline_recommendation': '',
    })
    
    # Intervention State
    interventions: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def summary(self) -> str:
        """Human-readable summary of patient state."""
        lines = [
            f"═══ Patient {self.patient_idx} ({self.cohort}) ═══",
            f"  Risk: {self.risk_state.get('current_risk', 0):.1%} "
            f"[{self.risk_state.get('risk_ci_lower', 0):.1%}–"
            f"{self.risk_state.get('risk_ci_upper', 0):.1%}]",
            f"  Band: {self.risk_state.get('risk_band', '?')}",
            f"  ACC/AHA: {self.risk_state.get('acc_aha_category', '?')}",
            f"  Genetic Confidence: {self.genetic_state.get('confidence_tier', '?')}",
        ]
        if self.interventions:
            lines.append("  Top Interventions:")
            for i, intv in enumerate(self.interventions[:3], 1):
                lines.append(
                    f"    {i}. {intv.get('scenario_id', '?')} "
                    f"→ Δ{intv.get('pct_reduction', 0):+.1f}%"
                )
        return '\n'.join(lines)


# ═══════════════════════════════════════════════════════════════════
# GUIDELINE MAPPER (ACC/AHA 2019)
# ═══════════════════════════════════════════════════════════════════

class GuidelineMapper:
    """
    Maps predicted CAD risk to ACC/AHA 2019 Guideline categories
    and generates clinical recommendations.
    
    Reference: 2019 ACC/AHA Guideline on Primary Prevention of CVD
    (Arnett et al., Circulation 2019)
    """
    
    CATEGORIES = [
        {
            'name': 'Low Risk',
            'range': (0.0, 0.05),
            'recommendation': (
                'Lifestyle modifications recommended. '
                'Emphasize heart-healthy diet, regular exercise, '
                'tobacco avoidance, and healthy weight maintenance.'
            ),
            'statin': 'Not indicated',
            'monitoring': 'Reassess in 5 years',
        },
        {
            'name': 'Borderline Risk',
            'range': (0.05, 0.075),
            'recommendation': (
                'Lifestyle modifications recommended. '
                'Consider statin therapy if risk-enhancing factors present '
                '(family history, elevated LDL-C, metabolic syndrome, '
                'South Asian ancestry, elevated hsCRP).'
            ),
            'statin': 'Consider if risk enhancers present',
            'monitoring': 'Reassess in 3-5 years',
        },
        {
            'name': 'Intermediate Risk',
            'range': (0.075, 0.20),
            'recommendation': (
                'Moderate-intensity statin therapy recommended to reduce '
                'LDL-C by 30-49%. Lifestyle interventions strongly advised. '
                'Consider coronary artery calcium (CAC) scoring for '
                'further risk stratification.'
            ),
            'statin': 'Moderate-intensity statin recommended',
            'monitoring': 'Annual reassessment',
        },
        {
            'name': 'High Risk',
            'range': (0.20, 1.01),
            'recommendation': (
                'High-intensity statin therapy recommended to reduce '
                'LDL-C by ≥50%. Aggressive lifestyle intervention required. '
                'Consider additional lipid-lowering therapy (ezetimibe, '
                'PCSK9 inhibitors) if LDL-C remains elevated. '
                'Specialist cardiology referral recommended.'
            ),
            'statin': 'High-intensity statin recommended',
            'monitoring': 'Specialist follow-up every 3-6 months',
        },
    ]
    
    @classmethod
    def classify(cls, risk_probability: float) -> Dict:
        """Map a risk probability to ACC/AHA guideline category."""
        risk = max(0.0, min(1.0, risk_probability))
        for cat in cls.CATEGORIES:
            lo, hi = cat['range']
            if lo <= risk < hi:
                return {
                    'risk_probability': round(risk, 4),
                    'acc_aha_category': cat['name'],
                    'recommendation': cat['recommendation'],
                    'statin_recommendation': cat['statin'],
                    'monitoring': cat['monitoring'],
                }
        # Fallback
        return {
            'risk_probability': round(risk, 4),
            'acc_aha_category': 'Unclassified',
            'recommendation': 'Consult clinician.',
            'statin_recommendation': 'Unknown',
            'monitoring': 'Unknown',
        }
    
    @classmethod
    def get_gene_context_notes(cls, gene_contributions: pd.DataFrame,
                                threshold_pct: float = 10.0) -> List[str]:
        """
        Generate gene-aware clinical context notes.
        If a gene contributes >threshold_pct% to genetic risk, 
        provide targeted pharmacological context.
        """
        notes = []
        if gene_contributions.empty:
            return notes
        
        GENE_CONTEXT = {
            'PCSK9': (
                'Elevated PCSK9-region genetic burden detected. '
                'PCSK9 inhibitors (e.g., evolocumab, alirocumab) may be '
                'considered for patients with persistently elevated LDL-C.'
            ),
            'LDLR': (
                'Elevated LDLR-region genetic burden detected. '
                'Aggressive statin therapy is recommended. '
                'Lifestyle intervention alone may be insufficient for '
                'adequate lipid control.'
            ),
            'LPA': (
                'Elevated Lp(a)-associated genetic burden detected. '
                'Lp(a) levels are largely genetically determined and '
                'resistant to lifestyle modification. '
                'Consider Lp(a) measurement and specialist referral.'
            ),
            'APOB': (
                'Elevated APOB-region genetic burden detected. '
                'Monitor apolipoprotein B levels. '
                'Consider combination lipid-lowering therapy.'
            ),
            'SORT1': (
                'SORT1/1p13.3 locus contributes to genetic risk. '
                'This locus affects hepatic LDL-C metabolism.'
            ),
        }
        
        for _, row in gene_contributions.iterrows():
            gene = row.get('gene_symbol', '')
            pct = row.get('gene_pct', 0)
            if pct >= threshold_pct and gene in GENE_CONTEXT:
                notes.append(GENE_CONTEXT[gene])
        
        return notes


# ═══════════════════════════════════════════════════════════════════
# INTERVENTION ENGINE
# ═══════════════════════════════════════════════════════════════════

class InterventionEngine:
    """
    Enhanced counterfactual engine with uncertainty quantification
    and personalized intervention ranking.
    """
    
    @staticmethod
    def integrated_risk(pipeline, X, prs_sigmoid, w1=0.85, w2=0.15):
        """Compute PRS-integrated CAD risk per NB7 formula."""
        p_model = pipeline.predict_proba(X)[:, 1]
        p_int = w1 * p_model + w2 * prs_sigmoid
        return np.clip(p_int, 0.0, 1.0)
    
    @staticmethod
    def compute_risk_with_uncertainty(pipeline, X, prs_sigmoid,
                                       n_bootstrap=200, w1=0.85, w2=0.15):
        """
        Compute risk with bootstrap-based confidence interval.
        Uses prediction variability across multiple stochastic passes.
        
        For tree-based models, we perturb inputs slightly (±1% noise)
        to estimate prediction stability, providing a practical CI.
        """
        base_risk = float(
            InterventionEngine.integrated_risk(pipeline, X, prs_sigmoid, w1, w2)[0]
        )
        
        # Monte Carlo noise injection for CI estimation
        risks = []
        X_arr = X.values if hasattr(X, 'values') else X
        
        for _ in range(n_bootstrap):
            noise = np.random.normal(1.0, 0.01, X_arr.shape)
            X_noisy = pd.DataFrame(X_arr * noise, columns=X.columns)
            r = float(
                InterventionEngine.integrated_risk(
                    pipeline, X_noisy, prs_sigmoid, w1, w2
                )[0]
            )
            risks.append(r)
        
        ci_lower = float(np.percentile(risks, 2.5))
        ci_upper = float(np.percentile(risks, 97.5))
        
        return {
            'risk': round(base_risk, 4),
            'ci_lower': round(ci_lower, 4),
            'ci_upper': round(ci_upper, 4),
        }
    
    @staticmethod
    def rank_interventions(results_df: pd.DataFrame) -> pd.DataFrame:
        """
        Rank interventions by risk reduction (descending delta).
        Returns sorted DataFrame with rank column.
        """
        ranked = results_df.sort_values('delta', ascending=False).copy()
        ranked['rank'] = range(1, len(ranked) + 1)
        return ranked.reset_index(drop=True)
    
    @staticmethod
    def dose_response(pipeline, patient_row, feature_list, feature_name,
                      values, prs_sigmoid, w1=0.85, w2=0.15):
        """
        Compute dose-response curve for a single feature.
        
        Args:
            values: list of feature values to simulate
        Returns:
            DataFrame with columns [value, risk]
        """
        X_base = pd.DataFrame(
            [patient_row[feature_list].values], columns=feature_list
        )
        
        results = []
        for val in values:
            X_mod = X_base.copy()
            if feature_name in X_mod.columns:
                X_mod[feature_name] = val
            risk = float(
                InterventionEngine.integrated_risk(
                    pipeline, X_mod, prs_sigmoid, w1, w2
                )[0]
            )
# ═══════════════════════════════════════════════════════════════════
# COMPONENT 6: PulsePhysio Physiological Simulation Engine
# ═══════════════════════════════════════════════════════════════════

class PulsePhysioSimulator:
    """
    Cardiovascular Hemodynamic Simulation Engine based on Pulse Physiology
    and Windkessel lumped-parameter cardiovascular dynamics.
    
    Simulates physiological adaptations (blood pressure, heart rate, vascular
    resistance, cardiac workload) in response to lifestyle and clinical interventions.
    """
    
    PULSE_SCENARIOS = {
        'exercise_aerobic': {
            'description': '90-day regular aerobic exercise conditioning',
            'mechanism': 'Arterial compliance improvement & cardiac reserve expansion',
            'sbp_delta': -3.5,        # mmHg (Cornelissen & Smart, JAHA 2013)
            'max_hr_delta': +5.0,     # bpm (exercise capacity increase)
            'chol_delta': 0.0,
            'source': 'Cornelissen & Smart, JAHA 2013',
        },
        'weight_loss_5pct': {
            'description': '5% sustained body weight reduction',
            'mechanism': 'Peripheral vascular resistance decompression & workload reduction',
            'sbp_delta': -4.0,        # mmHg systolic
            'max_hr_delta': 0.0,
            'chol_delta': -5.0,       # mg/dL
            'source': 'AHA/ACC Obesity Guidelines Meta-analysis',
        },
        'smoking_cessation': {
            'description': 'Complete tobacco / nicotine cessation',
            'mechanism': 'Endothelial nitric oxide bioavailability & elasticity recovery',
            'sbp_delta': -5.0,        # mmHg systolic
            'max_hr_delta': 0.0,
            'chol_delta': 0.0,
            'source': 'Critchley & Capewell, JAMA 2003',
        },
        'combined_exercise_diet': {
            'description': 'Combined aerobic training and cardioprotective diet',
            'mechanism': 'Synergistic vascular compliance, metabolic, and autonomic recovery',
            'sbp_delta': -7.5,        # mmHg systolic
            'max_hr_delta': +5.0,     # bpm
            'chol_delta': -25.0,      # mg/dL
            'source': 'Multi-factorial intervention trials',
        },
    }
    
    @staticmethod
    def initialize_hemodynamics(patient_dict: Dict[str, Any]) -> Dict[str, float]:
        """
        Initialize hemodynamic parameters for a clinical patient.
        Estimates DBP, MAP, PP, SVRI, and Double Product (RPP).
        """
        sbp = float(patient_dict.get('resting_bp', 130.0))
        # Clinical dataset records resting SBP; estimate DBP ≈ 0.67 * SBP
        dbp = float(sbp * 0.67)
        map_val = float((2.0 * dbp + sbp) / 3.0)
        pp = float(sbp - dbp)
        
        hr = float(patient_dict.get('max_heart_rate', 150.0))
        # Resting HR estimate ≈ 72 bpm or from max_hr
        resting_hr = max(55.0, min(100.0, hr * 0.48))
        
        # Rate-pressure double product (DP = resting_hr * SBP): surrogate for myocardial O2 consumption
        double_product = float(resting_hr * sbp)
        
        # Stroke volume estimate (mL) & Cardiac Output (L/min)
        # SV ≈ PP * 1.5, CO = (SV * HR) / 1000
        sv = max(40.0, min(110.0, pp * 1.4))
        co = (sv * resting_hr) / 1000.0
        
        # Systemic Vascular Resistance (SVR = (MAP - 4) / CO * 80 dynes*s/cm^5)
        svr = float(((map_val - 4.0) / max(co, 1.0)) * 80.0)
        
        return {
            'systolic_bp': round(sbp, 1),
            'diastolic_bp': round(dbp, 1),
            'map': round(map_val, 1),
            'pulse_pressure': round(pp, 1),
            'resting_hr': round(resting_hr, 1),
            'max_heart_rate': round(hr, 1),
            'stroke_volume': round(sv, 1),
            'cardiac_output': round(co, 2),
            'svr': round(svr, 1),
            'double_product': round(double_product, 0),
            'cholesterol': float(patient_dict.get('cholesterol', 200.0)),
        }
    
    @classmethod
    def simulate(cls, hemo_baseline: Dict[str, float], scenario_id: str) -> Dict[str, Any]:
        """
        Run physiological simulation for an intervention scenario.
        Returns new hemodynamic state and calculated deltas.
        """
        if scenario_id not in cls.PULSE_SCENARIOS:
            raise ValueError(f"Unknown Pulse scenario: {scenario_id}")
        
        scen = cls.PULSE_SCENARIOS[scenario_id]
        
        new_sbp = max(85.0, hemo_baseline['systolic_bp'] + scen['sbp_delta'])
        new_dbp = new_sbp * 0.67
        new_map = (2.0 * new_dbp + new_sbp) / 3.0
        new_pp = new_sbp - new_dbp
        
        new_max_hr = min(210.0, hemo_baseline['max_heart_rate'] + scen['max_hr_delta'])
        new_resting_hr = max(50.0, hemo_baseline['resting_hr'] - (1.5 if scen['max_hr_delta'] > 0 else 0.0))
        
        new_dp = new_resting_hr * new_sbp
        new_chol = max(100.0, hemo_baseline['cholesterol'] + scen['chol_delta'])
        
        # New Stroke volume & SVR
        new_sv = max(40.0, min(115.0, new_pp * 1.4))
        new_co = (new_sv * new_resting_hr) / 1000.0
        new_svr = float(((new_map - 4.0) / max(new_co, 1.0)) * 80.0)
        
        hemo_new = {
            'systolic_bp': round(new_sbp, 1),
            'diastolic_bp': round(new_dbp, 1),
            'map': round(new_map, 1),
            'pulse_pressure': round(new_pp, 1),
            'resting_hr': round(new_resting_hr, 1),
            'max_heart_rate': round(new_max_hr, 1),
            'stroke_volume': round(new_sv, 1),
            'cardiac_output': round(new_co, 2),
            'svr': round(new_svr, 1),
            'double_product': round(new_dp, 0),
            'cholesterol': round(new_chol, 1),
        }
        
        deltas = {
            'sbp_delta': round(new_sbp - hemo_baseline['systolic_bp'], 1),
            'dbp_delta': round(new_dbp - hemo_baseline['diastolic_bp'], 1),
            'map_delta': round(new_map - hemo_baseline['map'], 1),
            'max_hr_delta': round(new_max_hr - hemo_baseline['max_heart_rate'], 1),
            'dp_delta': round(new_dp - hemo_baseline['double_product'], 0),
            'dp_pct_reduction': round((hemo_baseline['double_product'] - new_dp) / hemo_baseline['double_product'] * 100, 2),
            'svr_pct_change': round((new_svr - hemo_baseline['svr']) / hemo_baseline['svr'] * 100, 2),
            'chol_delta': round(new_chol - hemo_baseline['cholesterol'], 1),
        }
        
        return {
            'scenario_id': scenario_id,
            'description': scen['description'],
            'mechanism': scen['mechanism'],
            'source': scen['source'],
            'baseline': hemo_baseline,
            'simulated': hemo_new,
            'deltas': deltas,
        }


# ═══════════════════════════════════════════════════════════════════
# UTILITY: Pretty Print
# ═══════════════════════════════════════════════════════════════════

def print_banner(title: str, width: int = 65):
    """Print a formatted section banner."""
    print("=" * width)
    print(f"  {title}")
    print("=" * width)

def print_complete(section: str):
    """Print section completion message."""
    print(f"\n[{section}] ✅")
    print("=" * 65)


if __name__ == '__main__':
    # Self-test
    print("Patient Intelligence Engine — Module Test")
    env = detect_environment()
    print(f"  Environment: {env}")
    
    try:
        paths = get_paths()
        print(f"  Base dir: {paths['BASE_DIR']}")
        print(f"  Paths loaded: {len(paths)} entries")
    except Exception as e:
        print(f"  Path detection skipped: {e}")
    
    # Test GuidelineMapper
    for risk in [0.03, 0.06, 0.12, 0.25]:
        result = GuidelineMapper.classify(risk)
        print(f"  Risk {risk:.0%} → {result['acc_aha_category']}")
    
    print("\n✅ Module test complete")
