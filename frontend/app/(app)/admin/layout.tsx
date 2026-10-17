"use client";

import { LayoutDashboard, ScanLine, Users } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { AdminRoute } from "@/components/layout/admin-route";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/admin", labelKey: "overview", icon: LayoutDashboard },
  { href: "/admin/users", labelKey: "users", icon: Users },
  { href: "/admin/predictions", labelKey: "predictions", icon: ScanLine },
] as const;

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const t = useTranslations("admin");
  const pathname = usePathname();

  return (
    <AdminRoute>
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:px-6">
        <div>
          <h1 className="font-heading text-3xl font-bold text-foreground">{t("title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t("description")}</p>
        </div>

        <nav aria-label={t("title")} className="flex w-fit gap-1 rounded-2xl border border-border bg-card p-1">
          {TABS.map((tab) => {
            const isActive = pathname === tab.href;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                aria-current={isActive ? "page" : undefined}
                className={cn(
                  "flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <tab.icon className="size-4" />
                {t(`tabs.${tab.labelKey}`)}
              </Link>
            );
          })}
        </nav>

        {children}
      </div>
    </AdminRoute>
  );
}
