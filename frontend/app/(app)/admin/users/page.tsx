"use client";

import { AlertCircle, Search, Users as UsersIcon } from "lucide-react";
import Link from "next/link";
import { useMessages, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  useAdminUsers,
  useDeleteAdminUser,
  useUpdateAdminUserStatus,
} from "@/features/admin/hooks";
import type { AdminUserListParams, UserStatus } from "@/features/admin/types";
import { labelFor } from "@/lib/i18n/labels";
import { useParseApiError } from "@/lib/i18n/use-api-error";

const LIMIT = 20;

export default function AdminUsersPage() {
  const t = useTranslations("admin.usersPage");
  const tCommon = useTranslations("common");
  const messages = useMessages();
  const parseApiError = useParseApiError();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<UserStatus | "">("");
  const [sort, setSort] = useState<AdminUserListParams["sort"]>("newest");
  const [confirmingUserId, setConfirmingUserId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setPage(1);
      setSearch(searchInput);
    }, 400);
    return () => clearTimeout(timeout);
  }, [searchInput]);

  const users = useAdminUsers({
    page,
    limit: LIMIT,
    search,
    status: status || undefined,
    sort,
  });
  const updateStatus = useUpdateAdminUserStatus();
  const deleteUser = useDeleteAdminUser();

  const rows = users.data ?? [];
  const hasNextPage = rows.length === LIMIT;

  const handleToggleStatus = async (userId: string, currentStatus: UserStatus) => {
    setActionError(null);
    try {
      await updateStatus.mutateAsync({
        userId,
        status: currentStatus === "Active" ? "Inactive" : "Active",
      });
    } catch (error) {
      setActionError(parseApiError(error).message);
    }
  };

  const handleConfirmDelete = async (userId: string) => {
    setActionError(null);
    try {
      await deleteUser.mutateAsync(userId);
      setConfirmingUserId(null);
    } catch (error) {
      setActionError(parseApiError(error).message);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3 rounded-2xl bg-card p-4 shadow-[var(--shadow-color-sm)]">
        <div className="flex min-w-48 flex-1 flex-col gap-1.5">
          <label htmlFor="admin-users-search" className="text-xs font-medium text-muted-foreground">
            {tCommon("search")}
          </label>
          <div className="relative">
            <Search className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="admin-users-search"
              className="ps-9"
              placeholder={t("searchPlaceholder")}
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="admin-users-status" className="text-xs font-medium text-muted-foreground">
            {t("status")}
          </label>
          <select
            id="admin-users-status"
            value={status}
            onChange={(event) => {
              setPage(1);
              setStatus(event.target.value as UserStatus | "");
            }}
            className="h-10 rounded-xl border border-input bg-background px-3 text-sm text-foreground"
          >
            <option value="">{tCommon("all")}</option>
            <option value="Active">{labelFor(messages.common.userStatuses, "Active")}</option>
            <option value="Inactive">{labelFor(messages.common.userStatuses, "Inactive")}</option>
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="admin-users-sort" className="text-xs font-medium text-muted-foreground">
            {tCommon("sort")}
          </label>
          <select
            id="admin-users-sort"
            value={sort}
            onChange={(event) => {
              setPage(1);
              setSort(event.target.value as AdminUserListParams["sort"]);
            }}
            className="h-10 rounded-xl border border-input bg-background px-3 text-sm text-foreground"
          >
            <option value="newest">{tCommon("newest")}</option>
            <option value="oldest">{tCommon("oldest")}</option>
            <option value="name">{t("sortByName")}</option>
          </select>
        </div>
      </div>

      {actionError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      )}

      {users.isLoading && (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full rounded-xl" />
          ))}
        </div>
      )}

      {!users.isLoading && users.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{parseApiError(users.error).message}</AlertDescription>
        </Alert>
      )}

      {!users.isLoading && !users.isError && rows.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card py-16 text-center">
          <UsersIcon className="size-8 text-muted-foreground" />
          <p className="text-base font-medium text-foreground">{t("emptyTitle")}</p>
          <p className="max-w-sm text-sm text-muted-foreground">{t("emptyDescription")}</p>
        </div>
      )}

      {!users.isLoading && !users.isError && rows.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("table.name")}</TableHead>
                <TableHead>{t("table.email")}</TableHead>
                <TableHead>{t("table.role")}</TableHead>
                <TableHead>{t("table.status")}</TableHead>
                <TableHead className="text-end">{t("table.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.userId}>
                  <TableCell>
                    <Link href={`/admin/users/${row.userId}`} className="font-medium hover:underline">
                      {row.fullName}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{row.email}</TableCell>
                  <TableCell>
                    <Badge variant={row.role === "Admin" ? "info" : "secondary"}>
                      {labelFor(messages.common.roles, row.role)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={row.status === "Active" ? "success" : "error"}>
                      {labelFor(messages.common.userStatuses, row.status)}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={updateStatus.isPending}
                        onClick={() => handleToggleStatus(row.userId, row.status)}
                      >
                        {row.status === "Active" ? t("deactivate") : t("activate")}
                      </Button>
                      {confirmingUserId === row.userId ? (
                        <>
                          <Button
                            type="button"
                            variant="destructive"
                            size="sm"
                            disabled={deleteUser.isPending}
                            onClick={() => handleConfirmDelete(row.userId)}
                          >
                            {tCommon("confirm")}
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => setConfirmingUserId(null)}
                          >
                            {tCommon("cancel")}
                          </Button>
                        </>
                      ) : (
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          onClick={() => setConfirmingUserId(row.userId)}
                        >
                          {tCommon("delete")}
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          <div className="flex items-center justify-between gap-3">
            <Button
              type="button"
              variant="outline"
              disabled={page === 1}
              onClick={() => setPage((current) => Math.max(1, current - 1))}
            >
              {tCommon("previous")}
            </Button>
            <span className="text-sm text-muted-foreground">{tCommon("page", { page })}</span>
            <Button
              type="button"
              variant="outline"
              disabled={!hasNextPage}
              onClick={() => setPage((current) => current + 1)}
            >
              {tCommon("next")}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
