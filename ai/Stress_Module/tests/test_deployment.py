"""Deployment verification -- run on the target machine after installing requirements.txt.

Confirms the model artifacts are intact, were loaded with the library versions they were
trained with, and still produce the predictions recorded at release. A corrupted copy, a
wrong models folder or a different scikit-learn/XGBoost build shows up here before a
farmer ever sees a wrong answer.

    pytest tests/test_deployment.py -v

After retraining, record the new expected outputs (and refresh samples/sample_response.json):

    python tests/test_deployment.py --record
"""

import json
import shutil
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "api"))

import main  # noqa: E402
import module2a_service  # noqa: E402
from manifest import MANIFEST_NAME, ArtifactIntegrityError, verify_manifest  # noqa: E402
from schemas import Module2Request  # noqa: E402

GOLDEN_PATH = ROOT / "tests" / "golden_outputs.json"
SCENARIOS_PATH = ROOT / "samples" / "test_scenarios.json"
SAMPLE_REQUEST_PATH = ROOT / "samples" / "sample_request.json"
SAMPLE_RESPONSE_PATH = ROOT / "samples" / "sample_response.json"

# Responses round confidence to 2 dp and anomaly_score to 3 dp. A different CPU or
# platform can move a value across a rounding boundary, so allow one unit of the last
# digit. Everything else (levels, statuses, scores, labels) must match exactly.
TOLERANCES = {"confidence": 0.011, "anomaly_score": 0.0011}

client = TestClient(main.app)


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _valid_scenarios() -> dict:
    """Scenarios from samples/test_scenarios.json that are meant to succeed."""
    scenarios = {}
    for name, body in _load(SCENARIOS_PATH).items():
        try:
            Module2Request.model_validate(body)
        except ValidationError:
            continue  # the deliberate 422 scenario
        scenarios[name] = body
    return scenarios


def _predict(body: dict) -> dict:
    response = client.post("/predict", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def _assert_matches(actual, expected, path="response"):
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path}: expected an object"
        assert set(actual) == set(expected), f"{path}: fields differ {set(actual) ^ set(expected)}"
        for key in expected:
            _assert_matches(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list) and len(actual) == len(expected), f"{path}: list differs"
        for i, (a, e) in enumerate(zip(actual, expected)):
            _assert_matches(a, e, f"{path}[{i}]")
    elif isinstance(expected, bool) or expected is None or isinstance(expected, str):
        assert actual == expected, f"{path}: {actual!r} != {expected!r}"
    else:
        tolerance = TOLERANCES.get(path.rsplit(".", 1)[-1], 0)
        assert abs(actual - expected) <= tolerance, f"{path}: {actual} != {expected}"


# --- Artifact integrity ------------------------------------------------------------

def test_artifacts_match_manifest_and_library_versions():
    manifest, mismatches = verify_manifest(module2a_service.models_dir())
    assert manifest["model_version"] == module2a_service.get_model_version()
    assert not mismatches, (
        f"installed libraries differ from training -- install requirements.txt exactly: {mismatches}"
    )


def test_corrupted_artifact_is_detected(tmp_path):
    shutil.copytree(module2a_service.models_dir(), tmp_path, dirs_exist_ok=True)
    with open(tmp_path / "module2a_schema.json", "a", encoding="utf-8") as handle:
        handle.write(" ")
    with pytest.raises(ArtifactIntegrityError, match="module2a_schema.json"):
        verify_manifest(tmp_path)


def test_missing_manifest_is_detected(tmp_path):
    shutil.copytree(module2a_service.models_dir(), tmp_path, dirs_exist_ok=True)
    (tmp_path / MANIFEST_NAME).unlink()
    with pytest.raises(FileNotFoundError, match="manifest"):
        verify_manifest(tmp_path)


def test_models_dir_override(tmp_path, monkeypatch):
    """MODELS_DIR points the service at artifacts mounted outside the package."""
    shutil.copytree(module2a_service.models_dir(), tmp_path, dirs_exist_ok=True)
    schema = _load(tmp_path / "module2a_schema.json")
    cached = module2a_service._artifacts
    monkeypatch.setenv("MODELS_DIR", str(tmp_path))
    module2a_service._artifacts = None
    try:
        assert module2a_service.models_dir() == tmp_path
        assert module2a_service.get_model_version() == schema["model_version"]
    finally:
        module2a_service._artifacts = cached


# --- Release outputs ---------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(_load(GOLDEN_PATH)) if GOLDEN_PATH.exists() else [])
def test_prediction_matches_release_output(name):
    expected = _load(GOLDEN_PATH)[name]
    _assert_matches(_predict(_valid_scenarios()[name]), expected)


def test_every_success_scenario_has_a_recorded_output():
    assert GOLDEN_PATH.exists(), "run: python tests/test_deployment.py --record"
    assert set(_load(GOLDEN_PATH)) == set(_valid_scenarios())


def test_shipped_sample_response_is_current():
    """samples/sample_response.json is what Backend integrates against; it must be real."""
    _assert_matches(_predict(_load(SAMPLE_REQUEST_PATH)), _load(SAMPLE_RESPONSE_PATH))


def _record() -> None:
    golden = {name: _predict(body) for name, body in _valid_scenarios().items()}
    GOLDEN_PATH.write_text(json.dumps(golden, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sample = _predict(_load(SAMPLE_REQUEST_PATH))
    SAMPLE_RESPONSE_PATH.write_text(json.dumps(sample, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Recorded {len(golden)} scenario outputs to {GOLDEN_PATH.name} and refreshed "
          f"{SAMPLE_RESPONSE_PATH.name} (model {module2a_service.get_model_version()})")


if __name__ == "__main__":
    if "--record" not in sys.argv:
        sys.exit(__doc__)
    _record()
