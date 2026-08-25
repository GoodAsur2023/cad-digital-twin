# Precision Cardiology Intelligence Platform: India-Specific CAD Digital Twin
### Multi-Component Machine Learning, Kitware Pulse Physiology Simulation, Genomics, and Explainable AI

[![Integrity Gate](https://img.shields.io/badge/NB12%20Integrity%20Gate-26%2F26%20PASS%20(100%25)-success)](#-master-26-point-integrity-gate)
[![Pulse Version](https://img.shields.io/badge/Kitware%20Pulse-v4.3.2%20C--API-blue)](#-mechanistic-physiological-simulation-pulsephysio)
[![Genomics](https://img.shields.io/badge/GenomeIndia-9%2C768%20Whole%20Genomes-purple)](#-genomic-architecture--single-source-of-truth)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-informational)](#-quickstart--installation)

---

## 📌 Executive Summary

Cardiovascular risk stratification in South Asian populations suffers from Eurocentric risk score miscalibration and lack of mechanistic multi-organ integration. This project delivers a **hybrid Counterfactual State-Transition Digital Twin ($S_t \to S_t'$) for Coronary Artery Disease (CAD) risk assessment and model-informed counterfactual intervention planning** tailored specifically to the Indian population.

### Key Architectural Pillars:
1. **Genomics (Single Source of Truth)**: GenomeIndia Project (9,768 whole genomes) harmonized across a canonical 40,079-variant map for **PGS000116** (40,067 direct allele matches, 12 non-palindromic strand flips, 0 proxies) combining 21,767 observed TSV frequencies (54.31%) and 18,312 calibrated South-Asian prior frequencies under $\text{Beta}(2.2, 2.0)$ (45.69%).
2. **Clinical Machine Learning**: Multi-tier gradient boosting architecture separating a **Baseline Clinical Feature Model** (AUC = **0.8595**, excluding exercise ST-depression) from an **Exercise-ST-Augmented Diagnostic Model** (AUC = **0.8845**, $\Delta\text{AUC} = +0.0250$), fused into a **Clinical Staged Fusion Ensemble** ($0.70 P_{\text{diag}} + 0.30 P_{\text{base}}$, AUC = **0.8938**, Brier = **0.1336**, ECE = **0.0792**).
3. **Mechanistic Physiology (PulsePhysio)**: Native **Kitware Pulse Physiology Engine v4.3.2 C-API (`libPulseC.dll`)** whole-body simulation across 238 CAD patients $\times$ 4 intervention scenarios (952 total runs), demonstrating a mean cardiac workload reduction of **−9.49%**.
4. **Explainability & Decision Support**: Decoupled TreeSHAP feature attribution (100% computed across empirical Clinical [82.3%] and Lifestyle [13.3%] features) with external genetic prior context shift and ACC/AHA decision mapping.
5. **Rigorous Quality Gate**: Automated 26-Point Master Integrity Gate ([`NB12`](NoteBooks/PY%20format/nb12_methodology_audit.py)) validating **26/26 assertions (100.0% PASS)** across 14 actively recomputed checks, 8 artifact verifications, and 4 scope declarations.

---

## 📂 Repository Structure

```
.
├── NoteBooks/                         # Core computational pipelines
│   ├── nb1_preprocessing_70k_FIXED.ipynb
│   ├── nb2_preprocessing_1190_clinical_FIXED.ipynb
│   ├── nb3_genome_preprocessing_FIXED.ipynb
│   ├── nb4_prs_score_computation_FIXED.ipynb
│   ├── nb5_model_training_lifestyle_FIXED.ipynb
│   ├── nb6_model_training_clinical.ipynb
│   ├── nb7_genetic_integration.ipynb
│   ├── nb8_calibration_explainability.ipynb
│   ├── nb9_digital_twin_counterfactual_revised.ipynb
│   ├── nb10_pulse_physio.ipynb
│   └── PY format/                    # Standalone Python scripts & integrity gates
│       ├── nb1_preprocessing_70k_FIXED.py ... nb10_pulsephysio_simulation.py
│       ├── nb12_methodology_audit.py  # Master 26-Point Integrity Gate
│       ├── patient_intelligence_engine.py
│       ├── pgs_catalog_ablation_engine.py
│       └── train_prediagnostic_vs_diagnostic.py
│
├── Outputs/                           # Generated models, reports, and data splits
│   ├── Clinical/                      # Train/test splits, scalers, fusion weight provenance
│   ├── Lifestyle/                     # 70k lifestyle train/test splits
│   ├── Genetics/                      # 40k canonical table, gene/pathway aggregations, GIE profile
│   ├── Models/                        # Calibrated ML pipelines (.pkl)
│   ├── Pulse/                         # Simulation results & literature reference JSON
│   ├── Digital_Twin/                  # Patient states, counterfactuals, sanity check outputs
│   ├── Integrated/                    # DCA tables, multimodal benchmarks
│   ├── Explainability/                # TreeSHAP value arrays & domain attributions
│   ├── Figures/                       # High-resolution publication charts & ROC curves
│   └── Reports/                       # 7 Academic reports + methodology audit JSON
│
├── Data/                              # Primary dataset files
│   └── Raw/                           # Cleveland, Hungarian, and 70k lifestyle CSVs
│
├── GenomeIndiaSummary/                # 22 canonical GenomeIndia chromosome TSVs
│   └── 9768GI_SummaryStats/           # GI_chr1.tsv ... GI_chr22.tsv
│
├── PGS CATALOGS/                      # Standardized PGS scoring files
│   ├── PGS000116/                     # Primary 40,079-variant catalog
│   ├── PGS002809/                     # 206 Lead GWAS hits
│   ├── PGS003725/                     # 1.3M LDpred2 sensitivity candidate
│   └── PGS004696/                     # 1.3M PRS-CSx sensitivity candidate
│
├── Pulse Physio Integration/          # Official Kitware Pulse v4.3.2 C-API Engine
│   ├── bin/                           # libPulseC.dll, data/ (substances, compounds, patients)
│   └── ReadMe.md
│
├── Supplementary_Materials/           # Non-executable references, guidelines & review logs
│   ├── Academic_Literature/          # Reference research papers (PDFs)
│   ├── Capstone_Guidelines/          # University capstone rubric, guidelines, docx templates
│   ├── Review_Transcripts/           # External review conversation logs (Stages 1–7)
│   ├── Presentation_Slides/          # Phase 2 presentation decks & evaluation slides
│   └── Design_Context/               # Early UI wireframes, diagrams & context notes
│
├── requirements.txt                   # Complete Python dependencies
├── .gitignore                         # Production gitignore rules
└── README.md                          # Platform documentation
```

---

## ⚡ Quickstart & Installation

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/your-username/cad-digital-twin.git
cd cad-digital-twin

# Create virtual environment
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Verify System Integrity Gate
Run the automated 26-Point Master Integrity Gate to verify reproducibility across all tiers:
```bash
python "NoteBooks/PY format/nb12_methodology_audit.py"
```

---

## 📊 Canonical Model Benchmark Matrix

| Model Tier | Cohort (N) | Target Variable | Test AUC (95% CI) | Brier Loss (95% CI) | Standard 10-Bin ECE (95% CI) | Role |
|---|:---:|---|:---:|:---:|:---:|---|
| **Lifestyle Only (XGBoost)** | 13,727 | `CVD_diagnosis` | **0.8061** [0.7992, 0.8135] | **0.1784** [0.1750, 0.1816] | **0.0122** [0.0090, 0.0199] | Behavioral screening |
| **Baseline Clinical Feature Model** | 238 | `CAD >50%` | **0.8595** [0.8134, 0.9029] | **0.1549** [0.1332, 0.1763] | **0.0596** [0.0561, 0.1254] | Routine clinical intake |
| **Exercise-ST-Augmented Diagnostic Model** | 238 | `CAD >50%` | **0.8845** [0.8433, 0.9242] | **0.1341** [0.1086, 0.1601] | **0.0549** [0.0508, 0.1146] | Stress-test confirmation |
| **Clinical Staged Fusion Ensemble** | 238 | `CAD >50%` | **0.8938** [0.8530, 0.9303] | **0.1336** [0.1117, 0.1560] | **0.0792** [0.0686, 0.1331] | Primary validated predictor |
| **Genetic Context Sensitivity ($\lambda=0.15$)** | 238 | `CAD >50%` | **0.8938** [0.8530, 0.9303] | **0.1398** [0.1205, 0.1595] | **0.1083** [0.0857, 0.1577] | Prior sensitivity check |

---

## 📑 Core Academic Reports

The full findings, technical appendix, ablation deep-dive, and paper-ready supplement are maintained in [`Outputs/Reports/`](Outputs/Reports/):
1. [`01_Executive_Summary_Report.md`](Outputs/Reports/01_Executive_Summary_Report.md) — Comprehensive high-level synthesis.
2. [`02_Technical_Appendix.md`](Outputs/Reports/02_Technical_Appendix.md) — Complete mathematical and statistical derivations.
3. [`03_PulsePhysio_Integration_Report.md`](Outputs/Reports/03_PulsePhysio_Integration_Report.md) — Hemodynamic translation and literature benchmarks.
4. [`04_Ablation_Study_Deep_Dive.md`](Outputs/Reports/04_Ablation_Study_Deep_Dive.md) — 4-catalog PRS comparison and uncertainty quantification.
5. [`05_Digital_Twin_Validation_Report.md`](Outputs/Reports/05_Digital_Twin_Validation_Report.md) — State-transition engine and 13 categorized sanity tests.
6. [`06_Gene_Level_Risk_Report.md`](Outputs/Reports/06_Gene_Level_Risk_Report.md) — 39 candidate gene loci, pathway contributions, and CPIC guidelines.
7. [`07_Paper_Ready_Supplement.md`](Outputs/Reports/07_Paper_Ready_Supplement.md) — Publication-ready supplementary materials with tables S1–S5.

---

## 🛡️ Master 26-Point Integrity Gate

```
==========================================================================================
  NB12 — MASTER 26-POINT METHODOLOGY INTEGRITY & REPRODUCIBILITY GATE
  Precision Cardiology Intelligence Platform | CAD_DT_Final (Stage 7 Live Recomputation)
==========================================================================================
  INTEGRITY GATE SUMMARY: 26/26 ASSERTIONS PASSED (100.0%)
  Verification Classes:        14 Actively Recomputed | 8 Artifact Verified | 4 Scope Declared
  Internal Reproducibility:    PASS
  External Validation:         NOT_PERFORMED (Requires prospective South Asian cohort)
  Deployment Scope:            RESEARCH_PROTOTYPE_ONLY
  Report saved:                Outputs/Reports/methodology_audit_report.json
==========================================================================================
```

---

## ⚖️ Non-Causal Implementation Disclaimer

> **Important**: This system is a research prototype. Model-based counterfactual intervention rankings are simulations computed via statistical model re-evaluation and Kitware Pulse hemodynamic translation; they **do not represent causal treatment effect estimates or direct clinical prescribing directives**. Prospective validation in South Asian clinical cohorts is required prior to translational bedside deployment.

---
*Developed for UE23CS320B Capstone Phase 2. All artifacts and metrics verified.*
