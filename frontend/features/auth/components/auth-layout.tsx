"use client";

import { motion } from "framer-motion";
import { Lock, ShieldCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { LanguageSwitcher } from "@/components/layout/language-switcher";

import { AuthIllustration } from "./auth-illustration";

interface AuthLayoutProps {
  heading: string;
  description: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

const SECURITY_CUES = [
  { icon: Lock, labelKey: "secureLogin" },
  { icon: ShieldCheck, labelKey: "encryptedConnection" },
  { icon: Sparkles, labelKey: "privacyProtected" },
] as const;

export function AuthLayout({ heading, description, children, footer }: AuthLayoutProps) {
  const t = useTranslations("auth.securityCues");
  const tCommon = useTranslations("common");

  return (
    <div className="relative min-h-screen bg-background">
      <LanguageSwitcher className="absolute end-4 top-4 z-10 sm:end-6 sm:top-6" />
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background:
            "radial-gradient(45% 45% at 15% 10%, color-mix(in oklch, var(--primary-100), transparent 55%), transparent), radial-gradient(45% 45% at 90% 90%, color-mix(in oklch, var(--primary-200), transparent 60%), transparent)",
        }}
      />

      <div className="flex min-h-screen flex-col lg:flex-row">
        <div className="flex h-40 shrink-0 items-center justify-center sm:h-56 lg:h-auto lg:basis-[45%]">
          <AuthIllustration />
        </div>

        <div className="flex flex-1 items-center justify-center px-4 py-8 sm:px-6 lg:basis-[55%] lg:py-10">
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="w-full max-w-[520px] rounded-2xl bg-card p-6 shadow-[var(--shadow-color-md)] sm:p-10"
          >
            <div className="mb-8 flex flex-col items-center gap-2 text-center">
              <Link href="/" className="font-heading text-xl font-bold text-primary">
                {tCommon("appName")}
              </Link>
              <h1 className="mt-3 font-heading text-3xl font-bold text-foreground">
                {heading}
              </h1>
              <p className="text-base text-muted-foreground">{description}</p>
            </div>

            {children}

            {footer}

            <div className="mt-8 flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
              {SECURITY_CUES.map(({ icon: Icon, labelKey }) => (
                <span key={labelKey} className="inline-flex items-center gap-1">
                  <Icon className="size-3.5" />
                  {t(labelKey)}
                </span>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
