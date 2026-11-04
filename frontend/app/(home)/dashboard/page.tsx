"use client";

import { useQueries } from "@tanstack/react-query";
import { useFormatter, useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ActionBar } from "@/features/dashboard/components/action-bar";
import { FarmMap } from "@/features/dashboard/components/farm-map";
import { FarmStatusBar } from "@/features/dashboard/components/farm-status-bar";
import { MapLegend } from "@/features/dashboard/components/map-legend";
import { HeaderControls } from "@/features/dashboard/components/navigation";
import { RecentChecks } from "@/features/dashboard/components/recent-checks";
import { WeatherInstruments } from "@/features/dashboard/components/weather-instruments";
import styles from "@/features/dashboard/home.module.css";
import { useRecentPredictions } from "@/features/dashboard/hooks";
import type { FarmMapArea, FarmMapFarm } from "@/features/dashboard/lib/farm-map";
import { farmStatusOf } from "@/features/dashboard/lib/farm-status";
import { leafStatusOf, type RecentCheck } from "@/features/dashboard/lib/leaf-status";
import { useFarms } from "@/features/farms/hooks";
import { fetchPrediction } from "@/features/predictions/api";
import { predictionQueryKey } from "@/features/predictions/hooks";
import { fetchCurrentWeather } from "@/features/weather/api";
import { currentWeatherQueryKey } from "@/features/weather/hooks";
import { useAuth } from "@/providers/auth-provider";
import { useActiveFarm } from "@/providers/active-farm-provider";

/** Enough recent checks to colour most farms by their latest leaf result. */
const RECENT_LIMIT = 8;
/** How many of them the side list shows. */
const RECENT_SHOWN = 4;
const WEATHER_STALE_MS = 5 * 60 * 1000;

function greetingKey(hour: number) {
  if (hour < 12) return "morning";
  if (hour < 17) return "afternoon";
  return "evening";
}

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const format = useFormatter();
  const { user } = useAuth();
  const farms = useFarms();
  const { activeFarmId, setActiveFarmId } = useActiveFarm();
  const recent = useRecentPredictions(RECENT_LIMIT);

  const farmList = useMemo(() => farms.data ?? [], [farms.data]);
  const activeFarm = farmList.find((farm) => farm.farmId === activeFarmId);

  // With no farm chosen yet, start on the first one so the page has something to show.
  useEffect(() => {
    if (!activeFarm && farmList.length > 0) setActiveFarmId(farmList[0].farmId);
  }, [activeFarm, farmList, setActiveFarmId]);

  // The summary rows only carry the disease name; each full report adds the
  // photo, farm, Module 1 verdict and the soil result saved with it.
  const detailData = useQueries({
    queries: (recent.data ?? []).map((row) => ({
      queryKey: predictionQueryKey(row.predictionId),
      queryFn: () => fetchPrediction(row.predictionId),
    })),
    combine: (results) => results.map((result) => result.data),
  });

  // Every farm's weather, so the map can colour each farm by the status rule.
  // One request per farm until the backend offers them together (updations.md row 14).
  const weatherByFarm = useQueries({
    queries: farmList.map((farm) => ({
      queryKey: currentWeatherQueryKey(farm.farmId),
      queryFn: () => fetchCurrentWeather(farm.farmId),
      staleTime: WEATHER_STALE_MS,
    })),
    combine: (results) =>
      Object.fromEntries(
        results.map((result, index) => [
          farmList[index]?.farmId,
          { data: result.data, isLoading: result.isLoading, isError: result.isError, refetch: result.refetch },
        ])
      ),
  });

  const checks: RecentCheck[] = useMemo(
    () =>
      (recent.data ?? []).map((row, index) => ({
        row,
        detail: detailData[index],
        status: leafStatusOf(row, detailData[index]),
      })),
    [recent.data, detailData]
  );

  const selectedWeather = activeFarmId ? weatherByFarm[activeFarmId] : undefined;
  const selectedStatus = farmStatusOf(activeFarmId ?? "", checks, selectedWeather?.data);
  const soilScore =
    checks.find(
      (check) =>
        check.detail?.farmId === activeFarmId && check.detail?.soilNutrient?.overallSoilHealthScore != null
    )?.detail?.soilNutrient?.overallSoilHealthScore ?? null;

  const leafCheck = checks.find((check) => check.detail?.farmId === activeFarmId && check.detail?.disease);

  const mapFarms: FarmMapFarm[] = farmList.map((farm) => ({
    id: farm.farmId,
    name: farm.farmName,
    latitude: farm.latitude,
    longitude: farm.longitude,
    status: farmStatusOf(farm.farmId, checks, weatherByFarm[farm.farmId]?.data).status ?? "unknown",
  }));

  // Keep pins clear of the status bar at the top of the map and the legend at the bottom.
  const statusBarRef = useRef<HTMLDivElement | null>(null);
  const [statusBar, setStatusBar] = useState<HTMLDivElement | null>(null);
  const [layoutKey, setLayoutKey] = useState(0);
  const attachStatusBar = useCallback((element: HTMLDivElement | null) => {
    statusBarRef.current = element;
    setStatusBar(element);
  }, []);
  useEffect(() => {
    if (!statusBar) return;
    const observer = new ResizeObserver(() => setLayoutKey((key) => key + 1));
    observer.observe(statusBar);
    return () => observer.disconnect();
  }, [statusBar]);
  const getArea = useCallback(
    (width: number, height: number): FarmMapArea => ({
      x0: 24,
      y0: (statusBarRef.current?.offsetHeight ?? 80) + 40,
      x1: width - 24,
      y1: height - 64,
    }),
    []
  );

  const firstName = user?.fullName.split(" ")[0] ?? t("fallbackName");
  const now = new Date();
  const hasFarm = !!activeFarm;
  const statusLoading =
    farms.isLoading || recent.isLoading || (hasFarm && (selectedWeather?.isLoading ?? true));

  return (
    <div className={styles.page}>
      <header className={styles.pageHead}>
        <div className={styles.greetingBlock}>
          <p className={styles.eyebrow}>{format.dateTime(now, { weekday: "long", day: "numeric", month: "long" })}</p>
          <h1 className={styles.greeting}>{t(`greeting.${greetingKey(now.getHours())}`, { name: firstName })}</h1>
        </div>
        <HeaderControls />
      </header>

      <div className={styles.desk}>
        <div className={styles.mapArea}>
          <FarmMap
            farms={mapFarms}
            selectedId={activeFarmId}
            onSelect={setActiveFarmId}
            getArea={getArea}
            layoutKey={`${layoutKey}-${mapFarms.map((farm) => farm.status).join()}`}
          >
            {activeFarm && (
              <div ref={attachStatusBar} className={styles.statusSlot}>
                <FarmStatusBar farmName={activeFarm.farmName} status={selectedStatus} isLoading={statusLoading} />
              </div>
            )}
            <MapLegend statuses={mapFarms.map((farm) => farm.status)} />
          </FarmMap>
        </div>

        <div className={styles.side}>
          <aside className={styles.panel}>
            <WeatherInstruments
              hasFarm={hasFarm}
              report={selectedWeather?.isError ? undefined : selectedWeather?.data}
              isLoading={hasFarm && (selectedWeather?.isLoading ?? true)}
              isError={selectedWeather?.isError ?? false}
              onRetry={() => selectedWeather?.refetch()}
            />
          </aside>

          <RecentChecks
            checks={checks}
            farms={farmList}
            activeFarmId={activeFarmId}
            limit={RECENT_SHOWN}
            isLoading={recent.isLoading}
            isError={recent.isError}
          />
        </div>

        <ActionBar
          hasFarm={hasFarm}
          soilScore={soilScore}
          leafCheck={leafCheck}
          weather={selectedWeather?.isError ? undefined : selectedWeather?.data}
        />
      </div>
    </div>
  );
}
