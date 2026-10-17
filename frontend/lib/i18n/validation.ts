import type { Messages } from "next-intl";

/** A key inside messages/<locale>/validation.json. */
export type ValidationKey = keyof Messages["validation"];

/**
 * Zod schemas store translation KEYS as their error messages (not English
 * text) so they stay plain module-level constants. `<FieldError>` turns the
 * key into the active language at render time. This identity helper only
 * exists so a typo in a schema key fails `tsc`.
 */
export function validationKey(key: ValidationKey): ValidationKey {
  return key;
}
