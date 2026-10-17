import { CloudRain, Droplets, Thermometer, Wind } from "lucide-react";
import { useTranslations } from "next-intl";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { CurrentWeather } from "@/features/weather/types";

interface ConditionTileProps {
  icon: React.ElementType;
  label: string;
  value: string;
  accent: string;
}

function ConditionTile({ icon: Icon, label, value, accent }: ConditionTileProps) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-border bg-muted/40 p-4">
      <Icon className={`size-6 ${accent}`} />
      <div>
        <p className="text-xl font-semibold text-foreground">{value}</p>
        <p className="text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

/** Live current conditions from the real Weather Module (Module 3, Open-Meteo
 * + rule engine), per REST_API_SPEC.md section 5A. Only the four fields the
 * module actually returns are shown -- no "feels like", UV index, pressure,
 * or visibility, since none of those exist in the delivered contract and
 * none are fabricated here. */
export function CurrentConditionsCard({ weather }: { weather: CurrentWeather }) {
  const t = useTranslations("weather");
  const tUnits = useTranslations("units");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t("currentConditions")}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <ConditionTile
            icon={Thermometer}
            label={t("metrics.temperature")}
            value={tUnits("celsius", { value: weather.temperature })}
            accent="text-warning-icon"
          />
          <ConditionTile
            icon={Droplets}
            label={t("metrics.humidity")}
            value={tUnits("percent", { value: weather.humidity })}
            accent="text-info-icon"
          />
          <ConditionTile
            icon={Wind}
            label={t("metrics.windSpeed")}
            value={tUnits("metersPerSecond", { value: weather.windSpeed })}
            accent="text-primary"
          />
          <ConditionTile
            icon={CloudRain}
            label={t("metrics.rainfallLast7Days")}
            value={tUnits("millimeters", { value: weather.rainfallLast7DaysMm })}
            accent="text-info-icon"
          />
        </div>
      </CardContent>
    </Card>
  );
}
