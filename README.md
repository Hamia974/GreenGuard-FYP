# GreenGuard

AI-assisted plant health monitoring and agricultural decision support for farmers — Final Year Project.

## Problem

Smallholder farmers often lack quick access to an agronomist. A leaf disease, a nutrient deficiency, or a weather pattern that favours fungal infection is usually noticed late, after yield is already lost. GreenGuard gives a farmer three independent checks from a phone or browser: what disease a leaf photo most likely shows, how healthy their soil and nutrients look, and what risks the current weather poses to their farm. The three results are shown side by side as a single report.

The interface is available in English and Urdu (right-to-left).

## Modules

GreenGuard has three independent AI modules plus an application-level report. Each module has one responsibility and returns its own JSON contract. The backend calls the modules, stores their outputs unchanged, and never combines them into a final diagnosis or confidence score.

| Module | Responsibility | Where it runs | Backend client |
|---|---|---|---|
| **1 — Disease Detection** | Top-3 disease shortlist from one leaf photo. Returns `status: "uncertain"` with `prediction: null` when it is not confident. | External hosted service (`DISEASE_MODULE_URL`, authenticated with `X-API-Key`) | `backend/ai_services/disease_module_client.py` |
| **2 — Soil & Nutrient Health** | Risk levels for 6 nutrients from a farmer questionnaire, pH/moisture/light comparison, and a 0–100 soil-health score | Hosted service, or the delivered source in `ai/Stress_Module` (port 8002) | `backend/ai_services/module2_client.py` |
| **3 — Weather Risk** | Current weather plus fungal-disease, heat-stress and drought risk from farm coordinates (Open-Meteo + rule engine) | Delivered source in `ai/Weather_Module/Weather_Module` (port 8001) | `backend/weather/services.py` |
| **4 — Integrated Analysis Report** | Stores the Module 1, 2 and 3 results side by side (`prediction_report.module1/module2/module3`) and displays each as its own section. Not an AI model. | Backend + frontend | `backend/predictions/` |

AI contracts: [`ai/API_CONTRACT.md`](ai/API_CONTRACT.md) (Module 1), [`ai/BACKEND_HANDOFF.md`](ai/BACKEND_HANDOFF.md) (Modules 2 and 3), and [`docs/REST_API_SPEC.md`](docs/REST_API_SPEC.md).

## Architecture

```
Browser (Next.js)  ──HTTPS, cookies──▶  Django REST API  ──▶  Module 1 (external)
                                             │           ──▶  Module 2 (service)
                                             │           ──▶  Module 3 (service → Open-Meteo)
                                             ▼
                                        PostgreSQL
```

- The frontend talks **only** to the Django REST API (`/api/v1/`). It never calls an AI service.
- **Quick Scan:** the farmer uploads a leaf photo for a selected farm. The backend calls Module 1, attaches the farm's latest stored Module 2 result (not a live call), calls Module 3 for the farm's coordinates, and stores the three results as one report in the farm's history.
- Each module also has its own standalone page and endpoint (`/module1`, `/module2`, `/weather`).
- Authentication uses JWTs in HttpOnly cookies, with CSRF protection and refresh-token rotation. Full design: [`docs/AUTHENTICATION.md`](docs/AUTHENTICATION.md).
- Roles: **Farmer** (farms, scans, history, notifications, profile) and **Admin** (users, predictions, analytics, system health).

## Technology stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS 4, shadcn/ui (Base UI), TanStack Query, React Hook Form, Zod, Axios, next-intl, Framer Motion, Recharts, Lucide |
| Backend | Python, Django 6, Django REST Framework, Simple JWT (with token blacklist), django-filter, django-cors-headers, Pillow, Gunicorn |
| Database | PostgreSQL 16 |
| AI services | FastAPI microservices (scikit-learn/XGBoost for Module 2; rule engine plus PyTorch LSTM forecast for Module 3); Module 1 is hosted by the AI team |
| Tooling | Docker / Docker Compose, GitHub Actions CI |

## Repository layout

```
GreenGuard/
├── frontend/          Next.js app (app/, features/, components/, lib/, messages/ en+ur)
├── backend/           Django project (config/) and apps: authentication, users, farms,
│                      module1, module2, weather, predictions, history, dashboard,
│                      notifications, adminpanel, ai_services
├── ai/                AI-team deliveries: Stress_Module (Module 2), Weather_Module (Module 3),
│                      Module 1 API contract and backend handoff notes
├── docs/              Specifications (source of truth) and integration status notes
├── docker-compose.yml Local container stack
└── .github/workflows/ CI (backend checks + tests, frontend i18n/typecheck/lint/build)
```

Authoritative specifications, in priority order: `docs/GREEN_GUARD_SYSTEM_SPECIFICATION_V2.md`, `docs/REST_API_SPEC.md`, `docs/DATABASE_SPECIFICATION.md`, `docs/UI_SPECIFICATION.md`, `docs/AI_MODULE_DELIVERY_SPECIFICATION.md`.

## Prerequisites

- Node.js 22 and npm
- Python 3.12 or newer (CI and the Docker image use 3.12)
- PostgreSQL 16 (or Docker)
- Docker Desktop with Compose v2 (optional, for the container stack)
- For live Module 1 calls: an API key from the AI team

## Local development (without Docker)

### 1. Database

Create an empty PostgreSQL database (default name `greenguard_db`) and a user that can create databases (the test runner creates `test_greenguard_db`).

### 2. Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate    macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in real values
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver         # http://localhost:8000
```

Health check: `GET http://localhost:8000/health/`.

### 3. AI services (only when `ENABLE_MOCK_AI=False`)

```bash
# Module 3 — Weather Risk (port 8001)
cd ai/Weather_Module/Weather_Module
python -m venv venv && venv\Scripts\activate   # or source venv/bin/activate
pip install -r requirements.txt
cd api && python main.py

# Module 2 — Soil & Nutrient (port 8002), only if not using the hosted URL
cd ai/Stress_Module
pip install -r requirements.txt
cd api && uvicorn main:app --port 8002
```

Module 1 is always reached at `DISEASE_MODULE_URL`. Ask the AI team for `GREENGUARD_API_KEY`.

### 4. Frontend

```bash
cd frontend
npm ci
cp .env.local.example .env.local
npm run dev                         # http://localhost:3000
```

Use `localhost` (not `127.0.0.1`) for both the frontend and the API in development. The session cookies use `SameSite=Lax`, and mixing the two hostnames makes the requests cross-site.

## Docker

`docker-compose.yml` runs PostgreSQL, the Django backend (Gunicorn), the Next.js frontend (standalone server), and the Module 2 and Module 3 services. Module 1 is not containerised: it stays an external service.

> **Status:** the Compose file validates (`docker compose config`), but building and running the stack end-to-end has **not yet been verified** in this repository.

```bash
cp .env.example .env                     # Postgres credentials + frontend build-time URL
cp backend/.env.example backend/.env     # backend config (SECRET_KEY, JWT_SECRET, AI settings, ...)
docker compose up --build -d
docker compose exec backend python manage.py migrate
docker compose ps                        # all services should become "healthy"
```

| Service | Host port | Notes |
|---|---|---|
| frontend | 3000 | `NEXT_PUBLIC_*` values are baked in at build time; rebuild after changing them |
| backend | 8000 | `/health/` checks the database connection |
| weather-module | 8001 | Module 3 |
| stress-module | 8002 | Module 2; Compose overrides `STRESS_MODULE_URL` to use this container |
| db | not published | Data persists in the `postgres_data` volume |

- These ports collide with a running local dev setup (`npm run dev`, `runserver`, a local Module 3). Stop those first, or change the host ports.
- Under Compose, the backend gets `DATABASE_NAME/USER/PASSWORD` from the root `.env` (the same values used to initialise Postgres), plus `DATABASE_HOST=db`.
- Migrations are a separate step and never run automatically on container start.
- Stop: `docker compose down` keeps the volumes. **`docker compose down -v` deletes the database and uploaded media.**
- Known gap: Gunicorn does not serve Django's static files, so `/admin/` is unstyled in the container. With `DEBUG=False`, uploaded media is not served either (see Known limitations).

## Environment variables

Names only. See the `.env.example` files for documented defaults. Never commit real values.

| File | Variables |
|---|---|
| `.env` (root, Compose only) | `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_NAME` |
| `backend/.env` | Core: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` · Database: `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT` · JWT/cookies: `JWT_SECRET`, `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, `JWT_REFRESH_TOKEN_LIFETIME_DAYS`, `JWT_COOKIE_SECURE`, `JWT_COOKIE_SAMESITE`, `JWT_COOKIE_DOMAIN` · CORS/CSRF: `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS` · Email: `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL`, `EMAIL_VERIFICATION_MAX_AGE_HOURS`, `FRONTEND_BASE_URL` · AI: `ENABLE_MOCK_AI`, `DISEASE_MODULE_URL`, `GREENGUARD_API_KEY`, `STRESS_MODULE_URL`, `WEATHER_MODULE_URL`, and `*_REQUEST_TIMEOUT_SECONDS` / `*_HEALTH_TIMEOUT_SECONDS` for each module · Geocoding: `GEOCODING_PROVIDER`, `GEOCODING_COUNTRY_CODE`, `GEOCODING_REQUEST_TIMEOUT_SECONDS`, `GOOGLE_MAPS_GEOCODING_API_KEY` · Throttling: `THROTTLE_RATE_ANON`, `THROTTLE_RATE_USER`, `THROTTLE_RATE_AUTH`, `THROTTLE_RATE_AUTH_REFRESH`, `THROTTLE_RATE_GEOCODE` · Production: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS` |
| `frontend/.env.local` | `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_NAME`, `NEXT_PUBLIC_ENVIRONMENT` |

With `DEBUG=False`, the backend refuses to start if `SECRET_KEY` or `DATABASE_PASSWORD` is unset or still a placeholder.

**Mock mode:** with `ENABLE_MOCK_AI=True`, the backend returns fixed responses that match the AI contracts, so no AI service needs to be running. Switching it off requires no frontend changes.

## Tests and validation

```bash
# Backend (uses a separate test_<DATABASE_NAME> database)
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test --noinput

# Frontend
cd frontend
npm run check:i18n     # English/Urdu catalogue parity
npm run typecheck
npm run lint
npm run build          # see note below
```

`npm run build` writes to `frontend/.next`, which is the same directory `npm run dev` uses. Stop the dev server first, or build a copy of the folder elsewhere.

The frontend has no automated unit or end-to-end tests yet. The AI modules ship their own pytest suites in `ai/*/tests/`. CI (`.github/workflows/ci.yml`) runs the backend checks and tests against PostgreSQL, and the frontend i18n check, typecheck, lint and build.

## Deployment

Not deployed yet. The backend has production hardening behind `DEBUG=False` (HTTPS redirect, HSTS, secure cookies, startup secret checks), and `manage.py check --deploy` passes. A production deployment still needs:

- static and media file serving (e.g. WhiteNoise or a reverse proxy, plus object storage for uploads);
- a shared cache (e.g. Redis) so rate limits apply across Gunicorn workers;
- `NUM_PROXIES` configured behind a reverse proxy;
- an SMTP email backend;
- a hosting decision for Modules 2 and 3.

See `docs/AUTHENTICATION.md` §1 for cookie settings across same-site and cross-site domains.

## Known limitations

- Logging out revokes the refresh token and clears the cookies, but it does not revoke an already-issued access token: a copy taken before logout stays valid until it expires. The access-token lifetime is 10 minutes (`JWT_ACCESS_TOKEN_LIFETIME_MINUTES`) to keep that window short. Password changes and resets revoke tokens immediately.
- Open-Meteo's free tier is for non-commercial use only.
- Hosted AI services on free tiers may cold-start slowly; the backend timeouts allow for this.

## Development workflow

- Follow `CLAUDE.md` and the specifications in `docs/`. API endpoints, JSON fields and AI contracts are not renamed or changed without the project owner's approval.
- Work on a branch, run the checks above, and open a pull request; CI must pass.
- Never commit `.env` files, credentials, uploaded media, logs, virtual environments, or build output (see `.gitignore`).

## Credits

Crop, soil, irrigation and symptom photos in `frontend/public/images/` come from Wikimedia Commons. Authors, sources and licences are listed in [`frontend/public/images/CREDITS.json`](frontend/public/images/CREDITS.json). AI modules were developed by the GreenGuard AI team.
