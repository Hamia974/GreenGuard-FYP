"""Pydantic schemas for the Module 2 public contract.

The field names and nesting mirror the Stress_Module documentation. Keep this
file as the single source of truth for API validation and serialization.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# Module 2A model retrained 2026-09-10 (module2a-v5) on all 15 crops -- see
# docs/MODEL_DOCUMENTATION.md (Training data). Per-crop macro-F1 for the 7
# newly added crops was verified to track the original 8, not collapse, before
# this gate was opened.
SUPPORTED_CROPS = {
    "wheat", "rice", "cotton", "sugarcane", "maize", "potato", "tomato", "chickpea",
    "eggplant", "cucumber", "bitter_gourd", "snake_gourd",
    "ridge_gourd", "ash_gourd", "bottle_gourd",
}


class Symptoms(BaseModel):
    yellowing_older_leaves: bool = False
    purple_reddish_tint: bool = False
    brown_scorched_leaf_edges: bool = False
    stunted_growth: bool = False
    poor_flowering_or_fruiting: bool = False
    weak_stems: bool = False
    interveinal_chlorosis_older_leaves: bool = False
    interveinal_chlorosis_young_leaves: bool = False
    leaf_curling_brittle: bool = False
    short_internodes_small_leaves: bool = False
    none_visible: bool = False

    @model_validator(mode="after")
    def validate_none_visible(self):
        symptom_values = self.model_dump(exclude={"none_visible"}).values()
        if self.none_visible and any(symptom_values):
            raise ValueError("none_visible cannot be combined with other symptoms")
        if not self.none_visible and not any(symptom_values):
            raise ValueError("select at least one symptom or none_visible")
        return self


class Module2Request(BaseModel):
    crop: str = Field(..., description="Crop value from module2_field_options.json")
    growth_stage: Literal["seedling", "vegetative", "flowering", "fruiting_grain_filling", "maturity"]
    soil_type: Literal["sandy", "sandy_loam", "loamy", "clay_loam", "clay", "saline_affected"]
    last_fertilizer_type: Literal["Urea", "DAP", "NPK_blend", "MOP_SOP", "FYM_compost", "No_Fertilizer", "Dont_know"]
    days_since_fertilizer: Literal["lt_15_days", "15_30_days", "30_60_days", "60_90_days", "gt_90_days", "not_applicable"]
    irrigation_source: Literal["canal", "tube_well", "rain_fed", "drip", "flood_basin"]
    irrigation_adequacy: Literal["insufficient", "adequate", "excessive"]
    temperature_c: float = Field(..., ge=-60, le=60)
    humidity_pct: float = Field(..., ge=0, le=100)
    rainfall_mm_last_7_days: float = Field(..., ge=0)
    # Required as of 2026-09-10: the deployment ships a soil meter with the farmer, so
    # these three readings are always available. Module 2B needs all three to produce a
    # growing-conditions comparison, and the orchestrator's score reserves 40 of its 100
    # points for them -- a null here would silently distort the score.
    ph_value: float = Field(..., ge=0, le=14)
    soil_moisture_pct: float = Field(..., ge=0, le=100)
    light_intensity_lux: float = Field(..., ge=0)
    symptoms: Symptoms

    @model_validator(mode="after")
    def validate_fertilizer_period(self):
        if self.last_fertilizer_type == "No_Fertilizer" and self.days_since_fertilizer != "not_applicable":
            raise ValueError("days_since_fertilizer must be not_applicable when no fertilizer was used")
        if self.last_fertilizer_type != "No_Fertilizer" and self.days_since_fertilizer == "not_applicable":
            raise ValueError("days_since_fertilizer is required when fertilizer was used")
        return self


# ---------- RESPONSE ----------
# These models document the exact JSON /predict returns. The endpoint returns the
# orchestrator's result as-is, so they describe the contract rather than reshape it;
# tests/test_api.py validates every sample response against them. Changing a field here
# requires Project Manager approval (AI_MODULE_DELIVERY_SPECIFICATION.md Section 3.6).

RiskLevel = Literal["low", "medium", "high"]
HealthLabel = Literal["good", "moderate", "poor"]
ConditionStatus = Literal["ok", "moderate", "critical"]


class NutrientRisk(BaseModel):
    level: RiskLevel
    confidence: float = Field(..., ge=0, le=1, description="Probability of the predicted level")


class InputTypicality(BaseModel):
    anomaly_score: float = Field(..., description="Higher = more typical of the training data")
    flag: Literal["typical", "unusual"]


class Module2AResult(BaseModel):
    # `model_version` is a contract field name; Pydantic otherwise reserves the
    # `model_` prefix for its own methods and warns.
    model_config = ConfigDict(protected_namespaces=())

    nitrogen_risk: NutrientRisk
    phosphorus_risk: NutrientRisk
    potassium_risk: NutrientRisk
    magnesium_risk: NutrientRisk
    zinc_risk: NutrientRisk
    boron_risk: NutrientRisk
    overall_nutrient_health: HealthLabel
    input_typicality: InputTypicality
    model_version: str


class ConditionComparison(BaseModel):
    current: float
    ideal_range: list[float | None] = Field(
        ..., min_length=2, max_length=2,
        description="[low, high]; high is null when there is no upper limit",
    )
    gap: float = Field(..., ge=0, description="Distance outside the ideal range; 0 when inside it")
    status: ConditionStatus


class PhComparison(ConditionComparison):
    nutrient_lockout_note: str


class Module2BResult(BaseModel):
    ph: PhComparison
    soil_moisture: ConditionComparison
    light: ConditionComparison
    crop_supported: Literal[True]


class Module2BUnavailable(BaseModel):
    crop_supported: Literal[False]
    message: str


class NutrientNote(BaseModel):
    nutrient: Literal["Nitrogen", "Phosphorus", "Potassium", "Magnesium", "Zinc", "Boron"]
    level: RiskLevel
    confidence_pct: int = Field(..., ge=0, le=100)
    confidence_text: str = Field(..., description="The percentage plus a plain reading of it")
    why: str | None = Field(None, description="Present only for needs_attention items")


class RecommendationNotes(BaseModel):
    """Farmer-facing notes built from the 2A/2B results (api/recommendations.py).

    Added in v1.1.0 with Project Manager approval (2026-09-11)."""

    headline: str
    needs_attention: list[NutrientNote] = Field(..., description="Medium/high risk, worst first")
    looking_fine: list[NutrientNote] = Field(..., description="Low risk")
    caveat: str
    soil_condition_note: str | None = Field(
        None, description="Present only when pH is outside the crop's ideal range")
    reliability_note: str | None = Field(
        None, description="Present only when module2a.input_typicality.flag is 'unusual'")


class SoilAnalysisResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    crop_supported: Literal[True]
    module2a: Module2AResult
    module2b: Module2BResult | Module2BUnavailable
    overall_soil_health_score: float | None = Field(..., ge=0, le=100)
    overall_soil_health_label: HealthLabel | None
    recommendation_notes: RecommendationNotes
    message: str | None = Field(None, description="Present only when Module 2B cannot serve the crop")
    model_version: str
    module2a_model_version: str


class UnsupportedCropResponse(BaseModel):
    crop_supported: Literal[False]
    message: str
    module2a: None
    module2b: None
    overall_soil_health_score: None
    overall_soil_health_label: None
    recommendation_notes: None


class ErrorResponse(BaseModel):
    message: str
