"use client";

import { AlertCircle, ScanLine, Search } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { useAdminPredictions, useDeleteAdminPrediction } from "@/features/admin/hooks";
import type { AdminPredictionListParams, PredictionStatusFilter } from "@/features/admin/types";
import { DiseaseName } from "@/features/module1/components/disease-name";
import { useParseApiError } from "@/lib/i18n/use-api-error";

const LIMIT = 20;

export default function AdminPredictionsPage() {
  const t = useTranslations("admin.predictionsPage");
  const tCommon = useTranslations("common");
  const tUnits = useTranslations("units");
  const format = useFormatter();
  const parseApiError = useParseApiError();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [statusFilter, setStatusFilter] = useState<PredictionStatusFilter | "">("");
  const [sort, setSort] = useState<AdminPredictionListParams["sort"]>("newest");
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setPage(1);
      setSearch(searchInput);
    }, 400);
    return () => clearTimeout(timeout);
  }, [searchInput]);

  const predictions = useAdminPredictions({
    page,
    limit: LIMIT,
    search,
    status: statusFilter || undefined,
    sort,
  });
  const deletePrediction = useDeleteAdminPrediction();

  const rows = predictions.data ?? [];
  const hasNextPage = rows.length === LIMIT;

  const handleConfirmDelete = async (predictionId: string) => {
    setActionError(null);
    try {
      await deletePrediction.mutateAsync(predictionId);
      setConfirmingId(null);
    } catch (error) {
      setActionError(parseApiError(error).message);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3 rounded-2xl bg-card p-4 shadow-[var(--shadow-color-sm)]">
        <div className="flex min-w-48 flex-1 flex-col gap-1.5">
          <label
            htmlFor="admin-predictions-search"
            className="text-xs font-medium text-muted-foreground"
          >
            {tCommon("search")}
          </label>
          <div className="relative">
            <Search className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              id="admin-predictions-search"
              className="ps-9"
              placeholder={t("searchPlaceholder")}
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
            />
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="admin-predictions-status"
            className="text-xs font-medium text-muted-foreground"
          >
            {t("status")}
          </label>
          <select
            id="admin-predictions-status"
            value={statusFilter}
            onChange={(event) => {
              setPage(1);
              setStatusFilter(event.target.value as PredictionStatusFilter | "");
            }}
            className="h-10 rounded-xl border border-input bg-background px-3 text-sm text-foreground"
          >
            <option value="">{tCommon("all")}</option>
            <option value="completed">{t("statuses.completed")}</option>
            <option value="pending">{t("statuses.pending")}</option>
            <option value="processing">{t("statuses.processing")}</option>
            <option value="failed">{t("statuses.failed")}</option>
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="admin-predictions-sort" className="text-xs font-medium text-muted-foreground">
            {tCommon("sort")}
          </label>
          <select
            id="admin-predictions-sort"
            value={sort}
            onChange={(event) => {
              setPage(1);
              setSort(event.target.value as AdminPredictionListParams["sort"]);
            }}
            className="h-10 rounded-xl border border-input bg-background px-3 text-sm text-foreground"
          >
            <option value="newest">{tCommon("newest")}</option>
            <option value="oldest">{tCommon("oldest")}</option>
          </select>
        </div>
      </div>

      {actionError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{actionError}</AlertDescription>
        </Alert>
      )}

      {predictions.isLoading && (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full rounded-xl" />
          ))}
        </div>
      )}

      {!predictions.isLoading && predictions.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{parseApiError(predictions.error).message}</AlertDescription>
        </Alert>
      )}

      {!predictions.isLoading && !predictions.isError && rows.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card py-16 text-center">
          <ScanLine className="size-8 text-muted-foreground" />
          <p className="text-base font-medium text-foreground">{t("emptyTitle")}</p>
          <p className="max-w-sm text-sm text-muted-foreground">{t("emptyDescription")}</p>
        </div>
      )}

      {!predictions.isLoading && !predictions.isError && rows.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("table.user")}</TableHead>
                <TableHead>{t("table.disease")}</TableHead>
                <TableHead>{t("table.confidence")}</TableHead>
                <TableHead>{t("table.created")}</TableHead>
                <TableHead className="text-end">{t("table.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((row) => (
                <TableRow key={row.predictionId}>
                  <TableCell className="font-medium">{row.user}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {row.diagnosis ? (
                      <DiseaseName displayName={row.diagnosis} />
                    ) : (
                      t("uncertain")
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {row.confidence !== null
                      ? tUnits("percent", { value: (row.confidence * 100).toFixed(0) })
                      : "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {format.dateTime(new Date(row.createdAt), "date")}
                  </TableCell>
                  <TableCell>
                    <div className="flex justify-end gap-2">
                      {confirmingId === row.predictionId ? (
                        <>
                          <Button
                            type="button"
                            variant="destructive"
                            size="sm"
                            disabled={deletePrediction.isPending}
                            onClick={() => handleConfirmDelete(row.predictionId)}
                          >
                            {tCommon("confirm")}
                          </Button>
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            onClick={() => setConfirmingId(null)}
                          >
                            {tCommon("cancel")}
                          </Button>
                        </>
                      ) : (
                        <Button
                          type="button"
                          variant="destructive"
                          size="sm"
                          onClick={() => setConfirmingId(row.predictionId)}
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
