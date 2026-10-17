import { AlertCircle, Sprout } from "lucide-react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { DiseaseName } from "@/features/module1/components/disease-name";

import type { RecentPrediction } from "../types";

interface RecentPredictionsCardProps {
  predictions: RecentPrediction[] | undefined;
  isLoading: boolean;
  isError: boolean;
}

export function RecentPredictionsCard({
  predictions,
  isLoading,
  isError,
}: RecentPredictionsCardProps) {
  const t = useTranslations("dashboard.recentAnalyses");
  const tDisease = useTranslations("disease");
  const tUnits = useTranslations("units");
  const format = useFormatter();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t("title")}</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
            <Skeleton className="h-12 w-full" />
          </div>
        )}

        {!isLoading && isError && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{t("loadError")}</AlertDescription>
          </Alert>
        )}

        {!isLoading && !isError && predictions?.length === 0 && (
          <div className="flex flex-col items-center gap-2 py-6 text-center">
            <Sprout className="size-8 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">{t("emptyTitle")}</p>
            <p className="max-w-xs text-xs text-muted-foreground">{t("emptyDescription")}</p>
          </div>
        )}

        {!isLoading && !isError && predictions && predictions.length > 0 && (
          <ul className="flex flex-col divide-y divide-border">
            {predictions.map((prediction) => (
              <li key={prediction.predictionId}>
                <Link
                  href={`/predictions/${prediction.predictionId}`}
                  className="flex items-center justify-between gap-3 rounded-lg py-3 hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <div>
                    <p className="text-sm font-medium text-foreground">
                      {prediction.diagnosis ? (
                        <DiseaseName displayName={prediction.diagnosis} />
                      ) : (
                        tDisease("noConfidentResult")
                      )}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {format.dateTime(new Date(prediction.createdAt), "date")}
                    </p>
                  </div>
                  {prediction.confidence !== null && (
                    <span className="rounded-full bg-info-bg px-2.5 py-1 text-xs font-medium text-info-text">
                      {tUnits("percent", { value: Math.round(prediction.confidence * 100) })}
                    </span>
                  )}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
