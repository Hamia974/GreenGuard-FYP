"use client";

import { AlertCircle, ArrowLeft, Leaf, RotateCcw } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { Skeleton } from "@/components/ui/skeleton";
import { Module2Results } from "@/features/module2/components/module2-results";
import { Module2Wizard } from "@/features/module2/components/module2-wizard";
import { useSubmitModule2Analysis } from "@/features/module2/hooks";
import type { Module2Result } from "@/features/module2/types";
import { useFarms } from "@/features/farms/hooks";
import { useActiveFarm } from "@/providers/active-farm-provider";

export default function Module2Page() {
  const t = useTranslations("soil.page");
  const tNav = useTranslations("navigation");
  const tFarms = useTranslations("farms");
  const farms = useFarms();
  const { activeFarmId } = useActiveFarm();
  const activeFarm = farms.data?.find((farm) => farm.farmId === activeFarmId);
  const submitAnalysis = useSubmitModule2Analysis(activeFarm?.farmId);
  const [result, setResult] = useState<Module2Result | null>(null);

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
          <Leaf className="size-5" />
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
        <div className="rounded-2xl bg-card p-6 shadow-[var(--shadow-color-md)] sm:p-8">
          {!result && (
            <Module2Wizard
              farm={activeFarm}
              onSubmit={(values) => submitAnalysis.mutateAsync(values)}
              onComplete={setResult}
            />
          )}

          {result && (
            <div className="flex flex-col gap-5">
              <Module2Results result={result} />
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setResult(null);
                  submitAnalysis.reset();
                }}
              >
                <RotateCcw className="size-4" />
                {t("startAnother")}
              </Button>
            </div>
          )}
        </div>
      )}

      {submitAnalysis.isError && !result && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{t("submitError")}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
