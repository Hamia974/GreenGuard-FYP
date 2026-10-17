"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FieldError } from "@/components/ui/field-error";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { Textarea } from "@/components/ui/textarea";
import { isLocationCurrent, normalizeAddress } from "@/features/farms/location";
import { coordinatesSchema, type FarmFormValues, farmSchema } from "@/features/farms/schemas";
import type { Farm, FarmLocation, FarmPayload } from "@/features/farms/types";
import { useParseApiError } from "@/lib/i18n/use-api-error";

import { FarmLocationPicker, FIND_LOCATION_BUTTON_ID } from "./farm-location-picker";

interface FarmFormProps {
  farm?: Farm;
  onSubmit: (values: FarmPayload) => Promise<void>;
  submitLabel: string;
  submittingLabel: string;
}

/** An existing farm's coordinates stay valid until its address is edited. */
function savedLocation(farm?: Farm): FarmLocation | null {
  if (!farm) return null;
  return {
    latitude: farm.latitude,
    longitude: farm.longitude,
    label: null,
    source: "saved",
    addressKey: normalizeAddress(farm.address),
  };
}

export function FarmForm({ farm, onSubmit, submitLabel, submittingLabel }: FarmFormProps) {
  const t = useTranslations("farms.form");
  const parseApiError = useParseApiError();
  const [formError, setFormError] = useState<string | null>(null);
  const [location, setLocation] = useState<FarmLocation | null>(() => savedLocation(farm));
  const [submitAttempted, setSubmitAttempted] = useState(false);

  const {
    register,
    control,
    handleSubmit,
    trigger,
    setFocus,
    formState: { errors, isSubmitting },
  } = useForm<FarmFormValues>({
    resolver: zodResolver(farmSchema),
    defaultValues: {
      farmName: farm?.farmName ?? "",
      address: farm?.address ?? "",
    },
  });
  const address = useWatch({ control, name: "address" }) ?? "";

  // Only coordinates confirmed for the address as it is NOW are submitted --
  // a location found for an earlier version of the address never is.
  const currentCoordinates = isLocationCurrent(location, address)
    ? coordinatesSchema.safeParse({ latitude: location.latitude, longitude: location.longitude })
    : null;

  const submit = async (values: FarmFormValues) => {
    setFormError(null);
    if (!currentCoordinates?.success) {
      document.getElementById(FIND_LOCATION_BUTTON_ID)?.focus();
      return;
    }
    try {
      await onSubmit({ ...values, ...currentCoordinates.data });
    } catch (error) {
      setFormError(parseApiError(error).message);
    }
  };

  return (
    <form
      onSubmit={(event) => {
        setSubmitAttempted(true);
        return handleSubmit(submit)(event);
      }}
      noValidate
      className="flex flex-col gap-5"
    >
      {formError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="farmName">{t("farmName")}</Label>
        <Input
          id="farmName"
          placeholder={t("farmNamePlaceholder")}
          aria-invalid={!!errors.farmName}
          disabled={isSubmitting}
          className="h-11 rounded-[var(--radius-input)]"
          {...register("farmName")}
        />
        <FieldError message={errors.farmName?.message} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="address">{t("address")}</Label>
        <Textarea
          id="address"
          placeholder={t("addressPlaceholder")}
          rows={3}
          aria-invalid={!!errors.address}
          disabled={isSubmitting}
          {...register("address")}
        />
        <FieldError message={errors.address?.message} />
      </div>

      <FarmLocationPicker
        address={address}
        location={location}
        onLocationChange={setLocation}
        validateAddress={() => trigger("address")}
        focusAddress={() => setFocus("address")}
        disabled={isSubmitting}
        showRequiredError={submitAttempted && !currentCoordinates?.success}
      />

      <Button
        type="submit"
        disabled={isSubmitting}
        className="h-[52px] rounded-2xl text-base font-semibold shadow-[var(--shadow-color-sm)] transition-transform hover:-translate-y-0.5 hover:shadow-[var(--shadow-color-hover)]"
      >
        {isSubmitting ? (
          <>
            <Spinner /> {submittingLabel}
          </>
        ) : (
          submitLabel
        )}
      </Button>
    </form>
  );
}
