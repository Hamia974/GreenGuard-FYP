"use client";

import { CheckCircle2, MapPin } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { FarmLocation } from "@/features/farms/types";

import { LocationMapPreview } from "./location-map-preview";

interface LocationSummaryProps {
  location: FarmLocation;
  onChange: () => void;
  disabled: boolean;
}

/** The location the form will submit. Coordinates are shown read-only. */
export function LocationSummary({ location, onChange, disabled }: LocationSummaryProps) {
  const t = useTranslations("farms.form.location");
  const place = location.source === "device" ? t("currentLocation") : location.label;

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-success-border bg-success-bg p-3">
      <div className="flex flex-wrap items-start gap-2">
        <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success-icon" aria-hidden />
        <div className="flex min-w-0 flex-1 flex-col gap-0.5">
          <p className="text-sm font-semibold text-success-text">
            {location.source === "saved" ? t("saved") : t("found")}
          </p>
          {place && (
            <p className="flex items-start gap-1.5 text-sm text-foreground">
              <MapPin className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
              <span dir="auto">{place}</span>
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            {t("coordinates")}:{" "}
            <span dir="ltr">
              {location.latitude.toFixed(6)}, {location.longitude.toFixed(6)}
            </span>
          </p>
        </div>
        <Button type="button" variant="outline" size="sm" onClick={onChange} disabled={disabled}>
          {t("change")}
        </Button>
      </div>

      <LocationMapPreview
        latitude={location.latitude}
        longitude={location.longitude}
        title={t("mapPreview")}
      />
    </div>
  );
}
