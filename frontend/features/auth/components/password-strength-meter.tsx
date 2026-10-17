"use client";

import { useTranslations } from "next-intl";

import { getPasswordStrength } from "@/features/auth/lib/password-strength";
import { cn } from "@/lib/utils";

const LEVEL_STYLES: Record<string, string> = {
  weak: "bg-error-icon",
  fair: "bg-warning-icon",
  good: "bg-info-icon",
  strong: "bg-success-icon",
};

export function PasswordStrengthMeter({ password }: { password: string }) {
  const t = useTranslations("auth.passwordStrength");
  if (!password) return null;

  const strength = getPasswordStrength(password);

  return (
    <div className="flex items-center gap-2" aria-live="polite">
      <div className="flex h-1 flex-1 gap-1">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className={cn(
              "h-full flex-1 rounded-full bg-muted transition-colors",
              index < strength.score && LEVEL_STYLES[strength.level]
            )}
          />
        ))}
      </div>
      <span className="min-w-10 text-end text-xs font-medium text-muted-foreground">
        {t(strength.level)}
      </span>
    </div>
  );
}
