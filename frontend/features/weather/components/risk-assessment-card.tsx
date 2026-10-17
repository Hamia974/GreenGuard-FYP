import { AlertTriangle, Droplet, Flame } from "lucide-react";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { RiskAssessment, RiskLevel } from "@/features/weather/types";

const RISK_BADGE_VARIANT: Record<RiskLevel, "success" | "warning" | "error"> = {
  Low: "success",
  Moderate: "warning",
  High: "error",
};

function RiskRow({
  icon: Icon,
  label,
  level,
  reason,
}: {
  icon: React.ElementType;
  label: string;
  level: RiskLevel;
  reason: string;
}) {
  const t = useTranslations("weather");

  return (
    <div className="flex flex-col gap-1.5 rounded-xl border border-border bg-muted/40 p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">{label}</span>
        </div>
        <Badge variant={RISK_BADGE_VARIANT[level]}>{t(`riskLevels.${level}`)}</Badge>
      </div>
      {/* Module 3's own explanation sentence -- shown exactly as delivered. */}
      <p dir="auto" className="text-xs text-muted-foreground">
        {reason}
      </p>
    </div>
  );
}

/** Rule-engine risk levels from the real Weather Module (Module 3), per
 * REST_API_SPEC.md section 5A -- fungal disease, heat stress, and drought
 * risk, each with the module's own plain-English reason sentence. No
 * overall 0-100 "Weather Risk Score" is shown (UI_SPECIFICATION.md section
 * 14.5) since nothing in the delivered contract produces one; adding a
 * synthetic score here would mean inventing a number, not reporting one.
 * The `*_reason` strings are display-only -- never parsed for logic. */
export function RiskAssessmentCard({
  title,
  assessment,
}: {
  title: string;
  assessment: RiskAssessment;
}) {
  const t = useTranslations("weather.risks");

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-2">
          <RiskRow
            icon={Flame}
            label={t("fungalDisease")}
            level={assessment.fungalDiseaseRisk}
            reason={assessment.fungalDiseaseReason}
          />
          <RiskRow
            icon={AlertTriangle}
            label={t("heatStress")}
            level={assessment.heatStressRisk}
            reason={assessment.heatStressReason}
          />
          <RiskRow
            icon={Droplet}
            label={t("drought")}
            level={assessment.droughtRisk}
            reason={assessment.droughtReason}
          />
        </div>
      </CardContent>
    </Card>
  );
}
