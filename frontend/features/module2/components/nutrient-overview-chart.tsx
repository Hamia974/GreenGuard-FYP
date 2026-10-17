"use client";

import { BarChart3 } from "lucide-react";
import { useFormatter, useLocale, useMessages, useTranslations } from "next-intl";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { getDirection } from "@/lib/i18n/config";
import { labelFor } from "@/lib/i18n/labels";

import type { NutrientNote, RecommendationNotes } from "../types";

// Fixed display order so Soil Health and Quick Scan always list the same rows.
const NUTRIENT_ORDER: NutrientNote["nutrient"][] = [
  "Nitrogen",
  "Phosphorus",
  "Potassium",
  "Magnesium",
  "Boron",
  "Zinc",
];

const ROW_HEIGHT_PX = 36;

interface ChartRow {
  name: string;
  /** recommendation_notes.*.confidence_pct exactly as delivered -- never rescaled. */
  value: number;
  level: string;
}

interface TooltipPayload {
  payload: ChartRow;
}

function NutrientTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  const t = useTranslations("soil.results.nutrientOverview");
  const tUnits = useTranslations("units");
  const row = payload?.[0]?.payload;
  if (!active || !row) return null;

  return (
    <div dir="auto" className="rounded-lg border border-border bg-popover px-3 py-2 text-start text-xs text-popover-foreground shadow-md">
      <p className="font-semibold">{row.name}</p>
      <p>
        {t.rich("confidenceValue", {
          value: tUnits("percent", { value: row.value }),
          num: (chunks) => <bdi dir="ltr">{chunks}</bdi>,
        })}
      </p>
      <p className="text-muted-foreground">{row.level}</p>
    </div>
  );
}

interface NutrientOverviewChartProps {
  notes: RecommendationNotes;
}

/**
 * One bar per nutrient showing Module 2's own `confidence_pct` -- how sure
 * the model is about that nutrient's risk level. It is NOT the amount of
 * the nutrient in the soil, and the values are not parts of a whole, so
 * the axis is a plain 0-100 confidence scale. Nutrients missing from the
 * response are listed as "not reported", never drawn as zero.
 */
export function NutrientOverviewChart({ notes }: NutrientOverviewChartProps) {
  const t = useTranslations("soil.results.nutrientOverview");
  const tUnits = useTranslations("units");
  const messages = useMessages();
  const format = useFormatter();
  const isRtl = getDirection(useLocale() as Parameters<typeof getDirection>[0]) === "rtl";

  const byNutrient = new Map(
    [...notes.needsAttention, ...notes.lookingFine].map((note) => [note.nutrient, note])
  );
  const nutrientName = (nutrient: string) => labelFor(messages.soil.results.nutrients, nutrient);
  const levelName = (level: string) => labelFor(messages.soil.results.riskLevels, level);

  const rows: ChartRow[] = [];
  const missing: string[] = [];
  for (const nutrient of NUTRIENT_ORDER) {
    const note = byNutrient.get(nutrient);
    if (note && typeof note.confidencePct === "number") {
      rows.push({ name: nutrientName(nutrient), value: note.confidencePct, level: levelName(note.level) });
    } else {
      missing.push(nutrientName(nutrient));
    }
  }

  const percent = (value: number) => tUnits("percent", { value });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <BarChart3 className="size-4 text-muted-foreground" aria-hidden />
          {t("title")}
        </CardTitle>
        <CardDescription>{t("description")}</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {rows.length === 0 ? (
          <p className="rounded-lg border border-dashed border-border px-3 py-6 text-center text-sm text-muted-foreground">
            {t("empty")}
          </p>
        ) : (
          <>
            {/* Recharts' accessibility layer: Tab focuses the chart, arrow keys move between bars and show each tooltip. */}
            {/* SVG text inherits the page's RTL direction and mis-anchors; the RTL mirror is done via axis props instead. */}
            <div dir="ltr" className="w-full" style={{ height: rows.length * ROW_HEIGHT_PX + 32 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={rows}
                  layout="vertical"
                  // Room for the value label at the end of the longest bar.
                  margin={isRtl ? { top: 0, right: 0, bottom: 0, left: 40 } : { top: 0, right: 40, bottom: 0, left: 0 }}
                  barCategoryGap={8}
                  accessibilityLayer
                  title={t("title")}
                  desc={t("description")}
                >
                  <CartesianGrid horizontal={false} stroke="var(--border)" strokeDasharray="3 3" />
                  <XAxis
                    type="number"
                    // A confidence scale; only widened (never clipped) if a value ever exceeds 100.
                    domain={[0, (dataMax: number) => Math.max(100, dataMax)]}
                    ticks={[0, 25, 50, 75, 100]}
                    reversed={isRtl}
                    tickFormatter={percent}
                    tick={{ fill: "var(--muted-foreground)", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    orientation={isRtl ? "right" : "left"}
                    width={84}
                    tick={{ fill: "var(--foreground)", fontSize: 12 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip cursor={{ fill: "var(--muted)" }} content={<NutrientTooltip />} />
                  <Bar dataKey="value" fill="var(--chart-1)" radius={isRtl ? [4, 0, 0, 4] : [0, 4, 4, 0]} maxBarSize={20}>
                    <LabelList
                      dataKey="value"
                      // With the reversed RTL axis Recharts draws negative-width rects, so "right" lands past the bar end in both directions.
                      position="right"
                      formatter={(value) => percent(Number(value))}
                      fill="var(--foreground)"
                      fontSize={11}
                    />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Text equivalent of the chart for keyboard and screen-reader users. */}
            <table className="sr-only">
              <caption>{t("tableCaption")}</caption>
              <thead>
                <tr>
                  <th scope="col">{t("nutrientColumn")}</th>
                  <th scope="col">{t("confidenceColumn")}</th>
                  <th scope="col">{t("riskColumn")}</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.name}>
                    <th scope="row">{row.name}</th>
                    <td>{percent(row.value)}</td>
                    <td>{row.level}</td>
                  </tr>
                ))}
                {missing.map((name) => (
                  <tr key={name}>
                    <th scope="row">{name}</th>
                    <td>{t("notReported")}</td>
                    <td>{t("notReported")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}

        {missing.length > 0 && rows.length > 0 && (
          <p className="text-xs text-muted-foreground">
            {t("missing", { nutrients: format.list(missing, { type: "conjunction" }) })}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
