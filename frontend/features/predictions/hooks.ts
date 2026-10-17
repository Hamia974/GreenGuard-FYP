"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { analyzePrediction, fetchPrediction } from "./api";
import type { Prediction } from "./types";

export const predictionQueryKey = (predictionId: string) => ["predictions", predictionId] as const;

interface AnalyzeInput {
  image: File;
  crop?: string;
}

export function useAnalyzePrediction(farmId: string | undefined) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ image, crop }: AnalyzeInput) => {
      if (!farmId) {
        return Promise.reject(new Error("No farm selected."));
      }
      return analyzePrediction(farmId, image, crop);
    },
    onSuccess: (prediction: Prediction) => {
      queryClient.setQueryData(predictionQueryKey(prediction.predictionId), prediction);
      // A new analysis changes the History list and the dashboard counts.
      queryClient.invalidateQueries({ queryKey: ["history"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function usePrediction(predictionId: string | undefined) {
  return useQuery({
    queryKey: predictionQueryKey(predictionId ?? ""),
    queryFn: () => fetchPrediction(predictionId as string),
    enabled: !!predictionId,
  });
}
