import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { LanguageSwitcher } from "@/components/layout/language-switcher";

interface LegalPageLayoutProps {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
}

export async function LegalPageLayout({ title, lastUpdated, children }: LegalPageLayoutProps) {
  const t = await getTranslations("legal");
  const tCommon = await getTranslations("common");

  return (
    <div className="min-h-screen bg-background">
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background:
            "radial-gradient(45% 45% at 15% 0%, color-mix(in oklch, var(--primary-100), transparent 60%), transparent), radial-gradient(45% 45% at 90% 100%, color-mix(in oklch, var(--primary-200), transparent 65%), transparent)",
        }}
      />

      <header className="mx-auto flex max-w-3xl flex-wrap items-center justify-between gap-3 px-4 py-6 sm:px-6">
        <Link href="/" className="font-heading text-lg font-bold text-primary">
          {tCommon("appName")}
        </Link>
        <div className="flex items-center gap-3">
          <LanguageSwitcher />
          <Link
            href="/register"
            className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-4 rtl:-scale-x-100" />
            {t("backToSignUp")}
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-4 pb-20 sm:px-6">
        <div className="rounded-2xl bg-card p-6 shadow-[var(--shadow-color-md)] sm:p-10">
          <div className="mb-8 border-b border-border pb-6">
            <h1 className="font-heading text-3xl font-bold text-foreground">{title}</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              {t("lastUpdated", { date: lastUpdated })}
            </p>
          </div>

          <div className="rounded-xl border border-warning-border bg-warning-bg px-4 py-3 text-sm text-warning-text">
            {t("placeholderNotice")}
          </div>

          <div className="mt-8 flex flex-col gap-6 text-sm leading-relaxed text-foreground [&_h2]:font-heading [&_h2]:text-lg [&_h2]:font-semibold [&_h2]:text-foreground [&_p]:text-muted-foreground [&_li]:text-muted-foreground">
            {children}
          </div>
        </div>
      </main>
    </div>
  );
}
