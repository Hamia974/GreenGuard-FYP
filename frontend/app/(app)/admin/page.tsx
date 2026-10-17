"use client";

import { AlertCircle, Cpu, ScanLine, ShieldCheck, Users } from "lucide-react";
import { useMessages, useTranslations } from "next-intl";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { StatCard } from "@/features/admin/components/stat-card";
import { StatusBadge } from "@/features/admin/components/status-badge";
import { DiseaseName } from "@/features/module1/components/disease-name";
import {
  useAdminDashboard,
  useAiMonitoring,
  usePlatformStatistics,
  useSystemHealth,
} from "@/features/admin/hooks";
import { labelFor } from "@/lib/i18n/labels";
import { useParseApiError } from "@/lib/i18n/use-api-error";

// Row labels for the API's own keys (imageModule, backend, ...) live in
// messages/<locale>/admin.json under aiModules / systemHealthItems.
export default function AdminOverviewPage() {
  const t = useTranslations("admin.overview");
  const messages = useMessages();
  const parseApiError = useParseApiError();
  const dashboard = useAdminDashboard();
  const aiMonitoring = useAiMonitoring();
  const systemHealth = useSystemHealth();
  const statistics = usePlatformStatistics();

  return (
    <div className="flex flex-col gap-6">
      {dashboard.isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-40 w-full rounded-2xl" />
          ))}
        </div>
      )}

      {!dashboard.isLoading && dashboard.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{parseApiError(dashboard.error).message}</AlertDescription>
        </Alert>
      )}

      {!dashboard.isLoading && !dashboard.isError && dashboard.data && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <StatCard
            label={t("totalUsers")}
            value={dashboard.data.totalUsers.toString()}
            description={t("activeUsers", { count: dashboard.data.activeUsers })}
            icon={Users}
            iconClassName="bg-info-bg text-info-icon"
          />
          <StatCard
            label={t("totalPredictions")}
            value={dashboard.data.totalPredictions.toString()}
            description={t("totalPredictionsDescription")}
            icon={ScanLine}
            iconClassName="bg-success-bg text-success-icon"
          />
          <StatCard
            label={t("systemStatus")}
            value={labelFor(messages.admin.statuses, dashboard.data.systemStatus)}
            description={t("systemStatusDescription")}
            icon={ShieldCheck}
            iconClassName="bg-warning-bg text-warning-icon"
          />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Cpu className="size-4" />
              {t("aiMonitoring")}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {aiMonitoring.isLoading &&
              Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-8 w-full rounded-lg" />
              ))}

            {!aiMonitoring.isLoading && aiMonitoring.isError && (
              <Alert variant="destructive">
                <AlertCircle />
                <AlertDescription>{parseApiError(aiMonitoring.error).message}</AlertDescription>
              </Alert>
            )}

            {!aiMonitoring.isLoading &&
              !aiMonitoring.isError &&
              aiMonitoring.data &&
              Object.entries(aiMonitoring.data).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="text-foreground">{labelFor(messages.admin.aiModules, key)}</span>
                  <StatusBadge status={value} />
                </div>
              ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldCheck className="size-4" />
              {t("systemHealth")}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            {systemHealth.isLoading &&
              Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-8 w-full rounded-lg" />
              ))}

            {!systemHealth.isLoading && systemHealth.isError && (
              <Alert variant="destructive">
                <AlertCircle />
                <AlertDescription>{parseApiError(systemHealth.error).message}</AlertDescription>
              </Alert>
            )}

            {!systemHealth.isLoading &&
              !systemHealth.isError &&
              systemHealth.data &&
              Object.entries(systemHealth.data).map(([key, value]) => (
                <div key={key} className="flex items-center justify-between text-sm">
                  <span className="text-foreground">
                    {labelFor(messages.admin.systemHealthItems, key)}
                  </span>
                  <StatusBadge status={value} />
                </div>
              ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t("platformStatistics")}</CardTitle>
        </CardHeader>
        <CardContent>
          {statistics.isLoading && <Skeleton className="h-16 w-full rounded-lg" />}

          {!statistics.isLoading && statistics.isError && (
            <Alert variant="destructive">
              <AlertCircle />
              <AlertDescription>{parseApiError(statistics.error).message}</AlertDescription>
            </Alert>
          )}

          {!statistics.isLoading && !statistics.isError && statistics.data && (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <p className="text-xs text-muted-foreground">{t("mostDetectedDisease")}</p>
                <p className="text-sm font-medium text-foreground">
                  {statistics.data.mostDetectedDisease ? (
                    <DiseaseName displayName={statistics.data.mostDetectedDisease} />
                  ) : (
                    t("notEnoughData")
                  )}
                </p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t("mostRecommendedCrop")}</p>
                <p className="text-sm font-medium text-foreground">
                  {statistics.data.mostRecommendedCrop
                    ? labelFor(messages.crops, statistics.data.mostRecommendedCrop)
                    : t("notAvailableYet")}
                </p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
