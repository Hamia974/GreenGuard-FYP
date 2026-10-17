"use client";

import { CheckCheck, Clock, Trash2 } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { NotificationItem } from "@/features/notifications/types";

interface NotificationCardProps {
  notification: NotificationItem;
  isMarkingRead: boolean;
  isDeleting: boolean;
  isConfirmingDelete: boolean;
  onMarkAsRead: () => void;
  onRequestDelete: () => void;
  onCancelDelete: () => void;
  onConfirmDelete: () => void;
}

export function NotificationCard({
  notification,
  isMarkingRead,
  isDeleting,
  isConfirmingDelete,
  onMarkAsRead,
  onRequestDelete,
  onCancelDelete,
  onConfirmDelete,
}: NotificationCardProps) {
  const t = useTranslations("notifications.card");
  const tCommon = useTranslations("common");
  const format = useFormatter();

  return (
    <Card
      className={cn(
        "transition-shadow",
        !notification.isRead && "border-s-4 border-s-primary",
      )}
    >
      <CardContent className="flex flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          {/* Title and message are server-stored text, shown as delivered. */}
          <h3
            dir="auto"
            className={cn(
              "text-base",
              notification.isRead
                ? "font-medium text-muted-foreground"
                : "font-semibold text-foreground",
            )}
          >
            {notification.title}
          </h3>
          {!notification.isRead && (
            <span className="mt-1 size-2 shrink-0 rounded-full bg-primary" aria-label={t("unread")} />
          )}
        </div>

        <p dir="auto" className="text-sm text-muted-foreground">
          {notification.message}
        </p>

        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Clock className="size-3.5 shrink-0" />
          {format.dateTime(new Date(notification.createdAt), "dateTimeMedium")}
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
            <Button type="button" size="sm" variant="ghost" disabled={isDeleting} onClick={onCancelDelete}>
              {tCommon("cancel")}
            </Button>
          </div>
        ) : (
          <div className="mt-1 flex flex-wrap items-center gap-2">
            {!notification.isRead && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={isMarkingRead}
                onClick={onMarkAsRead}
              >
                <CheckCheck className="size-3.5" />
                {isMarkingRead ? t("marking") : t("markAsRead")}
              </Button>
            )}
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
