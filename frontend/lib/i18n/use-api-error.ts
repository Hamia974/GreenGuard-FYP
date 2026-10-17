"use client";

import { useTranslations } from "next-intl";
import { useCallback } from "react";

import { parseApiError } from "@/lib/api-error";

/**
 * Localized wrapper around parseApiError: the generic "something went
 * wrong" / "can't reach the server" fallbacks render in the active
 * language. A message the backend itself returned is shown as-is (the API
 * contract is not changed for localization).
 */
export function useParseApiError() {
  const t = useTranslations("errors");
  return useCallback(
    (error: unknown) => parseApiError(error, {
        generic: t("generic"),
        network: t("network"),
        rateLimited: t("rateLimited"),
      }),
    [t]
  );
}
