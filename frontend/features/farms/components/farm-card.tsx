"use client";

import { MapPin, Pencil, Star, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent } from "@/components/ui/card";
import type { Farm } from "@/features/farms/types";
import { cn } from "@/lib/utils";

interface FarmCardProps {
  farm: Farm;
  isActive: boolean;
  isDeleting: boolean;
  isConfirmingDelete: boolean;
  onSetActive: () => void;
  onRequestDelete: () => void;
  onCancelDelete: () => void;
  onConfirmDelete: () => void;
}

export function FarmCard({
  farm,
  isActive,
  isDeleting,
  isConfirmingDelete,
  onSetActive,
  onRequestDelete,
  onCancelDelete,
  onConfirmDelete,
}: FarmCardProps) {
  const t = useTranslations("farms.card");
  const tCommon = useTranslations("common");

  return (
    <Card className={cn("transition-shadow", isActive && "ring-2 ring-primary")}>
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <div>
            <h3 className="font-heading text-base font-semibold text-foreground">
              {farm.farmName}
            </h3>
            <p className="mt-1 flex items-start gap-1.5 text-sm text-muted-foreground">
              <MapPin className="mt-0.5 size-3.5 shrink-0" />
              {farm.address}
            </p>
          </div>
          {isActive && (
            <span className="inline-flex shrink-0 items-center gap-1 rounded-full bg-success-bg px-2.5 py-1 text-xs font-medium text-success-text">
              <Star className="size-3" />
              {t("active")}
            </span>
          )}
        </div>

        <p className="text-xs text-muted-foreground">
          {/* Isolated so "lat, long" keeps its order inside right-to-left text. */}
          <span dir="ltr">
            {farm.latitude.toFixed(6)}, {farm.longitude.toFixed(6)}
          </span>
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
            {!isActive && (
              <Button type="button" size="sm" variant="secondary" onClick={onSetActive}>
                {t("setActive")}
              </Button>
            )}
            <LinkButton
              href={`/farms/${farm.farmId}/edit`}
              size="sm"
              variant="outline"
            >
              <Pencil className="size-3.5" />
              {tCommon("edit")}
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
