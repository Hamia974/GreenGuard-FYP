# Model Documentation — Module 2: Soil & Nutrient Analysis

**Version:** 1.2.0
**Type:** ML classifiers + unsupervised typicality detector (Module 2A), rule engine (Module 2B), weighted scoring layer

## General information

| | |
|---|---|
| Module name | GreenGuard Module 2 — Soil & Nutrient Analysis |
| Module version | 1.2.0 |
| Model name | Module 2A Nutrient Risk Classifier (6 × XGBoost) with Input Typicality Detector (IsolationForest) |
| Model version | `module2a-v5` |
| Scoring layer version | `module2-orchestrator-v1` |
| Release date | 2026-09-11 |
| Frameworks | XGBoost 3.4.1, scikit-learn 1.9.0 (CPU only) |

## Model purpose

Farmers in the target deployment do not have access to laboratory soil tests. Module 2
estimates which nutrients a crop is likely short of from what a farmer can observe and report —
crop, growth stage, soil type, fertilizer history, irrigation and visible leaf symptoms — plus
three readings from a handheld soil meter. It then compares those readings against the crop's
ideal growing conditions and combines both into one soil-health score the farmer can act on.

| Component | Type | What it produces |
|---|---|---|
| Module 2A — nutrient risk | 6 XGBoost classifiers, one per nutrient | `low` / `medium` / `high` risk + confidence for N, P, K, Mg, Zn, B |
| Module 2A — input typicality | IsolationForest (unsupervised, trained on inputs only) | `typical` / `unusual` flag + score |
| Module 2B — growing conditions | Deterministic rule engine, no model file | pH, moisture and light vs. the crop's ideal range; pH lockout note |
| Overall score | Transparent weighted sum | 0–100 score + `good` / `moderate` / `poor` |

## Model inputs

All inputs arrive in one `POST /predict` request. Allowed values are also published for the
frontend in `docs/module2_field_options.json`.

| Field | Type | Allowed values / range | Used by |
|---|---|---|---|
| `crop` | string | `wheat`, `rice`, `cotton`, `sugarcane`, `maize`, `potato`, `tomato`, `chickpea`, `eggplant`, `cucumber`, `bitter_gourd`, `snake_gourd`, `ridge_gourd`, `ash_gourd`, `bottle_gourd` | 2A, 2B |
| `growth_stage` | string | `seedling`, `vegetative`, `flowering`, `fruiting_grain_filling`, `maturity` | 2A |
| `soil_type` | string | `sandy`, `sandy_loam`, `loamy`, `clay_loam`, `clay`, `saline_affected` | 2A |
| `last_fertilizer_type` | string | `Urea`, `DAP`, `NPK_blend`, `MOP_SOP`, `FYM_compost`, `No_Fertilizer`, `Dont_know` | 2A |
| `days_since_fertilizer` | string | `lt_15_days`, `15_30_days`, `30_60_days`, `60_90_days`, `gt_90_days`, `not_applicable` (exactly when `No_Fertilizer`) | 2A |
| `irrigation_source` | string | `canal`, `tube_well`, `rain_fed`, `drip`, `flood_basin` | 2A |
| `irrigation_adequacy` | string | `insufficient`, `adequate`, `excessive` | 2A |
| `temperature_c` | number | −60 to 60 | 2A |
| `humidity_pct` | number | 0 to 100 | 2A |
| `rainfall_mm_last_7_days` | number | ≥ 0 | 2A |
| `ph_value` | number | 0 to 14 (soil meter) | 2B |
| `soil_moisture_pct` | number | 0 to 100 (soil meter) | 2B |
| `light_intensity_lux` | number | ≥ 0 (soil meter) | 2B |
| `symptoms` | object of 11 booleans | `yellowing_older_leaves`, `purple_reddish_tint`, `brown_scorched_leaf_edges`, `stunted_growth`, `poor_flowering_or_fruiting`, `weak_stems`, `interveinal_chlorosis_older_leaves`, `interveinal_chlorosis_young_leaves`, `leaf_curling_brittle`, `short_internodes_small_leaves`, `none_visible` — at least one must be true, and `none_visible` cannot be combined with any other | 2A |

The three meter readings are required. They feed Module 2B and the score; Module 2A is not
trained on them and never receives them.

## Model outputs

| Field | Values | Meaning |
|---|---|---|
| `module2a.<nutrient>_risk.level` | `low` / `medium` / `high` | Deficiency risk for each of the six nutrients |
| `module2a.<nutrient>_risk.confidence` | 0–1 (2 dp) | Model probability of the predicted level; shown to the farmer as a percentage |
| `module2a.overall_nutrient_health` | `good` / `moderate` / `poor` | Derived from the N, P and K levels by a fixed rule (in `models/module2a_schema.json`) |
| `module2a.input_typicality.flag` | `typical` / `unusual` | Whether this combination of answers resembles those the models were trained on |
| `module2a.input_typicality.anomaly_score` | number (3 dp) | Positive = typical, negative = unusual; further from 0 = more so |
| `module2b.ph` / `soil_moisture` / `light` | `current`, `ideal_range` `[low, high]`, `gap`, `status` (`ok` / `moderate` / `critical`) | Reading vs. the crop's ideal band; `high` is `null` when there is no upper limit; `gap` is 0 inside the band |
| `module2b.ph.nutrient_lockout_note` | text | Which nutrients the soil's pH makes less available, in plain language |
| `overall_soil_health_score` | 0–100 | Weighted score: N/P/K 15 each, Mg/Zn/B 5 each, pH 20, moisture 10, light 10 |
| `overall_soil_health_label` | `good` (≥ 80) / `moderate` (≥ 50) / `poor` | Bucket for the score |
| `model_version`, `module2a_model_version` | string | Scoring-layer and model versions that produced this result |
| `recommendation_notes` | object | Plain-language summary for the farmer: a headline, the nutrients that need attention (with the reason and confidence wording), the nutrients looking fine, and a not-a-lab-test caveat; `null` for an unsupported crop |

## Module 2B rules

Module 2B compares each meter reading with the crop's ideal range. A reading inside the range
is `ok`. A reading outside it is `moderate`, or `critical` when it is further out than these
limits: more than 1.0 pH unit, more than 20 percentage points of moisture, or more than
15,000 lux below the light minimum.

| Crop | Ideal pH | Ideal soil moisture (%) |
|---|---|---|
| Wheat | 6.0 – 7.5 | 50 – 70 |
| Rice | 5.5 – 7.0 | 80 – 100 |
| Cotton | 6.0 – 6.5 | 50 – 75 |
| Sugarcane | 6.0 – 6.5 | 50 – 75 |
| Maize | 5.5 – 7.5 | 60 – 80 |
| Potato | 4.8 – 6.5 | 60 – 80 |
| Tomato | 6.2 – 6.8 | 50 – 75 |
| Chickpea | 6.0 – 7.0 | 50 – 75 |
| Eggplant | 5.5 – 6.8 | 50 – 75 |
| Cucumber | 5.5 – 6.8 | 60 – 80 |
| Bitter gourd | 5.5 – 6.7 | 50 – 75 |
| Snake gourd | 5.5 – 6.8 | 50 – 75 |
| Ridge gourd | 5.5 – 6.8 | 50 – 75 |
| Ash gourd | 5.5 – 7.0 | 50 – 75 |
| Bottle gourd | 6.0 – 7.5 | 50 – 75 |

Light must be at least 25,000 lux for every crop, with no upper limit. The ranges are defined in
`api/module2b_service.py` (`CROP_RANGES`).

**Agronomy review (GG-M2-AR-01, Sabra Anwar, UCP biotechnology, 2026-09-13; approved with
changes):** the original 8 crops' pH/moisture ranges were confirmed correct except chickpea
(corrected 5.5–6.0 → 6.0–7.0 above, since chickpea performs well near neutral pH). The 7
horticultural crops (eggplant through bottle gourd) were reviewed as Preliminary and agreed as
a reasonable starting point, but still await local field validation before being treated as
equally rigorous as the original 8's ranges.

The reviewer also flagged the soil-health score weighting as not reflecting per-crop
importance. **Applied**: `orchestrator_service.py` now uses crop-dependent weights for the 6
Cucurbitaceae crops (cucumber + the 4 gourds), trimming N/P/K 2 points each to raise Zn/B 3
points each (see `CUCURBIT_SCORE_WEIGHTS`) — grounded in the same cucurbit zinc/boron
sensitivity documented in `Module2A_Engineering_Handoff.md` Section 7a, not a new guess.
**Not applied** (flagged without a concrete number, and investigation found no safe way to
apply one): the moisture/light critical-gap thresholds (20 points / 15,000 lux) and the
25,000 lux minimum should ideally be calibrated by soil type and crop growth stage, but real
field-capacity-by-soil-texture research (e.g. ~10-18% VWC for sandy soils vs. ~38-42% for
clay) turned out to use a completely different percentage scale than this app's uncalibrated
"0-100, soil meter" reading (whose existing bands, e.g. rice's 70-100%, are clearly a relative
consumer-meter index, not true volumetric water content) — grafting the two together would
silently miscalibrate a system the reviewer already approved, so this stays a documented
limitation rather than a guessed fix. Ranges may also need to differ by Pakistani region
(Punjab/Sindh/KP/Balochistan) and season once locally validated data is available.

**Second agronomy review (GG-M2-AR-02, Numan Niaz, Dogar Agri Farm owner, 10 years field
experience specifically in wheat/rice/maize/potato, 2026-09-15; approved with changes).**
Unlike the first review (a student, no field experience), this reviewer's suggestions were
cross-checked against published agronomy sources before applying, since a single
practitioner's field experience — however credible — is still one anecdotal source against
data the original ranges cited as "Reference"-sourced:
- **Applied** (widened ranges, corroborated by published sources): wheat pH 6.5–7.0 → 6.0–7.5
  (published optimum ~7.2 sits outside the old band); rice pH 6.0–6.5 → 5.5–7.0 (published
  range ~5.5–6.6); maize pH 6.0–7.0 → 5.5–7.5 (published range ~6.0–7.2, comfortably inside
  the wider band). Moisture: wheat 50–75% → 50–70%, rice 70–100% → 80–100%, maize 50–75% →
  60–80%, potato 50–75% → 60–80% (maize and potato both corroborated by published sources
  emphasizing high moisture demand at key growth stages; wheat/rice tightened on the
  reviewer's field-practice judgement, both still comfortably inside the old band so low-risk
  either way).
- **NOT applied**: the reviewer's suggested potato pH lower bound (4.8 → 5.0). Published
  sources specifically confirm potato's tolerance down to 4.8 (matching the pre-existing
  value), so the practitioner's suggestion was outweighed by literature here — potato's pH
  range is unchanged.
- **Applied**: laboratory-soil-test recommendation appended to the two `critical`-tier
  `nutrient_lockout_note` messages (pH < 5.0 and pH > 8.0). Both reviewers independently
  asked for this in their general-questions section, and this reviewer additionally marked
  "Advice Needed" on all 4 Section D critical-gap thresholds — the pH one is the only one
  with a concrete, well-supported trigger value from both reviews, hence the only one acted
  on; the moisture/light thresholds remain the same open limitation noted above.
- **Applied**: potato-specific score weighting (`POTATO_SCORE_WEIGHTS` in
  `orchestrator_service.py`) — N/P trimmed 2 points each, K raised 4 points (15 → 19), per
  the reviewer's own words: "potassium matters more in potato." Potato is a well-documented
  heavy potassium feeder; K deficiency disproportionately hurts tuber size/quality.
- **Corroborates review 1**: potassium's explanation symptom (`brown_scorched_leaf_edges`)
  was independently flagged by both reviewers, strengthening confidence in that change.
  Boron's explanation symptom was also flagged by both, but neither gave (review 2) or was
  empirically supported by (review 1's suggestion) a viable replacement — see the
  `DOMINANT_SYMPTOM` comment in `recommendations.py`; still an open, documented tension.
- **Refined, not new**: on regional/seasonal variation, this reviewer's practical view was
  narrower than review 1's — pH preference is crop chemistry and "does not need to change
  simply because of province," but irrigation/moisture advice specifically should vary
  regionally. Recorded here as a refinement of the same open item.

Sources: [Agrii — soil pH by crop](https://www.agrii.co.uk/our-services/digital-farming/the-importance-of-soil-ph-in-agriculture-for-different-crops/), [NC State Extension — soil pH, wheat and corn](https://corn.ces.ncsu.edu/corn-production-information/how-soil-ph-affects-wheat-and-corn-yields/), [NPCK — suitable soil for potato](https://npck.org/suitable-soil-for-planting-of-potato-crops/), [Yara — potato agronomic principles](https://www.yara.us/crop-nutrition/potato/agronomic-principles/).

Separately, the soil's pH sets the `nutrient_lockout_note`. This is the same for every crop:

| Soil pH | What the note tells the farmer |
|---|---|
| Below 5.0 | Strongly acidic: several major nutrients are limited; liming and a lab test are suggested |
| 5.0 to under 5.5 | Acidic: phosphorus is starting to lock up |
| 5.5 to 7.0 | Good range: most nutrients are readily available |
| Over 7.0 to 7.5 | Slightly high: micronutrients are becoming less available |
| Over 7.5 to 8.0 | Alkaline: iron, manganese and zinc availability is dropping |
| Over 8.0 | Strongly alkaline: zinc, iron, manganese and copper are likely locked up; a lab test is suggested |

The crop comparison (`status`) and the pH note are separate judgements and can differ. For
example, pH 5.1 is `critical` for tomato (1.1 below its 6.2-6.8 range), while the note
describes it as only acidic.

## Training data

Module 2A is trained on 37,500 farm records covering all 15 crops, 2,500 per crop. Each record
holds the questionnaire answers, the weather values and a `low` / `medium` / `high` label for
each nutrient.

- **Base records.** 20,000 records for the eight field crops, built from published agronomic
  relationships between soil, fertilizer history, irrigation, visible symptoms and nutrient
  deficiency.
- **Horticultural crops.** The seven horticultural crops were added by resampling base records,
  weighted so that each crop appears with the soil types, irrigation methods and climate it is
  usually grown in.
- **Cucurbit sensitivity.** For the six cucurbits (cucumber and the five gourds), zinc and boron
  risk is one level higher where a leaching risk factor is present: sandy or sandy-loam soil,
  or insufficient irrigation. This reflects the family's documented sensitivity to these two
  micronutrients.
- **Saline soil.** Zinc risk is one level higher on saline-affected soil for every crop. This
  matches the alkaline zinc lock-up described in Module 2B's pH notes.
- **Typicality detector.** A separate set of 60,000 unlabelled records (4,000 per crop),
  spanning each crop's usual conditions, trains the input-typicality detector. It uses no risk
  labels.

`scripts/build_v4_dataset.py`, in the AI team's repository, rebuilds the dataset exactly from
the base records. The evaluation split groups records by input signature, so identical answer
combinations never appear in both training and test (see Performance summary).

## Performance summary

Module 2A was evaluated on a held-out test set of about 7,500 rows per nutrient from a
37,500-row dataset. The split is grouped by input signature: no combination of answers the
model was trained on appears in the test set, so every score below is measured on inputs the
model has never seen. Precision, recall and F1 are macro averages over the three risk levels,
which weight `low`, `medium` and `high` equally rather than rewarding the most common level.

| Nutrient | Accuracy | Precision | Recall | F1 | Cross-validated F1 | High-risk recall |
|---|---|---|---|---|---|---|
| Nitrogen | 62.5% | 0.619 | 0.620 | 0.618 | 0.630 ± 0.003 | 65.3% |
| Phosphorus | 63.4% | 0.627 | 0.623 | 0.624 | 0.630 ± 0.002 | 61.4% |
| Potassium | 65.8% | 0.659 | 0.654 | 0.656 | 0.665 ± 0.003 | 66.5% |
| Magnesium | 54.0% | 0.525 | 0.531 | 0.524 | 0.523 ± 0.000 | 54.8% |
| Zinc | 64.6% | 0.641 | 0.657 | 0.646 | 0.648 ± 0.003 | 71.5% |
| Boron | 56.1% | 0.554 | 0.563 | 0.556 | 0.551 ± 0.003 | 63.8% |

A three-level random guess scores about 33%. Held-out and cross-validated scores agree
closely for every nutrient, and training scores sit within 0.03–0.09 of test scores, so the
models apply learned relationships rather than recalling training rows. Magnesium and boron
are the hardest targets: fewer observable signals distinguish their risk levels. *High-risk
recall* is the share of truly high-risk cases the model flags as high — the error that costs a
farmer most is a missed deficiency. Full metrics, hyperparameters and calibration figures are
in `models/module2a_model_card.json`.

**Model selection.** XGBoost was compared against a RandomForest baseline and a
HistGradientBoosting challenger on the same split (`models/model_comparison.csv`). Mean F1:
RandomForest 0.585, XGBoost 0.604, HistGradientBoosting 0.610. Both boosted models beat the
baseline on every nutrient; the two boosted models are within one to three cross-validation
standard deviations of each other, and XGBoost is retained as the served model.

**Feature relevance.** Permutation importance and feature-group ablation identify four inputs
with little individual influence (`irrigation_source`, `humidity_pct`,
`rainfall_mm_last_7_days`, `symptom_none_visible`); removing them changes cross-validated F1 by
no more than the noise floor (about 0.006), so all inputs are retained. `crop` is essential for
zinc (−0.082 F1 without it) and boron (−0.043), and `growth_stage` for potassium (−0.021). The weather inputs are fetched automatically at no
cost to the farmer and are kept for future retraining on field data.

## Validation

| Check | Result |
|---|---|
| Split integrity | Grouped by input signature; 0 of ~7,500 held-out rows per nutrient repeat a training input |
| Reliability | Cross-validated mean ± std reported per nutrient alongside held-out scores |
| Calibration | Expected Calibration Error 0.012–0.023 across all six; no recalibration required |
| Measurement-noise robustness | ±1 °C / ±3 % humidity / ±2 mm rainfall changes 2–5 % of held-out predictions |
| Behavioural testing | 12 directional agronomic invariants; 12/12 pass |
| Textbook presentations | 10 of 12 classic deficiency cases flagged medium or high; the two others are single-symptom cases returned as low at under 50 % confidence |
| Regression suite | 88 automated tests: API contract, validation, error responses, scoring, model behaviour, farmer-facing wording, artifact integrity and recorded release outputs |

Calibration matters because confidence is shown to the farmer as a percentage, so it must mean
what it says: of predictions made at 70 % confidence, about 70 % are correct.

## Response time

Measured on a development laptop (CPU only), service started with `python main.py`.

| Metric | Value |
|---|---|
| Startup until `/health` answers (includes loading and verifying model files) | ~3 s |
| Warm `/predict` over HTTP, median | ~46 ms |
| Warm `/predict` over HTTP, 95th percentile | ~61 ms |
| Memory (resident, after startup) | ~200 MB |

## Model files and integrity

| File | Purpose |
|---|---|
| `module2a_<nutrient>_risk.joblib` (6) | Trained XGBoost classifiers |
| `module2a_ordinal_encoder.joblib` | Encodes the categorical inputs |
| `module2a_anomaly_detector.joblib` | IsolationForest for input typicality |
| `module2a_schema.json` | Feature order, label mapping, trained crops, `overall_nutrient_health` rule |
| `manifest.json` | SHA-256 checksum of each file above and the library versions used for training |
| `module2a_model_card.json`, `model_comparison.csv` | Evaluation record (not loaded by the service) |

At startup the service checks every model file against `manifest.json`. A missing or altered
file makes `/predict` return 503 rather than serve predictions from the wrong model; a library
version different from training is logged as a warning. `tests/test_deployment.py` repeats
these checks and confirms the service reproduces the recorded release outputs.

## Notes

- **Training data.** Module 2A is trained on a structured dataset built from published
  agronomic relationships between farm conditions, symptoms and nutrient deficiencies. How it
  was built is summarised under Training data above. Metrics describe performance on that
  dataset; validation on field data collected from real farms is the natural next step once
  such data is available.
- **Advisory output.** Accuracy is 54–66 % per nutrient against a 33 % chance baseline, so
  results are guidance, not a diagnosis. The farmer-facing notes in the response
  (`recommendation_notes`) describe lower-confidence results by the signs behind them, show every confidence as a
  percentage, and include a short advisory note.
- **Input typicality.** An `unusual` flag does not block the prediction; it signals that the
  answers form an uncommon combination and the result deserves extra caution.
- **Module 2B ranges.** Moisture and light bands are general-purpose. The original 8 crops' pH/
  moisture ranges have been agronomy-reviewed (see Module 2B rules); the 7 horticultural crops
  remain provisional pending local field validation.
- **Overall score.** A transparent, tunable weighted sum, not a trained model — see
  `Module2_Orchestrator_Spec.md` Section 3.

## Retraining

Run `training/module2a_nutrient_risk.ipynb` top to bottom with the dataset in `data/` (held by
the AI team, not part of the delivery package). It overwrites the model files, model card and
`manifest.json`. Then run `python tests/test_deployment.py --record` to record the new release
outputs and refresh `samples/sample_response.json`, and update this document.

## Versioning

**Module**

v1.0.0 (2026-09-10) — `POST /predict` connects Module 2A (`module2a-v5`), Module 2B and the
weighted score in one response. pH, soil moisture and light are required inputs. All 15 crops
supported by both sub-modules.

v1.1.0 (2026-09-11) — Delivery packaging. No change to request or response fields, or to any
prediction:
- Typed response schema, published in `/docs` and the OpenAPI document.
- Error bodies unified on `{"message": ...}`, matching the Weather module. The 503 case
  previously returned `{"detail": "<server file path>"}`.
- Model-file checksum manifest, verified at startup.
- `MODELS_DIR` setting.
- Docker packaging:
  - `Dockerfile` with an unprivileged user, a built-in health check and an in-image
    deployment check;
  - `.dockerignore` and `docker-compose.yml`;
  - Linux wheels confirmed for x86_64 and arm64.
- Deployment verification tests with recorded release outputs.
- Delivery packaging script.
- Input typicality is now scored once per request instead of twice (about 20 ms faster, with
  identical output).
- `recommendation_notes` added to the response: plain-language notes for the farmer, built
  from the Module 2A and 2B results. Purely additive; `null` for an unsupported crop.

The Project Manager approved three response fields on 2026-09-11 as part of the Module 2
response contract:
- `module2a.input_typicality`, introduced with `module2a-v4`;
- `module2a_model_version`;
- `recommendation_notes`, added in v1.1.0.

v1.2.0 (2026-09-16) — Two agronomy reviews (GG-M2-AR-01, GG-M2-AR-02; full detail under Module
2B rules above) applied. No response field was added, removed, or renamed:
- Corrected pH/moisture ranges for chickpea, wheat, rice, maize and potato in
  `module2b_service.py`'s `CROP_RANGES` (see the table above).
- `overall_soil_health_score` weighting is now crop-dependent for two groups (previously a
  single flat weighting for every crop): the 6 Cucurbitaceae crops and `potato` each use
  adjusted weights — see `Module2_Orchestrator_Spec.md` Section 3 for the exact numbers and
  `docs/module2_field_options.json` for the schema note.
- Both critical-tier `nutrient_lockout_note` messages (pH < 5.0 and pH > 8.0) now end with a
  laboratory-soil-test recommendation.
- Potassium's `recommendation_notes` explanation symptom changed from `weak_stems` to
  `brown_scorched_leaf_edges` — verified as the model's actual #2 strongest feature for
  potassium, not just a relabel.
- `reliability_note` reworded to plain language for a farmer audience (no "anomaly"/"flag"
  terminology); `Module2_Frontend_Form_Spec.md` display guidance extended with a `status` →
  plain-wording table and a "field conditions" section promoted from optional to main display.

**Model**

`module2a-v4` — Trained on all 15 crops (7 horticultural crops added; see Training data).

`module2a-v5` (current) — The evaluation split is grouped by input signature, so every reported
score is measured on input combinations never seen in training. Retrained, re-tuned and
re-evaluated; metrics above.
