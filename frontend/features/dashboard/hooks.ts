"use client";

import { useQuery } from "@tanstack/react-query";

import {
  fetchDashboardOverview,
  fetchDashboardRecommendations,
  fetchDashboardWeather,
  fetchRecentPredictions,
} from "./api";

export const dashboardOverviewQueryKey = ["dashboard", "overview"] as const;
export const dashboardWeatherQueryKey = (farmId?: string) =>
  ["dashboard", "weather", farmId ?? null] as const;
export const dashboardRecommendationsQueryKey = ["dashboard", "recommendations"] as const;
export const dashboardRecentPredictionsQueryKey = (limit: number) =>
  ["dashboard", "recent-predictions", limit] as const;

export function useDashboardOverview() {
  return useQuery({
    queryKey: dashboardOverviewQueryKey,
    queryFn: fetchDashboardOverview,
  });
}

export function useDashboardWeather(farmId?: string) {
  return useQuery({
    queryKey: dashboardWeatherQueryKey(farmId),
    queryFn: () => fetchDashboardWeather(farmId),
  });
}

export function useRecentPredictions(limit = 5) {
  return useQuery({
    queryKey: dashboardRecentPredictionsQueryKey(limit),
    queryFn: () => fetchRecentPredictions(limit),
  });
}

export function useDashboardRecommendations() {
  return useQuery({
    queryKey: dashboardRecommendationsQueryKey,
    queryFn: fetchDashboardRecommendations,
  });
}
