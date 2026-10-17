import type { LucideIcon } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string;
  description: string;
  icon: LucideIcon;
  iconClassName?: string;
}

export function StatCard({ label, value, description, icon: Icon, iconClassName }: StatCardProps) {
  return (
    <Card className="h-40 justify-center transition-all duration-250 hover:-translate-y-0.5 hover:shadow-[var(--shadow-color-hover)]">
      <CardContent className="flex items-center gap-4">
        <div
          className={cn(
            "flex size-11 shrink-0 items-center justify-center rounded-full bg-info-bg text-info-icon",
            iconClassName
          )}
        >
          <Icon className="size-5" />
        </div>
        <div className="flex flex-col">
          <span className="font-heading text-2xl font-bold text-foreground">{value}</span>
          <span className="text-sm font-medium text-foreground">{label}</span>
          <span className="text-xs text-muted-foreground">{description}</span>
        </div>
      </CardContent>
    </Card>
  );
}
