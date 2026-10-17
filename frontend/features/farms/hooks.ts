"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { createFarm, deleteFarm, fetchFarm, fetchFarms, geocodeAddress, updateFarm } from "./api";
import type { FarmPayload } from "./types";

export const farmsQueryKey = ["farms"] as const;
export const farmQueryKey = (farmId: string) => ["farms", farmId] as const;

export function useFarms() {
  return useQuery({ queryKey: farmsQueryKey, queryFn: fetchFarms });
}

export function useFarm(farmId: string | undefined) {
  return useQuery({
    queryKey: farmQueryKey(farmId ?? ""),
    queryFn: () => fetchFarm(farmId as string),
    enabled: !!farmId,
  });
}

export function useCreateFarm() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: FarmPayload) => createFarm(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: farmsQueryKey });
    },
  });
}

export function useUpdateFarm(farmId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: FarmPayload) => updateFarm(farmId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: farmsQueryKey });
      queryClient.invalidateQueries({ queryKey: farmQueryKey(farmId) });
    },
  });
}

export function useDeleteFarm() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (farmId: string) => deleteFarm(farmId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: farmsQueryKey });
    },
  });
}

export function useGeocodeAddress() {
  return useMutation({
    mutationFn: ({ address, language }: { address: string; language: string }) =>
      geocodeAddress(address, language),
  });
}
