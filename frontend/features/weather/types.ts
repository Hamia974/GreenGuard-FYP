export type RiskLevel = "Low" | "Moderate" | "High";

export interface RiskAssessment {
  fungalDiseaseRisk: RiskLevel;
  fungalDiseaseReason: string;
  heatStressRisk: RiskLevel;
  heatStressReason: string;
  droughtRisk: RiskLevel;
  droughtReason: string;
}

export interface CurrentWeather {
  temperature: number;
  humidity: number;
  rainfallLast7DaysMm: number;
  windSpeed: number;
}

export interface WeatherUnits {
  temperature: string;
  humidity: string;
  rainfallLast7DaysMm: string;
  windSpeed: string;
}

/** Single day ahead only -- the Weather Module's LSTM add-on has no
 * multi-day or hourly forecast horizon. */
export interface NextDayForecast {
  temperature: number;
  humidity: number;
  rainfallMm: number;
}

/**
 * Full Module 3 (Weather Risk Engine) report, per the real ai/Weather_Module
 * contract (REST_API_SPEC.md section 5A). `forecast` and
 * `predictedRiskAssessment` are best-effort LSTM add-ons and are legitimately
 * `null` -- never treat a null as "no risk" or backfill a fabricated value.
 */
export interface WeatherReport {
  farmId: string;
  timestamp: string;
  weather: CurrentWeather;
  units: WeatherUnits;
  riskAssessment: RiskAssessment;
  forecast: NextDayForecast | null;
  predictedRiskAssessment: RiskAssessment | null;
}
