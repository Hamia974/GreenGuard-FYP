export type UserRole = "Farmer" | "Admin";

export interface AuthUser {
  userId: string;
  fullName: string;
  email: string;
  role: UserRole;
  isVerified: boolean;
  profileImage: string | null;
  createdAt: string | null;
}

export interface LoginPayload {
  email: string;
  password: string;
  /** false makes the session end when the browser closes. */
  rememberMe?: boolean;
}

export interface RegisterPayload {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
}
