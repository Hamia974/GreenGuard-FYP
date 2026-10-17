# GreenGuard Project Implementation Roadmap

## Version

1.0

---

# Purpose

This document defines the official implementation order for the GreenGuard project.

All development must strictly follow this roadmap.

Claude Code must complete one phase at a time.

Do not begin a new phase until the current phase has been completed, tested, and approved.

The documents inside the `/docs` directory remain the source of truth for all implementation details.

---

# Source Documents

Before starting any implementation, read and follow the following documents:

1. GREEN_GUARD_SYSTEM_SPECIFICATION_V2.md
2. REST_API_SPEC.md
3. DATABASE_SPECIFICATION.md
4. UI_SPECIFICATION.md
5. AI_MODULE_DELIVERY_SPECIFICATION.md

Never contradict these documents.

---

# Development Rules

- Complete one phase at a time.
- Never skip phases.
- Do not redesign the architecture.
- Follow REST_API_SPEC.md exactly.
- Follow DATABASE_SPECIFICATION.md exactly.
- Follow UI_SPECIFICATION.md exactly.
- Ask for approval before moving to the next phase.
- Keep the code modular and maintainable.
- Write production-quality code.
- Use clean architecture principles.
- Use reusable components whenever possible.

---

# Phase 1 — Project Setup

## Objective

Create the complete project foundation.

## Backend

- Create Django project
- Configure Django REST Framework
- Configure PostgreSQL
- Configure CORS
- Configure Media & Static files
- Configure Environment Variables
- Configure Logging

## Frontend

- Create Next.js project
- Configure Tailwind CSS
- Configure App Router
- Configure Global Layout
- Configure Fonts
- Configure Theme

## Shared

- Create project folder structure
- Configure Docker (if applicable)
- Configure Git structure
- Configure API base URLs

## Deliverables

- Backend runs successfully
- Frontend runs successfully
- Database connected
- Project structure completed

---

# Phase 2 — Authentication Module

## Objective

Implement complete authentication.

## Features

- User Registration
- User Login
- Logout
- JWT Authentication
- Password Hashing
- Protected Routes
- Forgot Password (optional)
- User Profile

## Backend

- Authentication APIs
- User Model
- JWT Configuration

## Frontend

- Registration Page
- Login Page
- Authentication Context
- Protected Navigation

## Deliverables

Authentication system fully operational.

---

# Phase 3 — Farm Management Module

## Objective

Allow users to manage farms.

## Features

- Create Farm
- Update Farm
- Delete Farm
- View Farms
- Select Active Farm

## Farm Information

- Farm Name
- Address
- Latitude
- Longitude

Location may be obtained using:

- Device GPS
OR
- Address Geocoding

Coordinates are stored in the database.

## Deliverables

Farm management fully functional.

---

# Phase 4 — Dashboard Module

## Objective

Develop the main dashboard.

## Components

- Welcome Section
- Weather Card
- Recent Predictions
- Farm Summary
- Statistics Cards
- Notification Preview
- Quick Actions

Dashboard should use responsive design.

---

# Phase 5 — Weather Module

## Objective

Implement weather integration.

## Backend Flow

Frontend

↓

Backend

↓

Database

↓

Retrieve Farm Coordinates

↓

Call Weather Module

↓

Return Weather Data

## Features

- Current Weather
- Weather Forecast
- Environmental Risk
- Weather History (optional)

The frontend never directly calls external weather services.

## Phase 5 Status Update (2026-09-01)

The dedicated Weather Dashboard page (`/weather`, `frontend/features/weather/`)
originally deferred during Phase 5 — see the 2026-08-08 roadmap-memory note
on UI_SPECIFICATION.md section 14 having no real forecast data source — has
now been built as a **page shell**. It reuses the existing
`GET /api/v1/dashboard/weather/` endpoint and `weather/services.py`
implementation exactly as-is (no new backend code, no new weather source):
current temperature/humidity/wind/rainfall and the three rule-engine risk
levels (fungal disease, heat stress, drought) are shown as real data with
proper loading/empty(no farm)/error states, and the forecast/UV/pressure/
map widgets described in UI_SPECIFICATION.md section 14 are shown as
explicitly-labeled "coming soon" placeholders rather than fabricated. The
Dashboard's "Weather Dashboard" quick action now links here instead of
being disabled. See `docs/MODULE3_INTEGRATION_STATUS.md` for why this
remains a shell: the AI team's Module 3 delivery (`ai/weather.zip`) turned
out to contain only a video file, not a usable service/contract.

## Phase 5 Status Update (2026-09-02) — Real Module 3 Delivered and Integrated

The AI team redelivered Module 3 as a real, runnable package at
`ai/Weather_Module/` (FastAPI + Open-Meteo + rule engine, plus an additive
nullable LSTM next-day forecast). See `docs/MODULE3_INTEGRATION_STATUS.md`
for the full delivery/integration writeup and REST_API_SPEC.md Sections 5A
and 9 for the exact, current contract. Summary of what changed:

- `backend/weather/services.py` no longer calls NASA POWER directly or
  re-derives risk thresholds — it calls the real module's `POST /predict`
  (`WEATHER_MODULE_URL`, default `http://localhost:8001`) and forwards its
  response unmodified, per CLAUDE.md's AI Contract. `ENABLE_MOCK_AI` (already
  used by Modules 1/2/4) now also gates Module 3.
- `GET /api/v1/dashboard/weather/`'s existing flat contract is unchanged for
  the frontend; it is now populated from the same Module 3 call via a pure
  field-flattening helper, not a second implementation.
- New `GET /api/v1/weather/current/` exposes the module's full contract
  (units, `*_reason` explanations, nullable `forecast` /
  `predicted_risk_assessment`) to the Weather page.
- The Weather page (`frontend/app/(app)/weather/`) now shows real current
  conditions, risk reasons, and a real (labeled experimental, single-day)
  forecast + predicted risk. UV index, wind direction/gusts, pressure/
  visibility, and the interactive map remain explicit "not yet available"
  placeholders — the delivered contract does not produce them, and none of
  it is fabricated.
- `docker-compose.yml` gained a `weather-module` service built from the
  module's own Dockerfile; the backend's `WEATHER_MODULE_URL` is overridden
  to `http://weather-module:8001` inside the compose network.
- `backend/config/settings.py` / `backend/.env.example`: `NASA_POWER_API_URL`
  and `WEATHER_REQUEST_TIMEOUT_SECONDS` removed (no longer referenced
  anywhere in the codebase); `WEATHER_MODULE_URL`,
  `WEATHER_MODULE_REQUEST_TIMEOUT_SECONDS`, and
  `WEATHER_MODULE_HEALTH_TIMEOUT_SECONDS` added.

---

# Phase 6 — Plant Analysis Module

## Objective

Implement image upload and AI prediction workflow.

## Features

- Upload Plant Image
- Image Validation
- Image Storage
- AI Request
- Save Prediction
- Display Results

Backend communicates with AI modules according to REST_API_SPEC.md.

## Module 2 Contract Status (as of 2026-08-22)

The Module 2 (Soil & Nutrient Health Check) input/output contract is now finalized — see REST_API_SPEC.md Section 8A and `docs/module2_field_options.json` / `docs/module2_io_examples.json`. It is documented as a standalone endpoint (`POST /api/v1/module2/analyze/`), independently usable outside of this phase's image-based prediction workflow (`POST /api/v1/predictions/analyze/`) — but its finalized output is also an upstream input to Module 4 (ANN Fusion) within that workflow.

> **Superseded 2026-10-03:** Module 4 is no longer an ANN Fusion model — see "Architecture Change — Module 4 Integrated Analysis Report" near the end of this document.

Module 4 (ANN Fusion) remains unfinalized. Fusion is documented as combining Module 1 (Image), Module 2 (Soil & Nutrient Health), and Module 3 (Weather) outputs. Exact input packaging (whether Module 2's output is passed verbatim or reduced) and the finalized output JSON contract are pending confirmation from the AI team.

This status note reflects a documentation/contract update only. Phase 6 implementation has not started and is not being marked complete as a result of this update — approval to begin implementing Module 2 (or Phase 6) must still be requested separately.

---

# Phase 7 — Prediction History Module

## Objective

Allow users to review previous predictions.

## Features

- Prediction List
- Search
- Filter
- View Details
- Delete Prediction

History is grouped by farm.

---

# Phase 8 — Notification Module

## Objective

Implement user notifications.

## Features

- View Notifications
- Mark as Read
- Delete Notification
- Notification Badge

## Phase 8 Status Update (2026-09-01)

Wired the one real creation trigger this app has an actual event for:
`predictions/views.py`'s `PredictionAnalyzeView` now creates a
`Notification` row ("Prediction Completed" / "Your latest plant analysis is
ready.", matching REST_API_SPEC.md section 7's own documented example
verbatim) after every successful analysis. Previously no endpoint ever
created a notification outside of tests, so `GET /api/v1/notifications/`
and the navbar's unread badge (`notification_count`, already wired to real
data since Phase 4) were always empty/zero for every real user despite
being fully implemented. No other trigger was added — no other real event
in this app currently has a corresponding documented notification.

---

# Phase 9 — User Settings Module

## Objective

Provide account management.

## Features

- Edit Profile
- Change Password
- Manage Farms
- Preferences

## Phase 9 Status Update (2026-09-01)

Added a read-only "Account Information" card to `/profile`
(`frontend/features/profile/components/account-information-card.tsx`)
showing Email, Account Type, Member Since, and Account ID — all already
returned by the existing `GET /api/v1/profile/` response, no backend change.
This closes the one real gap against UI_SPECIFICATION.md section 16.7 that
had a genuine data source. "Last Login" and "Email Verification Status"
(also listed in 16.7) were deliberately left out: neither field is ever
populated anywhere in this app (no login-signal wiring sets `last_login`;
no email-verification flow exists to set `is_verified`), so displaying them
would be a permanently-null/false field with no real action behind it.

The "Preferences" feature area (Notification Preferences, Appearance,
Privacy, Language, Sessions, Connected Devices — UI_SPECIFICATION.md
sections 16.9–16.14) is still intentionally not implemented, for the same
reason recorded in the original Phase 9 decision: none of it has a
REST_API_SPEC.md contract or backing model, and several of the UI spec's
own subsections are explicitly labeled "(Future)". Building toggles that
don't persist to a real backend would be exactly the kind of fake
frontend-only state this project's rules prohibit.

---

# Phase 10 — AI Integration

## Objective

Integrate all AI modules.

## Modules

- Image Analysis
- Weather Module
- Crop Recommendation
- ANN Fusion

## Rules

- Follow REST_API_SPEC.md exactly.
- Do not modify JSON contracts.
- Do not modify endpoint names.
- Handle API failures gracefully.
- Log AI communication.

## Phase 10 Status (as of 2026-08-31)

Phase 10's five rules above are satisfied by the Module 1/2/3/4 client and orchestration code already built during Phases 5-6 (`backend/ai_services/module1_client.py`, `module2_client.py`, `fusion_client.py`, `backend/weather/services.py`, `backend/predictions/views.py`): every client implements the exact REST_API_SPEC.md request/response contract, passes AI output through unmodified, raises a typed error on failure that the view maps to the documented HTTP status (500/503) with a generic message, and logs every call outcome (IDs and exception text only, never request/response payload contents). Verified via `manage.py check`, `makemigrations --check --dry-run`, the `ai_services`/`predictions`/`module2`/`weather` test suites (143 tests, mock mode + real-mode HTTP mocked success/connection-failure/HTTP-error/malformed-response/non-JSON-response), and a full-suite regression run (248 tests, all passing).

**Real AI-service deployment is deferred until the AI team delivers a trained model/service package** per AI_MODULE_DELIVERY_SPECIFICATION.md — no such package exists in this repository or environment as of this date (`ENABLE_MOCK_AI` remains `True`; `AI_SERVICE_BASE_URL` remains an unconfirmed placeholder). No new AI microservice was built and no AI JSON contract, endpoint name, or client request/response shape was changed. Admin AI-monitoring/system-health APIs (REST_API_SPEC.md's Admin APIs section) are not assigned to this phase by this roadmap and remain unimplemented pending a scoping decision.

Phase 10 is considered complete under its current roadmap definition.

---

# Phase 11 — Testing & Quality Assurance

## Backend

- API Testing
- Database Testing
- Authentication Testing

## Frontend

- UI Testing
- Responsive Testing
- Navigation Testing

## Integration

- Backend ↔ AI
- Backend ↔ Frontend
- End-to-End Prediction Workflow

Fix all identified issues before deployment.

## Phase 11 Status Update (2026-09-01)

A non-AI production-readiness audit found three real gaps under this
phase's own "Responsive Testing"/"Navigation Testing" and general error-
handling line items, all fixed:

**No 404/error boundary pages** — unmatched routes and runtime errors fell
through to Next.js's default (unstyled, off-brand) pages. Added
`frontend/app/not-found.tsx` (styled 404), `app/error.tsx` (route-level
error boundary with a "Try Again" reset button, never shows the raw error
message to the user), and `app/global-error.tsx` (catches a crash in the
root layout itself — necessarily plain-inline-styled since it replaces the
layout that would normally supply Tailwind/theme tokens).

**No mobile navigation at all** — `AppNavbar`'s nav links were
`hidden ... sm:flex` with no mobile alternative, so on any screen narrower
than the `sm` breakpoint the persistent nav was simply invisible with no
hamburger/drawer fallback — a real violation of CLAUDE.md's explicit Mobile
support requirement. Added `components/ui/sheet.tsx` (a new reusable slide-
in drawer primitive, built on the `@base-ui/react` Dialog part already used
by `components/ui/button.tsx` — no new dependency) and wired it into
`AppNavbar` as a hamburger-triggered mobile menu; the breakpoint for the
persistent desktop nav was also raised from `sm` to `lg` since two more nav
links (below) made `sm` too narrow to fit them without wrapping.

**Two real routes missing from persistent nav** — `/history` and `/weather`
both exist and are fully built but were reachable only via Dashboard quick-
action cards, not the navbar, on either desktop or (now) mobile. Added both
to `AppNavbar`'s shared `NAV_LINKS` list, used by both the desktop nav and
the new mobile drawer.

Verified via `tsc --noEmit` (clean), ESLint (clean), and `next build`
(clean, `/_not-found` now present in the route list as expected for a
custom 404 page).

---

# Phase 12 — Performance Optimization

## Backend

- Optimize Database Queries
- Add Indexes
- Improve API Response Time

## Frontend

- Lazy Loading
- Image Optimization
- Component Optimization
- Loading States

---

# Phase 13 — Security

## Implement

- JWT Security
- CSRF Protection
- Input Validation
- File Validation
- Rate Limiting
- Secure File Uploads
- Environment Variable Protection

## Phase 13 Status Update (2026-09-01)

Two real gaps found during a non-AI production-readiness audit, both fixed:

**Secure File Uploads (avatar upload was weaker than prediction upload)** —
`users/serializers.py`'s `ProfileUpdateSerializer.profile_image` had zero
validation (any file extension/content-type/size would be accepted as an
avatar), while `predictions/validators.py` already enforced extension +
MIME-type + size limits for plant-image uploads. Added a
`validate_profile_image` method reusing (not duplicating)
`validate_image_format`/`validate_image_content_type`/`validate_image_size`
from `predictions/validators.py`. The 224×224 minimum-resolution check was
deliberately *not* reused — that's a plant-analysis quality rule, not a
security control, and no doc specifies a minimum avatar resolution.

**Environment Variable Protection (no fail-fast check existed)** — a
deployment with `DEBUG=False` but an unedited `SECRET_KEY`/
`DATABASE_PASSWORD` (still the placeholder from `.env.example`, or unset)
would previously start up "successfully" with an insecure secret or an
empty DB password. `config/settings.py` now raises `ImproperlyConfigured`
at startup when `DEBUG=False` and `SECRET_KEY`/`DATABASE_PASSWORD` are
unset or match a known placeholder value — skipped automatically under
`manage.py test` so the test runner never needs a production-shaped `.env`.
Verified both the failure and success paths manually.

Also added `CSRF_TRUSTED_ORIGINS` (env-driven, defaults to
`CORS_ALLOWED_ORIGINS`) — the JWT-authenticated REST API itself is
CSRF-exempt by construction, but the Django admin at `/admin/` uses session
authentication and would fail CSRF verification in production once served
from a real domain rather than `localhost` without this.

---

# Phase 14 — Deployment Preparation

## Backend

- Production Settings
- Environment Variables
- Logging
- Error Handling

## Frontend

- Production Build
- Environment Configuration

## Database

- Migration Verification
- Backup Strategy

## Phase 14 Status Update (2026-09-01)

A pre-AI-integration production-readiness pass closed most of this phase's
previously-unbuilt items:

**Production settings audit** — `backend/config/settings.py` was reviewed
against Django's deployment checklist. Running
`python manage.py check --deploy` with production-like environment
variables (`DEBUG=False`, a real `SECRET_KEY`, a real `ALLOWED_HOSTS`)
reports **zero issues** — the SSL redirect / secure-cookie / HSTS block
added during the Phase 13 security-hardening session already satisfies
Django's own deployment checks. No settings changes were needed.

**Docker** — added `backend/Dockerfile` (gunicorn, non-baked config via env
vars), `frontend/Dockerfile` (multi-stage, Next.js `output: "standalone"`
added to `next.config.ts` for a lean runtime image), `.dockerignore` for
both, and a root `docker-compose.yml` wiring Postgres + backend + frontend
together for local/self-hosted use. Migrations are a separate manual step
(`docker compose exec backend python manage.py migrate`), deliberately not
run automatically on container start. No secrets are baked into any image;
the root `.env.example` documents the small set of compose-level variables
(Postgres credentials, the frontend's build-time API URL) separately from
`backend/.env.example`.

**CI** — added `.github/workflows/ci.yml`: a `backend` job (Postgres
service container, `manage.py check`, `makemigrations --check --dry-run`,
`manage.py test --noinput`, running against the existing mock-mode AI
fixtures since no real AI service exists to call) and a `frontend` job
(`tsc --noEmit`, ESLint, `next build`). No paid/external services used.

**Not done, and why:** the automatic-daily/weekly-backup and
disaster-recovery items under "Backup Strategy" remain an operational/
hosting-provider decision with no code artifact expected in this repo
(same conclusion as the 2026-08-31 audit) — a managed Postgres host's
built-in backup feature, or a `pg_dump` cron job on whatever server this is
eventually deployed to, is an infrastructure choice made at deploy time, not
something to hardcode here.

## Phase 14 Status Update (2026-09-01, continued)

A further production-readiness pass found and closed three infra gaps:

**Health/readiness endpoint** — neither `docker-compose.yml`'s `backend`
service nor `frontend` service had a healthcheck (only `db` did), so
`depends_on: condition: service_healthy` couldn't be used for either app
container. Added `GET /health/` (`backend/config/views.py`) — unauthenticated,
outside `/api/v1/`, checks real database connectivity via
`connection.ensure_connection()` — deliberately separate from the existing
authenticated, business-facing `GET /api/v1/admin/system-health/`. Wired
into `docker-compose.yml` as the `backend` service's healthcheck, with
`frontend` now depending on `backend: condition: service_healthy` (was an
unconditional `depends_on` before) and its own healthcheck against `/`.

**Containers ran as root** — neither Dockerfile had a `USER` directive.
Added a non-root `app` user in `backend/Dockerfile` (created via
`adduser`/`addgroup`, `/app` chowned before the switch) and adopted the
`node:22-slim` base image's built-in non-root `node` user in
`frontend/Dockerfile`.

**CI didn't run Django's deployment checks** — `.github/workflows/ci.yml`'s
backend job checked `manage.py check` (dev-mode) but never
`check --deploy` (production-mode). Added a dedicated step that overrides
`DEBUG=False` for just that one step (via GitHub Actions' per-step `env:`),
so the rest of the job keeps running against the existing dev-mode config;
existing CI secrets (`SECRET_KEY`/`DATABASE_PASSWORD`) already aren't
placeholder values, so this also exercises the new Phase 13 fail-fast
checks on every CI run without needing new secrets.

---

# Phase 15 — Final Review

Before considering the project complete, verify:

- All APIs follow REST_API_SPEC.md.
- Database matches DATABASE_SPECIFICATION.md.
- UI matches UI_SPECIFICATION.md.
- AI integration follows AI_MODULE_DELIVERY_SPECIFICATION.md.
- All modules are tested.
- No critical bugs remain.
- Documentation is updated.

---

# Phase 16 — Admin Dashboard

The Admin Dashboard was not assigned to any of the original 15 phases (see the
2026-08-31 gap audit note) even though GREEN_GUARD_SYSTEM_SPECIFICATION_V2.md
section 8/9.11/24.11/27.14 and REST_API_SPEC.md section 8 both fully specify
it. It does not depend on the AI team's trained models, so it was implemented
as Phase 16 rather than left unbuilt.

## Backend — `backend/adminpanel/`

New Django app, isolated from every existing app (reuses the `User`,
`Prediction`, and `Farm` models directly; introduces zero new models/tables/
migrations). Endpoints, exactly per REST_API_SPEC.md section 8:

- `GET /api/v1/admin/dashboard/` — total/active users, total predictions, system status
- `GET /api/v1/admin/users/` — search, status filter, sort, pagination
- `GET /api/v1/admin/users/{user_id}/` — profile + prediction count + registration date + status
- `PUT /api/v1/admin/users/{user_id}/status/` — activate/deactivate
- `DELETE /api/v1/admin/users/{user_id}/` — delete user (cascades to owned farms/predictions)
- `GET /api/v1/admin/predictions/` — search, status filter, sort, pagination
- `DELETE /api/v1/admin/predictions/{prediction_id}/` — delete any prediction
- `GET /api/v1/admin/ai-monitoring/` — Module 1/2/3/4 status (read-only)
- `GET /api/v1/admin/system-health/` — backend/database/ai_services/weather_api status
- `GET /api/v1/admin/statistics/` — platform-wide aggregates

Authorization: `adminpanel.permissions.IsAdminRole`, checked against the
application's own `User.role` field (not Django's `is_staff`/superuser
flags), paired with `IsAuthenticated` on every view — unauthenticated
requests get 401, authenticated non-Admin requests get 403, per section 8's
"Admin Rules". Two safety guards beyond the documented contract: an admin
cannot delete or deactivate their own account through these endpoints
(400, prevents an accidental Admin lockout).

AI monitoring / system health honesty rule (CLAUDE.md's AI Contract):
`adminpanel/services.py` never fabricates model accuracy, confidence,
uptime, or inference counts. When `ENABLE_MOCK_AI=True` (the current
default), Modules 1/2/4 report `"Mock Mode"` verbatim rather than pretending
to be online; when it is `False`, they report a bare network-reachability
probe of `AI_SERVICE_BASE_URL` (`"Healthy"`/`"Unreachable"`) with no
inference call. **Update (2026-09-02, Phase 5 real Module 3 delivery):**
Module 3 (weather) now shares the same `ENABLE_MOCK_AI` gate — reporting
`"Mock Mode"` when it's on, otherwise probed independently via the real
module's own `GET /health` (`"Connected"`/`"Unreachable"`) — since the
delivered `ai/Weather_Module` is mockable like the other three modules,
unlike the old always-on NASA POWER call this replaced. `most_recommended_crop` in Platform
Statistics always returns `null`: Module 2 records a soil-health check for a
crop the farmer already selected, it does not recommend one, so there is no
backing data source — same precedent already established for
`recommended_crop` in `history.serializers.HistoryListItemSerializer`.

`ENABLE_MOCK_AI`, `AI_SERVICE_BASE_URL`, and the Module 1/2/4 client
contracts were not touched.

## Frontend

New `frontend/features/admin/` module (types/api/hooks, Django-field-name to
camelCase mapping matching every other feature module's convention) plus:

- `/admin` — dashboard overview, AI monitoring panel, system health panel, platform statistics
- `/admin/users` — searchable/filterable/paginated user table, activate/deactivate, delete
- `/admin/users/[userId]` — user detail, activate/deactivate, delete
- `/admin/predictions` — searchable/filterable/paginated prediction table, delete

`components/layout/admin-route.tsx` blocks non-Admin accounts with an
access-denied state (the real security boundary is the backend's
`IsAdminRole`, checked independently on every request). Two new reusable UI
primitives were added since the project had none yet: `components/ui/badge.tsx`
and `components/ui/table.tsx`. The navbar shows an "Admin" link only when
`user.role === "Admin"`. Every list/detail view has its own loading
(Skeleton), empty, and error (Alert) state, matching the Farms/History pages'
established pattern; destructive actions (delete) require an inline confirm
step, matching the same pages.

## Tests

`backend/adminpanel/tests.py` — 49 tests: authentication (401) and
authorization (403) on every endpoint, correct aggregation against real
empty/populated data, search/status-filter/sort/pagination on both list
endpoints, the two self-action safety guards, 404 handling for missing and
malformed IDs, 422 handling for invalid input, and explicit assertions that
no response body ever contains a password/secret/token/confidence/accuracy/
uptime/latency value. No frontend test framework exists in this repository
(`package.json` has no Jest/Vitest/RTL/Playwright, consistent with the
Phase 11 finding) — `tsc --noEmit` / ESLint / `next build` remained the
verification method, matching every prior phase.

## Verification

`manage.py check` clean; `makemigrations --check --dry-run` reported "No
changes detected" (zero schema changes); `adminpanel` app: 49/49 tests
passing in isolation; full backend suite: 300/300 tests passing (up from
251 before this phase), zero regressions in any pre-existing app; `tsc
--noEmit` clean; ESLint clean; `next build` clean (22 routes, including the
new `/admin`, `/admin/users`, `/admin/users/[userId]`, `/admin/predictions`
alongside all pre-existing routes).

## AI-Dependent Work Remaining (unchanged by this phase)

Real trained Module 1 (image analysis), Module 2 (soil/nutrient), and
Module 4 (ANN fusion) services are still pending delivery from the AI team,
per Phase 10's status note. The Admin Dashboard is fully functional without
them — AI Monitoring correctly reports Mock Mode today and will correctly
report live reachability the moment `ENABLE_MOCK_AI` is set to `False` and
`AI_SERVICE_BASE_URL` points at a real service, with no code changes
required.

Phase 16 is considered complete under this scope.

---

# Architecture Change — Module 4 Integrated Analysis Report (2026-10-03)

The project owner finalized GreenGuard's architecture as **three independent AI modules** — Module 1 Disease Detection (live service), Module 2 Soil & Nutrient Health (live service), Module 3 Weather Risk (local service, Open-Meteo) — plus **Module 4, the Integrated Analysis Report**, an application-level layer that displays their results together. There is no ANN Fusion model, no Fusion service and no combined final diagnosis. Phase records above that mention ANN Fusion describe the architecture at the time and are kept as history.

Implemented:

- `POST /api/v1/predictions/analyze/` (Quick Scan) calls the live Module 1 (`ai_services/disease_module_client.py`, optional `crop`), attaches the farm's latest Module 2 result, calls Module 3, and stores `prediction_report = {module1, module2, module3}` verbatim. The response returns the saved record.
- `predictions` migration `0003` makes the legacy Fusion columns `final_diagnosis`, `confidence_score` and `recommendation_summary` nullable; new analyses leave them NULL. Existing rows are untouched.
- History, Admin predictions/statistics and the Dashboard read `diagnosis`/`confidence` from Module 1's own `prediction` (null when uncertain). Dashboard overview counts and recent analyses are now real.
- Admin AI Monitoring probes the real Module 1/2/3 `/health` endpoints; `fusion_module` reports "Not used — integration layer".
- Frontend report shows three labelled module sections (reusing the Disease Check, Soil Test and Weather components); the Fusion confidence/recommendation cards were removed and the nested Module 3 mapping bug fixed.
- `ai_services/module1_client.py`, `ai_services/fusion_client.py` and the `AI_SERVICE_BASE_URL`/`AI_REQUEST_TIMEOUT_SECONDS` settings became obsolete with this change. **Removed 2026-10-17** (pre-commit cleanup, owner-approved) together with their tests in `ai_services/tests.py`. The temporary `POST /api/v1/predictions/debug-upload-test/` endpoint (`predictions/debug_views.py`) was removed at the same time.

---

# Approval Process

After completing each phase:

1. Stop implementation.
2. Summarize completed work.
3. Explain files created or modified.
4. Wait for user approval before starting the next phase.

Claude Code must never automatically continue to another phase without approval.

---

# Final Goal

The objective is to deliver a production-ready GreenGuard application that is:

- Modular
- Maintainable
- Scalable
- Secure
- Responsive
- Well-documented
- Fully aligned with all project specifications