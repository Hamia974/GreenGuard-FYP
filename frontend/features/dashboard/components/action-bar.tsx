"use client";

import { ArrowRight, CloudSun, ScanLine } from "lucide-react";
import Link from "next/link";
import { useFormatter, useTranslations } from "next-intl";

import { DiseaseName } from "@/features/module1/components/disease-name";
import type { RiskLevel, WeatherReport } from "@/features/weather/types";
import { cn } from "@/lib/utils";

import styles from "../home.module.css";
import { weatherRisks, type RiskKey } from "../lib/home-status";
import type { RecentCheck } from "../lib/leaf-status";

interface ActionBarProps {
  hasFarm: boolean;
  /** The selected farm's latest soil score, from its reports; null when none was saved. */
  soilScore: number | null;
  /** The selected farm's latest leaf check, if any. */
  leafCheck: RecentCheck | undefined;
  /** The selected farm's weather report, while it loads or when it failed: undefined. */
  weather: WeatherReport | null | undefined;
}

const GAUGE_HEIGHT: Record<RiskLevel, string> = {
  Low: "34%",
  Moderate: "67%",
  High: "100%",
};
const GAUGE_ORDER: RiskKey[] = ["drought", "fungal", "heat"];

/** A line-drawn leaf: its veins trace and a scan line sweeps it on hover. */
function LeafArt() {
  return (
    <span className={styles.leafArt} aria-hidden="true">
      <svg viewBox="0 0 104 112">
        <path className={styles.leafLine} d="M52 106 C 52 80 52 60 52 22" />
        <path
          className={styles.leafLine}
          d="M52 10 C 84 26 96 58 82 86 C 72 104 52 106 52 106 C 52 106 32 104 22 86 C 8 58 20 26 52 10 Z"
        />
        <g className={styles.leafVeins}>
          <path d="M52 40 L 74 28" />
          <path d="M52 56 L 80 46" />
          <path d="M52 72 L 78 66" />
          <path d="M52 40 L 30 28" />
          <path d="M52 56 L 24 46" />
          <path d="M52 72 L 26 66" />
        </g>
        <g className={styles.leafSpots}>
          <circle cx="68" cy="58" r="3.5" />
          <circle cx="62" cy="70" r="2.5" />
          <circle cx="72" cy="74" r="2" />
        </g>
      </svg>
      <i className={styles.leafScan} />
    </span>
  );
}

/** A soil cross-section in three layers with a sprout that grows on hover. */
function SoilArt() {
  return (
    <svg className={styles.soilArt} viewBox="0 0 92 112" aria-hidden="true">
      <path className={styles.soilStem} d="M46 62 C 46 52 46 44 46 32" />
      <path
        className={cn(styles.soilLeaf, styles.soilLeafStart)}
        d="M46 46 C 34 46 26 38 24 26 C 36 26 44 34 46 46 Z"
      />
      <path
        className={cn(styles.soilLeaf, styles.soilLeafEnd)}
        d="M46 38 C 48 26 56 18 70 16 C 70 30 60 38 46 38 Z"
      />
      <rect
        className={styles.soilTop}
        x="2"
        y="62"
        width="88"
        height="14"
        rx="2"
      />
      <rect
        className={styles.soilMid}
        x="2"
        y="78"
        width="88"
        height="14"
        rx="2"
      />
      <rect
        className={styles.soilDeep}
        x="2"
        y="94"
        width="88"
        height="16"
        rx="2"
      />
      <g className={styles.soilGrains}>
        <circle cx="16" cy="100" r="1.5" />
        <circle cx="40" cy="104" r="1.5" />
        <circle cx="66" cy="99" r="1.5" />
        <circle cx="80" cy="105" r="1.5" />
      </g>
    </svg>
  );
}

interface SoilTestCardProps {
  hasFarm: boolean;
  /** The farm's latest soil score; null when none was saved. */
  soilScore: number | null;
}

/** The Soil test card: last score beside a soil cross-section, with the questionnaire button. */
export function SoilTestCard({ hasFarm, soilScore }: SoilTestCardProps) {
  const t = useTranslations("dashboard.actions");
  return (
    <Link
      href={hasFarm ? "/module2" : "/farms/new"}
      className={cn(styles.action, styles.actionSoil)}
    >
      <span className={styles.actionBody}>
        <span className={styles.actionText}>
          <span className={styles.actionTag}>{t("soilTag")}</span>
          <b className={styles.actionTitle}>{t("soil")}</b>
          {hasFarm && soilScore !== null && (
            <span className={styles.actionMetric}>
              {soilScore}
              <small>/100</small>
            </span>
          )}
          <small className={styles.actionSub}>
            {hasFarm ? t("soilNone") : t("needFarm")}
          </small>
          <span className={cn(styles.actionGo, styles.actionButton)}>
            {hasFarm ? t("soilGo") : t("addFarm")}
            <ArrowRight strokeWidth={1.75} aria-hidden="true" />
          </span>
        </span>
        <SoilArt />
      </span>
    </Link>
  );
}

interface WeatherTestCardProps {
  /** The weather report to summarise; undefined while it loads or when it failed. */
  weather: WeatherReport | null | undefined;
  /** Replaces the "Today" tag, for example "At the time" on a saved test. */
  tag?: string;
}

/** The Weather test card: the worst risk in words and all three as gauges. */
export function WeatherTestCard({ weather, tag }: WeatherTestCardProps) {
  const t = useTranslations("dashboard.actions");
  const tLevels = useTranslations("dashboard.levels");
  const tRisks = useTranslations("dashboard.farmStatus.riskNames");

  const risks = weatherRisks(weather);
  const worst = risks[0];
  let weatherSub = t("weatherSub");
  if (worst) {
    weatherSub =
      worst.level === "Low"
        ? t("weatherAllLow")
        : t("weatherWorst", {
            risk: tRisks(worst.key),
            level: tLevels(worst.level),
          });
  }
  const gauges = GAUGE_ORDER.map((key) =>
    risks.find((risk) => risk.key === key),
  ).filter((risk): risk is NonNullable<typeof risk> => !!risk);
  const gaugeLabel = gauges
    .map((risk) => `${tRisks(risk.key)}: ${tLevels(risk.level)}`)
    .join(", ");

  return (
    <Link href="/weather" className={cn(styles.action, styles.actionWeather)}>
      <span className={styles.actionBody}>
        <span className={styles.actionText}>
          <span className={styles.actionTag}>
            <CloudSun strokeWidth={1.75} aria-hidden="true" />
            {tag ?? t("weatherTag")}
          </span>
          <b className={styles.actionTitle}>{t("weather")}</b>
          <small className={styles.actionSub}>{weatherSub}</small>
          <span className={cn(styles.actionGo, styles.actionButton)}>
            {t("weatherGo")}
            <ArrowRight strokeWidth={1.75} aria-hidden="true" />
          </span>
        </span>
        {gauges.length > 0 && (
          <span className={styles.gauges} role="img" aria-label={gaugeLabel}>
            {gauges.map((risk) => (
              <span key={risk.key} className={styles.gauge}>
                <span className={styles.gaugeTrack}>
                  <i
                    className={styles[`gauge_${risk.status}`]}
                    style={
                      {
                        "--level": GAUGE_HEIGHT[risk.level],
                      } as React.CSSProperties
                    }
                  />
                </span>
                <em>{t(`gauge.${risk.key}`)}</em>
              </span>
            ))}
          </span>
        )}
      </span>
    </Link>
  );
}

/**
 * The three checks as distinct instruments: the leaf check shows its last
 * result, soil its last score beside a cross-section, and weather today's
 * three risk levels as gauges.
 */
export function ActionBar({
  hasFarm,
  soilScore,
  leafCheck,
  weather,
}: ActionBarProps) {
  const t = useTranslations("dashboard.actions");
  const format = useFormatter();

  // Leaf: what the last check on this farm found.
  let leafSub: React.ReactNode = t("leafSub");
  if (!hasFarm) {
    leafSub = t("needFarm");
  } else if (leafCheck?.status) {
    const date = format.dateTime(new Date(leafCheck.row.createdAt), {
      day: "numeric",
      month: "short",
    });
    const confidence =
      leafCheck.row.confidence !== null
        ? Math.round(leafCheck.row.confidence * 100)
        : null;
    if (leafCheck.status === "diseased") {
      const match = leafCheck.detail?.disease?.prediction;
      leafSub = t.rich(
        confidence !== null ? "leafLastDisease" : "leafLastDiseaseNoScore",
        {
          date,
          value: confidence ?? 0,
          name: () => (
            <DiseaseName
              displayName={match?.displayName ?? leafCheck.row.diagnosis ?? ""}
              disease={match?.disease}
            />
          ),
        },
      );
    } else if (leafCheck.status === "healthy") {
      leafSub = t("leafLastHealthy", { date });
    } else {
      leafSub = t("leafLastUnclear");
    }
  }

  return (
    <nav className={styles.actions} aria-label={t("label")}>
      <Link
        href={hasFarm ? "/quick-scan" : "/farms/new"}
        className={cn(styles.action, styles.actionLeaf)}
      >
        <span className={styles.actionBody}>
          <span className={styles.actionText}>
            <span className={styles.actionTag}>
              <ScanLine strokeWidth={1.75} aria-hidden="true" />
              {t("leafTag")}
            </span>
            <b className={styles.actionTitle}>{t("leaf")}</b>
            <small className={styles.actionSub}>{leafSub}</small>
            <span className={cn(styles.actionGo, styles.actionButton)}>
              {hasFarm ? t("leafGo") : t("addFarm")}
              <ArrowRight strokeWidth={1.75} aria-hidden="true" />
            </span>
          </span>
          <LeafArt />
        </span>
      </Link>

      <SoilTestCard hasFarm={hasFarm} soilScore={soilScore} />
      <WeatherTestCard weather={weather} />
    </nav>
  );
}
