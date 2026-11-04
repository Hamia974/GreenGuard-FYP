"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { HeaderControls } from "@/features/dashboard/components/navigation";

import styles from "../leaf-test.module.css";

/** Back to Home, the page title and the shared header controls (farm, language, alerts, account). */
export function LeafHeader() {
  const t = useTranslations("leafTest");
  return (
    <header className={styles.head}>
      <div className={styles.headText}>
        <Link href="/dashboard" className={styles.crumb}>
          <ArrowLeft strokeWidth={1.75} aria-hidden="true" />
          {t("back")}
        </Link>
        <h1 className={styles.title}>{t("title")}</h1>
      </div>
      <HeaderControls />
    </header>
  );
}
