import { apiClient } from "@/lib/api-client";

import type { DiseaseCheckResult, DiseasePredictionItem } from "./types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data?: T;
}

interface RawDiseasePredictionItem {
  class_id: string;
  crop: string;
  disease: string;
  display_name: string;
  is_healthy: boolean;
  confidence: number;
}

export interface RawDiseaseCheckResult {
  status: "ok" | "uncertain";
  farm_id: string | null;
  timestamp: string;
  prediction: RawDiseasePredictionItem | null;
  top3: RawDiseasePredictionItem[];
  crop_source: "user" | "model";
  detected_crop: string;
  warnings: string[];
  message: string | null;
  model_version: string;
  inference_ms: number;
  request_id: string;
}

function mapItem(raw: RawDiseasePredictionItem): DiseasePredictionItem {
  return {
    classId: raw.class_id,
    crop: raw.crop,
    disease: raw.disease,
    displayName: raw.display_name,
    isHealthy: raw.is_healthy,
    confidence: raw.confidence,
  };
}

export function mapDiseaseCheckResult(raw: RawDiseaseCheckResult): DiseaseCheckResult {
  return {
    status: raw.status,
    farmId: raw.farm_id,
    timestamp: raw.timestamp,
    prediction: raw.prediction ? mapItem(raw.prediction) : null,
    // top3 is present on every 200 response per ai/API_CONTRACT.md -- mapped
    // unconditionally here, never gated on `status`.
    top3: raw.top3.map(mapItem),
    cropSource: raw.crop_source,
    detectedCrop: raw.detected_crop,
    warnings: raw.warnings,
    message: raw.message,
    modelVersion: raw.model_version,
    requestId: raw.request_id,
  };
}

/**
 * POST /api/v1/module1/analyze/ -- the live Module 1 (Disease Detection)
 * standalone check. Quick Scan (POST /api/v1/predictions/analyze/) calls the
 * same live service and stores its response in the analysis report.
 */
export async function submitDiseaseCheck(
  farmId: string,
  image: File,
  crop?: string
): Promise<DiseaseCheckResult> {
  const formData = new FormData();
  formData.append("farm_id", farmId);
  formData.append("image", image);
  if (crop) {
    formData.append("crop", crop);
  }

  const { data } = await apiClient.post<ApiEnvelope<RawDiseaseCheckResult>>(
    "/module1/analyze/",
    formData,
    { headers: { "Content-Type": "multipart/form-data" } }
  );

  return mapDiseaseCheckResult(data.data as RawDiseaseCheckResult);
}
