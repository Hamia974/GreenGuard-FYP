export interface HistoryListItem {
  predictionId: string;
  /** Module 1's own disease result; null when Module 1 was uncertain. */
  diagnosis: string | null;
  /** Module 1's own confidence (0-1); null when Module 1 was uncertain. */
  confidence: number | null;
  /**
   * Always null today -- the Prediction model has no crop-recommendation
   * source. Preserved as a field (not dropped) because REST_API_SPEC.md
   * section 6's documented response shape includes it. See
   * backend/history/serializers.py for the full rationale.
   */
  recommendedCrop: string | null;
  createdAt: string;
}

export type HistorySort = "newest" | "oldest";

export interface HistoryQueryParams {
  page: number;
  limit: number;
  search: string;
  sort: HistorySort;
  fromDate: string;
  toDate: string;
}
