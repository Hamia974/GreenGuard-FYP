"use client";

import { AlertCircle, ArrowLeft } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useFormatter, useMessages, useTranslations } from "next-intl";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAdminUserDetail,
  useDeleteAdminUser,
  useUpdateAdminUserStatus,
} from "@/features/admin/hooks";
import { labelFor } from "@/lib/i18n/labels";
import { useParseApiError } from "@/lib/i18n/use-api-error";

export default function AdminUserDetailPage() {
  const t = useTranslations("admin.userDetail");
  const tCommon = useTranslations("common");
  const messages = useMessages();
  const format = useFormatter();
  const parseApiError = useParseApiError();
  const params = useParams<{ userId: string }>();
  const router = useRouter();
  const userId = params.userId;

  const detail = useAdminUserDetail(userId);
  const updateStatus = useUpdateAdminUserStatus();
  const deleteUser = useDeleteAdminUser();

  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleToggleStatus = async () => {
    if (!detail.data) return;
    setActionError(null);
    try {
      await updateStatus.mutateAsync({
        userId,
        status: detail.data.status === "Active" ? "Inactive" : "Active",
      });
    } catch (error) {
      setActionError(parseApiError(error).message);
    }
  };

  const handleConfirmDelete = async () => {
    setActionError(null);
    try {
      await deleteUser.mutateAsync(userId);
      router.push("/admin/users");
    } catch (error) {
      setActionError(parseApiError(error).message);
      setConfirmingDelete(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <LinkButton
        href="/admin/users"
        variant="ghost"
        size="sm"
        className="w-fit"
      >
        <ArrowLeft className="size-4 rtl:-scale-x-100" />
        {t("backToUsers")}
      </LinkButton>

      {actionError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      )}

      {detail.isLoading && <Skeleton className="h-64 w-full rounded-2xl" />}

      {!detail.isLoading && detail.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{parseApiError(detail.error).message}</AlertDescription>
        </Alert>
      )}

      {!detail.isLoading && !detail.isError && detail.data && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div className="flex items-center gap-4">
              {detail.data.profileImage ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={detail.data.profileImage}
                  alt={detail.data.fullName}
                  className="size-14 rounded-full object-cover ring-1 ring-border"
                />
              ) : (
                <div className="flex size-14 items-center justify-center rounded-full bg-muted text-lg font-semibold text-muted-foreground">
                  {detail.data.fullName.charAt(0).toUpperCase()}
                </div>
              )}
              <div>
                <CardTitle>{detail.data.fullName}</CardTitle>
                <p className="text-sm text-muted-foreground">{detail.data.email}</p>
              </div>
            </div>
            <div className="flex gap-2">
              <Badge variant={detail.data.role === "Admin" ? "info" : "secondary"}>
                {labelFor(messages.common.roles, detail.data.role)}
              </Badge>
              <Badge variant={detail.data.status === "Active" ? "success" : "error"}>
                {labelFor(messages.common.userStatuses, detail.data.status)}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="flex flex-col gap-6">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <p className="text-xs text-muted-foreground">{t("predictionCount")}</p>
                <p className="text-sm font-medium text-foreground">{detail.data.predictionCount}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{t("registrationDate")}</p>
                <p className="text-sm font-medium text-foreground">
                  {format.dateTime(new Date(detail.data.registrationDate), "date")}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap gap-2 border-t border-border pt-4">
              <Button
                type="button"
                variant="outline"
                disabled={updateStatus.isPending}
                onClick={handleToggleStatus}
              >
                {detail.data.status === "Active" ? t("deactivateAccount") : t("activateAccount")}
              </Button>

              {confirmingDelete ? (
                <>
                  <Button
                    type="button"
                    variant="destructive"
                    disabled={deleteUser.isPending}
                    onClick={handleConfirmDelete}
                  >
                    {t("confirmDelete")}
                  </Button>
                  <Button type="button" variant="ghost" onClick={() => setConfirmingDelete(false)}>
                    {tCommon("cancel")}
                  </Button>
                </>
              ) : (
                <Button type="button" variant="destructive" onClick={() => setConfirmingDelete(true)}>
                  {t("deleteAccount")}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
