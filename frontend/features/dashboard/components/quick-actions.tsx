import { CloudSun, History, MapPinPlus, ScanLine, UserRound } from "lucide-react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { Card, CardContent } from "@/components/ui/card";

interface QuickAction {
  labelKey: "addFarm" | "predictionHistory" | "weatherDashboard" | "profile";
  icon: typeof ScanLine;
  href?: string;
}

const actions: QuickAction[] = [
  { labelKey: "addFarm", icon: MapPinPlus, href: "/farms/new" },
  { labelKey: "predictionHistory", icon: History, href: "/history" },
  { labelKey: "weatherDashboard", icon: CloudSun, href: "/weather" },
  { labelKey: "profile", icon: UserRound, href: "/profile" },
];

export function QuickActions() {
  const t = useTranslations("dashboard.quickActions");

  return (
    <Card>
      <CardContent className="flex flex-wrap gap-3">
        {actions.map((action) =>
          action.href ? (
            <LinkButton
              href={action.href}
              key={action.labelKey}
              variant="secondary"
              size="sm"
              className="h-9 rounded-xl px-3.5"
            >
              <action.icon className="size-3.5" />
              {t(action.labelKey)}
            </LinkButton>
          ) : (
            <Button
              key={action.labelKey}
              variant="outline"
              size="sm"
              disabled
              className="h-9 rounded-xl px-3.5"
              title={t("comingSoon")}
            >
              <action.icon className="size-3.5" />
              {t(action.labelKey)}
            </Button>
          )
        )}
      </CardContent>
    </Card>
  );
}
