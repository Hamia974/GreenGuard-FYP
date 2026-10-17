"use client";

import { AlertTriangle, HelpCircle, Info } from "lucide-react";
import { useMessages, useTranslations } from "next-intl";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { labelFor } from "@/lib/i18n/labels";
import { cn } from "@/lib/utils";

import type { DiseaseCheckResult, DiseasePredictionItem, SupportedCrop } from "../types";
import { DiseaseName } from "./disease-name";

// Farmer-facing wording for the API's warning codes (ai/API_CONTRACT.md:
// BLURRY_IMAGE, LOW_LIGHT, OVEREXPOSED, CROP_MISMATCH) lives in
// messages/<locale>/disease.json under "warnings"; unknown codes show verbatim.

/** 0.8812 -> "88.12" (shown as 88.12% / ٪). Formatting only -- the raw API confidence is never recalculated. */
function confidencePercent(confidence: number): string {
  return (confidence * 100).toFixed(2);
}

function HealthBadge({ isHealthy }: { isHealthy: boolean }) {
  const t = useTranslations("disease.health");
  return (
    <span
      className={cn(
        "shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold",
        isHealthy ? "bg-success-icon/10 text-success-icon" : "bg-error-icon/10 text-error-icon"
      )}
    >
      {isHealthy ? t("healthy") : t("unhealthy")}
    </span>
  );
}

function ResultRow({ item }: { item: DiseasePredictionItem }) {
  const tUnits = useTranslations("units");
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card px-3 py-2.5 text-sm">
      <span className="font-medium text-foreground">
        <DiseaseName displayName={item.displayName} disease={item.disease} />
      </span>
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">
          {tUnits("percent", { value: confidencePercent(item.confidence) })}
        </span>
        <HealthBadge isHealthy={item.isHealthy} />
      </div>
    </div>
  );
}

interface DiseaseCheckResultsProps {
  result: DiseaseCheckResult;
  /** Shown as a Farm/Crop line above the result; omitted when the host page already shows it. */
  farmName?: string;
  crop?: SupportedCrop;
}

/**
 * Renders POST /api/v1/module1/analyze/'s result, per ai/API_CONTRACT.md
 * sections 5-9:
 *
 * - status "ok": `prediction` is the primary result; the OTHER top3 entries
 *   (filtered by stable class_id, never by display_name) are shown as
 *   "Closely related" -- the main prediction is never duplicated there.
 * - status "uncertain": `prediction` is null and never invented; ALL of
 *   top3 is shown as "Possible results" instead. top3 is rendered on every
 *   response either way -- never hidden because status is "uncertain".
 */
export function DiseaseCheckResults({ result, farmName, crop }: DiseaseCheckResultsProps) {
  const t = useTranslations("disease.results");
  const tUnits = useTranslations("units");
  const messages = useMessages();
  const { prediction, top3 } = result;
  const cropLabel = crop ? labelFor(messages.crops, crop) : t("cropNotSpecified");

  const closelyRelated = prediction
    ? top3.filter((item) => item.classId !== prediction.classId)
    : [];
  // farm_id is echoed by Module 1 exactly as the backend sent it (the farm's id),
  // and is null only when none was sent -- nothing is shown then.
  const farmId = result.farmId?.trim() || null;
  const message = result.message?.trim() || null;
  const warnings = result.warnings.filter((code) => code.trim() !== "");

  return (
    <div className="flex flex-col gap-4">
      {farmName && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
          <span>
            {t.rich("farm", {
              value: farmName,
              strong: (chunks) => <span className="font-medium text-foreground">{chunks}</span>,
            })}
          </span>
          <span>
            {t.rich("crop", {
              value: cropLabel,
              strong: (chunks) => <span className="font-medium text-foreground">{chunks}</span>,
            })}
          </span>
        </div>
      )}

      {result.status === "ok" && prediction && (
        <Card>
          <CardContent className="flex items-center justify-between gap-3">
            <p className="font-heading text-xl font-bold text-foreground">
              <DiseaseName displayName={prediction.displayName} disease={prediction.disease} />{" "}
              <span className="text-base font-medium text-muted-foreground">
                ({tUnits("percent", { value: confidencePercent(prediction.confidence) })})
              </span>
            </p>
            <HealthBadge isHealthy={prediction.isHealthy} />
          </CardContent>
        </Card>
      )}

      {result.status === "uncertain" && (
        <Alert>
          <HelpCircle />
          <AlertTitle>{t("uncertainTitle")}</AlertTitle>
          <AlertDescription>{t("uncertainDescription")}</AlertDescription>
        </Alert>
      )}

      {result.status === "ok" && closelyRelated.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("closelyRelated")}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {closelyRelated.map((item) => (
              <ResultRow key={item.classId} item={item} />
            ))}
          </CardContent>
        </Card>
      )}

      {result.status === "uncertain" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("possibleResults")}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {top3.map((item) => (
              <ResultRow key={item.classId} item={item} />
            ))}
          </CardContent>
        </Card>
      )}

      {farmId && (
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 rounded-lg border border-border bg-card px-3 py-2.5 text-sm">
          <span className="text-muted-foreground">{t("farmId")}</span>
          <span dir="ltr" className="break-all font-mono text-xs font-medium text-foreground">
            {farmId}
          </span>
        </div>
      )}

      {message && (
        <Alert>
          <Info />
          <AlertTitle>{t("note")}</AlertTitle>
          {/* Free text written by Module 1 -- shown exactly as delivered. */}
          <AlertDescription dir="auto">{message}</AlertDescription>
        </Alert>
      )}

      {warnings.length > 0 && (
        <Alert className="border-warning-border bg-warning-bg *:[svg]:text-warning-icon">
          <AlertTriangle />
          <AlertTitle className="text-foreground">{t("warning")}</AlertTitle>
          <AlertDescription className="text-foreground">
            <ul className="flex list-disc flex-col gap-1 ps-4">
              {warnings.map((code) => (
                <li key={code}>{labelFor(messages.disease.warnings, code)}</li>
              ))}
            </ul>
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
}
