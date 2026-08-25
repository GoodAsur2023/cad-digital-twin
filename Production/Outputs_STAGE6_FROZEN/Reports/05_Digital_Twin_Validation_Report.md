# Digital Twin Validation Report
## Counterfactual State-Transition Engine, 1,000-Fold Bootstrap Uncertainty, and Categorized Sanity Battery

**Project**: Capstone Phase 2 — UE23CS320B  
**Date**: August 2026  
**Classification**: Technical Reference (Stage 7 Hardened)  

---

## 1. Digital Twin Architecture & State Engine

The Precision Cardiology Digital Twin models an individual patient as an integrated multi-domain **Counterfactual State-Transition Model**:

$$
\mathbf{S}_t = \left\{ \mathbf{X}_{\text{clinical}}, \mathbf{X}_{\text{lifestyle}}, \text{PRS}_{\text{population}}, \mathbf{H}_{\text{pulse}}, \hat{P}_{\text{cad}}, \text{CI}_{95} \right\}
$$

```
[Patient Baseline State S_t] ──► [Intervention Challenge] ──► [PulsePhysio Grounding] ──► [Post-Intervention State S_t']
             │                                                                                        │
             ▼                                                                                        ▼
  [Baseline Risk + 95% CI]                                                               [Updated Risk + 95% CI]
```

*Important Scope Definition*: In the absence of longitudinal multi-year panel follow-up data, the Digital Twin is strictly defined as a Counterfactual State-Transition Engine ($S_t \to S_t'$) for model-informed intervention planning rather than an autonomous continuous-time trajectory tracker.

*Non-Causal Implementation Disclaimer*: **Intervention rankings are model-based counterfactual simulations and are not estimates of causal treatment effects or clinical prescriptions.**

---

## 2. Categorized Sanity Check Battery (13/13 PASS Live Re-Executed)

To verify that model counterfactuals respect physiological plausibility and mathematical monotonicity, the battery is split into two distinct categories:

| # | Category | Sanity Test Name | Cohort | Perturbation Applied | Expected Direction | Observed Shift ($\Delta P$) | Result |
|---|:---:|---|:---:|---|:---:|:---:|:---:|
| 1 | **Category A** | Sedentary $\to$ Active | Lifestyle | `physical_activity`: 0 $\to$ 1 | DECREASE | **-0.0365** | ✅ PASS |
| 2 | **Category A** | Normal BMI $\to$ Overweight | Lifestyle | `bmi`: 22 $\to$ 28 | INCREASE | **+0.0509** | ✅ PASS |
| 3 | **Category A** | Normal BMI $\to$ Obese | Lifestyle | `bmi`: 22 $\to$ 35 | INCREASE | **+0.0821** | ✅ PASS |
| 4 | **Category A** | Smoker+Sedentary $\to$ Clean+Active | Lifestyle | `smoking`: 1 $\to$ 0, `activity`: 0 $\to$ 1 | DECREASE | **-0.0097** | ✅ PASS |
| 5 | **Category A** | Smoking Cessation + BP Restoration | Lifestyle | `smoking`: 1 $\to$ 0, `sbp`: 140 $\to$ 125 | DECREASE | **-0.3341** | ✅ PASS |
| 6 | **Category A** | Heavy Alcohol $\to$ Abstinence | Lifestyle | `alcohol`: 1 $\to$ 0, `sbp`: 135 $\to$ 125 | DECREASE | **-0.1869** | ✅ PASS |
| 7 | **Category B** | Normal BP $\to$ Hypertensive | Clinical | `resting_bp`: 120 $\to$ 160 mmHg | INCREASE | **+0.0804** | ✅ PASS |
| 8 | **Category B** | Hypertensive $\to$ Normal BP | Clinical | `resting_bp`: 160 $\to$ 120 mmHg | DECREASE | **-0.0804** | ✅ PASS |
| 9 | **Category B** | Low Chol $\to$ High Chol | Clinical | `cholesterol`: 160 $\to$ 260 mg/dL | INCREASE | **+0.0453** | ✅ PASS |
| 10 | **Category B** | High Chol $\to$ Low Chol | Clinical | `cholesterol`: 260 $\to$ 160 mg/dL | DECREASE | **-0.0453** | ✅ PASS |
| 11 | **Category B** | Low Max HR $\to$ High Max HR | Clinical | `max_heart_rate`: 110 $\to$ 170 bpm | DECREASE | **-0.2217** | ✅ PASS |
| 12 | **Category B** | High Oldpeak $\to$ Zero Oldpeak | Clinical | `oldpeak`: 2.5 $\to$ 0.0 mm | DECREASE | **-0.2214** | ✅ PASS |
| 13 | **Category B** | Comprehensive Risk Normalization | Clinical | BP, Chol, MaxHR, Oldpeak normalized | DECREASE | **-0.6232** | ✅ PASS |

**Categorized Battery Performance**:
- **Category A (Intervention Plausibility Checks)**: **6/6 PASSED** (100.0%) — confirms that lifestyle and clinical improvements reduce predicted risk.
- **Category B (Model Sensitivity & Monotonicity Checks)**: **7/7 PASSED** (100.0%) — confirms mathematical monotonicity across continuous biomarkers without claiming direct causal intervention capability on non-modifiable diagnostic markers.
- **Total Battery**: **13/13 (100.0%) PASS** (verified via live model execution in NB12).

---

## 3. Intervention Realism Constraint Registry

All counterfactual scenario simulations pass through an immutable constraint validation registry to prevent physiologically impossible transitions:
- **Body Mass Index**: Maximum permitted single-step delta $\pm 5.0\text{ kg/m}^2$, physiologically bounded to $[16.0, 55.0]$.
- **Systolic Blood Pressure**: Maximum single-step treatment-responsive shift $\pm 30\text{ mmHg}$, bounded to $[85.0, 220.0]$.
- **Total Serum Cholesterol**: Maximum single-step reduction $-100\text{ mg/dL}$, bounded to $[100.0, 450.0]$.
- **Demographics (Age, Sex)**: Immutable; alterations are rejected by the state engine.
- **Diagnostic Stress Markers (Oldpeak)**: Flagged as non-intervention diagnostic targets.

---

## 4. Bootstrap Uncertainty Quantification ($N=1,000$)

Uncertainty bounds were computed using $N=1,000$ bootstrap resamples with Monte Carlo feature perturbation across representative patient archetypes:

| Patient Profile | Baseline Risk | 95% Confidence Interval | CI Width | Primary Counterfactual Target | Post-Intervention Risk [95% CI] |
|---|:---:|:---:|:---:|---|:---:|
| **P001 (62M, High Risk Smoker)** | **92.2%** | [88.5%, 92.3%] | 0.038 | Comprehensive Risk Factor Control | **38.7%** [31.5%, 44.2%] |
| **P002 (55F, Intermediate Risk)** | **61.8%** | [28.4%, 67.2%] | 0.388 | BP Control + Exercise | **48.9%** [24.1%, 55.3%] |
| **P003 (48F, Low-Intermediate)** | **22.9%** | [22.8%, 23.1%] | 0.003 | Lifestyle Maintenance | **21.5%** [21.4%, 21.8%] |

---

## 5. Cohort-Wide Counterfactual Intervention Shifts (n=238)

Average risk shifts across the 238 CAD patients in the clinical cohort ($\Delta P = P_{\text{post}} - P_{\text{baseline}}$):
1. **Exercise HR/BP Adaptation (`S2`)**: Mean $\Delta P = \mathbf{-0.1293}$ (-12.93% risk reduction).
2. **Comprehensive Multi-Factor Control (`S5`)**: Mean $\Delta P = \mathbf{-0.1163}$ (-11.63% risk reduction).
3. **5% Weight Loss + BP Improvement (`S3`)**: Mean $\Delta P = \mathbf{-0.1135}$ (-11.35% risk reduction).
4. **Cholesterol & Diet Optimization (`S4`)**: Mean $\Delta P = \mathbf{-0.0818}$ (-8.18% risk reduction).
5. **Smoking Cessation Hemodynamics (`S1`)**: Mean $\Delta P = \mathbf{-0.0169}$ (-1.69% risk reduction).

---

## 6. Illustrative ACC/AHA Clinical Decision Support Context Mapping

| Model-Estimated Probability | Illustrative Category | Statin Guidance Context | Illustrative Clinical Action Plan |
|---|---|---|---|
| $< 5.0\%$ | Low Risk | Not indicated | Primary lifestyle counseling; reassess at routine intervals |
| $5.0\% - 7.5\%$ | Borderline Risk | Consider if risk enhancers present | Moderate-intensity statin + lifestyle optimization |
| $7.5\% - 20.0\%$ | Intermediate Risk | Moderate-intensity statin | Target LDL reduction 30–49%; coronary calcium scoring consideration |
| $> 20.0\%$ | High Risk | High-intensity statin | Target LDL reduction $\ge 50\%$; consider PCSK9 inhibitor evaluation |

*Disclaimer: Research prototype for clinical decision support illustration; model estimates cross-sectional angiographic CAD probability (>50% stenosis), not prospective 10-year ASCVD survival risk.*

---
*Report generated from computational pipeline NB9. All values verified against canonical metrics in `Outputs/Digital_Twin/patient_states.json`.*