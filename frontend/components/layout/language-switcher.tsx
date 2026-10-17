"use client";

import { Globe } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useTransition } from "react";

import { setUserLocale } from "@/lib/i18n/actions";
import { getDirection, LOCALE_SETTINGS, type Locale, locales } from "@/lib/i18n/config";
import { cn } from "@/lib/utils";

/**
 * Compact English | اردو toggle. Writes the NEXT_LOCALE cookie through a
 * Server Action, then refreshes the current route so the server re-renders
 * with the new messages and <html lang dir>. Client state on the page
 * (half-filled forms, selected images) survives the switch.
 */
export function LanguageSwitcher({ className }: { className?: string }) {
  const t = useTranslations("language");
  const activeLocale = useLocale();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const changeLocale = (locale: Locale) => {
    if (locale === activeLocale) return;
    startTransition(async () => {
      await setUserLocale(locale);
      // Applied immediately so layout direction flips without waiting for
      // the refreshed payload; the server render then confirms the same values.
      document.documentElement.lang = locale;
      document.documentElement.dir = getDirection(locale);
      router.refresh();
    });
  };

  return (
    <div
      role="group"
      aria-label={t("switcherLabel")}
      className={cn(
        "inline-flex h-8 items-center gap-0.5 rounded-lg border border-border bg-background p-0.5",
        isPending && "opacity-60",
        className
      )}
    >
      <Globe className="mx-1 size-3.5 shrink-0 text-muted-foreground" aria-hidden="true" />
      {locales.map((locale) => {
        const isActive = locale === activeLocale;
        return (
          <button
            key={locale}
            type="button"
            lang={locale}
            aria-pressed={isActive}
            disabled={isPending}
            onClick={() => changeLocale(locale)}
            className={cn(
              "h-full rounded-md px-2 text-xs font-medium transition-colors outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
              isActive
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            )}
          >
            {LOCALE_SETTINGS[locale].nativeName}
          </button>
        );
      })}
    </div>
  );
}
