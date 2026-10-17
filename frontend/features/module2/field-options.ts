// REST_API_SPEC.md section 8A requires the frontend and backend to both read
// Module 2's categorical values from docs/module2_field_options.json rather
// than hardcoding a competing list. The backend (module2/field_options.py)
// reads that file directly. Turbopack's production build does not resolve
// imports outside the frontend/ project root even with
// experimental.externalDir, so this is a byte-identical mirror kept next to
// this file -- see field_options.data.json's own note. Any change to
// docs/module2_field_options.json must be copied here too.
import fieldOptions from "./field_options.data.json";

export const CROP_VALUES = fieldOptions.categorical_fields.crop as string[];
export const GROWTH_STAGE_VALUES = fieldOptions.categorical_fields.growth_stage as string[];
export const SOIL_TYPE_VALUES = fieldOptions.categorical_fields.soil_type as string[];
export const FERTILIZER_TYPE_VALUES = fieldOptions.categorical_fields
  .last_fertilizer_type as string[];
export const DAYS_SINCE_FERTILIZER_VALUES = fieldOptions.categorical_fields
  .days_since_fertilizer as string[];
export const IRRIGATION_SOURCE_VALUES = fieldOptions.categorical_fields
  .irrigation_source as string[];
export const IRRIGATION_ADEQUACY_VALUES = fieldOptions.categorical_fields
  .irrigation_adequacy as string[];
export const SYMPTOM_KEYS = fieldOptions.symptom_fields.keys as string[];

// As of module2a-v5 (2026-09-10), all 15 crops are trained and supported --
// see module2_field_options.json's crop_model_support.note. There is no
// longer a "pending retrain" crop subset requiring a separate UI branch.
export const SUPPORTED_CROPS = new Set(
  fieldOptions.crop_model_support.trained_and_supported as string[]
);

export const NO_FERTILIZER_VALUE = "No_Fertilizer";
export const NOT_APPLICABLE_VALUE = "not_applicable";
export const NONE_VISIBLE_KEY = "none_visible";

// Farmer-facing labels for every value above (per
// docs/Module2_Frontend_Form_Spec.md) live in messages/<locale>/soil.json
// under "options", and crop names in messages/<locale>/crops.json. They are
// UI copy only -- the raw values are what the API receives.

export function isCropSupported(crop: string): boolean {
  return SUPPORTED_CROPS.has(crop);
}

/** Real photo for a crop option, per requirement_4 (low-literacy farmers
 * identify crops by sight, not just the text label). Files live under
 * frontend/public/images/crops/<value>.jpg -- see public/images/CREDITS.json
 * for source/license of each photo. */
export function cropImageSrc(value: string): string {
  return `/images/crops/${value}.jpg`;
}

/** Real photo for a soil-texture option -- frontend/public/images/soil-types/<value>.jpg. */
export function soilTypeImageSrc(value: string): string {
  return `/images/soil-types/${value}.jpg`;
}

/** Real photo for an irrigation-source option -- frontend/public/images/irrigation/<value>.jpg. */
export function irrigationSourceImageSrc(value: string): string {
  return `/images/irrigation/${value}.jpg`;
}

/** Example photo of what a symptom looks like (for comparison only, not a
 * diagnosis) -- frontend/public/images/symptoms/<key>.jpg. */
export function symptomImageSrc(key: string): string {
  return `/images/symptoms/${key}.jpg`;
}

export function defaultSymptoms(): Record<string, boolean> {
  return Object.fromEntries(SYMPTOM_KEYS.map((key) => [key, false]));
}
