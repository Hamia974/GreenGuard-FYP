"""Module 2 API tests.

Run from Stress_Module with: pytest tests/test_api.py -v
"""

import json
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import main
import module2a_service
import module2b_service
from orchestrator_service import calculate_soil_health_score

client = TestClient(main.app)
SAMPLES = os.path.join(os.path.dirname(__file__), "..", "samples")


def _sample_request() -> dict:
    with open(os.path.join(SAMPLES, "sample_request.json"), encoding="utf-8") as handle:
        return json.load(handle)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "soil-nutrient-module"}


# --- Public /predict contract ------------------------------------------------------

def test_predict_rejects_empty_body():
    assert client.post("/predict", json={}).status_code == 422


def test_predict_returns_full_contract():
    response = client.post("/predict", json=_sample_request())
    assert response.status_code == 200
    body = response.json()

    assert body["crop_supported"] is True
    assert body["module2a"] is not None
    assert body["module2b"] is not None
    assert 0 <= body["overall_soil_health_score"] <= 100
    assert body["overall_soil_health_label"] in {"good", "moderate", "poor"}
    assert body["model_version"] == "module2-orchestrator-v1"

    for target in ["nitrogen_risk", "phosphorus_risk", "potassium_risk",
                   "magnesium_risk", "zinc_risk", "boron_risk"]:
        entry = body["module2a"][target]
        assert entry["level"] in {"low", "medium", "high"}
        assert 0.0 <= entry["confidence"] <= 1.0

    assert body["module2a"]["overall_nutrient_health"] in {"good", "moderate", "poor"}
    assert body["module2a"]["input_typicality"]["flag"] in {"typical", "unusual"}


def test_predict_requires_meter_readings():
    """ph/moisture/light are required as of 2026-09-10 -- the deployment ships a meter."""
    for field in ("ph_value", "soil_moisture_pct", "light_intensity_lux"):
        payload = _sample_request()
        del payload[field]
        assert client.post("/predict", json=payload).status_code == 422, field


def test_predict_rejects_contradictory_symptoms():
    payload = _sample_request()
    payload["symptoms"]["none_visible"] = True  # already has other symptoms set
    assert client.post("/predict", json=payload).status_code == 422


def test_sample_response_matches_response_schema():
    from schemas import SoilAnalysisResponse

    with open(os.path.join(SAMPLES, "sample_response.json"), encoding="utf-8") as handle:
        SoilAnalysisResponse.model_validate(json.load(handle))


def test_scored_response_has_no_extra_fields():
    """The typed response model must not add fields (e.g. message: null) to the JSON."""
    body = client.post("/predict", json=_sample_request()).json()
    assert set(body) == {
        "crop_supported", "module2a", "module2b", "overall_soil_health_score",
        "overall_soil_health_label", "recommendation_notes", "model_version",
        "module2a_model_version",
    }


def test_recommendation_notes_agree_with_module2a():
    """The notes restate 2A's results in plain words; they must never contradict them."""
    body = client.post("/predict", json=_sample_request()).json()
    notes = body["recommendation_notes"]
    assert notes["headline"]
    assert "soil-meter readings" in notes["caveat"]

    items = notes["needs_attention"] + notes["looking_fine"]
    assert sorted(item["nutrient"] for item in items) == sorted(
        ["Nitrogen", "Phosphorus", "Potassium", "Magnesium", "Zinc", "Boron"])
    for item in items:
        risk = body["module2a"][f"{item['nutrient'].lower()}_risk"]
        assert item["level"] == risk["level"]
        assert item["confidence_pct"] == round(risk["confidence"] * 100)
    assert all(item["level"] != "low" and item["why"] for item in notes["needs_attention"])
    assert all(item["level"] == "low" and "why" not in item for item in notes["looking_fine"])


def test_soil_condition_note_follows_module2b_ph_status():
    critical = client.post("/predict", json=_sample_request()).json()  # pH 4.5: critical for wheat
    assert (critical["recommendation_notes"]["soil_condition_note"]
            == critical["module2b"]["ph"]["nutrient_lockout_note"])

    in_range = client.post("/predict", json=dict(_sample_request(), ph_value=6.8)).json()
    assert in_range["module2b"]["ph"]["status"] == "ok"
    assert "soil_condition_note" not in in_range["recommendation_notes"]


# --- Error responses (same {"message": ...} shape as the Weather module) -----------

def test_missing_models_return_503_message(monkeypatch):
    def unavailable(_payload):
        raise FileNotFoundError("models/module2a_schema.json")

    monkeypatch.setattr(main, "analyze_soil", unavailable)
    response = client.post("/predict", json=_sample_request())
    assert response.status_code == 503
    assert response.json() == {"message": "Prediction Failed: model artifacts unavailable."}


def test_unexpected_error_returns_500_message(monkeypatch):
    def broken(_payload):
        raise RuntimeError("boom")

    monkeypatch.setattr(main, "analyze_soil", broken)
    response = TestClient(main.app, raise_server_exceptions=False).post(
        "/predict", json=_sample_request())
    assert response.status_code == 500
    assert response.json() == {"message": "Prediction Failed"}


def test_validation_error_keeps_standard_detail_shape():
    body = client.post("/predict", json={}).json()
    assert isinstance(body["detail"], list) and body["detail"]


def test_internal_submodules_are_not_publicly_routable():
    """Spec checklist: 2A and 2B must not be reachable from outside Module 2."""
    routes = {route.path for route in main.app.routes}
    assert "/predict" in routes
    assert not any("module2a" in path or "module2b" in path for path in routes)


# --- Scoring (pure function, testable without the models) --------------------------

def test_score_matches_spec_worked_example():
    """Module2_Orchestrator_Spec.md Section 3 worked example must yield 52.5/moderate."""
    module2a = {
        "nitrogen_risk": {"level": "high"},
        "phosphorus_risk": {"level": "medium"},
        "potassium_risk": {"level": "low"},
        "magnesium_risk": {"level": "medium"},
        "zinc_risk": {"level": "low"},
        "boron_risk": {"level": "medium"},
    }
    module2b = {
        "ph": {"status": "critical"},
        "soil_moisture": {"status": "ok"},
        "light": {"status": "ok"},
    }
    assert calculate_soil_health_score(module2a, module2b) == {
        "overall_soil_health_score": 52.5,
        "overall_soil_health_label": "moderate",
    }


def test_score_bounds():
    all_good_2a = {t: {"level": "low"} for t in
                   ["nitrogen_risk", "phosphorus_risk", "potassium_risk",
                    "magnesium_risk", "zinc_risk", "boron_risk"]}
    all_good_2b = {f: {"status": "ok"} for f in ["ph", "soil_moisture", "light"]}
    assert calculate_soil_health_score(all_good_2a, all_good_2b) == {
        "overall_soil_health_score": 100.0, "overall_soil_health_label": "good"}

    all_bad_2a = {t: {"level": "high"} for t in all_good_2a}
    all_bad_2b = {f: {"status": "critical"} for f in all_good_2b}
    assert calculate_soil_health_score(all_bad_2a, all_bad_2b) == {
        "overall_soil_health_score": 0.0, "overall_soil_health_label": "poor"}


def test_cucurbit_crops_weight_zinc_and_boron_more_than_default():
    """Per agronomy review GG-M2-AR-01: cucurbits get N/P/K 13 each, Zn/B 8 each."""
    module2a = {
        "nitrogen_risk": {"level": "low"}, "phosphorus_risk": {"level": "low"},
        "potassium_risk": {"level": "low"},
        "magnesium_risk": {"level": "low"}, "zinc_risk": {"level": "high"},
        "boron_risk": {"level": "low"},
    }
    module2b = {f: {"status": "ok"} for f in ["ph", "soil_moisture", "light"]}

    default = calculate_soil_health_score(module2a, module2b)
    cucurbit = calculate_soil_health_score(module2a, module2b, crop="bottle_gourd")

    # Zinc weighs more for cucurbits (8 vs 5), so the same high-zinc-risk penalty
    # costs a cucurbit crop more points than the default weighting.
    assert cucurbit["overall_soil_health_score"] < default["overall_soil_health_score"]
    # A non-cucurbit crop name must fall back to the default weights exactly.
    assert calculate_soil_health_score(module2a, module2b, crop="wheat") == default
    # eggplant is Solanaceae, not a cucurbit -- must also use the default weights.
    assert calculate_soil_health_score(module2a, module2b, crop="eggplant") == default


# --- Module 2A internal service ----------------------------------------------------

def test_module2a_ignores_meter_fields():
    """2A must never receive ph/moisture/light -- they are 2B's inputs."""
    payload = _sample_request()
    baseline = module2a_service.predict_nutrient_risks(payload)

    shifted = dict(payload, ph_value=8.9, soil_moisture_pct=5, light_intensity_lux=1)
    assert module2a_service.predict_nutrient_risks(shifted) == baseline


def test_typicality_flag_matches_isolation_forest_predict():
    """The flag is derived from the score; it must agree with the detector's own predict()."""
    art = module2a_service._get_artifacts()
    payload = _sample_request()
    for crop in sorted(module2a_service.get_trained_crops()):
        for soil in ("sandy", "clay", "saline_affected"):
            request = dict(payload, crop=crop, soil_type=soil)
            frame = module2a_service._build_feature_frame(request, art)
            expected = "typical" if art.anomaly_detector.predict(frame)[0] == 1 else "unusual"
            flag = module2a_service.predict_nutrient_risks(request)["input_typicality"]["flag"]
            assert flag == expected, (crop, soil)


def test_module2a_covers_all_supported_crops():
    payload = _sample_request()
    for crop in sorted(module2a_service.get_trained_crops()):
        result = module2a_service.predict_nutrient_risks(dict(payload, crop=crop))
        assert result["nitrogen_risk"]["level"] in {"low", "medium", "high"}


# --- Module 2B internal service (called directly; no public route by design) --------

def test_module2b_wheat_comparison():
    body = module2b_service.compare_growing_conditions({
        "crop": "wheat", "ph_value": 4.5,
        "soil_moisture_pct": 62, "light_intensity_lux": 28000,
    })
    assert body["crop_supported"] is True
    assert body["ph"]["gap"] == 1.5
    assert body["ph"]["status"] == "critical"
    assert body["soil_moisture"]["status"] == "ok"
    assert body["light"]["status"] == "ok"


def test_module2b_boundary_values():
    expected = {5.0: "moderate", 5.5: "good", 7.0: "good", 7.5: "borderline", 8.0: "moderate"}
    for ph_value, expected_status in expected.items():
        lockout_status, _ = module2b_service._ph_lockout(ph_value)
        assert lockout_status == expected_status


def test_module2b_rice_moisture_band():
    body = module2b_service.compare_growing_conditions({
        "crop": "rice", "ph_value": 6.2,
        "soil_moisture_pct": 60, "light_intensity_lux": 28000,
    })
    assert body["soil_moisture"]["status"] == "moderate"


def test_module2b_additional_crops_are_supported():
    for crop in ["eggplant", "cucumber", "bitter_gourd", "snake_gourd",
                 "ridge_gourd", "ash_gourd", "bottle_gourd"]:
        body = module2b_service.compare_growing_conditions({
            "crop": crop, "ph_value": 6.2,
            "soil_moisture_pct": 62, "light_intensity_lux": 28000,
        })
        assert body["crop_supported"] is True


def test_module2b_unknown_crop_is_unsupported():
    body = module2b_service.compare_growing_conditions({
        "crop": "unknown_crop", "ph_value": 6.2,
        "soil_moisture_pct": 60, "light_intensity_lux": 28000,
    })
    assert body["crop_supported"] is False


def test_module2b_status_and_lockout_note_are_independent():
    """Crop-band severity and absolute soil chemistry are separate judgements.

    pH 5.1 is critical *for tomato* (1.1 below its 6.2-6.8 band) but the pH note bands rate
    5.1 as only moderately acidic. Both are correct; neither should be coerced.
    """
    body = module2b_service.compare_growing_conditions({
        "crop": "tomato", "ph_value": 5.1,
        "soil_moisture_pct": 62, "light_intensity_lux": 28000,
    })
    assert body["ph"]["status"] == "critical"
    assert "starting to lock up" in body["ph"]["nutrient_lockout_note"]


# --- Regression tests for fixed defects --------------------------------------------

def test_module2b_guards_on_its_own_range_table():
    """A crop absent from CROP_RANGES must degrade gracefully, never raise KeyError.

    The guard previously consulted a list maintained in a different file, so any
    divergence between the two produced a 500 instead of this response.
    """
    original = module2b_service.CROP_RANGES.pop("wheat")
    try:
        body = module2b_service.compare_growing_conditions({
            "crop": "wheat", "ph_value": 6.2,
            "soil_moisture_pct": 60, "light_intensity_lux": 28000,
        })
        assert body["crop_supported"] is False
    finally:
        module2b_service.CROP_RANGES["wheat"] = original


def test_module2a_refuses_untrained_crop():
    """The encoder maps unseen categories to -1, which would otherwise yield a
    confident-looking prediction for a crop the model never saw."""
    import pytest

    payload = _sample_request()
    with pytest.raises(ValueError, match="not in Module 2A's trained crop set"):
        module2a_service.predict_nutrient_risks(dict(payload, crop="banana"))


def test_predict_unknown_crop_returns_unsupported_not_error():
    payload = dict(_sample_request(), crop="banana")
    response = client.post("/predict", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["crop_supported"] is False
    assert body["module2a"] is None
    assert body["overall_soil_health_score"] is None
    assert body["recommendation_notes"] is None


def test_score_withheld_when_module2b_cannot_serve_crop():
    """2B contributes 40 of the 100 points, so a partial score would not be
    comparable to a full one -- it is withheld rather than reported low."""
    original = module2b_service.CROP_RANGES.pop("wheat")
    try:
        from orchestrator_service import analyze_soil
        result = analyze_soil(_sample_request())
        assert result["crop_supported"] is True
        assert result["module2a"] is not None
        assert result["overall_soil_health_score"] is None
        assert result["overall_soil_health_label"] is None
    finally:
        module2b_service.CROP_RANGES["wheat"] = original


def test_crop_lists_stay_in_sync():
    """SUPPORTED_CROPS, Module 2A's trained crops and 2B's CROP_RANGES live in three
    separate files; drift between them is what produced the defects above."""
    from schemas import SUPPORTED_CROPS

    trained = module2a_service.get_trained_crops()
    assert SUPPORTED_CROPS == trained, SUPPORTED_CROPS ^ trained
    assert SUPPORTED_CROPS == set(module2b_service.CROP_RANGES), (
        SUPPORTED_CROPS ^ set(module2b_service.CROP_RANGES))
