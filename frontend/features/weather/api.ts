import { apiClient } from "@/lib/api-client";

import type { RiskAssessment, WeatherReport } from "./types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data?: T;
}

interface RawRiskAssessment {
  fungal_disease_risk: string;
  fungal_disease_reason: string;
  heat_stress_risk: string;
  heat_stress_reason: string;
  drought_risk: string;
  drought_reason: string;
}

export interface RawWeatherReport {
  farm_id: string;
  timestamp: string;
  weather: {
    temperature: number;
    humidity: number;
    rainfall_last_7_days_mm: number;
    wind_speed: number;
  };
  units: {
    temperature: string;
    humidity: string;
    rainfall_last_7_days_mm: string;
    wind_speed: string;
  };
  risk_assessment: RawRiskAssessment;
  forecast: { temperature: number; humidity: number; rainfall_mm: number } | null;
  predicted_risk_assessment: RawRiskAssessment | null;
}

function mapRisk(raw: RawRiskAssessment): RiskAssessment {
  return {
    fungalDiseaseRisk: raw.fungal_disease_risk as RiskAssessment["fungalDiseaseRisk"],
    fungalDiseaseReason: raw.fungal_disease_reason,
    heatStressRisk: raw.heat_stress_risk as RiskAssessment["heatStressRisk"],
    heatStressReason: raw.heat_stress_reason,
    droughtRisk: raw.drought_risk as RiskAssessment["droughtRisk"],
    droughtReason: raw.drought_reason,
  };
}

export function mapWeatherReport(raw: RawWeatherReport): WeatherReport {
  return {
    farmId: raw.farm_id,
    timestamp: raw.timestamp,
    weather: {
      temperature: raw.weather.temperature,
      humidity: raw.weather.humidity,
      rainfallLast7DaysMm: raw.weather.rainfall_last_7_days_mm,
      windSpeed: raw.weather.wind_speed,
    },
    units: {
      temperature: raw.units.temperature,
      humidity: raw.units.humidity,
      rainfallLast7DaysMm: raw.units.rainfall_last_7_days_mm,
      windSpeed: raw.units.wind_speed,
    },
    riskAssessment: mapRisk(raw.risk_assessment),
    forecast: raw.forecast
      ? {
          temperature: raw.forecast.temperature,
          humidity: raw.forecast.humidity,
          rainfallMm: raw.forecast.rainfall_mm,
        }
      : null,
    predictedRiskAssessment: raw.predicted_risk_assessment
      ? mapRisk(raw.predicted_risk_assessment)
      : null,
  };
}

/**
 * GET /api/v1/weather/current/ -- the full Module 3 report for the Weather
 * page. Returns null when the user has no farm yet (matches the backend's
 * "Add a farm to see weather insights." empty state).
 */
export async function fetchCurrentWeather(farmId?: string): Promise<WeatherReport | null> {
  const { data } = await apiClient.get<ApiEnvelope<RawWeatherReport | null>>("/weather/current/", {
    params: farmId ? { farm_id: farmId } : undefined,
  });
  return data.data ? mapWeatherReport(data.data) : null;
}
