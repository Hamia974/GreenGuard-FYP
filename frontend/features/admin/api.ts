import { apiClient } from "@/lib/api-client";

import type {
  AdminDashboardSummary,
  AdminPredictionListItem,
  AdminPredictionListParams,
  AdminUserDetail,
  AdminUserListItem,
  AdminUserListParams,
  AiModuleStatus,
  PlatformStatistics,
  SystemHealth,
  UserStatus,
} from "./types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data?: T;
}

interface RawDashboardSummary {
  total_users: number;
  active_users: number;
  total_predictions: number;
  system_status: string;
}

interface RawUserListItem {
  user_id: string;
  full_name: string;
  email: string;
  status: UserStatus;
  role: "Farmer" | "Admin";
}

interface RawUserDetail extends RawUserListItem {
  profile_image: string | null;
  prediction_count: number;
  registration_date: string;
}

interface RawPredictionListItem {
  prediction_id: string;
  user: string;
  diagnosis: string | null;
  confidence: number | null;
  created_at: string;
}

interface RawAiModuleStatus {
  image_module: string;
  soil_module: string;
  weather_module: string;
  fusion_module: string;
}

interface RawSystemHealth {
  backend: string;
  database: string;
  ai_services: string;
  weather_api: string;
}

interface RawPlatformStatistics {
  total_users: number;
  total_predictions: number;
  active_users: number;
  most_detected_disease: string | null;
  most_recommended_crop: string | null;
}

function mapDashboardSummary(raw: RawDashboardSummary): AdminDashboardSummary {
  return {
    totalUsers: raw.total_users,
    activeUsers: raw.active_users,
    totalPredictions: raw.total_predictions,
    systemStatus: raw.system_status,
  };
}

function mapUserListItem(raw: RawUserListItem): AdminUserListItem {
  return {
    userId: raw.user_id,
    fullName: raw.full_name,
    email: raw.email,
    status: raw.status,
    role: raw.role,
  };
}

function mapUserDetail(raw: RawUserDetail): AdminUserDetail {
  return {
    ...mapUserListItem(raw),
    profileImage: raw.profile_image,
    predictionCount: raw.prediction_count,
    registrationDate: raw.registration_date,
  };
}

function mapPredictionListItem(raw: RawPredictionListItem): AdminPredictionListItem {
  return {
    predictionId: raw.prediction_id,
    user: raw.user,
    diagnosis: raw.diagnosis,
    confidence: raw.confidence,
    createdAt: raw.created_at,
  };
}

function mapAiModuleStatus(raw: RawAiModuleStatus): AiModuleStatus {
  return {
    imageModule: raw.image_module,
    soilModule: raw.soil_module,
    weatherModule: raw.weather_module,
    fusionModule: raw.fusion_module,
  };
}

function mapSystemHealth(raw: RawSystemHealth): SystemHealth {
  return {
    backend: raw.backend,
    database: raw.database,
    aiServices: raw.ai_services,
    weatherApi: raw.weather_api,
  };
}

function mapPlatformStatistics(raw: RawPlatformStatistics): PlatformStatistics {
  return {
    totalUsers: raw.total_users,
    totalPredictions: raw.total_predictions,
    activeUsers: raw.active_users,
    mostDetectedDisease: raw.most_detected_disease,
    mostRecommendedCrop: raw.most_recommended_crop,
  };
}

/** GET /api/v1/admin/dashboard/ per REST_API_SPEC.md section 8. */
export async function fetchAdminDashboard(): Promise<AdminDashboardSummary> {
  const { data } = await apiClient.get<ApiEnvelope<RawDashboardSummary>>("/admin/dashboard/");
  return mapDashboardSummary(data.data as RawDashboardSummary);
}

/** GET /api/v1/admin/users/ per REST_API_SPEC.md section 8. */
export async function fetchAdminUsers(params: AdminUserListParams): Promise<AdminUserListItem[]> {
  const { data } = await apiClient.get<ApiEnvelope<RawUserListItem[]>>("/admin/users/", {
    params: {
      page: params.page,
      limit: params.limit,
      search: params.search || undefined,
      status: params.status || undefined,
      sort: params.sort,
    },
  });
  return (data.data ?? []).map(mapUserListItem);
}

/** GET /api/v1/admin/users/{user_id}/ per REST_API_SPEC.md section 8. */
export async function fetchAdminUserDetail(userId: string): Promise<AdminUserDetail> {
  const { data } = await apiClient.get<ApiEnvelope<RawUserDetail>>(`/admin/users/${userId}/`);
  return mapUserDetail(data.data as RawUserDetail);
}

/** PUT /api/v1/admin/users/{user_id}/status/ per REST_API_SPEC.md section 8. */
export async function updateAdminUserStatus(userId: string, status: UserStatus): Promise<void> {
  await apiClient.put(`/admin/users/${userId}/status/`, { status });
}

/** DELETE /api/v1/admin/users/{user_id}/ per REST_API_SPEC.md section 8. */
export async function deleteAdminUser(userId: string): Promise<void> {
  await apiClient.delete(`/admin/users/${userId}/`);
}

/** GET /api/v1/admin/predictions/ per REST_API_SPEC.md section 8. */
export async function fetchAdminPredictions(
  params: AdminPredictionListParams
): Promise<AdminPredictionListItem[]> {
  const { data } = await apiClient.get<ApiEnvelope<RawPredictionListItem[]>>("/admin/predictions/", {
    params: {
      page: params.page,
      limit: params.limit,
      search: params.search || undefined,
      status: params.status || undefined,
      sort: params.sort,
    },
  });
  return (data.data ?? []).map(mapPredictionListItem);
}

/** DELETE /api/v1/admin/predictions/{prediction_id}/ per REST_API_SPEC.md section 8. */
export async function deleteAdminPrediction(predictionId: string): Promise<void> {
  await apiClient.delete(`/admin/predictions/${predictionId}/`);
}

/** GET /api/v1/admin/ai-monitoring/ per REST_API_SPEC.md section 8. */
export async function fetchAiMonitoring(): Promise<AiModuleStatus> {
  const { data } = await apiClient.get<ApiEnvelope<RawAiModuleStatus>>("/admin/ai-monitoring/");
  return mapAiModuleStatus(data.data as RawAiModuleStatus);
}

/** GET /api/v1/admin/system-health/ per REST_API_SPEC.md section 8. */
export async function fetchSystemHealth(): Promise<SystemHealth> {
  const { data } = await apiClient.get<ApiEnvelope<RawSystemHealth>>("/admin/system-health/");
  return mapSystemHealth(data.data as RawSystemHealth);
}

/** GET /api/v1/admin/statistics/ per REST_API_SPEC.md section 8. */
export async function fetchPlatformStatistics(): Promise<PlatformStatistics> {
  const { data } = await apiClient.get<ApiEnvelope<RawPlatformStatistics>>("/admin/statistics/");
  return mapPlatformStatistics(data.data as RawPlatformStatistics);
}
