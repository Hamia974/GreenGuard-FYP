"use client";

import { useMutation } from "@tanstack/react-query";

import { submitDiseaseCheck } from "./api";

interface SubmitDiseaseCheckInput {
  image: File;
  crop?: string;
}

export function useSubmitDiseaseCheck(farmId: string | undefined) {
  return useMutation({
    mutationFn: ({ image, crop }: SubmitDiseaseCheckInput) => {
      if (!farmId) {
        return Promise.reject(new Error("No farm selected."));
      }
      return submitDiseaseCheck(farmId, image, crop);
    },
  });
}
