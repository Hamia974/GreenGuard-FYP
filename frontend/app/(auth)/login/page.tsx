import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { AuthLayout } from "@/features/auth/components/auth-layout";
import { LoginForm } from "@/features/auth/components/login-form";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("metadata");
  return { title: t("loginTitle") };
}

export default async function LoginPage() {
  const t = await getTranslations("auth.login");

  return (
    <AuthLayout heading={t("heading")} description={t("description")}>
      <LoginForm />
    </AuthLayout>
  );
}
