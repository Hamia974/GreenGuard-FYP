import { IntlErrorCode, type IntlError } from "next-intl";

const isDevelopment = process.env.NODE_ENV === "development";

/**
 * Shared by the server request config and the client provider. Missing
 * translations are loud in development (console error naming the key) and
 * silent in production, where `getMessageFallback` renders something
 * readable instead of crashing the page.
 */
export function handleIntlError(error: IntlError) {
  if (error.code === IntlErrorCode.ENVIRONMENT_FALLBACK) return;
  if (error.code === IntlErrorCode.MISSING_MESSAGE) {
    if (isDevelopment) console.error(`[i18n] ${error.message}`);
    return;
  }
  console.error(error);
}

export function getMessageFallback({
  namespace,
  key,
}: {
  namespace?: string;
  key: string;
}): string {
  const path = namespace ? `${namespace}.${key}` : key;
  // Dev: make the gap obvious on screen. Prod: show the last key segment,
  // which is at least a readable hint rather than a crash or blank space.
  return isDevelopment ? `⟦${path}⟧` : (path.split(".").pop() ?? path);
}
