"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  deleteAdminPrediction,
  deleteAdminUser,
  fetchAdminDashboard,
  fetchAdminPredictions,
  fetchAdminUserDetail,
  fetchAdminUsers,
  fetchAiMonitoring,
  fetchPlatformStatistics,
  fetchSystemHealth,
  updateAdminUserStatus,
} from "./api";
import type {
  AdminPredictionListParams,
  AdminUserListParams,
  UserStatus,
} from "./types";

export const adminDashboardQueryKey = ["admin", "dashboard"] as const;
export const adminUsersQueryKey = (params: AdminUserListParams) =>
  ["admin", "users", params] as const;
export const adminUserDetailQueryKey = (userId: string) => ["admin", "users", userId] as const;
export const adminPredictionsQueryKey = (params: AdminPredictionListParams) =>
  ["admin", "predictions", params] as const;
export const adminAiMonitoringQueryKey = ["admin", "ai-monitoring"] as const;
export const adminSystemHealthQueryKey = ["admin", "system-health"] as const;
export const adminStatisticsQueryKey = ["admin", "statistics"] as const;

export function useAdminDashboard() {
  return useQuery({ queryKey: adminDashboardQueryKey, queryFn: fetchAdminDashboard });
}

export function useAdminUsers(params: AdminUserListParams) {
  return useQuery({
    queryKey: adminUsersQueryKey(params),
    queryFn: () => fetchAdminUsers(params),
  });
}

export function useAdminUserDetail(userId: string | undefined) {
  return useQuery({
    queryKey: adminUserDetailQueryKey(userId ?? ""),
    queryFn: () => fetchAdminUserDetail(userId as string),
    enabled: !!userId,
  });
}

export function useUpdateAdminUserStatus() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, status }: { userId: string; status: UserStatus }) =>
      updateAdminUserStatus(userId, status),
    onSuccess: (_data, { userId }) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: adminUserDetailQueryKey(userId) });
      queryClient.invalidateQueries({ queryKey: adminDashboardQueryKey });
    },
  });
}

export function useDeleteAdminUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (userId: string) => deleteAdminUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      queryClient.invalidateQueries({ queryKey: adminDashboardQueryKey });
      queryClient.invalidateQueries({ queryKey: adminStatisticsQueryKey });
    },
  });
}

export function useAdminPredictions(params: AdminPredictionListParams) {
  return useQuery({
    queryKey: adminPredictionsQueryKey(params),
    queryFn: () => fetchAdminPredictions(params),
  });
}

export function useDeleteAdminPrediction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (predictionId: string) => deleteAdminPrediction(predictionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "predictions"] });
      queryClient.invalidateQueries({ queryKey: adminDashboardQueryKey });
      queryClient.invalidateQueries({ queryKey: adminStatisticsQueryKey });
    },
  });
}

export function useAiMonitoring() {
  return useQuery({ queryKey: adminAiMonitoringQueryKey, queryFn: fetchAiMonitoring });
}

export function useSystemHealth() {
  return useQuery({ queryKey: adminSystemHealthQueryKey, queryFn: fetchSystemHealth });
}

export function usePlatformStatistics() {
  return useQuery({ queryKey: adminStatisticsQueryKey, queryFn: fetchPlatformStatistics });
}
