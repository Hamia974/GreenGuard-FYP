export type UserRole = "Farmer" | "Admin";

export interface UserProfile {
  userId: string;
  fullName: string;
  email: string;
  role: UserRole;
  isVerified: boolean;
  profileImage: string | null;
  createdAt: string;
}

export interface ProfileUpdatePayload {
  fullName: string;
  profileImageFile?: File;
}

export interface ChangePasswordPayload {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export interface DeleteAccountPayload {
  currentPassword: string;
}
