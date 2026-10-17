"""Integrity manifest for the Module 2A inference artifacts.

The training notebook writes models/manifest.json right after saving the artifacts, and the
service verifies it at startup. A missing, truncated or swapped model file then stops the
service with a clear error instead of silently serving predictions from the wrong model.

The manifest also records the library versions the artifacts were trained with. The joblib
artifacts are pickles, which are only guaranteed to load correctly under the same
scikit-learn / XGBoost versions, so a version difference is reported as a warning.
"""

import hashlib
import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

MANIFEST_NAME = "manifest.json"

# Everything inference needs. The model card and model comparison are documentation and
# are deliberately excluded, so editing them can never stop the service from starting.
REQUIRED_ARTIFACTS = (
    "module2a_nitrogen_risk.joblib",
    "module2a_phosphorus_risk.joblib",
    "module2a_potassium_risk.joblib",
    "module2a_magnesium_risk.joblib",
    "module2a_zinc_risk.joblib",
    "module2a_boron_risk.joblib",
    "module2a_ordinal_encoder.joblib",
    "module2a_anomaly_detector.joblib",
    "module2a_schema.json",
)
TRACKED_LIBRARIES = ("scikit-learn", "xgboost", "numpy", "pandas", "joblib")


class ArtifactIntegrityError(RuntimeError):
    """An artifact exists but does not match the checksum recorded at training time."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _installed(library: str) -> str | None:
    try:
        return version(library)
    except PackageNotFoundError:
        return None


def write_manifest(models_dir, model_version: str) -> dict:
    """Record checksums and training-library versions for the saved artifacts."""
    models_dir = Path(models_dir)
    manifest = {
        "model_version": model_version,
        "artifacts": {name: _sha256(models_dir / name) for name in REQUIRED_ARTIFACTS},
        "trained_with": {library: _installed(library) for library in TRACKED_LIBRARIES},
    }
    (models_dir / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def verify_manifest(models_dir) -> tuple[dict, dict]:
    """Check every artifact against the manifest.

    Returns (manifest, version_mismatches). Raises FileNotFoundError if the manifest or an
    artifact is missing, and ArtifactIntegrityError if a checksum does not match.
    """
    models_dir = Path(models_dir)
    manifest_path = models_dir / MANIFEST_NAME
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Module 2A manifest not found at {manifest_path}. Re-run "
            "training/module2a_nutrient_risk.ipynb to regenerate the artifacts and manifest."
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    for name, expected in manifest["artifacts"].items():
        path = models_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Module 2A artifact missing: {path}")
        if _sha256(path) != expected:
            raise ArtifactIntegrityError(
                f"{name} does not match the checksum recorded in {MANIFEST_NAME}: the file is "
                "corrupted or was replaced without re-running the training notebook."
            )

    mismatches = {
        library: {"trained_with": trained, "installed": _installed(library)}
        for library, trained in manifest.get("trained_with", {}).items()
        if trained != _installed(library)
    }
    return manifest, mismatches
