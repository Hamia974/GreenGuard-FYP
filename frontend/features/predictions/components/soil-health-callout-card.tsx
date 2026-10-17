import { Sprout } from "lucide-react";
import { useTranslations } from "next-intl";

import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent } from "@/components/ui/card";

/**
 * Shown in the report's Soil & Nutrient section when the farm has no Soil
 * Test on record. Quick Scan never runs Module 2 itself (it needs the
 * farmer's questionnaire), so this links to the standalone check instead of
 * showing any placeholder result.
 */
export function SoilHealthCalloutCard() {
  const t = useTranslations("report.soilCallout");

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <p className="flex items-center gap-2 font-medium text-foreground">
          <Sprout className="size-4 text-primary" />
          {t("title")}
        </p>
        <p className="text-sm text-muted-foreground">{t("description")}</p>
        <LinkButton href="/module2" size="sm" className="w-fit">
          {t("action")}
        </LinkButton>
      </CardContent>
    </Card>
  );
}
