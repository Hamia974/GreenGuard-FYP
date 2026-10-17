"""Tests for the farmer-facing text layer (api/recommendations.py).

This module decides what a farmer actually reads, so its defects are user-visible even
when every model metric is healthy. Two real ones were fixed here previously and had no
coverage at the time:

  - a zinc-specific lockout explanation was being shown under the Phosphorus heading
  - a 36%-confidence "high risk" was headlined alongside a 99%-confidence one

Both are pinned below.

Run from Stress_Module with: pytest tests/test_recommendations.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

from recommendations import (  # noqa: E402
    HEADLINE_CONFIDENCE_FLOOR,
    build_recommendation_notes,
    confidence_phrase,
    explain,
)

SYMPTOM_KEYS = [
    "yellowing_older_leaves", "purple_reddish_tint", "brown_scorched_leaf_edges",
    "stunted_growth", "poor_flowering_or_fruiting", "weak_stems",
    "interveinal_chlorosis_older_leaves", "interveinal_chlorosis_young_leaves",
    "leaf_curling_brittle", "short_internodes_small_leaves", "none_visible",
]
RISK_TARGETS = ["nitrogen_risk", "phosphorus_risk", "potassium_risk",
                "magnesium_risk", "zinc_risk", "boron_risk"]


def _payload(**overrides) -> dict:
    base = {
        "crop": "wheat", "growth_stage": "vegetative", "soil_type": "loamy",
        "last_fertilizer_type": "NPK_blend", "days_since_fertilizer": "lt_15_days",
        "irrigation_source": "drip", "irrigation_adequacy": "adequate",
        "symptoms": {**{k: False for k in SYMPTOM_KEYS}, "none_visible": True},
    }
    base.update(overrides)
    return base


def _module2a(**levels) -> dict:
    """Build a 2A-shaped result; unspecified nutrients default to confident low."""
    result = {t: {"level": "low", "confidence": 0.9} for t in RISK_TARGETS}
    for target, (level, confidence) in levels.items():
        result[target] = {"level": level, "confidence": confidence}
    result["overall_nutrient_health"] = "moderate"
    result["input_typicality"] = {"anomaly_score": 0.05, "flag": "typical"}
    return result


# --- Confidence wording -------------------------------------------------------------

@pytest.mark.parametrize("confidence,expected_pct,expected_word", [
    (0.96, "96%", "strong match"),
    (0.85, "85%", "strong match"),
    (0.72, "72%", "likely"),
    (0.58, "58%", "possible"),
    (0.36, "36%", "based on limited signs"),
])
def test_confidence_phrase_tiers(confidence, expected_pct, expected_word):
    phrase = confidence_phrase(confidence)
    assert expected_pct in phrase
    assert expected_word in phrase


def test_confidence_is_always_shown_as_a_percentage():
    for confidence in (0.33, 0.5, 0.667, 1.0):
        assert "%" in confidence_phrase(confidence)


# --- Explanations must be nutrient-appropriate --------------------------------------

def test_saline_explanation_is_specific_per_nutrient():
    """Regression: a zinc lockout note used to appear under the Phosphorus heading."""
    payload = _payload(soil_type="saline_affected")

    zinc = explain("zinc_risk", payload)
    phosphorus = explain("phosphorus_risk", payload)

    assert "zinc" in zinc.lower()
    assert "zinc" not in phosphorus.lower()
    assert "calcium" in phosphorus.lower()


def test_explanation_cites_the_farmers_own_reported_inputs():
    payload = _payload(
        soil_type="sandy", last_fertilizer_type="No_Fertilizer",
        days_since_fertilizer="not_applicable",
        symptoms={**{k: False for k in SYMPTOM_KEYS}, "yellowing_older_leaves": True},
    )
    reason = explain("nitrogen_risk", payload)
    assert "yellowing" in reason
    assert "sandy" in reason
    assert "no fertilizer" in reason


def test_explanation_falls_back_when_nothing_notable_reported():
    assert "overall pattern" in explain("boron_risk", _payload())


# --- Headline ranking ---------------------------------------------------------------

def test_low_confidence_high_risk_is_not_headlined():
    """Regression: a 36%-confidence high risk was headlined next to a 99% one."""
    notes = build_recommendation_notes(
        _payload(),
        _module2a(nitrogen_risk=("high", 0.99), magnesium_risk=("high", 0.36)),
    )
    assert "Nitrogen" in notes["headline"]
    assert "Magnesium" not in notes["headline"]
    # Still reported, just not presented as urgent.
    assert any(item["nutrient"] == "Magnesium" for item in notes["needs_attention"])


def test_concerns_sorted_by_severity_then_confidence():
    notes = build_recommendation_notes(
        _payload(),
        _module2a(nitrogen_risk=("high", 0.60), phosphorus_risk=("high", 0.95),
                  potassium_risk=("medium", 0.90)),
    )
    order = [item["nutrient"] for item in notes["needs_attention"]]
    assert order == ["Phosphorus", "Nitrogen", "Potassium"]


def test_headline_grammar_singular_and_plural():
    single = build_recommendation_notes(_payload(), _module2a(nitrogen_risk=("high", 0.9)))
    assert "Nitrogen needs attention" in single["headline"]

    plural = build_recommendation_notes(
        _payload(), _module2a(nitrogen_risk=("high", 0.9), zinc_risk=("high", 0.9)))
    assert "need attention" in plural["headline"]
    assert "and" in plural["headline"]


def test_all_low_gives_a_reassuring_headline():
    notes = build_recommendation_notes(_payload(), _module2a())
    assert "No nutrient problems" in notes["headline"]
    assert notes["needs_attention"] == []
    assert len(notes["looking_fine"]) == 6


def test_limited_sign_concerns_are_watched_not_urgent():
    notes = build_recommendation_notes(
        _payload(), _module2a(boron_risk=("high", 0.40), zinc_risk=("medium", 0.45)))
    assert notes["headline"].startswith("Keep an eye on")
    assert "attention first" not in notes["headline"]


def test_headline_floor_is_the_documented_threshold():
    just_under = build_recommendation_notes(
        _payload(), _module2a(zinc_risk=("high", (HEADLINE_CONFIDENCE_FLOOR - 1) / 100)))
    just_over = build_recommendation_notes(
        _payload(), _module2a(zinc_risk=("high", (HEADLINE_CONFIDENCE_FLOOR + 1) / 100)))
    assert just_under["headline"] == "Keep an eye on Zinc."
    assert "needs attention first" in just_over["headline"]


def test_farmer_wording_stays_positive():
    """Low-confidence results are described by the signs behind them, never as doubtful."""
    notes = build_recommendation_notes(
        _payload(), _module2a(boron_risk=("high", 0.40), zinc_risk=("low", 0.36)))
    text = " ".join([notes["headline"], notes["caveat"]] + [
        item["confidence_text"] for item in notes["needs_attention"] + notes["looking_fine"]])
    for word in ("unclear", "confirm", "not certain", "unsure", "carefully"):
        assert word not in text.lower(), word


# --- Structure and caveats ----------------------------------------------------------

def test_notes_always_carry_the_advisory_caveat():
    notes = build_recommendation_notes(_payload(), _module2a())
    assert "soil-meter readings" in notes["caveat"]
    assert "soil lab test" in notes["caveat"]


def test_unusual_input_adds_a_reliability_note():
    result = _module2a(nitrogen_risk=("high", 0.9))
    result["input_typicality"] = {"anomaly_score": -0.14, "flag": "unusual"}
    notes = build_recommendation_notes(_payload(), result)
    assert "reliability_note" in notes
    assert "agriculture officer" in notes["reliability_note"]


def test_typical_input_adds_no_reliability_note():
    notes = build_recommendation_notes(_payload(), _module2a(nitrogen_risk=("high", 0.9)))
    assert "reliability_note" not in notes


def test_soil_condition_note_only_when_ph_is_off():
    """Module 2B reports pH status as ok/moderate/critical; the note must appear only for
    moderate/critical. Built from real 2B output so the two layers can't drift apart."""
    import module2b_service

    result = _module2a()
    reading = {"crop": "wheat", "soil_moisture_pct": 60, "light_intensity_lux": 30000}

    healthy = module2b_service.compare_growing_conditions({**reading, "ph_value": 6.8})
    assert healthy["ph"]["status"] == "ok"
    assert "soil_condition_note" not in build_recommendation_notes(_payload(), result, healthy)

    acidic = module2b_service.compare_growing_conditions({**reading, "ph_value": 4.6})
    assert acidic["ph"]["status"] == "critical"
    notes = build_recommendation_notes(_payload(), result, acidic)
    assert notes["soil_condition_note"] == acidic["ph"]["nutrient_lockout_note"]


def test_confident_medium_headline_is_not_called_uncertain():
    notes = build_recommendation_notes(_payload(), _module2a(potassium_risk=("medium", 0.90)))
    assert notes["headline"] == "Potassium may need attention."


def test_every_nutrient_appears_exactly_once():
    notes = build_recommendation_notes(
        _payload(), _module2a(nitrogen_risk=("high", 0.9), zinc_risk=("medium", 0.7)))
    named = [item["nutrient"] for item in notes["needs_attention"] + notes["looking_fine"]]
    assert len(named) == 6
    assert len(set(named)) == 6
