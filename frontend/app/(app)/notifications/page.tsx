"use client";

import { AlertCircle, CheckCircle2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Skeleton } from "@/components/ui/skeleton";
import { NotificationCard } from "@/features/notifications/components/notification-card";
import {
  useDeleteNotification,
  useMarkNotificationAsRead,
  useNotifications,
} from "@/features/notifications/hooks";
import { useParseApiError } from "@/lib/i18n/use-api-error";

export default function NotificationsPage() {
  const t = useTranslations("notifications");
  const parseApiError = useParseApiError();
  const notifications = useNotifications();
  const markAsRead = useMarkNotificationAsRead();
  const deleteNotification = useDeleteNotification();

  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const records = notifications.data ?? [];

  const handleMarkAsRead = async (notificationId: string) => {
    setActionError(null);
    try {
      await markAsRead.mutateAsync(notificationId);
    } catch (error) {
      setActionError(parseApiError(error).message);
    }
  };

  const handleConfirmDelete = async (notificationId: string) => {
    setActionError(null);
    try {
      await deleteNotification.mutateAsync(notificationId);
      setConfirmingId(null);
    } catch (error) {
      setActionError(parseApiError(error).message);
    }
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-10 sm:px-6">
      <div>
        <h1 className="font-heading text-3xl font-bold text-foreground">{t("title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("description")}</p>
      </div>

      {actionError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      )}

      {notifications.isLoading && (
        <div className="flex flex-col gap-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-28 w-full rounded-2xl" />
          ))}
        </div>
      )}

      {!notifications.isLoading && notifications.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{parseApiError(notifications.error).message}</AlertDescription>
        </Alert>
      )}

      {!notifications.isLoading && !notifications.isError && records.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card py-16 text-center">
          <CheckCircle2 className="size-8 text-muted-foreground" />
          <p className="text-base font-medium text-foreground">{t("emptyTitle")}</p>
          <p className="max-w-sm text-sm text-muted-foreground">{t("emptyDescription")}</p>
        </div>
      )}

      {!notifications.isLoading && !notifications.isError && records.length > 0 && (
        <div className="flex flex-col gap-4">
          {records.map((notification) => (
            <NotificationCard
              key={notification.notificationId}
              notification={notification}
              isMarkingRead={
                markAsRead.isPending && markAsRead.variables === notification.notificationId
              }
              isDeleting={
                deleteNotification.isPending && confirmingId === notification.notificationId
              }
              isConfirmingDelete={confirmingId === notification.notificationId}
              onMarkAsRead={() => handleMarkAsRead(notification.notificationId)}
              onRequestDelete={() => setConfirmingId(notification.notificationId)}
              onCancelDelete={() => setConfirmingId(null)}
              onConfirmDelete={() => handleConfirmDelete(notification.notificationId)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
