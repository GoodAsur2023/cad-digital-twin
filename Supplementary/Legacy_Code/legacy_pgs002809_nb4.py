# Generated from: nb4_prs_score_computation_FIXED.ipynb
# Converted at: 2026-06-18T05:23:43.297Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

# # 🧬 Notebook 4 — Polygenic Score (prs) Computation
# ## Population-Expected CVD Genetic Risk from Indian Ancestry Data
# ### Primary Production Score: PGS000116 (40,079 SNPs, lassosum) -> Outputs/Genetics/pgs000116_genomeindia_harmonized.csv
# ### Baseline Comparator: PGS002809 (182 SNPs, GWAS Hits) -> harmonized_genetic_map.csv
# 
# ---
# 
# ## 📂 File Structure & I/O Contract
# 
# ```
# CVD_DigitalTwin_Project/
# ├── data/
# │   └── processed/
# │       └── genetics/
# │           ├── harmonized_genetic_map.csv     ← INPUT  (182 SNPs, from Notebook 3)
# │           └── dropped_snps_audit_log.csv     ← INPUT  (for reference only)
# └── outputs/
#     └── genetics/
#         ├── prs_population_score.csv           ← OUTPUT (scalar prs + metadata)
#         ├── per_snp_contribution.csv           ← OUTPUT (182-row per-SNP breakdown)
#         └── prs_feature_vector.pkl             ← OUTPUT (dict for Notebook 7 fusion)
# ```
# 
# ---
# 
# ## 📌 What this notebook does
# 
# | Section | Task |
# |---------|------|
# | 1 | Load & validate harmonized genetic map |
# | 2 | Compute population-expected prs (Hardy-Weinberg formula) |
# | 3 | Normalize and contextualize the prs scalar |
# | 4 | SNP contribution analysis and paper figures |
# | 5 | Sensitivity analysis (±10% allele frequency perturbation) |
# | 6 | Export all outputs |
# 
# ---
# 
# ## 🎯 Scientific Background
# 
# A **Polygenic Score (prs)** — also called a Polygenic Risk Score (PRS) — aggregates the
# effects of many genetic variants into a single number representing an individual's (or
# population's) inherited predisposition to a disease. The standard formulation, established
# by Purcell et al. (2009) and formalized in Choi et al. (2020, *Nature Protocols*), is:
# 
# $$\text{prs} = \sum_{j=1}^{M} \hat{\beta}_j \cdot g_j$$
# 
# where $M$ is the number of SNPs, $\hat{\beta}_j$ is the GWAS effect size (log-odds ratio),
# and $g_j \in \{0, 1, 2\}$ is the individual's allelic dosage at SNP $j$.
# 
# Since we have **population-level** allele frequencies (not individual genotypes), we use
# the **expected dosage under Hardy-Weinberg Equilibrium (HWE)**. For a diploid organism,
# the expected allelic dosage for a risk allele with population frequency $p$ is:
# 
# $$E[g_j] = 2p_j$$
# 
# This is the standard HWE-based population expectation. See:
# - Choi et al. (2020) *Nature Protocols* — PRS construction tutorial
# - Martin et al. (2019) *Nature Genetics* — population transferability of prs
# - Khera et al. (2018) *Nature Genetics* — prs for coronary artery disease
# 
# Therefore the **population-expected prs** for Indian ancestry is:
# 
# $$\text{prs}_{\text{Indian}} = \sum_{j=1}^{M} 2 \cdot p_j^{\text{Indian}} \cdot \hat{\beta}_j$$
# 
# This represents the **expected genetic risk score for a randomly drawn individual**
# from the Indian ancestry population — not a specific person's score.
# 
# ---
# 
# ## ⚠️ Expected Output Summary (for debugging)
# 
# At the end of this notebook you should see approximately:
# - **182 SNPs** loaded from harmonized map
# - **Population prs scalar** in the range **~8–15** (raw, un-normalized), depending on the
#   exact effect weights and allele frequencies
# - **Top 10 SNPs** with the largest per-SNP contribution clearly identified
# - Sensitivity analysis showing prs varies by roughly **±5–10%** under ±10% frequency
#   perturbation (demonstrating robustness)
# - **3 output files** confirmed saved


# ---
# # Section 1 — Environment Setup & Data Loading
# 
# ## Why validate inputs before computing?
# The prs formula is a sum of products — any NaN in `effect_weight_beta` or
# `indian_ancestry_risk_allele_freq` will silently propagate to the final scalar,
# making it impossible to detect the source of error downstream. We assert-check
# every critical column before proceeding.
# 
# ### ✅ Expected state after this section:
# - `harmonized_df` has **182 rows** and **9 columns**
# - Zero null values in `effect_weight_beta` and `indian_ancestry_risk_allele_freq`
# - Allele frequencies all in (0, 1) — frequencies of exactly 0 or 1 were filtered
#   in Notebook 3 by the MAF filter


import os
import sys
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# ── Dual-Environment Support (Colab + Local) ────────────────
try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)
    BASE_DIR = "/content/drive/MyDrive/CAD_DT_Final/"
    print('✅ Google Colab detected — Drive mounted')
except ImportError:
    _candidates = [r'E:\Capstone', r'e:\Capstone']
    BASE_DIR = None
    for _p in _candidates:
        if os.path.isdir(_p):
            BASE_DIR = _p.replace('\\', '/') + '/'
            break
    if BASE_DIR is None:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace('\\', '/') + '/'
    print(f'ℹ️  Local environment — BASE_DIR: {BASE_DIR}')

# ── Add parent dir to sys.path for shared module ────────────
NB_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else '.'
if NB_DIR not in sys.path:
    sys.path.insert(0, NB_DIR)

# ── Paths (UPDATED TO SUPPORT BOTH ENVIRONMENTS) ──────────
GENETICS_IN_DIR  = BASE_DIR + "Outputs/Genetics/Comparators/PGS002809/"   # NB3 output
GENETICS_OUT_DIR = BASE_DIR + "Outputs/Genetics/Comparators/PGS002809/"   # NB4 also writes here
FIGURES_DIR      = BASE_DIR + "Outputs/Figures/"

HARMONIZED_MAP_PATH = GENETICS_IN_DIR  + "harmonized_genetic_map.csv"
PRS_OUT_PATH        = GENETICS_OUT_DIR + "prs_population_score.csv"
PER_SNP_OUT_PATH    = GENETICS_OUT_DIR + "per_snp_contribution.csv"
FEATURE_VEC_OUT     = GENETICS_OUT_DIR + "prs_feature_vector.pkl"
GENE_CONTRIB_PATH   = GENETICS_OUT_DIR + "gene_level_contributions.csv"
GI_PROFILE_PATH     = GENETICS_OUT_DIR + "genetic_intelligence_profile.json"

# ── Create folders (safe, no duplication risk) ───────────────
os.makedirs(GENETICS_OUT_DIR, exist_ok=True)
os.makedirs(FIGURES_DIR, exist_ok=True)

print("✅ Paths initialized")
print("Input :", HARMONIZED_MAP_PATH)
print("Output:", GENETICS_OUT_DIR)

# ── Load Data ───────────────────────────────────────────────────
assert os.path.isfile(HARMONIZED_MAP_PATH), f"❌ File not found: {HARMONIZED_MAP_PATH}"

df = pd.read_csv(HARMONIZED_MAP_PATH)

print(f"\n📊 Loaded harmonized map: {df.shape}")
print(df.head())

# ── Validation ──────────────────────────────────────────────────
REQUIRED_COLS = [
    'rsID', 'chromosome', 'position_grch',
    'effect_allele', 'effect_weight_beta',
    'gi_reference_allele', 'gi_alternate_allele',
    'gi_alt_allele_frequency', 'indian_ancestry_risk_allele_freq'
]

missing = [c for c in REQUIRED_COLS if c not in df.columns]
assert not missing, f"❌ Missing columns: {missing}"

# ── Validation: SNP count, nulls, frequency range ───────────────
assert len(df) > 150, f"❌ Only {len(df)} SNPs — expected > 150. Check NB3 output."
assert df['effect_weight_beta'].isnull().sum() == 0, "❌ Nulls in effect_weight_beta"
assert df['indian_ancestry_risk_allele_freq'].isnull().sum() == 0, "❌ Nulls in indian_ancestry_risk_allele_freq"

freq = df['indian_ancestry_risk_allele_freq']
assert (freq > 0).all() and (freq < 1).all(), (
    f"❌ Frequencies out of (0,1): min={freq.min():.6f}  max={freq.max():.6f}"
)

print(f"✅ Validation passed — {len(df)} SNPs, no nulls, frequencies in (0,1)")

# Working copy
harmonized_df = df.copy()

# ---
# # Section 2 — Compute Population-Expected prs (Hardy-Weinberg Formula)
# 
# ## Scientific justification for the formula
# 
# The standard prs formula for an **individual** is (Choi et al., 2020):
# $$\text{prs}_i = \sum_{j=1}^{M} \hat{\beta}_j \cdot g_{ij}$$
# 
# where $g_{ij} \in \{0, 1, 2\}$ is the dosage of the risk allele at SNP $j$ for
# individual $i$. Since we do not have individual genotypes, we use the
# **population expectation** of the dosage under Hardy-Weinberg Equilibrium:
# 
# $$E[g_j] = 0 \cdot (1-p_j)^2 + 1 \cdot 2p_j(1-p_j) + 2 \cdot p_j^2 = 2p_j$$
# 
# This simplification is exact under HWE (Hardy & Weinberg, 1908), and has been
# used extensively in population-level PRS calibration studies (Martin et al., 2017;
# Duncan et al., 2019; Polygenic Risk Score Task Force, 2021).
# 
# Therefore the per-SNP contribution is:
# $$c_j = 2 \cdot p_j^{\text{Indian}} \cdot \hat{\beta}_j$$
# 
# And the total population-expected prs:
# $$\text{prs}_{\text{pop}} = \sum_{j=1}^{M} c_j$$
# 
# ### Why use Indian-ancestry allele frequencies?
# Martin et al. (2019, *Nature Genetics*) demonstrated that prs derived from
# European GWAS cohorts show significantly reduced predictive accuracy in South
# Asian and African-ancestry populations due to LD structure differences and
# population-specific allele frequency drift. By re-anchoring each SNP's dosage
# expectation to its GenomeIndia frequency, we compute the baseline risk that is
# **calibrated to the Indian population** rather than a European reference.
# 
# ### ✅ Expected state after this section:
# - `per_snp_df` has **182 rows** with columns:
#   `rsID`, `chromosome`, `effect_allele`, `indian_ancestry_risk_allele_freq`,
#   `effect_weight_beta`, `expected_dosage`, `per_snp_contribution`
# - `population_prs` is a **single positive scalar** (typical range: ~8–15 for
#   a 182-SNP LDL/CVD score with moderate effect sizes)
# - All `per_snp_contribution` values should be positive (since all effect
#   weights in PGS002809 are positive risk-increasing alleles)


print("=" * 65)
print("  SECTION 2: Population-Expected PRS Computation")
print("=" * 65)

# Always use df consistently
df = harmonized_df.copy()

p    = df['indian_ancestry_risk_allele_freq'].values
beta = df['effect_weight_beta'].values

# prs_contribution = 2 * p_indian * beta  (HWE dosage model)
df['prs_contribution'] = 2.0 * p * beta
harmonized_df['prs_contribution'] = df['prs_contribution']

prs_raw = float(df['prs_contribution'].sum())

# Per-SNP dataframe (sorted)
per_snp_df = df[[
    'rsID', 'chromosome', 'position_grch',
    'effect_allele', 'effect_weight_beta',
    'indian_ancestry_risk_allele_freq', 'prs_contribution'
]].copy().sort_values('prs_contribution', ascending=False).reset_index(drop=True)

print(f"\n📐 Formula: prs = Σ (2 × p_indian × beta)")

print(f"\n📊 Computation Summary:")
print(f"   Total SNPs used              : {len(per_snp_df)}")
print(f"   Mean allele frequency        : {df['indian_ancestry_risk_allele_freq'].mean():.4f}")
print(f"   Mean effect weight (beta)    : {df['effect_weight_beta'].mean():.4f}")
print(f"   Mean per-SNP contribution    : {df['prs_contribution'].mean():.6f}")
print(f"   Max per-SNP contribution     : {df['prs_contribution'].max():.6f}")
print(f"   Min per-SNP contribution     : {df['prs_contribution'].min():.6f}")

print()
print(f"   ╔══════════════════════════════════════╗")
print(f"   ║  PRS_RAW = {prs_raw:.6f}{'':>20}║")
print(f"   ╚══════════════════════════════════════╝")

print(f"\n🔝 Top 10 SNPs by contribution:")
print(per_snp_df.head(10)[[
    'rsID','chromosome','effect_allele',
    'indian_ancestry_risk_allele_freq',
    'effect_weight_beta','prs_contribution'
]].to_string(index=False))

print(f"\n[SECTION 2 COMPLETE] ✅ prs_raw = {prs_raw:.6f}")

# ---
# # Section 3 — Monte Carlo Simulation for PRS Confidence Interval
# 
# Allele frequencies estimated from GenomeIndia (n=9,768) carry sampling uncertainty.
# Monte Carlo simulation propagates this uncertainty through the PRS formula to produce
# a 95% confidence interval around the population-expected PRS.
# 
# Each SNP's allele frequency is modelled as Beta(α, β) where α = p×n and β = (1−p)×n,
# consistent with the conjugate prior for binomial proportions.
# 


print("=" * 65)
print("  SECTION 3: Monte Carlo PRS Confidence Interval")
print("=" * 65)

N_SIM         = 10_000
GI_SAMPLE_N   = 9_768
np.random.seed(42)

# ALWAYS use df (same object from Section 2)
p_nominal = df['indian_ancestry_risk_allele_freq'].values
beta_vals = df['effect_weight_beta'].values

# Beta parameters
alpha_params = p_nominal * GI_SAMPLE_N
beta_params  = (1.0 - p_nominal) * GI_SAMPLE_N

# Sample frequencies
sampled_freqs = np.random.beta(
    alpha_params,
    beta_params,
    size=(N_SIM, len(p_nominal))
)

# Compute PRS
prs_simulations = (2.0 * sampled_freqs * beta_vals).sum(axis=1)

prs_mean_mc = float(np.mean(prs_simulations))
ci_lower    = float(np.percentile(prs_simulations, 2.5))
ci_upper    = float(np.percentile(prs_simulations, 97.5))

print(f"\n📊 Monte Carlo Summary:")
print(f"   prs_raw      : {prs_raw:.6f}")
print(f"   prs_mean_mc  : {prs_mean_mc:.6f}")
print(f"   95% CI       : [{ci_lower:.6f}, {ci_upper:.6f}]")

# Plot
fig, ax = plt.subplots(figsize=(9, 5))
ax.hist(prs_simulations, bins=80, edgecolor='white', alpha=0.85)
ax.axvline(prs_raw,     linewidth=2, label=f'prs_raw = {prs_raw:.4f}')
ax.axvline(prs_mean_mc, linestyle='--', label=f'MC mean = {prs_mean_mc:.4f}')
ax.axvline(ci_lower,    linestyle=':', label=f'95% CI')
ax.axvline(ci_upper,    linestyle=':')

ax.set_xlabel('PRS')
ax.set_ylabel('Count')
ax.set_title('Monte Carlo PRS Distribution')
ax.legend()
plt.tight_layout()

mc_fig_path = FIGURES_DIR + "nb4_monte_carlo_prs_distribution.png"

plt.tight_layout()
plt.savefig(mc_fig_path, dpi=300, bbox_inches='tight')
plt.show()

print(f"✅ Monte Carlo figure saved: {mc_fig_path}")
print("[SECTION 3 COMPLETE] ✅")

# ---
# # Section 4 — SNP Contribution Analysis & Paper Figures
# 
# ## Why visualize per-SNP contributions?
# 
# The per-SNP breakdown serves two purposes:
# 1. **Scientific interpretability**: Identifying which specific SNPs and genomic
#    regions drive the population-level genetic risk is a standard component of
#    polygenic score papers (Inouye et al., 2018, *JACC*; Khera et al., 2018).
# 2. **Quality control**: A handful of SNPs dominating the score can indicate
#    data quality issues; a smooth contribution distribution suggests a
#    well-calibrated score.
# 
# The SNPs with largest effect weights in PGS002809 map to known CVD loci
# including the *PCSK9* region (chr1:55M), *LPA* (chr6:160M), and chromosome
# 9p21 — all established in GWAS of coronary artery disease (Deloukas et al.,
# 2013; Nikpay et al., 2015).
# 
# ### ✅ Expected state after this section:
# - Bar chart saved to `outputs/figures/` — top contributors visible
# - Chromosome distribution plot showing spread across the genome
# - Top 10 table printed with rsID, chromosome, and contribution


print("=" * 65)
print("  SECTION 4: SNP Contribution Analysis & Figures")
print("=" * 65)

# ── Safety ─────────────────────────────────────
assert 'per_snp_df' in globals(), "❌ Run Section 2 first"

plt.rcParams.update({
    'figure.dpi': 150,
    'font.size': 11
})

# ── Top 20 SNPs (by absolute contribution) ─────
top20 = per_snp_df.copy().sort_values(
    'prs_contribution', key=np.abs, ascending=False
).head(20)

fig, ax = plt.subplots(figsize=(12, 7))

bars = ax.barh(
    y=range(len(top20)),
    width=top20['prs_contribution'].values
)

ax.set_yticks(range(len(top20)))
ax.set_yticklabels(
    [f"{r['rsID']} (chr{r['chromosome']})" for _, r in top20.iterrows()],
    fontsize=9
)
ax.invert_yaxis()

ax.set_xlabel('PRS Contribution (2 × p × β)')
ax.set_title(f'Top 20 SNP Contributions (PRS = {prs_raw:.4f})')

# annotate bars
for bar, (_, row) in zip(bars, top20.iterrows()):
    ax.text(
        bar.get_width(),
        bar.get_y() + bar.get_height()/2,
        f"{row['prs_contribution']:.4f}",
        va='center',
        fontsize=8
    )

plt.tight_layout()
fig1_path = FIGURES_DIR + "nb4_top20.png"
plt.savefig(fig1_path, dpi=300, bbox_inches='tight')
plt.show()

print(f"✅ Saved: {fig1_path}")

# ── Distribution ───────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# histogram
axes[0].hist(per_snp_df['prs_contribution'], bins=30)
axes[0].axvline(per_snp_df['prs_contribution'].mean(), linestyle='--')
axes[0].set_title('Contribution Distribution')

# chromosome aggregation
chr_contrib = (
    per_snp_df.groupby('chromosome')['prs_contribution']
    .sum()
    .reset_index()
)

axes[1].bar(
    chr_contrib['chromosome'].astype(str),
    chr_contrib['prs_contribution']
)
axes[1].set_title('Chromosome Contribution')

plt.tight_layout()
fig2_path = FIGURES_DIR + "nb4_distribution.png"
plt.savefig(fig2_path, dpi=300, bbox_inches='tight')
plt.show()

print(f"✅ Saved: {fig2_path}")

# ── Top 10 Table ───────────────────────────────
print("\n🔝 Top 10 SNPs:")

top10 = per_snp_df.copy().sort_values(
    'prs_contribution', key=np.abs, ascending=False
).head(10)

top10['pct'] = (top10['prs_contribution'] / prs_raw * 100).round(2)

print(top10[[
    'rsID','chromosome','effect_allele',
    'indian_ancestry_risk_allele_freq',
    'effect_weight_beta','prs_contribution','pct'
]].to_string(index=False))

print(f"\nTop 10 contribute {top10['prs_contribution'].sum() / prs_raw * 100:.1f}%")

print("[SECTION 4 COMPLETE] ✅")

# ---
# # Section 4.5 — Gene-Level PRS Aggregation & Variant Confidence
#
# ## Why aggregate PRS by gene?
#
# Individual SNP rsIDs are meaningless to clinicians. Gene-level aggregation
# transforms the PRS from a "bag of SNPs" into a biologically interpretable
# breakdown: "28% of your genetic risk comes from PCSK9, 15% from LDLR..."
#
# This section uses the gene annotations from the enhanced NB3 output to:
# 1. Group SNPs by gene symbol
# 2. Sum per-gene PRS contributions
# 3. Compute a Variant Confidence Score
# 4. Generate gene-level visualizations
#
# ### ✅ Expected state after this section:
# - `gene_contrib_df` with gene-level PRS breakdown
# - Gene contribution bar chart saved
# - Confidence score computed


print("=" * 65)
print("  SECTION 4.5: Gene-Level PRS Aggregation & Confidence")
print("=" * 65)

# Check if gene annotations are available
_has_genes = 'gene_symbol' in df.columns and df['gene_symbol'].notna().any()

if _has_genes:
    _gene_df = df.copy()
    _gene_df['gene_symbol'] = _gene_df['gene_symbol'].fillna('INTERGENIC')
    
    # ── Gene-level aggregation ─────────────────────────────
    gene_contrib_df = (
        _gene_df.groupby('gene_symbol')
        .agg(
            n_snps=('rsID', 'count'),
            gene_prs=('prs_contribution', 'sum'),
            avg_beta=('effect_weight_beta', 'mean'),
            avg_freq=('indian_ancestry_risk_allele_freq', 'mean'),
        )
        .reset_index()
    )
    gene_contrib_df['gene_pct'] = (gene_contrib_df['gene_prs'] / prs_raw * 100).round(2)
    gene_contrib_df = gene_contrib_df.sort_values('gene_prs', ascending=False).reset_index(drop=True)
    
    print(f"\n🧬 Gene-Level PRS Breakdown:")
    print(f"   Unique genes  : {len(gene_contrib_df)}")
    print(f"   Top 10 genes by contribution:")
    print(gene_contrib_df.head(10)[['gene_symbol', 'n_snps', 'gene_prs', 'gene_pct']].to_string(index=False))
    
    top_10_pct = gene_contrib_df.head(10)['gene_pct'].sum()
    print(f"\n   Top 10 genes account for {top_10_pct:.1f}% of total PRS")
    
    # ── Gene contribution bar chart ───────────────────────
    top_genes_plot = gene_contrib_df.head(15)
    fig, ax = plt.subplots(figsize=(12, 7))
    colors = ['#1565C0' if not str(g).startswith('INTERGENIC') else '#9E9E9E' 
              for g in top_genes_plot['gene_symbol']]
    bars = ax.barh(
        y=range(len(top_genes_plot)),
        width=top_genes_plot['gene_prs'].values,
        color=colors, edgecolor='white'
    )
    ax.set_yticks(range(len(top_genes_plot)))
    ax.set_yticklabels(
        [f"{r['gene_symbol']} ({r['n_snps']} SNPs)" 
         for _, r in top_genes_plot.iterrows()],
        fontsize=9
    )
    ax.invert_yaxis()
    ax.set_xlabel('Gene PRS Contribution (Σ 2×p×β)')
    ax.set_title(f'Top 15 Gene Contributions to Population PRS ({prs_raw:.4f})')
    for bar, (_, row) in zip(bars, top_genes_plot.iterrows()):
        ax.text(bar.get_width(), bar.get_y() + bar.get_height()/2,
                f" {row['gene_pct']:.1f}%", va='center', fontsize=8)
    plt.tight_layout()
    gene_fig_path = FIGURES_DIR + "nb4_gene_contributions.png"
    plt.savefig(gene_fig_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ Gene contribution chart saved: {gene_fig_path}")
    
    # Save gene contributions
    gene_contrib_df.to_csv(GENE_CONTRIB_PATH, index=False)
    print(f"✅ Gene contributions saved: {GENE_CONTRIB_PATH}")
else:
    print("  ⚠️ gene_symbol column not available — skipping gene aggregation")
    print("     Run NB3 with GI-DB annotation to enable this feature")
    gene_contrib_df = pd.DataFrame()

# ── Variant Confidence Score ─────────────────────────────
print("\n── Variant Confidence Score ─────────────────────")

n_total_pgs = 206  # Total SNPs in PGS002809 before harmonization
n_matched = len(df)
match_rate = n_matched / n_total_pgs

n_with_gene = df['gene_symbol'].notna().sum() if 'gene_symbol' in df.columns else 0
n_with_consequence = df['consequence_type'].notna().sum() if 'consequence_type' in df.columns else 0
n_with_clinvar = df['clinvar_significance'].notna().sum() if 'clinvar_significance' in df.columns else 0

annotation_rate = n_with_gene / n_matched if n_matched > 0 else 0
consequence_rate = n_with_consequence / n_matched if n_matched > 0 else 0
clinvar_rate = n_with_clinvar / n_matched if n_matched > 0 else 0

# Composite confidence (weighted)
confidence_composite = (
    0.50 * match_rate +
    0.25 * annotation_rate +
    0.15 * consequence_rate +
    0.10 * min(clinvar_rate * 5, 1.0)  # ClinVar is sparse, scale up
)

if confidence_composite >= 0.90:
    confidence_tier = 'HIGH'
elif confidence_composite >= 0.70:
    confidence_tier = 'MEDIUM'
else:
    confidence_tier = 'LOW'

confidence_result = {
    'variant_match_rate': round(match_rate, 4),
    'gene_annotation_rate': round(annotation_rate, 4),
    'consequence_annotation_rate': round(consequence_rate, 4),
    'clinvar_annotation_rate': round(clinvar_rate, 4),
    'composite_confidence': round(confidence_composite, 4),
    'tier': confidence_tier,
    'n_matched': n_matched,
    'n_total_pgs': n_total_pgs,
}

print(f"   Variant match rate      : {match_rate:.1%} ({n_matched}/{n_total_pgs})")
print(f"   Gene annotation rate    : {annotation_rate:.1%}")
print(f"   Consequence annotation  : {consequence_rate:.1%}")
print(f"   ClinVar annotation      : {clinvar_rate:.1%}")
print(f"   ╔══════════════════════════════════════╗")
print(f"   ║  Confidence: {confidence_composite:.2%} ({confidence_tier}){'':>10}║")
print(f"   ╚══════════════════════════════════════╝")

print("\n[SECTION 4.5 COMPLETE] ✅")

# ---
# # Section 5 — Sensitivity Analysis
# 
# ## Why run a sensitivity analysis on allele frequencies?
# 
# The GenomeIndia allele frequencies are estimated from **9,768 individuals**.
# While this is a large cohort, sampling uncertainty means the true population
# frequency $p_j$ is not known exactly. The 95% confidence interval for a
# frequency estimate $\hat{p}$ from $n$ samples is approximately
# $\hat{p} \pm 1.96\sqrt{\hat{p}(1-\hat{p})/(2n)}$ (for diploid data).
# 
# We test robustness by perturbing all allele frequencies by a multiplicative
# factor $\delta \in [-10\%, +10\%]$, clamping to (0.01, 0.99) to preserve
# biologically valid frequencies.
# 
# **If the prs is stable under these perturbations**, it means our score is not
# sensitive to minor inaccuracies in the frequency estimates — a key robustness
# claim for the paper. This approach mirrors the sensitivity analysis performed
# in Inouye et al. (2018, *JACC Cardiology*) for their coronary artery disease PRS.
# 
# ### ✅ Expected state after this section:
# - prs values across ±10% perturbations plotted
# - Total variation across the range should be **< 20%** of the nominal prs
#   (demonstrating robustness)
# - The nominal prs falls at the center of the sensitivity band


print("=" * 65)
print("  SECTION 5: Sensitivity Analysis — Allele Frequency Perturbation")
print("=" * 65)

# ── Safety ─────────────────────────────────────
assert 'prs_raw' in globals(), "❌ Run Section 2 first"

# ── Setup ─────────────────────────────────────
deltas = np.linspace(-0.10, 0.10, 41)

nominal_freq = df['indian_ancestry_risk_allele_freq'].values
beta_values  = df['effect_weight_beta'].values

prs_at_delta = []

# ── Perturbation Loop ──────────────────────────
for delta in deltas:
    perturbed_freq = nominal_freq * (1 + delta)
    perturbed_freq = np.clip(perturbed_freq, 0.01, 0.99)

    prs_perturbed = np.sum(2 * perturbed_freq * beta_values)
    prs_at_delta.append(prs_perturbed)

prs_at_delta = np.array(prs_at_delta)

# ── Metrics ────────────────────────────────────
prs_min = prs_at_delta.min()
prs_max = prs_at_delta.max()
prs_range = prs_max - prs_min
prs_range_pct = prs_range / prs_raw * 100

print(f"\n📊 Sensitivity Results:")
print(f"   Nominal prs : {prs_raw:.6f}")
print(f"   Range       : [{prs_min:.6f}, {prs_max:.6f}]")
print(f"   Variation   : {prs_range:.6f} ({prs_range_pct:.1f}%)")

if prs_range_pct < 20:
    print("   ✅ ROBUST (<20%)")
else:
    print("   ⚠️ NOT ROBUST (>20%)")

# ── SNP Sensitivity ────────────────────────────
freq_up_10 = np.clip(nominal_freq * 1.10, 0.01, 0.99)
snp_delta = 2 * (freq_up_10 - nominal_freq) * beta_values

snp_sensitivity_df = per_snp_df.copy()
snp_sensitivity_df['freq_sensitivity'] = snp_delta

# ── Plot ──────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# PRS curve
axes[0].plot(deltas * 100, prs_at_delta)
axes[0].axhline(prs_raw, linestyle='--')
axes[0].set_xlabel("Δ Frequency (%)")
axes[0].set_ylabel("PRS")
axes[0].set_title("PRS Sensitivity Curve")

# Top sensitive SNPs
top_sensitive = snp_sensitivity_df.sort_values(
    'freq_sensitivity', key=np.abs, ascending=False
).head(15)

axes[1].barh(
    range(len(top_sensitive)),
    top_sensitive['freq_sensitivity']
)

axes[1].set_yticks(range(len(top_sensitive)))
axes[1].set_yticklabels(top_sensitive['rsID'], fontsize=8)
axes[1].invert_yaxis()
axes[1].set_title("Top Sensitive SNPs")

plt.tight_layout()
sens_path = FIGURES_DIR + "nb4_sensitivity.png"
plt.savefig(sens_path, dpi=300, bbox_inches='tight')
plt.show()

print(f"✅ Sensitivity plot saved: {sens_path}")
print("[SECTION 5 COMPLETE] ✅")

# ---
# # Section 6 — Export All Outputs
# 
# ## Output file specifications
# 
# | File | Format | Content | Used by |
# |------|--------|---------|--------|
# | `prs_population_score.csv` | CSV | Scalar prs + metadata (1 row) | Notebook 7 |
# | `per_snp_contribution.csv` | CSV | 182-row SNP breakdown | Notebook 8 (figures) |
# | `prs_feature_vector.pkl` | Pickle | Python dict with all values | Notebook 7 (fusion) |
# 
# The pickle format for `prs_feature_vector.pkl` is chosen because it preserves
# Python data types exactly (no float precision loss from CSV serialization) and
# is the same format used for the trained model objects in Notebooks 5 and 6.
# 
# ### ✅ Expected state after this section:
# - All 3 output files confirmed to exist on disk
# - `prs_population_score.csv` has exactly **1 row** and **8 columns**
# - `per_snp_contribution.csv` has exactly **182 rows** and **9 columns**
# - `prs_feature_vector.pkl` loads as a Python dict with keys:
#   `population_prs`, `prs_mean`, `prs_std`, `prs_z`, `sigmoid_prs`, `n_snps`


print("=" * 65)
print("  SECTION 6: Export All Outputs")
print("=" * 65)

# ── Safety checks ───────────────────────────────────────────────
assert 'prs_raw' in globals(), "❌ prs_raw missing (run Section 2)"
assert 'prs_mean_mc' in globals(), "❌ Monte Carlo outputs missing (run Section 3)"
assert 'per_snp_df' in globals(), "❌ per_snp_df missing (run Section 2)"

# ── Output 1: prs_population_score.csv ──────────────────────
prs_score_record = pd.DataFrame([{
    'prs_raw': prs_raw,
    'prs_mean_mc': prs_mean_mc,
    'ci_lower': ci_lower,
    'ci_upper': ci_upper,
    'n_snps': len(per_snp_df),
    'confidence_composite': confidence_result['composite_confidence'],
    'confidence_tier': confidence_result['tier'],
}])

prs_score_record.to_csv(PRS_OUT_PATH, index=False)

print(f"\n✅ Saved: {PRS_OUT_PATH}")
print(prs_score_record.to_string(index=False))

# ── Output 2: per_snp_contribution.csv ──────────────────────
per_snp_export = per_snp_df.copy()

per_snp_export['pct_of_total_prs'] = (
    per_snp_export['prs_contribution'] / prs_raw * 100
)

per_snp_export['cumulative_contribution'] = (
    per_snp_export['prs_contribution'].cumsum()
)

# Include annotation columns if available
for acol in ['gene_symbol', 'consequence_type', 'impact_level',
             'clinvar_significance', 'functional_impact_weight']:
    if acol in harmonized_df.columns:
        _merge_map = harmonized_df.set_index('rsID')[acol]
        per_snp_export[acol] = per_snp_export['rsID'].map(_merge_map)

per_snp_export.to_csv(PER_SNP_OUT_PATH, index=False)

print(f"\n✅ Saved: {PER_SNP_OUT_PATH}")
print(f"   Shape: {per_snp_export.shape}")

# ── Output 3: prs_feature_vector.pkl (enhanced) ────────────
prs_feature_vector = {
    'prs_raw': prs_raw,
    'prs_mean_mc': prs_mean_mc,
    'ci_lower': ci_lower,
    'ci_upper': ci_upper,
    'n_snps': len(per_snp_df),
    'confidence': confidence_result,
}

# Add gene-level features if available
if not gene_contrib_df.empty:
    top_genes = gene_contrib_df.head(5)
    prs_feature_vector['top_genes'] = [
        {'gene': row['gene_symbol'], 'prs': round(float(row['gene_prs']), 6),
         'pct': float(row['gene_pct'])}
        for _, row in top_genes.iterrows()
    ]

with open(FEATURE_VEC_OUT, 'wb') as f:
    pickle.dump(prs_feature_vector, f)

print(f"\n✅ Saved: {FEATURE_VEC_OUT}")
print(f"   Keys: {list(prs_feature_vector.keys())}")

# ── Output 4: Genetic Intelligence Profile (JSON) ─────────
print("\n" + "─" * 55)
print("  Building Genetic Intelligence Profile...")
print("─" * 55)

# Annotation summary
annotation_summary = {}
if 'consequence_type' in harmonized_df.columns:
    annotation_summary['consequence_distribution'] = (
        harmonized_df['consequence_type'].fillna('unknown').value_counts().to_dict()
    )
if 'impact_level' in harmonized_df.columns:
    annotation_summary['impact_distribution'] = (
        harmonized_df['impact_level'].fillna('UNKNOWN').value_counts().to_dict()
    )
if 'clinvar_significance' in harmonized_df.columns:
    annotation_summary['clinvar_distribution'] = (
        harmonized_df['clinvar_significance'].dropna().value_counts().to_dict()
    )

# Top genes
top_genes_profile = []
if not gene_contrib_df.empty:
    for _, row in gene_contrib_df.head(10).iterrows():
        top_genes_profile.append({
            'gene': row['gene_symbol'],
            'n_snps': int(row['n_snps']),
            'contribution_prs': round(float(row['gene_prs']), 6),
            'contribution_pct': float(row['gene_pct']),
        })

# Top variants
top_variants_profile = []
for _, row in per_snp_df.head(10).iterrows():
    entry = {
        'rsID': row['rsID'],
        'chromosome': str(row['chromosome']),
        'position': int(row['position_grch']),
        'effect_allele': row['effect_allele'],
        'beta': round(float(row['effect_weight_beta']), 6),
        'indian_freq': round(float(row['indian_ancestry_risk_allele_freq']), 6),
        'prs_contribution': round(float(row['prs_contribution']), 6),
    }
    if 'gene_symbol' in per_snp_df.columns and pd.notna(row.get('gene_symbol')):
        entry['gene'] = row['gene_symbol']
    top_variants_profile.append(entry)

genetic_profile = {
    'overall_prs': round(prs_raw, 6),
    'prs_mean_mc': round(prs_mean_mc, 6),
    'prs_ci_95': [round(ci_lower, 6), round(ci_upper, 6)],
    'prs_percentile': 'population_mean',
    'n_snps_used': len(per_snp_df),
    'confidence': confidence_result,
    'top_genes': top_genes_profile,
    'top_variants': top_variants_profile,
    'population_context': 'Indian (GenomeIndia N=9768)',
    'pgs_catalog_id': 'PGS002809',
    'annotation_summary': annotation_summary,
}

with open(GI_PROFILE_PATH, 'w') as f:
    json.dump(genetic_profile, f, indent=2, default=str)

print(f"✅ Genetic Intelligence Profile saved: {GI_PROFILE_PATH}")
print(f"   Top genes: {[g['gene'] for g in top_genes_profile[:5]]}")
print(f"   Confidence: {confidence_result['tier']} ({confidence_result['composite_confidence']:.2%})")

# ── Validation ──────────────────────────────────────────────
print("\n" + "=" * 65)
print("  VALIDATION")
print("=" * 65)

# SNP count
assert len(per_snp_df) > 150, f"❌ Only {len(per_snp_df)} SNPs — expected > 150"
print(f"  ✅ SNP count: {len(per_snp_df)}")

# No nulls
for col in ['effect_weight_beta', 'indian_ancestry_risk_allele_freq']:
    n_null = harmonized_df[col].isnull().sum()
    assert n_null == 0, f"❌ {n_null} nulls in '{col}'"
print("  ✅ No nulls in critical columns")

# Frequency bounds
freq_check = harmonized_df['indian_ancestry_risk_allele_freq']
assert (freq_check > 0).all() and (freq_check < 1).all(), (
    f"❌ Frequencies out of bounds: min={freq_check.min():.6f}, max={freq_check.max():.6f}"
)
print(f"  ✅ Frequencies valid: min={freq_check.min():.4f}, max={freq_check.max():.4f}")

# Read-back CSV 1
val1 = pd.read_csv(PRS_OUT_PATH)
for col in ['prs_raw','prs_mean_mc','ci_lower','ci_upper','n_snps']:
    assert col in val1.columns, f"❌ Missing column in CSV 1: {col}"
assert abs(val1.iloc[0]['prs_raw'] - prs_raw) < 1e-8
print("  ✅ prs_population_score.csv verified")

# Read-back CSV 2
val2 = pd.read_csv(PER_SNP_OUT_PATH)
assert len(val2) == len(per_snp_df)
print(f"  ✅ per_snp_contribution.csv verified ({len(val2)} rows)")

# Read-back pickle
with open(FEATURE_VEC_OUT, 'rb') as f:
    val3 = pickle.load(f)

for key in ['prs_raw','prs_mean_mc','ci_lower','ci_upper','n_snps']:
    assert key in val3, f"❌ Missing key: {key}"

print(f"  ✅ Pickle verified — keys: {list(val3.keys())}")

# ── Final Summary ───────────────────────────────────────────────
print("\n" + "=" * 65)
print("  ✅ NOTEBOOK 4 COMPLETE — PRS Pipeline")
print("=" * 65)

print(f"  SNPs used   : {len(per_snp_df)}")
print(f"  prs_raw     : {prs_raw:.6f}")
print(f"  MC mean     : {prs_mean_mc:.6f}")
print(f"  95% CI      : [{ci_lower:.6f}, {ci_upper:.6f}]")

print(f"\n📁 {PRS_OUT_PATH}")
print(f"📁 {PER_SNP_OUT_PATH}")
print(f"📁 {FEATURE_VEC_OUT}")

print("\n🔜 Next: Notebook 5 (model_training_lifestyle.ipynb)")
print("=" * 65)

# NOTE:
# prs_raw is a population-level genetic risk signal
# it is NOT normalized here
# scaling and interpretation will be handled in NB7 (fusion stage)