"use client";

import { AlertOctagon, AlertTriangle, CheckCircle2, Droplets, Gauge, Sun } from "lucide-react";
import { useFormatter, useMessages, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { labelFor } from "@/lib/i18n/labels";
import { cn } from "@/lib/utils";

import type { ComparisonMetric, Module2BResult } from "../types";

// Farmer-facing wording for module2b's stable status enum lives in
// messages/<locale>/soil.json (results.metricStatuses) -- never show the raw
// enum value, per Module2_Frontend_Form_Spec.md's "Displaying the result".
// Each status carries its own icon so it never relies on color alone.
const STATUS_STYLES: Record<string, { className: string; icon: typeof CheckCircle2 }> = {
  ok: { className: "border-success-icon/40 bg-success-icon/10 [&>svg]:text-success-icon", icon: CheckCircle2 },
  moderate: { className: "border-warning-icon/50 bg-warning-icon/10 [&>svg]:text-warning-icon", icon: AlertTriangle },
  critical: { className: "border-error-icon/40 bg-error-icon/10 [&>svg]:text-error-icon", icon: AlertOctagon },
};

type MetricKey = "ph" | "soilMoisture" | "light";

interface MetricConfig {
  key: MetricKey;
  icon: typeof Gauge;
  /**
   * The quantity's definitional limits (pH 0-14, moisture 0-100%, lux >= 0).
   * Used only to keep the drawn scale physically sensible and to reject
   * impossible readings -- never as a healthy/unhealthy threshold.
   */
  bounds: [number, number];
  maxFractionDigits: number;
}

const METRICS: MetricConfig[] = [
  { key: "ph", icon: Gauge, bounds: [0, 14], maxFractionDigits: 2 },
  { key: "soilMoisture", icon: Droplets, bounds: [0, 100], maxFractionDigits: 1 },
  { key: "light", icon: Sun, bounds: [0, Number.POSITIVE_INFINITY], maxFractionDigits: 0 },
];

const isFiniteNumber = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value);

/**
 * Module 2B's own ideal range, validated. Returns null when it is missing or
 * malformed -- the indicator then shows "Reference range unavailable" rather
 * than guessing one. An upper value of null means "no upper limit"
 * (INTEGRATION_GUIDE.md).
 */
function readRange(metric: ComparisonMetric, [min, max]: [number, number]) {
  const [low, high] = Array.isArray(metric.idealRange) ? metric.idealRange : [null, null];
  if (!isFiniteNumber(low) || low < min || low > max) return null;
  if (high === null) return { low, high: null };
  if (!isFiniteNumber(high) || high <= low || high > max) return null;
  return { low, high };
}

function readMetric(metric: ComparisonMetric | undefined, bounds: [number, number]) {
  const current = metric && isFiniteNumber(metric.current) ? metric.current : null;
  const plausible = current !== null && current >= bounds[0] && current <= bounds[1];
  const range = metric ? readRange(metric, bounds) : null;
  return { current, plausible, range };
}

/** Purely visual window around the API's range and the reading -- not a threshold. */
function scaleFor(current: number, low: number, high: number | null, [min, max]: [number, number]) {
  const span = high === null ? low : high - low;
  const pad = span * 0.6;
  let start = Math.max(min, Math.min(low - pad, current));
  let end = Math.min(max, Math.max(high === null ? low + span * 0.8 : high + pad, current));
  // Keep a reading at the very edge from being drawn half off the track.
  const margin = (end - start) * 0.04;
  if (current <= start) start = Math.max(min, start - margin);
  if (current >= end) end = Math.min(max, end + margin);
  return (value: number) => ((value - start) / (end - start)) * 100;
}

function RangeTrack({
  current,
  low,
  high,
  bounds,
}: {
  current: number;
  low: number;
  high: number | null;
  bounds: [number, number];
}) {
  const toPct = scaleFor(current, low, high, bounds);
  const bandStart = toPct(low);
  const bandEnd = high === null ? 100 : toPct(high);
  const marker = Math.min(100, Math.max(0, toPct(current)));

  // Logical inset (inline-start) mirrors the scale in RTL, like the nutrient chart's reversed axis.
  return (
    <div aria-hidden className="relative h-6">
      <div className="absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 rounded-full bg-muted" />
      <div
        className={cn(
          "absolute top-1/2 h-2 -translate-y-1/2 border-y border-success-icon/50 bg-success-icon/25",
          // No upper limit: the band fades out toward the end of the track instead of closing.
          high === null
            ? "rounded-s-full border-s from-success-icon/35 to-success-icon/5 ltr:bg-gradient-to-r rtl:bg-gradient-to-l"
            : "rounded-full border-x"
        )}
        style={{ insetInlineStart: `${bandStart}%`, width: `${bandEnd - bandStart}%` }}
      />
      <div
        className="absolute top-0 h-6 w-1 -translate-x-1/2 rounded-full bg-foreground ring-2 ring-card rtl:translate-x-1/2"
        style={{ insetInlineStart: `${marker}%` }}
      />
    </div>
  );
}

function StatusChip({ status }: { status: string }) {
  const messages = useMessages();
  const style = STATUS_STYLES[status];
  const Icon = style?.icon ?? AlertTriangle;
  const fallback = status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium text-foreground",
        style?.className ?? "border-border bg-muted"
      )}
    >
      <Icon className="size-3.5" aria-hidden />
      {labelFor(messages.soil.results.metricStatuses, status, fallback)}
    </span>
  );
}

function MetricIndicator({ config, metric }: { config: MetricConfig; metric: ComparisonMetric | undefined }) {
  const t = useTranslations("soil.results");
  const tc = useTranslations("soil.results.conditions");
  const tUnits = useTranslations("units");
  const format = useFormatter();
  const { key, icon: Icon, bounds, maxFractionDigits } = config;

  const number = (value: number) => format.number(value, { maximumFractionDigits: maxFractionDigits });
  const withUnit = (value: number) => {
    if (key === "soilMoisture") return tUnits("percent", { value: number(value) });
    if (key === "light") return tUnits("lux", { value: number(value) });
    return number(value); // pH is unitless.
  };
  // Each value is isolated on its own (not forced LTR as a whole), so an Urdu
  // unit like "25,000 لکس" keeps its order and an RTL range reads low-to-high
  // from the right, matching the mirrored track.
  const num = (chunks: ReactNode) => <bdi>{chunks}</bdi>;

  const { current, plausible, range } = readMetric(metric, bounds);
  const status = typeof metric?.status === "string" && metric.status ? metric.status : null;

  // Position is a plain comparison of the reading with Module 2B's own range;
  // the size of the gap is Module 2B's `gap`, never recomputed here.
  let position: ReactNode = null;
  if (current !== null && plausible && range) {
    const gap = isFiniteNumber(metric?.gap) && metric.gap > 0 ? withUnit(metric.gap) : null;
    if (current < range.low) {
      position = gap ? tc.rich("belowRangeBy", { gap, num }) : tc("belowRange");
    } else if (range.high !== null && current > range.high) {
      position = gap ? tc.rich("aboveRangeBy", { gap, num }) : tc("aboveRange");
    } else {
      position = tc("withinRange");
    }
  }

  return (
    <section
      aria-labelledby={`soil-metric-${key}`}
      className="flex flex-col gap-2.5 rounded-lg border border-border bg-card p-3 text-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1.5">
        <h4 id={`soil-metric-${key}`} className="flex items-center gap-2 font-medium text-foreground">
          <Icon className="size-4 text-muted-foreground" aria-hidden />
          {t(`metrics.${key}`)}
        </h4>
        <div className="flex flex-wrap items-center gap-2">
          {current === null ? (
            <span className="text-xs text-muted-foreground">{t("notProvided")}</span>
          ) : (
            <bdi className="font-heading text-lg font-semibold text-foreground">{withUnit(current)}</bdi>
          )}
          {current !== null && status && <StatusChip status={status} />}
        </div>
      </div>

      {current !== null && !plausible && (
        <p className="text-xs text-muted-foreground">{tc("invalidReading")}</p>
      )}

      {current !== null && plausible && range && (
        <RangeTrack current={current} low={range.low} high={range.high} bounds={bounds} />
      )}

      {current !== null && (
        <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 text-xs text-muted-foreground">
          <span>
            {range
              ? range.high === null
                ? tc.rich("idealAtLeast", { low: withUnit(range.low), num })
                : tc.rich("idealBetween", { low: withUnit(range.low), high: withUnit(range.high), num })
              : tc("rangeUnavailable")}
          </span>
          {position && <span className="font-medium text-foreground">{position}</span>}
        </div>
      )}
    </section>
  );
}

interface SoilConditionsIndicatorProps {
  module2b: Module2BResult;
}

/**
 * Plots each Module 2B reading against the crop's ideal range exactly as the
 * soil module returned it. Every metric gets its own scale (pH, % and lux
 * are not comparable), and nothing here re-classifies a reading: the status
 * chip is Module 2B's own `status`, and a missing or malformed range is
 * shown as unavailable rather than filled in.
 */
export function SoilConditionsIndicator({ module2b }: SoilConditionsIndicatorProps) {
  const t = useTranslations("soil.results");
  const anyPlotted = METRICS.some((config) => {
    const { plausible, range } = readMetric(module2b[config.key], config.bounds);
    return plausible && range !== null;
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("soilConditions")}</CardTitle>
        <CardDescription>{t("conditions.description")}</CardDescription>
      </CardHeader>
      <CardContent className="@container flex flex-col gap-3">
        {/* Container query: the card is full-width on Soil Health but narrower inside the Quick Scan report. */}
        <div className="grid gap-3 @2xl:grid-cols-3">
          {METRICS.map((config) => (
            <MetricIndicator key={config.key} config={config} metric={module2b[config.key]} />
          ))}
        </div>
        {anyPlotted && (
          <div aria-hidden className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-5 rounded-full border border-success-icon/50 bg-success-icon/25" />
              {t("conditions.legendIdeal")}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-1 rounded-full bg-foreground" />
              {t("conditions.legendReading")}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
