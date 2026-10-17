import { Lock } from "lucide-react";
import { useTranslations } from "next-intl";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Module3PreviewCardProps {
  title: string;
  description: string;
}

/**
 * Placeholder for the widgets described in UI_SPECIFICATION.md section 14
 * that the real, integrated Weather Module (Module 3) still does not
 * produce -- UV index, wind direction/gusts, air pressure, visibility, and
 * an interactive multi-farm map. Current conditions, risk assessment, and
 * the next-day forecast ARE real and live (see CurrentConditionsCard,
 * RiskAssessmentCard, ForecastCard) -- only these two remain unsupported by
 * the delivered contract. Stay clearly unpopulated -- never filled with
 * fabricated data. See docs/MODULE3_INTEGRATION_STATUS.md.
 */
export function Module3PreviewCard({ title, description }: Module3PreviewCardProps) {
  const t = useTranslations("weather.preview");

  return (
    <Card className="border-dashed bg-muted/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base text-muted-foreground">
          <Lock className="size-4" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground">{description}</p>
        <p className="mt-2 text-xs font-medium text-muted-foreground/80">
          {t("notInContract")}
        </p>
      </CardContent>
    </Card>
  );
}
