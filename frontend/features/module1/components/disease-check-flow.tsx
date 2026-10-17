"use client";

import { AlertCircle, ImagePlus, Leaf, RotateCcw, Sparkles } from "lucide-react";
import { useMessages, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { UploadCard } from "@/features/predictions/components/upload-card";
import { labelFor } from "@/lib/i18n/labels";
import { useParseApiError } from "@/lib/i18n/use-api-error";
import type { Farm } from "@/features/farms/types";

import { useSubmitDiseaseCheck } from "../hooks";
import type { DiseaseCheckResult, SupportedCrop } from "../types";
import { CropSelect } from "./crop-select";
import { DiseaseCheckResults } from "./disease-check-results";

interface DiseaseCheckFlowProps {
  farm: Farm;
}

export function DiseaseCheckFlow({ farm }: DiseaseCheckFlowProps) {
  const t = useTranslations("disease.flow");
  const tUpload = useTranslations("upload");
  const tUnits = useTranslations("units");
  const messages = useMessages();
  const parseApiError = useParseApiError();
  const [image, setImage] = useState<{ file: File; previewUrl: string } | null>(null);
  const [crop, setCrop] = useState<SupportedCrop | undefined>(undefined);
  const [result, setResult] = useState<DiseaseCheckResult | null>(null);
  const submit = useSubmitDiseaseCheck(farm.farmId);

  useEffect(() => {
    return () => {
      if (image) URL.revokeObjectURL(image.previewUrl);
    };
  }, [image]);

  const reset = () => {
    if (image) URL.revokeObjectURL(image.previewUrl);
    setImage(null);
    setResult(null);
    submit.reset();
  };

  if (result) {
    return (
      <div className="flex flex-col gap-5">
        <DiseaseCheckResults result={result} farmName={farm.farmName} crop={crop} />
        <Button type="button" variant="outline" onClick={reset}>
          <RotateCcw className="size-4" />
          {t("checkAnother")}
        </Button>
      </div>
    );
  }

  if (submit.isPending) {
    return (
      <div className="flex flex-col items-center gap-4 rounded-2xl bg-card px-6 py-16 text-center shadow-[var(--shadow-color-md)]">
        <div className="flex size-16 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Spinner className="size-8" />
        </div>
        <div>
          <p className="font-heading text-xl font-bold text-foreground">{t("checkingTitle")}</p>
          <p className="mt-1 text-sm text-muted-foreground">{t("checkingDescription")}</p>
        </div>
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Sparkles className="size-3.5 text-primary" />
          {crop
            ? t("analyzingWithCrop", { crop: labelFor(messages.crops, crop) })
            : t("analyzingDetectedCrop")}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      <CropSelect value={crop} onChange={setCrop} />

      {!image && <UploadCard onImageReady={(file, previewUrl) => setImage({ file, previewUrl })} />}

      {image && (
        <div className="flex flex-col gap-5 rounded-2xl bg-card p-6 shadow-[var(--shadow-color-md)]">
          <div className="overflow-hidden rounded-2xl">
            {/* Object URLs aren't allowed by next/image's default loader. */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={image.previewUrl}
              alt={t("previewAlt")}
              className="max-h-96 w-full object-contain"
            />
          </div>
          <div className="flex items-center justify-between gap-3 text-sm text-muted-foreground">
            <span className="flex min-w-0 items-center gap-1.5">
              <Leaf className="size-4 shrink-0" />
              <span dir="auto" className="truncate">
                {image.file.name}
              </span>
            </span>
            <span className="shrink-0">
              {tUnits("megabytes", { value: (image.file.size / (1024 * 1024)).toFixed(2) })}
            </span>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                URL.revokeObjectURL(image.previewUrl);
                setImage(null);
                submit.reset();
              }}
            >
              <ImagePlus className="size-4" />
              {tUpload("changeImage")}
            </Button>
            <Button
              type="button"
              onClick={() =>
                submit.mutateAsync({ image: image.file, crop }).then(setResult).catch(() => {})
              }
            >
              {t("submit")}
            </Button>
          </div>
        </div>
      )}

      {submit.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{parseApiError(submit.error).message}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
