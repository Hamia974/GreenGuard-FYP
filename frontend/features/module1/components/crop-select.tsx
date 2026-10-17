"use client";

import { useMessages, useTranslations } from "next-intl";

import { labelFor } from "@/lib/i18n/labels";
import { cn } from "@/lib/utils";

import { SUPPORTED_CROPS, type SupportedCrop } from "../types";

interface CropSelectProps {
  value: SupportedCrop | undefined;
  onChange: (crop: SupportedCrop | undefined) => void;
}

/**
 * Crop picker for POST /api/v1/module1/analyze/'s optional `crop` field.
 * Per ai/API_CONTRACT.md: "Send it whenever the farmer has chosen one --
 * accuracy is materially worse without it," so this is a simple, always-
 * visible chip row rather than a hidden/advanced field. "Not sure" sends no
 * crop at all (the live service then infers `detected_crop` itself).
 */
export function CropSelect({ value, onChange }: CropSelectProps) {
  const t = useTranslations("disease.cropSelect");
  const messages = useMessages();

  return (
    <div role="group" aria-labelledby="crop-select-label" className="flex flex-col gap-2">
      <p id="crop-select-label" className="text-sm font-medium text-foreground">
        {t("question")}
      </p>
      <div className="flex flex-wrap gap-2">
        {SUPPORTED_CROPS.map((crop) => (
          <button
            key={crop}
            type="button"
            aria-pressed={value === crop}
            onClick={() => onChange(crop)}
            className={cn(
              "rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors",
              value === crop
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card text-foreground hover:bg-muted"
            )}
          >
            {labelFor(messages.crops, crop)}
          </button>
        ))}
        <button
          type="button"
          aria-pressed={value === undefined}
          onClick={() => onChange(undefined)}
          className={cn(
            "rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors",
            value === undefined
              ? "border-primary bg-primary text-primary-foreground"
              : "border-border bg-card text-foreground hover:bg-muted"
          )}
        >
          {t("notSure")}
        </button>
      </div>
    </div>
  );
}
