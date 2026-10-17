"use client";

import { useMutation } from "@tanstack/react-query";
import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { resendVerificationRequest } from "@/features/auth/api";
import { useParseApiError } from "@/lib/i18n/use-api-error";

/** Verification badge plus a "resend link" action for unverified accounts.
 * The link always goes to the account's own address (server-side). */
export function EmailVerificationStatus({ isVerified }: { isVerified: boolean }) {
  const t = useTranslations("profile.accountInfo");
  const parseApiError = useParseApiError();
  const resend = useMutation({ mutationFn: resendVerificationRequest });

  if (isVerified) {
    return <Badge variant="success">{t("verified")}</Badge>;
  }

  return (
    <div className="flex flex-col items-end gap-1.5">
      <div className="flex items-center gap-2">
        <Badge variant="warning">{t("notVerified")}</Badge>
        <Button
          type="button"
          variant="link"
          size="sm"
          className="h-auto px-0"
          disabled={resend.isPending || resend.isSuccess}
          onClick={() => resend.mutate()}
        >
          {resend.isPending && <Spinner />}
          {t("resendVerification")}
        </Button>
      </div>
      <p aria-live="polite" className="text-end text-xs text-muted-foreground">
        {resend.isSuccess && t("verificationSent")}
        {resend.isError && (
          <span className="text-destructive">{parseApiError(resend.error).message}</span>
        )}
      </p>
    </div>
  );
}
