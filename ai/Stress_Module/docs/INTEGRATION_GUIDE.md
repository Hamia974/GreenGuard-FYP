# Integration Guide — Module 2: Soil & Nutrient Analysis

**For: Backend (Django) team** · **Version:** 1.2.0

**Contract:** `REST_API_SPEC.md` (v2.1), Section 9 → AI Module 2. The same contract, in more
detail, is in `docs/Module2_Orchestrator_Spec.md`.

## Starting the service

| | |
|---|---|
| Local | `cd api` then `python main.py` (after `pip install -r requirements.txt`, Python 3.13) |
| Docker | `docker build -t greenguard-module2 .` then `docker run -p 8002:8002 greenguard-module2` |
| Base URL | `http://localhost:8002` (dev) — replace host/port for staging/production once deployed |
| Runtime | CPU only, no GPU; ~200 MB memory; no internet access or API keys needed |
| Startup | ~3 s — model files are loaded and checksum-verified before the service accepts requests |

### Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8002` | Port the service binds to (also honoured by the Docker image) |
| `MODELS_DIR` | the package's `models/` folder | Absolute path to the model files, if they are mounted elsewhere |
| `WEB_CONCURRENCY` | `1` | Number of worker processes (read by uvicorn); each holds its own copy of the models, ~200 MB |

### Running with Docker

```bash
docker build -t greenguard-module2 .
docker run -d --name module2 -p 8002:8002 greenguard-module2

# deployment check, inside the image:
docker run --rm greenguard-module2 python -m pytest -p no:cacheprovider /app/tests/test_deployment.py
```

Or `docker compose up --build -d` with the included `docker-compose.yml`, whose service block
can be copied into the project-wide compose file.

- **Base image:** `python:3.13-slim`, running as an unprivileged user.
- **No setup needed:** no volumes, secrets or outbound network access are required.
- **Port:** `-e PORT=9000 -p 9000:9000` changes it.
- **Health check:** a built-in `HEALTHCHECK` polls `/health` every 30 s, and `docker ps` reports
  the container as `healthy` or `unhealthy`.
- **Platforms:** every dependency installs from a ready-made wheel on both x86_64 and arm64
  Linux hosts (e.g. Apple Silicon or ARM servers).

## Where Backend gets each value

For every soil check, Backend receives the farmer's form from the frontend
(`POST /api/v1/predictions/analyze/`), gets the weather from the Weather Risk Module, and
combines the two into one Module 2 request.

**Call order**

1. Receive the analyze request from the frontend. Its form fields are listed in
   `REST_API_SPEC.md` → Analyze Plant.
2. Call the Weather Risk Module with the farm's `latitude` and `longitude`.
3. Build the Module 2 request from the table below and `POST` it to Module 2's `/predict`.
4. Store the Module 2 response unchanged as the prediction's soil output, pass it to the ANN
   Fusion Module with the other module outputs, and return it in the prediction report.

**Module 2 request fields**

| Module 2 field | Backend takes it from | What to do with it |
|---|---|---|
| `crop` | Frontend form: `crop` | Pass as-is |
| `growth_stage` | Frontend form: `growth_stage` | Pass as-is |
| `soil_type` | Frontend form: `soil_type` | Pass as-is |
| `last_fertilizer_type` | Frontend form: `last_fertilizer_type` | Pass as-is |
| `days_since_fertilizer` | Frontend form: `days_since_fertilizer` | Pass as-is (`not_applicable` when `No_Fertilizer`) |
| `irrigation_source` | Frontend form: `irrigation_source` | Pass as-is |
| `irrigation_adequacy` | Frontend form: `irrigation_adequacy` | Pass as-is |
| `ph_value` | Frontend form: `ph_value` (soil meter) | Convert to a number |
| `soil_moisture_pct` | Frontend form: `soil_moisture_pct` (soil meter) | Convert to a number |
| `light_intensity_lux` | Frontend form: `light_intensity_lux` (soil meter) | Convert to a number |
| `temperature_c` | Weather Risk Module response: `weather.temperature` | Copy the number |
| `humidity_pct` | Weather Risk Module response: `weather.humidity` | Copy the number |
| `rainfall_mm_last_7_days` | Weather Risk Module response: `weather.rainfall_last_7_days_mm` | Copy the number |
| `symptoms` | Frontend form: `symptoms` (a JSON array of the selected keys) | Convert to an object with all 11 keys (below) |

Form-data values arrive as text, so convert the three meter readings to numbers. Never fill a
missing value with a default. If the Weather module call fails, return the "Weather service is
temporarily unavailable" error from `REST_API_SPEC.md` (Section 13) without calling Module 2.

Converting `symptoms`:

```python
import json

SYMPTOM_KEYS = [  # same list as docs/module2_field_options.json -> symptom_fields.keys
    "yellowing_older_leaves", "purple_reddish_tint", "brown_scorched_leaf_edges",
    "stunted_growth", "poor_flowering_or_fruiting", "weak_stems",
    "interveinal_chlorosis_older_leaves", "interveinal_chlorosis_young_leaves",
    "leaf_curling_brittle", "short_internodes_small_leaves", "none_visible",
]
selected = json.loads(form["symptoms"])  # e.g. ["yellowing_older_leaves", "stunted_growth"]
symptoms = {key: key in selected for key in SYMPTOM_KEYS}
```

**Not sent to Module 2:** `image` (goes to Module 1), and `latitude` / `longitude` (go to the
Weather module).

**Added by Backend when storing** (Module 2 does not return these): the prediction ID, the user,
the farm location and an ISO 8601 timestamp.

## How to call this service

- **Method:** POST
- **URL:** `http://localhost:8002/predict`
- **Content-Type:** application/json

### Request body
```json
{
  "crop": "wheat",
  "growth_stage": "vegetative",
  "soil_type": "sandy",
  "last_fertilizer_type": "No_Fertilizer",
  "days_since_fertilizer": "not_applicable",
  "irrigation_source": "tube_well",
  "irrigation_adequacy": "excessive",
  "temperature_c": 30.0,
  "humidity_pct": 55,
  "rainfall_mm_last_7_days": 45.0,
  "ph_value": 4.5,
  "soil_moisture_pct": 62,
  "light_intensity_lux": 28000,
  "symptoms": {
    "yellowing_older_leaves": true,
    "purple_reddish_tint": false,
    "brown_scorched_leaf_edges": false,
    "stunted_growth": true,
    "poor_flowering_or_fruiting": false,
    "weak_stems": false,
    "interveinal_chlorosis_older_leaves": false,
    "interveinal_chlorosis_young_leaves": false,
    "leaf_curling_brittle": false,
    "short_internodes_small_leaves": false,
    "none_visible": false
  }
}
```

Every field is required. Allowed values for each field are in `docs/module2_field_options.json`
and `docs/MODEL_DOCUMENTATION.md` → "Model inputs". Validation rules beyond types and ranges:

- `days_since_fertilizer` must be `not_applicable` exactly when `last_fertilizer_type` is
  `No_Fertilizer`.
- At least one symptom must be `true`; `none_visible` cannot be combined with any other symptom.
- Where each field comes from (the frontend form, the Weather module, or a conversion) is
  listed in **Where Backend gets each value** above.

### Success response — HTTP 200
```json
{
  "crop_supported": true,
  "module2a": {
    "nitrogen_risk": {"level": "high", "confidence": 0.95},
    "phosphorus_risk": {"level": "low", "confidence": 0.39},
    "potassium_risk": {"level": "medium", "confidence": 0.55},
    "magnesium_risk": {"level": "high", "confidence": 0.41},
    "zinc_risk": {"level": "low", "confidence": 0.7},
    "boron_risk": {"level": "high", "confidence": 0.42},
    "overall_nutrient_health": "moderate",
    "input_typicality": {"anomaly_score": 0.065, "flag": "typical"},
    "model_version": "module2a-v5"
  },
  "module2b": {
    "ph": {
      "current": 4.5,
      "ideal_range": [6.0, 7.5],
      "gap": 1.5,
      "status": "critical",
      "nutrient_lockout_note": "Soil is strongly acidic. This severely limits potassium, nitrogen, phosphorus, calcium, and magnesium — and can raise aluminum/manganese to toxic levels. Fertilizer alone will not fix this; consider liming. A laboratory soil test is recommended to confirm and guide correction."
    },
    "soil_moisture": {"current": 62.0, "ideal_range": [50.0, 70.0], "gap": 0.0, "status": "ok"},
    "light": {"current": 28000.0, "ideal_range": [25000.0, null], "gap": 0.0, "status": "ok"},
    "crop_supported": true
  },
  "overall_soil_health_score": 47.5,
  "overall_soil_health_label": "poor",
  "recommendation_notes": {
    "headline": "Nitrogen needs attention first.",
    "needs_attention": [
      {"nutrient": "Nitrogen", "level": "high", "confidence_pct": 95, "confidence_text": "95% confident — strong match", "why": "yellowing on your older leaves, sandy soil (nutrients wash out faster), no fertilizer applied"},
      {"nutrient": "Boron", "level": "high", "confidence_pct": 42, "confidence_text": "42% confident — based on limited signs", "why": "sandy soil (nutrients wash out faster), no fertilizer applied"},
      {"nutrient": "Magnesium", "level": "high", "confidence_pct": 41, "confidence_text": "41% confident — based on limited signs", "why": "sandy soil (nutrients wash out faster), no fertilizer applied"},
      {"nutrient": "Potassium", "level": "medium", "confidence_pct": 55, "confidence_text": "55% confident — possible", "why": "sandy soil (nutrients wash out faster), no fertilizer applied"}
    ],
    "looking_fine": [
      {"nutrient": "Phosphorus", "level": "low", "confidence_pct": 39, "confidence_text": "39% confident — based on limited signs"},
      {"nutrient": "Zinc", "level": "low", "confidence_pct": 70, "confidence_text": "70% confident — likely"}
    ],
    "caveat": "This advice is based on your answers and soil-meter readings. A soil lab test can add exact nutrient levels if you need them.",
    "soil_condition_note": "Soil is strongly acidic. This severely limits potassium, nitrogen, phosphorus, calcium, and magnesium — and can raise aluminum/manganese to toxic levels. Fertilizer alone will not fix this; consider liming. A laboratory soil test is recommended to confirm and guide correction."
  },
  "model_version": "module2-orchestrator-v1",
  "module2a_model_version": "module2a-v5"
}
```
This is a real, live-captured response to the request above (`samples/sample_response.json`),
not a fabricated example. `tests/test_deployment.py` checks the running service against it.

Field notes:

- `confidence` is the model's probability for the predicted level (0–1). Show it to the farmer
  as a percentage.
- `input_typicality.flag` is `"unusual"` when the answers form an uncommon combination compared
  with the training data. The prediction is still returned; show it with extra caution.
- `ideal_range` is `[low, high]`; `high` is `null` when there is no upper limit. `gap` is `0`
  when the reading is inside the range.
- `nutrient_lockout_note` is display text for the farmer.
- Store `model_version` and `module2a_model_version` with each result so any stored prediction
  can be traced to the model that made it.
- `recommendation_notes` is ready-to-display text for the farmer, built from the results above:
  - `headline`: a one-line summary.
  - `needs_attention`: nutrients at medium or high risk, already sorted worst first. Each has
    `confidence_pct`, `confidence_text`, and `why` (the farmer's own answers that point to it).
  - `looking_fine`: nutrients at low risk (no `why`).
  - `caveat`: always present. Show it with the results.
  - `soil_condition_note`: present only when the pH is outside the crop's range.
  - `reliability_note`: present only when `input_typicality.flag` is `"unusual"`.

### Unsupported crop — HTTP 200
A crop outside the 15 supported crops is not an error:
```json
{
  "crop_supported": false,
  "message": "Nutrient and soil-condition analysis isn't available yet for this crop.",
  "module2a": null,
  "module2b": null,
  "overall_soil_health_score": null,
  "overall_soil_health_label": null,
  "recommendation_notes": null
}
```

A second, currently unreachable variant exists for a crop that Module 2A serves but Module 2B
has no ranges for: `crop_supported: true` with the full `module2a` result, `module2b` as
`{"crop_supported": false, "message": "..."}`, the score and label `null`, and a top-level
`message`. All 15 crops are served by both sub-modules in v1.1.0, but handle it defensively.

### Error responses
| Status | When | Body |
|---|---|---|
| 422 | A field missing, of the wrong type, out of range, or breaking one of the validation rules above | FastAPI's default validation error: `{"detail": [{"type": ..., "loc": [...], "msg": ...}, ...]}` |
| 503 | Model files missing, or failed checksum verification at load | `{"message": "Prediction Failed: model artifacts unavailable."}` |
| 500 | Any other internal failure | `{"message": "Prediction Failed"}` |

Every non-422 error uses the `message` key, the same shape as the Weather module. Branch on the
status code, not on the exact message text.

**Changed in v1.1.0:** the 503 body was previously `{"detail": "<server file path>"}`. If
Backend error handling was already written against `detail` for this case, update it to
`message`.

## Health check

`GET /health` → `{"status": "ok", "service": "soil-nutrient-module"}` — use this for uptime
monitoring. It is a liveness check: it answers even when the model files are unavailable, so a
model problem never looks like a dead service. To confirm the models are serving, send
`samples/sample_request.json` to `/predict` and expect HTTP 200.

## Verifying a deployment

After installing on a new machine or building the container, run from the module folder:

```bash
pytest tests/test_deployment.py -v
```

It confirms the model files match their checksums, the installed libraries match those used
for training, and the service reproduces the recorded release outputs for every scenario in
`samples/test_scenarios.json`.

## What Backend should NOT do

- Do not call Module 2A or Module 2B directly — they have no routes; everything goes through
  `/predict`.
- Do not recalculate or modify risk levels, confidences or the overall score — store and
  forward them as-is.
- Do not rename any field before storing or returning to the frontend.
- Do not re-sort `recommendation_notes.needs_attention` or rebuild the confidence wording —
  display both exactly as returned.
- Do not treat `overall_soil_health_score` / `overall_soil_health_label` as always present —
  they are `null` whenever the crop is unsupported.
- Do not parse `nutrient_lockout_note` or `message` strings for logic — wording may change
  between versions. Branch on `crop_supported`, `level` and `status` instead.
- Do not send `None` or `null` for "no fertilizer" — send `"No_Fertilizer"` with
  `"days_since_fertilizer": "not_applicable"`.
- Do not retry a 422 — the request itself needs fixing.

## Farmer-facing notes

`recommendation_notes` is generated by `api/recommendations.py` from the Module 2A and 2B
results. It restates them in plain language and never changes them. Display guidance for the
frontend (order, confidence wording, when to show the soil and reliability notes) is in
`docs/Module2_Frontend_Form_Spec.md`.

## Open items to confirm with the Project Manager / AI team

1. `docker build` and the in-image deployment check have not yet been run, because Docker is
   not installed on the development machine. Run them once it is.
2. Module 2B's ideal pH/moisture ranges for the 7 horticultural crops remain provisional pending
   local field validation (the original 8 crops are now agronomy-reviewed — see item below).

**Resolved on 2026-09-11, with Project Manager approval:**
- the Module 2 response includes `module2a.input_typicality`, `module2a_model_version` and
  `recommendation_notes`;
- `REST_API_SPEC.md` was updated to v2.1 so that its Module 2 sections match this delivery.

**Resolved 2026-09-13 to 2026-09-16 (v1.2.0):** two agronomy reviews (GG-M2-AR-01, GG-M2-AR-02)
applied — corrected crop pH/moisture ranges, crop-dependent score weighting for cucurbits and
potato, a lab-soil-test recommendation on critical pH messages, and a plain-language rewrite of
farmer-facing reliability wording. No request/response field changed. Full detail in
`docs/MODEL_DOCUMENTATION.md` → Versioning and → Module 2B rules.
