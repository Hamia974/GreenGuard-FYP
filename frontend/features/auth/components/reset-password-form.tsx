"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import { FieldError } from "@/components/ui/field-error";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { resetPasswordRequest } from "@/features/auth/api";
import { PasswordInput } from "@/features/auth/components/password-input";
import { PasswordStrengthMeter } from "@/features/auth/components/password-strength-meter";
import {
  type ResetPasswordFormValues,
  resetPasswordSchema,
} from "@/features/auth/schemas";
import { useParseApiError } from "@/lib/i18n/use-api-error";

export function ResetPasswordForm() {
  const t = useTranslations("auth");
  const parseApiError = useParseApiError();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [formError, setFormError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: { newPassword: "", confirmPassword: "" },
  });

  const newPassword = watch("newPassword");

  const onSubmit = async (values: ResetPasswordFormValues) => {
    if (!token) {
      setFormError(t("resetPassword.missingToken"));
      return;
    }
    setFormError(null);
    try {
      await resetPasswordRequest(token, values.newPassword, values.confirmPassword);
      setIsComplete(true);
    } catch (error) {
      setFormError(parseApiError(error).message);
    }
  };

  if (isComplete) {
    return (
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="flex size-14 items-center justify-center rounded-full bg-success-bg text-success-icon">
          <CheckCircle2 className="size-7" />
        </div>
        <p className="text-sm text-muted-foreground">{t("resetPassword.success")}</p>
        <LinkButton href="/login" className="h-11 rounded-2xl px-6">
          {t("resetPassword.goToSignIn")}
        </LinkButton>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} noValidate className="flex flex-col gap-5">
      {!token && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>
            {t.rich("resetPassword.invalidLink", {
              link: (chunks) => (
                <Link href="/forgot-password" className="underline">
                  {chunks}
                </Link>
              ),
            })}
          </AlertDescription>
        </Alert>
      )}

      {formError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="newPassword">{t("fields.newPassword")}</Label>
        <PasswordInput
          id="newPassword"
          autoComplete="new-password"
          placeholder={t("fields.newPasswordPlaceholder")}
          aria-invalid={!!errors.newPassword}
          disabled={isSubmitting}
          {...register("newPassword")}
        />
        <PasswordStrengthMeter password={newPassword} />
        <FieldError message={errors.newPassword?.message} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="confirmPassword">{t("fields.confirmPassword")}</Label>
        <PasswordInput
          id="confirmPassword"
          autoComplete="new-password"
          placeholder={t("fields.confirmNewPasswordPlaceholder")}
          aria-invalid={!!errors.confirmPassword}
          disabled={isSubmitting}
          {...register("confirmPassword")}
        />
        <FieldError message={errors.confirmPassword?.message} />
      </div>

      <Button
        type="submit"
        disabled={isSubmitting || !token}
        className="h-[52px] rounded-2xl text-base font-semibold shadow-[var(--shadow-color-sm)] transition-transform hover:-translate-y-0.5 hover:shadow-[var(--shadow-color-hover)]"
      >
        {isSubmitting ? (
          <>
            <Spinner /> {t("resetPassword.submitting")}
          </>
        ) : (
          t("resetPassword.submit")
        )}
      </Button>
    </form>
  );
}
