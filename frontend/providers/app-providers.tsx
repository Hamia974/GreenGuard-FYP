"use client";

import { ActiveFarmProvider } from "@/providers/active-farm-provider";
import { AuthProvider } from "@/providers/auth-provider";
import { QueryProvider } from "@/providers/query-provider";
import { ThemeProvider } from "@/providers/theme-provider";

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="light"
      enableSystem
      disableTransitionOnChange
    >
      <QueryProvider>
        <AuthProvider>
          <ActiveFarmProvider>{children}</ActiveFarmProvider>
        </AuthProvider>
      </QueryProvider>
    </ThemeProvider>
  );
}
