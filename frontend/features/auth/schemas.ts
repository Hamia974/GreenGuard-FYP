import { z } from "zod";

import { validationKey as v } from "@/lib/i18n/validation";

// Error messages are validation.json keys, translated by <FieldError>.

export const loginSchema = z.object({
  email: z.email(v("emailInvalid")),
  password: z.string().min(1, v("passwordRequired")),
  rememberMe: z.boolean(),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    fullName: z
      .string()
      .trim()
      .min(1, v("fullNameRequired"))
      .max(200, v("fullNameTooLong")),
    email: z.email(v("emailInvalid")),
    password: z
      .string()
      .min(8, v("passwordMinLength")),
    confirmPassword: z.string().min(1, v("confirmPasswordRequired")),
    acceptTerms: z
      .boolean()
      .refine((value) => value === true, v("acceptTermsRequired")),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: v("passwordsDoNotMatch"),
    path: ["confirmPassword"],
  });

export type RegisterFormValues = z.infer<typeof registerSchema>;

export const forgotPasswordSchema = z.object({
  email: z.email(v("emailInvalid")),
});

export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    newPassword: z.string().min(8, v("passwordMinLength")),
    confirmPassword: z.string().min(1, v("confirmPasswordRequired")),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: v("passwordsDoNotMatch"),
    path: ["confirmPassword"],
  });

export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;
