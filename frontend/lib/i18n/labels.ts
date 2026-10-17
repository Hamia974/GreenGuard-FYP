/**
 * Looks up the human-readable label for a raw API / enum value (crop ids,
 * disease slugs, questionnaire option values, ...) inside a message group
 * obtained from `useMessages()`.
 *
 * The raw value itself is NEVER changed or sent anywhere -- this is display
 * only. An unknown value (e.g. a class the AI team adds later) falls back
 * to `fallback`, or to the raw value, so new backend values never vanish.
 */
export function labelFor(
  labels: Readonly<Record<string, string>>,
  value: string,
  fallback?: string
): string {
  return Object.prototype.hasOwnProperty.call(labels, value) ? labels[value] : (fallback ?? value);
}
