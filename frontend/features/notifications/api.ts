import { apiClient } from "@/lib/api-client";

import type { NotificationItem } from "./types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data?: T;
}

interface RawNotificationItem {
  notification_id: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

function mapNotification(raw: RawNotificationItem): NotificationItem {
  return {
    notificationId: raw.notification_id,
    title: raw.title,
    message: raw.message,
    isRead: raw.is_read,
    createdAt: raw.created_at,
  };
}

/** GET /api/v1/notifications/ per REST_API_SPEC.md section 7. Returns all, newest first. */
export async function fetchNotifications(): Promise<NotificationItem[]> {
  const { data } = await apiClient.get<ApiEnvelope<RawNotificationItem[]>>("/notifications/");
  return (data.data ?? []).map(mapNotification);
}

/** PUT /api/v1/notifications/{notification_id}/read/ per REST_API_SPEC.md section 7. */
export async function markNotificationAsRead(notificationId: string): Promise<void> {
  await apiClient.put(`/notifications/${notificationId}/read/`);
}

/** DELETE /api/v1/notifications/{notification_id}/ per REST_API_SPEC.md section 7. */
export async function deleteNotification(notificationId: string): Promise<void> {
  await apiClient.delete(`/notifications/${notificationId}/`);
}
