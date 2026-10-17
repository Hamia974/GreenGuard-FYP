# GreenGuard — Module 2: Soil & Nutrient Orchestrator
### Engineering Spec

**This is the ONLY externally accessible endpoint for soil/nutrient analysis.** Module 2A (ML nutrient risk classifier) and Module 2B (pH/moisture/light rule engine) are internal services, called only by Module 2. Nothing outside this module ever calls 2A or 2B directly — not the frontend, not other modules.

```
Frontend submits soil-test form
        ↓
   [Module 2 — orchestrator, public API]
        ↓                    ↓
   Module 2A            Module 2B
   (ML, internal)        (rules, internal)
        ↓                    ↓
        └──────── combine ───┘
                   ↓
   Module 2 computes overall_soil_health_score
                   ↓
   Return: { module2a output, module2b output, overall_score, recommendation_notes }
```

---

## 1. What Module 2 does

1. Receives the full farmer submission (everything from the Module 2A form + the 3 Module 2B fields) in a single API call.
2. Internally calls Module 2A with its subset of fields → gets 6 nutrient risk levels + confidence.
3. Internally calls Module 2B with its subset of fields (crop, ph_value, soil_moisture_pct, light_intensity_lux) → gets pH/moisture/light comparison + lockout note.
4. Computes `overall_soil_health_score` from both outputs (formula in Section 3) and builds the farmer-facing `recommendation_notes` from them.
5. Returns everything in one response.

Module 2 does no ML and no rule lookups itself — it's purely an orchestrator + scoring layer. Keep 2A and 2B's own logic untouched; Module 2 just calls them and combines results.

---

## 2. Internal call contracts (for reference — these are NOT the public API)

Module 2 must build these sub-payloads from the single incoming request and call each internal service:

**→ Module 2A internal input:** `crop`, `growth_stage`, `soil_type`, `last_fertilizer_type`, `days_since_fertilizer`, `irrigation_source`, `irrigation_adequacy`, `temperature_c`, `humidity_pct`, `rainfall_mm_last_7_days`, `symptoms.*` (allowed values in `module2_field_options.json`)

**→ Module 2B internal input:** `crop`, `ph_value`, `soil_moisture_pct`, `light_intensity_lux` (rules in `MODEL_DOCUMENTATION.md` → Module 2B rules)

**Crop support (updated 2026-09-10):** all 15 crops are now trained and supported by Module 2A (`module2a-v5`) and covered by Module 2B's reference ranges. `analyze_soil()` still screens every request against `SUPPORTED_CROPS` and against the crops Module 2A was actually trained on, returning the unsupported-crop response in Section 4 for anything outside that set.

Module 2B additionally reports its own `crop_supported` flag. If 2B cannot serve a crop, Module 2 returns the 2A result but withholds the score (`null`) rather than reporting a misleadingly low number — 2B contributes 40 of the 100 points, so a partial score would not be comparable to a full one.

---

## 3. Overall Soil Health Score — formula

**This is a heuristic weighted-scoring formula, not a trained/validated model.** It's transparent and tunable by design — document it as such in your FYP, don't present it as more rigorous than it is.

### Weights (sum to 100)

| Factor | Source | Weight |
|---|---|---|
| Nitrogen risk | Module 2A | 15 |
| Phosphorus risk | Module 2A | 15 |
| Potassium risk | Module 2A | 15 |
| Magnesium risk | Module 2A | 5 |
| Zinc risk | Module 2A | 5 |
| Boron risk | Module 2A | 5 |
| pH status | Module 2B | 20 |
| Soil moisture status | Module 2B | 10 |
| Light status | Module 2B | 10 |
| **Total** | | **100** |

**Why these weights:** N/P/K get 3x the weight of Mg/Zn/B, matching both their agronomic primacy and their higher model confidence (Mg/Zn/B are the weaker predictions — see `MODEL_DOCUMENTATION.md` → Performance summary). pH gets the single highest weight because it drives lockout of everything else (see the pH notes in `MODEL_DOCUMENTATION.md` → Module 2B rules). These are a defensible starting point, not derived from data — say so if asked, and treat as a tunable parameter, not a fixed law.

**Crop-dependent exceptions:** the table above is the default.
- (Added 2026-09-14, per agronomy review GG-M2-AR-01) For the 6 Cucurbitaceae crops (`cucumber`, `bitter_gourd`, `snake_gourd`, `ridge_gourd`, `ash_gourd`, `bottle_gourd` — not `eggplant`, which is Solanaceae), N/P/K drop to 13 each and Zn/B rise to 8 each, total still 100 — see `CUCURBIT_SCORE_WEIGHTS` in `orchestrator_service.py`. This reflects the documented higher zinc/boron sensitivity of this crop family (`Module2A_Engineering_Handoff.md` Section 7a), not a new, ungrounded guess.
- (Added 2026-09-15, per agronomy review GG-M2-AR-02, Numan Niaz — Dogar Agri Farm owner, 10 yrs field experience) For `potato`, N/P drop to 13 each and K rises to 19, total still 100 — see `POTATO_SCORE_WEIGHTS`. Potato is a well-documented heavy potassium feeder; the reviewer's own words: "potassium matters more in potato."

### Per-factor scoring

Each factor contributes a fraction of its weight based on its severity level:

| Severity | Fraction of weight earned |
|---|---|
| `low` (2A) / `ok` (2B) | 1.0 |
| `medium` (2A) / `moderate` (2B) | 0.5 |
| `high` (2A) / `critical` (2B) | 0.0 |

```
score = Σ (factor_weight × severity_fraction)   across all 9 factors
```

### Bucketing

| Score range | Overall label |
|---|---|
| 80 – 100 | Good |
| 50 – 79 | Moderate |
| 0 – 49 | Poor |

### Worked example

Given: nitrogen=high(0), phosphorus=medium(0.5), potassium=low(1.0), magnesium=medium(0.5), zinc=low(1.0), boron=medium(0.5), pH=critical(0), moisture=ok(1.0), light=ok(1.0)

```
= 15(0) + 15(0.5) + 15(1.0) + 5(0.5) + 5(1.0) + 5(0.5) + 20(0) + 10(1.0) + 10(1.0)
= 0 + 7.5 + 15 + 2.5 + 5 + 2.5 + 0 + 10 + 10
= 52.5  →  "Moderate"
```

**Future refinement (not required for v1, note for later):** consider discounting each 2A factor's contribution by its confidence score (e.g., a low-confidence "high" risk shouldn't count as heavily as a high-confidence one). Keep v1 simple — implement the flat formula above first, revisit if time allows.

---

## 4. Public API contract (the ONLY external contract)

### INPUT — single POST from frontend, one combined payload

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

### OUTPUT — combined response

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

`module2a.input_typicality` (added with `module2a-v4`) is a signal from an unsupervised anomaly detector, not a 7th risk target: it reports whether this submission resembles the data Module 2A was trained on. It does not feed the score. Use it to caveat a result in the UI when `flag` is `"unusual"` — see `api/recommendations.py`.

`recommendation_notes` (added in v1.1.0) is ready-to-display farmer text, built from the 2A and 2B results by `api/recommendations.py`. It contains:
- a `headline`;
- `needs_attention`: medium and high risk, worst first, each with `confidence_pct`, `confidence_text` and `why`;
- `looking_fine`: low risk;
- a `caveat`;
- and, only when they apply, `soil_condition_note` (pH outside the crop's range) and `reliability_note` (`input_typicality.flag` is `"unusual"`).

It restates the results and never changes them, and it is `null` for an unsupported crop. The Project Manager approved `recommendation_notes`, `module2a.input_typicality` and `module2a_model_version` as part of this contract on 2026-09-11.

### OUTPUT — unsupported crop case

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

---

## 5. Build checklist — completed 2026-09-10

- [x] Single public endpoint accepts the combined input schema above. → `POST /predict` in `api/main.py`.
- [x] Orchestrator splits the payload and calls 2A's and 2B's internal functions — no logic duplicated. → `analyze_soil()` in `api/orchestrator_service.py`.
- [x] Crop-support check happens once, at the top, before calling either sub-module. → guard at the head of `analyze_soil()`.
- [x] Score calculation implemented exactly per Section 3 as an independently testable pure function. → `calculate_soil_health_score()`.
- [x] Unit test the worked example — returns exactly 52.5 / "moderate". → `tests/test_api.py::test_score_matches_spec_worked_example`.
- [x] Confirm 2A and 2B are NOT independently reachable via any other route. → the temporary `/dev/module2b/compare` route has been removed; `tests/test_api.py::test_internal_submodules_are_not_publicly_routable` asserts no route path exposes them.

### Implementation notes

- **Artifact loading:** Module 2A's eight model files load once at startup, are checked against the checksums in `models/manifest.json`, and stay in memory. If a file is missing or fails the check, `/health` still answers and `/predict` returns HTTP 503 with `{"message": "Prediction Failed: model artifacts unavailable."}`; the exact cause is written to the server log.
- **Feature order** is read from `models/module2a_schema.json` (`feature_columns_in_order`), never hardcoded, so the service cannot drift from whatever the notebook last trained.
- **Farmer-facing text** lives in `api/recommendations.py`, deliberately outside the model layer, so the wording can change without touching the models. The orchestrator returns it as `recommendation_notes`.
