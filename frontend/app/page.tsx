import { getTranslations } from "next-intl/server";

import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { LinkButton } from "@/components/ui/link-button";

export default async function Home() {
  const t = await getTranslations("home");
  const tCommon = await getTranslations("common");

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
      <LanguageSwitcher className="absolute end-4 top-4 sm:end-6 sm:top-6" />
      <span className="rounded-full border border-border bg-card px-4 py-1.5 text-sm font-medium text-muted-foreground shadow-[var(--shadow-color-sm)]">
        {t("badge")}
      </span>
      <h1 className="font-heading text-4xl font-bold text-foreground sm:text-5xl">
        {tCommon("appName")}
      </h1>
      <p className="max-w-md text-base text-muted-foreground">{t("description")}</p>
      <div className="mt-2 flex items-center gap-3">
        <LinkButton href="/login" className="h-11 rounded-2xl px-6">
          {t("signIn")}
        </LinkButton>
        <LinkButton
          href="/register"
          variant="outline"
          className="h-11 rounded-2xl px-6"
        >
          {t("createAccount")}
        </LinkButton>
      </div>
    </main>
  );
}
