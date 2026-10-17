import { CheckCircle2 } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import type { Prediction } from "../types";

interface ReportHeaderProps {
  prediction: Prediction;
}

export function ReportHeader({ prediction }: ReportHeaderProps) {
  const t = useTranslations("report.header");
  const format = useFormatter();

  return (
    <div className="flex flex-col gap-2">
      <h1 className="font-heading text-2xl font-bold text-foreground sm:text-3xl">
        {t("title")}
      </h1>
      <p className="text-sm text-muted-foreground">{t("description")}</p>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
        <span>
          {t("id")} <span dir="ltr">{prediction.predictionId}</span>
        </span>
        <span>
          {format.dateTime(new Date(prediction.createdAt), "dateTime")}
        </span>
      </div>
      {prediction.predictionStatus === "completed" && (
        <span className="inline-flex w-fit items-center gap-1.5 rounded-full bg-success-icon/10 px-3 py-1 text-xs font-semibold text-success-icon">
          <CheckCircle2 className="size-3.5" />
          {t("completed")}
        </span>
      )}
    </div>
  );
}
