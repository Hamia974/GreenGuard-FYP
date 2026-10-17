"use client";

import { CloudSun, MapPin, RefreshCw } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import type { Farm } from "@/features/farms/types";

interface WeatherPageHeaderProps {
  activeFarm?: Farm;
  lastUpdatedAt?: number;
  isRefreshing: boolean;
  onRefresh: () => void;
}

/**
 * "Last updated" reflects when this browser last successfully fetched data
 * from the Weather Module (Module 3, via the Django backend -- React
 * Query's `dataUpdatedAt`), not the report's own `timestamp` field, since
 * the two can differ slightly (server-generation time vs. client-fetch
 * time). Per UI_SPECIFICATION.md section 14.3.
 */
export function WeatherPageHeader({
  activeFarm,
  lastUpdatedAt,
  isRefreshing,
  onRefresh,
}: WeatherPageHeaderProps) {
  const t = useTranslations("weather.dashboard");
  const tCommon = useTranslations("common");
  const format = useFormatter();
  const updatedLabel = lastUpdatedAt ? format.dateTime(new Date(lastUpdatedAt), "time") : null;

  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="flex items-center gap-2 font-heading text-3xl font-bold text-foreground">
          <CloudSun className="size-7 text-primary" />
          {t("title")}
        </h1>
        {activeFarm ? (
          <p className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
            <MapPin className="size-3.5" />
            {activeFarm.farmName}
            {activeFarm.address ? ` · ${activeFarm.address}` : ""}
          </p>
        ) : (
          <p className="mt-1 text-sm text-muted-foreground">{t("description")}</p>
        )}
      </div>

      {activeFarm && (
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {updatedLabel && <span>{t("updatedAt", { time: updatedLabel })}</span>}
          <Button size="sm" variant="outline" onClick={onRefresh} disabled={isRefreshing}>
            <RefreshCw className={isRefreshing ? "size-3.5 animate-spin" : "size-3.5"} />
            {tCommon("refresh")}
          </Button>
        </div>
      )}
    </div>
  );
}
