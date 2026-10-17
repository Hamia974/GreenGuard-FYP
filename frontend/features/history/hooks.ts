"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { deleteHistoryPrediction, fetchHistory } from "./api";
import type { HistoryQueryParams } from "./types";

const historyListRoot = ["history"] as const;
export const historyQueryKey = (params: Partial<HistoryQueryParams>) =>
  [...historyListRoot, params] as const;

export function useHistory(params: Partial<HistoryQueryParams>) {
  return useQuery({
    queryKey: historyQueryKey(params),
    queryFn: () => fetchHistory(params),
    placeholderData: keepPreviousData,
  });
}

export function useDeleteHistoryPrediction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (predictionId: string) => deleteHistoryPrediction(predictionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: historyListRoot });
    },
  });
}
