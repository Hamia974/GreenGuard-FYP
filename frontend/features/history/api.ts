import { apiClient } from "@/lib/api-client";

import type { HistoryListItem, HistoryQueryParams } from "./types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data?: T;
}

interface RawHistoryListItem {
  prediction_id: string;
  diagnosis: string | null;
  confidence: number | null;
  recommended_crop: string | null;
  created_at: string;
}

function mapHistoryListItem(raw: RawHistoryListItem): HistoryListItem {
  return {
    predictionId: raw.prediction_id,
    diagnosis: raw.diagnosis,
    confidence: raw.confidence,
    recommendedCrop: raw.recommended_crop,
    createdAt: raw.created_at,
  };
}

/**
 * GET /api/v1/history/ per REST_API_SPEC.md section 6. A distinct, narrower
 * contract from GET /api/v1/predictions/ (Phase 6) -- this list item has no
 * plant image, full AI report, or farm information, because section 6's
 * documented response shape doesn't include them. Detail viewing reuses the
 * existing Phase 6 Prediction Report page/route rather than a second
 * near-duplicate detail page.
 */
export async function fetchHistory(params: Partial<HistoryQueryParams>): Promise<HistoryListItem[]> {
  const { data } = await apiClient.get<ApiEnvelope<RawHistoryListItem[]>>("/history/", {
    params: {
      page: params.page,
      limit: params.limit,
      search: params.search || undefined,
      sort: params.sort,
      from_date: params.fromDate || undefined,
      to_date: params.toDate || undefined,
    },
  });
  return (data.data ?? []).map(mapHistoryListItem);
}

/** DELETE /api/v1/history/{prediction_id}/ per REST_API_SPEC.md section 6. */
export async function deleteHistoryPrediction(predictionId: string): Promise<void> {
  await apiClient.delete(`/history/${predictionId}/`);
}
