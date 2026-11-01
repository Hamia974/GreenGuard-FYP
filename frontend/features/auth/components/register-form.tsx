"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Check, X } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { FieldError } from "@/components/ui/field-error";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { PasswordInput } from "@/features/auth/components/password-input";
import { PasswordStrengthMeter } from "@/features/auth/components/password-strength-meter";
import { type RegisterFormValues, registerSchema } from "@/features/auth/schemas";
import { useParseApiError } from "@/lib/i18n/use-api-error";
import { useAuth } from "@/providers/auth-provider";

/** Register API fields, and the form fields that show their errors. */
const API_FIELDS = [
  ["full_name", "fullName"],
  ["email", "email"],
  ["password", "password"],
  ["confirm_password", "confirmPassword"],
] as const;

export function RegisterForm() {
  const t = useTranslations("auth");
  const parseApiError = useParseApiError();
  const { register: registerUser, login } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const [isRedirecting, setIsRedirecting] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    watch,
    setError,
    formState: { errors, isSubmitting: isSubmittingForm },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      fullName: "",
      email: "",
      password: "",
      confirmPassword: "",
      acceptTerms: false,
    },
  });

  const password = watch("password");
  const confirmPassword = watch("confirmPassword");
  const showMatchFeedback = confirmPassword.length > 0;
  const passwordsMatch = password === confirmPassword;

  const isSubmitting = isSubmittingForm || isRedirecting;

  const onSubmit = async (values: RegisterFormValues) => {
    setFormError(null);
    try {
      await registerUser({
        fullName: values.fullName,
        email: values.email,
        password: values.password,
        confirmPassword: values.confirmPassword,
      });
      await login({ email: values.email, password: values.password });
      // (auth)/layout.tsx redirects once the session is established.
      setIsRedirecting(true);
    } catch (error) {
      const { message, fieldErrors } = parseApiError(error);
      let shownBesideField = false;
      for (const [apiField, field] of API_FIELDS) {
        if (fieldErrors[apiField]) {
          setError(field, { message: fieldErrors[apiField] });
          shownBesideField = true;
        }
      }
      if (!shownBesideField) setFormError(message);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
      {formError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <div className="auth-field">
        <Label htmlFor="fullName">{t("fields.fullName")}</Label>
        <Input
          id="fullName"
          autoComplete="name"
          placeholder={t("fields.fullNamePlaceholder")}
          aria-invalid={!!errors.fullName}
          className="h-11 rounded-[var(--radius-input)]"
          disabled={isSubmitting}
          {...register("fullName")}
        />
        <FieldError message={errors.fullName?.message} />
      </div>

      <div className="auth-field">
        <Label htmlFor="email">{t("fields.email")}</Label>
        <Input
          id="email"
          type="email"
          autoComplete="email"
          placeholder={t("fields.emailPlaceholder")}
          aria-invalid={!!errors.email}
          className="h-11 rounded-[var(--radius-input)]"
          disabled={isSubmitting}
          {...register("email")}
        />
        <FieldError message={errors.email?.message} />
      </div>

      <div className="auth-field">
        <Label htmlFor="password">{t("fields.password")}</Label>
        <PasswordInput
          showIcon={false}
          id="password"
          autoComplete="new-password"
          placeholder={t("fields.passwordPlaceholder")}
          aria-invalid={!!errors.password}
          disabled={isSubmitting}
          {...register("password")}
        />
        <PasswordStrengthMeter password={password} />
        <FieldError message={errors.password?.message} />
      </div>

      <div className="auth-field">
        <Label htmlFor="confirmPassword">{t("fields.confirmPassword")}</Label>
        <PasswordInput
          showIcon={false}
          id="confirmPassword"
          autoComplete="new-password"
          placeholder={t("fields.confirmPasswordPlaceholder")}
          aria-invalid={!!errors.confirmPassword}
          disabled={isSubmitting}
          {...register("confirmPassword")}
        />
        {showMatchFeedback && !errors.confirmPassword && (
          <p
            className={`flex items-center gap-1 text-xs ${
              passwordsMatch ? "text-success-text" : "text-error-text"
            }`}
          >
            {passwordsMatch ? <Check className="size-3.5" /> : <X className="size-3.5" />}
            {passwordsMatch ? t("register.passwordsMatch") : t("register.passwordsDoNotMatch")}
          </p>
        )}
        <FieldError message={errors.confirmPassword?.message} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="acceptTerms" className="font-normal">
          <Controller
            control={control}
            name="acceptTerms"
            render={({ field }) => (
              <Checkbox
                id="acceptTerms"
                disabled={isSubmitting}
                checked={field.value}
                onCheckedChange={field.onChange}
                aria-invalid={!!errors.acceptTerms}
              />
            )}
          />
          <span>
            {t.rich("register.acceptTerms", {
              terms: (chunks) => (
                <Link href="/terms" className="text-primary hover:underline">
                  {chunks}
                </Link>
              ),
              privacy: (chunks) => (
                <Link href="/privacy" className="text-primary hover:underline">
                  {chunks}
                </Link>
              ),
            })}
          </span>
        </Label>
        <FieldError message={errors.acceptTerms?.message} />
      </div>

      <Button
        type="submit"
        disabled={isSubmitting}
        className="auth-submit"
      >
        {isSubmitting ? (
          <>
            <Spinner /> {t("register.submitting")}
          </>
        ) : (
          t("register.submit")
        )}
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        {t.rich("register.haveAccount", {
          link: (chunks) => (
            <Link href="/login" className="font-medium text-primary hover:underline">
              {chunks}
            </Link>
          ),
        })}
      </p>
    </form>
  );
}
