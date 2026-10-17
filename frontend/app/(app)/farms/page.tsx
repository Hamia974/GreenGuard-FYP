"use client";

import { AlertCircle, MapPinPlus, Sprout } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { LinkButton } from "@/components/ui/link-button";
import { Spinner } from "@/components/ui/spinner";
import { FarmCard } from "@/features/farms/components/farm-card";
import { useDeleteFarm, useFarms } from "@/features/farms/hooks";
import { useParseApiError } from "@/lib/i18n/use-api-error";
import { useActiveFarm } from "@/providers/active-farm-provider";

export default function FarmsPage() {
  const t = useTranslations("farms");
  const parseApiError = useParseApiError();
  const { data: farms, isLoading, isError } = useFarms();
  const deleteFarm = useDeleteFarm();
  const { activeFarmId, setActiveFarmId } = useActiveFarm();

  const [confirmingFarmId, setConfirmingFarmId] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleConfirmDelete = async (farmId: string) => {
    setDeleteError(null);
    try {
      await deleteFarm.mutateAsync(farmId);
      if (activeFarmId === farmId) {
        setActiveFarmId(null);
      }
      setConfirmingFarmId(null);
    } catch (error) {
      setDeleteError(parseApiError(error).message);
    }
  };

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-3xl font-bold text-foreground">{t("list.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("list.description")}</p>
        </div>
        <LinkButton href="/farms/new" className="h-11 rounded-2xl px-5">
          <MapPinPlus className="size-4" />
          {t("addFarm")}
        </LinkButton>
      </div>

      {deleteError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{deleteError}</AlertDescription>
        </Alert>
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Spinner className="size-6" />
        </div>
      )}

      {isError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{t("list.loadError")}</AlertDescription>
        </Alert>
      )}

      {!isLoading && !isError && farms?.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border bg-card py-16 text-center">
          <Sprout className="size-8 text-muted-foreground" />
          <p className="text-base font-medium text-foreground">{t("list.emptyTitle")}</p>
          <p className="max-w-sm text-sm text-muted-foreground">{t("list.emptyDescription")}</p>
          <LinkButton href="/farms/new" className="mt-2 h-11 rounded-2xl px-5">
            {t("addFarm")}
          </LinkButton>
        </div>
      )}

      {!isLoading && !isError && farms && farms.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {farms.map((farm) => (
            <FarmCard
              key={farm.farmId}
              farm={farm}
              isActive={activeFarmId === farm.farmId}
              isDeleting={deleteFarm.isPending && confirmingFarmId === farm.farmId}
              isConfirmingDelete={confirmingFarmId === farm.farmId}
              onSetActive={() => setActiveFarmId(farm.farmId)}
              onRequestDelete={() => setConfirmingFarmId(farm.farmId)}
              onCancelDelete={() => setConfirmingFarmId(null)}
              onConfirmDelete={() => handleConfirmDelete(farm.farmId)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
