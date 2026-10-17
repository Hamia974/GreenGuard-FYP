"use client";

import {
  CloudSun,
  History,
  LogOut,
  Menu,
  ScanLine,
  ShieldCheck,
  Sprout,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { LinkButton } from "@/components/ui/link-button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { NotificationBell } from "@/components/layout/notification-bell";
import { useAuth } from "@/providers/auth-provider";

const NAV_LINKS = [
  { href: "/dashboard", labelKey: "dashboard" },
  { href: "/quick-scan", labelKey: "quickScan" },
  { href: "/module1", labelKey: "diseaseCheck", icon: ScanLine },
  { href: "/farms", labelKey: "farms" },
  { href: "/module2", labelKey: "soilHealth" },
  { href: "/history", labelKey: "history", icon: History },
  { href: "/weather", labelKey: "weather", icon: CloudSun },
] as const;

const MOBILE_LINK_CLASS =
  "flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted";

/** Top navigation for the authenticated app shell. New routes are added here as later phases ship. */
export function AppNavbar() {
  const t = useTranslations("navigation");
  const tCommon = useTranslations("common");
  const { user, logout } = useAuth();
  const router = useRouter();
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const closeMobileMenu = () => setIsMobileMenuOpen(false);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    await logout();
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-10 border-b border-border bg-card/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link href="/dashboard" className="flex items-center gap-2 font-heading text-lg font-bold text-primary">
          <Sprout className="size-5" />
          {tCommon("appName")}
        </Link>

        <nav aria-label={t("mainNavigation")} className="hidden items-center gap-1 lg:flex">
          {NAV_LINKS.map((link) => (
            <LinkButton
              href={link.href}
              key={link.href}
              variant="ghost"
              size="sm"
            >
              {"icon" in link && <link.icon className="size-4" />}
              {t(link.labelKey)}
            </LinkButton>
          ))}
          {user?.role === "Admin" && (
            <LinkButton href="/admin" variant="ghost" size="sm">
              <ShieldCheck className="size-4" />
              {t("admin")}
            </LinkButton>
          )}
        </nav>

        <div className="flex items-center gap-2 sm:gap-3">
          <LanguageSwitcher />
          <NotificationBell />
          {user && (
            <Link
              href="/profile"
              className="hidden text-sm text-muted-foreground transition-colors hover:text-foreground sm:inline"
            >
              {user.fullName}
            </Link>
          )}
          <Button
            type="button"
            variant="outline"
            size="sm"
            disabled={isLoggingOut}
            onClick={handleLogout}
            className="hidden lg:inline-flex"
          >
            <LogOut className="rtl:-scale-x-100" />
            {t("logout")}
          </Button>

          <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
            <SheetTrigger
              render={
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  className="lg:hidden"
                  aria-label={t("openMenu")}
                />
              }
            >
              <Menu className="size-4" />
            </SheetTrigger>
            <SheetContent>
              <SheetHeader>
                <SheetTitle>{t("menu")}</SheetTitle>
              </SheetHeader>
              <nav aria-label={t("mainNavigation")} className="flex flex-1 flex-col gap-1">
                {NAV_LINKS.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    onClick={closeMobileMenu}
                    className={MOBILE_LINK_CLASS}
                  >
                    {"icon" in link && <link.icon className="size-4" />}
                    {t(link.labelKey)}
                  </Link>
                ))}
                {user?.role === "Admin" && (
                  <Link href="/admin" onClick={closeMobileMenu} className={MOBILE_LINK_CLASS}>
                    <ShieldCheck className="size-4" />
                    {t("admin")}
                  </Link>
                )}
                <Link href="/profile" onClick={closeMobileMenu} className={MOBILE_LINK_CLASS}>
                  {t("profile")}
                </Link>
              </nav>
              <Button
                type="button"
                variant="outline"
                disabled={isLoggingOut}
                onClick={() => {
                  setIsMobileMenuOpen(false);
                  void handleLogout();
                }}
              >
                <LogOut className="rtl:-scale-x-100" />
                {t("logout")}
              </Button>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
