"use client";

import { Check, MapPin } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { GeocodeResult } from "@/features/farms/types";

import { LocationMapPreview } from "./location-map-preview";

interface LocationCandidatesProps {
  results: GeocodeResult[];
  selectedIndex: number;
  onSelect: (index: number) => void;
  onConfirm: () => void;
  disabled: boolean;
}

function formatCoordinates({ latitude, longitude }: GeocodeResult) {
  return `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`;
}

/** Lookup results awaiting the farmer's confirmation -- never auto-selected. */
export function LocationCandidates({
  results,
  selectedIndex,
  onSelect,
  onConfirm,
  disabled,
}: LocationCandidatesProps) {
  const t = useTranslations("farms.form.location");
  const selected = results[selectedIndex] ?? results[0];
  const hasChoice = results.length > 1;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border bg-card p-3">
      <fieldset className="flex min-w-0 flex-col gap-2">
        <legend className="text-sm font-semibold text-foreground">
          {hasChoice ? t("multipleFound") : t("found")}
        </legend>
        <p className="text-xs text-muted-foreground">
          {hasChoice ? t("selectCorrect") : t("checkAndConfirm")}
        </p>

        {hasChoice ? (
          <div className="flex flex-col gap-2">
            {results.map((result, index) => (
              <label
                key={`${result.latitude},${result.longitude},${index}`}
                className="flex cursor-pointer items-start gap-2.5 rounded-lg border border-border p-2.5 transition-colors focus-within:ring-3 focus-within:ring-ring/50 has-[:checked]:border-primary has-[:checked]:bg-primary/5"
              >
                <input
                  type="radio"
                  name="farm-location-candidate"
                  className="mt-1 size-4 shrink-0 accent-[var(--primary)]"
                  checked={index === selectedIndex}
                  disabled={disabled}
                  onChange={() => onSelect(index)}
                />
                <span className="flex min-w-0 flex-col">
                  <span dir="auto" className="text-sm text-foreground">
                    {result.label}
                  </span>
                  <span dir="ltr" className="text-xs text-muted-foreground rtl:text-end">
                    {formatCoordinates(result)}
                  </span>
                </span>
              </label>
            ))}
          </div>
        ) : (
          <p className="flex items-start gap-1.5 text-sm text-foreground">
            <MapPin className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
            <span dir="auto">{selected.label}</span>
          </p>
        )}
      </fieldset>

      <LocationMapPreview
        latitude={selected.latitude}
        longitude={selected.longitude}
        title={t("mapPreview")}
      />

      <Button type="button" onClick={onConfirm} disabled={disabled} className="h-11">
        <Check aria-hidden />
        {t("confirm")}
      </Button>
    </div>
  );
}
