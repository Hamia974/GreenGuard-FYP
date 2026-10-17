"use client";

import { useTranslations } from "next-intl";

import type { ValidationKey } from "@/lib/i18n/validation";
import { cn } from "@/lib/utils";

/**
 * Renders a form field's error. Client-side zod errors carry a
 * validation.json key and are translated here; server-side field errors
 * (already human text from the API) are shown unchanged.
 */
export function FieldError({ message, className }: { message?: string; className?: string }) {
  const t = useTranslations("validation");
  if (!message) return null;

  const key = message as ValidationKey;
  return <p className={cn("text-xs text-error-text", className)}>{t.has(key) ? t(key) : message}</p>;
}
