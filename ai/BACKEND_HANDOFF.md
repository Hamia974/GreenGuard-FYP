# GreenGuard AI Modules — Backend Handoff

**For:** Backend (Django) team · **From:** GreenGuard AI team · **Date:** 2026-09-15

This covers the two AI services ready for integration: **Module 2 — Soil & Nutrient Analysis**
and **Module 3 — Weather Risk**. Each comes two ways: a **live URL** you can call today, and a
**zip file** you can run yourselves. The API is the same either way.

---

## 1. At a glance

| | Module 3 — Weather Risk | Module 2 — Soil & Nutrient Analysis |
|---|---|---|
| **Live URL** | `https://greenguardai-1.onrender.com` | `https://greenguardai-gba4.onrender.com` |
| **Try it in a browser** | [/docs](https://greenguardai-1.onrender.com/docs) | [/docs](https://greenguardai-gba4.onrender.com/docs) |
| **Zip file** | `Weather_Module.zip` | `Stress_Module.zip` |
| **Local port** | 8001 | 8002 |

| **Endpoints** | `GET /health`, `POST /predict` | `GET /health`, `POST /predict` |
| **Input** | Farm latitude and longitude | Farmer's form answers, 3 soil-meter readings, and 3 weather values from Module 3 |
| **Output** | Current weather; fungal, heat and drought risk; optional next-day forecast | Risk for 6 nutrients, pH/moisture/light check, 0–100 soil-health score, farmer-ready notes |
| **Version** | 1.12.0 | 1.2.0 (model `module2a-v5`) |
| **Full docs (inside zip)** | `docs/INTEGRATION_GUIDE.md` | `docs/INTEGRATION_GUIDE.md` |
| **Memory** | ~170 MB | ~200 MB |

Source code for both is also on GitHub: `https://github.com/Minahil501/GreenGuardAI`.
The API contract is `REST_API_SPEC.md` (v2.1), Section 9. See **Section 11** for known differences.

---

## 2. Which one should you use?

- **Live URLs** — use them now, for development, integration testing and demos. Nothing to install.
- **Zip files** — use them to run the services next to Django (your own server, or the same
  `docker-compose`) for anything real users will touch, or when you need speed and no sleep.

Section 10 compares the two in detail. Both give identical responses — we checked the live
Module 2 against its recorded sample response and they match exactly.

---

## 3. Configure the URLs in Django

Keep the addresses in settings, never in code, so you can switch between the live URLs, local
copies and a production server without code changes:

```bash
# .env
WEATHER_MODULE_URL=https://greenguardai-1.onrender.com
SOIL_MODULE_URL=https://greenguardai-gba4.onrender.com
AI_MODULE_TIMEOUT_SECONDS=90

# running the zips locally instead:
# WEATHER_MODULE_URL=http://localhost:8001
# SOIL_MODULE_URL=http://localhost:8002
```

---

## 4. How the analyze request flows

```
Frontend ──► POST /api/v1/predictions/analyze/   (photo, latitude, longitude, form answers)
               │
               ├─ 1. Weather Module   POST {WEATHER_MODULE_URL}/predict   { latitude, longitude, farm_id }
               │        └─ if this fails: return "Weather service is temporarily unavailable." — do NOT call Module 2
               │
               ├─ 2. Soil Module      POST {SOIL_MODULE_URL}/predict      { form answers + 3 weather values }
               │
               ├─ 3. Disease Module, then Fusion Module (outside this handoff)
               │
               └─ 4. Store every module's response unchanged in PostgreSQL, return the report
```

Call Weather **before** Soil — Module 2 needs three of its numbers.

---

## 5. Module 3 — Weather Risk

**Call:** `POST {WEATHER_MODULE_URL}/predict` · `Content-Type: application/json`

**Request**
```json
{ "latitude": 31.5204, "longitude": 74.3587, "farm_id": "farm_001" }
```
- `latitude` −90 to 90 and `longitude` −180 to 180 are required. Take them from the farm record
  in your database.
- `farm_id` is optional. It is only echoed back (defaults to `"unknown"`).

**Response — HTTP 200** (fields you will use)
```json
{
  "farm_id": "farm_001",
  "timestamp": "2026-09-15T10:15:00Z",
  "weather": { "temperature": 26.4, "humidity": 91.0, "rainfall_last_7_days_mm": 2.8, "wind_speed": 1.4 },
  "units": { "temperature": "celsius", "humidity": "percent", "rainfall_last_7_days_mm": "mm", "wind_speed": "m/s" },
  "risk_assessment": {
    "fungal_disease_risk": "High",  "fungal_disease_reason": "Today's temperature (26.4°C) and humidity (91%) ...",
    "heat_stress_risk": "Low",      "heat_stress_reason": "...",
    "drought_risk": "High",         "drought_reason": "Only 2.8mm of rain fell in the last 7 days ..."
  },
  "forecast": { "temperature": 31.5, "humidity": 63.5, "rainfall_mm": 2.0 },
  "predicted_risk_assessment": { "...": "same shape as risk_assessment, for tomorrow" }
}
```
- Risk values are `Low`, `Moderate`, `High` (capitalised).
- `forecast` and `predicted_risk_assessment` **can be `null`**. Always check before reading them.
- `*_reason` strings are for display only. Branch on `*_risk`, never on the wording.

**Errors**

| Status | When | Body |
|---|---|---|
| 422 | Missing or out-of-range coordinates | `{"detail": [...]}` (FastAPI validation format) |
| 500 | Open-Meteo unreachable or another internal failure | `{"message": "Prediction Failed: weather service unavailable."}` or `{"message": "Prediction Failed"}` |

The service fetches live weather from Open-Meteo (free, no API key). It needs outbound internet.

---

## 6. Module 2 — Soil & Nutrient Analysis

**Call:** `POST {SOIL_MODULE_URL}/predict` · `Content-Type: application/json`

### Build the request

| Module 2 field | Take it from | Notes |
|---|---|---|
| `crop` | Form | One of 15 crops — list in `docs/module2_field_options.json` |
| `growth_stage`, `soil_type` | Form | Pass as-is |
| `last_fertilizer_type`, `days_since_fertilizer` | Form | `"No_Fertilizer"` (never `None`) goes with `"not_applicable"` |
| `irrigation_source`, `irrigation_adequacy` | Form | Pass as-is |
| `ph_value`, `soil_moisture_pct`, `light_intensity_lux` | Form (soil meter) | **Required.** Form data arrives as text — convert to numbers |
| `temperature_c` | Weather response `weather.temperature` | Copy the number |
| `humidity_pct` | Weather response `weather.humidity` | Copy the number |
| `rainfall_mm_last_7_days` | Weather response `weather.rainfall_last_7_days_mm` | Copy the number |
| `symptoms` | Form (JSON array of selected keys) | Convert to an object with all 11 keys — code below |

Never fill a missing value with a default.

### Example request
```json
{
  "crop": "wheat", "growth_stage": "vegetative", "soil_type": "sandy",
  "last_fertilizer_type": "No_Fertilizer", "days_since_fertilizer": "not_applicable",
  "irrigation_source": "tube_well", "irrigation_adequacy": "excessive",
  "temperature_c": 30.0, "humidity_pct": 55, "rainfall_mm_last_7_days": 45.0,
  "ph_value": 4.5, "soil_moisture_pct": 62, "light_intensity_lux": 28000,
  "symptoms": {
    "yellowing_older_leaves": true, "purple_reddish_tint": false, "brown_scorched_leaf_edges": false,
    "stunted_growth": true, "poor_flowering_or_fruiting": false, "weak_stems": false,
    "interveinal_chlorosis_older_leaves": false, "interveinal_chlorosis_young_leaves": false,
    "leaf_curling_brittle": false, "short_internodes_small_leaves": false, "none_visible": false
  }
}
```

### Response — HTTP 200 (shape)
```
crop_supported              true
module2a                    6 nutrients, each {level: low|medium|high, confidence: 0–1},
                            overall_nutrient_health, input_typicality {anomaly_score, flag}, model_version
module2b                    ph / soil_moisture / light — each {current, ideal_range, gap, status: ok|moderate|critical};
                            ph also has nutrient_lockout_note
overall_soil_health_score   0–100 (or null)
overall_soil_health_label   good | moderate | poor (or null)
recommendation_notes        farmer-ready text: headline, needs_attention, looking_fine, caveat, and optional notes
model_version, module2a_model_version
```
Full example: `samples/sample_response.json` in the zip.

- Nutrient levels are lowercase (`low`, `medium`, `high`) — unlike the Weather module.
- A crop outside the 15 supported returns **HTTP 200** with `crop_supported: false`, a `message`,
  and `null` everywhere else. It is not an error.
- Treat `overall_soil_health_score` and `overall_soil_health_label` as possibly `null`.

**Errors**

| Status | When | Body |
|---|---|---|
| 422 | Missing, wrong type, out of range, or breaks a rule (e.g. `none_visible` with another symptom) | `{"detail": [...]}` |
| 503 | Model files missing or failed their checksum check | `{"message": "Prediction Failed: model artifacts unavailable."}` |
| 500 | Any other internal failure | `{"message": "Prediction Failed"}` |

---

## 7. Django example

```python
import json
import requests
from django.conf import settings

TIMEOUT = int(settings.AI_MODULE_TIMEOUT_SECONDS)  # 90 — covers a cold start on the free host
SYMPTOM_KEYS = [
    "yellowing_older_leaves", "purple_reddish_tint", "brown_scorched_leaf_edges",
    "stunted_growth", "poor_flowering_or_fruiting", "weak_stems",
    "interveinal_chlorosis_older_leaves", "interveinal_chlorosis_young_leaves",
    "leaf_curling_brittle", "short_internodes_small_leaves", "none_visible",
]

class AIModuleError(Exception):
    pass

def get_weather(lat, lon, farm_id):
    try:
        r = requests.post(f"{settings.WEATHER_MODULE_URL}/predict",
                          json={"latitude": lat, "longitude": lon, "farm_id": farm_id}, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise AIModuleError("Weather service is temporarily unavailable.") from exc
    if r.status_code != 200:
        raise AIModuleError("Weather service is temporarily unavailable.")
    return r.json()

def get_soil_analysis(form, weather):
    selected = json.loads(form["symptoms"])
    body = {
        "crop": form["crop"], "growth_stage": form["growth_stage"], "soil_type": form["soil_type"],
        "last_fertilizer_type": form["last_fertilizer_type"],
        "days_since_fertilizer": form["days_since_fertilizer"],
        "irrigation_source": form["irrigation_source"], "irrigation_adequacy": form["irrigation_adequacy"],
        "ph_value": float(form["ph_value"]),
        "soil_moisture_pct": float(form["soil_moisture_pct"]),
        "light_intensity_lux": float(form["light_intensity_lux"]),
        "temperature_c": weather["weather"]["temperature"],
        "humidity_pct": weather["weather"]["humidity"],
        "rainfall_mm_last_7_days": weather["weather"]["rainfall_last_7_days_mm"],
        "symptoms": {key: key in selected for key in SYMPTOM_KEYS},
    }
    try:
        r = requests.post(f"{settings.SOIL_MODULE_URL}/predict", json=body, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise AIModuleError("AI module is currently unavailable.") from exc
    if r.status_code == 422:
        raise ValueError(r.json()["detail"])          # our request is wrong — fix it, don't retry
    if r.status_code != 200:
        raise AIModuleError("AI module is currently unavailable.")
    return r.json()                                    # store exactly as returned
```

The two error messages match `REST_API_SPEC.md` Section 13.

---

## 8. Timeouts, cold starts and retries

- **Timeout: 90 seconds per call** while using the live URLs. The free host puts a service to
  sleep after about 15 minutes idle, and the first request after that takes 30–60 s. One analyze
  request can wake both services in turn.
- **Warm response times on the live URLs:** Weather about 1.3–1.6 s, Soil about 0.6–1.2 s.
  Self-hosted from the zip, Soil answers in about 0.15 s.
- **Retry** only on timeouts, connection errors, 500 or 503 — once, after a few seconds.
  **Never retry a 422**: the request itself is wrong.
- **Before a demo**, open both `/health` URLs in a browser a minute early to wake the services.

---

## 9. Health checks and monitoring

- `GET /health` on each service returns `{"status": "ok", "service": "weather-risk-module"}` or
  `{"status": "ok", "service": "soil-nutrient-module"}`. Use it for your admin
  `/api/v1/admin/ai-monitoring/` endpoint.
- Module 2's `/health` answers even if its model files are broken. To confirm it is really
  serving, send `samples/sample_request.json` to `/predict` and expect HTTP 200.
- **What is monitored today:** service logs, CPU/memory and deploy history, in the AI team's
  Render dashboard.
- **What is not:** neither service stores its predictions. Since Backend stores every response
  in PostgreSQL, **that database is where prediction monitoring should happen** — for example,
  predictions per crop, how often `module2a.input_typicality.flag` is `"unusual"` (a rising share
  means farmers' conditions are drifting from the training data), and how risk levels change over
  time.

---

## 10. Live URLs vs running from the zip

### Live URLs (hosted by the AI team on Render, free plan)

**Advantages**
- Start integrating immediately — no Python, PyTorch or model files to install.
- Always the latest version: the AI team pushes to GitHub and it redeploys automatically.
- Frontend, backend and AI work in parallel against the same running services.
- HTTPS included; demos work from any machine.
- The two modules run independently — if one fails, the other keeps working.

**Disadvantages**
- **Sleeps after ~15 minutes idle.** The first request after that takes 30–60 s.
- **Slower:** the free plan gives a small share of a CPU.
- **No authentication.** Anyone with the URL can call `/predict`, although `REST_API_SPEC.md`
  says AI modules are internal. The services store no data, but they can be spammed.
- **Depends on Render and the internet**, and on Open-Meteo for weather.
- **Farm coordinates leave your infrastructure** (encrypted over HTTPS, but sent to Render and
  Open-Meteo).
- **Changes go live on push** — no staging copy. A bad update affects everyone using the URL.
- **Limited free hours and short log history.** Not suitable for real farmers.

### Zip files (you run them)

**Advantages**
- Fast (Soil ~0.15 s) and never sleeps.
- Private: run on the same server or Docker network as Django, with no public URL.
- You control when to upgrade, and can test a new version before switching.
- No dependency on the AI team's hosting account.

**Disadvantages**
- You install, run and keep the services alive (Docker makes this simple — Section 12).
- Memory on your server: about 370 MB for both.
- New AI versions arrive as a new zip — you redeploy them yourselves.

**Recommendation:** use the live URLs now for development and demos. Run from the zips (or the
same Docker images) for production.

---

## 11. Known limitations and open items

1. **Weather response has extra fields.** `units`, `forecast` and `predicted_risk_assessment`
   are returned but not listed in `REST_API_SPEC.md` v2.1's Module 3 section. They are additive —
   store them unchanged — and the spec will be updated.
2. **Weather input.** The spec's Module 3 example shows only `farm_id`. The service needs
   `latitude` and `longitude` — Backend looks them up from the farm record and sends them.
3. **`farm_id`:** confirm whether Backend will always send it. The Weather module only echoes it.
4. **Module 2 crop ranges:** the 8 original crops are agronomy-reviewed. The 7 horticultural
   crops (eggplant, cucumber and the gourds) are provisional pending field validation. Values may
   change; field names will not.
5. **Weather risk thresholds** are rule-based placeholders pending agronomy review. Values may
   change; field names will not.
6. **Advisory output:** Module 2's accuracy is 54–66% per nutrient (against 33% chance). Present
   results as guidance, not a diagnosis — the farmer notes already do.

---

## 12. Running from the zip files

Both need **Python 3.13** or **Docker**. Unzip each into its own folder.

### With Docker (recommended)
```bash
# Weather
cd Weather_Module
docker build -t greenguard-module3 .
docker run -d --name module3 -p 8001:8001 greenguard-module3

# Soil & Nutrient
cd Stress_Module
docker build -t greenguard-module2 .
docker run -d --name module2 -p 8002:8002 greenguard-module2
```
Both images have been built and tested. Module 2's image includes a health check
(`docker ps` shows `healthy`) and a `docker-compose.yml` whose service block can be copied into
the project-wide compose file. Change the port with `-e PORT=9000 -p 9000:9000`.

### With Python
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
cd api
python main.py                 # Weather on :8001, Soil on :8002
```

### Check it works
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl -X POST http://localhost:8002/predict -H "Content-Type: application/json" --data @samples/sample_request.json
```

### Verify a deployment
```bash
cd Stress_Module && pytest tests/test_deployment.py -v   # model checksums, library versions, recorded outputs
cd Weather_Module && pytest tests/test_api.py -v
```

---

## 13. What Backend must not do

- Do not call the Soil module before the Weather module, or with made-up weather values.
- Do not modify, recalculate or rename any field — store and forward responses exactly.
- Do not re-sort `recommendation_notes.needs_attention` or rebuild confidence wording.
- Do not parse `*_reason`, `message` or note text for logic — branch on `*_risk`, `level`,
  `status` and `crop_supported`.
- Do not send `None` or `null` for "no fertilizer" — send `"No_Fertilizer"`.
- Do not retry a 422.
- Do not expose these URLs to the frontend — only Django calls them.

**Questions:** contact the GreenGuard AI team. Full detail for each module is in its
`README.md` and `docs/` folder.
