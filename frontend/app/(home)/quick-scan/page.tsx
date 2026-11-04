"use client";

import { Plus } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useMemo } from "react";

import { useFarms } from "@/features/farms/hooks";
import { LeafHeader } from "@/features/leaf-test/components/leaf-header";
import { LeafTestFlow } from "@/features/leaf-test/components/leaf-test-flow";
import styles from "@/features/leaf-test/leaf-test.module.css";
import { cn } from "@/lib/utils";
import { useActiveFarm } from "@/providers/active-farm-provider";

export default function LeafTestPage() {
  const t = useTranslations("leafTest");
  const router = useRouter();
  const farms = useFarms();
  const { activeFarmId, setActiveFarmId } = useActiveFarm();
  const farmList = useMemo(() => farms.data ?? [], [farms.data]);
  const activeFarm = farmList.find((farm) => farm.farmId === activeFarmId);

  // Like the dashboard: with no farm chosen yet, use the first one.
  useEffect(() => {
    if (!activeFarm && farmList.length > 0) setActiveFarmId(farmList[0].farmId);
  }, [activeFarm, farmList, setActiveFarmId]);

  return (
    <div className={styles.page}>
      <LeafHeader />

      {farms.isLoading && <div className={styles.skeleton} style={{ height: 420 }} aria-hidden="true" />}

      {!farms.isLoading && farmList.length === 0 && (
        <div className={cn(styles.card, styles.empty)}>
          <h2>{t("noFarm.title")}</h2>
          <p>{t("noFarm.description")}</p>
          <Link href="/farms/new" className={cn(styles.btn, styles.btnPrimary)}>
            <Plus strokeWidth={1.75} aria-hidden="true" />
            {t("noFarm.action")}
          </Link>
        </div>
      )}

      {activeFarm && (
        <LeafTestFlow
          key={activeFarm.farmId}
          farm={activeFarm}
          onComplete={(prediction) => router.push(`/predictions/${prediction.predictionId}`)}
        />
      )}
    </div>
  );
}
