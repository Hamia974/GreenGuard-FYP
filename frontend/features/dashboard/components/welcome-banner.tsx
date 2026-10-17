"use client";

import { Sprout } from "lucide-react";
import { useFormatter, useTranslations } from "next-intl";

function getGreetingKey(hour: number): "morning" | "afternoon" | "evening" {
  if (hour < 12) return "morning";
  if (hour < 17) return "afternoon";
  return "evening";
}

interface WelcomeBannerProps {
  firstName: string;
}

export function WelcomeBanner({ firstName }: WelcomeBannerProps) {
  const t = useTranslations("dashboard.welcome");
  const format = useFormatter();
  const now = new Date();
  const dateLabel = format.dateTime(now, "weekdayLong");

  return (
    <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-primary-700 via-primary-800 to-primary-900 px-6 py-8 text-primary-foreground shadow-[var(--shadow-color-md)] sm:px-8">
      <Sprout className="pointer-events-none absolute -end-4 -bottom-6 size-32 text-white/10 sm:size-40" />
      <div className="relative flex flex-col gap-1">
        <p className="text-sm font-medium text-white/80">{dateLabel}</p>
        <h1 className="font-heading text-2xl font-bold sm:text-3xl">
          {t(getGreetingKey(now.getHours()), { name: firstName })}
        </h1>
        <p className="max-w-md text-sm text-white/80">{t("subtitle")}</p>
      </div>
    </div>
  );
}
