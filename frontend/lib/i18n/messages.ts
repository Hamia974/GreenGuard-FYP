import type { Messages } from "next-intl";

import { defaultLocale, type Locale } from "./config";

type MessageTree = { [key: string]: string | MessageTree };

const loaders: Record<Locale, () => Promise<{ default: Messages }>> = {
  en: () => import("@/messages/en"),
  ur: () => import("@/messages/ur"),
};

/** Recursively fills any key missing from `messages` with the value from `fallback`. */
function withFallback(messages: MessageTree, fallback: MessageTree): MessageTree {
  const merged: MessageTree = { ...fallback };
  for (const [key, value] of Object.entries(messages)) {
    const fallbackValue = fallback[key];
    merged[key] =
      typeof value === "object" && typeof fallbackValue === "object"
        ? withFallback(value, fallbackValue)
        : value;
  }
  return merged;
}

/**
 * Loads a locale's messages with English underneath as a safety net: a key
 * that is somehow missing from a translation renders in English instead of
 * crashing the page. `npm run check:i18n` and the typed `Messages` shape are
 * what keep translations complete -- this is only the last line of defence.
 */
export async function loadMessages(locale: Locale): Promise<Messages> {
  const messages = (await loaders[locale]()).default;
  if (locale === defaultLocale) return messages;

  const fallback = (await loaders[defaultLocale]()).default;
  return withFallback(
    messages as unknown as MessageTree,
    fallback as unknown as MessageTree
  ) as unknown as Messages;
}
