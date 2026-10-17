import type { DiseaseCheckResult } from "@/features/module1/types";
import type { Module2Result } from "@/features/module2/types";
import type { WeatherReport } from "@/features/weather/types";

/**
 * One Quick Scan analysis -- Module 4, the integrated report. Each section
 * is the unmodified result of its own independent AI module; nothing here
 * is a combined or fused value.
 */
export interface Prediction {
  predictionId: string;
  farmId: string;
  uploadedImage: string | null;
  predictionStatus: string;
  createdAt: string;
  updatedAt: string;
  /** Module 1 (Disease Detection). Null only for reports saved before the live contract. */
  disease: DiseaseCheckResult | null;
  /** Module 2 (Soil & Nutrient): the farm's latest Soil Test, or null if none was run. */
  soilNutrient: Module2Result | null;
  /** Module 3 (Weather Risk). */
  weather: WeatherReport | null;
  /** True for reports created by the retired ANN Fusion pipeline. */
  isLegacyReport: boolean;
}
