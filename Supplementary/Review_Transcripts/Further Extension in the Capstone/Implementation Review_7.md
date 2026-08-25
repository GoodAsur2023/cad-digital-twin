# Full NB9 Implementation

**User:** Anonymous  
**Created:** 6/19/2026 13:39:06  
**Updated:** 8/21/2026 12:32:40  
**Exported:** 8/21/2026 12:33:56  
**Link:** [https://chatgpt.com/c/6a34f8ef-7408-83ee-a559-86257ac30627](https://chatgpt.com/c/6a34f8ef-7408-83ee-a559-86257ac30627)  

## Prompt:
21/08/2026, 12:32:18

This is the implementation plan that I am proposing to go ahead with to resolve the current issues highlighted by you

[Attachment: Rectifications_1.md]

## Response:
21/08/2026, 12:32:20

I reviewed the proposed **Stage 7 Review Feedback Implementation Plan** against the issues we identified in the latest code/run review. Overall, **the plan is well targeted and I approve the direction**, but I would make a few important additions before you implement it.

The plan correctly focuses on NB4, NB7, NB10, NB12, and the release manifest rather than changing the architecture. `Rectifications_1.md`

## Verdict

### Overall: ✅ Approved with 4 amendments

Your plan resolves most of the issues we identified:

| Issue we found | Your plan | Verdict |
|---|---|---|
| Synthetic prior terminology | ✅ Rename | Good |
| Hardcoded NB4 QC values | ✅ Dynamic | Good |
| Stale NB7 PGS002809 comments | ✅ Remove | Good |
| NB10 test-set SD scaling | ✅ Remove | **Excellent** |
| NB10 Pulse claim | ✅ Reword | **Excellent** |
| NB12 loose tolerances | ✅ Tighten | **Excellent** |
| NB12 silent fallback | ✅ Remove | **Excellent** |
| Fusion provenance consistency | ✅ Add exact check | Good |
| Benchmark structure-only validation | ✅ Strengthen | **Excellent** |
| Literature check | ✅ Clarify | Good |
| 27 assertion count | ✅ Fix | Good |
| Release hashes | ✅ Expand | **Excellent** |

The plan is therefore fundamentally correct. `Rectifications_1.md`

---

# 1. NB4: Rename `SOUTH_ASIAN_SYNTHETIC_PRIOR` carefully

I agree with:

> `SOUTH_ASIAN_SYNTHETIC_PRIOR` → `DETERMINISTIC_SYNTHETIC_PRIOR`

That is scientifically safer because the code uses a deterministic Beta(2.2, 2.0) assumption rather than measuring a variant-specific empirical frequency.

However, I would make the wording slightly more explicit:

> **`DETERMINISTIC_SYNTHETIC_PRIOR_BETA_2_2_2_0`**

or keep the shorter enum and document the exact distribution:

$$
p_i\sim Beta(2.2,2.0)
$$

The key is that nobody should later interpret this as an observed GenomeIndia allele frequency.

Your plan already points in exactly that direction. `Rectifications_1.md`

### Add one requirement

For every fallback variant, retain:

```text
frequency_source = DETERMINISTIC_SYNTHETIC_PRIOR
gi_ref_allele = NA
gi_alt_allele = NA
match_status = POSITION_NOT_FOUND
strand_status = NO_GI_MATCH
```

Do **not** regress to fabricated REF/ALT fields.

---

# 2. NB4 QC dynamic calculation: definitely do this

This is one of the most important parts of the plan.

You explicitly say:

> "Compute the exact number of matches, flips, synthetic fallback counts, and unresolved mismatches dynamically..." `Rectifications_1.md`

Good.

I would expand it to also calculate dynamically:

```text
input_pgs_variants
position_matches
direct_matches
strand_flips
synthetic_prior_rows
unresolved_rows
duplicate_rsid_count
missing_beta_count
missing_effect_frequency_count
```

The output should be derived from the actual dataframe, never from expected numbers.

This will make NB4's QC report meaningful.

---

# 3. NB7 changes: good, but add one more requirement

Your NB7 plan correctly removes stale PGS002809/182-SNP/11.88 comments. `Rectifications_1.md`

I also recommend removing any comments that say:

> "PRS contributes 15% of the final score."

That wording is now misleading because the production architecture is using the canonical fusion prediction and the genetic layer is a **population-context/sensitivity layer**, not an individual genetic predictor.

The code should explicitly distinguish:

```text
p_canonical_fusion
```

from:

```text
population_genetic_context
```

and:

```text
genetic_context_sensitivity
```

This prevents future confusion.

---

# 4. 🟢 NB10 fix is exactly right

This is the most important implementation change in your plan.

You propose removing:

```text
std_sbp
std_hr
std_chol
```

derived from the test set and applying the intervention directly in raw clinical units. `Rectifications_1.md`

That is precisely what I recommend.

The correct flow is:

```text
Raw patient state
        ↓
Pulse-grounded Δ
        ↓
Raw intervention state'
        ↓
clinical_pipeline.predict_proba()
        ↓
fitted training scaler
        ↓
model
```

That is substantially cleaner than manually converting physiological changes to z-space using test-set statistics.

### One addition

Do not calculate the raw intervention from:

```text
row_hemo['sbp_delta']
```

and blindly apply it to every patient.

Keep your existing scenario-specific response functions, but make their **output units explicitly raw clinical units**:

```text
SBP: mmHg
DBP: mmHg
HR: bpm
cholesterol: mg/dL
```

Then the pipeline handles preprocessing.

---

# 5. NB10 terminology change: approved

Changing:

> "952 native Pulse C-API simulations"

to:

> **"952 Pulse-grounded cohort counterfactual simulations"**

is exactly right. `Rectifications_1.md`

And:

> "Pulse-grounded/ML counterfactual concordance"

is the correct terminology.

This should also be reflected in:

- NB12
- JSON audit
- paper
- figures
- web interface.

The native Pulse C-API remains your **mechanistic reference simulation**, while the patient cohort uses the parameterized Pulse-grounded response model.

---

# 6. NB12 strictness: strongly approved

Your plan to move:

```text
atol = 0.002
```

to:

```text
atol = 1e-6
rtol = 0
```

is exactly the right direction for canonical artifact reproducibility. `Rectifications_1.md`

But I want one nuance.

For **AUC/Brier/ECE** derived from serialized prediction arrays, `1e-6` is reasonable.

For metrics involving floating-point bootstrap regeneration, don't demand exact equality against recomputed stochastic results unless the random seed and resampling procedure are exactly frozen.

So distinguish:

### Deterministic values

```text
PRS
GBI
AUC from canonical predictions
fusion weights
```

→ very tight tolerance.

### Stochastic values

```text
bootstrap CI
```

→ verify:

- seed,
- sample count,
- algorithm,
- stored prediction array,

rather than simply exact-value equality if the computation can differ by platform.

This distinction will make NB12 robust instead of brittle.

---

# 7. NB12 Check 4/5: excellent fix

The plan says:

> remove fallback assignments that silently succeed when baseline values are missing. `Rectifications_1.md`

This is absolutely necessary.

The rule should be:

```text
missing canonical value
        ↓
FAIL
```

never:

```text
missing canonical value
        ↓
compute replacement
        ↓
PASS
```

This is one of the most important changes in the entire plan.

---

# 8. NB12 Check 13: make it stronger than stated

You plan to verify:

> fusion weights in provenance exactly match manifest. `Rectifications_1.md`

Yes-but add a third comparison:

```text
fusion_weight_provenance.json
        =
release_manifest.json
        =
canonical fusion implementation
```

The **actual implementation weight** must be checked too.

Otherwise you can have:

```text
manifest = 0.5/0.5
provenance = 0.5/0.5
code = 0.6/0.4
```

and NB12 would still pass.

So require:

$$
w_{manifest}=w_{provenance}=w_{implementation}
$$

---

# 9. NB12 Check 15: this is a very strong addition

Your plan says:

> validate canonical benchmark metrics rather than merely checking JSON structure. `Rectifications_1.md`

Exactly.

I would go one step further.

The canonical benchmark should be **generated from the canonical prediction artifact**, not independently from models.

Use:

```text
canonical_test_predictions.parquet
```

as the source of truth.

Then:

```text
AUC
Brier
ECE
Sensitivity
Specificity
DCA
```

all derive from it.

That is the most robust solution to the previous 0.8788 vs 0.8838 problem.

---

# 10. Add this to your plan: Canonical prediction artifact validation

This is the biggest omission in the current plan.

Your earlier fixes already introduced `canonical_test_predictions.parquet`.

Now make it a **first-class release artifact**.

The manifest should hash:

```text
canonical_test_predictions.parquet
canonical_benchmark_metrics.json
methodology_audit_report.json
```

Your plan already proposes the first two additions conceptually. `Rectifications_1.md`

I would explicitly say:

> **All downstream benchmark metrics are generated from `canonical_test_predictions.parquet`; no downstream module independently reconstructs test probabilities for benchmark reporting.**

That is the strongest permanent solution.

---

# 11. Add one more NB12 check: prediction-artifact integrity

I'd make this:

### Check 27

**Canonical prediction artifact integrity**

Verify:

```text
patient count
target values
columns
prediction ranges [0,1]
no NaN
patient IDs/order
AUC/Brier recomputation
```

But then your count becomes:

```text
26 methodology assertions
+
1 release preflight
+
1 prediction-artifact integrity
=
28 total assertions
```

I don't recommend doing that yet because you've already settled the 27-assertion structure.

Instead, integrate this into **Check 15**.

That is cleaner.

---

# 12. The assertion-count fix in your plan is correct

Your plan says:

> **26 methodology assertions + 1 release preflight = 27 total assertions.** `Rectifications_1.md`

That's exactly how I recommend describing it.

Use:

> **NB12 - 26-Point Methodology Gate + Release Manifest Preflight**

and report:

```text
Methodology assertions: 26/26
Release preflight: PASS
Total assertions: 27/27
```

This is much clearer than calling it a "27-point methodology gate."

---

# 13. NB12 literature check: I agree, with one preferred implementation

Your plan says:

> "Ensure the values are correctly labeled as `ARTIFACT_VERIFIED` or actively computed as absolute relative error against the original Pulse output." `Rectifications_1.md`

I'd choose **active computation**.

Have a separate immutable:

```text
pulse_literature_reference.json
```

with:

```text
source
citation
reference_value
units
acceptable_range
```

Then NB12 computes:

$$
RelativeError=
\frac{|Prediction-Reference|}
{|Reference|}
$$

itself.

That is stronger than simply validating stored error values.

---

# 14. One thing I would add to NB10

Your plan fixes the scaling problem, but I would explicitly add:

> **The raw intervention state must be passed through the exact fitted clinical preprocessing/model pipeline without reconstructing or approximating the scaler.**

In other words:

```python
x_counterfactual_raw
    ↓
clinical_pipeline.predict_proba(x_counterfactual_raw)
```

rather than:

```python
x_counterfactual_raw
    ↓
manual scaling
    ↓
model.predict_proba()
```

The latter recreates preprocessing logic unnecessarily.

This is particularly important because `clinical_pipeline` contains the fitted scaler.

---

# 15. One thing I would NOT change in your plan

Do **not** attempt to make the 2,195 missing GenomeIndia variants "observed."

Your proposed terminology change is the correct solution.

The model can legitimately have:

```text
Observed GenomeIndia frequency
+
Deterministic synthetic prior
```

provided the UI/paper clearly distinguishes them.

Trying to invent a more elaborate "calibration" mechanism now would increase complexity and make the project harder to reproduce.

---

# 16. Suggested revised implementation sequence

I would slightly reorder your plan.

### Phase A - NB4

1. Rename synthetic prior.
2. Dynamically calculate all QC.
3. Ensure missing GI rows have no fake REF/ALT.
4. Regenerate canonical genomic artifacts.

### Phase B - NB7

5. Remove stale comments/terminology.
6. Make NB7 consume canonical prediction artifact.
7. Verify top-gene/context metadata.

### Phase C - NB10

8. Remove test-set SD scaling.
9. Apply raw-unit perturbations.
10. Pass raw counterfactual features through the fitted clinical pipeline.
11. Rename Pulse-grounded outputs.

### Phase D - NB12

12. Remove fallback/self-validating checks.
13. Tighten deterministic comparison tolerances.
14. Verify manifest/provenance/implementation fusion weights.
15. Recompute canonical benchmark metrics from canonical predictions.
16. Actively compute literature deviations.
17. Correct 26+1 assertion terminology.

### Phase E - Release

18. Generate manifest.
19. Hash all critical artifacts.
20. Run NB12.
21. **Only publish the release if all 27 assertions pass.**

This sequence minimizes the chance of chasing mismatched outputs.

---

# 17. The one extra validation I strongly recommend

After all modifications, perform a **two-run reproducibility test**.

Run the complete release pipeline twice:

```text
Run A
→ Release A

Run B
→ Release B
```

Then compare:

```text
canonical harmonization hash
PRS
GBI
clinical predictions
fusion predictions
AUC
Brier
ECE
NB12 JSON
```

They should be identical for deterministic components.

This would be a much stronger demonstration of reproducibility than simply one successful run.

---

# 18. Final approval

I would approve your implementation plan with these additions:

### Add to NB4

> Treat the Beta(2.2,2.0) fallback explicitly as a **deterministic synthetic frequency prior**, not a calibrated GenomeIndia observation.

### Add to NB10

> Apply Pulse-derived deltas in raw clinical units and pass the resulting raw patient state through the **actual fitted clinical pipeline**, eliminating manual/test-set scaling.

### Add to NB12

> Make canonical prediction artifact → canonical benchmark → release manifest a single dependency chain, and verify **manifest = provenance = implementation** for fusion weights.

### Add to verification

> Perform **two complete deterministic release runs** and compare their release artifacts.

With those additions, I think your plan is **complete**.

And importantly, it preserves the architecture you have spent all this time building. It doesn't introduce another NB, another model, or another data source-it makes the existing system **deterministic, auditable, and reproducible**.

The proposed changes themselves are clearly scoped to NB4, NB7, NB10, NB12, and release orchestration, which is exactly where the remaining issues belong. `Rectifications_1.md`



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)