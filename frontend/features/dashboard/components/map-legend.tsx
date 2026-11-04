"use client";

import { useTranslations } from "next-intl";

import styles from "../home.module.css";
import type { FarmMapStatus } from "../lib/farm-map";

const ORDER: FarmMapStatus[] = ["critical", "risk", "watch", "healthy", "unknown"];
const DOTS: Record<FarmMapStatus, string> = {
  critical: styles.dotCritical,
  risk: styles.dotRisk,
  watch: styles.dotWatch,
  healthy: styles.dotHealthy,
  unknown: styles.dotNone,
};

/** How many farms are in each state, as a key to the pin colours. */
export function MapLegend({ statuses }: { statuses: FarmMapStatus[] }) {
  const t = useTranslations("dashboard.status");
  const tLegend = useTranslations("dashboard.legend");
  const shown = ORDER.filter((status) => statuses.includes(status));
  if (shown.length === 0) return null;

  return (
    <ul className={styles.legend} aria-label={tLegend("label")}>
      {shown.map((status) => (
        <li key={status}>
          <i className={`${styles.dot} ${DOTS[status]}`} aria-hidden="true" />
          {t(status)}
          <b>{statuses.filter((value) => value === status).length}</b>
        </li>
      ))}
    </ul>
  );
}
