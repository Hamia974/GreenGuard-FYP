export type NotificationType = "system" | "prediction" | "weather";

export interface NotificationItem {
  notificationId: string;
  title: string;
  message: string;
  isRead: boolean;
  createdAt: string;
}
