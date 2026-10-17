"use client";

import { Bell } from "lucide-react";
import { useTranslations } from "next-intl";

import { LinkButton } from "@/components/ui/link-button";
import { useDashboardOverview } from "@/features/dashboard/hooks";

/** Top-right notification bell per UI_SPECIFICATION.md section 7.12: shows
 * the unread count (capped at "99+") and opens the Notification Center. */
export function NotificationBell() {
  const t = useTranslations("navigation");
  const overview = useDashboardOverview();
  const unreadCount = overview.data?.notificationCount ?? 0;

  return (
    <LinkButton
      href="/notifications"
      aria-label={
        unreadCount > 0
          ? t("notificationsWithCount", { count: unreadCount })
          : t("notifications")
      }
      variant="ghost"
      size="icon"
      className="relative"
    >
      <Bell className="size-5" />
      {unreadCount > 0 && (
        <span className="absolute -end-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-error-text px-1 text-[10px] font-semibold leading-none text-white">
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      )}
    </LinkButton>
  );
}
