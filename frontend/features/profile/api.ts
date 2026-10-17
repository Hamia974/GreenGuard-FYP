import { apiClient } from "@/lib/api-client";

import type {
  ChangePasswordPayload,
  DeleteAccountPayload,
  ProfileUpdatePayload,
  UserProfile,
} from "./types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data?: T;
}

interface RawProfile {
  user_id: string;
  full_name: string;
  email: string;
  role: string;
  is_verified?: boolean;
  profile_image: string | null;
  created_at: string;
}

function mapProfile(raw: RawProfile): UserProfile {
  return {
    userId: raw.user_id,
    fullName: raw.full_name,
    email: raw.email,
    role: raw.role as UserProfile["role"],
    isVerified: raw.is_verified ?? false,
    profileImage: raw.profile_image,
    createdAt: raw.created_at,
  };
}

export async function fetchUserProfile(): Promise<UserProfile> {
  const { data } = await apiClient.get<ApiEnvelope<RawProfile>>("/profile/");
  return mapProfile(data.data as RawProfile);
}

export async function updateUserProfile(payload: ProfileUpdatePayload): Promise<void> {
  const formData = new FormData();
  formData.append("full_name", payload.fullName);
  if (payload.profileImageFile) {
    formData.append("profile_image", payload.profileImageFile);
  }
  await apiClient.put("/profile/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
}

export async function changeUserPassword(payload: ChangePasswordPayload): Promise<void> {
  await apiClient.post("/auth/change-password/", {
    current_password: payload.currentPassword,
    new_password: payload.newPassword,
    confirm_password: payload.confirmPassword,
  });
}

export async function deleteUserAccount(payload: DeleteAccountPayload): Promise<void> {
  await apiClient.delete("/profile/", {
    data: { current_password: payload.currentPassword },
  });
}
