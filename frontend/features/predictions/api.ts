import { apiClient } from "@/lib/api-client";
import { mapDiseaseCheckResult, type RawDiseaseCheckResult } from "@/features/module1/api";
import { mapModule2Result, type RawModule2Result } from "@/features/module2/api";
import { mapWeatherReport, type RawWeatherReport } from "@/features/weather/api";

import type { Prediction } from "./types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data?: T;
}

/**
 * `prediction_report` holds each module's own response verbatim. Typed as
 * `unknown` because rows saved by the retired ANN Fusion pipeline carry an
 * older, incompatible shape -- each section is only mapped once it is
 * confirmed to match its module's current contract.
 */
interface RawPredictionReport {
  module1?: unknown;
  module2?: unknown;
  module3?: unknown;
  module4?: unknown;
}

interface RawPrediction {
  prediction_id: string;
  farm_id: string;
  uploaded_image: string | null;
  prediction_report: RawPredictionReport | null;
  prediction_status: string;
  created_at: string;
  updated_at: string;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** Live Module 1 contract (ai/API_CONTRACT.md): always carries `status` and `top3`. */
function isDiseaseResult(value: unknown): value is RawDiseaseCheckResult {
  return isObject(value) && typeof value.status === "string" && Array.isArray(value.top3);
}

function isModule2Result(value: unknown): value is RawModule2Result {
  return isObject(value) && typeof value.crop_supported === "boolean";
}

/** Module 3 contract: nested `weather` + `risk_assessment` objects. */
function isWeatherReport(value: unknown): value is RawWeatherReport {
  return isObject(value) && isObject(value.weather) && isObject(value.risk_assessment);
}

function mapPrediction(raw: RawPrediction): Prediction {
  const report = raw.prediction_report ?? {};
  return {
    predictionId: raw.prediction_id,
    farmId: raw.farm_id,
    uploadedImage: raw.uploaded_image,
    predictionStatus: raw.prediction_status,
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
    disease: isDiseaseResult(report.module1) ? mapDiseaseCheckResult(report.module1) : null,
    soilNutrient: isModule2Result(report.module2) ? mapModule2Result(report.module2) : null,
    weather: isWeatherReport(report.module3) ? mapWeatherReport(report.module3) : null,
    isLegacyReport: "module4" in report,
  };
}

/**
 * POST /api/v1/predictions/analyze/ (Quick Scan) per REST_API_SPEC.md
 * section 3. Returns the saved analysis -- Module 1, 2 and 3 results side
 * by side -- in the same shape as GET /api/v1/predictions/{id}/.
 */
export async function analyzePrediction(
  farmId: string,
  image: File,
  crop?: string
): Promise<Prediction> {
  const formData = new FormData();
  formData.append("farm_id", farmId);
  formData.append("image", image);
  if (crop) {
    formData.append("crop", crop);
  }

  const { data } = await apiClient.post<ApiEnvelope<RawPrediction>>(
    "/predictions/analyze/",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return mapPrediction(data.data as RawPrediction);
}

export async function fetchPrediction(predictionId: string): Promise<Prediction> {
  const { data } = await apiClient.get<ApiEnvelope<RawPrediction>>(
    `/predictions/${predictionId}/`
  );
  return mapPrediction(data.data as RawPrediction);
}
