"use client";

import { DirectionProvider } from "@base-ui/react/direction-provider";
import { type Messages, NextIntlClientProvider } from "next-intl";

import { getDirection, type Locale } from "@/lib/i18n/config";
import { getMessageFallback, handleIntlError } from "@/lib/i18n/error-handling";
import { formats } from "@/lib/i18n/formats";

interface I18nProviderProps {
  locale: Locale;
  messages: Messages;
  children: React.ReactNode;
}

/**
 * Client-side half of the i18n setup. The root layout resolves the locale
 * and messages on the server (lib/i18n/request.ts) and hands them here, so
 * every Client Component can call useTranslations()/useFormatter().
 *
 * No `timeZone` is passed on purpose: dates keep rendering in the viewer's
 * own browser time zone, exactly as they did before localization.
 */
export function I18nProvider({ locale, messages, children }: I18nProviderProps) {
  return (
    <NextIntlClientProvider
      locale={locale}
      messages={messages}
      formats={formats}
      onError={handleIntlError}
      getMessageFallback={getMessageFallback}
    >
      <DirectionProvider direction={getDirection(locale)}>{children}</DirectionProvider>
    </NextIntlClientProvider>
  );
}
