"use client";

import { AlertCircle, AlertTriangle, LocateFixed, Search } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { FieldError } from "@/components/ui/field-error";
import { Spinner } from "@/components/ui/spinner";
import { useGeocodeAddress } from "@/features/farms/hooks";
import { isLocationCurrent, normalizeAddress } from "@/features/farms/location";
import type { FarmLocation, GeocodeResult } from "@/features/farms/types";

import { LocationCandidates } from "./location-candidates";
import { LocationSummary } from "./location-summary";

export const FIND_LOCATION_BUTTON_ID = "find-farm-location";
const REQUIRED_ERROR_ID = "farm-location-error";

type LookupErrorKind = "notFound" | "service" | "gpsUnsupported" | "gpsUnavailable";

interface FarmLocationPickerProps {
  /** The address currently typed in the form. */
  address: string;
  location: FarmLocation | null;
  onLocationChange: (location: FarmLocation | null) => void;
  /** Runs the address field's validation (and shows its error); resolves false if invalid. */
  validateAddress: () => Promise<boolean>;
  focusAddress: () => void;
  disabled: boolean;
  /** True when a submit was attempted without valid coordinates for the current address. */
  showRequiredError: boolean;
}

export function FarmLocationPicker({
  address,
  location,
  onLocationChange,
  validateAddress,
  focusAddress,
  disabled,
  showRequiredError,
}: FarmLocationPickerProps) {
  const t = useTranslations("farms.form");
  const tLocation = useTranslations("farms.form.location");
  const tCommon = useTranslations("common");
  const locale = useLocale();
  const geocode = useGeocodeAddress();
  const lookupInFlight = useRef(false);

  // Results/errors remember the address they were produced for, so editing
  // the address hides them instead of leaving stale ones on screen.
  const [candidates, setCandidates] = useState<{ addressKey: string; results: GeocodeResult[] } | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [lookupError, setLookupError] = useState<{ kind: LookupErrorKind; addressKey: string } | null>(null);
  const [isLocating, setIsLocating] = useState(false);

  const addressKey = normalizeAddress(address);
  const locationIsCurrent = isLocationCurrent(location, address);
  const activeCandidates = candidates?.addressKey === addressKey ? candidates.results : null;
  const addressChanged = !activeCandidates && ((!!location && !locationIsCurrent) || !!candidates);
  const isBusy = disabled || geocode.isPending || isLocating;

  const visibleError =
    lookupError &&
    (lookupError.kind === "gpsUnsupported" ||
      lookupError.kind === "gpsUnavailable" ||
      lookupError.addressKey === addressKey)
      ? lookupError.kind
      : null;

  const handleFindLocation = async () => {
    if (lookupInFlight.current) return;
    lookupInFlight.current = true;
    try {
      if (!(await validateAddress())) {
        focusAddress();
        return;
      }
      const requestedKey = addressKey;
      setLookupError(null);
      setCandidates(null);
      setSelectedIndex(0);
      try {
        const results = await geocode.mutateAsync({ address: address.trim(), language: locale });
        if (results.length === 0) {
          setLookupError({ kind: "notFound", addressKey: requestedKey });
        } else {
          setCandidates({ addressKey: requestedKey, results });
        }
      } catch {
        setLookupError({ kind: "service", addressKey: requestedKey });
      }
    } finally {
      lookupInFlight.current = false;
    }
  };

  const handleConfirm = () => {
    if (!activeCandidates) return;
    const chosen = activeCandidates[selectedIndex] ?? activeCandidates[0];
    onLocationChange({ ...chosen, source: "address", addressKey });
    setCandidates(null);
  };

  const handleUseCurrentLocation = () => {
    if (!("geolocation" in navigator)) {
      setLookupError({ kind: "gpsUnsupported", addressKey });
      return;
    }
    setLookupError(null);
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        onLocationChange({
          latitude: Number(position.coords.latitude.toFixed(8)),
          longitude: Number(position.coords.longitude.toFixed(8)),
          label: null,
          source: "device",
          addressKey,
        });
        setCandidates(null);
        setIsLocating(false);
      },
      () => {
        setLookupError({ kind: "gpsUnavailable", addressKey });
        setIsLocating(false);
      }
    );
  };

  const handleChangeLocation = () => {
    onLocationChange(null);
    focusAddress();
  };

  const errorMessages: Record<LookupErrorKind, string> = {
    notFound: tLocation("notFound"),
    service: tLocation("serviceError"),
    gpsUnsupported: t("locationUnsupported"),
    gpsUnavailable: t("locationUnavailable"),
  };

  return (
    <section
      aria-labelledby="farm-location-title"
      className="flex flex-col gap-3 rounded-xl border border-border bg-muted/40 p-3 sm:p-4"
    >
      <div>
        <h2 id="farm-location-title" className="text-sm font-medium text-foreground">
          {tLocation("title")}
        </h2>
        <p className="mt-0.5 text-xs text-muted-foreground">{tLocation("hint")}</p>
      </div>

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <Button
          id={FIND_LOCATION_BUTTON_ID}
          type="button"
          onClick={handleFindLocation}
          disabled={isBusy}
          aria-busy={geocode.isPending}
          aria-describedby={showRequiredError ? REQUIRED_ERROR_ID : undefined}
          className="h-11 sm:flex-1"
        >
          {geocode.isPending ? <Spinner className="size-4" /> : <Search aria-hidden />}
          {geocode.isPending ? tLocation("finding") : tLocation("findLocation")}
        </Button>
        <span className="text-center text-xs text-muted-foreground" aria-hidden>
          {tLocation("or")}
        </span>
        <Button
          type="button"
          variant="outline"
          onClick={handleUseCurrentLocation}
          disabled={isBusy}
          aria-busy={isLocating}
          className="h-11 sm:flex-1"
        >
          {isLocating ? <Spinner className="size-4" /> : <LocateFixed aria-hidden />}
          {t("useCurrentLocation")}
        </Button>
      </div>

      <div aria-live="polite" className="flex flex-col gap-3 empty:hidden">
        {addressChanged && (
          <p className="flex items-start gap-2 rounded-lg border border-warning-border bg-warning-bg p-2.5 text-xs text-warning-text">
            <AlertTriangle className="mt-px size-4 shrink-0 text-warning-icon" aria-hidden />
            {tLocation("addressChanged")}
          </p>
        )}

        {visibleError && (
          <div
            role="alert"
            className="flex flex-wrap items-center gap-2 rounded-lg border border-error-border bg-error-bg p-2.5 text-xs text-error-text"
          >
            <AlertCircle className="size-4 shrink-0 text-error-icon" aria-hidden />
            <span className="min-w-0 flex-1">{errorMessages[visibleError]}</span>
            {visibleError === "service" && (
              <Button type="button" variant="outline" size="sm" onClick={handleFindLocation} disabled={isBusy}>
                {tCommon("tryAgain")}
              </Button>
            )}
          </div>
        )}

        {activeCandidates && (
          <LocationCandidates
            results={activeCandidates}
            selectedIndex={selectedIndex}
            onSelect={setSelectedIndex}
            onConfirm={handleConfirm}
            disabled={disabled}
          />
        )}

        {locationIsCurrent && !activeCandidates && (
          <LocationSummary location={location} onChange={handleChangeLocation} disabled={isBusy} />
        )}
      </div>

      {showRequiredError && (
        <div id={REQUIRED_ERROR_ID} role="alert">
          <FieldError message="locationRequired" />
        </div>
      )}
    </section>
  );
}
