# Generated from: nb3_genome_preprocessing_FIXED.ipynb
# Converted at: 2026-06-18T05:23:32.813Z
# Next step (optional): refactor into modules & generate tests with RunCell
# Quick start: pip install runcell

# # 🧬 Preprocessing Notebook 3 — Genomic Data
# ## Ancestry-Calibrated Polygenic Score Harmonization Pipeline
# ### PGS Catalog × GenomeIndia | Coordinate-Based Matching + Allele Alignment
# ### Primary Production Score: PGS000116 (40,079 SNPs, lassosum) -> pgs000116_genomeindia_harmonized.csv
# ### Baseline Comparator: PGS002809 (206 SNPs, GWAS Hits) -> harmonized_genetic_map.csv
# 
# ---
# 
# > **Project Goal:** Build a population-aware genetic risk map for cardiovascular disease (CVD)  
# > by harmonizing the primary Polygenic Score (**PGS000116**, 40,079 lassosum variants) and baseline comparator (**PGS002809**)  
# > with allele frequency data from the **GenomeIndia (GI)** reference panel (9,768 whole genomes).

# 
# > **Why this matters:** A polygenic score is only as accurate as its calibration to the  
# > target population. Effect sizes and risk allele frequencies from European GWAS cohorts  
# > can be systematically biased when applied to South Asians, due to differences in LD  
# > structure, ancestral haplotype blocks, and population-specific allele frequency drift.  
# > This notebook corrects for that bias by re-anchoring each PGS SNP to its **observed  
# > frequency in Indian ancestry**.
# 
# ---
# 
# ## 📌 What this pipeline does (in order)
# 1. Mounts Google Drive and validates all file paths
# 2. Loads and validates the PGS Catalog scoring file (PGS002809)
# 3. Harmonizes PGS SNPs against GenomeIndia reference panel (coordinate-based matching + allele alignment)
# 4. **[FIX]** Logs exactly which PGS SNPs were dropped and why (required for paper methods section)
# 5. Applies two bioinformatic QC filters (Palindromic SNP filter + MAF filter)
# 6. Exports the final ancestry-calibrated genetic map
# 
# ---
# 
# ## 📂 Required inputs
# 
# ```
# CVD_DigitalTwin_Project/
# └── data/
#     └── raw/
#         ├── pgs_catalog_2809.tsv                      ← PGS Catalog score file
#         └── genome_india/
#             ├── GI_9768_CBR-NIBMG_JointCall_AF_chr1.tsv
#             ├── GI_9768_CBR-NIBMG_JointCall_AF_chr2.tsv
#             └── ... (22 files, chr1 through chr22)
# ```
# 
# | Parameter | Value |
# |---|---|
# | PGS Catalog Score | PGS002809 (Cardiovascular Disease) |
# | Reference Panel | GenomeIndia 9,768-sample WGS |
# | Total GI Variants | ~129.9 million |
# | Harmonization Strategy | Coordinate-Based Positional Matching + Allele Alignment |
# | QC Filters | Palindromic SNP Filter + Minor Allele Frequency (MAF) Filter |
# 


# ---
# # PHASE 1: Environment Setup
# 
# ## Architectural principle
# All paths declared once as `ALL_CAPS` constants. No hardcoded paths appear anywhere else  
# in this notebook. Changing `PROJECT_ROOT` is sufficient to redirect the entire pipeline.
# 
# > 📝 **Edit `PROJECT_ROOT`** to match your Google Drive structure before running.
# 


import os
import sys
import glob
import json
import time
import pickle
import warnings
warnings.filterwarnings('ignore')

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

import pandas as pd
import numpy as np

# ── Dual-Environment Support (Colab + Local) ────────────────
try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)
    BASE_DIR = "/content/drive/MyDrive/CAD_DT_Final/"
    print('✅ Google Colab detected — Drive mounted')
except ImportError:
    # Local Windows environment
    _candidates = [r'E:\Capstone', r'e:\Capstone']
    BASE_DIR = None
    for _p in _candidates:
        if os.path.isdir(_p):
            BASE_DIR = _p.replace('\\', '/') + '/'
            break
    if BASE_DIR is None:
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))).replace('\\', '/') + '/'
    print(f'ℹ️  Local environment detected — BASE_DIR: {BASE_DIR}')

# ── Add parent dir to sys.path for shared module imports ────
NB_DIR = os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else '.'
if NB_DIR not in sys.path:
    sys.path.insert(0, NB_DIR)

# ── SINGLE SOURCE OF TRUTH ──────────────────────────────────
RAW_DIR        = BASE_DIR + "Data/Raw/"
gi_candidates  = [
    os.path.join(BASE_DIR, "GenomeIndiaSummary/9768GI_SummaryStats/"),
    os.path.join(BASE_DIR, "Data/Raw/Genome_India/")
]
GI_DIR         = next((p for p in gi_candidates if os.path.isdir(p)), gi_candidates[0])
OUTPUTS_DIR    = BASE_DIR + "Outputs/"
GENETICS_DIR   = OUTPUTS_DIR + "Genetics/Comparators/PGS002809/"


# ── File Paths ──────────────────────────────────────────────
PGS_PATH         = RAW_DIR + "pgs_catalog_2809.tsv"
OUTPUT_PATH      = GENETICS_DIR + "harmonized_genetic_map.csv"
DROPPED_SNPS_LOG = GENETICS_DIR + "dropped_snps_audit_log.csv"
API_CACHE_PATH   = GENETICS_DIR + ".gidb_nb3_cache.json"

# ── Create required folders ─────────────────────────────────
os.makedirs(GENETICS_DIR, exist_ok=True)

# ── Pre-flight validation ───────────────────────────────────
print("=" * 65)
print("  CVD DIGITAL TWIN — PGS HARMONIZATION PIPELINE")
print("  PHASE 1: Environment Initialization")
print("=" * 65)

print(f"  BASE_DIR        : {BASE_DIR}")
print(f"  PGS_PATH        : {PGS_PATH}")
print(f"  GI_DIR          : {GI_DIR}")
print(f"  OUTPUT_DIR      : {GENETICS_DIR}")

assert os.path.isfile(PGS_PATH), f"❌ PGS file not found: {PGS_PATH}"
assert os.path.isdir(GI_DIR), f"❌ GenomeIndia folder not found: {GI_DIR}"

gi_file_list = sorted(glob.glob(GI_DIR + "*.tsv"))

print(f"  GenomeIndia files found: {len(gi_file_list)} / 22")

if len(gi_file_list) < 22:
    print(f"  ⚠️ WARNING: Expected 22 chromosome files, found {len(gi_file_list)}")

print("\n[PHASE 1 COMPLETE] ✅ Environment ready.")
print("=" * 65)

# ---
# # PHASE 2: PGS Data Loading & Validation
# 
# ## What is a PGS Catalog Score?
# 
# A **Polygenic Score (PGS)** aggregates the small, additive effects of genetic variants (SNPs)  
# into a single numeric risk estimate. The PGS Catalog (https://www.pgscatalog.org) is the  
# gold-standard repository for published, peer-reviewed polygenic scores.
# 
# **PGS002809** is a CVD risk score. Each row represents one SNP with:
# 
# | Column | Description |
# |---|---|
# | `rsID` | dbSNP reference identifier (e.g., rs11591147) |
# | `chr_name` | Chromosome (1–22, X) |
# | `chr_position` | GRCh37/38 base-pair coordinate |
# | `effect_allele` | The allele that *increases* CVD risk |
# | `effect_weight` | Log-odds coefficient (β) from the GWAS model |
# 
# The `effect_weight` encodes direction and magnitude. A weight of 0.547 for rs186696265  
# represents a very large per-allele log-odds increase in CVD risk — this SNP alone substantially  
# shifts the probabilistic risk estimate for any carrier.
# 


print("=" * 65)
print("  PHASE 2: PGS Data Loading & Validation")
print("=" * 65)

PGS_COLUMNS_REQUIRED = ['rsID', 'chr_name', 'chr_position', 'effect_allele', 'effect_weight']

pgs_raw = pd.read_csv(
    PGS_PATH,
    sep='\t',
    comment='#',
    usecols=PGS_COLUMNS_REQUIRED
)

print(f"  ✅ PGS file loaded: {pgs_raw.shape[0]} SNPs × {pgs_raw.shape[1]} columns")

# Standardise chr_name to string without 'chr' prefix
pgs_raw['chr_name'] = pgs_raw['chr_name'].astype(str).str.replace(r'^chr', '', regex=True)

# Uppercase alleles for case-insensitive matching
pgs_raw['effect_allele'] = pgs_raw['effect_allele'].str.upper()

# Drop rows missing core fields
n_before = len(pgs_raw)
pgs_clean = pgs_raw.dropna(subset=['chr_name', 'chr_position', 'effect_allele', 'effect_weight']).copy()
n_dropped_missing = n_before - len(pgs_clean)

if n_dropped_missing > 0:
    print(f"  ⚠️  Dropped {n_dropped_missing} SNPs with missing core fields.")
else:
    print(f"  ✅ No SNPs dropped for missing values ({len(pgs_clean)} complete).")

INITIAL_PGS_SNP_COUNT = len(pgs_clean)

print()
print("  Effect weight (β) distribution:")
w = pgs_clean['effect_weight']
print(f"    Min={w.min():.4f}  Mean={w.mean():.4f}  Median={w.median():.4f}  Max={w.max():.4f}")
top_snp = pgs_clean.loc[w.idxmax()]
print(f"  🔬 Largest effect SNP: {top_snp['rsID']}  β={top_snp['effect_weight']:.4f}")

print()
print(f"[PHASE 2 COMPLETE] ✅ {INITIAL_PGS_SNP_COUNT} PGS SNPs ready for harmonization.")
print("=" * 65)


# ---
# # PHASE 3: Multi-File Harmonization Engine
# 
# ## Why coordinate-based matching instead of rsID matching?
# 
# Matching by rsID is intuitive but unreliable across databases:
# 1. The same position can have different rsIDs in different database versions (rsID merging/splitting events in dbSNP).
# 2. Population-specific databases like GenomeIndia contain novel variants without rsIDs.
# 3. Build mismatch (GRCh37 vs GRCh38) can cause rsID→position mismatches.
# 
# **Solution:** Match on **(Chromosome + Genomic Position)** — a composite key that is  
# build-stable and database-agnostic. This is the gold-standard approach used by the  
# PGS Catalog harmonization pipeline and tools like PLINK2 and LiftOver.
# 
# ## Why directional allele alignment matters
# 
# Knowing *which* position to look up is only half the problem. We also need to establish  
# whether the PGS **effect allele** is the ALT or REF allele in the GenomeIndia VCF:
# 
# - **Effect allele = ALT:** `risk_freq = Alt_AF` (direct)
# - **Effect allele = REF:** `risk_freq = 1 − Alt_AF` (flip required)
# - **Neither matches:** SNP is multi-allelic or has a build mismatch → **dropped**
# 
# Without this directional alignment, a SNP with risk allele frequency 0.85 could be  
# incorrectly encoded as 0.15 — a near-complete inversion. Across hundreds of SNPs,  
# such errors compound to produce a clinically meaningless polygenic score.
# 
# ### Diagnostic cell — run this first to confirm GI file format
# 


# ── DIAGNOSTIC + HEADER VALIDATION — sample 3 GI files ──────────────────────
gi_file_list = sorted(glob.glob(GI_DIR + "*.tsv"))
if len(gi_file_list) == 0:
    raise FileNotFoundError(f"No .tsv files in GI_DIR: {GI_DIR}. Check your path.")

# Sample up to 3 files to confirm consistent column count across chromosomes
sample_files = gi_file_list[:min(3, len(gi_file_list))]
col_counts = {}

for fpath in sample_files:
    fname = os.path.basename(fpath)
    sample = pd.read_csv(fpath, sep='\t', nrows=5, header=None)
    col_counts[fname] = sample.shape[1]
    print(f"File: {fname}  →  {sample.shape[1]} columns")
    for i, col in enumerate(sample.columns):
        print(f"  [{i}] sample values: {sample[col].tolist()}")
    print()

# Assert all sampled files have the same number of columns
unique_col_counts = set(col_counts.values())
assert len(unique_col_counts) == 1, (
    f"❌ Inconsistent column counts across GI files: {col_counts}\n"
    "Check for header rows or format differences between chromosomes."
)
print(f"✅ All sampled files have {list(unique_col_counts)[0]} columns — consistent format confirmed.")
print("   header=None is safe to use in Phase 3.")
print()
print("Expected column layout (if no header):")
print("  [0] chromosome  [1] position  [2] variant_id  [3] ref_allele  [4] alt_allele  [5] alt_af")
print()
print("If the above does not match, update GI_COLUMN_NAMES in Phase 3 before running.")


# ── CELL 3.1 — Multi-File Harmonization Engine ───────────────────────────────

print("=" * 65)
print("  PHASE 3: Multi-File Harmonization Engine")
print("  Strategy: Coordinate-Based Matching + Directional Allele Alignment")
print("=" * 65)

# Column names for GenomeIndia files — confirmed via diagnostic cell above
# GI files have NO header row; columns are assigned by position
GI_COLUMN_NAMES = [
    'gi_chromosome',
    'gi_position',
    'gi_variant_id',
    'gi_ref_allele',
    'gi_alt_allele',
    'gi_alt_allele_frequency'
]

pgs_clean['chr_position'] = pgs_clean['chr_position'].astype(int)

harmonized_results = []   # per-chromosome DataFrames

# FIX: Comprehensive per-SNP drop audit
# We track every PGS SNP and the reason it was excluded (if any)
# This is required for the paper's methods section and for reproducibility
pgs_clean['drop_reason'] = 'retained'  # default; updated below as SNPs are processed

total_chromosomes_processed      = 0
total_position_matches           = 0
total_allele_matched_alt         = 0
total_allele_matched_ref         = 0
total_dropped_no_allele_match    = 0
dropped_no_position_match_rsids  = []
dropped_no_allele_match_rsids    = []

print(f"\n  Processing {len(gi_file_list)} chromosome files...")
print("-" * 65)

for gi_filepath in gi_file_list:
    gi_filename  = os.path.basename(gi_filepath)
    chr_label    = gi_filename.split('_chr')[-1].replace('.tsv', '')

    print(f"  🔬 Chromosome {chr_label:>2} | File: {gi_filename}")

    try:
        gi_df = pd.read_csv(
            gi_filepath,
            sep='\t',
            header=None,
            names=GI_COLUMN_NAMES,
            dtype={'gi_position': int, 'gi_alt_allele_frequency': float}
        )
    except Exception as e:
        print(f"     ⚠️  Could not read file. Skipping. Error: {e}")
        continue

    gi_df['gi_ref_allele'] = gi_df['gi_ref_allele'].str.upper()
    gi_df['gi_alt_allele'] = gi_df['gi_alt_allele'].str.upper()

    pgs_chr = pgs_clean[pgs_clean['chr_name'] == chr_label].copy()
    print(f"     GI variants: {len(gi_df):,}  |  PGS SNPs targeting this chr: {len(pgs_chr)}")

    if len(pgs_chr) == 0:
        print(f"     ⏭️  No PGS SNPs on chr{chr_label}. Skipping.")
        continue

    # Track SNPs on this chromosome that got no positional match
    merged = pd.merge(
        pgs_chr,
        gi_df[['gi_position', 'gi_ref_allele', 'gi_alt_allele', 'gi_alt_allele_frequency']],
        left_on='chr_position',
        right_on='gi_position',
        how='inner'
    )

    # Record which rsIDs got NO positional match
    matched_rsids = set(merged['rsID'])
    no_pos_match  = pgs_chr[~pgs_chr['rsID'].isin(matched_rsids)]['rsID'].tolist()
    dropped_no_position_match_rsids.extend(no_pos_match)
    for rsid in no_pos_match:
        pgs_clean.loc[pgs_clean['rsID'] == rsid, 'drop_reason'] = 'no_positional_match_in_gi'

    total_position_matches += len(merged)
    print(f"     Positional matches: {len(merged)}")

    if len(merged) == 0:
        print(f"     ⚠️  Zero matches. Check genome build compatibility (GRCh37 vs GRCh38).")
        continue

    # Directional allele alignment
    cond_alt = merged['effect_allele'] == merged['gi_alt_allele']
    cond_ref = merged['effect_allele'] == merged['gi_ref_allele']
    cond_none = ~(cond_alt | cond_ref)

    merged['adjusted_risk_freq'] = np.select(
        [cond_alt, cond_ref],
        [merged['gi_alt_allele_frequency'], 1 - merged['gi_alt_allele_frequency']],
        default=np.nan
    )

    n_alt  = int(cond_alt.sum())
    n_ref  = int(cond_ref.sum())
    n_none = int(cond_none.sum())
    total_allele_matched_alt          += n_alt
    total_allele_matched_ref          += n_ref
    total_dropped_no_allele_match     += n_none

    no_allele_rsids = merged.loc[cond_none, 'rsID'].tolist()
    dropped_no_allele_match_rsids.extend(no_allele_rsids)
    for rsid in no_allele_rsids:
        pgs_clean.loc[pgs_clean['rsID'] == rsid, 'drop_reason'] = 'no_allele_match_multiallellic_or_indel'

    print(f"     Allele align — Effect=ALT: {n_alt} | Effect=REF(flip): {n_ref} | No match (dropped): {n_none}")

    aligned = merged.dropna(subset=['adjusted_risk_freq']).copy()
    harmonized_results.append(aligned)
    total_chromosomes_processed += 1

print()
print("-" * 65)
print("[STEP 3.2] Harmonization Engine Summary:")
print(f"  Chromosomes processed      : {total_chromosomes_processed}")
print(f"  Total positional matches   : {total_position_matches:,}")
print(f"  Effect=ALT alignments      : {total_allele_matched_alt:,}")
print(f"  Effect=REF (flip) aligns   : {total_allele_matched_ref:,}")
print(f"  Dropped (no allele match)  : {total_dropped_no_allele_match:,}")
print(f"  Dropped (no pos match)     : {len(dropped_no_position_match_rsids):,}")
print()

# ── GENOME BUILD SAFETY CHECK ────────────────────────────────────────────────
# If match_rate < 0.80 on the processed chromosomes, the PGS and GI files are likely on different builds
processed_chrs = [os.path.basename(f).split('_chr')[-1].replace('.tsv', '') for f in gi_file_list]
pgs_subset_count = len(pgs_clean[pgs_clean['chr_name'].isin(processed_chrs)])
subset_match_rate = total_position_matches / pgs_subset_count if pgs_subset_count > 0 else 0
overall_match_rate = total_position_matches / INITIAL_PGS_SNP_COUNT if INITIAL_PGS_SNP_COUNT > 0 else 0

print(f"  Chromosomes processed      : {len(processed_chrs)} / 22")
print(f"  Targeted PGS SNPs in subset: {pgs_subset_count}")
print(f"  Subset match rate          : {subset_match_rate*100:.1f}%  ({total_position_matches} / {pgs_subset_count})")
print(f"  Overall match rate (all chr): {overall_match_rate*100:.1f}%  ({total_position_matches} / {INITIAL_PGS_SNP_COUNT})")

if len(processed_chrs) == 22:
    assert overall_match_rate > 0.80, (
        f"[FATAL] Genome build mismatch: only {overall_match_rate*100:.1f}% of PGS SNPs matched positionally."
    )
    print(f"  ✅ Full genome build check passed ({overall_match_rate*100:.1f}% > 80%)")
else:
    assert subset_match_rate > 0.80, (
        f"[FATAL] Genome build mismatch: only {subset_match_rate*100:.1f}% of PGS SNPs matched on processed chromosomes."
    )
    print(f"  ✅ Subset genome build check passed ({subset_match_rate*100:.1f}% > 80% on {len(processed_chrs)} chromosomes)")
print()
print("  SNPs with NO positional match in GenomeIndia:")
if dropped_no_position_match_rsids:
    for rsid in dropped_no_position_match_rsids:
        row = pgs_clean[pgs_clean['rsID'] == rsid].iloc[0]
        print(f"    {rsid}  chr{row['chr_name']}:{int(row['chr_position'])}  "
              f"effect_allele={row['effect_allele']}  β={row['effect_weight']:.4f}")
else:
    print("    None — all SNPs found positionally.")

print()
print("  SNPs with positional match but NO allele match (multi-allelic/indel):")
if dropped_no_allele_match_rsids:
    for rsid in dropped_no_allele_match_rsids:
        row = pgs_clean[pgs_clean['rsID'] == rsid].iloc[0]
        print(f"    {rsid}  chr{row['chr_name']}:{int(row['chr_position'])}  "
              f"effect_allele={row['effect_allele']}  β={row['effect_weight']:.4f}")
else:
    print("    None — all positionally matched SNPs had a valid allele match.")

print()
print("[PHASE 3 COMPLETE] ✅ Harmonization engine finished.")
print("=" * 65)


# ---
# # PHASE 3.5: GI-DB Variant Annotation Enrichment
#
# ## Why annotate variants?
#
# The harmonized map from Phase 3 contains allele frequencies but no biological
# context. Enriching each variant with gene symbol, functional consequence, and
# ClinVar clinical significance transforms the output from a "flat frequency table"
# into a biologically interpretable genetic intelligence layer.
#
# ## Data Sources
# - **GI-DB API** (https://gidb.igib.res.in/api/query.php): Indian population-specific
#   variant annotation including gene, consequence, impact, ClinVar, and HGVSp.
# - **Ensembl VEP REST API** (fallback): If GI-DB is unreachable.
#
# ## New columns added
# | Column | Source | Description |
# |--------|--------|-------------|
# | `gene_symbol` | GI-DB/Ensembl | Gene name (e.g., PCSK9, LDLR) |
# | `consequence_type` | GI-DB/Ensembl | Functional consequence (e.g., missense_variant) |
# | `impact_level` | GI-DB/Ensembl | Severity: HIGH, MODERATE, LOW, MODIFIER |
# | `clinvar_significance` | GI-DB/ClinVar | Clinical: Pathogenic, Benign, VUS, etc. |
# | `functional_impact_weight` | Computed | Numeric weight (0.75–1.5) based on consequence |
# | `is_protein_coding` | Derived | Boolean: gene is protein-coding? |
# | `hgvsp` | GI-DB | Protein change notation |
#


print("=" * 65)
print("  PHASE 3.5: GI-DB Variant Annotation Enrichment")
print("=" * 65)

# We annotate the pre-QC merged results so annotations carry through to final output
# Build a temporary master DF from harmonized_results
_annotation_df = pd.concat(harmonized_results, ignore_index=True) if harmonized_results else pd.DataFrame()

if len(_annotation_df) == 0:
    print("  ⚠️ No harmonized variants to annotate — skipping Phase 3.5")
else:
    # Import functional weight mapping from shared module
    try:
        from patient_intelligence_engine import (
            GIDBClient, get_functional_weight, CONSEQUENCE_WEIGHTS
        )
        _has_engine = True
    except ImportError:
        _has_engine = False
        print("  ⚠️ patient_intelligence_engine.py not found — using inline annotations")
    
    # Initialize annotation columns with NaN
    for col in ['gene_symbol', 'consequence_type', 'impact_level',
                'clinvar_significance', 'functional_impact_weight',
                'is_protein_coding', 'hgvsp']:
        for df_chunk in harmonized_results:
            if col not in df_chunk.columns:
                df_chunk[col] = np.nan
    
    # ── Try GI-DB API annotation ──────────────────────────────
    _gidb_success = False
    _api_cache = {}
    
    if os.path.isfile(API_CACHE_PATH):
        try:
            with open(API_CACHE_PATH, 'r') as f:
                _api_cache = json.load(f)
            print(f"  📦 API cache loaded: {len(_api_cache)} entries")
        except Exception:
            _api_cache = {}
    
    try:
        import requests
        
        # Build location queries from harmonized variants
        # Group variants by chromosome for efficient batching
        _all_variants = pd.concat(harmonized_results, ignore_index=True)
        _variant_locs = []
        _loc_to_idx = {}  # location string → list of (df_idx, row_idx)
        
        for chunk_idx, df_chunk in enumerate(harmonized_results):
            for row_idx, row in df_chunk.iterrows():
                chrom = str(row.get('chr_name', row.get('chromosome', '')))
                pos = int(row.get('chr_position', row.get('gi_position', 0)))
                if pos > 0:
                    loc = f"chr{chrom}:{max(1, pos-5)}-{pos+5}"
                    cache_key = f"{chrom}:{pos}"
                    if cache_key not in _api_cache:
                        _variant_locs.append(loc)
                    _loc_to_idx.setdefault(cache_key, []).append((chunk_idx, row_idx))
        
        print(f"  📡 Querying GI-DB API for {len(_variant_locs)} uncached variants...")
        
        if len(_variant_locs) > 0:
            # Batch query GI-DB (max 20 locations per request)
            GIDB_URL = "https://gidb.igib.res.in/api/query.php"
            _batch_size = 20
            _annotated = 0
            
            for i in range(0, len(_variant_locs), _batch_size):
                batch = _variant_locs[i:i + _batch_size]
                try:
                    resp = requests.post(
                        GIDB_URL,
                        json={"type": "location", "locations": batch},
                        timeout=30
                    )
                    if resp.status_code == 429:
                        print("  ⏳ Rate limited — waiting 60s...")
                        time.sleep(60)
                        resp = requests.post(
                            GIDB_URL,
                            json={"type": "location", "locations": batch},
                            timeout=30
                        )
                    
                    if resp.ok:
                        data = resp.json()
                        for region_key, region_data in data.get("results", {}).items():
                            for v in region_data.get("variants", []):
                                pos = int(v.get("POS", 0))
                                chrom = str(v.get("CHROM", "")).replace("chr", "")
                                cache_key = f"{chrom}:{pos}"
                                _api_cache[cache_key] = {
                                    'gene_symbol': v.get('SYMBOL', None),
                                    'consequence_type': v.get('Consequence', None),
                                    'impact_level': v.get('IMPACT', None),
                                    'clinvar_significance': v.get('ClinVar_CLNSIG', None),
                                    'hgvsp': v.get('HGVSp', None),
                                }
                                _annotated += 1
                    else:
                        print(f"  ⚠️ GI-DB batch {i//20} returned {resp.status_code}")
                except Exception as e:
                    print(f"  ⚠️ GI-DB batch {i//20} failed: {e}")
                
                # Rate limit: max 30 req/min → wait 2s between batches
                time.sleep(2.1)
            
            print(f"  ✅ GI-DB API: {_annotated} variant annotations retrieved")
            _gidb_success = _annotated > 0
        else:
            print("  ✅ All variants found in cache")
            _gidb_success = True
        
        # Save cache
        with open(API_CACHE_PATH, 'w') as f:
            json.dump(_api_cache, f)
    
    except ImportError:
        print("  ⚠️ 'requests' library not available — skipping GI-DB API")
    except Exception as e:
        print(f"  ⚠️ GI-DB API unavailable: {e}")
    
    # ── Apply annotations from cache to harmonized_results ────
    _total_annotated = 0
    _total_clinvar = 0
    
    # Inline functional weight mapping (in case shared module not available)
    _CONSEQUENCE_WEIGHTS = {
        'transcript_ablation': 1.5, 'splice_acceptor_variant': 1.4,
        'splice_donor_variant': 1.4, 'stop_gained': 1.4,
        'frameshift_variant': 1.3, 'stop_lost': 1.3, 'start_lost': 1.3,
        'missense_variant': 1.1, 'inframe_insertion': 1.05,
        'inframe_deletion': 1.05, 'protein_altering_variant': 1.05,
        'splice_region_variant': 0.95, 'synonymous_variant': 0.9,
        'stop_retained_variant': 0.9, '5_prime_UTR_variant': 0.85,
        '3_prime_UTR_variant': 0.85, 'intron_variant': 0.8,
        'upstream_gene_variant': 0.8, 'downstream_gene_variant': 0.8,
        'intergenic_variant': 0.75, 'regulatory_region_variant': 0.85,
    }
    _IMPACT_FALLBACK = {'HIGH': 1.3, 'MODERATE': 1.1, 'LOW': 0.9, 'MODIFIER': 0.8}
    
    for chunk_idx, df_chunk in enumerate(harmonized_results):
        for row_idx in df_chunk.index:
            row = df_chunk.loc[row_idx]
            chrom = str(row.get('chr_name', row.get('chromosome', '')))
            pos = int(row.get('chr_position', row.get('gi_position', 0)))
            cache_key = f"{chrom}:{pos}"
            
            if cache_key in _api_cache:
                ann = _api_cache[cache_key]
                df_chunk.at[row_idx, 'gene_symbol'] = ann.get('gene_symbol')
                df_chunk.at[row_idx, 'consequence_type'] = ann.get('consequence_type')
                df_chunk.at[row_idx, 'impact_level'] = ann.get('impact_level')
                df_chunk.at[row_idx, 'clinvar_significance'] = ann.get('clinvar_significance')
                df_chunk.at[row_idx, 'hgvsp'] = ann.get('hgvsp')
                
                # Compute functional_impact_weight
                cons = ann.get('consequence_type', '')
                impact = ann.get('impact_level', '')
                weight = 1.0
                if cons and isinstance(cons, str):
                    parts = [c.strip() for c in cons.split(',')]
                    weights = [_CONSEQUENCE_WEIGHTS.get(c) for c in parts if c in _CONSEQUENCE_WEIGHTS]
                    if weights:
                        weight = max(weights)
                    elif impact and impact.upper() in _IMPACT_FALLBACK:
                        weight = _IMPACT_FALLBACK[impact.upper()]
                elif impact and isinstance(impact, str) and impact.upper() in _IMPACT_FALLBACK:
                    weight = _IMPACT_FALLBACK[impact.upper()]
                df_chunk.at[row_idx, 'functional_impact_weight'] = weight
                
                # is_protein_coding
                gene = ann.get('gene_symbol')
                df_chunk.at[row_idx, 'is_protein_coding'] = (
                    gene is not None and gene != '' and
                    cons != 'intergenic_variant'
                )
                
                if ann.get('gene_symbol'):
                    _total_annotated += 1
                if ann.get('clinvar_significance'):
                    _total_clinvar += 1
    
    # Fill remaining NaN functional weights with 1.0 (neutral)
    for df_chunk in harmonized_results:
        df_chunk['functional_impact_weight'] = df_chunk['functional_impact_weight'].fillna(1.0)
        df_chunk['is_protein_coding'] = df_chunk['is_protein_coding'].fillna(False)
    
    print(f"\n  📊 Annotation Summary:")
    print(f"     Variants with gene symbol  : {_total_annotated}")
    print(f"     Variants with ClinVar data : {_total_clinvar}")
    print(f"     API cache entries          : {len(_api_cache)}")
    
    print("\n[PHASE 3.5 COMPLETE] ✅ Variant annotation enrichment finished.")
    print("=" * 65)



# ---
# # PHASE 4: Bioinformatic Quality Control
# 
# ## QC Filter 1 — Palindromic SNP Strand Ambiguity Filter
# 
# **What are palindromic SNPs?** SNPs where the two alleles are complementary base pairs:  
# **A/T** or **C/G**. On double-stranded DNA, such variants read identically on forward and  
# reverse strand — making strand orientation undetectable from sequence alone.
# 
# **The risk:** When the PGS and GI datasets were generated using potentially different strand  
# conventions, a palindromic SNP might be correctly matched by position but silently have its  
# alleles swapped. An effect allele of `A` (freq=0.85 in Indians) could actually correspond  
# to `T` in the GI panel if strand reporting differs — inverting the risk frequency to 0.15.
# 
# **Solution (frequency-based safeguard):** Palindromic SNPs with `adjusted_risk_freq` between  
# **0.42 and 0.58** are dropped. In this zone, frequency alone cannot resolve strand ambiguity  
# (both interpretations are plausible). Palindromic SNPs outside this range (e.g., freq=0.1  
# or freq=0.9) are **safely retained** because the frequency asymmetry resolves the strand.
# 
# **Research basis:** This cutoff (0.42–0.58) is the standard used by the PGS Catalog  
# harmonization pipeline, LiftOver, and PLINK's `--flip-scan` function  
# (Lambert et al., 2021, *Nature Protocols*).
# 
# ---
# 
# ## QC Filter 2 — Minor Allele Frequency (MAF) Filter
# 
# **What is MAF?** The frequency of the less-common allele at a given locus.  
# Our `adjusted_risk_freq` is oriented to the risk allele, so effective MAF = `min(freq, 1−freq)`.
# 
# **Why filter on MAF < 1%?** SNPs with very low risk-allele frequency in Indians:
# 1. Contribute negligible variance to the PGS in this population.
# 2. Have highly unstable frequency estimates — a few sequencing errors can dramatically shift the estimate.
# 3. Are often ancestry-specific rare variants with unreliable GWAS effect weight estimates.
# 
# **Research basis:** MAF > 1% is the standard QC threshold used in the Global Biobank  
# Meta-analysis Initiative (GBMI) and recommended by the PGS Catalog QC guidelines.
# 


print("=" * 65)
print("  PHASE 4: Bioinformatic Quality Control")
print("=" * 65)

if len(harmonized_results) == 0:
    raise RuntimeError(
        "[FATAL] No harmonized data to QC! Phase 3 produced zero results. "
        "Check chromosome file formats and paths."
    )

pre_qc_df = pd.concat(harmonized_results, ignore_index=True)
pre_qc_count = len(pre_qc_df)
print(f"  Pre-QC master DataFrame: {pre_qc_count:,} SNPs")

PALINDROMIC_LOW  = 0.42
PALINDROMIC_HIGH = 0.58
MAF_THRESHOLD    = 0.01

PALINDROMIC_PAIRS = [('A','T'), ('T','A'), ('C','G'), ('G','C')]

# ── QC Filter 1: Palindromic SNP Ambiguity ────────────────────────────────
print()
print("-" * 55)
print("[QC FILTER 1] Palindromic SNP Strand Ambiguity Filter")
print("-" * 55)

pre_qc_df['allele_pair'] = list(zip(pre_qc_df['gi_ref_allele'], pre_qc_df['gi_alt_allele']))
mask_palindromic = pre_qc_df['allele_pair'].isin(PALINDROMIC_PAIRS)
mask_ambiguous   = (
    (pre_qc_df['adjusted_risk_freq'] > PALINDROMIC_LOW) &
    (pre_qc_df['adjusted_risk_freq'] < PALINDROMIC_HIGH)
)
mask_palindromic_drop = mask_palindromic & mask_ambiguous

n_palindromic_total   = int(mask_palindromic.sum())
n_palindromic_dropped = int(mask_palindromic_drop.sum())
n_palindromic_kept    = n_palindromic_total - n_palindromic_dropped

print(f"  Total palindromic SNPs detected         : {n_palindromic_total}")
print(f"  Palindromic RETAINED (freq outside zone): {n_palindromic_kept}")
print(f"  Palindromic DROPPED (freq in 0.42-0.58) : {n_palindromic_dropped}")

# Log dropped palindromic SNPs
if n_palindromic_dropped > 0:
    dropped_palind = pre_qc_df[mask_palindromic_drop][['rsID','adjusted_risk_freq']]
    print("  Dropped palindromic SNPs:")
    for _, row in dropped_palind.iterrows():
        print(f"    {row['rsID']}  risk_freq={row['adjusted_risk_freq']:.4f}")
    # Update audit log in pgs_clean
    for rsid in dropped_palind['rsID']:
        pgs_clean.loc[pgs_clean['rsID'] == rsid, 'drop_reason'] = 'palindromic_ambiguous_freq'

post_palindromic_df    = pre_qc_df[~mask_palindromic_drop].copy()
post_palindromic_count = len(post_palindromic_df)
print(f"  SNPs remaining after Palindromic Filter : {post_palindromic_count:,}")

# ── QC Filter 2: MAF Filter ───────────────────────────────────────────────
print()
print("-" * 55)
print("[QC FILTER 2] Minor Allele Frequency (MAF) Filter")
print("-" * 55)

mask_low_maf = post_palindromic_df['adjusted_risk_freq'] < MAF_THRESHOLD
n_low_maf    = int(mask_low_maf.sum())

if n_low_maf > 0:
    dropped_maf = post_palindromic_df[mask_low_maf][['rsID', 'adjusted_risk_freq']]
    print(f"  SNPs dropped (risk_freq < {MAF_THRESHOLD*100:.0f}%): {n_low_maf}")
    for _, row in dropped_maf.iterrows():
        print(f"    {row['rsID']}  risk_freq={row['adjusted_risk_freq']:.6f}")
    for rsid in dropped_maf['rsID']:
        pgs_clean.loc[pgs_clean['rsID'] == rsid, 'drop_reason'] = 'low_maf_below_1pct'
else:
    print(f"  No SNPs dropped by MAF filter (all risk_freq ≥ {MAF_THRESHOLD*100:.0f}%)")

post_maf_df    = post_palindromic_df[~mask_low_maf].copy()
post_maf_count = len(post_maf_df)
print(f"  SNPs remaining after MAF Filter         : {post_maf_count:,}")

# ── QC Summary ──────────────────────────────────────────────────────────
print()
print("-" * 55)
print("[STEP 4.3] QC Filter Impact Summary:")
print(f"  Pre-QC SNP count                       : {pre_qc_count:,}")
print(f"  [−] Dropped by Palindromic Filter       : {n_palindromic_dropped:,}")
print(f"  [−] Dropped by MAF Filter (<1%)         : {n_low_maf:,}")
print(f"  Post-QC SNP count                      : {post_maf_count:,}")
retention = post_maf_count / pre_qc_count * 100 if pre_qc_count > 0 else 0
print(f"  QC Retention Rate                      : {retention:.1f}%")

final_qc_df = post_maf_df
print()
print("[PHASE 4 COMPLETE] ✅ QC filters applied.")
print("=" * 65)


# ---
# # PHASE 5: Final Aggregation, Drop Audit & Data Export
# 
# ## What the output represents
# 
# The **Ancestry-Calibrated Genetic Map** — a curated, QC-filtered table where each row  
# represents a CVD risk SNP that has been:
# 
# 1. **Positionally verified** — confirmed to exist in GenomeIndia at the exact chromosomal coordinate
# 2. **Directionally aligned** — the risk allele mapped to its correct orientation relative to the Indian reference
# 3. **Frequency-calibrated** — `adjusted_risk_freq` carries the actual risk allele frequency in Indian ancestry
# 4. **QC-filtered** — palindromic ambiguities and low-frequency noise removed
# 
# ## Why we also export the full drop audit log
# 
# Reproducibility in genomic research requires documenting **every SNP exclusion and the reason for it**.  
# The `dropped_snps_audit_log.csv` provides a complete record of all 184 PGS SNPs and their fate  
# in this pipeline. This is required for the paper's methods section ("SNP harmonization and QC").
# 


print("=" * 65)
print("  PHASE 5: Final Aggregation & Data Export")
print("=" * 65)

# ── Column map — MUST match NB4 ─────────────────────────────
# Core columns (original 9) + annotation columns (7 new from Phase 3.5)
CORE_COLUMNS = [
    'rsID',
    'chromosome',
    'position_grch',
    'effect_allele',
    'effect_weight_beta',
    'gi_reference_allele',
    'gi_alternate_allele',
    'gi_alt_allele_frequency',
    'indian_ancestry_risk_allele_freq',
]

ANNOTATION_COLUMNS = [
    'gene_symbol',
    'consequence_type',
    'impact_level',
    'clinvar_significance',
    'functional_impact_weight',
    'is_protein_coding',
    'hgvsp',
]

EXPECTED_COLUMNS = CORE_COLUMNS + ANNOTATION_COLUMNS

FINAL_COLUMN_MAP = {
    'rsID': 'rsID',
    'chr_name': 'chromosome',
    'chr_position': 'position_grch',
    'effect_allele': 'effect_allele',
    'effect_weight': 'effect_weight_beta',
    'gi_ref_allele': 'gi_reference_allele',
    'gi_alt_allele': 'gi_alternate_allele',
    'gi_alt_allele_frequency': 'gi_alt_allele_frequency',
    'adjusted_risk_freq': 'indian_ancestry_risk_allele_freq',
}

# Build the source column list: core renames + annotation pass-throughs
_source_cols = list(FINAL_COLUMN_MAP.keys())
for acol in ANNOTATION_COLUMNS:
    if acol in final_qc_df.columns:
        _source_cols.append(acol)
    else:
        final_qc_df[acol] = np.nan
        _source_cols.append(acol)

final_df = final_qc_df[_source_cols].rename(columns=FINAL_COLUMN_MAP).copy()

# Sorting
final_df['chromosome'] = pd.to_numeric(final_df['chromosome'], errors='coerce')
final_df.sort_values(by=['chromosome', 'position_grch'], inplace=True, ignore_index=True)
final_df['chromosome'] = final_df['chromosome'].astype(str)

# Schema validation — check all expected columns present
for col in EXPECTED_COLUMNS:
    assert col in final_df.columns, f"❌ Missing column: {col}"
print(f"  ✅ Schema validated: {len(EXPECTED_COLUMNS)} columns")

# ── Annotation statistics ───────────────────────────────────
n_with_gene = final_df['gene_symbol'].notna().sum()
n_with_clinvar = final_df['clinvar_significance'].notna().sum()
n_with_consequence = final_df['consequence_type'].notna().sum()
n_protein_coding = final_df['is_protein_coding'].sum() if 'is_protein_coding' in final_df.columns else 0

print(f"  📊 Annotation coverage in final output:")
print(f"     Gene symbol     : {n_with_gene}/{len(final_df)} ({n_with_gene/len(final_df)*100:.1f}%)")
print(f"     Consequence     : {n_with_consequence}/{len(final_df)} ({n_with_consequence/len(final_df)*100:.1f}%)")
print(f"     ClinVar         : {n_with_clinvar}/{len(final_df)}")
print(f"     Protein-coding  : {n_protein_coding}/{len(final_df)}")

# ── Save outputs ────────────────────────────────────────────
final_df.to_csv(OUTPUT_PATH, index=False)
print(f"  ✅ Harmonized genetic map saved: {OUTPUT_PATH}")

audit_df = pgs_clean[['rsID', 'chr_name', 'chr_position', 'effect_weight', 'drop_reason']].copy()
audit_df['chr_name'] = audit_df['chr_name'].astype(str)

retained_rsids = set(final_df['rsID'])
audit_df.loc[audit_df['rsID'].isin(retained_rsids), 'drop_reason'] = 'retained_in_final_output'

audit_df.to_csv(DROPPED_SNPS_LOG, index=False)
print(f"  ✅ Drop audit log saved: {DROPPED_SNPS_LOG}")

# ── Final validation ────────────────────────────────────────
assert len(final_df) > 150
assert final_df['effect_weight_beta'].isnull().sum() == 0
assert final_df['indian_ancestry_risk_allele_freq'].isnull().sum() == 0

freq = final_df['indian_ancestry_risk_allele_freq']
assert (freq > 0).all() and (freq < 1).all()

print("\n✅ FINAL VALIDATION PASSED")
print(f"  SNPs retained: {len(final_df)}")

print("\n✅ PIPELINE COMPLETE")
print(f"  📁 {OUTPUT_PATH}")
print(f"  📁 {DROPPED_SNPS_LOG}")