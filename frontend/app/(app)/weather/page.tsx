"use client";

import { AlertCircle, CloudSun, MapPinPlus } from "lucide-react";
import { useTranslations } from "next-intl";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useFarms } from "@/features/farms/hooks";
import { CurrentConditionsCard } from "@/features/weather/components/current-conditions-card";
import { ForecastCard } from "@/features/weather/components/forecast-card";
import { Module3PreviewCard } from "@/features/weather/components/module3-preview-card";
import { RiskAssessmentCard } from "@/features/weather/components/risk-assessment-card";
import { WeatherPageHeader } from "@/features/weather/components/weather-page-header";
import { useCurrentWeather } from "@/features/weather/hooks";
import { useActiveFarm } from "@/providers/active-farm-provider";

function WeatherSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-28 w-full rounded-2xl" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Skeleton className="h-40 w-full rounded-2xl" />
        <Skeleton className="h-40 w-full rounded-2xl" />
      </div>
      <Skeleton className="h-40 w-full rounded-2xl" />
    </div>
  );
}

export default function WeatherDashboardPage() {
  const t = useTranslations("weather");
  const tFarms = useTranslations("farms");
  const farms = useFarms();
  const { activeFarmId } = useActiveFarm();
  const activeFarm = farms.data?.find((farm) => farm.farmId === activeFarmId);
  const weather = useCurrentWeather(activeFarmId ?? undefined);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6">
      <WeatherPageHeader
        activeFarm={activeFarm}
        lastUpdatedAt={weather.dataUpdatedAt}
        isRefreshing={weather.isFetching}
        onRefresh={() => weather.refetch()}
      />

      {!farms.isLoading && !activeFarmId && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-10 text-center">
            <CloudSun className="size-10 text-muted-foreground" />
            <p className="font-medium text-foreground">{tFarms("noFarmSelected")}</p>
            <p className="max-w-sm text-sm text-muted-foreground">{t("dashboard.noFarmDescription")}</p>
            <LinkButton href="/farms">
              <MapPinPlus className="size-3.5" />
              {tFarms("manageFarms")}
            </LinkButton>
          </CardContent>
        </Card>
      )}

      {activeFarmId && weather.isLoading && <WeatherSkeleton />}

      {activeFarmId && !weather.isLoading && weather.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{t("dashboard.loadError")}</AlertDescription>
        </Alert>
      )}

      {activeFarmId && !weather.isLoading && !weather.isError && !weather.data && (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center">
            <CloudSun className="size-10 text-muted-foreground" />
            <p className="font-medium text-foreground">{t("unavailableTitle")}</p>
            <p className="max-w-sm text-sm text-muted-foreground">{t("unavailableDescription")}</p>
          </CardContent>
        </Card>
      )}

      {activeFarmId && !weather.isLoading && !weather.isError && weather.data && (
        <>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <CurrentConditionsCard weather={weather.data.weather} />
            <RiskAssessmentCard
              title={t("environmentalRisk")}
              assessment={weather.data.riskAssessment}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <ForecastCard
              forecast={weather.data.forecast}
              predictedRiskAssessment={weather.data.predictedRiskAssessment}
            />
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <Module3PreviewCard
                title={t("preview.uvWind.title")}
                description={t("preview.uvWind.description")}
              />
              <Module3PreviewCard
                title={t("preview.map.title")}
                description={t("preview.map.description")}
              />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
