"use client";

import { AlertTriangleIcon } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect } from "react";

import { Button } from "@/components/ui/button";

/**
 * Global runtime-error boundary. Never shows the raw error message to the
 * user (matches the backend's own "never expose server errors" rule) --
 * only logs it to the console for local/devtools debugging.
 */
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("errors.boundary");
  const tCommon = useTranslations("common");

  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-3 bg-background px-6 text-center">
      <AlertTriangleIcon className="size-8 text-destructive" />
      <h1 className="font-heading text-2xl font-bold text-foreground">{t("title")}</h1>
      <p className="max-w-sm text-sm text-muted-foreground">{t("description")}</p>
      <Button type="button" className="mt-2 h-11 rounded-2xl px-5" onClick={() => reset()}>
        {tCommon("tryAgain")}
      </Button>
    </main>
  );
}
