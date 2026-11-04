"use client";

import { AlertCircle } from "lucide-react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";

import { useFarms } from "@/features/farms/hooks";
import { LeafHeader } from "@/features/leaf-test/components/leaf-header";
import { LeafResult } from "@/features/leaf-test/components/leaf-result";
import styles from "@/features/leaf-test/leaf-test.module.css";
import { usePrediction } from "@/features/predictions/hooks";

export default function LeafTestResultPage() {
  const t = useTranslations("leafTest.result");
  const params = useParams<{ predictionId: string }>();
  const prediction = usePrediction(params.predictionId);
  const farms = useFarms();
  const farmName = farms.data?.find((farm) => farm.farmId === prediction.data?.farmId)?.farmName;

  return (
    <div className={styles.page}>
      <LeafHeader />

      {prediction.isLoading && <div className={styles.skeleton} style={{ height: 520 }} aria-hidden="true" />}

      {!prediction.isLoading && prediction.isError && (
        <p className={styles.note} role="alert">
          <AlertCircle strokeWidth={1.75} aria-hidden="true" />
          <span>{t("notFound")}</span>
        </p>
      )}

      {prediction.data && <LeafResult prediction={prediction.data} farmName={farmName} />}
    </div>
  );
}
