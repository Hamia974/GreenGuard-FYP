"use client";

import { AlertCircle, History as HistoryIcon, ScanLine } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { HistoryCard } from "@/features/history/components/history-card";
import { HistoryFilters } from "@/features/history/components/history-filters";
import { useDeleteHistoryPrediction, useHistory } from "@/features/history/hooks";
import type { HistorySort } from "@/features/history/types";
import { useParseApiError } from "@/lib/i18n/use-api-error";

// REST_API_SPEC.md section 6 documents `page`/`limit` but no default page
// size; 10 matches UI_SPECIFICATION.md 13.18's documented pagination
// default ("10 reports per page").
const LIMIT = 10;

export default function HistoryPage() {
  const t = useTranslations("history");
  const tCommon = useTranslations("common");
  const parseApiError = useParseApiError();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState<HistorySort>("newest");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const history = useHistory({ page, limit: LIMIT, search, sort, fromDate, toDate });
  const deleteHistory = useDeleteHistoryPrediction();

  function updateFilter<T>(setter: (value: T) => void) {
    return (value: T) => {
      setPage(1);
      setter(value);
    };
  }

  const handleConfirmDelete = async (predictionId: string) => {
    setDeleteError(null);
    try {
      await deleteHistory.mutateAsync(predictionId);
      setConfirmingId(null);
    } catch (error) {
      setDeleteError(parseApiError(error).message);
    }
  };

  const records = history.data ?? [];
  // No total-count metadata is returned by GET /api/v1/history/ (per
  // REST_API_SPEC.md section 6's documented response shape, which is a
  // bare `data` array) -- a full page of results is the only available
  // signal that another page might exist.
  const hasNextPage = records.length === LIMIT;

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6">
      <div>
        <h1 className="font-heading text-3xl font-bold text-foreground">{t("title")}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t("description")}</p>
      </div>

      <HistoryFilters
        search={search}
        sort={sort}
        fromDate={fromDate}
        toDate={toDate}
        onSearchChange={updateFilter(setSearch)}
        onSortChange={updateFilter(setSort)}
        onFromDateChange={updateFilter(setFromDate)}
        onToDateChange={updateFilter(setToDate)}
      />

      {deleteError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{deleteError}</AlertDescription>
        </Alert>
      )}

      {history.isLoading && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-32 w-full rounded-2xl" />
          ))}
        </div>
      )}

      {!history.isLoading && history.isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{parseApiError(history.error).message}</AlertDescription>
        </Alert>
      )}

      {!history.isLoading && !history.isError && records.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card py-16 text-center">
          <HistoryIcon className="size-8 text-muted-foreground" />
          <p className="text-base font-medium text-foreground">{t("emptyTitle")}</p>
          <p className="max-w-sm text-sm text-muted-foreground">{t("emptyDescription")}</p>
          <LinkButton href="/quick-scan" className="mt-2 h-11 rounded-2xl px-5">
            <ScanLine className="size-4" />
            {t("emptyAction")}
          </LinkButton>
        </div>
      )}

      {!history.isLoading && !history.isError && records.length > 0 && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {records.map((record) => (
              <HistoryCard
                key={record.predictionId}
                record={record}
                isDeleting={deleteHistory.isPending && confirmingId === record.predictionId}
                isConfirmingDelete={confirmingId === record.predictionId}
                onRequestDelete={() => setConfirmingId(record.predictionId)}
                onCancelDelete={() => setConfirmingId(null)}
                onConfirmDelete={() => handleConfirmDelete(record.predictionId)}
              />
            ))}
          </div>

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
