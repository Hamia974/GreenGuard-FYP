"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { dashboardOverviewQueryKey } from "@/features/dashboard/hooks";

import { deleteNotification, fetchNotifications, markNotificationAsRead } from "./api";

export const notificationsQueryKey = ["notifications"] as const;

export function useNotifications() {
  return useQuery({
    queryKey: notificationsQueryKey,
    queryFn: fetchNotifications,
  });
}

/** Invalidates the notification list and the dashboard badge count together,
 * since REST_API_SPEC.md section 7's Notification Rules require the badge
 * to "update automatically" whenever read/delete state changes. */
function useInvalidateNotifications() {
  const queryClient = useQueryClient();
  return () => {
    queryClient.invalidateQueries({ queryKey: notificationsQueryKey });
    queryClient.invalidateQueries({ queryKey: dashboardOverviewQueryKey });
  };
}

export function useMarkNotificationAsRead() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: (notificationId: string) => markNotificationAsRead(notificationId),
    onSuccess: invalidate,
  });
}

export function useDeleteNotification() {
  const invalidate = useInvalidateNotifications();
  return useMutation({
    mutationFn: (notificationId: string) => deleteNotification(notificationId),
    onSuccess: invalidate,
  });
}
