import { MapPin, MapPinPlus, Sprout } from "lucide-react";
import { useTranslations } from "next-intl";

import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { Farm } from "@/features/farms/types";

interface FarmSummaryCardProps {
  totalFarms: number;
  activeFarm: Farm | undefined;
  isLoading: boolean;
}

export function FarmSummaryCard({ totalFarms, activeFarm, isLoading }: FarmSummaryCardProps) {
  const t = useTranslations("dashboard.farmSummary");
  const tFarms = useTranslations("farms");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Sprout className="size-5 text-primary" />
          {t("title")}
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {isLoading ? (
          <Skeleton className="h-20 w-full" />
        ) : totalFarms === 0 ? (
          <div className="flex flex-col items-center gap-2 py-4 text-center">
            <p className="text-sm font-medium text-foreground">{t("emptyTitle")}</p>
            <p className="max-w-xs text-xs text-muted-foreground">{t("emptyDescription")}</p>
            <LinkButton href="/farms/new" size="sm" className="mt-1">
              <MapPinPlus className="size-3.5" />
              {tFarms("addFarm")}
            </LinkButton>
          </div>
        ) : (
          <>
            <div className="flex items-baseline gap-2">
              <span className="font-heading text-2xl font-bold text-foreground">
                {totalFarms}
              </span>
              <span className="text-sm text-muted-foreground">
                {t("registered", { count: totalFarms })}
              </span>
            </div>

            {activeFarm ? (
              <div className="rounded-lg bg-muted p-3">
                <p className="text-xs font-medium text-muted-foreground">{t("activeFarm")}</p>
                <p className="text-sm font-semibold text-foreground">{activeFarm.farmName}</p>
                <p className="mt-1 flex items-start gap-1.5 text-xs text-muted-foreground">
                  <MapPin className="mt-0.5 size-3 shrink-0" />
                  {activeFarm.address}
                </p>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">{t("selectActiveFarm")}</p>
            )}

            <LinkButton href="/farms" size="sm" variant="outline">
              {tFarms("manageFarms")}
            </LinkButton>
          </>
        )}
      </CardContent>
    </Card>
  );
}
