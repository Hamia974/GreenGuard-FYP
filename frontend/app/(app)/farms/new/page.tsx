"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { FarmForm } from "@/features/farms/components/farm-form";
import { useCreateFarm } from "@/features/farms/hooks";
import type { FarmPayload } from "@/features/farms/types";

export default function NewFarmPage() {
  const t = useTranslations("farms");
  const router = useRouter();
  const createFarm = useCreateFarm();

  const handleSubmit = async (values: FarmPayload) => {
    const farm = await createFarm.mutateAsync(values);
    router.push(`/farms?created=${farm.farmId}`);
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
          <h1 className="font-heading text-2xl font-bold text-foreground">{t("addFarm")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("create.description")}</p>
        </div>

        <FarmForm
          onSubmit={handleSubmit}
          submitLabel={t("create.submit")}
          submittingLabel={t("create.submitting")}
        />
      </div>
    </div>
  );
}
