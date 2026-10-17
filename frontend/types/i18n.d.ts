import type { Locale } from "@/lib/i18n/config";
import type { formats } from "@/lib/i18n/formats";
import type messages from "@/messages/en";

/**
 * Makes every translation key type-checked: `t("dashbord.title")` (typo) or
 * a key that only exists in one component's imagination fails `tsc`.
 * English (messages/en) is the reference shape; messages/ur/index.ts is
 * typed against it, so a key missing from Urdu also fails `tsc`.
 */
declare module "next-intl" {
  interface AppConfig {
    Locale: Locale;
    Messages: typeof messages;
    Formats: typeof formats;
  }
}
