"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { DiseaseName } from "@/features/module1/components/disease-name";

import styles from "../home.module.css";
import type { FarmStatus } from "../lib/farm-status";
import { StatusPill } from "./status-pill";

interface FarmStatusBarProps {
  farmName: string;
  status: FarmStatus;
  isLoading: boolean;
}

/**
 * The one thing to know about the selected farm, laid across the top of the
 * map: its status, what caused it, and the next step.
 */
export function FarmStatusBar({ farmName, status, isLoading }: FarmStatusBarProps) {
  const t = useTranslations("dashboard.farmStatus");
  const tLevels = useTranslations("dashboard.levels");
  const { leaf, risk } = status;
  const match = leaf?.detail?.disease?.prediction;

  const causes: React.ReactNode[] = [];
  if (leaf?.status === "diseased") {
    causes.push(
      t.rich("disease", {
        name: () => (
          <DiseaseName displayName={match?.displayName ?? leaf.row.diagnosis ?? ""} disease={match?.disease} />
        ),
      })
    );
  }
  if (leaf?.status === "uncertain") causes.push(t("unclear"));
  if (risk) causes.push(t("risk", { risk: t(`riskNames.${risk.key}`), level: tLevels(risk.level) }));

  let sentence: React.ReactNode;
  if (causes.length > 0) {
    sentence = causes.map((cause, index) => (
      <span key={index}>
        {index > 0 && t("and")}
        {cause}
      </span>
    ));
  } else {
    sentence = status.status ? t("clear") : t("empty");
  }

  let action = { href: "/quick-scan", label: t("checkLeaf") };
  if (leaf?.status === "diseased") action = { href: `/predictions/${leaf.row.predictionId}`, label: t("openReport") };
  else if (leaf?.status === "uncertain") action = { href: "/quick-scan", label: t("retake") };
  else if (risk) action = { href: "/weather", label: t("seeWeather") };

  return (
    <div className={styles.statusBar} aria-live="polite">
      <div className={styles.statusText}>
        <p className={styles.label}>{t("today", { farm: farmName })}</p>
        {isLoading ? (
          <div className={styles.skeleton} style={{ height: 28, width: "min(420px, 100%)" }} />
        ) : (
          <p className={styles.statusSentence}>{sentence}</p>
        )}
      </div>
      {!isLoading && status.status && <StatusPill status={status.status} />}
      {!isLoading && (
        <Link href={action.href} className={styles.statusAction}>
          {action.label}
          <ArrowRight strokeWidth={1.75} className="rtl:-scale-x-100" aria-hidden="true" />
        </Link>
      )}
    </div>
  );
}
