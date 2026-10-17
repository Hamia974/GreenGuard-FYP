"use client";

import { ShieldAlert } from "lucide-react";
import { useTranslations } from "next-intl";

import { LinkButton } from "@/components/ui/link-button";
import { useAuth } from "@/providers/auth-provider";

/**
 * Blocks non-Admin accounts from the Admin Dashboard. Nested inside
 * app/(app)/layout.tsx's ProtectedRoute, which already guarantees the user
 * is authenticated and loaded by the time this renders -- this only adds
 * the role check, per REST_API_SPEC.md section 8 ("Only users with the
 * Admin role are authorized"). The backend independently enforces the same
 * rule on every /api/v1/admin/* endpoint (see adminpanel.permissions.IsAdminRole)
 * -- this is a UX convenience, not the real security boundary.
 */
export function AdminRoute({ children }: { children: React.ReactNode }) {
  const t = useTranslations("admin.accessDenied");
  const tNav = useTranslations("navigation");
  const { user } = useAuth();

  if (user?.role !== "Admin") {
    return (
      <div className="mx-auto flex max-w-md flex-col items-center gap-3 px-4 py-24 text-center">
        <ShieldAlert className="size-8 text-destructive" />
        <p className="text-base font-medium text-foreground">{t("title")}</p>
        <p className="text-sm text-muted-foreground">{t("description")}</p>
        <LinkButton href="/dashboard" className="mt-2 h-11 rounded-2xl px-5">
          {tNav("backToDashboard")}
        </LinkButton>
      </div>
    );
  }

  return <>{children}</>;
}
