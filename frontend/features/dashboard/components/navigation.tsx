"use client";

import {
  ChevronsLeft,
  ChevronsRight,
  CloudSun,
  History,
  House,
  Leaf,
  LogOut,
  MapPin,
  ShieldCheck,
  Sprout,
  UserRound,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";

import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { NotificationBell } from "@/components/layout/notification-bell";
import { useFarms } from "@/features/farms/hooks";
import { cn } from "@/lib/utils";
import { useAuth } from "@/providers/auth-provider";
import { useActiveFarm } from "@/providers/active-farm-provider";

import styles from "../home.module.css";
import { FarmSwitcher } from "./farm-switcher";

const ICON_STROKE = 1.75;
const EXPANDED_KEY = "gg-rail-expanded";

const NAV_ITEMS = [
  { href: "/dashboard", key: "home", icon: House },
  { href: "/quick-scan", key: "leafCheck", icon: Leaf },
  { href: "/module2", key: "soilHealth", icon: Sprout },
  { href: "/weather", key: "weather", icon: CloudSun },
  { href: "/farms", key: "farms", icon: MapPin },
  { href: "/history", key: "history", icon: History },
] as const;

/** Slim navigation rail (icon over a short label) that expands to full labels and remembers the choice. */
export function Rail() {
  const t = useTranslations("dashboard.nav");
  const tNav = useTranslations("navigation");
  const pathname = usePathname();
  const { user } = useAuth();
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    try {
      setExpanded(window.localStorage.getItem(EXPANDED_KEY) === "1");
    } catch {
      // Storage can be blocked; the rail simply starts collapsed.
    }
  }, []);

  const toggle = () => {
    setExpanded((value) => {
      try {
        window.localStorage.setItem(EXPANDED_KEY, value ? "0" : "1");
      } catch {
        // Not remembered when storage is blocked.
      }
      return !value;
    });
  };

  const items =
    user?.role === "Admin" ? [...NAV_ITEMS, { href: "/admin", key: "admin", icon: ShieldCheck } as const] : NAV_ITEMS;
  const ToggleIcon = expanded ? ChevronsLeft : ChevronsRight;

  return (
    <nav className={cn(styles.rail, expanded && styles.railExpanded)} aria-label={tNav("mainNavigation")}>
      <Link href="/" className={styles.brand} aria-label="Green Guard home">
        <Image src="/images/brand/shield.png" alt="" width={44} height={52} />
        <span className={styles.brandText}>Green Guard</span>
      </Link>

      <div className={styles.nav}>
        {items.map(({ href, key, icon: Icon }) => {
          const label = key === "admin" ? tNav("admin") : t(key);
          const current = pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`));
          return (
            <Link
              key={href}
              href={href}
              className={styles.navItem}
              aria-current={current ? "page" : undefined}
              title={label}
            >
              <span className={styles.navIcon} aria-hidden="true">
                <Icon strokeWidth={ICON_STROKE} />
              </span>
              <span className={styles.navLabel}>{label}</span>
            </Link>
          );
        })}
      </div>

      <button
        type="button"
        className={styles.railToggle}
        onClick={toggle}
        aria-expanded={expanded}
        aria-label={expanded ? t("collapse") : t("expand")}
        title={expanded ? t("collapse") : t("expand")}
      >
        <ToggleIcon strokeWidth={ICON_STROKE} className="rtl:-scale-x-100" aria-hidden="true" />
      </button>
    </nav>
  );
}

/** Account button with profile and log out, in the top bar only. */
function AccountMenu() {
  const t = useTranslations("dashboard.account");
  const tNav = useTranslations("navigation");
  const { user, logout } = useAuth();
  const farms = useFarms();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [isLoggingOut, setIsLoggingOut] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (event: MouseEvent | KeyboardEvent) => {
      if (event instanceof KeyboardEvent ? event.key === "Escape" : !ref.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", close);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", close);
    };
  }, [open]);

  const handleLogout = async () => {
    setIsLoggingOut(true);
    await logout();
    router.push("/login");
  };

  if (!user) return null;
  return (
    <div className={styles.account} ref={ref}>
      <button
        type="button"
        className={styles.avatarButton}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t("menu")}
        onClick={() => setOpen((value) => !value)}
      >
        {user.fullName.trim().charAt(0).toUpperCase()}
      </button>
      {open && (
        <div className={styles.menu} role="menu">
          <div className={styles.menuHead}>
            <b>{user.fullName}</b>
            {farms.data && <span>{t("farmCount", { count: farms.data.length })}</span>}
          </div>
          <Link href="/profile" role="menuitem" className={styles.menuItem} onClick={() => setOpen(false)}>
            <UserRound strokeWidth={ICON_STROKE} aria-hidden="true" />
            {t("profile")}
          </Link>
          <button
            type="button"
            role="menuitem"
            className={styles.menuItem}
            onClick={handleLogout}
            disabled={isLoggingOut}
          >
            <LogOut strokeWidth={ICON_STROKE} className="rtl:-scale-x-100" aria-hidden="true" />
            {tNav("logout")}
          </button>
        </div>
      )}
    </div>
  );
}

/** The page header's controls: the farm being viewed, language, notifications and the account. */
export function HeaderControls() {
  const farms = useFarms();
  const { activeFarmId, setActiveFarmId } = useActiveFarm();

  return (
    <div className={styles.headerControls}>
      {farms.data && farms.data.length > 0 && (
        <FarmSwitcher farms={farms.data} activeFarmId={activeFarmId} onChange={setActiveFarmId} />
      )}
      <div className={styles.tools}>
        <LanguageSwitcher />
        <NotificationBell />
        <AccountMenu />
      </div>
    </div>
  );
}
