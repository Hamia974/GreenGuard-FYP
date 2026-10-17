"use client";

import { useEffect, useState } from "react";

import { defaultLocale, getDirection, isLocale, LOCALE_COOKIE, type Locale } from "@/lib/i18n/config";
import enErrors from "@/messages/en/errors.json";
import urErrors from "@/messages/ur/errors.json";

// The root layout (and with it the i18n provider) is gone when this renders,
// so it reads the same message files directly instead of useTranslations().
const BOUNDARY_MESSAGES: Record<Locale, typeof enErrors.boundary> = {
  en: enErrors.boundary,
  ur: urErrors.boundary,
};

function readLocaleCookie(): Locale {
  if (typeof document === "undefined") return defaultLocale;
  const value = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${LOCALE_COOKIE}=`))
    ?.split("=")[1];
  return isLocale(value) ? value : defaultLocale;
}

/**
 * Catches errors thrown by the root layout itself (app/error.tsx cannot --
 * it renders inside the layout, so a layout-level crash bypasses it). Must
 * render its own <html>/<body> since it replaces the entire root layout,
 * so it cannot rely on globals.css/Tailwind tokens being available -- kept
 * to plain inline styles as a last-resort fallback.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const [locale] = useState<Locale>(readLocaleCookie);
  const messages = BOUNDARY_MESSAGES[locale];

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <html lang={locale} dir={getDirection(locale)}>
      <body
        style={{
          display: "flex",
          minHeight: "100vh",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          gap: "0.75rem",
          padding: "1.5rem",
          textAlign: "center",
          fontFamily: "system-ui, sans-serif",
          background: "#E3E5D8",
          color: "#101916",
        }}
      >
        <h1 style={{ fontSize: "1.5rem", fontWeight: 700 }}>{messages.title}</h1>
        <p style={{ maxWidth: "24rem", fontSize: "0.875rem", color: "#355245" }}>
          {messages.description}
        </p>
        <button
          type="button"
          onClick={() => reset()}
          style={{
            marginTop: "0.5rem",
            height: "2.75rem",
            borderRadius: "1rem",
            padding: "0 1.25rem",
            border: "none",
            background: "#101916",
            color: "#E3E5D8",
            fontWeight: 500,
            cursor: "pointer",
          }}
        >
          {messages.retry}
        </button>
      </body>
    </html>
  );
}
