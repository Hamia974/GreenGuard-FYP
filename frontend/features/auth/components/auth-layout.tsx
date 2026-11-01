"use client";

import { useTranslations } from "next-intl";

import { LanguageSwitcher } from "@/components/layout/language-switcher";

import { AuthPhotoPanel } from "./auth-photo-panel";

interface AuthLayoutProps {
  heading: string;
  description: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

/** The product name reads the same in every language. */
const BRAND_NAME = "Green Guard";

export function AuthLayout({ heading, description, children, footer }: AuthLayoutProps) {
  const t = useTranslations("auth");

  return (
    <div className="auth-page">
      <AuthPhotoPanel headline={t("panelHeadline")} brandName={BRAND_NAME} />
      <main className="auth-main">
        <LanguageSwitcher className="auth-language" />
        <div className="auth-inner">
          <div className="auth-heading">
            <h1>{heading}</h1>
            <p>{description}</p>
          </div>
          {children}
          {footer}
        </div>
      </main>
    </div>
  );
}
