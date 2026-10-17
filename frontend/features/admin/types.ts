export interface AdminDashboardSummary {
  totalUsers: number;
  activeUsers: number;
  totalPredictions: number;
  systemStatus: string;
}

export type UserStatus = "Active" | "Inactive";
export type AdminUserRole = "Farmer" | "Admin";

export interface AdminUserListItem {
  userId: string;
  fullName: string;
  email: string;
  status: UserStatus;
  role: AdminUserRole;
}

export interface AdminUserDetail extends AdminUserListItem {
  profileImage: string | null;
  predictionCount: number;
  registrationDate: string;
}

export interface AdminUserListParams {
  page?: number;
  limit?: number;
  search?: string;
  status?: UserStatus;
  sort?: "newest" | "oldest" | "name";
}

export type PredictionStatusFilter = "pending" | "processing" | "completed" | "failed";

export interface AdminPredictionListParams {
  page?: number;
  limit?: number;
  search?: string;
  status?: PredictionStatusFilter;
  sort?: "newest" | "oldest";
}

export interface AdminPredictionListItem {
  predictionId: string;
  user: string;
  /** Module 1's own disease result; null when Module 1 was uncertain. */
  diagnosis: string | null;
  /** Module 1's own confidence (0-1); null when Module 1 was uncertain. */
  confidence: number | null;
  createdAt: string;
}

export interface AiModuleStatus {
  imageModule: string;
  soilModule: string;
  weatherModule: string;
  fusionModule: string;
}

export interface SystemHealth {
  backend: string;
  database: string;
  aiServices: string;
  weatherApi: string;
}

export interface PlatformStatistics {
  totalUsers: number;
  totalPredictions: number;
  activeUsers: number;
  mostDetectedDisease: string | null;
  mostRecommendedCrop: string | null;
}
