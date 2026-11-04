"use client";

import {
  ArrowRight,
  Camera,
  History,
  Info,
  RotateCcw,
  TriangleAlert,
} from "lucide-react";
import Link from "next/link";
import { useFormatter, useMessages, useTranslations } from "next-intl";
import { useState } from "react";

import {
  SoilTestCard,
  WeatherTestCard,
} from "@/features/dashboard/components/action-bar";
import { StatusPill } from "@/features/dashboard/components/status-pill";
import type { Status } from "@/features/dashboard/lib/home-status";
import { DiseaseName } from "@/features/module1/components/disease-name";
import type { DiseasePredictionItem } from "@/features/module1/types";
import { Module2Results } from "@/features/module2/components/module2-results";
import type { Prediction } from "@/features/predictions/types";
import { CurrentConditionsCard } from "@/features/weather/components/current-conditions-card";
import { ForecastCard } from "@/features/weather/components/forecast-card";
import { RiskAssessmentCard } from "@/features/weather/components/risk-assessment-card";
import { labelFor } from "@/lib/i18n/labels";
import { cn } from "@/lib/utils";

import styles from "../leaf-test.module.css";
import { LeafGuide } from "./leaf-test-flow";

/** 0.8812 -> 88. Display rounding only; the API value is never recalculated. */
const percent = (confidence: number) => Math.round(confidence * 100);

const TICKS = Array.from({ length: 60 }, (_, index) => index);

/** The saved photo in a round lens with a tick ring, or the leaf outline when there is none. */
function Lens({ src, onFail }: { src: string | null; onFail: () => void }) {
  const t = useTranslations("leafTest.result");
  return (
    <div className={styles.lens}>
      <svg
        className={styles.lensTicks}
        viewBox="-160 -160 320 320"
        aria-hidden="true"
      >
        {TICKS.map((index) => (
          <line
            key={index}
            className={index % 5 === 0 ? styles.lensTickBig : undefined}
            x1="0"
            y1="-158"
            x2="0"
            y2={index % 5 === 0 ? -146 : -152}
            transform={`rotate(${index * 6})`}
          />
        ))}
      </svg>
      <div className={styles.lensPhoto}>
        {src ? (
          // Report photos come from the API's media storage, so a plain img is used.
          // eslint-disable-next-line @next/next/no-img-element
          <img src={src} alt={t("photoAlt")} onError={onFail} />
        ) : (
          <div className={styles.noPhoto}>
            <LeafGuide />
            {t("noPhoto")}
          </div>
        )}
      </div>
    </div>
  );
}

/** How sure the check is, as a ring; "?" when it could not decide. */
function Ring({ value, status }: { value: number | null; status: Status }) {
  const t = useTranslations("leafTest.result");
  const tUnits = useTranslations("units");
  const radius = 46;
  const length = 2 * Math.PI * radius;
  return (
    <div className={styles.ring}>
      <svg viewBox="0 0 104 104" width="104" height="104" aria-hidden="true">
        <circle className={styles.ringTrack} cx="52" cy="52" r={radius} />
        {value !== null && (
          <circle
            className={cn(styles.ringFill, styles[`ring_${status}`])}
            cx="52"
            cy="52"
            r={radius}
            strokeDasharray={length}
            strokeDashoffset={length * (1 - value / 100)}
          />
        )}
      </svg>
      <span className={styles.ringValue}>
        <b>{value !== null ? tUnits("percent", { value }) : "?"}</b>
        <small>{value !== null ? t("sureShort") : t("ringUnsure")}</small>
      </span>
    </div>
  );
}

function Ranks({
  title,
  items,
}: {
  title: string;
  items: DiseasePredictionItem[];
}) {
  const tUnits = useTranslations("units");
  return (
    <div className={styles.ranks}>
      <p className={styles.label}>{title}</p>
      {items.length === 0 ? (
        <p className={styles.colEmpty}>—</p>
      ) : (
        <ul aria-label={title}>
          {items.map((item) => (
            <li key={item.classId}>
              <span>
                <DiseaseName
                  displayName={item.displayName}
                  disease={item.disease}
                />
              </span>
              <span className={styles.bar} aria-hidden="true">
                <i
                  className={styles.fill_mark}
                  style={{ width: `${percent(item.confidence)}%` }}
                />
              </span>
              <em>{tUnits("percent", { value: percent(item.confidence) })}</em>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

interface LeafResultProps {
  prediction: Prediction;
  farmName: string | undefined;
}

/**
 * One saved leaf test. A dark green spotlight leads with the photo in a lens,
 * the verdict and how sure the check is; below, the other likely results,
 * photo notes and details, then this farm's soil, weather and history.
 * Nothing is combined or invented.
 */
export function LeafResult({ prediction, farmName }: LeafResultProps) {
  const t = useTranslations("leafTest.result");
  const tReport = useTranslations("report.sections.weather");
  const messages = useMessages();
  const format = useFormatter();
  const [photoFailed, setPhotoFailed] = useState(false);
  const { disease, soilNutrient, weather } = prediction;
  const photo = photoFailed ? null : prediction.uploadedImage;

  const saved = new Date(prediction.createdAt);
  const date = format.dateTime(saved, {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
  const time = format.dateTime(saved, { hour: "numeric", minute: "2-digit" });

  const main = disease?.status === "ok" ? disease.prediction : null;
  let status: Status = "watch";
  let kind: "diseased" | "healthy" | "uncertain" = "uncertain";
  if (main) {
    kind = main.isHealthy ? "healthy" : "diseased";
    status = main.isHealthy ? "healthy" : "risk";
  }
  const sure = main ? percent(main.confidence) : null;
  const others = disease
    ? main
      ? disease.top3.filter((item) => item.classId !== main.classId)
      : disease.top3
    : [];
  const warnings = disease?.warnings.filter((code) => code.trim() !== "") ?? [];
  const message = disease?.message?.trim() || null;
  const cropName = disease
    ? labelFor(messages.crops, disease.detectedCrop)
    : null;

  return (
    <>
      <section className={styles.hero} aria-labelledby="leaf-verdict">
        {photo && (
          <div
            className={styles.heroBlur}
            style={{ backgroundImage: `url("${photo}")` }}
            aria-hidden="true"
          />
        )}
        <div className={styles.heroShade} aria-hidden="true" />

        <Lens src={photo} onFail={() => setPhotoFailed(true)} />

        <div className={styles.heroCopy}>
          <p className={styles.heroEyebrow}>
            {farmName
              ? t("eyebrow", { farm: farmName, date })
              : t("eyebrowNoFarm", { date })}
          </p>

          {!disease ? (
            <>
              <h2 id="leaf-verdict" className={styles.verdict}>
                {t("unavailable")}
              </h2>
            </>
          ) : (
            <>
              <div className={styles.row}>
                <StatusPill status={status} className={styles.heroPill} />
                <span className={styles.heroEyebrow}>{t(kind)}</span>
              </div>
              <h2 id="leaf-verdict" className={styles.verdict}>
                {main ? (
                  <DiseaseName
                    displayName={main.displayName}
                    disease={main.disease}
                  />
                ) : (
                  t("uncertain")
                )}
              </h2>
              <div className={styles.sure}>
                <Ring value={sure} status={status} />
                <p>
                  {sure !== null
                    ? t("sureLine", { value: sure })
                    : t("uncertainLine")}
                </p>
              </div>
            </>
          )}

          <div className={cn(styles.actions, styles.actionsStart)}>
            <Link
              href="/quick-scan"
              className={cn(styles.btn, styles.heroPrimary)}
            >
              <Camera strokeWidth={1.75} aria-hidden="true" />
              {t("checkAnother")}
            </Link>
            {(!main || warnings.length > 0) && (
              <Link
                href="/quick-scan"
                className={cn(styles.btn, styles.heroSecondary)}
              >
                <RotateCcw strokeWidth={1.75} aria-hidden="true" />
                {t("retake")}
              </Link>
            )}
          </div>
        </div>
      </section>

      {prediction.isLegacyReport && (
        <p className={styles.note}>
          <Info strokeWidth={1.75} aria-hidden="true" />
          <span>{t("legacy")}</span>
        </p>
      )}

      <div className={styles.cols}>
        <div className={styles.col}>
          <Ranks title={main ? t("alsoBe") : t("mayBe")} items={others} />
        </div>

        <div className={styles.col}>
          <p className={styles.label}>{t("photoNotes")}</p>
          {!main && disease && (
            <p className={styles.note}>
              <Info strokeWidth={1.75} aria-hidden="true" />
              <span>{t("uncertainHelp")}</span>
            </p>
          )}
          {warnings.map((code) => (
            <p key={code} className={styles.note}>
              <TriangleAlert strokeWidth={1.75} aria-hidden="true" />
              <span>{labelFor(messages.disease.warnings, code)}</span>
            </p>
          ))}
          {message && (
            <p className={styles.note}>
              <Info strokeWidth={1.75} aria-hidden="true" />
              <span dir="auto">
                <b>{t("note")}</b> {message}
              </span>
            </p>
          )}
          {main && warnings.length === 0 && !message && (
            <p className={styles.colEmpty}>{t("photoOk")}</p>
          )}
        </div>

        <div className={styles.col}>
          <p className={styles.label}>{t("detailsTitle")}</p>
          <dl
            className={styles.facts}
            style={{ gridTemplateColumns: "minmax(0, 1fr)" }}
          >
            {disease && (
              <div>
                <dt>{t("crop")}</dt>
                <dd>
                  {disease.cropSource === "user"
                    ? t("cropByYou", { crop: cropName ?? "" })
                    : t("cropDetected", { crop: cropName ?? "" })}
                </dd>
              </div>
            )}
            <div>
              <dt>{t("farm")}</dt>
              <dd>{farmName ?? "—"}</dd>
            </div>
            <div>
              <dt>{t("saved")}</dt>
              <dd>
                {date}, {time}
              </dd>
            </div>
          </dl>
          <Link href="/history" className={styles.historyLink}>
            <History strokeWidth={1.75} aria-hidden="true" />
            {t("allTests")}
            <ArrowRight strokeWidth={1.75} aria-hidden="true" />
          </Link>
        </div>
      </div>

      <div className={styles.moreCards}>
        <SoilTestCard
          hasFarm
          soilScore={soilNutrient?.overallSoilHealthScore ?? null}
        />
        <WeatherTestCard weather={weather} tag={t("strip.weatherLabel")} />
      </div>

      {(soilNutrient || weather) && (
        <details className={styles.details}>
          <summary>{t("details")}</summary>
          <div className={styles.detailsBody}>
            {soilNutrient && <Module2Results result={soilNutrient} />}
            {weather && (
              <>
                <CurrentConditionsCard weather={weather.weather} />
                <RiskAssessmentCard
                  title={tReport("environmentalRisk")}
                  assessment={weather.riskAssessment}
                />
                <ForecastCard
                  forecast={weather.forecast}
                  predictedRiskAssessment={weather.predictedRiskAssessment}
                />
              </>
            )}
          </div>
        </details>
      )}
    </>
  );
}
