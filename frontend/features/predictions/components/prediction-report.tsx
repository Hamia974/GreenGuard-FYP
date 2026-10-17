import { CloudSun, Info, ShieldAlert, Sprout } from "lucide-react";
import { useTranslations } from "next-intl";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent } from "@/components/ui/card";
import { DiseaseCheckResults } from "@/features/module1/components/disease-check-results";
import { Module2Results } from "@/features/module2/components/module2-results";
import { CurrentConditionsCard } from "@/features/weather/components/current-conditions-card";
import { ForecastCard } from "@/features/weather/components/forecast-card";
import { RiskAssessmentCard } from "@/features/weather/components/risk-assessment-card";

import type { Prediction } from "../types";
import { ModuleSection } from "./module-section";
import { PlantImageCard } from "./plant-image-card";
import { ReportHeader } from "./report-header";
import { SoilHealthCalloutCard } from "./soil-health-callout-card";

function UnavailableCard({ message }: { message: string }) {
  return (
    <Card>
      <CardContent>
        <p className="text-sm text-muted-foreground">{message}</p>
      </CardContent>
    </Card>
  );
}

interface PredictionReportProps {
  prediction: Prediction;
}

/**
 * Module 4 -- the integrated analysis report. It runs no model and adds no
 * result of its own: it lays out the three independent module results
 * side by side, each rendered by that module's own existing components.
 * There is deliberately no combined diagnosis, confidence or
 * recommendation here, because no module produces one.
 */
export function PredictionReport({ prediction }: PredictionReportProps) {
  const t = useTranslations("report");
  const { disease, soilNutrient, weather } = prediction;

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-5">
        <ReportHeader prediction={prediction} />
        {prediction.isLegacyReport && (
          <Alert>
            <Info />
            <AlertDescription>{t("legacyNotice")}</AlertDescription>
          </Alert>
        )}
        <PlantImageCard prediction={prediction} />
      </div>

      <ModuleSection
        moduleNumber={1}
        title={t("sections.disease.title")}
        source={
          disease
            ? t("sections.disease.sourceWithVersion", { version: disease.modelVersion })
            : t("sections.disease.source")
        }
        icon={ShieldAlert}
      >
        {disease ? (
          <DiseaseCheckResults result={disease} />
        ) : (
          <UnavailableCard message={t("sections.disease.unavailable")} />
        )}
      </ModuleSection>

      <ModuleSection
        moduleNumber={2}
        title={t("sections.soil.title")}
        source={t("sections.soil.source")}
        icon={Sprout}
      >
        {soilNutrient ? <Module2Results result={soilNutrient} /> : <SoilHealthCalloutCard />}
      </ModuleSection>

      <ModuleSection
        moduleNumber={3}
        title={t("sections.weather.title")}
        source={t("sections.weather.source")}
        icon={CloudSun}
      >
        {weather ? (
          <div className="flex flex-col gap-4">
            <CurrentConditionsCard weather={weather.weather} />
            <RiskAssessmentCard
              title={t("sections.weather.environmentalRisk")}
              assessment={weather.riskAssessment}
            />
            <ForecastCard
              forecast={weather.forecast}
              predictedRiskAssessment={weather.predictedRiskAssessment}
            />
          </div>
        ) : (
          <UnavailableCard message={t("sections.weather.unavailable")} />
        )}
      </ModuleSection>
    </div>
  );
}
