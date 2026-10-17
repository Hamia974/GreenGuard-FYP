"""Internal Module 2 orchestration and weighted scoring.

Module 2 is the only externally reachable soil/nutrient endpoint. It performs no ML and
no rule lookups of its own: it splits the incoming submission, calls Module 2A and
Module 2B, and combines their results with the heuristic score defined in
docs/Module2_Orchestrator_Spec.md Section 3 and the farmer-facing notes built by
recommendations.py.

The score is a transparent, tunable weighted sum -- not a trained or validated model.
It is documented as such in the spec and should be presented that way.
"""

from module2a_service import get_model_version, get_trained_crops, predict_nutrient_risks
from module2b_service import compare_growing_conditions
from recommendations import build_recommendation_notes
from schemas import SUPPORTED_CROPS

ORCHESTRATOR_VERSION = "module2-orchestrator-v1"

# Weights sum to 100. Rationale in Module2_Orchestrator_Spec.md Section 3: N/P/K carry
# 3x the weight of Mg/Zn/B (agronomic primacy + stronger model performance), and pH
# carries the single largest weight because it gates availability of everything else.
SCORE_WEIGHTS = {
    "nitrogen_risk": 15,
    "phosphorus_risk": 15,
    "potassium_risk": 15,
    "magnesium_risk": 5,
    "zinc_risk": 5,
    "boron_risk": 5,
    "ph": 20,
    "soil_moisture": 10,
    "light": 10,
}

# Cucurbitaceae (cucumber + the 4 gourds -- NOT eggplant, which is Solanaceae) are
# documented (agronomy literature; see docs/MODEL_DOCUMENTATION.md and
# docs/Module2A_Engineering_Handoff.md Section 7a) as more zinc- and boron-sensitive
# than the other trained crops. Per agronomy review GG-M2-AR-01 (Sabra Anwar, UCP,
# 2026-09-13), which flagged the flat weighting as not reflecting per-crop importance:
# N/P/K trimmed 2 points each (15->13) to fund raising Zn/B 3 points each (5->8).
# Total stays 100. This is still a tunable heuristic, not a validated weighting --
# same caveat as SCORE_WEIGHTS above.
CUCURBIT_CROPS = {
    "cucumber", "bitter_gourd", "snake_gourd", "ridge_gourd", "ash_gourd", "bottle_gourd",
}
CUCURBIT_SCORE_WEIGHTS = {
    **SCORE_WEIGHTS,
    "nitrogen_risk": 13, "phosphorus_risk": 13, "potassium_risk": 13,
    "zinc_risk": 8, "boron_risk": 8,
}
assert sum(CUCURBIT_SCORE_WEIGHTS.values()) == 100

# Potato is a well-documented heavy potassium feeder -- K deficiency disproportionately
# hurts tuber size/quality relative to other crops. Per agronomy review GG-M2-AR-02
# (Numan Niaz, Dogar Agri Farm owner, 10 yrs experience specifically in potato/maize/
# wheat/rice, 2026-09-15): "potassium matters more in potato." N/P trimmed 2 points
# each (15->13) to fund raising K 4 points (15->19). Total stays 100.
POTATO_SCORE_WEIGHTS = {
    **SCORE_WEIGHTS,
    "nitrogen_risk": 13, "phosphorus_risk": 13, "potassium_risk": 19,
}
assert sum(POTATO_SCORE_WEIGHTS.values()) == 100

CROP_WEIGHT_OVERRIDES = {crop: CUCURBIT_SCORE_WEIGHTS for crop in CUCURBIT_CROPS}
CROP_WEIGHT_OVERRIDES["potato"] = POTATO_SCORE_WEIGHTS


def _weights_for(crop: str | None) -> dict:
    return CROP_WEIGHT_OVERRIDES.get(crop, SCORE_WEIGHTS)

# Module 2A speaks low/medium/high; Module 2B speaks ok/moderate/critical.
SEVERITY_FRACTION = {
    "low": 1.0, "medium": 0.5, "high": 0.0,
    "ok": 1.0, "moderate": 0.5, "critical": 0.0,
}

MODULE2A_FIELDS = (
    "crop", "growth_stage", "soil_type", "last_fertilizer_type", "days_since_fertilizer",
    "irrigation_source", "irrigation_adequacy", "temperature_c", "humidity_pct",
    "rainfall_mm_last_7_days", "symptoms",
)
MODULE2B_FIELDS = ("crop", "ph_value", "soil_moisture_pct", "light_intensity_lux")

RISK_TARGETS = (
    "nitrogen_risk", "phosphorus_risk", "potassium_risk",
    "magnesium_risk", "zinc_risk", "boron_risk",
)


def calculate_soil_health_score(module2a_result: dict, module2b_result: dict,
                                 crop: str | None = None) -> dict:
    """Combine 2A and 2B severities into a 0-100 score plus its bucket label.

    Pure function over the two sub-results (plus the crop, only to pick a weight set),
    so it can be tested independently of the models -- see the spec's worked example,
    which must yield 52.5 / "moderate" (uses the default, non-cucurbit weights since
    `crop` is omitted).
    """
    weights = _weights_for(crop)
    score = 0.0
    for target in RISK_TARGETS:
        level = module2a_result[target]["level"]
        score += weights[target] * SEVERITY_FRACTION[level]

    for factor in ("ph", "soil_moisture", "light"):
        status = module2b_result[factor]["status"]
        score += weights[factor] * SEVERITY_FRACTION[status]

    score = round(score, 2)
    if score >= 80:
        label = "good"
    elif score >= 50:
        label = "moderate"
    else:
        label = "poor"
    return {"overall_soil_health_score": score, "overall_soil_health_label": label}


def analyze_soil(payload: dict) -> dict:
    """Call Module 2A and 2B, then combine their results into the public response."""
    crop = payload["crop"]
    # Screened against both the public contract and what Module 2A was actually trained
    # on. Those two lists are maintained in different files, so checking only one would
    # turn any future divergence into a 500 instead of this documented response.
    if crop not in SUPPORTED_CROPS or crop not in get_trained_crops():
        return {
            "crop_supported": False,
            "message": "Nutrient and soil-condition analysis isn't available yet for this crop.",
            "module2a": None,
            "module2b": None,
            "overall_soil_health_score": None,
            "overall_soil_health_label": None,
            "recommendation_notes": None,
        }

    module2a_result = predict_nutrient_risks({k: payload[k] for k in MODULE2A_FIELDS})
    module2b_result = compare_growing_conditions({k: payload[k] for k in MODULE2B_FIELDS})
    # Built from the farmer's full submission: the explanations cite what they reported.
    notes = build_recommendation_notes(payload, module2a_result, module2b_result)

    # 2B answers per-crop; if it can't serve this crop the weighted score would be
    # missing 40 of its 100 points, so the score is withheld rather than reported low.
    if not module2b_result.get("crop_supported", False):
        return {
            "crop_supported": True,
            "module2a": module2a_result,
            "module2b": module2b_result,
            "overall_soil_health_score": None,
            "overall_soil_health_label": None,
            "recommendation_notes": notes,
            "message": module2b_result.get(
                "message", "Growing-conditions comparison isn't available for this crop."
            ),
            "model_version": ORCHESTRATOR_VERSION,
            "module2a_model_version": get_model_version(),
        }

    scored = calculate_soil_health_score(module2a_result, module2b_result, crop=crop)
    return {
        "crop_supported": True,
        "module2a": module2a_result,
        "module2b": module2b_result,
        **scored,
        "recommendation_notes": notes,
        "model_version": ORCHESTRATOR_VERSION,
        "module2a_model_version": get_model_version(),
    }
