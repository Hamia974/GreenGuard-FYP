import { apiClient } from "@/lib/api-client";

import type { DashboardOverview, RecentPrediction, WeatherSummary } from "./types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data?: T;
}

interface RawDashboardOverview {
  welcome_message: string;
  total_predictions: number;
  recent_predictions: number;
  notification_count: number;
  weather_summary: { temperature: number; humidity: number } | null;
  farm_summary: { total_farms: number };
  prediction_statistics: {
    healthy_count: number;
    diseased_count: number;
    accuracy: number | null;
  };
}

interface RawWeatherSummary {
  temperature: number | null;
  humidity: number | null;
  rainfall: number | null;
  wind_speed: number | null;
  fungal_disease_risk: string | null;
  heat_stress_risk: string | null;
  drought_risk: string | null;
}

interface RawRecentPrediction {
  prediction_id: string;
  diagnosis: string | null;
  confidence: number | null;
  created_at: string;
}

function mapOverview(raw: RawDashboardOverview): DashboardOverview {
  return {
    welcomeMessage: raw.welcome_message,
    totalPredictions: raw.total_predictions,
    recentPredictions: raw.recent_predictions,
    notificationCount: raw.notification_count,
    weatherSummary: raw.weather_summary,
    farmSummary: { totalFarms: raw.farm_summary.total_farms },
    predictionStatistics: {
      healthyCount: raw.prediction_statistics.healthy_count,
      diseasedCount: raw.prediction_statistics.diseased_count,
      accuracy: raw.prediction_statistics.accuracy,
    },
  };
}

function mapWeather(raw: RawWeatherSummary): WeatherSummary {
  return {
    temperature: raw.temperature,
    humidity: raw.humidity,
    rainfall: raw.rainfall,
    windSpeed: raw.wind_speed,
    fungalDiseaseRisk: raw.fungal_disease_risk,
    heatStressRisk: raw.heat_stress_risk,
    droughtRisk: raw.drought_risk,
  };
}

function mapPrediction(raw: RawRecentPrediction): RecentPrediction {
  return {
    predictionId: raw.prediction_id,
    diagnosis: raw.diagnosis,
    confidence: raw.confidence,
    createdAt: raw.created_at,
  };
}

export async function fetchDashboardOverview(): Promise<DashboardOverview> {
  const { data } = await apiClient.get<ApiEnvelope<RawDashboardOverview>>("/dashboard/");
  return mapOverview(data.data as RawDashboardOverview);
}

export async function fetchDashboardWeather(farmId?: string): Promise<WeatherSummary> {
  const { data } = await apiClient.get<ApiEnvelope<RawWeatherSummary>>("/dashboard/weather/", {
    params: farmId ? { farm_id: farmId } : undefined,
  });
  return mapWeather(data.data as RawWeatherSummary);
}

export async function fetchRecentPredictions(limit = 5): Promise<RecentPrediction[]> {
  const { data } = await apiClient.get<ApiEnvelope<RawRecentPrediction[]>>(
    "/dashboard/recent-predictions/",
    { params: { limit } }
  );
  return (data.data ?? []).map(mapPrediction);
}

export async function fetchDashboardRecommendations(): Promise<string[]> {
  const { data } = await apiClient.get<ApiEnvelope<string[]>>("/dashboard/recommendations/");
  return data.data ?? [];
}
