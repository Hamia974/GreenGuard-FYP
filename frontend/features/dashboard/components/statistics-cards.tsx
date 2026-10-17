import { Leaf, ScanLine, ShieldAlert, Target } from "lucide-react";
import { useTranslations } from "next-intl";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

import type { PredictionStatistics } from "../types";

interface StatisticsCardsProps {
  totalPredictions: number;
  statistics: PredictionStatistics;
}

interface StatCardConfig {
  /** Key under dashboard.statistics in messages/<locale>/dashboard.json. */
  key: "totalPredictions" | "healthyPlants" | "diseasedPlants" | "aiAccuracy";
  value: string;
  icon: typeof ScanLine;
  iconClassName: string;
}

export function StatisticsCards({ totalPredictions, statistics }: StatisticsCardsProps) {
  const t = useTranslations("dashboard.statistics");
  const tUnits = useTranslations("units");

  const cards: StatCardConfig[] = [
    {
      key: "totalPredictions",
      value: totalPredictions.toString(),
      icon: ScanLine,
      iconClassName: "bg-info-bg text-info-icon",
    },
    {
      key: "healthyPlants",
      value: statistics.healthyCount.toString(),
      icon: Leaf,
      iconClassName: "bg-success-bg text-success-icon",
    },
    {
      key: "diseasedPlants",
      value: statistics.diseasedCount.toString(),
      icon: ShieldAlert,
      iconClassName: "bg-error-bg text-error-icon",
    },
    {
      key: "aiAccuracy",
      value: statistics.accuracy !== null ? tUnits("percent", { value: statistics.accuracy }) : "—",
      icon: Target,
      iconClassName: "bg-warning-bg text-warning-icon",
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card
          key={card.key}
          className="h-40 justify-center transition-all duration-250 hover:-translate-y-0.5 hover:shadow-[var(--shadow-color-hover)]"
        >
          <CardContent className="flex items-center gap-4">
            <div
              className={cn(
                "flex size-11 shrink-0 items-center justify-center rounded-full",
                card.iconClassName
              )}
            >
              <card.icon className="size-5" />
            </div>
            <div className="flex flex-col">
              <span className="font-heading text-2xl font-bold text-foreground">
                {card.value}
              </span>
              <span className="text-sm font-medium text-foreground">{t(`${card.key}.label`)}</span>
              <span className="text-xs text-muted-foreground">{t(`${card.key}.description`)}</span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
