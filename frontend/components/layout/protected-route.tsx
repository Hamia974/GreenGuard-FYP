"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Spinner } from "@/components/ui/spinner";
import { buildLoginRedirect } from "@/features/auth/lib/safe-redirect";
import { useAuth } from "@/providers/auth-provider";

/**
 * Redirects unauthenticated visitors to /login, remembering where they were
 * going. A UX convenience only -- every API endpoint enforces authentication
 * and ownership server-side regardless of what this component renders.
 */
export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace(buildLoginRedirect());
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <Spinner className="size-6" />
      </div>
    );
  }

  return <>{children}</>;
}
