"use client";

import { AlertCircle, MapPinPlus, Sprout } from "lucide-react";
import { useTranslations } from "next-intl";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { AccountInformationCard } from "@/features/profile/components/account-information-card";
import { ChangePasswordForm } from "@/features/profile/components/change-password-form";
import { DeleteAccountSection } from "@/features/profile/components/delete-account-section";
import { EditProfileForm } from "@/features/profile/components/edit-profile-form";
import { ProfileHeader } from "@/features/profile/components/profile-header";
import {
  useChangePassword,
  useDeleteAccount,
  useUpdateUserProfile,
  useUserProfile,
} from "@/features/profile/hooks";
import type {
  ChangePasswordFormValues,
  DeleteAccountFormValues,
  EditProfileFormValues,
} from "@/features/profile/schemas";
import { useAuth } from "@/providers/auth-provider";

export default function ProfilePage() {
  const t = useTranslations("profile");
  const tFarms = useTranslations("farms");
  const { refreshUser } = useAuth();
  const { data: profile, isLoading, isError } = useUserProfile();

  const updateProfile = useUpdateUserProfile();
  const changePassword = useChangePassword();
  const deleteAccount = useDeleteAccount();

  const handleUpdateProfile = async (values: EditProfileFormValues, imageFile?: File) => {
    await updateProfile.mutateAsync({ fullName: values.fullName, profileImageFile: imageFile });
    await refreshUser();
  };

  const handleChangePassword = async (values: ChangePasswordFormValues) => {
    await changePassword.mutateAsync({
      currentPassword: values.currentPassword,
      newPassword: values.newPassword,
      confirmPassword: values.confirmPassword,
    });
  };

  const handleDeleteAccount = async (values: DeleteAccountFormValues) => {
    await deleteAccount.mutateAsync({ currentPassword: values.currentPassword });
    // The DELETE response already cleared the session cookies; a full
    // reload drops all in-memory auth and query state for the old account.
    window.location.href = "/login";
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 px-4 py-10 sm:px-6">
      <div>
        <h1 className="font-heading text-3xl font-bold text-foreground">{t("title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("description")}</p>
      </div>

      {isLoading && (
        <div className="flex flex-col gap-6">
          <Skeleton className="h-32 w-full rounded-2xl" />
          <Skeleton className="h-64 w-full rounded-2xl" />
        </div>
      )}

      {!isLoading && isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{t("loadError")}</AlertDescription>
        </Alert>
      )}

      {!isLoading && !isError && profile && (
        <>
          <ProfileHeader profile={profile} />

          <AccountInformationCard profile={profile} />

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{t("sections.profileInformation")}</CardTitle>
            </CardHeader>
            <CardContent>
              <EditProfileForm profile={profile} onSubmit={handleUpdateProfile} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{t("sections.changePassword")}</CardTitle>
            </CardHeader>
            <CardContent>
              <ChangePasswordForm onSubmit={handleChangePassword} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Sprout className="size-5 text-primary" />
                {tFarms("manageFarms")}
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">{t("sections.manageFarmsDescription")}</p>
              <LinkButton href="/farms" size="sm">
                <MapPinPlus className="size-3.5" />
                {tFarms("goToFarms")}
              </LinkButton>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">{t("sections.dangerZone")}</CardTitle>
            </CardHeader>
            <CardContent>
              <DeleteAccountSection onConfirm={handleDeleteAccount} />
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
