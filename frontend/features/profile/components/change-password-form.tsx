"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FieldError } from "@/components/ui/field-error";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { PasswordInput } from "@/features/auth/components/password-input";
import { PasswordStrengthMeter } from "@/features/auth/components/password-strength-meter";
import {
  type ChangePasswordFormValues,
  changePasswordSchema,
} from "@/features/profile/schemas";
import { useParseApiError } from "@/lib/i18n/use-api-error";

interface ChangePasswordFormProps {
  onSubmit: (values: ChangePasswordFormValues) => Promise<void>;
}

export function ChangePasswordForm({ onSubmit }: ChangePasswordFormProps) {
  const t = useTranslations("profile.changePassword");
  const parseApiError = useParseApiError();
  const [formError, setFormError] = useState<string | null>(null);
  const [isSaved, setIsSaved] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ChangePasswordFormValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: { currentPassword: "", newPassword: "", confirmPassword: "" },
  });

  const newPassword = watch("newPassword");

  const submit = async (values: ChangePasswordFormValues) => {
    setFormError(null);
    setIsSaved(false);
    try {
      await onSubmit(values);
      reset();
      setIsSaved(true);
    } catch (error) {
      const { message, fieldErrors } = parseApiError(error);
      if (fieldErrors.current_password) {
        setError("currentPassword", { message: fieldErrors.current_password });
      } else if (fieldErrors.new_password) {
        setError("newPassword", { message: fieldErrors.new_password });
      } else {
        setFormError(message);
      }
    }
  };

  return (
    <form
      onSubmit={handleSubmit(submit)}
      onChange={() => setIsSaved(false)}
      noValidate
      className="flex flex-col gap-5"
    >
      {formError && (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}

      {isSaved && (
        <Alert>
          <CheckCircle2 />
          <AlertDescription>{t("success")}</AlertDescription>
        </Alert>
      )}

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="currentPassword">{t("currentPassword")}</Label>
        <PasswordInput
          id="currentPassword"
          autoComplete="current-password"
          aria-invalid={!!errors.currentPassword}
          disabled={isSubmitting}
          {...register("currentPassword")}
        />
        <FieldError message={errors.currentPassword?.message} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="newPassword">{t("newPassword")}</Label>
        <PasswordInput
          id="newPassword"
          autoComplete="new-password"
          aria-invalid={!!errors.newPassword}
          disabled={isSubmitting}
          {...register("newPassword")}
        />
        <PasswordStrengthMeter password={newPassword} />
        <FieldError message={errors.newPassword?.message} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="confirmPassword">{t("confirmNewPassword")}</Label>
        <PasswordInput
          id="confirmPassword"
          autoComplete="new-password"
          aria-invalid={!!errors.confirmPassword}
          disabled={isSubmitting}
          {...register("confirmPassword")}
        />
        <FieldError message={errors.confirmPassword?.message} />
      </div>

      <Button type="submit" disabled={isSubmitting} className="h-11 w-fit rounded-2xl px-6">
        {isSubmitting ? (
          <>
            <Spinner /> {t("submitting")}
          </>
        ) : (
          t("submit")
        )}
      </Button>
    </form>
  );
}
