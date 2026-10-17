# GreenGuard — Module 3: Weather Risk Engine

**Version:** 1.12.0 · **Status:** complete, runnable, live-tested (including a clean `pip install -r requirements.txt` from a fresh environment)

## 1. What this module does

Given a farm's GPS coordinates, this service:
1. Fetches real weather data (temperature, humidity, rainfall, wind speed) from the free [Open-Meteo](https://open-meteo.com/) API.
2. Applies rule-based thresholds to estimate **fungal disease risk**, **heat stress risk**, and **drought risk**, each with a plain-English reason sentence.
3. Additionally forecasts tomorrow's weather with a small LSTM and runs the same risk rules on that forecast, as a nullable, best-effort supplement (§8).
4. Returns the result as JSON, in the exact format defined in `REST_API_SPEC.md`.

**Core risk logic is intentionally rule-based, not learned** — see `docs/MODEL_DOCUMENTATION.md` for why. The LSTM forecast add-on (v1.6.0+) is a separate, additive layer on top of that rule engine, not a replacement for it; the module is not "pure rule-based" anymore, but its risk decisions still are.

## 2. Folder structure

```
AI_MODULE_3_WEATHER/
├── api/
│   ├── main.py              # The REST API itself
│   ├── weather_service.py   # Open-Meteo fetch + risk logic
│   ├── schemas.py           # Exact request/response JSON contract
│   ├── lstm_model.py        # LSTM architecture (shared by training + inference)
│   └── lstm_forecast.py     # Additive next-day forecast + predicted risk
├── training/
│   └── train_lstm.py        # Offline script — retrain the LSTM, not run by the service
├── models/
│   ├── weather_lstm.pt      # Trained LSTM weights
│   ├── scaler.json          # Feature normalization stats
│   └── eval_report.json     # Held-out MAE/RMSE vs. persistence/climatology baselines
├── docs/
│   ├── MODEL_DOCUMENTATION.md
│   └── INTEGRATION_GUIDE.md
├── tests/
│   └── test_api.py
├── samples/
│   ├── sample_request.json
│   └── sample_response.json
├── config/
├── requirements.txt
├── Dockerfile
├── .dockerignore
├── README.md
└── .env.example
```

## 3. Installation

Open a terminal inside this folder and run:

```bash
python -m venv venv

# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

## 4. Running the API

The port comes from the `PORT` variable in `.env` (defaults to `8001` if not set — see section 7).

```bash
cd api
python main.py
```

You should see something like:
```
Uvicorn running on http://0.0.0.0:8001
```

## 5. Testing it yourself

Open this in your browser — FastAPI gives you a free interactive test page:
```
http://localhost:8001/docs
```

Click on `POST /predict` → "Try it out" → paste this in:
```json
{
  "latitude": 31.5204,
  "longitude": 74.3587,
  "farm_id": "farm_001"
}
```
→ Click Execute. You should get back weather + risk data for Lahore.

## 6. Running the automated tests

```bash
pip install pytest
cd ..
pytest tests/test_api.py -v
```
All tests should pass.

## 7. Environment variables

Copy `.env.example` to `.env` and adjust if needed (defaults work out of the box — Open-Meteo requires no key). `PORT` controls what port the server binds to for both the `python main.py` path and the Docker container (`docker run -e PORT=9000 ...` or `--env-file .env`, default `8001` either way).

## 8. LSTM forecast add-on (optional, introduced v1.6.0, retrained on 14 Pakistan coordinates as of v1.9.0)

`api/lstm_forecast.py` adds two extra, **nullable** response fields — `forecast` (next-day weather) and `predicted_risk_assessment` (the existing rule engine run on that forecast) — without touching the core `weather`/`risk_assessment` contract at all. See `docs/MODEL_DOCUMENTATION.md` → "LSTM forecast add-on" for the full details, the held-out evaluation numbers, and known geographic coverage limits (weak outside the Punjab agricultural belt — see "Known limitations" there).

Trained weights are already included at `models/weather_lstm.pt` + `models/scaler.json`, so no extra setup is needed to run the service as-is. To retrain (e.g. with more coordinates or a longer date range):
```bash
cd training
python train_lstm.py
```
This re-fetches training data live from Open-Meteo's free historical archive API, trains on a chronological 80/20 split per location (never on the same days it's tested on), and overwrites `models/weather_lstm.pt` + `models/scaler.json` + `models/eval_report.json`. The last file has real held-out MAE/RMSE against persistence and climatology baselines — see `docs/MODEL_DOCUMENTATION.md` → "Evaluation" for the current numbers and an honest read of them (the model beats persistence on humidity/rainfall but not yet on temperature). If the model/scaler files are ever missing or fail to load, `/predict` still returns 200 — it just returns `forecast: null` and `predicted_risk_assessment: null`.

## 9. Important notes

- The rule thresholds (20-30°C + 80% humidity = High fungal risk, etc.) are **placeholders**, carried over from the architecture doc. They're isolated in one function (`assess_risk` in `weather_service.py`) so they're easy to update later once reviewed.
- `farm_id` in the response simply echoes back whatever the Backend sends in the request (defaults to `"unknown"` if not provided) — confirm with Backend whether they'll always send it.
- If Open-Meteo is unreachable, the endpoint returns HTTP 500 with `{"message": "Prediction Failed: weather service unavailable."}` — every 500 uses the `message` key (fixed in v1.10.0; see `docs/INTEGRATION_GUIDE.md` → "Error responses" for the bug that preceded this and why it mattered).
- `forecast` and `predicted_risk_assessment` are best-effort and can legitimately be `null` — see §8 above. Never treat them as guaranteed-present.
- Every risk label (`fungal_disease_risk`, `heat_stress_risk`, `drought_risk`, in both `risk_assessment` and `predicted_risk_assessment`) has a sibling `*_reason` string (v1.7.0+) — a sentence naming the specific threshold/value that produced it. Safe to display; don't parse it for logic, wording can change between versions.
- `REST_API_SPEC.md` is referenced throughout this module's docs as the source of truth for the JSON contract, but it is not present in this repository as of this delivery — confirm with the Project Manager / Backend team where the current copy lives before relying on it for contract verification.
