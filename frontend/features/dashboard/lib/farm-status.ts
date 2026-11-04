import type { WeatherReport } from "@/features/weather/types";

import { LEAF_TO_STATUS, STATUS_RANK, weatherRisks, type Status, type WeatherRisk } from "./home-status";
import type { RecentCheck } from "./leaf-status";

export interface FarmStatus {
  /** Null when the farm has no leaf check and no weather yet. */
  status: Status | null;
  /** The farm's latest leaf check, if any. */
  leaf: RecentCheck | null;
  /** The worst weather risk above Low, if any. */
  risk: WeatherRisk | null;
}

/**
 * The agreed farm status rule (2026-11-05): the worst of the latest leaf
 * check and the weather risks. Critical only when a disease and a High
 * weather risk happen together. Both causes are returned so the page can
 * always say why.
 */
export function farmStatusOf(
  farmId: string,
  checks: RecentCheck[],
  report: WeatherReport | null | undefined
): FarmStatus {
  const leaf = checks.find((check) => check.detail?.farmId === farmId) ?? null;
  const [worstRisk] = weatherRisks(report);
  const risk = worstRisk && worstRisk.status !== "healthy" ? worstRisk : null;

  const leafStatus = leaf?.status ? LEAF_TO_STATUS[leaf.status] : null;
  const weatherStatus = worstRisk?.status ?? null;

  let status: Status | null = null;
  for (const candidate of [leafStatus, weatherStatus]) {
    if (candidate && (!status || STATUS_RANK[candidate] > STATUS_RANK[status])) status = candidate;
  }
  if (leaf?.status === "diseased" && worstRisk?.level === "High") status = "critical";

  return { status, leaf, risk };
}
