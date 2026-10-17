"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, ArrowLeft, ArrowRight, CloudSun } from "lucide-react";
import { useMessages, useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import { type FieldError, useForm } from "react-hook-form";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FieldError as FieldErrorText } from "@/components/ui/field-error";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import type { Farm } from "@/features/farms/types";
import { labelFor } from "@/lib/i18n/labels";
import { useParseApiError } from "@/lib/i18n/use-api-error";

import {
  CROP_VALUES,
  DAYS_SINCE_FERTILIZER_VALUES,
  FERTILIZER_TYPE_VALUES,
  GROWTH_STAGE_VALUES,
  IRRIGATION_ADEQUACY_VALUES,
  IRRIGATION_SOURCE_VALUES,
  NOT_APPLICABLE_VALUE,
  NO_FERTILIZER_VALUE,
  SOIL_TYPE_VALUES,
  cropImageSrc,
  defaultSymptoms,
  irrigationSourceImageSrc,
  soilTypeImageSrc,
} from "../field-options";
import { type Module2FormValues, module2Schema } from "../schemas";
import type { Module2Result } from "../types";
import { type Option, OptionGrid } from "./option-grid";
import { SymptomChecklist } from "./symptom-checklist";

type LabelMap = Readonly<Record<string, string>>;

/** Builds option buttons from the raw API values. Labels come from the active
 * locale's messages (falling back to the raw value); the raw value is what
 * gets submitted. */
function toOptions(
  values: string[],
  labels: LabelMap,
  hints?: LabelMap,
  images?: (value: string) => string
): Option[] {
  return values.map((value) => ({
    value,
    label: labelFor(labels, value),
    hint: hints ? labelFor(hints, value, "") || undefined : undefined,
    imageSrc: images?.(value),
  }));
}

const STEP_COUNT = 7;

const STEP_FIELDS: Record<number, (keyof Module2FormValues)[]> = {
  1: ["crop", "growthStage"],
  2: ["soilType"],
  3: ["lastFertilizerType", "daysSinceFertilizer"],
  4: ["irrigationSource", "irrigationAdequacy"],
  5: ["symptoms"],
  6: [],
  7: ["phValue", "soilMoisturePct", "lightIntensityLux"],
};

/** Meter readings (Step 7) are required -- an empty string becomes `undefined`
 * so the zod schema's `required_error` fires instead of silently passing `NaN`
 * or `null` through to the API (module2_field_options.json: ph_value /
 * soil_moisture_pct / light_intensity_lux are all `"required": true`). */
function parseRequiredNumber(raw: string): number | undefined {
  return raw === "" ? undefined : Number(raw);
}

interface Module2WizardProps {
  farm: Farm;
  onSubmit: (values: Module2FormValues) => Promise<Module2Result>;
  onComplete: (result: Module2Result) => void;
}

/** 7-step Soil & Nutrient Health questionnaire, per UI_SPECIFICATION.md
 * Chapter 12A and Module2_Frontend_Form_Spec.md. Weather (step 6) is
 * resolved automatically server-side -- never collected here. */
export function Module2Wizard({ farm, onSubmit, onComplete }: Module2WizardProps) {
  const t = useTranslations("soil.wizard");
  const tCommon = useTranslations("common");
  const messages = useMessages();
  const parseApiError = useParseApiError();
  const [step, setStep] = useState(1);

  const options = useMemo(() => {
    const labels = messages.soil.options;
    return {
      crop: toOptions(CROP_VALUES, messages.crops, undefined, cropImageSrc),
      growthStage: toOptions(GROWTH_STAGE_VALUES, labels.growthStage),
      soilType: toOptions(SOIL_TYPE_VALUES, labels.soilType, labels.soilTypeHint, soilTypeImageSrc),
      lastFertilizerType: toOptions(FERTILIZER_TYPE_VALUES, labels.lastFertilizerType),
      daysSinceFertilizer: toOptions(
        DAYS_SINCE_FERTILIZER_VALUES.filter((value) => value !== NOT_APPLICABLE_VALUE),
        labels.daysSinceFertilizer
      ),
      irrigationSource: toOptions(
        IRRIGATION_SOURCE_VALUES,
        labels.irrigationSource,
        undefined,
        irrigationSourceImageSrc
      ),
      irrigationAdequacy: toOptions(IRRIGATION_ADEQUACY_VALUES, labels.irrigationAdequacy),
    };
  }, [messages]);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    watch,
    setValue,
    trigger,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Module2FormValues>({
    resolver: zodResolver(module2Schema),
    defaultValues: {
      symptoms: defaultSymptoms(),
    },
  });

  const values = watch();
  const isNoFertilizer = values.lastFertilizerType === NO_FERTILIZER_VALUE;
  const symptomsError = errors.symptoms as unknown as FieldError | undefined;

  const goNext = async () => {
    const fields = STEP_FIELDS[step];
    const valid = fields.length === 0 || (await trigger(fields));
    if (!valid) return;
    setStep((current) => Math.min(current + 1, STEP_COUNT));
  };

  const goBack = () => setStep((current) => Math.max(current - 1, 1));

  const submit = async (formValues: Module2FormValues) => {
    setFormError(null);
    try {
      const result = await onSubmit(formValues);
      onComplete(result);
    } catch (error) {
      setFormError(parseApiError(error).message);
    }
  };

  return (
    <form onSubmit={handleSubmit(submit)} noValidate className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{t("stepOf", { step, total: STEP_COUNT })}</span>
          <span dir="auto">{farm.farmName}</span>
        </div>
        <Progress value={(step / STEP_COUNT) * 100} />
      </div>

      {formError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      {step === 1 && (
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <Label>{t("questions.crop")}</Label>
            <OptionGrid
              options={options.crop}
              value={values.crop}
              onChange={(value) => setValue("crop", value, { shouldValidate: true })}
              columns="sm:grid-cols-3"
            />
            <FieldErrorText message={errors.crop?.message} />
          </div>

          <div className="flex flex-col gap-2">
            <Label>{t("questions.growthStage")}</Label>
            <OptionGrid
              options={options.growthStage}
              value={values.growthStage}
              onChange={(value) => setValue("growthStage", value, { shouldValidate: true })}
            />
            <FieldErrorText message={errors.growthStage?.message} />
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="flex flex-col gap-2">
          <Label>{t("questions.soilType")}</Label>
          <OptionGrid
            options={options.soilType}
            value={values.soilType}
            onChange={(value) => setValue("soilType", value, { shouldValidate: true })}
            columns="sm:grid-cols-3"
          />
          <FieldErrorText message={errors.soilType?.message} />
        </div>
      )}

      {step === 3 && (
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <Label>{t("questions.lastFertilizerType")}</Label>
            <OptionGrid
              options={options.lastFertilizerType}
              value={values.lastFertilizerType}
              onChange={(value) => {
                setValue("lastFertilizerType", value, { shouldValidate: true });
                if (value === NO_FERTILIZER_VALUE) {
                  setValue("daysSinceFertilizer", NOT_APPLICABLE_VALUE, { shouldValidate: true });
                } else if (values.daysSinceFertilizer === NOT_APPLICABLE_VALUE) {
                  setValue("daysSinceFertilizer", "" as never, { shouldValidate: false });
                }
              }}
            />
            <FieldErrorText message={errors.lastFertilizerType?.message} />
          </div>

          {!isNoFertilizer && (
            <div className="flex flex-col gap-2">
              <Label>{t("questions.daysSinceFertilizer")}</Label>
              <OptionGrid
                options={options.daysSinceFertilizer}
                value={values.daysSinceFertilizer}
                onChange={(value) => setValue("daysSinceFertilizer", value, { shouldValidate: true })}
              />
              <FieldErrorText message={errors.daysSinceFertilizer?.message} />
            </div>
          )}
        </div>
      )}

      {step === 4 && (
        <div className="flex flex-col gap-5">
          <div className="flex flex-col gap-2">
            <Label>{t("questions.irrigationSource")}</Label>
            <OptionGrid
              options={options.irrigationSource}
              value={values.irrigationSource}
              onChange={(value) => setValue("irrigationSource", value, { shouldValidate: true })}
              columns="sm:grid-cols-3"
            />
            <FieldErrorText message={errors.irrigationSource?.message} />
          </div>

          <div className="flex flex-col gap-2">
            <Label>{t("questions.irrigationAdequacy")}</Label>
            <OptionGrid
              options={options.irrigationAdequacy}
              value={values.irrigationAdequacy}
              onChange={(value) => setValue("irrigationAdequacy", value, { shouldValidate: true })}
              columns="sm:grid-cols-1"
            />
            <FieldErrorText message={errors.irrigationAdequacy?.message} />
          </div>
        </div>
      )}

      {step === 5 && (
        <div className="flex flex-col gap-2">
          <Label>{t("questions.symptoms")}</Label>
          <p className="text-xs text-muted-foreground">{t("symptomsHint")}</p>
          <SymptomChecklist
            value={values.symptoms ?? defaultSymptoms()}
            onChange={(next) => setValue("symptoms", next, { shouldValidate: true })}
          />
          <FieldErrorText message={symptomsError?.message} />
        </div>
      )}

      {step === 6 && (
        <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-muted/40 px-4 py-8 text-center">
          <CloudSun className="size-8 text-primary" />
          <p className="text-sm font-medium text-foreground">
            {t("weatherStep.title", { farm: farm.farmName })}
          </p>
          <p className="max-w-xs text-xs text-muted-foreground">{t("weatherStep.description")}</p>
        </div>
      )}

      {step === 7 && (
        <div className="flex flex-col gap-5">
          <p className="text-xs text-muted-foreground">{t("meterStep.intro")}</p>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="phValue">{t("meterStep.ph")}</Label>
            <Input
              id="phValue"
              type="number"
              step="any"
              placeholder={t("meterStep.phPlaceholder")}
              dir="ltr"
              {...register("phValue", { setValueAs: parseRequiredNumber })}
            />
            <FieldErrorText message={errors.phValue?.message} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="soilMoisturePct">{t("meterStep.soilMoisture")}</Label>
            <Input
              id="soilMoisturePct"
              type="number"
              step="any"
              placeholder={t("meterStep.soilMoisturePlaceholder")}
              dir="ltr"
              {...register("soilMoisturePct", { setValueAs: parseRequiredNumber })}
            />
            <FieldErrorText message={errors.soilMoisturePct?.message} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="lightIntensityLux">{t("meterStep.light")}</Label>
            <Input
              id="lightIntensityLux"
              type="number"
              step="any"
              placeholder={t("meterStep.lightPlaceholder")}
              dir="ltr"
              {...register("lightIntensityLux", { setValueAs: parseRequiredNumber })}
            />
            <FieldErrorText message={errors.lightIntensityLux?.message} />
          </div>
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={goBack}
          disabled={step === 1 || isSubmitting}
        >
          <ArrowLeft className="size-4 rtl:-scale-x-100" />
          {tCommon("back")}
        </Button>

        {step < STEP_COUNT ? (
          <Button type="button" onClick={goNext}>
            {tCommon("next")}
            <ArrowRight className="size-4 rtl:-scale-x-100" />
          </Button>
        ) : (
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Spinner /> {t("analyzing")}
              </>
            ) : (
              t("submit")
            )}
          </Button>
        )}
      </div>
    </form>
  );
}
