"use client";

import { useMutation } from "@tanstack/react-query";

import { submitModule2Analysis } from "./api";
import type { Module2FormValues } from "./schemas";

export function useSubmitModule2Analysis(farmId: string | undefined) {
  return useMutation({
    mutationFn: (values: Module2FormValues) => {
      if (!farmId) {
        return Promise.reject(new Error("No farm selected."));
      }
      return submitModule2Analysis(farmId, values);
    },
  });
}
