import { CloudRain, Droplets, Sparkles, Thermometer } from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { NextDayForecast, RiskAssessment, RiskLevel } from "@/features/weather/types";

const RISK_BADGE_VARIANT: Record<RiskLevel, "success" | "warning" | "error"> = {
  Low: "success",
  Moderate: "warning",
  High: "error",
};

interface ForecastCardProps {
  forecast: NextDayForecast | null;
  predictedRiskAssessment: RiskAssessment | null;
}

/**
 * The Weather Module's LSTM forecast add-on -- next day only, never a
 * multi-day or hourly forecast (UI_SPECIFICATION.md sections 14.6/14.7
 * describe those, but the delivered contract doesn't produce them; see
 * docs/REST_API_SPEC.md section 5A). Both `forecast` and
 * `predictedRiskAssessment` are best-effort and legitimately null -- shown
 * as a clear unavailable state, never backfilled with a fabricated value.
 * Per the module's own evaluation, its forecast currently beats a
 * "tomorrow = today" baseline on humidity/rainfall but not temperature --
 * shown as a caveat, not presented as guaranteed-accurate.
 */
export function ForecastCard({ forecast, predictedRiskAssessment }: ForecastCardProps) {
  const t = useTranslations("weather");
  const tUnits = useTranslations("units");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Sparkles className="size-4 text-primary" />
          {t("forecast.title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {!forecast && (
          <p className="text-sm text-muted-foreground">{t("forecast.unavailable")}</p>
        )}

        {forecast && (
          <>
            <div className="grid grid-cols-3 gap-3">
              <div className="flex items-center gap-2">
                <Thermometer className="size-4 text-warning-icon" />
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    {tUnits("celsius", { value: forecast.temperature })}
                  </p>
                  <p className="text-xs text-muted-foreground">{t("metrics.temperature")}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Droplets className="size-4 text-info-icon" />
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    {tUnits("percent", { value: forecast.humidity })}
                  </p>
                  <p className="text-xs text-muted-foreground">{t("metrics.humidity")}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <CloudRain className="size-4 text-info-icon" />
                <div>
                  <p className="text-sm font-semibold text-foreground">
                    {tUnits("millimeters", { value: forecast.rainfallMm })}
                  </p>
                  <p className="text-xs text-muted-foreground">{t("metrics.rainfall")}</p>
                </div>
              </div>
            </div>

            {predictedRiskAssessment && (
              <div className="flex flex-col gap-2 border-t border-border pt-3">
                <p className="text-xs font-medium text-muted-foreground">
                  {t("forecast.predictedRisk")}
                </p>
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                  <Badge variant={RISK_BADGE_VARIANT[predictedRiskAssessment.fungalDiseaseRisk]}>
                    {t("forecast.fungal", {
                      level: t(`riskLevels.${predictedRiskAssessment.fungalDiseaseRisk}`),
                    })}
                  </Badge>
                  <Badge variant={RISK_BADGE_VARIANT[predictedRiskAssessment.heatStressRisk]}>
                    {t("forecast.heat", {
                      level: t(`riskLevels.${predictedRiskAssessment.heatStressRisk}`),
                    })}
                  </Badge>
                  <Badge variant={RISK_BADGE_VARIANT[predictedRiskAssessment.droughtRisk]}>
                    {t("forecast.drought", {
                      level: t(`riskLevels.${predictedRiskAssessment.droughtRisk}`),
                    })}
                  </Badge>
                </div>
              </div>
            )}

            <p className="text-xs text-muted-foreground/80">{t("forecast.caveat")}</p>
          </>
        )}
      </CardContent>
    </Card>
  );
}
