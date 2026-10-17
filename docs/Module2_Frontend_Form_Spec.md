# Module 2 — Farmer Questionnaire Form Spec
### Frontend Developer Handoff

This form collects everything Module 2 needs (which internally covers both 2A and 2B — the frontend only ever talks to the backend, which calls Module 2). Everything here is answerable from what the farmer can see, except the 3 meter readings in Step 7 (required — a soil meter ships with the deployment). No lab test is ever required. Fields marked **(auto)** are NOT shown to the farmer — the backend fills them in.

---

## 1. Form fields, in display order

### Step 1 — Crop & Stage

**Q: What crop are you growing?**
`crop` — single-select, pictorial (icon per crop)

**Currently model-supported crops:**

| Value sent to API | Icon meaning |
|---|---|
| `wheat` | Wheat stalk/spike icon |
| `rice` | Rice paddy / rice grain icon |
| `cotton` | Cotton boll icon |
| `sugarcane` | Sugarcane stalk icon |
| `maize` | Corn cob icon |
| `potato` | Potato tuber icon |
| `tomato` | Tomato icon |
| `chickpea` | Chickpea pod icon |

**Horticultural crops — fully supported (current model: `module2a-v5`):**

| Value sent to API | Icon meaning |
|---|---|
| `eggplant` | Eggplant / brinjal icon |
| `cucumber` | Cucumber icon |
| `bitter_gourd` | Bitter gourd (karela) icon |
| `snake_gourd` | Snake gourd icon |
| `ridge_gourd` | Ridge gourd (turai) icon |
| `ash_gourd` | Ash gourd (petha) icon |
| `bottle_gourd` | Bottle gourd (lauki) icon |

✅ **Updated 2026-09-10 — all 15 crops are now trained and served.** Earlier revisions of this spec told you to show "coming soon" for the 7 horticultural crops because the model had not been trained on them. That is no longer true: the current model (`module2a-v5`) is trained on all 15, per-crop performance for these 7 was verified to track the original 8, and Module 2B covers them too. **Send all 15 crop values straight to `/predict` — no special-casing, no "coming soon" branch.**

If a crop outside this list of 15 ever reaches the API, it returns `crop_supported: false` with a message you can display directly, rather than an error — so no client-side crop gate is needed.

One note (does not affect the frontend): Module 2B's ideal pH/moisture bands for the original 8 crops have been through two agronomy reviews; the 7 horticultural crops' bands remain provisional pending local field validation. Any change only adjusts values; the form and the API stay the same.

**Q: What stage is your crop at?**
`growth_stage` — single-select, pictorial (small plant-growth-stage illustration)

| Value sent to API | Icon meaning |
|---|---|
| `seedling` | Tiny sprout, 1–2 leaves |
| `vegetative` | Leafy plant, no flowers yet |
| `flowering` | Plant with visible flowers |
| `fruiting_grain_filling` | Plant with visible fruit/grain heads |
| `maturity` | Fully grown, ready-to-harvest look |

---

### Step 2 — Soil

**Q: What does your soil look/feel like?**
`soil_type` — single-select, pictorial (soil texture close-up photo, not illustration — texture is hard to convey as an icon)

| Value sent to API | Photo/description meaning |
|---|---|
| `sandy` | Loose, gritty, pale, water drains fast, doesn't hold shape in hand |
| `sandy_loam` | Mostly sandy but holds a loose clump briefly |
| `loamy` | Dark, crumbly, holds shape but breaks apart easily — considered the "balanced" soil |
| `clay_loam` | Slightly sticky when wet, holds shape better than loam |
| `clay` | Sticky, dense, holds a firm ball shape when wet, cracks when dry |
| `saline_affected` | Whitish crust/patches visible on soil surface, poor plant growth in patches |

**Recommended UX:** show 6 real soil photos in a grid, one-tap select — don't rely on farmers matching a technical term. Consider a short "not sure? tap here" helper showing all 6 side by side for comparison.

---

### Step 3 — Fertilizer History

**Q: What fertilizer did you last use?**
`last_fertilizer_type` — single-select, pictorial (bag/product icon)

| Value sent to API | Icon meaning |
|---|---|
| `Urea` | White prilled/granular urea bag icon |
| `DAP` | DAP fertilizer bag icon (commonly dark granules) |
| `NPK_blend` | Generic "NPK" labeled bag icon |
| `MOP_SOP` | Potash bag icon (MOP/SOP) |
| `FYM_compost` | Farmyard manure / compost pile icon |
| `No_Fertilizer` | Crossed-out bag icon / "none" icon |
| `Dont_know` | Question-mark icon |

⚠️ **Backend value must be exactly `No_Fertilizer`** (not `None`) — a bare `None` is read as a missing value by the data tools and breaks the prediction. Label on the button can say "None" in the UI; just don't let the submitted value be a bare `None`/null string.

**Q: How long ago?** *(only shown if fertilizer ≠ No_Fertilizer)*
`days_since_fertilizer` — single-select, simple button row (no icons needed, just text/calendar chip)

| Value sent to API | Button label |
|---|---|
| `lt_15_days` | "Less than 2 weeks ago" |
| `15_30_days` | "2–4 weeks ago" |
| `30_60_days` | "1–2 months ago" |
| `60_90_days` | "2–3 months ago" |
| `gt_90_days` | "More than 3 months ago" |

If fertilizer = `No_Fertilizer`, auto-set `days_since_fertilizer` = `not_applicable`, skip this question.

---

### Step 4 — Irrigation

**Q: How do you water your field?**
`irrigation_source` — single-select, pictorial (icon)

| Value sent to API | Icon meaning |
|---|---|
| `canal` | Canal/channel water icon |
| `tube_well` | Tube well / pump icon |
| `rain_fed` | Rain cloud icon |
| `drip` | Drip irrigation line icon |
| `flood_basin` | Flooded field/basin icon |

**Q: How would you describe your watering?**
`irrigation_adequacy` — single-select, 3-button row with simple visual (e.g., a water-level gauge icon at low/mid/high fill)

| Value sent to API | Button label |
|---|---|
| `insufficient` | "Not enough — soil often dries out" |
| `adequate` | "Just right" |
| `excessive` | "Too much — soil often waterlogged" |

---

### Step 5 — Visible Symptoms (multi-select checklist)

**Q: Do you see any of these on the leaves?** — multi-select, pictorial (reference photo per symptom, since visual matching is far more reliable than a text description for a farmer)

| Value sent to API (`symptoms.*`) | Photo/illustration meaning |
|---|---|
| `yellowing_older_leaves` | Bottom/older leaves turning uniformly pale yellow, newer leaves still green |
| `purple_reddish_tint` | Leaves or stems with a purple/reddish discoloration |
| `brown_scorched_leaf_edges` | Brown, dry, "burnt-looking" edges/margins on leaves |
| `stunted_growth` | Plant visibly smaller/shorter than expected for its age |
| `poor_flowering_or_fruiting` | Few or no flowers/fruit forming despite the right stage |
| `weak_stems` | Thin, floppy, or easily bent stems |
| `interveinal_chlorosis_older_leaves` | Older leaves yellow BETWEEN the veins, veins themselves stay green |
| `interveinal_chlorosis_young_leaves` | Same pattern (yellow between green veins) but on the NEWEST leaves |
| `leaf_curling_brittle` | Leaves curling, cracking, or brittle at growing tips |
| `short_internodes_small_leaves` | Leaves noticeably small, bunched closely together on the stem |
| `none_visible` | "None of these — plant looks normal" (mutually exclusive with all others; selecting this clears all other checkboxes) |

**UX rule:** if the farmer taps "None of these," automatically deselect all other symptom checkboxes (and vice versa — selecting any symptom deselects "None"). Enforce this client-side before submit.

---

### Step 6 — Weather **(auto — do not ask the farmer)**

The frontend does not collect or send these three values. It sends the farm's `latitude` and `longitude` with the analyze request; the backend calls the Weather Risk Module and passes its readings on to Module 2 (`REST_API_SPEC.md`, Analyze Plant):

| Module 2 field | Filled in by the backend from |
|---|---|
| `temperature_c` | Weather Risk Module `weather.temperature` (°C) |
| `humidity_pct` | Weather Risk Module `weather.humidity` (%) |
| `rainfall_mm_last_7_days` | Weather Risk Module `weather.rainfall_last_7_days_mm` (trailing 7 days) |

**Do not build a form input for these.** If the weather lookup fails, the analyze request returns an error; show it and let the farmer try again.

---

### Step 7 — Meter Readings (REQUIRED as of 2026-09-10)

⚠️ **Changed 2026-09-10 — these three fields were previously optional and are now required.** A soil meter is supplied with the deployment, so the farmer always has these readings. **The API returns HTTP 422 if any of them is missing or `null`.** Build them as required inputs with validation before submit; do not send `null`.

| Field | Form label | Input type | Valid range | Required |
|---|---|---|---|---|
| `ph_value` | "Soil pH (from your meter)" | number input | 0 – 14 (typical 4.5 – 8.5) | Yes |
| `soil_moisture_pct` | "Soil moisture % (from your meter)" | number input | 0 – 100 | Yes |
| `light_intensity_lux` | "Light intensity — lux (from your meter)" | number input | 0 or more (typically up to about 120,000) | Yes |

**What they're used for:** these drive Module 2B's growing-conditions comparison and the pH nutrient-lockout explanation, and they carry 40 of the 100 points in `overall_soil_health_score`. They are **not** inputs to the Module 2A nutrient model, which was never trained on them — the backend drops them before calling 2A. So they will not change the six nutrient risk predictions, but they very much affect the pH advice and the overall score.

Show a short helper near this section, e.g. "Take these three readings with your meter before submitting — they let us check whether your soil is locking up nutrients."

---

## 2. Submit request

⚠️ **One form, one submit, one call to the backend.** The frontend sends the form to Django's analyze endpoint (`POST /api/v1/predictions/analyze/`, `multipart/form-data` — see `REST_API_SPEC.md`). It never calls Module 2, 2A or 2B directly; the backend builds Module 2's request from these fields.

| Form field | Value |
|---|---|
| `image` | The leaf photo |
| `latitude`, `longitude` | Farm location (the backend uses it to fetch the weather values) |
| `crop`, `growth_stage`, `soil_type` | Values from Steps 1–2 |
| `last_fertilizer_type`, `days_since_fertilizer` | Values from Step 3 (`No_Fertilizer` with `not_applicable` when none was used) |
| `irrigation_source`, `irrigation_adequacy` | Values from Step 4 |
| `symptoms` | JSON array of the selected symptom keys from Step 5, e.g. `["yellowing_older_leaves", "stunted_growth"]`, or `["none_visible"]` |
| `ph_value`, `soil_moisture_pct`, `light_intensity_lux` | Meter readings from Step 7 |

`ph_value`, `soil_moisture_pct` and `light_intensity_lux` are **required** — send real meter readings, never empty. A missing or invalid value is rejected with HTTP 422.

## 3. Displaying the result

The Module 2 part of the prediction report holds everything needed to show the farmer's soil result. Its full shape is in `Module2_Orchestrator_Spec.md` and `REST_API_SPEC.md` (Section 9, AI Module 2). Display it in this order:

1. **Soil health badge:** `overall_soil_health_label` and `overall_soil_health_score`, e.g. "Soil Health: Poor (47.5/100)".
2. **Headline:** `recommendation_notes.headline`, e.g. "Nitrogen needs attention first."
3. **Soil condition:** if `recommendation_notes.soil_condition_note` is present, show it near the top. It explains why nutrients can be short even after fertilizer, and appears only when the pH is outside the crop's ideal range.
4. **Needs attention:** `recommendation_notes.needs_attention`, in the order given. For each item show `nutrient`, `level`, `confidence_text` and `why`.
5. **Looking fine:** `recommendation_notes.looking_fine`, with `nutrient` and `confidence_text`.
6. **Field conditions — main section, not optional:** `module2b.ph`, `module2b.soil_moisture` and `module2b.light` — the reading (`current`), the crop's ideal range (`ideal_range`; an upper value of `null` means no upper limit), and `status`. These are the farmer's own meter readings and 40% of the score, so give them a visible section, not a collapsed/"more detail" area.
7. **Data reliability:** always show a short trust line, from `module2a.input_typicality.flag`:
   - `"typical"` → **"✓ This result looks reliable."**
   - `"unusual"` → use `recommendation_notes.reliability_note` as-is (present only in this case).
8. **Caveat:** always show `recommendation_notes.caveat` with the results.

**Plain-language rule — this whole section is farmer-facing, not a lab report.** Never show ML/lab terms on screen: no "anomaly", "anomaly score", "flag", "typical/unusual profile", raw `status` enum values, or raw `confidence` decimals. Translate every technical value to plain wording before rendering, per the tables below. `confidence_text` and `recommendation_notes` text are already translated — use them as-is. `status` is not pre-translated (it's a stable enum for your own logic/color-coding); map it yourself:

| `status` value | Show the farmer |
|---|---|
| `ok` | "Good" |
| `moderate` | "Needs attention" |
| `critical` | "Serious problem" |

**Confidence wording:** show `confidence_text` exactly as given — it already contains the percentage. Do not re-derive it. The tiers are:

| Confidence | Rendered text |
|---|---|
| ≥ 85% | "96% confident — strong match" |
| 65–84% | "72% confident — likely" |
| 50–64% | "58% confident — possible" |
| < 50% | "36% confident — based on limited signs" |

**Ordering matters:** `needs_attention` is sorted worst-first and, within a severity level, most-confident-first. Do not re-sort it.

**Unsupported crop:** if `crop_supported` is `false`, show the `message` instead of the result; the other fields are `null`.
