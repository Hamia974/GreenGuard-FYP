"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Mail } from "lucide-react";
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
import { type LoginFormValues, loginSchema } from "@/features/auth/schemas";
import { useParseApiError } from "@/lib/i18n/use-api-error";
import { useAuth } from "@/providers/auth-provider";

export function LoginForm() {
  const t = useTranslations("auth");
  const parseApiError = useParseApiError();
  const { login } = useAuth();
  const [formError, setFormError] = useState<string | null>(null);
  const [isRedirecting, setIsRedirecting] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting: isSubmittingForm },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "", rememberMe: false },
  });

  const isSubmitting = isSubmittingForm || isRedirecting;

  const onSubmit = async (values: LoginFormValues) => {
    setFormError(null);
    try {
      await login({
        email: values.email,
        password: values.password,
        rememberMe: values.rememberMe,
      });
      // (auth)/layout.tsx redirects to the validated ?next= destination.
      setIsRedirecting(true);
    } catch (error) {
      setFormError(parseApiError(error).message);
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

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="email">{t("fields.email")}</Label>
        <div className="relative">
          <Mail className="pointer-events-none absolute top-1/2 start-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder={t("fields.emailPlaceholder")}
            aria-invalid={!!errors.email}
            className="h-11 rounded-[var(--radius-input)] ps-8.5"
            disabled={isSubmitting}
            {...register("email")}
          />
        </div>
        <FieldError message={errors.email?.message} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="password">{t("fields.password")}</Label>
        <PasswordInput
          id="password"
          autoComplete="current-password"
          placeholder={t("fields.passwordPlaceholder")}
          aria-invalid={!!errors.password}
          disabled={isSubmitting}
          {...register("password")}
        />
        <FieldError message={errors.password?.message} />
      </div>

      <div className="flex items-center justify-between">
        <Label htmlFor="rememberMe" className="font-normal">
          <Controller
            control={control}
            name="rememberMe"
            render={({ field }) => (
              <Checkbox
                id="rememberMe"
                disabled={isSubmitting}
                checked={field.value}
                onCheckedChange={field.onChange}
              />
            )}
          />
          {t("login.rememberMe")}
        </Label>
        <Link
          href="/forgot-password"
          className="text-sm font-medium text-primary hover:underline"
        >
          {t("login.forgotPassword")}
        </Link>
      </div>

      <Button
        type="submit"
        disabled={isSubmitting}
        className="h-[52px] rounded-2xl text-base font-semibold shadow-[var(--shadow-color-sm)] transition-transform hover:-translate-y-0.5 hover:shadow-[var(--shadow-color-hover)]"
      >
        {isSubmitting ? (
          <>
            <Spinner /> {t("login.submitting")}
          </>
        ) : (
          t("login.submit")
        )}
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        {t.rich("login.noAccount", {
          link: (chunks) => (
            <Link href="/register" className="font-medium text-primary hover:underline">
              {chunks}
            </Link>
          ),
        })}
      </p>
    </form>
  );
}
