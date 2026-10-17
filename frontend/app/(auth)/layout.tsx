"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { getRedirectFromLocation } from "@/features/auth/lib/safe-redirect";
import { useAuth } from "@/providers/auth-provider";

/** Signed-in visitors are sent on to their (validated) `?next=` destination.
 * This is also how the login and register forms navigate after success. */
export default function AuthRouteLayout({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace(getRedirectFromLocation());
    }
  }, [isLoading, isAuthenticated, router]);

  return <>{children}</>;
}
