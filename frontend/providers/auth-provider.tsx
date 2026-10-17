"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { fetchProfile, loginRequest, logoutRequest, registerRequest } from "@/features/auth/api";
import type { AuthUser, LoginPayload, RegisterPayload } from "@/features/auth/types";
import { SESSION_EXPIRED_EVENT } from "@/lib/api-client";

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  register: (payload: RegisterPayload) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const queryClient = useQueryClient();

  useEffect(() => {
    let cancelled = false;

    // The session lives in HttpOnly cookies the page cannot read, so the
    // only way to know whether one exists is to ask the backend. A 401 here
    // is retried once through the refresh cookie by the API client.
    async function hydrate() {
      try {
        const profile = await fetchProfile();
        if (!cancelled) setUser(profile);
      } catch {
        // Signed out (or backend unreachable) -- stay anonymous.
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    }

    hydrate();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const handleSessionExpired = () => {
      setUser(null);
      queryClient.clear();
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
    return () => window.removeEventListener(SESSION_EXPIRED_EVENT, handleSessionExpired);
  }, [queryClient]);

  const login = useCallback(async (payload: LoginPayload) => {
    const loggedInUser = await loginRequest(payload);
    // Never let a previous account's cached farms/reports show for this one.
    queryClient.clear();
    setUser(loggedInUser);
  }, [queryClient]);

  const register = useCallback(async (payload: RegisterPayload) => {
    await registerRequest(payload);
  }, []);

  const logout = useCallback(async () => {
    try {
      await logoutRequest();
    } catch {
      // The backend clears the cookies and revokes the refresh token; if it
      // is unreachable the user is still signed out of this UI, and the
      // tokens expire on their own.
    }
    setUser(null);
    queryClient.clear();
  }, [queryClient]);

  const refreshUser = useCallback(async () => {
    const profile = await fetchProfile();
    setUser(profile);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isLoading,
      isAuthenticated: user !== null,
      login,
      register,
      logout,
      refreshUser,
    }),
    [user, isLoading, login, register, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
