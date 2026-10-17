"use client";

import { AlertCircle, ArrowLeft, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { PredictionReport } from "@/features/predictions/components/prediction-report";
import { usePrediction } from "@/features/predictions/hooks";

export default function PredictionReportPage() {
  const t = useTranslations("report");
  const tNav = useTranslations("navigation");
  const params = useParams<{ predictionId: string }>();
  const prediction = usePrediction(params.predictionId);

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6 px-4 py-10 sm:px-6">
      <Link
        href="/dashboard"
        className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4 rtl:-scale-x-100" />
        {tNav("backToDashboard")}
      </Link>

      {prediction.isLoading && (
        <div className="flex flex-col gap-5">
          <Skeleton className="h-24 w-full rounded-2xl" />
          <Skeleton className="h-64 w-full rounded-2xl" />
          <Skeleton className="h-48 w-full rounded-2xl" />
        </div>
      )}

      {!prediction.isLoading && prediction.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{t("notFound")}</AlertDescription>
        </Alert>
      )}

      {!prediction.isLoading && prediction.data && (
        <>
          <PredictionReport prediction={prediction.data} />
          <LinkButton href="/quick-scan" variant="outline" className="w-fit">
            <RotateCcw className="size-4" />
            {t("newScan")}
          </LinkButton>
        </>
      )}
    </div>
  );
}
