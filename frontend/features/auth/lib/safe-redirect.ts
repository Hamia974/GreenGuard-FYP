export const DEFAULT_AUTHENTICATED_PATH = "/dashboard";
export const REDIRECT_PARAM = "next";

/** Pages a signed-in user is bounced away from -- never a valid destination. */
const AUTH_PAGE_PATHS = ["/login", "/register", "/forgot-password", "/reset-password"];

/**
 * Returns `target` only if it is a same-origin, app-relative path; otherwise
 * the dashboard. Blocks open redirects such as `https://evil.example`,
 * protocol-relative `//evil.example`, the `/\evil.example` backslash trick,
 * `javascript:` URLs and anything with control characters, plus redirect
 * loops back into the auth pages.
 */
export function getSafeRedirect(target: string | null | undefined): string {
  if (!target || !target.startsWith("/") || target.startsWith("//")) {
    return DEFAULT_AUTHENTICATED_PATH;
  }
  if ([...target].some((char) => char === "\\" || char.charCodeAt(0) < 0x20 || char.charCodeAt(0) === 0x7f)) {
    return DEFAULT_AUTHENTICATED_PATH;
  }

  let url: URL;
  try {
    url = new URL(target, "http://greenguard.invalid");
  } catch {
    return DEFAULT_AUTHENTICATED_PATH;
  }
  if (url.origin !== "http://greenguard.invalid") return DEFAULT_AUTHENTICATED_PATH;
  if (AUTH_PAGE_PATHS.some((path) => url.pathname === path || url.pathname.startsWith(`${path}/`))) {
    return DEFAULT_AUTHENTICATED_PATH;
  }
  return `${url.pathname}${url.search}${url.hash}`;
}

/** Reads `?next=` from the current URL. Uses `window.location` rather than
 * `useSearchParams()` so callers don't need a Suspense boundary. */
export function getRedirectFromLocation(): string {
  if (typeof window === "undefined") return DEFAULT_AUTHENTICATED_PATH;
  return getSafeRedirect(new URLSearchParams(window.location.search).get(REDIRECT_PARAM));
}

/** `/login?next=<current path>` for the page the visitor was trying to open. */
export function buildLoginRedirect(): string {
  if (typeof window === "undefined") return "/login";
  const current = `${window.location.pathname}${window.location.search}`;
  const safe = getSafeRedirect(current);
  return safe === DEFAULT_AUTHENTICATED_PATH
    ? "/login"
    : `/login?${REDIRECT_PARAM}=${encodeURIComponent(safe)}`;
}
