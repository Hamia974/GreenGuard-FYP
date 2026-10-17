// Per ai/API_CONTRACT.md's "POST /v1/predict" table -- the model covers
// only these 7 crops. Mirrors backend/ai_services/disease_module_client.py's
// SUPPORTED_CROPS exactly; kept as a small static list rather than fetched
// from GET /v1/classes, per that endpoint's own doc note that it exists for
// per-class metadata (this app never looks any up -- display_name/is_healthy
// come back inline on every prediction/top3 entry), not for the crop list.
export const SUPPORTED_CROPS = [
  "wheat",
  "rice",
  "cotton",
  "maize",
  "sugarcane",
  "tomato",
  "potato",
] as const;

export type SupportedCrop = (typeof SUPPORTED_CROPS)[number];

// Display names for these crop ids live in messages/<locale>/crops.json.

export type DiseaseCheckStatus = "ok" | "uncertain";

export interface DiseasePredictionItem {
  classId: string;
  crop: string;
  disease: string;
  displayName: string;
  isHealthy: boolean;
  /** Raw 0-1 value from the API, never recalculated or averaged here. */
  confidence: number;
}

export interface DiseaseCheckResult {
  status: DiseaseCheckStatus;
  farmId: string | null;
  timestamp: string;
  /** The best class, or null when status is "uncertain" -- never invented. */
  prediction: DiseasePredictionItem | null;
  /** Always present (including when uncertain) -- see api.ts for why this must always render. */
  top3: DiseasePredictionItem[];
  cropSource: "user" | "model";
  detectedCrop: string;
  warnings: string[];
  message: string | null;
  modelVersion: string;
  requestId: string;
}
