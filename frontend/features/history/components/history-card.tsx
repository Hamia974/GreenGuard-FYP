"use client";

import { Calendar, Eye, Trash2 } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent } from "@/components/ui/card";
import type { HistoryListItem } from "@/features/history/types";
import { DiseaseName } from "@/features/module1/components/disease-name";

function confidenceLevel(confidence: number): "veryHigh" | "high" | "medium" | "low" {
  if (confidence >= 0.9) return "veryHigh";
  if (confidence >= 0.75) return "high";
  if (confidence >= 0.5) return "medium";
  return "low";
}

interface HistoryCardProps {
  record: HistoryListItem;
  isDeleting: boolean;
  isConfirmingDelete: boolean;
  onRequestDelete: () => void;
  onCancelDelete: () => void;
  onConfirmDelete: () => void;
}

export function HistoryCard({
  record,
  isDeleting,
  isConfirmingDelete,
  onRequestDelete,
  onCancelDelete,
  onConfirmDelete,
}: HistoryCardProps) {
  const t = useTranslations("history.card");
  const tDisease = useTranslations("disease");
  const tCommon = useTranslations("common");
  const format = useFormatter();

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex flex-col gap-0.5">
            <p className="text-xs text-muted-foreground">{t("moduleLabel")}</p>
            <h3 className="font-heading text-base font-semibold text-foreground">
              {record.diagnosis ? (
                <DiseaseName displayName={record.diagnosis} />
              ) : (
                tDisease("noConfidentResult")
              )}
            </h3>
          </div>
          {record.confidence !== null && (
            <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-info-bg px-2.5 py-1 text-xs font-medium text-info-text">
              {t("confidenceBadge", {
                value: Math.round(record.confidence * 100),
                level: t(`confidenceLevels.${confidenceLevel(record.confidence)}`),
              })}
            </span>
          )}
        </div>

        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Calendar className="size-3.5 shrink-0" />
          {format.dateTime(new Date(record.createdAt), "dateTimeMedium")}
        </p>

        {isConfirmingDelete ? (
          <div className="mt-1 flex flex-wrap items-center gap-2 rounded-lg bg-error-bg p-2">
            <span className="text-xs text-error-text">{t("confirmDelete")}</span>
            <Button
              type="button"
              size="sm"
              variant="destructive"
              disabled={isDeleting}
              onClick={onConfirmDelete}
            >
              {isDeleting ? tCommon("deleting") : tCommon("confirm")}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              disabled={isDeleting}
              onClick={onCancelDelete}
            >
              {tCommon("cancel")}
            </Button>
          </div>
        ) : (
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <LinkButton
              href={`/predictions/${record.predictionId}`}
              size="sm"
              variant="outline"
            >
              <Eye className="size-3.5" />
              {t("viewReport")}
            </LinkButton>
            <Button type="button" size="sm" variant="destructive" onClick={onRequestDelete}>
              <Trash2 className="size-3.5" />
              {tCommon("delete")}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
