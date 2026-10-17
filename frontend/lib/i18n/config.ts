/**
 * Single source of truth for which languages GreenGuard supports.
 *
 * Adding a language = add it to `locales` + `LOCALE_SETTINGS`, then create
 * messages/<locale>/ (see docs/I18N_GUIDE.md). Nothing else hardcodes a
 * locale list.
 */
export const locales = ["en", "ur"] as const;

export type Locale = (typeof locales)[number];

export const defaultLocale: Locale = "en";

/** Cookie holding the visitor's chosen language. Read on the server for every request. */
export const LOCALE_COOKIE = "NEXT_LOCALE";

/** One year -- the choice should survive browser restarts. */
export const LOCALE_COOKIE_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

export type TextDirection = "ltr" | "rtl";

interface LocaleSettings {
  /** Shown in the language switcher, always in the language's own script. */
  nativeName: string;
  dir: TextDirection;
}

export const LOCALE_SETTINGS: Record<Locale, LocaleSettings> = {
  en: { nativeName: "English", dir: "ltr" },
  ur: { nativeName: "اردو", dir: "rtl" },
};

export function isLocale(value: unknown): value is Locale {
  return typeof value === "string" && (locales as readonly string[]).includes(value);
}

export function getDirection(locale: Locale): TextDirection {
  return LOCALE_SETTINGS[locale].dir;
}
