import { useFormatter, useMessages, useTranslations } from "next-intl";

import { Card, CardContent } from "@/components/ui/card";
import { labelFor } from "@/lib/i18n/labels";

import type { Prediction } from "../types";

interface PlantImageCardProps {
  prediction: Prediction;
}

export function PlantImageCard({ prediction }: PlantImageCardProps) {
  const t = useTranslations("report.plantImage");
  const messages = useMessages();
  const format = useFormatter();
  const disease = prediction.disease;

  return (
    <Card>
      <CardContent className="flex flex-col gap-4 sm:flex-row">
        <div className="overflow-hidden rounded-2xl sm:w-2/5 sm:shrink-0">
          {prediction.uploadedImage ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={prediction.uploadedImage}
              alt={t("imageAlt")}
              className="h-full w-full object-cover"
            />
          ) : (
            <div className="flex h-48 w-full items-center justify-center bg-muted text-sm text-muted-foreground">
              {t("noImage")}
            </div>
          )}
        </div>
        <div className="flex flex-col justify-center gap-1.5 text-sm">
          <p className="text-muted-foreground">{t("uploadDate")}</p>
          <p className="font-medium text-foreground">
            {format.dateTime(new Date(prediction.createdAt), "dateTime")}
          </p>
          {disease && (
            <>
              <p className="mt-3 text-muted-foreground">{t("crop")}</p>
              <p className="font-medium text-foreground">
                {labelFor(messages.crops, disease.detectedCrop)}{" "}
                <span className="font-normal text-muted-foreground">
                  ({disease.cropSource === "user" ? t("cropSelectedByYou") : t("cropDetected")})
                </span>
              </p>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
