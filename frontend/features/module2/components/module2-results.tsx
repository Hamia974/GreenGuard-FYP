"use client";

import { AlertTriangle, CheckCircle2, ShieldCheck } from "lucide-react";
import { useMessages, useTranslations } from "next-intl";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { labelFor } from "@/lib/i18n/labels";
import { cn } from "@/lib/utils";

import type { Module2Result, NutrientNote } from "../types";
import { NutrientOverviewChart } from "./nutrient-overview-chart";
import { SoilConditionsIndicator } from "./soil-conditions-indicator";

const LABEL_STYLES: Record<string, string> = {
  good: "bg-success-icon/10 text-success-icon",
  moderate: "bg-warning-icon/10 text-warning-icon",
  poor: "bg-error-icon/10 text-error-icon",
};

const RISK_DOT: Record<string, string> = {
  high: "bg-error-icon",
  medium: "bg-warning-icon",
  low: "bg-success-icon",
};

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function NutrientNoteRow({ note }: { note: NutrientNote }) {
  const messages = useMessages();

  return (
    <div className="flex flex-col gap-1 rounded-lg border border-border bg-card px-3 py-2.5 text-sm">
      <div className="flex items-center gap-2">
        <span className={cn("size-2 shrink-0 rounded-full", RISK_DOT[note.level])} />
        <span className="font-medium text-foreground">
          {labelFor(messages.soil.results.nutrients, note.nutrient)}
        </span>
        {/* Free text written by Module 2 -- shown exactly as delivered. */}
        <span dir="auto" className="text-xs text-muted-foreground">
          {note.confidenceText}
        </span>
      </div>
      {note.why && (
        <p dir="auto" className="ps-4 text-xs text-muted-foreground">
          {note.why}
        </p>
      )}
    </div>
  );
}

interface Module2ResultsProps {
  result: Module2Result;
}

/**
 * Renders Module 2's result. App-owned labels are localized; every sentence
 * Module 2 itself wrote (headline, notes, caveat, message) is shown exactly
 * as delivered, with dir="auto" so it reads correctly inside an RTL page.
 */
export function Module2Results({ result }: Module2ResultsProps) {
  const t = useTranslations("soil.results");
  const tUnits = useTranslations("units");
  const messages = useMessages();

  if (!result.cropSupported) {
    return (
      <Alert>
        <AlertTriangle />
        <AlertTitle>{t("notSupportedTitle")}</AlertTitle>
        <AlertDescription dir={result.message ? "auto" : undefined}>
          {result.message ?? t("notSupportedDescription")}
        </AlertDescription>
      </Alert>
    );
  }

  const { module2a, module2b, overallSoilHealthScore, overallSoilHealthLabel, recommendationNotes } =
    result;
  if (!module2a || !module2b || !recommendationNotes) return null;

  const healthLabel = (value: string) =>
    labelFor(messages.soil.results.healthLabels, value, capitalize(value));

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">{t("soilHealth")}</p>
              <p className="font-heading text-2xl font-bold text-foreground">
                {tUnits("outOf100", {
                  value: overallSoilHealthScore !== null ? Math.round(overallSoilHealthScore) : "—",
                })}
              </p>
            </div>
            {overallSoilHealthLabel && (
              <span
                className={cn(
                  "rounded-full px-3 py-1.5 text-sm font-semibold",
                  LABEL_STYLES[overallSoilHealthLabel]
                )}
              >
                {healthLabel(overallSoilHealthLabel)}
              </span>
            )}
          </div>
          <p dir="auto" className="font-medium text-foreground">
            {recommendationNotes.headline}
          </p>
        </CardContent>
      </Card>

      {recommendationNotes.soilConditionNote && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>{t("soilConditionTitle")}</AlertTitle>
          <AlertDescription dir="auto">{recommendationNotes.soilConditionNote}</AlertDescription>
        </Alert>
      )}

      {recommendationNotes.needsAttention.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("needsAttention")}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {recommendationNotes.needsAttention.map((note) => (
              <NutrientNoteRow key={note.nutrient} note={note} />
            ))}
          </CardContent>
        </Card>
      )}

      {recommendationNotes.lookingFine.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("lookingFine")}</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-2">
            {recommendationNotes.lookingFine.map((note) => (
              <NutrientNoteRow key={note.nutrient} note={note} />
            ))}
            <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
              <CheckCircle2 className="size-4" />
              {t("overallNutrientHealth", { label: healthLabel(module2a.overallNutrientHealth) })}
            </div>
          </CardContent>
        </Card>
      )}

      <NutrientOverviewChart notes={recommendationNotes} />

      <SoilConditionsIndicator module2b={module2b} />

      <Alert>
        <ShieldCheck />
        <AlertDescription className="flex flex-col gap-2">
          {module2a.inputTypicality.flag === "typical" ? (
            <span>{t("reliable")}</span>
          ) : (
            <span dir="auto">{recommendationNotes.reliabilityNote}</span>
          )}
          <span dir="auto" className="text-xs text-muted-foreground">
            {recommendationNotes.caveat}
          </span>
        </AlertDescription>
      </Alert>
    </div>
  );
}
