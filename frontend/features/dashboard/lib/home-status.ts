import type { RiskLevel, WeatherReport } from "@/features/weather/types";

import type { LeafStatus } from "./leaf-status";

/** The four statuses of the design system; Critical is kept rare. */
export type Status = "healthy" | "watch" | "risk" | "critical";

export const STATUS_RANK: Record<Status, number> = { healthy: 0, watch: 1, risk: 2, critical: 3 };

/** Module 1's leaf verdict as a status: an unclear photo is something to watch. */
export const LEAF_TO_STATUS: Record<LeafStatus, Status> = {
  healthy: "healthy",
  uncertain: "watch",
  diseased: "risk",
};

/** Module 3's risk level as a status. */
export const RISK_TO_STATUS: Record<RiskLevel, Status> = {
  Low: "healthy",
  Moderate: "watch",
  High: "risk",
};

export type RiskKey = "drought" | "fungal" | "heat";

export interface WeatherRisk {
  key: RiskKey;
  level: RiskLevel;
  /** Module 3's own explanation, shown as-is. */
  reason: string;
  status: Status;
}

/** The three Module 3 risks for one farm, worst first. */
export function weatherRisks(report: WeatherReport | null | undefined): WeatherRisk[] {
  if (!report) return [];
  const { riskAssessment: risk } = report;
  const risks: WeatherRisk[] = [
    { key: "drought", level: risk.droughtRisk, reason: risk.droughtReason, status: RISK_TO_STATUS[risk.droughtRisk] },
    { key: "fungal", level: risk.fungalDiseaseRisk, reason: risk.fungalDiseaseReason, status: RISK_TO_STATUS[risk.fungalDiseaseRisk] },
    { key: "heat", level: risk.heatStressRisk, reason: risk.heatStressReason, status: RISK_TO_STATUS[risk.heatStressRisk] },
  ];
  return risks
    .filter((item) => item.status)
    .sort((a, b) => STATUS_RANK[b.status] - STATUS_RANK[a.status]);
}
