# Model Documentation — Module 3: Weather Risk Engine

**Version:** 1.12.0
**Type:** Rule-based system (core), with an additive LSTM forecast (v1.6.0+)

## Why rule-based, not ML?

Per `greenguard-final-architecture-v3.md`, Module 3 is intentionally a rule engine, not a trained model. Weather-to-risk relationships (e.g. "high humidity + warm temperature → fungal risk") are well-established agronomic rules, not something that needs to be learned from a dataset. No training data was required for this module.

## Data source

**Open-Meteo API** (switched from NASA POWER in v1.1.0 — see below)
- Endpoint: `https://api.open-meteo.com/v1/forecast`
- Free, no API key required
- Parameters used: `temperature_2m`, `relative_humidity_2m`, `wind_speed_10m` (current conditions, updated hourly) + `precipitation_sum` (daily, last 7 completed days)
- Docs: https://open-meteo.com/en/docs

### Why we switched away from NASA POWER

NASA POWER is a climate-research archive, not a live weather feed — its most recent 2-10 days are often unprocessed placeholders (`-999`), so it can never return genuinely "today's" weather, only recent history at best. A farmer checking current risk needs live conditions, so we moved to Open-Meteo, which updates hourly and has no such lag.

## Risk logic

**Fungal disease risk** — considers both today's snapshot AND the last 3 days' trend:
- **High** if today is very humid (≥85%) in a moderate temperature range (15-30°C), OR the last 3 full days in a row were all "conducive" (15-30°C avg temp AND ≥80% avg humidity)
- **Moderate** if today's humidity ≥65%, OR at least 1 of the last 3 days was conducive
- **Low** otherwise

The consecutive-day check exists because most leaf-fungal pathogens need *sustained* humid conditions over multiple days to establish, not a single humid moment. This is computed internally from hourly data and does NOT appear as a new field in the API response — it only influences which risk label gets returned, so the JSON contract in REST_API_SPEC.md is unaffected.

**Heat stress risk** — now also considers a 3-day hot streak, since cumulative heat exposure damages crops more than one hot day:
| Condition | Risk |
|---|---|
| temp > 40°C, OR 3 consecutive days averaging > 35°C | High |
| temp > 35°C, OR 1+ consecutive hot day | Moderate |
| otherwise | Low |

**Drought risk** — now also considers consecutive dry days (a 7-day rainfall sum alone can hide "one shower, then bone dry"):
| Condition | Risk |
|---|---|
| rainfall_7d < 10mm, OR 5+ consecutive dry days (<1mm) | High |
| rainfall_7d < 25mm, OR 3+ consecutive dry days | Moderate |
| otherwise | Low |

**Known bug (found while adding `*_reason` in v1.7.0, not yet fixed):** the "5+ consecutive dry days" clause above is dead code. `_consecutive_days()`'s `lookback_days` defaults to 3, so `consecutive_dry_days` can never exceed 3 — the High-risk drought decision is really driven only by `rainfall_7d < 10mm`. Harmless today (the clause never fires, so it can't produce a wrong label), but it means the "sustained dry streak" story for High drought risk isn't actually implemented, only for Moderate. Fix requires a call on intent (raise `lookback_days` for this call, or drop the clause) — flagged for the AI team, not changed here.

**Status: IMPROVED DEFAULTS, still not biotech-validated for a specific crop/region.** These replace the original crude architecture-doc placeholders with values grounded in general plant-pathology/agronomy knowledge. Update the constants in `assess_risk()` (and the day-classifier functions `_is_fungal_conducive()`, `_is_hot_day()`, `_is_dry_day()`) in `weather_service.py` once real thresholds are confirmed — no other file needs to change.

## LSTM forecast add-on (v1.6.0)

**Status: additive only.** Everything above this section (the rule engine, its thresholds, `weather`, `risk_assessment`) is completely unmodified by this add-on. If the LSTM model or scaler file is missing, corrupted, or throws for any reason, `main.py` catches it and returns `forecast: null, predicted_risk_assessment: null` — the rest of the response is unaffected. This is a forward-looking supplement to the rule engine, not a replacement for it.

**What it predicts:** tomorrow's `[avg_temp, avg_humidity, rainfall]`, from the same 7-day daily summary (`api/weather_service.py`'s `_build_daily_summary()`) already computed for the rule engine's consecutive-day logic. `predicted_risk_assessment` is then produced by calling the existing, unmodified `assess_risk()` on that forecasted day, rolled into the same trailing 7-day window used for today's risk — so the forecasted risk uses exactly the same rules as current risk, just one day further ahead.

**Architecture:** a single-layer LSTM (hidden size 32) followed by a linear head, `api/lstm_model.py`. ~4.6k trainable parameters. Framework: PyTorch (`torch==2.14.0`, CPU-only build).

**Training data:** self-supervised — no manually labeled risk outcomes are used or required. `training/train_lstm.py` pulls ~2 years of daily `[temperature_2m_mean, relative_humidity_2m_mean, precipitation_sum]` from Open-Meteo's free historical archive API (`archive-api.open-meteo.com`, no key needed) across 14 Pakistani coordinates, weighted toward the Punjab agricultural belt (Lahore, Multan, Faisalabad, Okara, Sahiwal, Jhelum, Kasur, Sheikhupura, Gujranwala, Sargodha, Bahawalpur), plus Peshawar, Islamabad, and Hyderabad for broader climate diversity. Each location's ~731-day series is split **chronologically** (not shuffled) into the first 80% for training and the last 20% held out entirely for evaluation, so no test-set day is ever trained on. 8,078 training windows, 2,058 held-out test windows in the current model.

**Evaluation (v1.9.0):** scored on the 2,058 held-out windows against two baselines, since "the model has low error" is meaningless without something to compare it to:

| Feature | Model | MAE | RMSE |
|---|---|---|---|
| Temperature (°C) | **LSTM** | 1.40 | 1.77 |
| | persistence (tomorrow = today) | 1.24 | 1.62 |
| | climatology (tomorrow = the average) | 8.01 | 8.59 |
| Humidity (%) | **LSTM** | 5.25 | 7.09 |
| | persistence | 5.34 | 7.24 |
| | climatology | 14.75 | 17.57 |
| Rainfall (mm) | **LSTM** | 2.31 | 6.25 |
| | persistence | 2.64 | 7.84 |
| | climatology | 2.53 | 6.77 |

Full precision saved to `models/eval_report.json` on every training run.

Honest read: same pattern as before the coordinate expansion — the LSTM crushes climatology on every feature, **beats persistence on humidity and rainfall**, but still **loses to persistence on temperature** (1.40°C MAE vs. 1.24°C). Adding 8 more locations didn't flip that result, which is expected: more geographic coverage improves how well the model generalizes across locations, it doesn't by itself fix a feature where persistence is just a strong signal. Reported here rather than only quoting training loss, since training loss alone would have hidden this.

**Known limitations:**
- Predicts a single day ahead only — no multi-day forecast horizon.
- Trained on 14 Pakistani coordinates, concentrated in the Punjab agricultural belt with a few outliers for diversity (KP, federal capital, Sindh). Still weak coverage for **northern mountains** (Gilgit-Baltistan, Chitral, Hunza, Skardu, Murree — alpine/sub-zero climate, nothing like the training data), the **Arabian Sea coast** (Karachi, Gwadar — maritime humidity patterns), and **Balochistan's interior** (arid highland, different rainfall regime). Predictions for farms in those zones are extrapolation, not interpolation, and should be trusted less. Add coordinates from those zones to `TRAIN_COORDINATES` and retrain to improve coverage further.
- Does not currently beat the persistence baseline on temperature (see Evaluation above) — the model adds real value on humidity and rainfall, but for temperature specifically "predict tomorrow = today" is presently at least as good.
- `predicted_risk_assessment` inherits every caveat of the underlying rule thresholds (see above), plus whatever error the forecast itself carries — it is two layers of approximation stacked, not a second opinion independent of the first.
- Retraining (`python training/train_lstm.py`) overwrites `models/weather_lstm.pt`, `models/scaler.json`, and `models/eval_report.json` with no versioning of prior weights — copy them out first if you want to keep a previous run.

## Reliability features

| Feature | What it does | Why |
|---|---|---|
| **Caching (15 min)** | Repeated requests for the same location (rounded to ~1km) reuse the previous weather data instead of calling the live API again | Reduces load on the free weather API and speeds up repeated checks |
| **Retry with backoff** | Network errors or 5xx server errors are automatically retried up to 3 times (0.5s, 1s, 2s delays) | A single network hiccup shouldn't fail the whole prediction |
| **Rate-limit handling** | If the weather provider returns 429, we respect their `Retry-After` header, and return a clear error if still rate-limited after retries | Graceful degradation instead of silent failure |
| **Input validation** | Sanity-checks provider values (temperature -60 to 60°C, humidity 0-100%, wind speed 0-150 m/s) and confirms hourly data arrays are well-formed before using them | Protects against silently passing through corrupted/implausible data |

The in-memory cache is fine for this single-process demo/FYP deployment. If this ever runs as multiple server instances in production, it should be swapped for a shared cache like Redis — noted directly in the code as a comment.

Earlier versions (v1.3.0) also had request de-duplication, stale-data fallback, and a fail-fast cooldown. These were removed in v1.4.0 as unnecessary complexity for this project's actual scale — see Versioning below.

## Remaining known limitations (documented, not blocking)

- **Multi-process/multi-instance deployment**: the cache is in-memory per process — won't be shared if this module is ever scaled to multiple server instances (would need Redis).
- **No usage/rate monitoring**: we react to a 429 when it happens, but don't proactively track how close we are to Open-Meteo's free-tier limit.
- **Worst-case latency**: with retries, a slow/dying provider can still make one request take up to ~30-45 seconds before failing.
- **Timezone edge cases near midnight**: "today" is decided by the farm's local time (`timezone=auto`) — behavior right at a midnight boundary hasn't been explicitly tested.
- **Grid-point resolution**: weather reflects the nearest Open-Meteo forecast model grid point to the given coordinates (roughly a few km resolution) and a forecast model's current conditions, not a physical sensor/ground station at the exact farm — small local variation is possible.
- **No fallback on provider failure**: if Open-Meteo's API is down or slow, the endpoint fails with HTTP 500 rather than falling back to cached/estimated data (as of v1.4.0 — see Versioning below).

## Versioning

v1.0.0 — Initial rule-based implementation, live NASA POWER integration, matches REST_API_SPEC.md contract.
v1.0.1 — Fixed NASA POWER data lag issue (`-999` placeholder values on recent days).
v1.1.0 — Switched data source from NASA POWER to Open-Meteo for genuinely real-time current conditions instead of lagged historical data.
v1.2.0 — Improved risk thresholds to be more agronomically realistic (still placeholders, not yet biotech-validated). Added consecutive-day fungal risk analysis using hourly historical data. Added response caching (15 min), automatic retry with backoff, and rate-limit (429) handling.
v1.3.0 — Extended consecutive-day analysis to heat stress and drought risk (previously fungal-only). Added input validation (sanity-checks on provider values, hourly array integrity). Added stale-data fallback, request de-duplication (thundering-herd protection), fail-fast cooldown after failures, and automatic cache pruning.
v1.4.0 — Removed request de-duplication (per-key locking), stale-data fallback, fail-fast cooldown, and automatic cache pruning. These were solving multi-instance/high-traffic problems this single-process FYP deployment doesn't have, and the stale-fallback flag was being discarded unused by main.py. Simplified back to a plain TTL cache; on a live-fetch failure the endpoint now always returns HTTP 500, matching REST_API_SPEC.md and the README.
v1.5.0 — Added a `units` object to the `/predict` response (sibling of `weather`), giving fixed unit labels for each `weather` field (`celsius`, `percent`, `mm`, `m/s`) so the response is self-describing instead of relying on Backend to hardcode units from documentation alone. Purely additive — no existing field was renamed, removed, or changed in type.
v1.6.0 — Added an LSTM forecast add-on: `forecast` (next-day weather) and `predicted_risk_assessment` (existing rule engine run on the forecasted day), both nullable and both additive — see "LSTM forecast add-on" above. Added `torch` as a new dependency and a new `training/train_lstm.py` offline training script. Nothing in the rule engine or its existing fields changed.
v1.7.0 — Added `fungal_disease_reason`, `heat_stress_reason`, `drought_reason` to `RiskAssessment` — a plain-English sentence naming the specific threshold/value that produced each `*_risk` label, generated inside `assess_risk()` itself so `risk_assessment` and `predicted_risk_assessment` both get it automatically with zero duplicated logic. Purely additive — no existing field renamed or removed. Discovered and documented (not fixed) a pre-existing dead-code bug in the drought "5+ consecutive dry days" clause — see "Known bug" above.
v1.8.0 — `training/train_lstm.py` now does a proper chronological train/test split per location (last 20% of days held out) and reports real held-out MAE/RMSE against persistence and climatology baselines, instead of only training-set loss. No API/contract change — this only affects how the LSTM in `models/` is trained and evaluated. See "Evaluation" above for the actual numbers, including where the model currently loses to the persistence baseline (temperature).
v1.9.0 — Expanded `TRAIN_COORDINATES` from 6 to 14, adding 8 Punjab agricultural districts (Okara, Sahiwal, Jhelum, Kasur, Sheikhupura, Gujranwala, Sargodha, Bahawalpur) for better coverage of GreenGuard's likely farm base. Retrained: 8,078 training windows / 2,058 held-out test windows (up from 3,462 / 882). Held-out evaluation result unchanged in character -- still beats persistence on humidity/rainfall, still loses on temperature -- but now backed by ~4x more evaluation data. No API/contract change.
v1.10.0 — **Bug fix, found during final pre-delivery review:** the 500 error body did not actually match its own documented `{"message": "..."}` contract for the single most likely failure case. `main.py` raised an `HTTPException` when Open-Meteo was unreachable; FastAPI's *built-in* `HTTPException` handler takes priority over the app's custom `generic_error_handler` (registered for the base `Exception` class) and formats every `HTTPException` as `{"detail": "..."}` regardless. So "Open-Meteo unreachable" -- the documented, expected 500 scenario -- actually returned `{"detail": "Prediction Failed: weather service unavailable."}`, while only a genuinely unexpected, undocumented bug elsewhere would hit `generic_error_handler` and return the documented `{"message": "Prediction Failed"}`. A Backend client parsing `response.json()["message"]` on 500 would `KeyError` on the common case and only work on the rare one. Fixed by adding an explicit `@app.exception_handler(HTTPException)` that reformats to `{"message": exc.detail}`, unifying both paths under the one documented shape (422 validation errors are a different exception type, `RequestValidationError`, and are unaffected -- still FastAPI's default `{"detail": [...]}`). This restores the contract that was always documented; it does not change it, so no new PM sign-off is needed the way the v1.5.0/v1.6.0/v1.7.0 additions did -- but tell Backend directly if they'd already started coding against the old (wrong) `{"detail": ...}` shape for this path.
v1.11.0 — **Bug fix, found while double-checking "are we really ready to deliver":** `pip install -r requirements.txt` failed outright from a clean environment. `torch==2.14.0` is not published on the default PyPI index for this platform (confirmed: only up to 2.13.0 is, on Windows/Python 3.13) -- so both the README's plain install instructions and the Dockerfile's `RUN pip install -r requirements.txt` would have failed before ever reaching the app. Verified by building a genuinely fresh venv from scratch (nothing pre-installed) and running the real install command -- it failed with `ERROR: No matching distribution found for torch==2.14.0` before the fix, then succeeded and the service ran correctly afterward. Fixed by adding `--extra-index-url https://download.pytorch.org/whl/cpu` as the first line of `requirements.txt` (a directive pip honors when reading the file), which is also the correct index for a small CPU-only build rather than a much larger CUDA-enabled one. No code or contract change -- packaging only.
v1.12.0 — Requested review of the Dockerfile specifically (it remains the one thing in this package never run through an actual `docker build`, since Docker isn't available in this environment -- see the caveat still open below). Found and fixed a real gap on inspection: the `CMD` hardcoded `--port 8001`, silently ignoring the `PORT` env var that `python main.py` (and `.env.example`) document as configurable -- `docker run -e PORT=9000 ...` would do nothing. Fixed with `ENV PORT=8001` plus an exec-form `CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]` (needs exactly one shell layer to expand `${PORT}`; a bare JSON-array CMD can't do env substitution at all, and an unbracketed shell-form CMD gets double-wrapped by Docker into two redundant shell layers -- both traps this avoids). Also added `.dockerignore` to keep the build context to just what's actually needed. `docker build` itself is still unverified -- flagged, not hidden.
