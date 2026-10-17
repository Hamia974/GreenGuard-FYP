import { z } from "zod";

import { validationKey as v } from "@/lib/i18n/validation";

// Error messages are validation.json keys, translated by <FieldError>.

export const editProfileSchema = z.object({
  fullName: z
    .string()
    .trim()
    .min(1, v("fullNameRequired"))
    .max(200, v("fullNameTooLong")),
});

export type EditProfileFormValues = z.infer<typeof editProfileSchema>;

export const changePasswordSchema = z
  .object({
    currentPassword: z.string().min(1, v("currentPasswordRequired")),
    newPassword: z.string().min(8, v("passwordMinLength")),
    confirmPassword: z.string().min(1, v("confirmNewPasswordRequired")),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: v("passwordsDoNotMatch"),
    path: ["confirmPassword"],
  });

export type ChangePasswordFormValues = z.infer<typeof changePasswordSchema>;

export const deleteAccountSchema = z
  .object({
    currentPassword: z.string().min(1, v("currentPasswordRequired")),
    confirmationText: z.string(),
  })
  .superRefine((data, ctx) => {
    if (data.confirmationText !== "DELETE") {
      ctx.addIssue({
        code: "custom",
        message: v("deleteConfirmationMismatch"),
        path: ["confirmationText"],
      });
    }
  });

export type DeleteAccountFormValues = z.infer<typeof deleteAccountSchema>;
