import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

/**
 * Single Axios instance for all communication with the Django REST backend.
 * The frontend must never call AI services or the database directly —
 * every request goes through this client to /api/v1/*.
 *
 * Authentication uses HttpOnly cookies set by the backend (see
 * docs/AUTHENTICATION.md): this code never sees, stores or attaches a JWT.
 * It only sends cookies (`withCredentials`) and echoes the CSRF token on
 * unsafe requests.
 */
export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_BASE_URL,
  timeout: 30_000,
  withCredentials: true,
  headers: {
    Accept: "application/json",
  },
});

/** Event fired when the session can no longer be refreshed; AuthContext listens for this. */
export const SESSION_EXPIRED_EVENT = "greenguard:session-expired";

/** Must match authentication/backends.py CSRF_FAILED_MESSAGE. */
const CSRF_FAILED_MESSAGE = "CSRF verification failed.";
const CSRF_HEADER = "X-CSRFToken";
const SAFE_METHODS = new Set(["get", "head", "options"]);

/** Endpoints that never carry an authenticated session, so a 401 from them
 * must not trigger a token refresh. */
const PUBLIC_AUTH_PATHS = [
  "/auth/csrf/",
  "/auth/login/",
  "/auth/register/",
  "/auth/refresh/",
  "/auth/logout/",
  "/auth/forgot-password/",
  "/auth/reset-password/",
  "/auth/verify-email/",
];

// Kept in memory only: the CSRF token is not a credential, but there is no
// reason to persist it, and a reload simply fetches a fresh one.
let csrfToken: string | null = null;
let csrfPromise: Promise<string> | null = null;

async function fetchCsrfToken(): Promise<string> {
  const response = await axios.get(`${process.env.NEXT_PUBLIC_API_BASE_URL}/auth/csrf/`, {
    withCredentials: true,
  });
  return response.data.data.csrf_token as string;
}

function getCsrfToken(): Promise<string> {
  if (csrfToken) return Promise.resolve(csrfToken);
  csrfPromise ??= fetchCsrfToken()
    .then((token) => {
      csrfToken = token;
      return token;
    })
    .finally(() => {
      csrfPromise = null;
    });
  return csrfPromise;
}

function isSafeMethod(method?: string) {
  return SAFE_METHODS.has((method ?? "get").toLowerCase());
}

function isPublicAuthPath(url?: string) {
  return PUBLIC_AUTH_PATHS.some((path) => url?.includes(path));
}

function announceSessionExpired() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }
}

apiClient.interceptors.request.use(async (config) => {
  if (!isSafeMethod(config.method)) {
    config.headers.set(CSRF_HEADER, await getCsrfToken());
  }
  return config;
});

async function postRefresh(): Promise<boolean> {
  try {
    await axios.post(`${process.env.NEXT_PUBLIC_API_BASE_URL}/auth/refresh/`, null, {
      withCredentials: true,
      headers: { [CSRF_HEADER]: await getCsrfToken() },
    });
    return true;
  } catch {
    return false;
  }
}

/**
 * Refresh tokens are single-use (rotated and blacklisted on every refresh),
 * so two tabs refreshing at once would make the slower one present an
 * already-spent token. The Web Locks API serialises refreshes across tabs:
 * the second tab waits, then refreshes with the cookie the first tab just
 * received.
 */
function refreshSession(): Promise<boolean> {
  if (typeof navigator !== "undefined" && navigator.locks) {
    // lib.dom types the result as Promise<Promise<boolean>>; at runtime the
    // lock resolves with the callback's settled value, which .then() unwraps.
    return navigator.locks.request("greenguard-auth-refresh", postRefresh).then((ok) => ok);
  }
  return postRefresh();
}

type RetryableConfig = InternalAxiosRequestConfig & {
  _retried?: boolean;
  _csrfRetried?: boolean;
};

let refreshPromise: Promise<boolean> | null = null;

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<{ detail?: string }>) => {
    const config = error.config as RetryableConfig | undefined;
    if (!config) throw error;

    // The CSRF cookie can expire or be cleared independently of the
    // in-memory token; fetch a fresh pair once and retry.
    if (
      error.response?.status === 403 &&
      error.response.data?.detail === CSRF_FAILED_MESSAGE &&
      !config._csrfRetried
    ) {
      config._csrfRetried = true;
      csrfToken = null;
      return apiClient(config);
    }

    if (error.response?.status !== 401 || config._retried || isPublicAuthPath(config.url)) {
      throw error;
    }

    config._retried = true;
    refreshPromise ??= refreshSession().finally(() => {
      refreshPromise = null;
    });

    if (!(await refreshPromise)) {
      announceSessionExpired();
      throw error;
    }

    return apiClient(config);
  }
);
