import { AlertCircle, CloudRain, CloudSun, Droplets, RefreshCw, Thermometer, Wind } from "lucide-react";
import { useMessages, useTranslations } from "next-intl";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Farm } from "@/features/farms/types";
import { labelFor } from "@/lib/i18n/labels";
import { cn } from "@/lib/utils";

import type { WeatherSummary } from "../types";

interface WeatherCardProps {
  weather: WeatherSummary | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry?: () => void;
  /** The farm these weather values belong to. Undefined when no farm is active/selected. */
  activeFarm?: Farm;
}

function hasData(weather: WeatherSummary | undefined): weather is WeatherSummary {
  if (!weather) return false;
  return weather.temperature !== null || weather.humidity !== null;
}

const RISK_STYLES: Record<string, string> = {
  High: "bg-error-icon/10 text-error-icon",
  Moderate: "bg-warning-icon/10 text-warning-icon",
  Low: "bg-success-icon/10 text-success-icon",
};

function RiskBadge({ label, value }: { label: string; value: string | null }) {
  const messages = useMessages();
  if (!value) return null;
  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-lg px-3 py-2 text-xs font-medium",
        RISK_STYLES[value] ?? "bg-muted text-muted-foreground"
      )}
    >
      <span>{label}</span>
      {/* Styling keys off the raw Module 3 value; only the visible text is localized. */}
      <span>{labelFor(messages.weather.riskLevels, value)}</span>
    </div>
  );
}

export function WeatherCard({ weather, isLoading, isError, onRetry, activeFarm }: WeatherCardProps) {
  const t = useTranslations("dashboard.weatherCard");
  const tWeather = useTranslations("weather");
  const tUnits = useTranslations("units");
  const tCommon = useTranslations("common");
  const tFarms = useTranslations("farms");

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-2">
        <div className="flex min-w-0 flex-col gap-0.5">
          <CardTitle className="flex items-center gap-2 text-lg">
            <CloudSun className="size-5 text-primary" />
            {t("title")}
          </CardTitle>
          {activeFarm && (
            <p className="truncate text-xs text-muted-foreground">
              {activeFarm.farmName}
              {activeFarm.address ? ` · ${activeFarm.address}` : ""}
            </p>
          )}
        </div>
        {activeFarm && !isLoading && (isError || hasData(weather)) && onRetry && (
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={onRetry}
            aria-label={t("refresh")}
            className="shrink-0"
          >
            <RefreshCw className="size-3.5" />
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {!activeFarm && (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <CloudSun className="size-8 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">{tFarms("noFarmSelected")}</p>
            <p className="max-w-xs text-xs text-muted-foreground">{t("noFarmDescription")}</p>
            <LinkButton href="/farms" size="sm" className="mt-1">
              {tFarms("manageFarms")}
            </LinkButton>
          </div>
        )}

        {activeFarm && isLoading && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        )}

        {activeFarm && !isLoading && isError && (
          <div className="flex flex-col items-center gap-3 py-4 text-center">
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{t("loadError")}</AlertDescription>
            </Alert>
            {onRetry && (
              <Button size="sm" variant="outline" onClick={onRetry}>
                <RefreshCw className="size-3.5" />
                {tCommon("retry")}
              </Button>
            )}
          </div>
        )}

        {activeFarm && !isLoading && !isError && !hasData(weather) && (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <CloudSun className="size-8 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">{tWeather("unavailableTitle")}</p>
            <p className="max-w-xs text-xs text-muted-foreground">
              {tWeather("unavailableDescription")}
            </p>
          </div>
        )}

        {activeFarm && !isLoading && !isError && hasData(weather) && (
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center gap-2">
                <Thermometer className="size-4 text-warning-icon" />
                <div>
                  <p className="text-lg font-semibold text-foreground">
                    {tUnits("celsius", { value: weather.temperature ?? "—" })}
                  </p>
                  <p className="text-xs text-muted-foreground">{tWeather("metrics.temperature")}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Droplets className="size-4 text-info-icon" />
                <div>
                  <p className="text-lg font-semibold text-foreground">
                    {tUnits("percent", { value: weather.humidity ?? "—" })}
                  </p>
                  <p className="text-xs text-muted-foreground">{tWeather("metrics.humidity")}</p>
                </div>
              </div>
              {weather.windSpeed !== null && (
                <div className="flex items-center gap-2">
                  <Wind className="size-4 text-primary" />
                  <div>
                    <p className="text-lg font-semibold text-foreground">
                      {tUnits("metersPerSecond", { value: weather.windSpeed })}
                    </p>
                    <p className="text-xs text-muted-foreground">{tWeather("metrics.windSpeed")}</p>
                  </div>
                </div>
              )}
              {weather.rainfall !== null && (
                <div className="flex items-center gap-2">
                  <CloudRain className="size-4 text-info-icon" />
                  <div>
                    <p className="text-lg font-semibold text-foreground">
                      {tUnits("millimeters", { value: weather.rainfall })}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {tWeather("metrics.rainfallLast7Days")}
                    </p>
                  </div>
                </div>
              )}
            </div>

            {(weather.fungalDiseaseRisk || weather.heatStressRisk || weather.droughtRisk) && (
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                <RiskBadge label={t("fungalRisk")} value={weather.fungalDiseaseRisk} />
                <RiskBadge label={t("heatStress")} value={weather.heatStressRisk} />
                <RiskBadge label={t("droughtRisk")} value={weather.droughtRisk} />
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
