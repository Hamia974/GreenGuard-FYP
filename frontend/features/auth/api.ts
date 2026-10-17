import { apiClient } from "@/lib/api-client";

import type { AuthUser, LoginPayload, RegisterPayload } from "./types";

interface ApiEnvelope<T> {
  success: boolean;
  message: string;
  data?: T;
}

interface RawUser {
  user_id: string;
  full_name: string;
  email: string;
  role: string;
  is_verified?: boolean;
  profile_image?: string | null;
  created_at?: string;
}

/** Tokens are set as HttpOnly cookies by the backend, never returned here. */
interface LoginResponseData {
  user: RawUser;
}

interface RegisterResponseData {
  user_id: string;
  full_name: string;
  email: string;
}

interface ProfileResponseData extends RawUser {
  profile_image: string | null;
  created_at: string;
}

function mapUser(raw: RawUser): AuthUser {
  return {
    userId: raw.user_id,
    fullName: raw.full_name,
    email: raw.email,
    role: raw.role as AuthUser["role"],
    isVerified: raw.is_verified ?? false,
    profileImage: raw.profile_image ?? null,
    createdAt: raw.created_at ?? null,
  };
}

export async function loginRequest(payload: LoginPayload): Promise<AuthUser> {
  const { data } = await apiClient.post<ApiEnvelope<LoginResponseData>>("/auth/login/", {
    email: payload.email,
    password: payload.password,
    remember_me: payload.rememberMe ?? true,
  });
  return mapUser((data.data as LoginResponseData).user);
}

export async function registerRequest(
  payload: RegisterPayload
): Promise<RegisterResponseData> {
  const { data } = await apiClient.post<ApiEnvelope<RegisterResponseData>>(
    "/auth/register/",
    {
      full_name: payload.fullName,
      email: payload.email,
      password: payload.password,
      confirm_password: payload.confirmPassword,
    }
  );
  return data.data as RegisterResponseData;
}

export async function logoutRequest(): Promise<void> {
  await apiClient.post("/auth/logout/");
}

export async function fetchProfile(): Promise<AuthUser> {
  const { data } = await apiClient.get<ApiEnvelope<ProfileResponseData>>(
    "/profile/"
  );
  return mapUser(data.data as ProfileResponseData);
}

export async function forgotPasswordRequest(email: string): Promise<void> {
  await apiClient.post("/auth/forgot-password/", { email });
}

export async function resetPasswordRequest(
  token: string,
  newPassword: string,
  confirmPassword: string
): Promise<void> {
  await apiClient.post("/auth/reset-password/", {
    token,
    new_password: newPassword,
    confirm_password: confirmPassword,
  });
}

export async function verifyEmailRequest(token: string): Promise<void> {
  await apiClient.post("/auth/verify-email/", { token });
}

export async function resendVerificationRequest(): Promise<void> {
  await apiClient.post("/auth/resend-verification/");
}
