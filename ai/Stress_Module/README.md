# GreenGuard — Module 2: Soil & Nutrient Analysis

**Version:** 1.2.0 · **Model:** `module2a-v5` · **Port:** 8002 · **Tests:** 89 passing

## 1. What this module does

A farmer answers a short soil questionnaire (crop, growth stage, soil type, fertilizer,
irrigation, visible symptoms) and takes three readings with a soil meter (pH, soil moisture,
light). With the local weather added, one call to `POST /predict` returns:

- **Nutrient risk** for nitrogen, phosphorus, potassium, magnesium, zinc and boron —
  `low` / `medium` / `high`, each with a confidence (Module 2A, machine learning).
- **Growing conditions** — pH, moisture and light compared with the crop's ideal range, with
  a plain-language pH note (Module 2B, rules).
- **Soil-health score** — 0–100 with a `good` / `moderate` / `poor` label.
- **Farmer notes** — a ready-to-display summary of what needs attention and why.

Module 2A and 2B are internal; `/predict` is the only prediction endpoint.

## 2. Documentation

| Document | For | Contents |
|---|---|---|
| `docs/INTEGRATION_GUIDE.md` | Backend | **Start here** — where each value comes from, request, response, errors |
| `docs/MODEL_DOCUMENTATION.md` | Everyone | Inputs, outputs, performance, rules, training data, versions |
| `docs/Module2_Orchestrator_Spec.md` | Backend | Full request/response contract and scoring formula |
| `docs/Module2_Frontend_Form_Spec.md` | Frontend | Form fields and how to display the result |
| `docs/module2_field_options.json` | Frontend, Backend | Allowed values for every field |

The official project contract is `REST_API_SPEC.md` (v2.1), Section 9 → AI Module 2.

## 3. Folder structure

```
Stress_Module/
├── api/                   # The FastAPI service
│   ├── main.py            # Endpoints: /health, /predict
│   ├── schemas.py         # Request/response contract
│   ├── orchestrator_service.py
│   ├── module2a_service.py
│   ├── module2b_service.py
│   ├── recommendations.py # Farmer notes
│   └── manifest.py        # Model-file checksum check
├── models/                # Trained model files + manifest.json (checksums)
├── docs/                  # Documentation (see above)
├── samples/               # Sample request/response and test scenarios
├── tests/                 # Automated tests, including the deployment check
├── training/              # Training notebook (AI team; not run by the service)
├── config/                # Reserved — configuration is via environment variables
├── Dockerfile · docker-compose.yml · .dockerignore
├── requirements.txt
├── .env.example
└── README.md
```

The training data (`data/`) and analysis scripts (`scripts/`) stay with the AI team and are not
part of the delivery package.

## 4. Requirements

- Python 3.13, CPU only — no GPU, internet access or API keys needed
- About 200 MB of memory; starts in about 3 seconds; about 50 ms per prediction
- Libraries in `requirements.txt`, pinned to the versions the models were trained with

## 5. Installation

```bash
python -m venv venv

# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

## 6. Configuration

Copy `.env.example` to `.env` to change a setting. The defaults work as they are.

| Variable | Default | Purpose |
|---|---|---|
| `PORT` | `8002` | Port the service listens on |
| `MODELS_DIR` | `models/` in this folder | Absolute path to the model files, if stored elsewhere |
| `WEB_CONCURRENCY` | `1` | Number of worker processes (about 200 MB each) |

## 7. Running the API

**Locally**

```bash
cd api
python main.py
```

The service runs at `http://localhost:8002`.

**With Docker**

```bash
docker build -t greenguard-module2 .
docker run -d --name module2 -p 8002:8002 greenguard-module2
```

Or run `docker compose up --build -d`. The image runs as an unprivileged user and has a
built-in health check, so `docker ps` shows the container as `healthy` once it is ready.

## 8. Using the API

| Endpoint | Purpose |
|---|---|
| `GET /health` | Returns `{"status": "ok", "service": "soil-nutrient-module"}` |
| `POST /predict` | Soil and nutrient analysis |

To try it, open `http://localhost:8002/docs`, choose `POST /predict` → **Try it out**, and paste
the contents of `samples/sample_request.json`. The expected answer is in
`samples/sample_response.json`; more examples are in `samples/test_scenarios.json`.

| Status | Meaning |
|---|---|
| 200 | Result returned — or `crop_supported: false` for a crop outside the 15 supported |
| 422 | A field is missing or invalid |
| 503 | Model files missing or failed their checksum check |
| 500 | Unexpected failure |

## 9. Testing

```bash
pytest tests/ -v
```

After deploying to a new machine, run the deployment check. It confirms the model files are
intact, the libraries match training, and the results match the recorded release outputs:

```bash
pytest tests/test_deployment.py -v

# inside Docker
docker run --rm greenguard-module2 python -m pytest -p no:cacheprovider /app/tests/test_deployment.py
```

One test needs the training data and is skipped automatically when `data/` is absent.

## 10. Retraining (AI team)

1. Run `training/module2a_nutrient_risk.ipynb` with the training data in `data/`. It replaces the
   model files and writes a new `models/manifest.json`.
2. Record the new release outputs: `python tests/test_deployment.py --record`
3. Build the delivery package: `python scripts/package_delivery.py` (writes `Stress_Module.zip`
   next to this folder, without the data, caches or `.env`).

## 11. Important notes

- `ph_value`, `soil_moisture_pct` and `light_intensity_lux` are required.
- Send `No_Fertilizer` — never `None` — when no fertilizer was used.
- Backend must store and forward the response unchanged, including `recommendation_notes`.
- The soil-health score is a transparent weighted sum, not a trained model.
- Module 2B's crop ranges have been through two agronomy reviews (GG-M2-AR-01, GG-M2-AR-02 —
  see `docs/MODEL_DOCUMENTATION.md` → Module 2B rules); the 7 horticultural crops' ranges are
  still marked provisional pending local field validation, the original 8's are reviewer-confirmed.
- The Docker files are ready but have not yet been run through `docker build`, because Docker is
  not installed on the development machine.

**Maintained by:** GreenGuard AI team
