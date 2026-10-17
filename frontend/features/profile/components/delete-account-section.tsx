"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { AlertTriangle } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FieldError } from "@/components/ui/field-error";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Spinner } from "@/components/ui/spinner";
import { PasswordInput } from "@/features/auth/components/password-input";
import {
  type DeleteAccountFormValues,
  deleteAccountSchema,
} from "@/features/profile/schemas";
import { useParseApiError } from "@/lib/i18n/use-api-error";

interface DeleteAccountSectionProps {
  onConfirm: (values: DeleteAccountFormValues) => Promise<void>;
}

export function DeleteAccountSection({ onConfirm }: DeleteAccountSectionProps) {
  const t = useTranslations("profile.deleteAccount");
  const tCommon = useTranslations("common");
  const parseApiError = useParseApiError();
  const [isExpanded, setIsExpanded] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<DeleteAccountFormValues>({
    resolver: zodResolver(deleteAccountSchema),
    defaultValues: { currentPassword: "", confirmationText: "" },
  });

  const submit = async (values: DeleteAccountFormValues) => {
    setFormError(null);
    try {
      await onConfirm(values);
    } catch (error) {
      const { message, fieldErrors } = parseApiError(error);
      if (fieldErrors.current_password) {
        setError("currentPassword", { message: fieldErrors.current_password });
      } else {
        setFormError(message);
      }
    }
  };

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-destructive/30 bg-destructive/5 p-4">
      <div>
        <h3 className="flex items-center gap-2 font-heading text-base font-semibold text-destructive">
          <AlertTriangle className="size-4" />
          {t("title")}
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">{t("warning")}</p>
      </div>

      {!isExpanded ? (
        <Button
          type="button"
          variant="destructive"
          className="w-fit"
          onClick={() => setIsExpanded(true)}
        >
          {t("title")}
        </Button>
      ) : (
        <form onSubmit={handleSubmit(submit)} noValidate className="flex flex-col gap-4">
          {formError && (
            <Alert variant="destructive">
              <AlertDescription>{formError}</AlertDescription>
            </Alert>
          )}

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="deleteCurrentPassword">{t("currentPassword")}</Label>
            <PasswordInput
              id="deleteCurrentPassword"
              autoComplete="current-password"
              aria-invalid={!!errors.currentPassword}
              disabled={isSubmitting}
              {...register("currentPassword")}
            />
            <FieldError message={errors.currentPassword?.message} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="confirmationText">
              {t.rich("typeToConfirm", {
                word: (chunks) => (
                  <span dir="ltr" className="font-mono font-semibold">
                    {chunks}
                  </span>
                ),
              })}
            </Label>
            <Input
              id="confirmationText"
              autoComplete="off"
              aria-invalid={!!errors.confirmationText}
              disabled={isSubmitting}
              className="h-11 rounded-[var(--radius-input)]"
              {...register("confirmationText")}
            />
            <FieldError message={errors.confirmationText?.message} />
          </div>

          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="destructive" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Spinner /> {tCommon("deleting")}
                </>
              ) : (
                t("submit")
              )}
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={isSubmitting}
              onClick={() => setIsExpanded(false)}
            >
              {tCommon("cancel")}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}
