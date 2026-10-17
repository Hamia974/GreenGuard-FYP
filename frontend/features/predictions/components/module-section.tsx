import type { LucideIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

interface ModuleSectionProps {
  moduleNumber: 1 | 2 | 3;
  title: string;
  /** One line naming where this result comes from. */
  source: string;
  icon: LucideIcon;
  children: ReactNode;
}

/**
 * One independent AI module's result inside the integrated analysis report.
 * The module number and source line keep every result traceable to the
 * module that produced it -- the report never merges them.
 */
export function ModuleSection({ moduleNumber, title, source, icon: Icon, children }: ModuleSectionProps) {
  const t = useTranslations("report");
  const headingId = `module-${moduleNumber}-heading`;

  return (
    <section aria-labelledby={headingId} className="flex flex-col gap-4">
      <div className="flex items-start gap-3">
        <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-primary/10 text-primary">
          <Icon className="size-5" />
        </div>
        <div className="flex flex-col gap-0.5">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
            {t("moduleLabel", { number: moduleNumber })}
          </p>
          <h2 id={headingId} className="font-heading text-xl font-semibold text-foreground">
            {title}
          </h2>
          <p className="text-sm text-muted-foreground">{source}</p>
        </div>
      </div>
      {children}
    </section>
  );
}
