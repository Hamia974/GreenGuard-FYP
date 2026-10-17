"""Internal Module 2B pH and growing-conditions rule engine.

Called only by the Module 2 orchestrator; it has no public route of its own
(see docs/Module2_Orchestrator_Spec.md).
"""

# wheat/rice/maize pH+moisture and potato moisture widened per agronomy review
# GG-M2-AR-02 (Numan Niaz, Dogar Agri Farm owner, 10 yrs field experience in exactly
# these 4 crops, 2026-09-15), cross-checked against published agronomy sources before
# applying (see docs/MODEL_DOCUMENTATION.md for the citations and the one suggestion
# NOT applied -- potato's pH lower bound, where his 5.0 conflicts with published sources
# that confirm potato's tolerance down to 4.8, matching the pre-existing value).
CROP_RANGES = {
    "wheat": ((6.0, 7.5), (50, 70), (25000, None)),
    "rice": ((5.5, 7.0), (80, 100), (25000, None)),
    "cotton": ((6.0, 6.5), (50, 75), (25000, None)),
    "sugarcane": ((6.0, 6.5), (50, 75), (25000, None)),
    "maize": ((5.5, 7.5), (60, 80), (25000, None)),
    "potato": ((4.8, 6.5), (60, 80), (25000, None)),
    "tomato": ((6.2, 6.8), (50, 75), (25000, None)),
    # 6.0-7.0 per agronomy review GG-M2-AR-01 (Sabra Anwar, UCP, 2026-09-13):
    # chickpea performs well near neutral pH, so the original 5.5-6.0 was too narrow.
    "chickpea": ((6.0, 7.0), (50, 75), (25000, None)),
    # Horticultural ranges, reviewed as Preliminary in GG-M2-AR-01 -- reviewer agreed
    # with these as a starting point but flagged them for local field validation
    # (docs/MODEL_DOCUMENTATION.md, Module 2B rules).
    "eggplant": ((5.5, 6.8), (50, 75), (25000, None)),
    "cucumber": ((5.5, 6.8), (60, 80), (25000, None)),
    "bitter_gourd": ((5.5, 6.7), (50, 75), (25000, None)),
    "snake_gourd": ((5.5, 6.8), (50, 75), (25000, None)),
    "ridge_gourd": ((5.5, 6.8), (50, 75), (25000, None)),
    "ash_gourd": ((5.5, 7.0), (50, 75), (25000, None)),
    "bottle_gourd": ((6.0, 7.5), (50, 75), (25000, None)),
}


def _ph_lockout(ph_value: float) -> tuple[str, str]:
    """Return pH lockout status and the documented farmer-facing note."""
    if ph_value < 5.0:
        return "critical", (
            "Soil is strongly acidic. This severely limits potassium, nitrogen, "
            "phosphorus, calcium, and magnesium — and can raise aluminum/manganese "
            "to toxic levels. Fertilizer alone will not fix this; consider liming. "
            "A laboratory soil test is recommended to confirm and guide correction."
        )
    if ph_value < 5.5:
        return "moderate", (
            "Soil is acidic. Phosphorus is starting to lock up, and aluminum/"
            "manganese levels are rising. Worth monitoring."
        )
    if ph_value <= 7.0:
        return "good", (
            "pH is in a good range — most nutrients, including phosphorus and "
            "micronutrients like zinc and iron, are readily available to your plant."
        )
    if ph_value <= 7.5:
        return "borderline", (
            "pH is slightly high. Micronutrients (zinc, iron, manganese) are "
            "starting to become less available."
        )
    if ph_value <= 8.0:
        return "moderate", (
            "Soil is alkaline. Iron, manganese, and zinc availability is dropping — "
            "this can cause yellowing even if fertilizer was applied. Phosphorus is "
            "also starting to lock with calcium."
        )
    return "critical", (
        "Soil is strongly alkaline. Zinc, iron, manganese, and copper are likely "
        "severely locked up, and phosphorus is bound with calcium. This is a common "
        "issue in alkaline/calcareous soils and is a frequent cause of zinc deficiency "
        "regardless of fertilizer history. A laboratory soil test is recommended to "
        "confirm and guide correction."
    )


def _comparison(current: float, ideal_range: tuple[float, float | None], field: str) -> dict:
    ideal_low, ideal_high = ideal_range
    in_range = current >= ideal_low and (ideal_high is None or current <= ideal_high)
    if in_range:
        gap = 0
        status = "ok"
    elif current < ideal_low:
        gap = round(ideal_low - current, 2)
        status = "critical" if gap > {"ph": 1.0, "moisture": 20, "light": 15000}[field] else "moderate"
    else:
        gap = round(current - ideal_high, 2)
        status = "critical" if gap > {"ph": 1.0, "moisture": 20, "light": 15000}[field] else "moderate"
    return {"current": current, "ideal_range": [ideal_low, ideal_high], "gap": gap, "status": status}


def compare_growing_conditions(payload: dict) -> dict:
    """Compare one crop's pH, moisture, and light against Module 2B rules."""
    crop = payload["crop"]
    # Guard on CROP_RANGES itself. Checking a separate list instead would
    # let a crop pass the guard and then raise KeyError on the lookup below.
    if crop not in CROP_RANGES:
        return {
            "crop_supported": False,
            "message": "Growing-conditions comparison isn't available yet for this crop.",
        }

    # Two independent judgements, by design: `status` is how far this
    # crop's ideal band the reading sits, while `nutrient_lockout_note` describes the
    # soil chemistry, which is crop-independent. They can legitimately disagree -- a pH
    # of 5.1 is critical for tomato (band starts at 6.2) but only moderately acidic in
    # absolute terms.
    _, lockout_note = _ph_lockout(payload["ph_value"])
    ph = _comparison(payload["ph_value"], CROP_RANGES[crop][0], "ph")
    ph["nutrient_lockout_note"] = lockout_note

    moisture = _comparison(payload["soil_moisture_pct"], CROP_RANGES[crop][1], "moisture")
    light = _comparison(payload["light_intensity_lux"], CROP_RANGES[crop][2], "light")

    return {
        "ph": ph,
        "soil_moisture": moisture,
        "light": light,
        "crop_supported": True,
    }
