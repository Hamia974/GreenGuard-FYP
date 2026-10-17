export interface NutrientRisk {
  level: "high" | "medium" | "low";
  confidence: number;
}

export interface InputTypicality {
  anomalyScore: number;
  flag: "typical" | "unusual";
}

export interface Module2AResult {
  nitrogenRisk: NutrientRisk;
  phosphorusRisk: NutrientRisk;
  potassiumRisk: NutrientRisk;
  magnesiumRisk: NutrientRisk;
  zincRisk: NutrientRisk;
  boronRisk: NutrientRisk;
  overallNutrientHealth: "good" | "moderate" | "poor";
  inputTypicality: InputTypicality;
  modelVersion: string;
}

export interface ComparisonMetric {
  current: number | null;
  idealRange: [number | null, number | null];
  gap: number | null;
  status: string | null;
  nutrientLockoutNote?: string;
}

export interface Module2BResult {
  ph: ComparisonMetric;
  soilMoisture: ComparisonMetric;
  light: ComparisonMetric;
}

export interface NutrientNote {
  nutrient: "Nitrogen" | "Phosphorus" | "Potassium" | "Magnesium" | "Zinc" | "Boron";
  level: "high" | "medium" | "low";
  confidencePct: number;
  /** Pre-translated by the AI module, e.g. "82% confident — strong match". Show as-is. */
  confidenceText: string;
  /** The farmer's own answers that point to this nutrient. Present only for needs_attention items. */
  why?: string;
}

export interface RecommendationNotes {
  headline: string;
  /** Medium/high risk, worst first -- do not re-sort. */
  needsAttention: NutrientNote[];
  /** Low risk. */
  lookingFine: NutrientNote[];
  caveat: string;
  /** Present only when pH is outside the crop's ideal range. */
  soilConditionNote?: string;
  /** Present only when module2a.inputTypicality.flag is "unusual". */
  reliabilityNote?: string;
}

export interface Module2Result {
  cropSupported: boolean;
  message?: string;
  module2a: Module2AResult | null;
  module2b: Module2BResult | null;
  overallSoilHealthScore: number | null;
  overallSoilHealthLabel: "good" | "moderate" | "poor" | null;
  recommendationNotes: RecommendationNotes | null;
  modelVersion?: string;
  module2aModelVersion?: string;
}
