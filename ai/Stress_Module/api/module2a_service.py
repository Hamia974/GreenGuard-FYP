"""Internal Module 2A nutrient-risk classifier boundary.

Loads the artifacts produced by ``training/module2a_nutrient_risk.ipynb`` and serves
the six per-nutrient risk predictions plus an input-typicality signal.

This module must not be exposed as a standalone FastAPI route -- Module 2's
orchestrator is the only caller (see docs/Module2_Orchestrator_Spec.md).

Design notes:
  - Artifacts load once and stay cached in memory. main.py pre-loads them at startup
    (warm_up), after they pass the models/manifest.json checksum check. Loading stays
    lazy as a fallback, so a missing models folder never stops the API from starting.
  - Feature order comes from ``module2a_schema.json`` rather than being hardcoded, so
    the service cannot drift out of sync with whatever the notebook last trained.
  - ph_value / soil_moisture_pct / light_intensity_lux are deliberately NOT passed to
    the model. They are Module 2B's inputs; Module 2A was never trained on them
    (see docs/MODEL_DOCUMENTATION.md, Model inputs).
"""

import json
import logging
import os
from pathlib import Path
from threading import Lock

import joblib
import pandas as pd

from manifest import verify_manifest

logger = logging.getLogger(__name__)

DEFAULT_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

_artifacts = None
_load_lock = Lock()


def models_dir() -> Path:
    """Folder the artifacts load from: MODELS_DIR if set, else the shipped models/.

    Read when the artifacts load rather than at import, so a value from .env (which
    main.py loads after importing this module) is honoured.
    """
    return Path(os.getenv("MODELS_DIR") or DEFAULT_MODELS_DIR)


class _Module2AArtifacts:
    """Everything needed for inference, loaded once and reused."""

    def __init__(self) -> None:
        models = models_dir()
        schema_path = models / "module2a_schema.json"
        if not schema_path.exists():
            raise FileNotFoundError(
                f"Module 2A schema not found at {schema_path}. Run "
                "training/module2a_nutrient_risk.ipynb to produce the model artifacts."
            )
        # Refuse to serve from artifacts that differ from what training produced.
        _, mismatches = verify_manifest(models)
        if mismatches:
            logger.warning(
                "Module 2A artifacts were trained with different library versions than "
                "are installed; install requirements.txt exactly: %s", mismatches,
            )
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))

        self.model_version = self.schema["model_version"]
        self.feature_columns = self.schema["feature_columns_in_order"]
        self.categorical_features = self.schema["categorical_features"]
        self.numeric_features = self.schema["numeric_features"]
        self.symptom_features = self.schema["symptom_features"]
        self.risk_targets = self.schema["risk_targets"]
        self.level_map = self.schema["level_map"]
        self.level_map_inv = {v: k for k, v in self.level_map.items()}
        self.overall_rule = {int(k): v for k, v in self.schema["overall_nutrient_health_rule"].items()}
        self.trained_crops = set(self.schema["trained_crops"])

        self.encoder = joblib.load(models / "module2a_ordinal_encoder.joblib")
        self.models = {
            target: joblib.load(models / f"module2a_{target}.joblib")
            for target in self.risk_targets
        }
        anomaly_path = models / self.schema["anomaly_detector"]["artifact"]
        self.anomaly_detector = joblib.load(anomaly_path)

        # Serving predicts one row at a time. The artifacts were trained with n_jobs=-1,
        # which at inference spawns joblib workers per call for no measurable speedup
        # (measured: identical median latency) while emitting a parallelism warning on
        # every prediction -- thousands across a test run, enough to bury a real one.
        for estimator in (*self.models.values(), self.anomaly_detector):
            if hasattr(estimator, "n_jobs"):
                estimator.n_jobs = 1


def _get_artifacts() -> _Module2AArtifacts:
    global _artifacts
    if _artifacts is None:
        with _load_lock:
            if _artifacts is None:
                _artifacts = _Module2AArtifacts()
    return _artifacts


def _build_feature_frame(payload: dict, art: _Module2AArtifacts) -> pd.DataFrame:
    """Flatten an API-shaped payload into the exact feature vector the models expect.

    Only the trained feature columns are read; ph_value / soil_moisture_pct /
    light_intensity_lux are ignored by design.
    """
    row = {col: payload[col] for col in art.categorical_features + art.numeric_features}

    symptoms = payload.get("symptoms", {})
    for col in art.symptom_features:
        key = col.removeprefix("symptom_")
        row[col] = int(bool(symptoms.get(key, False)))

    frame = pd.DataFrame([row])[art.feature_columns]
    frame[art.categorical_features] = art.encoder.transform(frame[art.categorical_features])
    return frame


def predict_nutrient_risks(payload: dict) -> dict:
    """Return six nutrient risk predictions for one farmer submission.

    Output shape matches ``Module2AResult`` in schemas.py: a
    ``{"level", "confidence"}`` pair per nutrient, the derived
    ``overall_nutrient_health``, the unsupervised ``input_typicality`` signal, and the
    model version the prediction came from.
    """
    art = _get_artifacts()

    # The ordinal encoder maps an unseen category to -1 rather than failing, so an
    # untrained crop would otherwise yield a confident-looking but meaningless
    # prediction. The orchestrator already screens crops, but this is the boundary that
    # actually knows what the model was trained on, so it refuses explicitly.
    crop = payload.get("crop")
    if crop not in art.trained_crops:
        raise ValueError(
            f"crop {crop!r} is not in Module 2A's trained crop set. "
            f"Trained crops: {sorted(art.trained_crops)}"
        )

    frame = _build_feature_frame(payload, art)

    result: dict = {}
    for target in art.risk_targets:
        proba = art.models[target].predict_proba(frame)[0]
        level_idx = int(proba.argmax())
        result[target] = {
            "level": art.level_map_inv[level_idx],
            "confidence": round(float(proba[level_idx]), 2),
        }

    npk_sum = sum(
        art.level_map[result[t]["level"]]
        for t in ("nitrogen_risk", "phosphorus_risk", "potassium_risk")
    )
    result["overall_nutrient_health"] = art.overall_rule[npk_sum]

    # Independent of the six risk predictions: how closely this submission resembles
    # the inputs the models were trained on. Used to caveat low-familiarity cases.
    # IsolationForest.predict() is defined as decision_function() < 0 -> outlier, so the
    # flag comes from the one score instead of scoring all 300 trees a second time.
    anomaly_score = float(art.anomaly_detector.decision_function(frame)[0])
    result["input_typicality"] = {
        "anomaly_score": round(anomaly_score, 3),
        "flag": "typical" if anomaly_score >= 0 else "unusual",
    }
    result["model_version"] = art.model_version
    return result


def warm_up() -> None:
    """Load the artifacts ahead of the first request.

    Called at application startup so the ~2.4s load cost is paid at boot instead of by
    whichever farmer happens to submit first after a restart.
    """
    _get_artifacts()


def get_model_version() -> str:
    """Model version string, for the orchestrator's response metadata."""
    return _get_artifacts().model_version


def get_trained_crops() -> set[str]:
    """Crops this model was actually trained on, read from the shipped schema."""
    return set(_get_artifacts().trained_crops)
