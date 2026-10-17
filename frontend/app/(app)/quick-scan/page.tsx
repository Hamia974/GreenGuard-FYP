"use client";

import { ArrowLeft, ScanLine } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";

import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { QuickScanFlow } from "@/features/predictions/components/quick-scan-flow";
import { useFarms } from "@/features/farms/hooks";
import { useActiveFarm } from "@/providers/active-farm-provider";

export default function QuickScanPage() {
  const t = useTranslations("quickScan.page");
  const tNav = useTranslations("navigation");
  const tFarms = useTranslations("farms");
  const router = useRouter();
  const farms = useFarms();
  const { activeFarmId } = useActiveFarm();
  const activeFarm = farms.data?.find((farm) => farm.farmId === activeFarmId);

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 px-4 py-10 sm:px-6">
      <Link
        href="/dashboard"
        className="inline-flex w-fit items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="size-4 rtl:-scale-x-100" />
        {tNav("backToDashboard")}
      </Link>

      <div className="flex items-center gap-3">
        <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <ScanLine className="size-5" />
        </div>
        <div>
          <h1 className="font-heading text-2xl font-bold text-foreground">{t("title")}</h1>
          <p className="text-sm text-muted-foreground">{t("description")}</p>
        </div>
      </div>

      {farms.isLoading && <Skeleton className="h-64 w-full rounded-2xl" />}

      {!farms.isLoading && !activeFarm && (
        <div className="rounded-2xl bg-card p-6 text-center shadow-[var(--shadow-color-md)] sm:p-8">
          <p className="font-medium text-foreground">{tFarms("noFarmSelected")}</p>
          <p className="mt-1 text-sm text-muted-foreground">{t("noFarmDescription")}</p>
          <LinkButton href="/farms" className="mt-4">
            {tFarms("goToFarms")}
          </LinkButton>
        </div>
      )}

      {activeFarm && (
        <QuickScanFlow
          farm={activeFarm}
          onComplete={(prediction) => router.push(`/predictions/${prediction.predictionId}`)}
        />
      )}
    </div>
  );
}
