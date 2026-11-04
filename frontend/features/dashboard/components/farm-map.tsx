"use client";

import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef } from "react";

import styles from "../home.module.css";
import {
  createFarmMap,
  type FarmMapArea,
  type FarmMapController,
  type FarmMapFarm,
} from "../lib/farm-map";

interface FarmMapProps {
  farms: FarmMapFarm[];
  selectedId: string | null;
  onSelect: (farmId: string) => void;
  /** Free space on the map, in canvas pixels, so pins stay clear of the overlays. */
  getArea: (width: number, height: number) => FarmMapArea;
  /** Changes whenever the overlays change size. */
  layoutKey: string;
  /** Overlays drawn on top of the map: the status bar and the legend. */
  children?: React.ReactNode;
}

/** The farm map: Green Guard's signature view of every farm. Clicking a pin selects that farm. */
export function FarmMap({ farms, selectedId, onSelect, getArea, layoutKey, children }: FarmMapProps) {
  const t = useTranslations("dashboard.map");
  const locale = useLocale();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const controllerRef = useRef<FarmMapController | null>(null);
  const callbacks = useRef({ getArea, onSelect });
  callbacks.current = { getArea, onSelect };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    controllerRef.current = createFarmMap(canvas, {
      getArea: (width, height) => callbacks.current.getArea(width, height),
      onSelect: (farmId) => callbacks.current.onSelect(farmId),
    });
    return () => {
      controllerRef.current?.destroy();
      controllerRef.current = null;
    };
  }, []);

  useEffect(() => {
    controllerRef.current?.update({
      farms,
      selectedId,
      rtl: document.documentElement.dir === "rtl",
    });
  }, [farms, selectedId, locale, layoutKey]);

  return (
    <section className={styles.map} aria-label={t("label")}>
      <canvas ref={canvasRef} className={styles.mapCanvas} aria-hidden="true" />
      {farms.length === 0 && <p className={styles.mapEmpty}>{t("empty")}</p>}
      <span className={styles.mapTag}>{t("note")}</span>
      {children}
    </section>
  );
}
