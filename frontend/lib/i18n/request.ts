import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";

import { defaultLocale, isLocale, LOCALE_COOKIE } from "./config";
import { getMessageFallback, handleIntlError } from "./error-handling";
import { formats } from "./formats";
import { loadMessages } from "./messages";

/**
 * Resolves the active locale for every server render from the
 * NEXT_LOCALE cookie (set by the language switcher). URLs stay locale-free
 * (/dashboard, not /ur/dashboard), so no route or link in the app changes.
 */
export default getRequestConfig(async () => {
  const cookieLocale = (await cookies()).get(LOCALE_COOKIE)?.value;
  const locale = isLocale(cookieLocale) ? cookieLocale : defaultLocale;

  return {
    locale,
    messages: await loadMessages(locale),
    formats,
    onError: handleIntlError,
    getMessageFallback,
  };
});
