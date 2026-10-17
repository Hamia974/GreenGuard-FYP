import { apiClient } from "@/lib/api-client";

import type { Module2FormValues } from "./schemas";
import type {
  ComparisonMetric,
  Module2AResult,
  Module2BResult,
  Module2Result,
  NutrientNote,
  NutrientRisk,
  RecommendationNotes,
} from "./types";

// The backend resolves weather, then calls the Module 2 service on Render,
// whose free-tier cold start alone can take ~40s -- longer than apiClient's
// default 30s. Applied to this request only.
const MODULE2_ANALYZE_TIMEOUT_MS = 120_000;

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data?: T;
}

interface RawNutrientRisk {
  level: "high" | "medium" | "low";
  confidence: number;
}

interface RawInputTypicality {
  anomaly_score: number;
  flag: "typical" | "unusual";
}

interface RawModule2A {
  nitrogen_risk: RawNutrientRisk;
  phosphorus_risk: RawNutrientRisk;
  potassium_risk: RawNutrientRisk;
  magnesium_risk: RawNutrientRisk;
  zinc_risk: RawNutrientRisk;
  boron_risk: RawNutrientRisk;
  overall_nutrient_health: "good" | "moderate" | "poor";
  input_typicality: RawInputTypicality;
  model_version: string;
}

interface RawComparisonMetric {
  current: number | null;
  ideal_range: [number | null, number | null];
  gap: number | null;
  status: string | null;
  nutrient_lockout_note?: string;
}

interface RawModule2B {
  ph: RawComparisonMetric;
  soil_moisture: RawComparisonMetric;
  light: RawComparisonMetric;
}

interface RawNutrientNote {
  nutrient: "Nitrogen" | "Phosphorus" | "Potassium" | "Magnesium" | "Zinc" | "Boron";
  level: "high" | "medium" | "low";
  confidence_pct: number;
  confidence_text: string;
  why?: string;
}

interface RawRecommendationNotes {
  headline: string;
  needs_attention: RawNutrientNote[];
  looking_fine: RawNutrientNote[];
  caveat: string;
  soil_condition_note?: string | null;
  reliability_note?: string | null;
}

export interface RawModule2Result {
  crop_supported: boolean;
  message?: string;
  module2a: RawModule2A | null;
  module2b: RawModule2B | null;
  overall_soil_health_score: number | null;
  overall_soil_health_label: "good" | "moderate" | "poor" | null;
  recommendation_notes: RawRecommendationNotes | null;
  model_version?: string;
  module2a_model_version?: string;
}

function toRequestBody(farmId: string, values: Module2FormValues) {
  return {
    farm_id: farmId,
    crop: values.crop,
    growth_stage: values.growthStage,
    soil_type: values.soilType,
    last_fertilizer_type: values.lastFertilizerType,
    days_since_fertilizer: values.daysSinceFertilizer,
    irrigation_source: values.irrigationSource,
    irrigation_adequacy: values.irrigationAdequacy,
    ph_value: values.phValue,
    soil_moisture_pct: values.soilMoisturePct,
    light_intensity_lux: values.lightIntensityLux,
    symptoms: values.symptoms,
  };
}

function mapMetric(raw: RawComparisonMetric): ComparisonMetric {
  return {
    current: raw.current,
    idealRange: raw.ideal_range,
    gap: raw.gap,
    status: raw.status,
    nutrientLockoutNote: raw.nutrient_lockout_note,
  };
}

function mapRisk(raw: RawNutrientRisk): NutrientRisk {
  return { level: raw.level, confidence: raw.confidence };
}

function mapModule2A(raw: RawModule2A): Module2AResult {
  return {
    nitrogenRisk: mapRisk(raw.nitrogen_risk),
    phosphorusRisk: mapRisk(raw.phosphorus_risk),
    potassiumRisk: mapRisk(raw.potassium_risk),
    magnesiumRisk: mapRisk(raw.magnesium_risk),
    zincRisk: mapRisk(raw.zinc_risk),
    boronRisk: mapRisk(raw.boron_risk),
    overallNutrientHealth: raw.overall_nutrient_health,
    inputTypicality: {
      anomalyScore: raw.input_typicality.anomaly_score,
      flag: raw.input_typicality.flag,
    },
    modelVersion: raw.model_version,
  };
}

function mapModule2B(raw: RawModule2B): Module2BResult {
  return {
    ph: mapMetric(raw.ph),
    soilMoisture: mapMetric(raw.soil_moisture),
    light: mapMetric(raw.light),
  };
}

function mapNutrientNote(raw: RawNutrientNote): NutrientNote {
  return {
    nutrient: raw.nutrient,
    level: raw.level,
    confidencePct: raw.confidence_pct,
    confidenceText: raw.confidence_text,
    why: raw.why,
  };
}

function mapRecommendationNotes(raw: RawRecommendationNotes): RecommendationNotes {
  return {
    headline: raw.headline,
    needsAttention: raw.needs_attention.map(mapNutrientNote),
    lookingFine: raw.looking_fine.map(mapNutrientNote),
    caveat: raw.caveat,
    soilConditionNote: raw.soil_condition_note ?? undefined,
    reliabilityNote: raw.reliability_note ?? undefined,
  };
}

export function mapModule2Result(raw: RawModule2Result): Module2Result {
  return {
    cropSupported: raw.crop_supported,
    message: raw.message,
    module2a: raw.module2a ? mapModule2A(raw.module2a) : null,
    module2b: raw.module2b ? mapModule2B(raw.module2b) : null,
    overallSoilHealthScore: raw.overall_soil_health_score,
    overallSoilHealthLabel: raw.overall_soil_health_label,
    recommendationNotes: raw.recommendation_notes
      ? mapRecommendationNotes(raw.recommendation_notes)
      : null,
    modelVersion: raw.model_version,
    module2aModelVersion: raw.module2a_model_version,
  };
}

export async function submitModule2Analysis(
  farmId: string,
  values: Module2FormValues
): Promise<Module2Result> {
  const { data } = await apiClient.post<ApiEnvelope<RawModule2Result>>(
    "/module2/analyze/",
    toRequestBody(farmId, values),
    { timeout: MODULE2_ANALYZE_TIMEOUT_MS }
  );
  return mapModule2Result(data.data as RawModule2Result);
}
