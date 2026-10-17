import { Bell } from "lucide-react";
import { useTranslations } from "next-intl";

import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface NotificationsPreviewCardProps {
  notificationCount: number | undefined;
  isLoading: boolean;
}

export function NotificationsPreviewCard({
  notificationCount,
  isLoading,
}: NotificationsPreviewCardProps) {
  const t = useTranslations("dashboard.notificationsPreview");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg">
          <Bell className="size-5 text-primary" />
          {t("title")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-16 w-full" />
        ) : (
          <div className="flex flex-col items-center gap-2 py-4 text-center">
            <p className="text-sm font-medium text-foreground">
              {notificationCount && notificationCount > 0
                ? t("unread", { count: notificationCount })
                : t("empty")}
            </p>
            <p className="max-w-xs text-xs text-muted-foreground">{t("description")}</p>
            <LinkButton
              href="/notifications"
              variant="outline"
              size="sm"
              className="mt-1"
            >
              {t("viewAll")}
            </LinkButton>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
