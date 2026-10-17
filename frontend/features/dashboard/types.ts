export interface WeatherSummary {
  temperature: number | null;
  humidity: number | null;
  rainfall: number | null;
  windSpeed: number | null;
  fungalDiseaseRisk: string | null;
  heatStressRisk: string | null;
  droughtRisk: string | null;
}

export interface FarmSummary {
  totalFarms: number;
}

export interface PredictionStatistics {
  healthyCount: number;
  diseasedCount: number;
  accuracy: number | null;
}

export interface DashboardOverview {
  welcomeMessage: string;
  totalPredictions: number;
  recentPredictions: number;
  notificationCount: number;
  weatherSummary: { temperature: number; humidity: number } | null;
  farmSummary: FarmSummary;
  predictionStatistics: PredictionStatistics;
}

export interface RecentPrediction {
  predictionId: string;
  /** Module 1's own disease result; null when Module 1 was uncertain. */
  diagnosis: string | null;
  /** Module 1's own confidence (0-1); null when Module 1 was uncertain. */
  confidence: number | null;
  createdAt: string;
}
