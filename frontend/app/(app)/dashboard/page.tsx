"use client";

import { AlertCircle } from "lucide-react";
import { useTranslations } from "next-intl";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { FarmSummaryCard } from "@/features/dashboard/components/farm-summary-card";
import { MainTests } from "@/features/dashboard/components/main-tests";
import { NotificationsPreviewCard } from "@/features/dashboard/components/notifications-preview-card";
import { QuickActions } from "@/features/dashboard/components/quick-actions";
import { RecentPredictionsCard } from "@/features/dashboard/components/recent-predictions-card";
import { StatisticsCards } from "@/features/dashboard/components/statistics-cards";
import { WeatherCard } from "@/features/dashboard/components/weather-card";
import { WelcomeBanner } from "@/features/dashboard/components/welcome-banner";
import {
  useDashboardOverview,
  useDashboardWeather,
  useRecentPredictions,
} from "@/features/dashboard/hooks";
import { useFarms } from "@/features/farms/hooks";
import { useAuth } from "@/providers/auth-provider";
import { useActiveFarm } from "@/providers/active-farm-provider";

function DashboardSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <Skeleton className="h-40 w-full rounded-2xl" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-40 w-full rounded-2xl" />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Skeleton className="h-64 w-full rounded-2xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const t = useTranslations("dashboard");
  const { user } = useAuth();
  const overview = useDashboardOverview();
  const recentPredictions = useRecentPredictions(5);
  const farms = useFarms();
  const { activeFarmId } = useActiveFarm();
  const weather = useDashboardWeather(activeFarmId ?? undefined);

  const firstName = user?.fullName.split(" ")[0] ?? t("fallbackName");
  const activeFarm = farms.data?.find((farm) => farm.farmId === activeFarmId);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8 sm:px-6">
      {overview.isLoading && <DashboardSkeleton />}

      {!overview.isLoading && overview.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{t("loadError")}</AlertDescription>
        </Alert>
      )}

      {!overview.isLoading && !overview.isError && overview.data && (
        <>
          <WelcomeBanner firstName={firstName} />

          <MainTests
            hasActiveFarm={!!activeFarm}
            hasAnyFarm={!!farms.data && farms.data.length > 0}
            activeFarmName={activeFarm?.farmName}
          />

          <StatisticsCards
            totalPredictions={overview.data.totalPredictions}
            statistics={overview.data.predictionStatistics}
          />

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <WeatherCard
              weather={weather.data}
              isLoading={weather.isLoading}
              isError={weather.isError}
              onRetry={() => weather.refetch()}
              activeFarm={activeFarm}
            />
            <RecentPredictionsCard
              predictions={recentPredictions.data}
              isLoading={recentPredictions.isLoading}
              isError={recentPredictions.isError}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <FarmSummaryCard
              totalFarms={overview.data.farmSummary.totalFarms}
              activeFarm={activeFarm}
              isLoading={farms.isLoading}
            />
            <NotificationsPreviewCard
              notificationCount={overview.data.notificationCount}
              isLoading={false}
            />
          </div>

          <QuickActions />
        </>
      )}
    </div>
  );
}
