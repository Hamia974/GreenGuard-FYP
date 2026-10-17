# Module 3 (Weather) — AI Delivery Status

**Status as of 2026-09-02: INTEGRATED.** The AI team redelivered Module 3 as
a real, runnable package at `ai/Weather_Module/` (superseding the earlier
`ai/weather.zip`, which contained only a video file — see "Prior delivery"
below), and it is now fully wired into the Django backend and the Weather
page.

## What was delivered

`ai/Weather_Module/Weather_Module/` — a runnable FastAPI microservice:

- `api/main.py`, `api/weather_service.py`, `api/schemas.py` — the REST API,
  Open-Meteo fetch + rule-based risk engine, and exact JSON contract.
- `api/lstm_model.py`, `api/lstm_forecast.py`, `models/weather_lstm.pt`,
  `models/scaler.json`, `models/eval_report.json` — an additive, nullable
  next-day forecast (LSTM) layered on top of the rule engine.
- `docs/INTEGRATION_GUIDE.md`, `docs/MODEL_DOCUMENTATION.md` — the module's
  own contract documentation and evaluation numbers.
- `tests/test_api.py`, `samples/`, `requirements.txt`, `Dockerfile`,
  `.env.example` — verified runnable: a fresh `venv` + `pip install -r
  requirements.txt` succeeds, and `pytest tests/test_api.py -v` passes (23
  passed, as of this integration).

## Integration summary

- Django calls it via `backend/weather/services.py` (`fetch_weather_for_coordinates`),
  configured with `WEATHER_MODULE_URL` (default `http://localhost:8001`).
  See REST_API_SPEC.md Section 9 ("AI Module 3") for the exact contract and
  Section 5A for the new `GET /api/v1/weather/current/` endpoint that
  exposes it to the Weather page.
- `GET /api/v1/dashboard/weather/`'s pre-existing flat contract is
  preserved unchanged — now populated from the same Module 3 call via
  `weather.services.to_dashboard_summary()` (field access only, no
  recalculation) instead of the old NASA POWER-backed service.
- `GET /api/v1/weather/current/` (new) exposes the module's full response —
  `units`, `*_reason` explanations, and the nullable `forecast` /
  `predicted_risk_assessment` — for the Weather page
  (`frontend/app/(app)/weather/`).
- `ENABLE_MOCK_AI` (already used by Modules 1/2/4) now also gates Module 3,
  returning a fixed mock response matching
  `ai/Weather_Module/Weather_Module/samples/sample_response.json` exactly,
  so local development does not require the microservice to be running.

## Prior delivery (superseded)

The AI team had previously placed a file at `ai/weather.zip` (13.1 MB
compressed / 85.2 MB uncompressed) described as the Module 3 delivery.
Inspecting it showed it contained exactly one file, `weather.mp4` (a video),
with no source code, model, or documentation of any kind — it could not be
integrated. Until the redelivery above, the application ran on a stopgap
NASA POWER-backed implementation built in Phase 5
(`backend/weather/services.py`, now replaced). `ai/weather.zip` itself was
left in place, unmodified.

## Known limitations carried over from the module's own documentation

See `ai/Weather_Module/Weather_Module/docs/MODEL_DOCUMENTATION.md` for full
detail. In short: the LSTM forecast predicts one day ahead only, is trained
on 14 Pakistani coordinates concentrated in the Punjab agricultural belt
(weaker for northern mountains, the Arabian Sea coast, and Balochistan's
interior), currently loses to a "tomorrow = today" baseline on temperature
(though it beats it on humidity and rainfall), and the rule thresholds in
`assess_risk()` are documented placeholders pending biotech/agronomy
validation. A pre-existing, documented dead-code condition in the drought
rule (the "5+ consecutive dry days" High-risk clause can never fire, since
`_consecutive_days()`'s lookback is 3) was flagged by the AI team, not fixed
by this integration, per the instruction not to modify the module's risk
logic.
