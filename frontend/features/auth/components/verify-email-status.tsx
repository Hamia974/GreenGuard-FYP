"use client";

import { useQueryClient } from "@tanstack/react-query";
import { isAxiosError } from "axios";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { LinkButton } from "@/components/ui/link-button";
import { Spinner } from "@/components/ui/spinner";
import { verifyEmailRequest } from "@/features/auth/api";
import { profileQueryKey } from "@/features/profile/hooks";
import { useParseApiError } from "@/lib/i18n/use-api-error";
import { useAuth } from "@/providers/auth-provider";

type VerifyState = { status: "verifying" } | { status: "success" } | { status: "error"; message: string };

/** Consumes the `?token=` from the verification email exactly once. */
export function VerifyEmailStatus() {
  const t = useTranslations("auth.verifyEmail");
  const parseApiError = useParseApiError();
  const token = useSearchParams().get("token");
  const { isAuthenticated, refreshUser } = useAuth();
  const queryClient = useQueryClient();
  const [state, setState] = useState<VerifyState>({ status: "verifying" });
  const hasSubmitted = useRef(false);

  useEffect(() => {
    // Guards against React Strict Mode's double effect run in development.
    if (!token || hasSubmitted.current) return;
    hasSubmitted.current = true;

    verifyEmailRequest(token)
      .then(() => setState({ status: "success" }))
      .catch((error) =>
        setState({
          status: "error",
          // 400 is the one expected failure (bad, expired or tampered link);
          // anything else falls back to the generic/network messages.
          message:
            isAxiosError(error) && error.response?.status === 400
              ? t("invalidLink")
              : parseApiError(error).message,
        })
      );
  }, [token, parseApiError, t]);

  useEffect(() => {
    if (state.status === "success" && isAuthenticated) {
      void refreshUser().catch(() => undefined);
      void queryClient.invalidateQueries({ queryKey: profileQueryKey });
    }
  }, [state.status, isAuthenticated, refreshUser, queryClient]);

  const continueHref = isAuthenticated ? "/dashboard" : "/login";
  const continueLabel = isAuthenticated ? t("goToDashboard") : t("goToSignIn");

  if (!token) {
    return (
      <Alert variant="destructive">
        <AlertCircle />
        <AlertDescription>{t("missingToken")}</AlertDescription>
      </Alert>
    );
  }

  if (state.status === "verifying") {
    return (
      <div role="status" className="flex items-center justify-center gap-2 py-6 text-sm text-muted-foreground">
        <Spinner /> {t("verifying")}
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="flex flex-col gap-4">
        <Alert variant="destructive">
          <AlertCircle />
          <AlertDescription>
            {state.message} {isAuthenticated ? t("resendFromProfile") : t("signInToResend")}
          </AlertDescription>
        </Alert>
        <LinkButton
          href={isAuthenticated ? "/profile" : "/login"}
          variant="outline"
          className="h-11 rounded-2xl"
        >
          {isAuthenticated ? t("goToProfile") : t("goToSignIn")}
        </LinkButton>
      </div>
    );
  }

  return (
    <div role="status" className="flex flex-col items-center gap-4 text-center">
      <div className="flex size-14 items-center justify-center rounded-full bg-success-bg text-success-icon">
        <CheckCircle2 className="size-7" />
      </div>
      <p className="text-sm text-muted-foreground">{t("success")}</p>
      <LinkButton href={continueHref} className="h-11 rounded-2xl px-6">
        {continueLabel}
      </LinkButton>
    </div>
  );
}
