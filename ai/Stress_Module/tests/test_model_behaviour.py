"""Behavioural tests for the SERVED Module 2A models.

test_api.py verifies the API's plumbing -- that requests validate, route and return the
right shape. These tests verify something different and, for an ML service, more
fragile: that the artifacts actually sitting in models/ still behave sensibly.

Without these, a degraded retrain, a stale artifact, or an encoder/model mismatch would
pass the entire existing suite unnoticed, because every response would still have the
correct *shape*.

The directional checks mirror the property-based suite in
training/module2a_nutrient_risk.ipynb (Section 5.5), but run against the loaded
production artifacts rather than in-memory objects from the training session.

A failure here means "investigate", not automatically "bug" -- the underlying rules can
have interaction effects a single-variable check cannot capture.

Run from Stress_Module with: pytest tests/test_model_behaviour.py -v
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import module2a_service  # noqa: E402

LEVEL_ORDER = {"low": 0, "medium": 1, "high": 2}

SYMPTOM_KEYS = [
    "yellowing_older_leaves", "purple_reddish_tint", "brown_scorched_leaf_edges",
    "stunted_growth", "poor_flowering_or_fruiting", "weak_stems",
    "interveinal_chlorosis_older_leaves", "interveinal_chlorosis_young_leaves",
    "leaf_curling_brittle", "short_internodes_small_leaves", "none_visible",
]

# Neutral, healthy baseline: loamy soil, just fertilised, adequate water, no symptoms.
# Every check below changes exactly one thing from here.
NEUTRAL_BASE = {
    "crop": "wheat", "growth_stage": "vegetative", "soil_type": "loamy",
    "last_fertilizer_type": "NPK_blend", "days_since_fertilizer": "lt_15_days",
    "irrigation_source": "drip", "irrigation_adequacy": "adequate",
    "temperature_c": 26.0, "humidity_pct": 60.0, "rainfall_mm_last_7_days": 10.0,
    "ph_value": 6.5, "soil_moisture_pct": 60.0, "light_intensity_lux": 30000.0,
    "symptoms": {**{k: False for k in SYMPTOM_KEYS}, "none_visible": True},
}


def _with(**overrides) -> dict:
    payload = dict(NEUTRAL_BASE)
    symptoms = overrides.pop("symptoms", None)
    if symptoms:
        merged = {k: False for k in SYMPTOM_KEYS}
        merged.update(symptoms)
        merged["none_visible"] = not any(v for k, v in merged.items() if k != "none_visible")
        payload["symptoms"] = merged
    payload.update(overrides)
    return payload


def _level(payload: dict, target: str) -> int:
    return LEVEL_ORDER[module2a_service.predict_nutrient_risks(payload)[target]["level"]]


# --- Artifact integrity -------------------------------------------------------------

def test_all_artifacts_load():
    art = module2a_service._get_artifacts()
    assert len(art.models) == 6
    assert art.encoder is not None
    assert art.anomaly_detector is not None
    assert art.model_version.startswith("module2a-")


def test_models_agree_with_shipped_schema():
    """Catches 'notebook retrained but schema.json wasn't updated' mismatches."""
    art = module2a_service._get_artifacts()
    expected_features = len(art.feature_columns)

    for target, model in art.models.items():
        assert model.n_features_in_ == expected_features, target
        assert len(model.classes_) == 3, target

    assert art.anomaly_detector.n_features_in_ == expected_features
    assert art.encoder.n_features_in_ == len(art.categorical_features)
    assert set(art.level_map) == {"low", "medium", "high"}


def test_overall_health_rule_covers_every_reachable_sum():
    """N/P/K each contribute 0-2, so sums 0..6 must all be mapped."""
    art = module2a_service._get_artifacts()
    assert set(art.overall_rule) == set(range(7))


# --- Directional behaviour (mirrors notebook Section 5.5) ---------------------------

DOMINANT_SYMPTOM = [
    ("nitrogen_risk", "yellowing_older_leaves"),
    ("phosphorus_risk", "purple_reddish_tint"),
    # brown_scorched_leaf_edges per agronomy review GG-M2-AR-01 -- see recommendations.py.
    ("potassium_risk", "brown_scorched_leaf_edges"),
    ("magnesium_risk", "interveinal_chlorosis_older_leaves"),
    ("zinc_risk", "interveinal_chlorosis_young_leaves"),
    ("boron_risk", "leaf_curling_brittle"),
]


@pytest.mark.parametrize("target,symptom", DOMINANT_SYMPTOM)
def test_dominant_symptom_never_lowers_its_own_nutrient_risk(target, symptom):
    baseline = _level(NEUTRAL_BASE, target)
    with_symptom = _level(_with(symptoms={symptom: True}), target)
    assert with_symptom >= baseline, f"{symptom} lowered {target}"


def test_sandy_soil_does_not_lower_nitrogen_risk():
    assert _level(_with(soil_type="sandy"), "nitrogen_risk") >= _level(NEUTRAL_BASE, "nitrogen_risk")


def test_no_fertilizer_does_not_lower_nitrogen_risk():
    starved = _with(last_fertilizer_type="No_Fertilizer", days_since_fertilizer="not_applicable")
    assert _level(starved, "nitrogen_risk") >= _level(NEUTRAL_BASE, "nitrogen_risk")


def test_long_gap_since_fertilizer_does_not_lower_nitrogen_risk():
    assert _level(_with(days_since_fertilizer="gt_90_days"), "nitrogen_risk") >= \
           _level(NEUTRAL_BASE, "nitrogen_risk")


def test_recent_fertilizer_does_not_raise_risk_versus_none():
    starved = _with(last_fertilizer_type="No_Fertilizer", days_since_fertilizer="not_applicable")
    assert _level(NEUTRAL_BASE, "nitrogen_risk") <= _level(starved, "nitrogen_risk")


@pytest.mark.parametrize("target", ["magnesium_risk", "boron_risk"])
def test_saline_soil_does_not_lower_micronutrient_risk(target):
    assert _level(_with(soil_type="saline_affected"), target) >= _level(NEUTRAL_BASE, target)


# --- v4 dataset relationships must survive into the served model --------------------

def test_saline_soil_raises_zinc_risk():
    """The saline zinc-lockout relationship (docs/MODEL_DOCUMENTATION.md, Training data) must be learnable and
    actually present in the shipped model, not just in the CSV."""
    assert _level(_with(soil_type="saline_affected"), "zinc_risk") > \
           _level(NEUTRAL_BASE, "zinc_risk")


def test_cucurbit_risk_factors_raise_zinc_versus_clean_conditions():
    """Cucurbit prior (docs/MODEL_DOCUMENTATION.md, Training data): sandy soil or insufficient irrigation."""
    clean = _with(crop="bottle_gourd")
    stressed = _with(crop="bottle_gourd", soil_type="sandy", irrigation_adequacy="insufficient")
    assert _level(stressed, "zinc_risk") >= _level(clean, "zinc_risk")


def test_healthy_input_predicts_low_risk_across_the_board():
    """Well-fed crop, no symptoms, good conditions -- a model that flags problems here
    is broken regardless of its aggregate metrics."""
    result = module2a_service.predict_nutrient_risks(NEUTRAL_BASE)
    levels = [result[t]["level"] for t in module2a_service._get_artifacts().risk_targets]
    assert all(level == "low" for level in levels), levels
    assert result["overall_nutrient_health"] == "good"


def test_severe_case_is_not_reported_as_healthy():
    severe = _with(
        soil_type="sandy", last_fertilizer_type="No_Fertilizer",
        days_since_fertilizer="not_applicable", irrigation_adequacy="insufficient",
        symptoms={"yellowing_older_leaves": True, "stunted_growth": True},
    )
    result = module2a_service.predict_nutrient_risks(severe)
    assert result["nitrogen_risk"]["level"] in {"medium", "high"}
    assert result["overall_nutrient_health"] != "good"


# --- Confidence and typicality ------------------------------------------------------

def test_confidences_are_valid_probabilities():
    art = module2a_service._get_artifacts()
    result = module2a_service.predict_nutrient_risks(NEUTRAL_BASE)
    for target in art.risk_targets:
        confidence = result[target]["confidence"]
        # Lower bound is 1/3: the top class of three can never be less likely than even.
        assert 0.33 <= confidence <= 1.0, (target, confidence)


def test_typicality_flags_plausible_inputs_as_typical():
    """The detector must not cry wolf on ordinary submissions -- an earlier
    misconfiguration flagged most of the training set itself as unusual."""
    art = module2a_service._get_artifacts()
    unusual = 0
    checked = 0
    for crop in sorted(art.trained_crops):
        for soil in ("loamy", "sandy", "clay", "saline_affected"):
            result = module2a_service.predict_nutrient_risks(_with(crop=crop, soil_type=soil))
            unusual += result["input_typicality"]["flag"] == "unusual"
            checked += 1
    assert unusual / checked < 0.20, f"{unusual}/{checked} plausible inputs flagged unusual"


def test_typicality_flags_a_contradictory_input_as_unusual():
    contradictory = _with(
        crop="bottle_gourd", growth_stage="maturity", soil_type="saline_affected",
        last_fertilizer_type="FYM_compost", days_since_fertilizer="gt_90_days",
        irrigation_source="flood_basin", irrigation_adequacy="excessive",
        temperature_c=47.0, humidity_pct=94.0, rainfall_mm_last_7_days=128.0,
        symptoms={k: True for k in SYMPTOM_KEYS if k != "none_visible"},
    )
    result = module2a_service.predict_nutrient_risks(contradictory)
    assert result["input_typicality"]["flag"] == "unusual"


# --- Determinism, latency, concurrency ----------------------------------------------

def test_predictions_are_deterministic():
    first = module2a_service.predict_nutrient_risks(NEUTRAL_BASE)
    second = module2a_service.predict_nutrient_risks(NEUTRAL_BASE)
    assert first == second


def test_warm_prediction_latency_is_acceptable():
    module2a_service.predict_nutrient_risks(NEUTRAL_BASE)  # ensure artifacts are warm
    start = time.perf_counter()
    for _ in range(10):
        module2a_service.predict_nutrient_risks(NEUTRAL_BASE)
    per_call_ms = (time.perf_counter() - start) / 10 * 1000
    assert per_call_ms < 500, f"{per_call_ms:.0f}ms per warm prediction"


def test_concurrent_predictions_are_consistent():
    """The artifact cache is populated under a lock; concurrent first-callers must not
    race into partially-initialised state or disagree on the answer."""
    expected = module2a_service.predict_nutrient_risks(NEUTRAL_BASE)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(
            lambda _: module2a_service.predict_nutrient_risks(NEUTRAL_BASE), range(24)))
    assert all(result == expected for result in results)


# --- Reported metrics must be honest ------------------------------------------------

def test_reported_metrics_come_from_a_leak_free_split():
    """The model card's held-out scores must reproduce on the notebook's split, and that
    split must never place an identical input combination on both sides.

    If copied rows straddle the split, every held-out score is inflated while all the
    other tests in this suite keep passing -- this is the only check that notices.
    """
    from pathlib import Path

    import pandas as pd
    from sklearn.metrics import f1_score
    from sklearn.model_selection import StratifiedGroupKFold

    base = Path(__file__).resolve().parent.parent
    art = module2a_service._get_artifacts()
    card = json.loads((base / "models" / "module2a_model_card.json").read_text(encoding="utf-8"))
    data_path = base / "data" / "module2_farmer.csv"
    if not data_path.exists():
        pytest.skip("training data is not shipped in the delivery package "
                    "(AI_MODULE_DELIVERY_SPECIFICATION.md Section 4.13)")
    df = pd.read_csv(data_path)

    X = df[art.feature_columns].copy()
    X[art.categorical_features] = art.encoder.transform(df[art.categorical_features])
    groups = df[art.schema["split_group_columns"]].astype(str).agg("|".join, axis=1).to_numpy()

    for target in art.risk_targets:
        y = df[target].map(art.level_map)
        train_idx, test_idx = next(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
                                   .split(X, y, groups=groups))
        assert not set(groups[train_idx]) & set(groups[test_idx]), f"{target}: input leakage"

        f1 = f1_score(y.iloc[test_idx], art.models[target].predict(X.iloc[test_idx]), average="macro")
        reported = card["test_metrics"][target]["macro_f1"]
        assert abs(f1 - reported) < 0.005, f"{target}: card says {reported:.3f}, split gives {f1:.3f}"
