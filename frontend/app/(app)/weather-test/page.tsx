"use client";

import { AlertCircle, ArrowLeft, CheckCircle2, CloudSun, MapPinPlus, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import { useFarms } from "@/features/farms/hooks";
import { CurrentConditionsCard } from "@/features/weather/components/current-conditions-card";
import { ForecastCard } from "@/features/weather/components/forecast-card";
import { RiskAssessmentCard } from "@/features/weather/components/risk-assessment-card";
import { useWeatherTest } from "@/features/weather/hooks";
import { useActiveFarm } from "@/providers/active-farm-provider";

/**
 * "Weather Test" — an explicit farmer action, distinct from the always-on
 * Weather Dashboard (/weather). Clicking the button below is the trigger
 * that calls the existing GET /api/v1/weather/current/ endpoint (same
 * client as the dashboard, via useWeatherTest) — no second weather API, no
 * duplicated Weather Module logic. Wording throughout is farmer-facing:
 * no "API", "endpoint", "coordinates", or other implementation language.
 */
export default function WeatherTestPage() {
  const t = useTranslations("weather.test");
  const tWeather = useTranslations("weather");
  const tNav = useTranslations("navigation");
  const tFarms = useTranslations("farms");
  const tCommon = useTranslations("common");
  const farms = useFarms();
  const { activeFarmId } = useActiveFarm();
  const activeFarm = farms.data?.find((farm) => farm.farmId === activeFarmId);
  const test = useWeatherTest(activeFarmId ?? undefined);

  const hasRun = test.isSuccess || test.isError;

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10 sm:px-6">
      <Link
        href="/dashboard"
        className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4 rtl:-scale-x-100" />
        {tNav("backToDashboard")}
      </Link>

      <div className="flex items-center gap-3">
        <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <CloudSun className="size-5" />
        </div>
        <div>
          <h1 className="font-heading text-2xl font-bold text-foreground">{t("title")}</h1>
          <p className="text-sm text-muted-foreground">{t("description")}</p>
        </div>
      </div>

      {farms.isLoading && <Skeleton className="h-64 w-full rounded-2xl" />}

      {!farms.isLoading && !activeFarm && (
        <div className="rounded-2xl bg-card p-6 text-center shadow-[var(--shadow-color-md)] sm:p-8">
          <CloudSun className="mx-auto mb-3 size-10 text-muted-foreground" />
          <p className="font-medium text-foreground">{tFarms("noFarmSelected")}</p>
          <p className="mt-1 text-sm text-muted-foreground">{t("noFarmDescription")}</p>
          <LinkButton href="/farms" className="mt-4 h-11 rounded-2xl px-5">
            <MapPinPlus className="size-4" />
            {tFarms("goToFarms")}
          </LinkButton>
        </div>
      )}

      {activeFarm && (
        <div className="flex flex-col gap-5 rounded-2xl bg-card p-6 shadow-[var(--shadow-color-md)] sm:p-8">
          {!hasRun && !test.isPending && (
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <CloudSun className="size-12 text-primary" />
              <p className="text-base font-medium text-foreground">
                {t("readyTitle", { farm: activeFarm.farmName })}
              </p>
              <p className="max-w-sm text-sm text-muted-foreground">{t("readyDescription")}</p>
              <Button
                size="lg"
                className="mt-2 h-12 rounded-2xl px-6 text-base"
                onClick={() => test.mutate()}
              >
                <CloudSun className="size-5" />
                {t("start")}
              </Button>
            </div>
          )}

          {test.isPending && (
            <div className="flex flex-col items-center gap-3 py-8 text-center">
              <Spinner className="size-8 text-primary" />
              <p className="text-base font-medium text-foreground">
                {t("testingTitle", { farm: activeFarm.farmName })}
              </p>
              <p className="text-sm text-muted-foreground">{t("testingDescription")}</p>
            </div>
          )}

          {test.isError && !test.isPending && (
            <div className="flex flex-col items-center gap-3 py-4 text-center">
              <Alert variant="destructive" className="text-start">
                <AlertCircle />
                <AlertDescription>{t("error")}</AlertDescription>
              </Alert>
              <Button variant="outline" className="h-11 rounded-2xl px-5" onClick={() => test.mutate()}>
                <RotateCcw className="size-4" />
                {tCommon("tryAgain")}
              </Button>
            </div>
          )}

          {test.isSuccess && !test.isPending && (
            <div className="flex flex-col gap-5">
              {test.data ? (
                <>
                  <div className="flex items-center gap-2 rounded-xl bg-success-bg px-4 py-3 text-success-text">
                    <CheckCircle2 className="size-5 shrink-0" />
                    <p className="text-sm font-medium">{t("complete")}</p>
                  </div>

                  <CurrentConditionsCard weather={test.data.weather} />
                  <RiskAssessmentCard
                    title={t("cropRisk")}
                    assessment={test.data.riskAssessment}
                  />
                  <ForecastCard
                    forecast={test.data.forecast}
                    predictedRiskAssessment={test.data.predictedRiskAssessment}
                  />
                </>
              ) : (
                <div className="flex flex-col items-center gap-2 py-6 text-center">
                  <CloudSun className="size-10 text-muted-foreground" />
                  <p className="font-medium text-foreground">{tWeather("unavailableTitle")}</p>
                  <p className="max-w-sm text-sm text-muted-foreground">
                    {tWeather("unavailableDescription")}
                  </p>
                </div>
              )}

              <Button
                variant="outline"
                className="h-11 self-start rounded-2xl px-5"
                onClick={() => test.reset()}
              >
                <RotateCcw className="size-4" />
                {t("testAgain")}
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
