"use client";

import { ArrowRight, CloudSun, Leaf, MapPin, ScanLine } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { cn } from "@/lib/utils";

interface TestCardConfig {
  href: string;
  /** Key under dashboard.mainTests.tests in messages/<locale>/dashboard.json. */
  key: "weather" | "soil" | "disease";
  icon: typeof CloudSun;
  iconBg: string;
  iconColor: string;
}

const TESTS: TestCardConfig[] = [
  {
    href: "/weather-test",
    key: "weather",
    icon: CloudSun,
    iconBg: "bg-info-bg",
    iconColor: "text-info-icon",
  },
  {
    href: "/module2",
    key: "soil",
    icon: Leaf,
    iconBg: "bg-primary/10",
    iconColor: "text-primary",
  },
  {
    href: "/quick-scan",
    key: "disease",
    icon: ScanLine,
    iconBg: "bg-warning-bg",
    iconColor: "text-warning-icon",
  },
];

interface MainTestsProps {
  /** A farm is actively selected — tests can run immediately. */
  hasActiveFarm: boolean;
  /** The farmer owns at least one farm, even if none is selected yet. */
  hasAnyFarm: boolean;
  activeFarmName?: string;
}

/**
 * The three primary farmer actions (Weather / Soil / Disease Test), shown
 * immediately after login per requirement_3 — large, obvious action cards
 * rather than sidebar links. Each links straight to its dedicated test flow;
 * when no farm is selected yet, it routes to Farm setup first instead
 * (every test requires a farm, same as the existing Quick Scan/Soil pages).
 */
export function MainTests({ hasActiveFarm, hasAnyFarm, activeFarmName }: MainTestsProps) {
  const t = useTranslations("dashboard.mainTests");
  const tFarms = useTranslations("farms");

  const statusLabel = hasActiveFarm
    ? activeFarmName
    : hasAnyFarm
      ? t("selectFarmToStart")
      : t("addFarmToStart");

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-1 text-center sm:text-start">
        <h2 className="font-heading text-xl font-bold text-foreground sm:text-2xl">
          {t("title")}
        </h2>
        <p className="text-sm text-muted-foreground">{t("description")}</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {TESTS.map((test) => (
          <Link
            key={test.href}
            href={hasActiveFarm ? test.href : "/farms"}
            className="group flex flex-col gap-4 rounded-2xl border border-border bg-card p-6 text-start shadow-[var(--shadow-color-sm)] transition-all hover:-translate-y-0.5 hover:shadow-[var(--shadow-color-hover)] focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-ring/50"
          >
            <div
              className={cn(
                "flex size-14 items-center justify-center rounded-2xl",
                test.iconBg,
                test.iconColor
              )}
            >
              <test.icon className="size-7" />
            </div>

            <div className="flex flex-col gap-1">
              <h3 className="font-heading text-lg font-bold text-foreground">
                {t(`tests.${test.key}.title`)}
              </h3>
              <p className="text-sm text-muted-foreground">{t(`tests.${test.key}.description`)}</p>
            </div>

            <div className="mt-auto flex items-center justify-between gap-2 pt-2">
              <span className="inline-flex min-w-0 items-center gap-1 truncate text-xs font-medium text-muted-foreground">
                {hasActiveFarm && <MapPin className="size-3 shrink-0" />}
                <span className="truncate">{statusLabel}</span>
              </span>
              <span className="inline-flex shrink-0 items-center gap-1 text-sm font-semibold text-primary">
                {hasActiveFarm ? t("start") : tFarms("addFarm")}
                <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5 rtl:-scale-x-100 rtl:group-hover:-translate-x-0.5" />
              </span>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
