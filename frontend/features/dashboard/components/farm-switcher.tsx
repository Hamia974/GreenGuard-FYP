"use client";

import { ChevronDown, MapPin } from "lucide-react";
import { useTranslations } from "next-intl";

import type { Farm } from "@/features/farms/types";

import styles from "../home.module.css";

interface FarmSwitcherProps {
  farms: Farm[];
  activeFarmId: string | null;
  onChange: (farmId: string) => void;
}

/** Chooses which farm the whole home page shows. */
export function FarmSwitcher({ farms, activeFarmId, onChange }: FarmSwitcherProps) {
  const t = useTranslations("dashboard.switcher");
  return (
    <div className={styles.switcher}>
      <MapPin className={styles.switcherIcon} strokeWidth={1.75} aria-hidden="true" />
      <label htmlFor="home-farm" className="sr-only">
        {t("label")}
      </label>
      <select id="home-farm" value={activeFarmId ?? ""} onChange={(event) => onChange(event.target.value)}>
        {farms.map((farm) => (
          <option key={farm.farmId} value={farm.farmId}>
            {farm.farmName}
          </option>
        ))}
      </select>
      <ChevronDown className={styles.switcherChevron} strokeWidth={1.75} aria-hidden="true" />
    </div>
  );
}
