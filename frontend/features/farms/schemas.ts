import { z } from "zod";

import { validationKey as v } from "@/lib/i18n/validation";

// Error messages are validation.json keys, translated by <FieldError>.
// Coordinates are not typed by the farmer: they come from Find Location or
// Use Current Location (see FarmLocationPicker) and are checked separately.
export const farmSchema = z.object({
  farmName: z
    .string()
    .trim()
    .min(1, v("farmNameRequired"))
    .max(100, v("farmNameTooLong")),
  address: z.string().trim().min(1, v("addressRequired")),
});

export const coordinatesSchema = z.object({
  latitude: z
    .number({ error: v("latitudeRequired") })
    .min(-90, v("latitudeRange"))
    .max(90, v("latitudeRange")),
  longitude: z
    .number({ error: v("longitudeRequired") })
    .min(-180, v("longitudeRange"))
    .max(180, v("longitudeRange")),
});

export type FarmFormValues = z.infer<typeof farmSchema>;
