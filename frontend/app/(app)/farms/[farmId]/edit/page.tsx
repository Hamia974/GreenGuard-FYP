"use client";

import { AlertCircle, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { use } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Spinner } from "@/components/ui/spinner";
import { FarmForm } from "@/features/farms/components/farm-form";
import { useFarm, useUpdateFarm } from "@/features/farms/hooks";
import type { FarmPayload } from "@/features/farms/types";

interface EditFarmPageProps {
  params: Promise<{ farmId: string }>;
}

export default function EditFarmPage({ params }: EditFarmPageProps) {
  const t = useTranslations("farms");
  const tCommon = useTranslations("common");
  const { farmId } = use(params);
  const router = useRouter();
  const { data: farm, isLoading, isError } = useFarm(farmId);
  const updateFarm = useUpdateFarm(farmId);

  const handleSubmit = async (values: FarmPayload) => {
    await updateFarm.mutateAsync(values);
    router.push("/farms");
  };

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-6 px-4 py-10 sm:px-6">
      <Link
        href="/farms"
        className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4 rtl:-scale-x-100" />
        {t("backToFarms")}
      </Link>

      <div className="rounded-2xl bg-card p-6 shadow-[var(--shadow-color-md)] sm:p-8">
        <div className="mb-6">
          <h1 className="font-heading text-2xl font-bold text-foreground">{t("edit.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("edit.description")}</p>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-10">
            <Spinner className="size-6" />
          </div>
        )}

        {isError && (
          <Alert variant="destructive">
            <AlertCircle />
            <AlertDescription>{t("edit.notFound")}</AlertDescription>
          </Alert>
        )}

        {farm && (
          <FarmForm
            farm={farm}
            onSubmit={handleSubmit}
            submitLabel={tCommon("saveChanges")}
            submittingLabel={tCommon("saving")}
          />
        )}
      </div>
    </div>
  );
}
