"use client";

import { Search } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { Input } from "@/components/ui/input";
import type { HistorySort } from "@/features/history/types";

interface HistoryFiltersProps {
  search: string;
  sort: HistorySort;
  fromDate: string;
  toDate: string;
  onSearchChange: (value: string) => void;
  onSortChange: (value: HistorySort) => void;
  onFromDateChange: (value: string) => void;
  onToDateChange: (value: string) => void;
}

export function HistoryFilters({
  search,
  sort,
  fromDate,
  toDate,
  onSearchChange,
  onSortChange,
  onFromDateChange,
  onToDateChange,
}: HistoryFiltersProps) {
  const t = useTranslations("history.filters");
  const tCommon = useTranslations("common");

  // Local, immediately-typed value; the parent's `search` (and therefore the
  // API request) updates after a short pause, per UI_SPECIFICATION.md 13.4
  // ("Search should support real-time filtering") without firing a request
  // on every keystroke.
  const [searchInput, setSearchInput] = useState(search);

  useEffect(() => {
    const timeout = setTimeout(() => onSearchChange(searchInput), 400);
    return () => clearTimeout(timeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchInput]);

  return (
    <div className="flex flex-wrap items-end gap-3 rounded-2xl bg-card p-4 shadow-[var(--shadow-color-sm)]">
      <div className="flex min-w-48 flex-1 flex-col gap-1.5">
        <label htmlFor="history-search" className="text-xs font-medium text-muted-foreground">
          {tCommon("search")}
        </label>
        <div className="relative">
          <Search className="pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="history-search"
            className="ps-9"
            placeholder={t("searchPlaceholder")}
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
          />
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="history-sort" className="text-xs font-medium text-muted-foreground">
          {tCommon("sort")}
        </label>
        <select
          id="history-sort"
          value={sort}
          onChange={(event) => onSortChange(event.target.value as HistorySort)}
          className="h-10 rounded-xl border border-input bg-background px-3 text-sm text-foreground"
        >
          <option value="newest">{tCommon("newest")}</option>
          <option value="oldest">{tCommon("oldest")}</option>
        </select>
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="history-from-date" className="text-xs font-medium text-muted-foreground">
          {t("from")}
        </label>
        <Input
          id="history-from-date"
          type="date"
          className="w-40"
          value={fromDate}
          onChange={(event) => onFromDateChange(event.target.value)}
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label htmlFor="history-to-date" className="text-xs font-medium text-muted-foreground">
          {t("to")}
        </label>
        <Input
          id="history-to-date"
          type="date"
          className="w-40"
          value={toDate}
          onChange={(event) => onToDateChange(event.target.value)}
        />
      </div>
    </div>
  );
}
