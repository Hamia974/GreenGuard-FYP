# GreenGuard Authentication

How browser sessions, CSRF protection, token rotation, password reset and
email verification work. Code: `backend/authentication/` and
`frontend/lib/api-client.ts`.

> **Spec status:** `REST_API_SPEC.md` Section 1 documents the endpoint
> contracts for this design (updated 2026-10-17). This file explains how the
> mechanisms work.

---

## 1. Browser sessions (HttpOnly cookies)

Login and refresh set two HttpOnly cookies; the tokens never appear in a JSON
body, and the frontend never reads, stores or attaches a JWT (nothing is
written to `localStorage`/`sessionStorage`).

| Cookie       | Contents          | Path            | Lifetime                                   |
|--------------|-------------------|-----------------|--------------------------------------------|
| `gg_access`  | JWT access token  | `/api/`         | `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` (10)   |
| `gg_refresh` | JWT refresh token | `/api/v1/auth/` | `JWT_REFRESH_TOKEN_LIFETIME_DAYS` (7), or a browser-session cookie when "Remember me" is unticked |
| `csrftoken`  | Django CSRF secret| `/`             | Django default                             |

All three share `Secure` (`JWT_COOKIE_SECURE`, default `not DEBUG`),
`SameSite` (`JWT_COOKIE_SAMESITE`, default `Lax`) and `Domain`
(`JWT_COOKIE_DOMAIN`, default unset = host-only). Logout and account deletion
clear the JWT cookies with the same path/domain/SameSite they were set with.

The refresh cookie is scoped to `/api/v1/auth/`, so it is sent only to the
auth endpoints, never with ordinary API requests.

### Deployment origins

- **Same site** (`localhost:3000` → `localhost:8000`, or `app.example.com` →
  `api.example.com`): `SameSite=Lax` works. Use the same hostname on both
  sides in development — `127.0.0.1:3000` → `localhost:8000` is cross-site and
  the cookies will not be sent.
- **Cross site** (e.g. two unrelated hosting domains): set
  `JWT_COOKIE_SAMESITE=None`, which requires HTTPS (`JWT_COOKIE_SECURE=True`;
  settings refuse to start otherwise). Browsers that block third-party cookies
  may still refuse them, so a shared parent domain is strongly preferred.

## 2. Authentication class

`authentication.backends.CookieJWTAuthentication` is the only DRF
authentication class:

1. **`Authorization: Bearer <token>`** — checked first, for trusted
   non-browser clients (API tools, a future mobile app, tests). An invalid,
   expired or malformed Bearer token is rejected with 401; it never silently
   falls back to the cookie. Bearer requests are not CSRF-checked, because a
   cross-site page cannot attach that header. The browser frontend never
   sends this header.
2. **`gg_access` cookie** — used when there is no Bearer header (a non-Bearer
   header such as `Basic` from a password-protected staging proxy is
   ignored). Every cookie-authenticated request runs Django's CSRF check.

Expiry, signature, the inactive-user check and user lookup are inherited from
Simple JWT's `JWTAuthentication`. Public auth endpoints set
`authentication_classes = []`, so a stale cookie or header can never break
login, registration or refresh.

## 3. CSRF

- `GET /api/v1/auth/csrf/` sets the `csrftoken` cookie and returns the token
  in `data.csrf_token` (the frontend may be on another origin, where it cannot
  read the cookie).
- The API client keeps that token in memory and sends it as `X-CSRFToken` on
  every unsafe request.
- Checked server-side by Django's `CsrfViewMiddleware` logic (token + Origin
  against `CSRF_TRUSTED_ORIGINS`) on: login (login CSRF), refresh, logout and
  every cookie-authenticated unsafe request. Failure returns
  `403 {"detail": "CSRF verification failed."}`; the client re-fetches the
  token once and retries.
- `CSRF_TRUSTED_ORIGINS` defaults to `CORS_ALLOWED_ORIGINS`.
  `CORS_ALLOWED_ORIGINS` must be explicit (`*` is rejected because
  credentials are allowed).

## 4. Refresh and rotation

`POST /api/v1/auth/refresh/` reads `gg_refresh`, rotates it
(`ROTATE_REFRESH_TOKENS`), blacklists the old one
(`BLACKLIST_AFTER_ROTATION`) and records the new one as outstanding, then
re-sets both cookies. A replayed, revoked, expired or tampered refresh token,
or one belonging to an inactive or deleted user, returns 401 and clears the
cookies. The "Remember me" choice is carried in a `remember_me` claim, so a
rotated cookie keeps the original lifetime.

Frontend (`lib/api-client.ts`): on a 401 from a private endpoint the client
refreshes once and retries the request once (`_retried` guard). Concurrent
401s share one refresh, and the Web Locks API serialises refreshes across tabs
so two tabs never spend the same single-use token. If refresh fails, the
`greenguard:session-expired` event signs the UI out and clears cached queries.

## 5. Revocation

| Event            | Effect |
|------------------|--------|
| Logout           | Blacklists this browser's refresh token; clears cookies. |
| Password change  | Blacklists **all** the user's refresh tokens and immediately invalidates every access token issued before the change, then issues fresh cookies for the current browser so it stays signed in. |
| Password reset   | Blacklists all the user's refresh tokens and immediately invalidates every issued access token. |
| Account deletion | Deletes the user (their tokens can no longer resolve a user); clears cookies. |
| Deactivation     | Access and refresh are both rejected for an inactive user. |

Every token carries a hash of the user's password hash (Simple JWT
`CHECK_REVOKE_TOKEN`, claim `hash_password`). An access or refresh token whose
hash no longer matches is rejected, so **any** password change -- through the
API, the Django admin, `manage.py changepassword` or a hasher upgrade -- revokes
already-issued access tokens at once. This adds no database query: the user row
is already loaded on every authenticated request.

Logout is not covered by that binding. Logout clears the HttpOnly cookie, so
the browser itself loses the access token, but it does **not** revoke an access
token that has already been issued: a copy taken before logout stays valid
until it expires. To keep that window short, the access-token lifetime is 10
minutes (`JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, default `10`). This reduces the
post-logout window; it does not close it. There is deliberately no access-token
denylist or other server-side revocation state. The refresh token is
blacklisted on logout, so a copied access token cannot be renewed.
`authentication/test_sessions.py` pins this behaviour.

## 6. Password reset

`POST /auth/forgot-password/` always returns the same response, whether or not
the email is registered. For an active account it emails
`{FRONTEND_BASE_URL}/reset-password?token=…`. The signed token expires after 1
hour and is bound to a slice of the current password hash, so it stops working
as soon as the password changes (single-use).

## 7. Email verification

Registration emails `{FRONTEND_BASE_URL}/verify-email?token=…`. The signed
token (`EMAIL_VERIFICATION_MAX_AGE_HOURS`, default 48) carries the user ID and
the email address. It is rejected if either no longer matches, so it cannot
verify another account or a changed address. Links are single-use: a link is
accepted only while the account is unverified, and the account is flipped with
a conditional update, so exactly one request succeeds. After that, this link
and any other link issued for the account return `400` like an invalid one.
Signed-in unverified users can request a new link from their profile
(`POST /auth/resend-verification/`, sent only to their own address).
Unverified users can still sign in.

## 8. Email delivery

Configure `EMAIL_BACKEND`/`EMAIL_HOST`/`EMAIL_PORT`/`EMAIL_HOST_USER`/
`EMAIL_HOST_PASSWORD`/`EMAIL_USE_TLS`/`DEFAULT_FROM_EMAIL` and
`FRONTEND_BASE_URL`. Delivery failures are logged at ERROR level on the
`greenguard` logger with the recipient and exception type only — never the
link or token. The API response is unchanged, so failures don't reveal whether
an account exists. With the console backend (development only) the raw link is
also logged at INFO so it can be copied from the terminal.

## 9. Rate limiting

Scoped throttles (per client IP for anonymous requests): `auth`
(`THROTTLE_RATE_AUTH`, 10/min) on register, login, forgot-password,
reset-password, verify-email and resend-verification; `auth_refresh`
(`THROTTLE_RATE_AUTH_REFRESH`, 30/min) on refresh. Throttling is disabled only
under `manage.py test`.

Deployment notes:
- Throttle counters use Django's default cache (`LocMemCache`, per process).
  With several worker processes or instances, configure a shared cache
  (e.g. Redis) for accurate limits.
- Behind a reverse proxy, configure DRF's `NUM_PROXIES` so the client IP
  is read from `X-Forwarded-For`; otherwise every user shares the proxy's IP
  and one limit.

## 10. Frontend redirects

`features/auth/lib/safe-redirect.ts` only accepts same-origin, app-relative
`?next=` paths. It rejects absolute and protocol-relative URLs, backslashes,
control characters and the auth pages themselves (no redirect loops), falling
back to `/dashboard`. Route guards are UX only: every endpoint enforces
authentication and ownership server-side.
