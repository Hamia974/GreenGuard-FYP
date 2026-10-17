# Module 1 (Disease Detection) — AI Delivery Status

> **Update 2026-10-03 — now also used by Quick Scan.** GreenGuard's
> architecture was finalized as three independent AI modules plus Module 4,
> an application-level Integrated Analysis Report (no ANN Fusion model).
> `POST /api/v1/predictions/analyze/` now calls this same live service
> through `ai_services/disease_module_client.py` and stores its response
> verbatim as the report's `module1` section, including the
> `status: "uncertain"` / `prediction: null` case. The old placeholder
> `ai_services/module1_client.py` and `ai_services/fusion_client.py` (and
> their `AI_SERVICE_BASE_URL` / `AI_REQUEST_TIMEOUT_SECONDS` settings) were
> removed on 2026-10-17. The record below describes the 2026-09-26 state
> and is kept as history.

**Status as of 2026-09-26: INTEGRATED, as a standalone endpoint.** The AI
team delivered Module 1 as a real, live FastAPI service (currently deployed
on Render), documented in `ai/API_CONTRACT.md`. It is wired into the Django
backend and a new Disease Check page, but — unlike Module 2 and Module 3 —
it is **not** wired into the existing `POST /api/v1/predictions/analyze/`
Fusion pipeline. See "Why a standalone endpoint" below.

## What was delivered

A live HTTP service (not a local package in this repo):

- `POST /v1/predict` — disease-only detection for one leaf photo, optionally
  narrowed by a farmer-selected `crop`. Returns `status: "ok"` with a
  `prediction` + `top3` shortlist, or `status: "uncertain"` with
  `prediction: null` and `top3` as a fallback result list, never both a
  fabricated verdict and low confidence hidden from the farmer.
- `GET /v1/classes` — the full 38-class list grouped by crop (not consumed
  by this integration — see `ai_services/disease_module_client.py`'s
  `SUPPORTED_CROPS` comment for why).
- `GET /health` — liveness/model-ready check, no `X-API-Key` required.
- `ai/API_CONTRACT.md` — the service's own contract documentation,
  including a "Divergence from REST_API_SPEC.md" section flagging that its
  shape does not match the older Section 9 "AI Module 1" placeholder
  contract (`disease`/`nutrient_deficiency`/`insect`) that Module 4 Fusion
  still consumes.

## Why a standalone endpoint

`predictions/views.py`'s `PredictionAnalyzeView` and `ai_services/module1_client.py`
were built years earlier against a different, still-undelivered Module 1
contract: a single always-present `{disease, nutrient_deficiency, insect}`
label, fed into Module 4 (ANN Fusion) alongside Module 3's weather report.
The live service that was actually delivered returns something structurally
different — disease-only, `top3`-shaped, and able to abstain
(`status: "uncertain"`) rather than always emitting a confident label.

Reconciling the two would mean either changing Module 4's input contract
(an AI contract change, which CLAUDE.md requires explicit approval for) or
forcing the live service's uncertain/no-nutrient/no-insect shape into a
contract it was never designed to fill. Per CLAUDE.md ("Do not redesign the
architecture without approval," "Never modify AI contracts") this
integration does not touch `module1_client.py`, `PredictionAnalyzeView`, or
Module 4 to make that decision unilaterally.

Instead, the live service is exposed as its own public endpoint,
`POST /api/v1/module1/analyze/` (REST_API_SPEC.md Section 8B) — the same
resolution already applied to Module 2 when *its* AI-team delivery turned
out to be a completely different service than the old placeholder contract
described (see `doc-inconsistencies` memory entry #3 / REST_API_SPEC.md
Section 8A). Module 2 and Module 3 are both unchanged by this work.

## Integration summary

- `backend/ai_services/disease_module_client.py` — the live HTTP client.
  Configured via `DISEASE_MODULE_URL` (default `http://localhost:8003`,
  production value `https://gg-module1.onrender.com`) and
  `DISEASE_MODULE_REQUEST_TIMEOUT_SECONDS` (default 60, per the service's
  own cold-start guidance). Retries once on timeout or HTTP 503 only, never
  on 400/401/413/422. Sends `X-API-Key` (from `GREENGUARD_API_KEY`, never
  logged, never sent to the frontend) on every `/v1/*` call except
  `/health`, which needs none.
- `backend/module1/` (new Django app) — `DiseaseAnalyzeView` at
  `POST /api/v1/module1/analyze/`, `DiseaseCheckRequestSerializer`, and an
  append-only `DiseaseCheck` model (mirrors `module2.Module2Analysis`'s
  pattern: one JSON snapshot per run, no binary image stored).
- `ENABLE_MOCK_AI` (already used by Modules 2/3/4 and the older Module 1
  placeholder) also gates this client, returning a fixed mock response
  matching the live contract's documented "confident" example, so local
  development does not require the live service to be reachable.
- `frontend/features/module1/` + `frontend/app/(app)/module1/` — a
  "Disease Check" page (crop picker, leaf-photo upload, confident/uncertain
  result card per `ai/API_CONTRACT.md`'s rendering rules) calling only
  `POST /api/v1/module1/analyze/`. The frontend never calls the live
  service directly and never receives `GREENGUARD_API_KEY`.

## Known limitations, per the service's own documentation

See `ai/API_CONTRACT.md` in full. In short: covers 7 crops only (wheat,
rice, cotton, maize, sugarcane, tomato, potato); confidence is a raw model
probability when no crop is sent, but a *within-crop renormalized share*
when one is — comparable only against other same-branch responses, never
averaged or recalculated here; `top3` accuracy varies sharply by crop
(potato's 3-class list is not worth showing standalone; rice's top-3 barely
beats chance); the crop-mismatch check (`CROP_MISMATCH`) is deliberately
disabled (`crop_mismatch_threshold` set above any attainable probability)
because it rejected more good farmer-supplied crops than real mistakes; and
the free-tier Render deployment can take 30s+ to wake from a cold start,
which is why the request timeout is generous and the frontend shows a
"may take up to a minute" note while waiting.
