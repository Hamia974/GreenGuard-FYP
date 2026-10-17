import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { Suspense } from "react";

import { AuthLayout } from "@/features/auth/components/auth-layout";
import { VerifyEmailStatus } from "@/features/auth/components/verify-email-status";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("metadata");
  return { title: t("verifyEmailTitle") };
}

/** Deliberately outside the (auth) route group: a signed-in user opening the
 * emailed link must stay here long enough to verify, not be bounced to the
 * dashboard. */
export default async function VerifyEmailPage() {
  const t = await getTranslations("auth.verifyEmail");

  return (
    <AuthLayout heading={t("heading")} description={t("description")}>
      <Suspense fallback={null}>
        <VerifyEmailStatus />
      </Suspense>
    </AuthLayout>
  );
}
