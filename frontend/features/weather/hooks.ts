"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { fetchCurrentWeather } from "./api";

export const currentWeatherQueryKey = (farmId?: string) =>
  ["weather", "current", farmId ?? null] as const;

export function useCurrentWeather(farmId?: string) {
  return useQuery({
    queryKey: currentWeatherQueryKey(farmId),
    queryFn: () => fetchCurrentWeather(farmId),
    enabled: !!farmId,
  });
}

/**
 * "Weather Test" — an explicit, farmer-triggered fetch (Dashboard action
 * card / /weather-test page) rather than the automatic query the Weather
 * Dashboard runs on page load. Calls the exact same `fetchCurrentWeather`
 * client against the same `GET /api/v1/weather/current/` endpoint — no
 * second weather API, no duplicated Weather Module logic — and seeds the
 * Weather Dashboard's query cache with the result so the two stay in sync.
 */
export function useWeatherTest(farmId?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => {
      if (!farmId) {
        throw new Error("No farm selected.");
      }
      return fetchCurrentWeather(farmId);
    },
    onSuccess: (data) => {
      queryClient.setQueryData(currentWeatherQueryKey(farmId), data);
    },
  });
}
