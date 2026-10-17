"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  changeUserPassword,
  deleteUserAccount,
  fetchUserProfile,
  updateUserProfile,
} from "./api";
import type { ChangePasswordPayload, DeleteAccountPayload, ProfileUpdatePayload } from "./types";

export const profileQueryKey = ["profile"] as const;

export function useUserProfile() {
  return useQuery({ queryKey: profileQueryKey, queryFn: fetchUserProfile });
}

export function useUpdateUserProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: ProfileUpdatePayload) => updateUserProfile(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: profileQueryKey });
    },
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (payload: ChangePasswordPayload) => changeUserPassword(payload),
  });
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: (payload: DeleteAccountPayload) => deleteUserAccount(payload),
  });
}
