"use client";

import { AlertCircle, ImagePlus, Leaf, Sparkles } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import type { Farm } from "@/features/farms/types";
import { CropSelect } from "@/features/module1/components/crop-select";
import type { SupportedCrop } from "@/features/module1/types";
import { useParseApiError } from "@/lib/i18n/use-api-error";

import { useAnalyzePrediction } from "../hooks";
import type { Prediction } from "../types";
import { UploadCard } from "./upload-card";

// Purely descriptive of what the single synchronous POST /predictions/analyze/
// call does server-side (see PredictionAnalyzeView) -- not a real progress
// signal, since the backend has none. Per UI_SPECIFICATION.md 11.20 ("Never
// use fake loading") this deliberately does NOT fabricate per-stage timing
// or percentages; it is one honest in-flight state that stays up for as
// long as the real request takes.
// Stage wording lives in messages/<locale>/quickScan.json (processing.stages).
const PROCESSING_STAGES = ["module1", "module2", "module3"] as const;

interface QuickScanFlowProps {
  farm: Farm;
  onComplete: (prediction: Prediction) => void;
}

export function QuickScanFlow({ farm, onComplete }: QuickScanFlowProps) {
  const t = useTranslations("quickScan");
  const tUpload = useTranslations("upload");
  const tUnits = useTranslations("units");
  const parseApiError = useParseApiError();
  const [image, setImage] = useState<{ file: File; previewUrl: string } | null>(null);
  const [crop, setCrop] = useState<SupportedCrop | undefined>(undefined);
  const analyze = useAnalyzePrediction(farm.farmId);

  useEffect(() => {
    return () => {
      if (image) URL.revokeObjectURL(image.previewUrl);
    };
  }, [image]);

  if (analyze.isPending) {
    return (
      <div className="flex flex-col items-center gap-6 rounded-2xl bg-card px-6 py-16 text-center shadow-[var(--shadow-color-md)]">
        <div className="flex size-16 items-center justify-center rounded-full bg-primary/10 text-primary">
          <Spinner className="size-8" />
        </div>
        <div>
          <p className="font-heading text-xl font-bold text-foreground">{t("processing.title")}</p>
          <p className="mt-1 text-sm text-muted-foreground">{t("processing.description")}</p>
        </div>
        <ul className="flex flex-col gap-2 text-start">
          {PROCESSING_STAGES.map((stage) => (
            <li key={stage} className="flex items-center gap-2 text-sm text-muted-foreground">
              <Sparkles className="size-4 shrink-0 text-primary" />
              {t(`processing.stages.${stage}`)}
            </li>
          ))}
        </ul>
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
                analyze.reset();
              }}
            >
              <ImagePlus className="size-4" />
              {tUpload("changeImage")}
            </Button>
            <Button
              type="button"
              onClick={() =>
                analyze.mutateAsync({ image: image.file, crop }).then(onComplete).catch(() => {})
              }
            >
              {t("submit")}
            </Button>
          </div>
        </div>
      )}

      {analyze.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{parseApiError(analyze.error).message}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
