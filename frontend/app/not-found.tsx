import { CompassIcon } from "lucide-react";
import { getTranslations } from "next-intl/server";

import { LinkButton } from "@/components/ui/link-button";

/** Global 404 -- catches any unmatched route across both the (auth) and (app) segments. */
export default async function NotFound() {
  const t = await getTranslations("errors.notFound");
  const tNav = await getTranslations("navigation");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background px-6 text-center">
      <CompassIcon className="size-8 text-muted-foreground" />
      <h1 className="font-heading text-2xl font-bold text-foreground">{t("title")}</h1>
      <p className="max-w-sm text-sm text-muted-foreground">{t("description")}</p>
      <LinkButton href="/dashboard" className="mt-2 h-11 rounded-2xl px-5">
        {tNav("backToDashboard")}
      </LinkButton>
    </main>
  );
}
