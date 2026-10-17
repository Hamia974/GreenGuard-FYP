"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, Mail, MailCheck } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FieldError } from "@/components/ui/field-error";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { forgotPasswordRequest } from "@/features/auth/api";
import {
  type ForgotPasswordFormValues,
  forgotPasswordSchema,
} from "@/features/auth/schemas";
import { useParseApiError } from "@/lib/i18n/use-api-error";

export function ForgotPasswordForm() {
  const t = useTranslations("auth");
  const parseApiError = useParseApiError();
  const [formError, setFormError] = useState<string | null>(null);
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: "" },
  });

  const onSubmit = async (values: ForgotPasswordFormValues) => {
    setFormError(null);
    try {
      await forgotPasswordRequest(values.email);
      setSubmittedEmail(values.email);
    } catch (error) {
      setFormError(parseApiError(error).message);
    }
  };

  if (submittedEmail) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex size-14 items-center justify-center rounded-full bg-success-bg text-success-icon">
          <MailCheck className="size-7" />
        </div>
        <p className="text-sm text-muted-foreground">
          {t.rich("forgotPassword.sent", {
            email: submittedEmail,
            strong: (chunks) => <strong>{chunks}</strong>,
          })}
        </p>
        <Link href="/login" className="text-sm font-medium text-primary hover:underline">
          {t("forgotPassword.backToSignIn")}
        </Link>
      </div>
    );
  }

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

      <Button
        type="submit"
        disabled={isSubmitting}
        className="h-[52px] rounded-2xl text-base font-semibold shadow-[var(--shadow-color-sm)] transition-transform hover:-translate-y-0.5 hover:shadow-[var(--shadow-color-hover)]"
      >
        {isSubmitting ? (
          <>
            <Spinner /> {t("forgotPassword.submitting")}
          </>
        ) : (
          t("forgotPassword.submit")
        )}
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        {t.rich("forgotPassword.remembered", {
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
