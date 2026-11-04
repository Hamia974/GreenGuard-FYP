"use client";

import { useMessages, useTranslations } from "next-intl";

import type { WeatherReport } from "@/features/weather/types";
import { labelFor } from "@/lib/i18n/labels";
import { cn } from "@/lib/utils";

import styles from "../home.module.css";
import { weatherRisks, type Status } from "../lib/home-status";
import { useCountUp } from "../lib/use-count-up";
import { StatusPill } from "./status-pill";

const LEVEL_STEPS = { Low: 1, Moderate: 2, High: 3 } as const;
const BAR_CLASSES: Record<Status, string> = {
  healthy: styles.barHealthy,
  watch: styles.barWatch,
  risk: styles.barRisk,
  critical: styles.barCritical,
};
const RING_LENGTH = 2 * Math.PI * 15;

interface WeatherInstrumentsProps {
  hasFarm: boolean;
  report: WeatherReport | null | undefined;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

/**
 * Module 3's readings for the selected farm as instruments: the temperature
 * with tomorrow's, a humidity ring, 7-day rain, wind, and one meter per risk
 * with Module 3's own reason under the worst one.
 */
export function WeatherInstruments({ hasFarm, report, isLoading, isError, onRetry }: WeatherInstrumentsProps) {
  const t = useTranslations("dashboard.weather");
  const tUnits = useTranslations("units");
  const messages = useMessages();
  const risks = weatherRisks(report);
  const temperature = useCountUp(report ? Math.round(report.weather.temperature) : null);
  const humidity = report ? Math.round(report.weather.humidity) : 0;

  return (
    <section className={styles.instruments} aria-labelledby="home-weather-title">
      <p id="home-weather-title" className={styles.label}>
        {t("label")}
      </p>

      {!hasFarm && <p className={styles.note}>{t("noFarm")}</p>}
      {hasFarm && isLoading && <div className={styles.skeleton} style={{ height: 220 }} />}
      {hasFarm && !isLoading && (isError || !report) && (
        <p className={styles.note}>
          {t("unavailable")}{" "}
          <button type="button" className={styles.textButton} onClick={onRetry}>
            {t("retry")}
          </button>
        </p>
      )}

      {report && (
        <>
          <div className={styles.tempRow}>
            <span className={styles.temperature}>{tUnits("celsius", { value: temperature ?? 0 })}</span>
            {report.forecast && (
              <span className={styles.note}>{t("tomorrow", { value: Math.round(report.forecast.temperature) })}</span>
            )}
          </div>

          <div className={styles.readings}>
            <div className={styles.reading}>
              <span className={styles.label}>{t("humidity")}</span>
              <span className={styles.ring} role="img" aria-label={t("humidityValue", { value: humidity })}>
                <svg viewBox="0 0 36 36" aria-hidden="true">
                  <circle cx="18" cy="18" r="15" className={styles.ringTrack} />
                  <circle
                    cx="18"
                    cy="18"
                    r="15"
                    className={styles.ringFill}
                    style={{ strokeDasharray: RING_LENGTH, strokeDashoffset: RING_LENGTH * (1 - humidity / 100) }}
                  />
                </svg>
                <b>{humidity}%</b>
              </span>
            </div>
            <div className={styles.reading}>
              <span className={styles.label}>{t("rain")}</span>
              <span className={styles.readingValue}>
                {report.weather.rainfallLast7DaysMm}
                <small> mm</small>
              </span>
            </div>
            <div className={styles.reading}>
              <span className={styles.label}>{t("wind")}</span>
              <span className={styles.readingValue}>
                {report.weather.windSpeed}
                <small> m/s</small>
              </span>
            </div>
          </div>

          <ul className={styles.meters}>
            {risks.map((risk, index) => (
              <li key={risk.key} className={styles.meter}>
                <div className={styles.meterHead}>
                  <b>{t(`risks.${risk.key}`)}</b>
                  <StatusPill status={risk.status} label={labelFor(messages.weather.riskLevels, risk.level)} />
                </div>
                <div className={styles.meterBar} aria-hidden="true">
                  {[1, 2, 3].map((step) => (
                    <i key={step} className={cn(step <= LEVEL_STEPS[risk.level] && BAR_CLASSES[risk.status])} />
                  ))}
                </div>
                {index === 0 && risk.status !== "healthy" && <p className={styles.reason}>{risk.reason}</p>}
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
