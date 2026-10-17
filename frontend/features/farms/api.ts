import { apiClient } from "@/lib/api-client";

import type { Farm, FarmPayload, GeocodeResult } from "./types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data?: T;
}

interface RawFarm {
  farm_id: string;
  farm_name: string;
  address: string;
  latitude: number | string;
  longitude: number | string;
  created_at: string;
  updated_at: string;
}

function mapFarm(raw: RawFarm): Farm {
  return {
    farmId: raw.farm_id,
    farmName: raw.farm_name,
    address: raw.address,
    latitude: Number(raw.latitude),
    longitude: Number(raw.longitude),
    createdAt: raw.created_at,
    updatedAt: raw.updated_at,
  };
}

function toRequestBody(payload: FarmPayload) {
  return {
    farm_name: payload.farmName,
    address: payload.address,
    latitude: payload.latitude,
    longitude: payload.longitude,
  };
}

export async function fetchFarms(): Promise<Farm[]> {
  const { data } = await apiClient.get<ApiEnvelope<RawFarm[]>>("/farms/");
  return (data.data ?? []).map(mapFarm);
}

export async function fetchFarm(farmId: string): Promise<Farm> {
  const { data } = await apiClient.get<ApiEnvelope<RawFarm>>(`/farms/${farmId}/`);
  return mapFarm(data.data as RawFarm);
}

export async function createFarm(payload: FarmPayload): Promise<Farm> {
  const { data } = await apiClient.post<ApiEnvelope<RawFarm>>(
    "/farms/",
    toRequestBody(payload)
  );
  return mapFarm(data.data as RawFarm);
}

export async function updateFarm(farmId: string, payload: FarmPayload): Promise<Farm> {
  const { data } = await apiClient.put<ApiEnvelope<RawFarm>>(
    `/farms/${farmId}/`,
    toRequestBody(payload)
  );
  return mapFarm(data.data as RawFarm);
}

export async function deleteFarm(farmId: string): Promise<void> {
  await apiClient.delete(`/farms/${farmId}/`);
}

/** Address -> candidate coordinates, looked up by the backend (provider keys stay server-side). */
export async function geocodeAddress(address: string, language: string): Promise<GeocodeResult[]> {
  const { data } = await apiClient.post<ApiEnvelope<{ results: GeocodeResult[] }>>(
    "/farms/geocode/",
    { address, language }
  );
  return data.data?.results ?? [];
}
