import { z } from "zod";

import { validationKey as v } from "@/lib/i18n/validation";

import {
  CROP_VALUES,
  DAYS_SINCE_FERTILIZER_VALUES,
  FERTILIZER_TYPE_VALUES,
  GROWTH_STAGE_VALUES,
  IRRIGATION_ADEQUACY_VALUES,
  IRRIGATION_SOURCE_VALUES,
  NONE_VISIBLE_KEY,
  NOT_APPLICABLE_VALUE,
  NO_FERTILIZER_VALUE,
  SOIL_TYPE_VALUES,
  SYMPTOM_KEYS,
} from "./field-options";

// Error messages are validation.json keys, translated by <FieldError>.
const symptomsShape = Object.fromEntries(SYMPTOM_KEYS.map((key) => [key, z.boolean()]));

export const module2Schema = z
  .object({
    crop: z.enum(CROP_VALUES as [string, ...string[]], { error: v("cropRequired") }),
    growthStage: z.enum(GROWTH_STAGE_VALUES as [string, ...string[]], {
      error: v("growthStageRequired"),
    }),
    soilType: z.enum(SOIL_TYPE_VALUES as [string, ...string[]], {
      error: v("soilTypeRequired"),
    }),
    lastFertilizerType: z.enum(FERTILIZER_TYPE_VALUES as [string, ...string[]], {
      error: v("fertilizerTypeRequired"),
    }),
    daysSinceFertilizer: z.enum(DAYS_SINCE_FERTILIZER_VALUES as [string, ...string[]], {
      error: v("daysSinceFertilizerRequired"),
    }),
    irrigationSource: z.enum(IRRIGATION_SOURCE_VALUES as [string, ...string[]], {
      error: v("irrigationSourceRequired"),
    }),
    irrigationAdequacy: z.enum(IRRIGATION_ADEQUACY_VALUES as [string, ...string[]], {
      error: v("irrigationAdequacyRequired"),
    }),
    symptoms: z.object(symptomsShape),
    // Required as of module2_field_options.json v7.0 -- a soil meter ships
    // with the deployment, so these three readings are always available.
    // The Stress Module's /predict rejects a missing/null value with 422.
    phValue: z
      .number({ error: v("phRequired") })
      .min(0, v("phRange"))
      .max(14, v("phRange")),
    soilMoisturePct: z
      .number({ error: v("soilMoistureRequired") })
      .min(0, v("soilMoistureRange"))
      .max(100, v("soilMoistureRange")),
    lightIntensityLux: z
      .number({ error: v("lightIntensityRequired") })
      .min(0, v("lightIntensityMin")),
  })
  .check((ctx) => {
    const values = ctx.value;

    if (
      values.lastFertilizerType === NO_FERTILIZER_VALUE &&
      values.daysSinceFertilizer !== NOT_APPLICABLE_VALUE
    ) {
      ctx.issues.push({
        code: "custom",
        input: values.daysSinceFertilizer,
        path: ["daysSinceFertilizer"],
        message: v("daysSinceFertilizerNotApplicable"),
      });
    }

    if (
      values.lastFertilizerType !== NO_FERTILIZER_VALUE &&
      values.daysSinceFertilizer === NOT_APPLICABLE_VALUE
    ) {
      ctx.issues.push({
        code: "custom",
        input: values.daysSinceFertilizer,
        path: ["daysSinceFertilizer"],
        message: v("daysSinceFertilizerMissing"),
      });
    }

    const noneVisible = values.symptoms[NONE_VISIBLE_KEY];
    const otherSelected = Object.entries(values.symptoms).some(
      ([key, val]) => key !== NONE_VISIBLE_KEY && val
    );
    if (noneVisible && otherSelected) {
      ctx.issues.push({
        code: "custom",
        input: values.symptoms,
        path: ["symptoms"],
        message: v("symptomsNoneConflict"),
      });
    }
  });

export type Module2FormValues = z.infer<typeof module2Schema>;

export function defaultModule2FormValues(
  symptoms: Record<string, boolean>
): Partial<Module2FormValues> {
  return { symptoms };
}
