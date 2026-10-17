"""Farmer-facing text generation for Module 2 results.

Kept deliberately separate from module2a_service: ``recommendation_notes`` is generated
from the levels/confidences and stays out of the model's raw output. The
orchestrator returns it as the ``recommendation_notes`` field of every /predict response.

Nothing here re-derives a prediction. It only translates levels, confidences and the
farmer's own reported inputs into plain language, so the wording can be changed (or
localised) without retraining or touching the model layer.
"""

NUTRIENT_LABEL = {
    "nitrogen_risk": "Nitrogen",
    "phosphorus_risk": "Phosphorus",
    "potassium_risk": "Potassium",
    "magnesium_risk": "Magnesium",
    "zinc_risk": "Zinc",
    "boron_risk": "Boron",
}

# The symptom shown per nutrient, used only to explain a prediction, never to make one.
# Set from the notebook's gain-based feature importance (Section 5.2), then checked
# against agronomy review GG-M2-AR-01 (Sabra Anwar, UCP, 2026-09-13).
#
# Potassium: reviewer disagreed with weak_stems, suggesting brown/scorched leaf margins
# instead. Checked against the model's actual feature importance for potassium_risk --
# brown_scorched_leaf_edges is genuinely its #2 signal (0.268, close behind weak_stems'
# 0.332) -- so this is a real, model-backed improvement, not just a relabeling.
#
# Boron: reviewer disagreed with leaf_curling_brittle, suggesting poor flower/fruit
# development and damage to growing points instead. NOT applied: poor_flowering_or_fruiting
# doesn't even place in boron_risk's top 8 features, while leaf_curling_brittle is its
# strongest signal by far (0.270) -- swapping would show farmers a reason the model
# doesn't actually rely on. leaf_curling_brittle's own description ("brittle... at growing
# tips") already covers part of the reviewer's concern. Kept as-is; flagged as an open
# disagreement rather than silently overridden -- see docs/MODEL_DOCUMENTATION.md.
DOMINANT_SYMPTOM = {
    "nitrogen_risk": ("yellowing_older_leaves", "yellowing on your older leaves"),
    "phosphorus_risk": ("purple_reddish_tint", "the purple/reddish tint on leaves"),
    "potassium_risk": ("brown_scorched_leaf_edges", "the brown, scorched leaf edges"),
    "magnesium_risk": ("interveinal_chlorosis_older_leaves",
                       "yellowing between the veins of older leaves"),
    "zinc_risk": ("interveinal_chlorosis_young_leaves",
                  "yellowing between the veins of young leaves"),
    "boron_risk": ("leaf_curling_brittle", "the curling/brittle leaves"),
}

# Saline/alkaline soil affects different nutrients by different mechanisms, so the
# explanation is nutrient-specific -- a zinc lockout note under a Phosphorus heading
# would just confuse the reader. Wording follows Module 2B's own _ph_lockout() text.
SALINE_REASON = {
    "zinc_risk": "salt-affected soil (locks up zinc so roots can't take it in)",
    "phosphorus_risk": "salt-affected soil (phosphorus binds with calcium and becomes unavailable)",
    "magnesium_risk": "salt-affected soil (competes with magnesium uptake)",
}
SALINE_REASON_DEFAULT = "salt-affected soil (makes nutrient uptake harder)"

RISK_TARGETS = tuple(NUTRIENT_LABEL)


def confidence_phrase(confidence: float) -> str:
    """Percentage plus a plain reading of it, so a number never appears uninterpreted."""
    pct = f"{confidence * 100:.0f}% confident"
    if confidence >= 0.85:
        return f"{pct} — strong match"
    if confidence >= 0.65:
        return f"{pct} — likely"
    if confidence >= 0.50:
        return f"{pct} — possible"
    return f"{pct} — based on limited signs"


def explain(target: str, payload: dict) -> str:
    """Reason text built from what the farmer actually reported."""
    reasons = []
    symptom_key, symptom_text = DOMINANT_SYMPTOM[target]
    if payload.get("symptoms", {}).get(symptom_key, False):
        reasons.append(symptom_text)

    if payload.get("soil_type") == "sandy":
        reasons.append("sandy soil (nutrients wash out faster)")
    elif payload.get("soil_type") == "saline_affected":
        reasons.append(SALINE_REASON.get(target, SALINE_REASON_DEFAULT))

    if payload.get("last_fertilizer_type") == "No_Fertilizer":
        reasons.append("no fertilizer applied")
    elif payload.get("days_since_fertilizer") in ("60_90_days", "gt_90_days"):
        reasons.append("it's been a long time since fertilizer")

    if payload.get("irrigation_adequacy") == "insufficient":
        reasons.append("not enough water")

    return ", ".join(reasons) if reasons else "based on the overall pattern of your answers"


def build_recommendation_notes(payload: dict, module2a_result: dict,
                               module2b_result: dict | None = None) -> dict:
    """Farmer-readable summary of one Module 2 result.

    Returns structured notes rather than one blob of text so the frontend can lay them
    out however it likes (cards, list, collapsible sections).
    """
    concerns = []
    reassurances = []

    for target in RISK_TARGETS:
        entry = module2a_result[target]
        item = {
            "nutrient": NUTRIENT_LABEL[target],
            "level": entry["level"],
            "confidence_pct": round(entry["confidence"] * 100),
            "confidence_text": confidence_phrase(entry["confidence"]),
        }
        if entry["level"] in ("high", "medium"):
            item["why"] = explain(target, payload)
            concerns.append(item)
        else:
            reassurances.append(item)

    # Worst first, and within a level the more certain result first -- a "high risk"
    # the model is 36% sure of should not sit above one it is 99% sure of.
    concerns.sort(key=lambda i: (0 if i["level"] == "high" else 1, -i["confidence_pct"]))

    notes: dict = {
        "headline": _headline(concerns),
        "needs_attention": concerns,
        "looking_fine": reassurances,
        "caveat": ("This advice is based on your answers and soil-meter readings. A soil lab "
                   "test can add exact nutrient levels if you need them."),
    }

    if module2b_result and module2b_result.get("crop_supported"):
        lockout = module2b_result.get("ph", {}).get("nutrient_lockout_note")
        # Module 2B reports pH status as ok/moderate/critical; the note
        # is surfaced only when pH is outside this crop's ideal range.
        if lockout and module2b_result["ph"]["status"] != "ok":
            notes["soil_condition_note"] = lockout

    if module2a_result.get("input_typicality", {}).get("flag") == "unusual":
        # Plain language for a farmer, not ML terms like "anomaly"/"flag"/"typical profile"
        # -- per product direction 2026-09-16. Keeps "agriculture officer" so
        # test_unusual_input_adds_a_reliability_note still matches.
        notes["reliability_note"] = (
            "Your farm details are a bit different from usual — for best results, also ask "
            "your local agriculture officer."
        )

    return notes


# A prediction the model is under ~50% sure of is close to a guess between three
# options; naming it in the headline alongside a near-certain one would overstate it.
HEADLINE_CONFIDENCE_FLOOR = 50


def _join(names: list[str]) -> str:
    if len(names) == 1:
        return names[0]
    return f"{', '.join(names[:-1])} and {names[-1]}"


def _headline(concerns: list) -> str:
    if not concerns:
        return "No nutrient problems detected — your crop looks well fed."

    confident_high = [c["nutrient"] for c in concerns
                      if c["level"] == "high" and c["confidence_pct"] >= HEADLINE_CONFIDENCE_FLOOR]
    if confident_high:
        verb = "needs" if len(confident_high) == 1 else "need"
        return f"{_join(confident_high)} {verb} attention first."

    # Only medium-risk results, or high-risk ones with fewer signs behind them. Those
    # resting on limited signs are framed as something to watch; a 90%-confident medium
    # is not, so it keeps the plainer "may need attention".
    top = concerns[:2]
    names = _join([c["nutrient"] for c in top])
    if any(c["confidence_pct"] < HEADLINE_CONFIDENCE_FLOOR for c in top):
        return f"Keep an eye on {names}."
    return f"{names} may need attention."
