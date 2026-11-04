import type { Prediction } from "@/features/predictions/types";

import type { RecentPrediction } from "../types";

export type LeafStatus = "healthy" | "uncertain" | "diseased";

/** One recent leaf check: the summary row plus its full report once loaded. */
export interface RecentCheck {
  row: RecentPrediction;
  detail: Prediction | undefined;
  status: LeafStatus | null;
}

/**
 * Module 1's own verdict for one leaf check. Returns null while the full
 * report is still loading and the summary row alone cannot tell healthy from
 * diseased (it only carries the display name).
 */
export function leafStatusOf(
  row: RecentPrediction,
  detail: Prediction | undefined
): LeafStatus | null {
  const disease = detail?.disease;
  if (disease) {
    if (disease.status === "uncertain" || !disease.prediction) return "uncertain";
    return disease.prediction.isHealthy ? "healthy" : "diseased";
  }
  return row.diagnosis === null ? "uncertain" : null;
}
