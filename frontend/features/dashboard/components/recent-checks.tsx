"use client";

import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";
import { useState } from "react";

import type { Farm } from "@/features/farms/types";
import { DiseaseName } from "@/features/module1/components/disease-name";
import { cn } from "@/lib/utils";

import styles from "../home.module.css";
import { LEAF_TO_STATUS } from "../lib/home-status";
import type { RecentCheck } from "../lib/leaf-status";
import { StatusPill } from "./status-pill";

const LEAF_FALLBACK = "/images/crops/cucumber.jpg";

/** A report photo from the API's media storage, falling back to a bundled picture when it fails to load. */
function Thumb({ src }: { src: string | null | undefined }) {
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const shown = src && src !== failedSrc ? src : null;
  return (
    // Report photos come from the API's media storage, so a plain img is used.
    // eslint-disable-next-line @next/next/no-img-element
    <img
      className={styles.thumb}
      src={shown ?? LEAF_FALLBACK}
      alt=""
      onError={() => shown && setFailedSrc(shown)}
    />
  );
}

interface RecentChecksProps {
  checks: RecentCheck[];
  farms: Farm[];
  activeFarmId: string | null;
  limit: number;
  isLoading: boolean;
  isError: boolean;
}

/** The latest leaf checks, newest first. Disease results are set apart from routine ones. */
export function RecentChecks({ checks, farms, activeFarmId, limit, isLoading, isError }: RecentChecksProps) {
  const t = useTranslations("dashboard.recent");
  const format = useFormatter();
  const shown = checks.slice(0, limit);

  return (
    <section className={styles.recent} aria-labelledby="home-recent-title">
      <div className={styles.sectionHead}>
        <p id="home-recent-title" className={styles.label}>
          {t("title")}
        </p>
        <Link href="/history" className={styles.link}>
          {t("seeAll")}
        </Link>
      </div>

      {isLoading && <div className={styles.skeleton} style={{ height: 112 }} aria-hidden="true" />}
      {!isLoading && isError && <p className={styles.note}>{t("loadError")}</p>}
      {!isLoading && !isError && shown.length === 0 && <p className={styles.note}>{t("empty")}</p>}

      {shown.length > 0 && (
        <ul className={styles.checks}>
          {shown.map(({ row, detail, status }) => {
            const farm = farms.find((item) => item.farmId === detail?.farmId);
            const farmLabel = detail?.farmId === activeFarmId ? t("thisFarm") : farm?.farmName;
            const match = detail?.disease?.prediction;
            const confidence =
              status !== "uncertain" && row.confidence !== null
                ? t("confident", { value: Math.round(row.confidence * 100) })
                : null;
            const date = format.dateTime(new Date(row.createdAt), { day: "numeric", month: "short" });

            let title: React.ReactNode = t("pendingTitle");
            let href = `/predictions/${row.predictionId}`;
            if (status === "diseased") {
              title = t.rich("diseasedTitle", {
                name: () => (
                  <DiseaseName displayName={match?.displayName ?? row.diagnosis ?? ""} disease={match?.disease} />
                ),
              });
            } else if (status === "uncertain") {
              title = t("uncertainTitle");
              href = "/quick-scan";
            } else if (status === "healthy") {
              title = t("healthyTitle");
            }

            return (
              <li key={row.predictionId}>
                <Link href={href} className={cn(styles.check, status === "diseased" && styles.checkDisease)}>
                  <Thumb src={detail?.uploadedImage} />
                  <span className={styles.checkText}>
                    <b>{title}</b>
                    <span>{[confidence, date, farmLabel].filter(Boolean).join(" · ")}</span>
                  </span>
                  {status && <StatusPill status={LEAF_TO_STATUS[status]} />}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
