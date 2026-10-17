# GreenGuard REST API Specification

Version: 2.1

Status: Final

> **2026-09-18:** Section 8A and the "AI Module 2" internal contract were reconciled with the Stress Module's actual delivered v1.2.0 contract (`ai/Stress_Module`, real FastAPI microservice on `STRESS_MODULE_URL`, default port 8002) — this document had not been updated since the v2.0 placeholder even though the AI team's own `INTEGRATION_GUIDE.md` already described itself as reconciled against a "v2.1". Changes: `ph_value`/`soil_moisture_pct`/`light_intensity_lux` are now required (were documented optional); all 15 catalog crops are trained-and-supported (was 8, with 7 "pending retrain"); the response gained `module2a.input_typicality`, `module2a.model_version`, `recommendation_notes`, and top-level `module2a_model_version`. No change to the public `/api/v1/module2/analyze/` endpoint path, request `farm_id`/categorical fields, or external error contract.

> **2026-10-17:** Section 1 (Authentication) and the authentication notes in the general sections and Sections 10, 14, 19 and 26 were updated to match the implemented cookie-based design (`docs/AUTHENTICATION.md`): login and refresh set HttpOnly cookies and no longer return `access_token`/`refresh_token` in the body; refresh reads the refresh cookie instead of a `refresh_token` body field; CSRF is required on login, refresh, logout and cookie-authenticated unsafe requests; logout no longer requires an access token; `GET /auth/csrf/`, `POST /auth/verify-email/` and `POST /auth/resend-verification/` are now documented; the login `user` object gained `is_verified` and the request gained optional `remember_me`. All other endpoints are unchanged.

Project: GreenGuard

Backend Framework:
Django REST Framework

Frontend:
Next.js

Database:
PostgreSQL

Authentication:
JWT Authentication

API Style:
RESTful APIs

Response Format:
JSON

Communication:
HTTPS

Author:
GreenGuard Development Team

---

# Document Purpose

This document defines all REST APIs exposed by the GreenGuard backend.

It serves as the single source of truth for:

• Frontend Development

• Backend Development

• AI Integration

• Testing

• Deployment

• Future Maintenance

All developers must follow this specification strictly.

---

# Architecture Overview

GreenGuard follows a Layered Client–Server Architecture.

```

Frontend (Next.js)

↓

Django REST API

↓

Business Logic Layer

↓

AI Integration Layer

↓

Module 1 — Disease Detection (live service)

Module 2 — Soil & Nutrient Health (live service; standalone endpoint — see Section 8A)

Module 3 — Weather Risk (local service, Open-Meteo)

↓

Module 4 — Integrated Analysis Report (application layer — not an AI model; shows the Module 1, 2 and 3 results side by side)

↓

PostgreSQL Database

```

The frontend communicates ONLY with Django.

The frontend NEVER communicates directly with AI modules.

The backend orchestrates all AI services.

---

# API Base URL

Development

```

http://localhost:8000/api/v1/

```

Production

```

https://api.greenguard.com/api/v1/

```

---

# API Design Principles

The API follows REST principles.

Every endpoint must

• Use HTTPS

• Return JSON

• Be stateless

• Validate all requests

• Return appropriate HTTP status codes

• Require JWT authentication unless marked public

• Follow consistent naming conventions

---

# Request Headers

Content-Type

```

application/json

```

Multipart Upload

```

multipart/form-data

```

Authorization

Browsers authenticate with the HttpOnly `gg_access` cookie and send `X-CSRFToken: <CSRF_TOKEN>` on unsafe requests. Non-browser clients may instead send:

```

Authorization: Bearer <JWT_TOKEN>

```

See Section 1.

---

# Standard Success Response

```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": {}
}
```

---

# Standard Validation Error

```json
{
  "success": false,
  "message": "Validation failed.",
  "errors": {}
}
```

---

# Standard Server Error

```json
{
  "success": false,
  "message": "Internal Server Error."
}
```

---

# HTTP Status Codes

200 OK

201 Created

204 No Content

400 Bad Request

401 Unauthorized

403 Forbidden

404 Not Found

409 Conflict

422 Validation Error

500 Internal Server Error

---

# API Versioning

Current Version

/api/v1/

Future Versions

/api/v2/

/api/v3/

Older versions must remain backward compatible whenever possible.

---

# Authentication Method

GreenGuard uses JWT Authentication, delivered to browsers as HttpOnly cookies (see Section 1).

Authentication flow

Register

↓

Get CSRF Token

↓

Login (server sets HttpOnly cookies)

↓

Access Protected APIs (cookies sent automatically)

↓

Refresh on 401 (tokens rotated)

---

# User Roles

Farmer

Default application user.

Admin

Manages users, analytics, AI monitoring, and system settings.

Only Admin can access Admin APIs.

---

# API Categories

1. Authentication APIs

2. Farm APIs

3. User APIs

4. Dashboard APIs

5. Prediction APIs

6. History APIs

7. Notification APIs

8. Recommendation APIs

9. Admin APIs

10. Module 2 — Soil & Nutrient Health APIs

11. Internal AI Service Contracts

---

# General API Rules

• Every endpoint must validate input.

• Never expose database IDs directly when unnecessary.

• Never expose internal AI implementation.

• Frontend must never call AI services directly.

• Backend must never modify AI predictions.

• Backend only validates, stores, and forwards AI responses.

• All timestamps must be returned in ISO 8601 format.

• UUID should be used for major entities.

• Every prediction must be stored before returning the response.

• AI modules must remain independent.

• GreenGuard has three independent AI modules — Module 1 (Disease Detection), Module 2 (Soil & Nutrient Health) and Module 3 (Weather Risk). Module 4 is the application-level Integrated Analysis Report: it stores and displays the three module results together and runs no model of its own. There is no ANN Fusion model, no Fusion service and no combined "final diagnosis" — each module's result stays separate and traceable to its source (see "Module 4" in Section 9).

# 1. Authentication APIs

GreenGuard uses JWT (JSON Web Token) authentication. Browsers receive the tokens as **HttpOnly cookies**: login and refresh never return a token in the JSON body, and the frontend never reads, stores or attaches a JWT (nothing is written to `localStorage` or `sessionStorage`). Implementation details: `docs/AUTHENTICATION.md`.

Authentication Flow

Get CSRF Token (GET /api/v1/auth/csrf/)

↓

User Login (sets the `gg_access` and `gg_refresh` cookies)

↓

Authenticated Requests (cookies sent automatically; `X-CSRFToken` header on unsafe methods)

↓

Refresh on 401 (rotates the refresh token, re-sets both cookies)

↓

Logout (blacklists the refresh token, clears both cookies)

---

## Session Cookies

| Cookie | Contents | Path | Lifetime |
|--------|----------|------|----------|
| `gg_access` | JWT access token | `/api/` | `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` (default 10 minutes) |
| `gg_refresh` | JWT refresh token | `/api/v1/auth/` | `JWT_REFRESH_TOKEN_LIFETIME_DAYS` (default 7 days), or a browser-session cookie when `remember_me` is `false` |
| `csrftoken` | Django CSRF secret | `/` | Django default |

All three are set with the same `Secure` (default: on whenever `DEBUG=False`), `SameSite` (default `Lax`) and `Domain` (default: host-only) settings. Both JWT cookies are `HttpOnly`. The refresh cookie is only sent to the auth endpoints.

Browser clients must send requests with credentials (Axios `withCredentials: true`, or `fetch` with `credentials: "include"`).

---

## Authenticating Requests

Browser clients

• Authenticated by the `gg_access` cookie.

• Every unsafe request (POST, PUT, PATCH, DELETE) authenticated by the cookie must carry the CSRF token in the `X-CSRFToken` header.

Non-browser clients (API tools, tests, a future mobile app)

• May send `Authorization: Bearer <ACCESS_TOKEN>` instead. The header is checked before the cookie.

• An invalid, expired or malformed Bearer token returns 401; it never falls back to the cookie.

• Bearer requests are not CSRF-checked, because a cross-site page cannot attach that header.

• The token is taken from the `Set-Cookie` headers of login or refresh; it is never in a response body.

Where endpoint sections later in this document list `Authorization: Bearer <JWT_TOKEN>`, either method of authenticating applies.

Unauthenticated or invalid-token requests to a protected endpoint return 401 with Django REST Framework's standard error body:

```json
{
    "detail": "Authentication credentials were not provided."
}
```

---

## CSRF Protection

Get a token from `GET /api/v1/auth/csrf/` and send it as the `X-CSRFToken` header. The request's `Origin` must also be listed in `CSRF_TRUSTED_ORIGINS` (defaults to `CORS_ALLOWED_ORIGINS`).

CSRF is checked on

• Login, refresh and logout (always, even though they need no access token).

• Every unsafe request authenticated by the `gg_access` cookie, including change-password and resend-verification.

CSRF is not checked on

• `GET` requests, Bearer-authenticated requests, and the public register, forgot-password, reset-password and verify-email endpoints (they act on no existing session).

CSRF failure

Status Code

403 Forbidden

```json
{
    "detail": "CSRF verification failed."
}
```

---

## Authentication Endpoints

| Method | Endpoint | Authentication | CSRF | Description |
|--------|----------|----------------|------|-------------|
| GET | /api/v1/auth/csrf/ | No | No | Issue CSRF token |
| POST | /api/v1/auth/register/ | No | No | Register new user |
| POST | /api/v1/auth/login/ | No | Yes | User Login (sets cookies) |
| POST | /api/v1/auth/logout/ | No (works with an expired session) | Yes | Logout User |
| POST | /api/v1/auth/refresh/ | Refresh cookie | Yes | Rotate tokens |
| POST | /api/v1/auth/forgot-password/ | No | No | Request Password Reset |
| POST | /api/v1/auth/reset-password/ | No | No | Reset Password |
| POST | /api/v1/auth/change-password/ | Yes | Yes (cookie) | Change Current Password |
| POST | /api/v1/auth/verify-email/ | No | No | Verify email address |
| POST | /api/v1/auth/resend-verification/ | Yes | Yes (cookie) | Resend verification email |

---

# Get CSRF Token

Endpoint

GET

/api/v1/auth/csrf/

Authentication

Not Required

Description

Sets the `csrftoken` cookie and returns the matching token in the body, because the frontend may run on another origin where it cannot read the cookie.

---

Success Response

Status Code

200 OK

```json
{
    "success": true,
    "message": "CSRF token issued.",
    "data": {
        "csrf_token": "<CSRF_TOKEN>"
    }
}
```

---

# Register User

Endpoint

POST

/api/v1/auth/register/

Authentication

Not Required

Description

Registers a new GreenGuard user with the Farmer role and emails an email-verification link (see Verify Email). Registration does not sign the user in and sets no cookies.

Request Headers

Content-Type

application/json

---

Request Body

```json
{
    "full_name": "Muhammad Ali",
    "email": "ali@example.com",
    "password": "StrongPassword123",
    "confirm_password": "StrongPassword123"
}
```

Validation Rules

• Full Name Required

• Email Required

• Email Must Be Unique (case-insensitive; stored lower-case)

• Valid Email Format

• Password Minimum 8 Characters, and must pass Django's password validators (not too similar to the user's details, not a common password, not entirely numeric)

• Passwords Must Match

• A client-supplied role is ignored; new users are always Farmers

---

Success Response

Status Code

201 Created

```json
{
    "success": true,
    "message": "User registered successfully.",
    "data": {
        "user_id": "3f6c2a9e-8d1b-4c7a-9e2f-1a2b3c4d5e6f",
        "full_name": "Muhammad Ali",
        "email": "ali@example.com"
    }
}
```

---

Validation Error

Status Code

422 Validation Error

```json
{
    "success": false,
    "message": "Validation failed.",
    "errors": {
        "email": [
            "Email already exists."
        ]
    }
}
```

---

# User Login

Endpoint

POST

/api/v1/auth/login/

Authentication

Not Required

CSRF

Required (`X-CSRFToken`)

Description

Authenticates user credentials and sets the `gg_access` and `gg_refresh` HttpOnly cookies. The tokens are not returned in the body. A stale or invalid access cookie never blocks login. Unverified users can sign in.

Request Body

```json
{
    "email": "ali@example.com",
    "password": "StrongPassword123",
    "remember_me": true
}
```

`remember_me` is optional (default `true`). When `false`, the refresh cookie is a browser-session cookie, so closing the browser ends the session; the choice is kept across refreshes.

---

Success Response

Status Code

200 OK

Response Headers

`Set-Cookie: gg_access=…; HttpOnly; Path=/api/` and `Set-Cookie: gg_refresh=…; HttpOnly; Path=/api/v1/auth/`

```json
{
    "success": true,
    "message": "Login successful.",
    "data": {
        "user": {
            "user_id": "3f6c2a9e-8d1b-4c7a-9e2f-1a2b3c4d5e6f",
            "full_name": "Muhammad Ali",
            "email": "ali@example.com",
            "role": "Farmer",
            "is_verified": false
        }
    }
}
```

---

Invalid Credentials

Status Code

401 Unauthorized

Returned for a wrong email or password, an inactive account, or a malformed request body. The message never reveals which.

```json
{
    "success": false,
    "message": "Invalid email or password."
}
```

Other errors: 403 CSRF failure, 429 rate limit.

---

# Logout

Endpoint

POST

/api/v1/auth/logout/

Authentication

Not Required (works even when the access token has expired)

CSRF

Required (`X-CSRFToken`)

Description

Blacklists this browser's refresh token (if present) and clears both JWT cookies (`Max-Age=0`). Always returns 200.

Logout does **not** revoke an access token that was already issued. The browser loses it when the cookie is cleared, but a copy taken before logout stays valid until it expires (at most `JWT_ACCESS_TOKEN_LIFETIME_MINUTES`, default 10 minutes). It cannot be renewed, because the refresh token is blacklisted.

Request Body

None

---

Success Response

Status Code

200 OK

```json
{
    "success": true,
    "message": "Logout successful."
}
```

---

# Refresh Token

Endpoint

POST

/api/v1/auth/refresh/

Authentication

Refresh cookie (`gg_refresh`), sent automatically by the browser

CSRF

Required (`X-CSRFToken`)

Description

Rotates the refresh token: the old one is blacklisted, so a replayed token is rejected. Re-sets both cookies with a new access and refresh token, keeping the original `remember_me` choice. The frontend calls this once after a 401 from a protected endpoint, then retries the request once.

Request Body

None

---

Success Response

Status Code

200 OK

```json
{
    "success": true,
    "message": "Token refreshed successfully."
}
```

---

Invalid Refresh Token

Status Code

401 Unauthorized

Returned, and both cookies cleared, when the refresh cookie is missing, expired, tampered, already used or blacklisted, issued before the user's last password change, or belongs to an inactive or deleted user.

```json
{
    "success": false,
    "message": "Invalid or expired refresh token."
}
```

---

# Forgot Password

Endpoint

POST

/api/v1/auth/forgot-password/

Authentication

Not Required

Description

For an active account, emails a link to `{FRONTEND_BASE_URL}/reset-password?token=…`. The link expires after 1 hour and can be used once. The response is identical whether or not the email is registered.

Request Body

```json
{
    "email": "ali@example.com"
}
```

---

Success Response

Status Code

200 OK

```json
{
    "success": true,
    "message": "Password reset instructions sent to your email."
}
```

Other errors: 422 invalid email format, 429 rate limit.

---

# Reset Password

Endpoint

POST

/api/v1/auth/reset-password/

Authentication

Not Required

Description

Sets a new password from a reset-link token. On success every refresh token for the account is blacklisted and every issued access token stops working immediately, signing out all devices. The user is not signed in; they log in with the new password.

Request Body

```json
{
    "token": "RESET_TOKEN",
    "new_password": "NewStrongPassword123",
    "confirm_password": "NewStrongPassword123"
}
```

---

Success Response

Status Code

200 OK

```json
{
    "success": true,
    "message": "Password reset successful."
}
```

---

Invalid Token

Status Code

400 Bad Request

Returned for an expired, tampered or already-used token, or an inactive account.

```json
{
    "success": false,
    "message": "Reset link is invalid or has expired."
}
```

Other errors: 422 validation error (password rules, passwords must match), 429 rate limit.

---

# Change Password

Endpoint

POST

/api/v1/auth/change-password/

Authentication

Required

CSRF

Required for cookie-authenticated requests

Description

Changes the password of the signed-in user. Every refresh token for the account is blacklisted and every access token issued before the change stops working immediately, signing out all other devices. The response sets fresh cookies for the current browser, so it stays signed in.

Request Body

```json
{
    "current_password": "OldPassword123",
    "new_password": "NewPassword123",
    "confirm_password": "NewPassword123"
}
```

---

Success Response

Status Code

200 OK

```json
{
    "success": true,
    "message": "Password changed successfully."
}
```

---

Validation Error

Status Code

422 Validation Error

```json
{
    "success": false,
    "message": "Validation failed.",
    "errors": {
        "current_password": [
            "Current password is incorrect."
        ]
    }
}
```

Other errors: 401 not authenticated, 403 CSRF failure.

---

# Verify Email

Endpoint

POST

/api/v1/auth/verify-email/

Authentication

Not Required

Description

Consumes the token from the link emailed at registration (`{FRONTEND_BASE_URL}/verify-email?token=…`). The token expires after `EMAIL_VERIFICATION_MAX_AGE_HOURS` (default 48) and is bound to the account and its email address. Links are single-use: once the account is verified, this link and every other link issued for it is rejected.

Request Body

```json
{
    "token": "VERIFICATION_TOKEN"
}
```

---

Success Response

Status Code

200 OK

```json
{
    "success": true,
    "message": "Email verified successfully."
}
```

---

Invalid Token

Status Code

400 Bad Request

```json
{
    "success": false,
    "message": "Verification link is invalid or has expired."
}
```

Other errors: 422 missing token, 429 rate limit.

---

# Resend Verification Email

Endpoint

POST

/api/v1/auth/resend-verification/

Authentication

Required

CSRF

Required for cookie-authenticated requests

Description

Sends a new verification link to the signed-in user's own address. Does nothing if the address is already verified.

Request Body

None

---

Success Response

Status Code

200 OK

```json
{
    "success": true,
    "message": "Verification email sent."
}
```

When already verified, the message is `"Email is already verified."`.

---

# Authentication Rules

• JWT Authentication, delivered to browsers as HttpOnly cookies

• Tokens are never returned in a response body or stored by the frontend

• Bearer header accepted for non-browser clients only

• CSRF token required on login, refresh, logout and every cookie-authenticated unsafe request

• Passwords Stored Using Secure Hashing

• Access token lifetime: 10 minutes by default (`JWT_ACCESS_TOKEN_LIFETIME_MINUTES`)

• Refresh tokens rotate on every refresh; the old token is blacklisted

• Logout blacklists the refresh token but cannot revoke an already-issued access token before it expires

• Password change and reset revoke every issued access and refresh token immediately

• Admin APIs Accessible Only To Admin Users

• Unauthorized Requests Return HTTP 401

• Rate limits: 10 requests per minute for register, login, forgot-password, reset-password, verify-email and resend-verification; 30 per minute for refresh. Exceeding a limit returns 429 with a `detail` message.

---

# Protected APIs

The following API groups require authentication.

• Farm APIs

• User APIs

• Dashboard APIs

• Prediction APIs

• History APIs

• Notification APIs

• Recommendation APIs

• Admin APIs

• Module 2 — Soil & Nutrient Health APIs

---

# Authentication Sequence

Get CSRF Token

↓

Login

↓

Browser Receives HttpOnly Cookies

↓

Access Protected APIs (cookies + `X-CSRFToken`)

↓

Refresh On 401

↓

Logout

↓

Session Ends

# 2. Farm APIs

Farm APIs allow authenticated users to manage the farms they own.

Each farm stores geographic coordinates (latitude and longitude) used by the Weather Module to retrieve weather information and, later, by Prediction APIs to associate an analysis with a farm.

A farm belongs to exactly one user. Users may only view, create, update, or delete their own farms.

All Farm APIs require JWT Authentication.

---

## Farm Endpoints

| Method | Endpoint | Authentication | Description |
|---------|-------------------------------|----------------|-----------------------------|
| GET | /api/v1/farms/ | Required | Get All Farms |
| POST | /api/v1/farms/ | Required | Create Farm |
| GET | /api/v1/farms/{farm_id}/ | Required | Get Farm Details |
| PUT | /api/v1/farms/{farm_id}/ | Required | Update Farm |
| DELETE | /api/v1/farms/{farm_id}/ | Required | Delete Farm |
| POST | /api/v1/farms/geocode/ | Required | Find Farm Location (address → coordinates) |

---

# Get All Farms

Endpoint

GET

/api/v1/farms/

Authentication

Required

Authorization

Bearer <JWT_TOKEN>

Description

Returns all farms owned by the authenticated user, most recently created first.

---

Success Response

```json
{
    "success": true,
    "message": "Farms retrieved successfully.",
    "data": [
        {
            "farm_id": "8f14e45f-ceea-4c9a-b3f4-000000000001",
            "farm_name": "Green Valley Farm",
            "address": "123 Farm Road, Lahore, Punjab",
            "latitude": 31.5204,
            "longitude": 74.3587,
            "created_at": "2026-07-31T10:00:00Z",
            "updated_at": "2026-07-31T10:00:00Z"
        }
    ]
}
```

---

# Create Farm

Endpoint

POST

/api/v1/farms/

Authentication

Required

Request Headers

Content-Type

application/json

---

Request Body

```json
{
    "farm_name": "Green Valley Farm",
    "address": "123 Farm Road, Lahore, Punjab",
    "latitude": 31.5204,
    "longitude": 74.3587
}
```

Validation Rules

• Farm Name Required

• Farm Name Maximum 100 Characters

• Address Required

• Latitude Required

• Latitude Range -90 to +90

• Longitude Required

• Longitude Range -180 to +180

---

Success Response

Status Code

201 Created

```json
{
    "success": true,
    "message": "Farm created successfully.",
    "data": {
        "farm_id": "8f14e45f-ceea-4c9a-b3f4-000000000001",
        "farm_name": "Green Valley Farm",
        "address": "123 Farm Road, Lahore, Punjab",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "created_at": "2026-07-31T10:00:00Z",
        "updated_at": "2026-07-31T10:00:00Z"
    }
}
```

---

Validation Error

Status Code

422 Validation Error

```json
{
    "success": false,
    "message": "Validation failed.",
    "errors": {
        "latitude": [
            "Latitude must be between -90 and 90."
        ]
    }
}
```

---

# Get Farm Details

Endpoint

GET

/api/v1/farms/{farm_id}/

Authentication

Required

Description

Returns details for a single farm owned by the authenticated user.

---

Success Response

```json
{
    "success": true,
    "message": "Farm retrieved successfully.",
    "data": {
        "farm_id": "8f14e45f-ceea-4c9a-b3f4-000000000001",
        "farm_name": "Green Valley Farm",
        "address": "123 Farm Road, Lahore, Punjab",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "created_at": "2026-07-31T10:00:00Z",
        "updated_at": "2026-07-31T10:00:00Z"
    }
}
```

---

Error Response

Status Code

404 Not Found

```json
{
    "success": false,
    "message": "Farm not found."
}
```

---

# Update Farm

Endpoint

PUT

/api/v1/farms/{farm_id}/

Authentication

Required

Request Headers

Content-Type

application/json

---

Request Body

```json
{
    "farm_name": "Green Valley Farm",
    "address": "123 Farm Road, Lahore, Punjab",
    "latitude": 31.5204,
    "longitude": 74.3587
}
```

Validation Rules

Same as Create Farm.

---

Success Response

```json
{
    "success": true,
    "message": "Farm updated successfully.",
    "data": {
        "farm_id": "8f14e45f-ceea-4c9a-b3f4-000000000001",
        "farm_name": "Green Valley Farm",
        "address": "123 Farm Road, Lahore, Punjab",
        "latitude": 31.5204,
        "longitude": 74.3587,
        "created_at": "2026-07-31T10:00:00Z",
        "updated_at": "2026-07-31T10:05:00Z"
    }
}
```

---

# Delete Farm

Endpoint

DELETE

/api/v1/farms/{farm_id}/

Authentication

Required

Description

Permanently deletes a farm owned by the authenticated user.

---

Success Response

```json
{
    "success": true,
    "message": "Farm deleted successfully."
}
```

---

# Find Farm Location (Geocode Address)

Endpoint

POST

/api/v1/farms/geocode/

Authentication

Required

Description

Converts the free-text farm address typed in the Farm form (village, tehsil, district, landmark...) into candidate coordinates, so farmers never type latitude/longitude. Nothing is saved: the farmer confirms one candidate in the UI and the form then submits its `latitude`/`longitude` through the unchanged Create Farm / Update Farm endpoints.

The backend calls the configured provider (`GEOCODING_PROVIDER`: `open_meteo` or `google`, see backend/.env.example); the frontend never calls a geocoding provider directly, so provider keys stay server-side. Results are restricted to `GEOCODING_COUNTRY_CODE` (default `PK`), country/province-level matches are dropped as too vague, and results are cached for 24 hours. Rate limited per user (`THROTTLE_RATE_GEOCODE`, default 20/min).

---

Request Body

```json
{
    "address": "Village Baghbanpura, Lahore, Punjab, Pakistan",
    "language": "en"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| address | string | Yes | Max 500 characters. |
| language | string | No | `en` (default) or `ur` — language for result labels, when the provider has it. |

---

Success Response (200)

`results` holds up to 5 candidates, best match first. An empty list means no usable location was found (message: "No location found for this address.").

```json
{
    "success": true,
    "message": "Locations found.",
    "data": {
        "results": [
            {
                "label": "Baghbanpura, Lahore District, Punjab, Pakistan",
                "latitude": 31.58648,
                "longitude": 74.37743
            }
        ]
    }
}
```

---

Error Responses

422 — standard validation error (e.g. empty `address`).

503 — provider unreachable, misconfigured or failing:

```json
{
    "success": false,
    "message": "Location service is temporarily unavailable."
}
```

---

# Farm Rules

• A farm must belong to exactly one user.

• Users may only view, update, or delete their own farms.

• Latitude and longitude are required and are used by the Weather Module.

• In the Farm form, coordinates come only from Find Location (POST /api/v1/farms/geocode/, confirmed by the farmer) or the device's current location — never typed manually. Coordinates found for an address stop counting as soon as that address is edited.

• Selecting the "active" farm (the farm currently in context for the dashboard and predictions) is a frontend-only concept and is not persisted by the backend.

---

# 3. Prediction APIs

The Prediction Module is the core functionality of GreenGuard.

It is responsible for receiving the leaf image, collecting the result of each independent AI module, storing them together as one analysis record, and returning that integrated report (Module 4).

The frontend communicates only with the Prediction API.

The backend is responsible for invoking all AI modules internally.

The frontend never communicates directly with AI models.

---

# Prediction Workflow

User Uploads Image

↓

Frontend (Next.js)

↓

POST /api/v1/predictions/analyze/

↓

Django Backend

↓

Validate Request

↓

Store Uploaded Image

↓

Call Module 1 — Disease Detection (live service)

↓

Include Farm's Latest Module 2 (Soil & Nutrient Health) Result — not invoked live; retrieved from the persisted Module2Analysis record

↓

Call Module 3 — Weather Risk

↓

Module 4 — Store the three results together as one Prediction (Integrated Analysis Report)

↓

Return the Saved Report

---

# Prediction Endpoints

| Method | Endpoint | Authentication | Description |
|----------|------------------------------------|----------------|-----------------------------|
| POST | /api/v1/predictions/analyze/ | Required | Analyze Plant Health |
| GET | /api/v1/predictions/ | Required | Get All Predictions |
| GET | /api/v1/predictions/{id}/ | Required | Get Prediction Details |
| DELETE | /api/v1/predictions/{id}/ | Required | Delete Prediction |

---

# Analyze Plant

Endpoint

POST

/api/v1/predictions/analyze/

Authentication

Required

Authorization

Bearer <JWT_TOKEN>

Content Type

multipart/form-data

---

# Request Parameters

| Parameter | Type | Required | Description |
|------------|----------|-----------|-------------------------------|
| image | File | Yes | Leaf Image |
| farm_id | UUID | Yes | Farm this prediction belongs to. The backend resolves latitude/longitude from this farm's stored record before calling the Weather Risk Module (same pattern as GET /api/v1/dashboard/weather/). Must belong to the authenticated user. |
| crop | Text | No | Crop shown in the photo, forwarded to Module 1 unchanged (`wheat`, `rice`, `cotton`, `maize`, `sugarcane`, `tomato`, `potato`; case-insensitive — Module 1 is the sole judge of valid values, see `ai/API_CONTRACT.md`). Omit when unknown; Module 1 then detects the crop itself. |

> **Note:** This endpoint no longer accepts raw soil-sensor parameters (nitrogen, phosphorus, potassium, ph, ec, organic_carbon, zinc, iron, copper, manganese, boron, sulfur). Those fields belonged to an earlier, unfinalized placeholder for "Module 2." The finalized Module 2 (Soil & Nutrient Health Check) is now its own standalone endpoint — see Section 10 — with a farmer-questionnaire input shape, not raw sensor numbers.

---

# Backend Processing

Step 1

Validate Request

↓

Step 2

Send Image (plus `crop` if given, and `farm_id`) to Module 1 — Disease Detection

↓

Step 3

Retrieve Farm's Latest Persisted Module 2 (Soil & Nutrient Health) Result — not invoked live

↓

Step 4

Resolve Farm Coordinates and Send to Module 3 — Weather Risk

↓

Step 5

Store One Prediction Containing All Three Results (Module 4 — Integrated Analysis Report)

↓

Step 6

Return the Saved Report

The Prediction row is created only after every step succeeds — either one complete record is written or nothing is persisted.

---

# Module 1 — Disease Detection

Internal Service (live, deployed)

The backend sends the uploaded leaf image to the live Disease Detection service (`POST {DISEASE_MODULE_URL}/v1/predict`, see "AI Module 1" in Section 9 and `ai/API_CONTRACT.md`).

Output

Disease prediction (`prediction`) with confidence, crop and health status, plus the `top3` shortlist, `warnings` and `message`.

When the model is not confident it returns `status: "uncertain"` with `prediction: null`; `top3` is still populated. This is a normal result, not an error, and is stored as-is.

Module 1 does not detect nutrient deficiencies or insects. Soil and nutrient health comes only from Module 2, and no GreenGuard module detects insects.

The backend must never modify any fields returned by this module.

---

# Module 2 — Soil & Nutrient Health

The farm's latest persisted Soil & Nutrient Health result (Section 8A), stored verbatim, or `null` when the farm has never run one. Module 2 needs the farmer's questionnaire, which Quick Scan does not collect, so it is never called live here.

---

# Module 3 — Weather Risk

Internal Service (local)

The backend sends the farm's location.

Input

Latitude

Longitude

Output

Temperature

Humidity

Rainfall

Wind Speed

Heat Stress Risk

Fungal Disease Risk

Drought Risk

Weather data is retrieved using the Open-Meteo API, via the ai/Weather_Module Module 3 microservice (see Section 9 for the exact contract).

The backend stores the returned data without modification.

---

# Module 4 — Integrated Analysis Report

Module 4 is not an AI model and not a service. It is this endpoint's application-level result: one Prediction record whose `prediction_report` holds the three module results side by side.

```json
{
  "module1": { "...": "exact Module 1 (Disease Detection) response" },
  "module2": { "...": "farm's latest Module 2 result, verbatim — or null" },
  "module3": { "...": "exact Module 3 (Weather Risk) response" }
}
```

The backend never combines these results. It does not produce a final diagnosis, a combined confidence score, or recommendations of its own.

---

# Success Response

```json
{
  "success": true,
  "message": "Prediction completed successfully.",
  "data": {
    "prediction_id": "6f1c...",
    "farm_id": "a91b...",
    "uploaded_image": "http://localhost:8000/media/predictions/....jpg",
    "final_diagnosis": null,
    "confidence_score": null,
    "prediction_report": {
      "module1": { "status": "ok", "prediction": { "display_name": "Yellow Rust", "confidence": 0.8812, "...": "..." }, "top3": ["..."], "...": "..." },
      "module2": null,
      "module3": { "weather": { "...": "..." }, "risk_assessment": { "...": "..." }, "...": "..." }
    },
    "recommendation_summary": null,
    "prediction_status": "completed",
    "created_at": "2026-10-03T10:15:00Z",
    "updated_at": "2026-10-03T10:15:00Z"
  }
}
```

`data` has the same shape as GET /api/v1/predictions/{prediction_id}/.

`final_diagnosis`, `confidence_score` and `recommendation_summary` are legacy fields from the retired ANN Fusion design. They are always `null` for new analyses (no module produces them) and are kept only so older records stay readable.

The backend must not rename, remove or recompute any field inside `module1`, `module2` or `module3`.

---

# Validation Rules

Image

Required

JPEG

PNG

JPG

Maximum Size

10 MB

Farm ID

Required

Must belong to the authenticated user

Missing Values

Return HTTP 422

---

# Error Responses

400

Invalid Request

401

Unauthorized

404

Farm Not Found (farm_id does not belong to the authenticated user)

404

Prediction Not Found

422

Validation Failed

500

Prediction Failed

503

Disease Detection or Weather service temporarily unavailable

Module 1's own documented error codes (`ai/API_CONTRACT.md`) are translated into friendly messages exactly as for POST /api/v1/module1/analyze/ (Section 8B).

---

# Get Prediction History

Endpoint

GET

/api/v1/predictions/

Authentication

Required

Description

Returns all predictions created by the authenticated user.

Supports

Search

Pagination

Filtering

Sorting

---

# Get Prediction Details

Endpoint

GET

/api/v1/predictions/{prediction_id}/

Authentication

Required

Description

Returns the complete analysis report: the Module 1, Module 2 and Module 3 results in `prediction_report`, unmodified.

---

# Delete Prediction

Endpoint

DELETE

/api/v1/predictions/{prediction_id}/

Authentication

Required

Description

Deletes a prediction record belonging to the authenticated user.

Only the owner of the prediction may delete it.

Admin users may delete any prediction.

---

# Prediction Storage

Every successful prediction must be stored.

Stored Information

User

Uploaded Image

Module 1 (Disease Detection) Output

Module 2 (Soil & Nutrient Health) Output, or null

Module 3 (Weather Risk) Output

Timestamp

Prediction Status

# 4. User APIs

User APIs manage user profile information and account settings.

All User APIs require JWT Authentication.

---

## User Endpoints

| Method | Endpoint | Authentication | Description |
|---------|-------------------------|----------------|-----------------------------|
| GET | /api/v1/profile/ | Required | Get User Profile |
| PUT | /api/v1/profile/ | Required | Update User Profile |
| DELETE | /api/v1/profile/ | Required | Delete User Account |

---

# Get User Profile

Endpoint

GET

/api/v1/profile/

Authentication

Required

Authorization

Bearer <JWT_TOKEN>

Description

Returns the authenticated user's profile information.

---

Success Response

```json
{
    "success": true,
    "message": "Profile retrieved successfully.",
    "data": {
        "user_id": "usr_001",
        "full_name": "Muhammad Ali",
        "email": "ali@example.com",
        "role": "Farmer",
        "profile_image": "https://...",
        "created_at": "2026-07-31T10:00:00Z"
    }
}
```

---

# Update Profile

Endpoint

PUT

/api/v1/profile/

Authentication

Required

Content Type

multipart/form-data

---

Request Body

| Field | Type | Required |
|---------|----------|----------|
| full_name | String | Yes |
| profile_image | File | No |

---

Success Response

```json
{
    "success": true,
    "message": "Profile updated successfully."
}
```

---

# Delete Account

Endpoint

DELETE

/api/v1/profile/

Authentication

Required

Content Type

application/json

Description

Permanently deletes the authenticated user's account.

Associated prediction history may be anonymized or removed according to system policy.

The current password must be re-entered and is verified server-side before deletion proceeds.

---

Request Body

| Field | Type | Required |
|---------|----------|----------|
| current_password | String | Yes |

---

Success Response

```json
{
    "success": true,
    "message": "Account deleted successfully."
}
```

---

Error Response (incorrect or missing password)

```json
{
    "success": false,
    "message": "Validation failed.",
    "errors": {
        "current_password": ["Current password is incorrect."]
    }
}
```

---

# 5. Dashboard APIs

The Dashboard provides a summarized overview of the user's farm activities and latest AI analyses.

The frontend should load the dashboard using a single API call.

---

## Dashboard Endpoints

| Method | Endpoint | Authentication | Description |
|---------|------------------------------|----------------|----------------------------|
| GET | /api/v1/dashboard/ | Required | Dashboard Overview |
| GET | /api/v1/dashboard/weather/ | Required | Weather Summary (flat, dashboard-card shape) |
| GET | /api/v1/weather/current/ | Required | Full Weather Report (Section 5A — the real Module 3 contract, for the Weather page) |
| GET | /api/v1/dashboard/recent-predictions/ | Required | Recent Predictions |
| GET | /api/v1/dashboard/recommendations/ | Required | Latest Recommendations |

---

# Dashboard Overview

Endpoint

GET

/api/v1/dashboard/

Authentication

Required

Description

Returns all information required for the Home Dashboard.

---

Dashboard Includes

• Welcome Banner

• User Information

• Quick Scan Shortcut

• Recent Predictions

• Weather Summary

• Recommendation Summary

• Disease Statistics

• Prediction Statistics

• Notification Count

---

Success Response

```json
{
    "success": true,
    "message": "Dashboard loaded successfully.",
    "data": {
        "welcome_message": "Welcome back, Muhammad Ali",
        "total_predictions": 26,
        "recent_predictions": 5,
        "notification_count": 2,
        "weather_summary": {
            "temperature": 33.4,
            "humidity": 84
        }
    }
}
```

---

# Weather Summary

Endpoint

GET

/api/v1/dashboard/weather/

Authentication

Required

Description

Returns the latest weather information used on the dashboard.

---

Success Response

```json
{
    "success": true,
    "message": "Weather summary loaded successfully.",
    "data": {
        "temperature": 33.4,
        "humidity": 84,
        "rainfall": 2.3,
        "wind_speed": 9.1,
        "fungal_disease_risk": "High",
        "heat_stress_risk": "Moderate",
        "drought_risk": "Low"
    }
}
```

`wind_speed` is in m/s, matching the Module 3 contract's native unit (see Section 5A/Section 9) — not converted to km/h.

This flat shape is unchanged from before the real Module 3 integration and is used only by the compact dashboard weather card; it is derived from the same underlying Module 3 call as Section 5A below, not a second weather integration.

---

# 5A. Weather Report (Full Module 3 Detail)

Endpoint

GET

/api/v1/weather/current/

Authentication

Required

Description

Returns the Weather Module's full report for the Weather page (UI_SPECIFICATION.md section 14) — current conditions, risk assessment with reasons, units, and the nullable next-day forecast / predicted risk. This is the real AI Module 3 output (Section 9) passed through unchanged, not the flattened dashboard-card shape above.

Query Parameters

| Parameter | Description |
|---|---|
| farm_id | Optional. Defaults to the user's most recently created farm, same rule as `GET /api/v1/dashboard/weather/`. |

Success Response

```json
{
    "success": true,
    "message": "Weather report loaded successfully.",
    "data": {
        "farm_id": "8f14e45f-ceea-4c9a-b3f4-000000000001",
        "timestamp": "2026-09-01T22:39:35Z",
        "weather": {
            "temperature": 28.0,
            "humidity": 78.0,
            "rainfall_last_7_days_mm": 1.8,
            "wind_speed": 2.2
        },
        "units": {
            "temperature": "celsius",
            "humidity": "percent",
            "rainfall_last_7_days_mm": "mm",
            "wind_speed": "m/s"
        },
        "risk_assessment": {
            "fungal_disease_risk": "Moderate",
            "fungal_disease_reason": "...",
            "heat_stress_risk": "Low",
            "heat_stress_reason": "...",
            "drought_risk": "High",
            "drought_reason": "..."
        },
        "forecast": null,
        "predicted_risk_assessment": null
    }
}
```

`data` is `null` (with `success: true`) when the user has no farm yet, same empty-state convention as the dashboard weather endpoint. `forecast` / `predicted_risk_assessment` are nullable — see Section 9's "AI Module 3" contract.

Error Responses

| Status | Condition | Message |
|---|---|---|
| 404 | Requested `farm_id` does not belong to the user | "Farm not found." |
| 503 | Weather Module unreachable | "Weather service is temporarily unavailable." |

---

# Recent Predictions

Endpoint

GET

/api/v1/dashboard/recent-predictions/

Authentication

Required

Description

Returns a list of the user's most recent analysis records. `diagnosis` and `confidence` are Module 1's own `prediction.display_name` and `prediction.confidence`, read verbatim — both `null` when Module 1 returned `status: "uncertain"`.

---

Query Parameters

| Parameter | Description |
|-----------|-----------------------------|
| limit | Number of records to return |

Example

/api/v1/dashboard/recent-predictions/?limit=5

---

Success Response

```json
{
    "success": true,
    "message": "Recent predictions retrieved successfully.",
    "data": [
        {
            "prediction_id": "pred_001",
            "diagnosis": "Powdery Mildew",
            "confidence": 0.94,
            "created_at": "2026-07-31T10:15:15Z"
        }
    ]
}
```

---

# Latest Recommendations

Endpoint

GET

/api/v1/dashboard/recommendations/

Authentication

Required

Description

Reserved. Always returns an empty list: these were produced by the retired ANN Fusion layer, and no current module produces a cross-module recommendation list. Module 2's own recommendation notes appear in its result.

---

Success Response

```json
{
    "success": true,
    "message": "Recommendations loaded successfully.",
    "data": [
        "Apply nitrogen-rich fertilizer.",
        "Monitor humidity for the next 72 hours.",
        "Inspect plants after 5–7 days."
    ]
}
```

---

# Dashboard Rules

• Dashboard loads after successful login.

• One API call should populate the main dashboard.

• Dashboard should display only data belonging to the authenticated user.

• Recent Predictions should be ordered by newest first.

• Dashboard must remain responsive for desktop, tablet, and mobile devices.

• Empty states should be handled gracefully if no predictions exist.

• Weather information should reflect the latest available analysis.

# 6. Prediction History APIs

The Prediction History module allows authenticated users to access all previous AI analyses performed using GreenGuard.

Each prediction record includes the independent results of:

• Module 1 — Disease Detection

• Module 2 — Soil & Nutrient Health (the farm's latest result at scan time, or null)

• Module 3 — Weather Risk

Module 4 is the integrated report that shows these together; it adds no result of its own.

Module 2 is also a separate, standalone feature (Section 8A) usable independently of the prediction workflow.

Prediction history enables users to review previous analyses and crop health trends. In the list, `diagnosis` and `confidence` are Module 1's own result (null when Module 1 was uncertain); `search` matches Module 1's disease name.

---

## History Endpoints

| Method | Endpoint | Authentication | Description |
|----------|-------------------------------------------|----------------|--------------------------------|
| GET | /api/v1/history/ | Required | Get Prediction History |
| GET | /api/v1/history/{prediction_id}/ | Required | Get Prediction Details |
| DELETE | /api/v1/history/{prediction_id}/ | Required | Delete Prediction Record |

---

# Get Prediction History

Endpoint

GET

/api/v1/history/

Authentication

Required

Description

Returns all prediction records belonging to the authenticated user.

Supports

• Pagination

• Search

• Sorting

• Date Filtering

---

Query Parameters

| Parameter | Description |
|------------|------------------------------|
| page | Current Page |
| limit | Number of Records |
| search | Search Diagnosis |
| sort | newest / oldest |
| from_date | Start Date |
| to_date | End Date |

Example

GET

/api/v1/history/?page=1&limit=10

---

Success Response

```json
{
    "success": true,
    "message": "Prediction history retrieved successfully.",
    "data": [
        {
            "prediction_id": "pred_001",
            "diagnosis": "Powdery Mildew",
            "confidence": 0.94,
            "recommended_crop": "Tomato",
            "created_at": "2026-07-31T10:15:15Z"
        }
    ]
}
```

---

# Get Prediction Details

Endpoint

GET

/api/v1/history/{prediction_id}/

Authentication

Required

Description

Returns the complete AI report for a selected prediction.

The response includes

• Module 1 — Disease Detection Output

• Module 2 — Soil & Nutrient Health Output (or null)

• Module 3 — Weather Risk Output

The backend returns the exact JSON stored during prediction.

---

Success Response

Returns

The same record shape as GET /api/v1/predictions/{prediction_id}/, with `prediction_report` holding the three module results.

No prediction fields should be modified.

---

# Delete Prediction

Endpoint

DELETE

/api/v1/history/{prediction_id}/

Authentication

Required

Description

Deletes a prediction record.

Only the owner of the prediction may delete it.

Administrators may delete any record.

---

Success Response

```json
{
    "success": true,
    "message": "Prediction deleted successfully."
}
```

---

# History Rules

• Users can access only their own prediction history.

• History must be ordered by newest first.

• Deleted records cannot be recovered.

• Pagination is required when records exceed one page.

• Prediction details must preserve the original AI outputs.

---

# 7. Notification APIs

GreenGuard notifies users about important activities.

Examples

• Prediction Completed

• High Disease Risk

• Weather Alerts

• System Announcements

• Recommendation Updates

---

## Notification Endpoints

| Method | Endpoint | Authentication | Description |
|----------|-----------------------------------------------|----------------|----------------------------|
| GET | /api/v1/notifications/ | Required | Get Notifications |
| PUT | /api/v1/notifications/{notification_id}/read/ | Required | Mark Notification as Read |
| DELETE | /api/v1/notifications/{notification_id}/ | Required | Delete Notification |

---

# Get Notifications

Endpoint

GET

/api/v1/notifications/

Authentication

Required

Description

Returns all notifications for the authenticated user.

Notifications are ordered by newest first.

---

Success Response

```json
{
    "success": true,
    "message": "Notifications retrieved successfully.",
    "data": [
        {
            "notification_id": "not_001",
            "title": "Prediction Completed",
            "message": "Your latest plant analysis is ready.",
            "is_read": false,
            "created_at": "2026-07-31T10:20:00Z"
        }
    ]
}
```

---

# Mark Notification as Read

Endpoint

PUT

/api/v1/notifications/{notification_id}/read/

Authentication

Required

Description

Marks a notification as read.

---

Success Response

```json
{
    "success": true,
    "message": "Notification marked as read."
}
```

---

# Delete Notification

Endpoint

DELETE

/api/v1/notifications/{notification_id}/

Authentication

Required

Description

Permanently deletes a notification.

---

Success Response

```json
{
    "success": true,
    "message": "Notification deleted successfully."
}
```

---

# Notification Rules

• Notifications belong only to the authenticated user.

• New notifications appear at the top.

• Read status must persist in the database.

• Notification badge count should update automatically.

• Deleting a notification is permanent.

• System-generated notifications cannot be edited by users.

• Notification timestamps use ISO 8601 format.

# 8. Admin APIs

The Admin Module provides centralized system management and monitoring capabilities.

Only users with the **Admin** role are authorized to access these endpoints.

The Admin Dashboard allows administrators to monitor users, predictions, AI services, system statistics, and platform health.

---

## Admin Endpoints

| Method | Endpoint | Authentication | Role | Description |
|----------|-------------------------------------------|----------------|--------|----------------------------|
| GET | /api/v1/admin/dashboard/ | Required | Admin | Admin Dashboard Overview |
| GET | /api/v1/admin/users/ | Required | Admin | Get All Users |
| GET | /api/v1/admin/users/{user_id}/ | Required | Admin | Get User Details |
| PUT | /api/v1/admin/users/{user_id}/status/ | Required | Admin | Activate / Deactivate User |
| DELETE | /api/v1/admin/users/{user_id}/ | Required | Admin | Delete User |
| GET | /api/v1/admin/predictions/ | Required | Admin | Get All Predictions |
| DELETE | /api/v1/admin/predictions/{prediction_id}/ | Required | Admin | Delete Prediction |
| GET | /api/v1/admin/ai-monitoring/ | Required | Admin | AI Module Status |
| GET | /api/v1/admin/system-health/ | Required | Admin | System Health |
| GET | /api/v1/admin/statistics/ | Required | Admin | Platform Statistics |

---

# Admin Dashboard

Endpoint

GET

/api/v1/admin/dashboard/

Authentication

Required

Role

Admin

Description

Returns a summarized overview of the entire GreenGuard platform.

---

Dashboard Includes

• Total Registered Users

• Total Predictions

• Total Active Users

• Total AI Requests

• System Health

• AI Module Status

• Recent Activities

• Latest Notifications

---

Success Response

```json
{
    "success": true,
    "message": "Admin dashboard loaded successfully.",
    "data": {
        "total_users": 125,
        "active_users": 98,
        "total_predictions": 1356,
        "system_status": "Healthy"
    }
}
```

---

# Get All Users

Endpoint

GET

/api/v1/admin/users/

Authentication

Required

Role

Admin

Description

Returns all registered users.

Supports

• Search

• Pagination

• Sorting

• Status Filtering

---

Success Response

```json
{
    "success": true,
    "message": "Users retrieved successfully.",
    "data": [
        {
            "user_id": "usr_001",
            "full_name": "Muhammad Ali",
            "email": "ali@example.com",
            "status": "Active",
            "role": "Farmer"
        }
    ]
}
```

---

# Get User Details

Endpoint

GET

/api/v1/admin/users/{user_id}/

Authentication

Required

Role

Admin

Description

Returns complete information about a selected user.

Includes

• Profile Information

• Prediction Count

• Registration Date

• Account Status

---

# Update User Status

Endpoint

PUT

/api/v1/admin/users/{user_id}/status/

Authentication

Required

Role

Admin

Description

Activates or deactivates a user account.

---

Request Body

```json
{
    "status": "Inactive"
}
```

---

Success Response

```json
{
    "success": true,
    "message": "User status updated successfully."
}
```

---

# Delete User

Endpoint

DELETE

/api/v1/admin/users/{user_id}/

Authentication

Required

Role

Admin

Description

Deletes a user account.

Associated prediction records may also be removed according to system policy.

---

Success Response

```json
{
    "success": true,
    "message": "User deleted successfully."
}
```

---

# Get All Predictions

Endpoint

GET

/api/v1/admin/predictions/

Authentication

Required

Role

Admin

Description

Returns prediction records from all users.

Supports

• Search

• Pagination

• Filtering

• Sorting

---

Success Response

```json
{
    "success": true,
    "message": "Predictions retrieved successfully.",
    "data": [
        {
            "prediction_id": "pred_001",
            "user": "Muhammad Ali",
            "diagnosis": "Powdery Mildew",
            "confidence": 0.94,
            "created_at": "2026-07-31T10:15:15Z"
        }
    ]
}
```

---

# Delete Prediction

Endpoint

DELETE

/api/v1/admin/predictions/{prediction_id}/

Authentication

Required

Role

Admin

Description

Deletes any prediction record from the system.

---

Success Response

```json
{
    "success": true,
    "message": "Prediction deleted successfully."
}
```

---

# AI Monitoring

Endpoint

GET

/api/v1/admin/ai-monitoring/

Authentication

Required

Role

Admin

Description

Displays the operational status of all AI modules.

Monitored Modules

• Module 1 — Disease Detection (live service, probed via its `GET /health`)

• Module 2 — Soil & Nutrient Health (live service, probed via its `GET /health`)

• Module 3 — Weather Risk (local service, probed via its `GET /health`)

• Module 4 — Integrated Report: not a service, so it is never probed. `fusion_module` keeps its key for compatibility and always reports `"Not used — integration layer"`.

Each probed module reports `"Connected"`, `"Unreachable"`, or `"Mock Mode"` when `ENABLE_MOCK_AI` is on.

---

Success Response

```json
{
    "success": true,
    "message": "AI monitoring loaded successfully.",
    "data": {
        "image_module": "Connected",
        "soil_module": "Connected",
        "weather_module": "Connected",
        "fusion_module": "Not used — integration layer"
    }
}
```

---

# System Health

Endpoint

GET

/api/v1/admin/system-health/

Authentication

Required

Role

Admin

Description

Returns the operational status of backend services.

Includes

• Backend Server

• PostgreSQL Database

• AI Services — the two deployed modules (Module 1 and Module 2): `"Healthy"` when both are reachable, `"Degraded"` when one is, `"Unreachable"` when neither is, `"Mock Mode"` when mocks are on

• Weather Module (Module 3) Connection

• Storage

---

Success Response

```json
{
    "success": true,
    "message": "System health retrieved successfully.",
    "data": {
        "backend": "Healthy",
        "database": "Healthy",
        "ai_services": "Healthy",
        "weather_api": "Connected"
    }
}
```

---

# Platform Statistics

Endpoint

GET

/api/v1/admin/statistics/

Authentication

Required

Role

Admin

Description

Returns analytical statistics about GreenGuard.

Statistics Include

• Total Users

• Total Predictions

• Most Detected Diseases

• Most Recommended Crops

• Daily Prediction Count

• Monthly Prediction Trends

• Active User Count

---

Success Response

```json
{
    "success": true,
    "message": "Statistics retrieved successfully.",
    "data": {
        "total_users": 125,
        "total_predictions": 1356,
        "active_users": 98,
        "most_detected_disease": "Powdery Mildew",
        "most_recommended_crop": "Tomato"
    }
}
```

---

# Admin Rules

• Only users with the **Admin** role can access Admin APIs.

• Unauthorized users must receive **HTTP 403 Forbidden**.

• All admin actions must be logged for auditing.

• Admins can manage users and prediction records.

• AI monitoring endpoints are read-only.

• System health endpoints do not expose sensitive server information.

• All timestamps use ISO 8601 format.

• Admin APIs follow the same authentication and response standards as all other APIs.

# 8A. Module 2 — Soil & Nutrient Health APIs

## Overview

Module 2 ("Soil & Nutrient Health Check") is a standalone, farmer-facing questionnaire feature. It is **independent of the Plant Image Prediction workflow** (`POST /api/v1/predictions/analyze/`) — a farmer can run a Soil & Nutrient Health Check for a farm without uploading a leaf image, and can analyze a leaf image without running a Soil & Nutrient Health Check.

Architecture

```
Frontend
   ↓
POST /api/v1/module2/analyze/   (single public endpoint)
   ↓
Django Backend — Module 2 Orchestrator
   ├── Module 2A — Nutrient Risk (ML model)
   └── Module 2B — Soil / pH / Lockout Analysis
   ↓
Combined Module 2 Response
   ↓
Frontend
```

The frontend NEVER calls Module 2A or Module 2B directly — they are internal to the backend. One form, one submit action, one API call.

Module 2's latest persisted result for a farm is also included, verbatim, as the `module2` section of every Quick Scan report (`POST /api/v1/predictions/analyze/`) — never a live call. See "AI Module 2" in Section 9 for the internal contract.

---

## Module 2 Endpoint

| Method | Endpoint | Authentication | Description |
|--------|-----------------------------|-----------------|--------------------------------------------|
| POST | /api/v1/module2/analyze/ | Required | Run a Soil & Nutrient Health Check for a farm |

---

## Analyze Soil & Nutrient Health

Endpoint

POST

/api/v1/module2/analyze/

Authentication

Required

Authorization

Bearer <JWT_TOKEN>

Content Type

application/json

---

### Request Parameters

| Field | Type | Required | Source | Notes |
|---|---|---|---|---|
| farm_id | UUID | Yes | Farmer selects | Must belong to the authenticated user. The backend resolves this farm's stored latitude/longitude and calls the Module 3 Weather Risk Module (`ai/Weather_Module`) to auto-fill `temperature_c`, `humidity_pct`, and `rainfall_mm_last_7_days` before calling the Module 2 Orchestrator. The farmer never enters weather values manually, and the frontend never includes them in this request. |
| crop | string | Yes | Farmer | One of `module2_field_options.json` → `categorical_fields.crop`. See "Unsupported Crop Behavior" below. |
| growth_stage | string | Yes | Farmer | One of `categorical_fields.growth_stage` |
| soil_type | string | Yes | Farmer | One of `categorical_fields.soil_type` |
| last_fertilizer_type | string | Yes | Farmer | One of `categorical_fields.last_fertilizer_type`. The no-fertilizer value MUST be the literal string `"No_Fertilizer"` — never `"None"`, `null`, or `"none"`. |
| days_since_fertilizer | string | Yes | Farmer, or auto-set by frontend | One of `categorical_fields.days_since_fertilizer`. Must equal `"not_applicable"` when `last_fertilizer_type == "No_Fertilizer"`, and must NOT equal `"not_applicable"` otherwise. When fertilizer is `No_Fertilizer`, the frontend auto-sets this value and does not ask the farmer the question. |
| irrigation_source | string | Yes | Farmer | One of `categorical_fields.irrigation_source` |
| irrigation_adequacy | string | Yes | Farmer | One of `categorical_fields.irrigation_adequacy` |
| symptoms | object | Yes | Farmer | Boolean flags keyed exactly as `module2_field_options.json` → `symptom_fields.keys`. `none_visible` is mutually exclusive with every other key (enforced client-side before submit, and validated server-side). |
| ph_value | float | Yes | Farmer's soil meter | Range 0–14 (typical 4.5–8.5). **Required as of the Stress Module's v1.1.0 delivery (2026-09-10)** — a soil meter ships with the deployment. Missing or `null` is rejected with HTTP 422; never defaulted. Not used as a Module 2A model feature, but drives Module 2B's growing-conditions comparison and 40 of the 100 points in `overall_soil_health_score`. |
| soil_moisture_pct | float | Yes | Farmer's soil meter | Range 0–100. Required — see `ph_value` above. |
| light_intensity_lux | float | Yes | Farmer's soil meter | Range 0 or more (typically up to ~120,000). Required — see `ph_value` above. |

The full set of valid categorical values is defined in `docs/module2_field_options.json` — the frontend and backend must both read from that file rather than hardcoding a competing list.

---

### Example Request

```json
{
  "farm_id": "8f14e45f-ceea-4c9a-b3f4-000000000001",
  "crop": "wheat",
  "growth_stage": "vegetative",
  "soil_type": "sandy",
  "last_fertilizer_type": "No_Fertilizer",
  "days_since_fertilizer": "not_applicable",
  "irrigation_source": "tube_well",
  "irrigation_adequacy": "excessive",
  "ph_value": 4.5,
  "soil_moisture_pct": 62,
  "light_intensity_lux": 28000,
  "symptoms": {
    "yellowing_older_leaves": true,
    "purple_reddish_tint": false,
    "brown_scorched_leaf_edges": false,
    "stunted_growth": true,
    "poor_flowering_or_fruiting": false,
    "weak_stems": false,
    "interveinal_chlorosis_older_leaves": false,
    "interveinal_chlorosis_young_leaves": false,
    "leaf_curling_brittle": false,
    "short_internodes_small_leaves": false,
    "none_visible": false
  }
}
```

Note: `temperature_c`, `humidity_pct`, and `rainfall_mm_last_7_days` are intentionally absent from this request — they are resolved server-side from `farm_id` and appended by the backend before calling the Module 2 Orchestrator (see Section 11, "AI Module 2").

---

### Success Response — Supported Crop

Status Code

200 OK

```json
{
    "success": true,
    "message": "Soil & nutrient health check completed successfully.",
    "data": {
        "crop_supported": true,
        "module2a": {
            "nitrogen_risk": { "level": "high", "confidence": 0.95 },
            "phosphorus_risk": { "level": "low", "confidence": 0.39 },
            "potassium_risk": { "level": "medium", "confidence": 0.55 },
            "magnesium_risk": { "level": "high", "confidence": 0.41 },
            "zinc_risk": { "level": "low", "confidence": 0.7 },
            "boron_risk": { "level": "high", "confidence": 0.42 },
            "overall_nutrient_health": "moderate",
            "input_typicality": { "anomaly_score": 0.065, "flag": "typical" },
            "model_version": "module2a-v5"
        },
        "module2b": {
            "ph": {
                "current": 4.5,
                "ideal_range": [6.0, 7.5],
                "gap": 1.5,
                "status": "critical",
                "nutrient_lockout_note": "Soil is strongly acidic. This severely limits potassium, nitrogen, phosphorus, calcium, and magnesium — and can raise aluminum/manganese to toxic levels. Fertilizer alone will not fix this; consider liming. A laboratory soil test is recommended to confirm and guide correction."
            },
            "soil_moisture": {
                "current": 62.0,
                "ideal_range": [50.0, 70.0],
                "gap": 0.0,
                "status": "ok"
            },
            "light": {
                "current": 28000.0,
                "ideal_range": [25000.0, null],
                "gap": 0.0,
                "status": "ok"
            },
            "crop_supported": true
        },
        "overall_soil_health_score": 47.5,
        "overall_soil_health_label": "poor",
        "recommendation_notes": {
            "headline": "Nitrogen needs attention first.",
            "needs_attention": [
                { "nutrient": "Nitrogen", "level": "high", "confidence_pct": 95, "confidence_text": "95% confident — strong match", "why": "yellowing on your older leaves, sandy soil (nutrients wash out faster), no fertilizer applied" }
            ],
            "looking_fine": [
                { "nutrient": "Phosphorus", "level": "low", "confidence_pct": 39, "confidence_text": "39% confident — based on limited signs" }
            ],
            "caveat": "This advice is based on your answers and soil-meter readings. A soil lab test can add exact nutrient levels if you need them.",
            "soil_condition_note": "Soil is strongly acidic. This severely limits potassium, nitrogen, phosphorus, calcium, and magnesium — and can raise aluminum/manganese to toxic levels. Fertilizer alone will not fix this; consider liming. A laboratory soil test is recommended to confirm and guide correction."
        },
        "model_version": "module2-orchestrator-v1",
        "module2a_model_version": "module2a-v5"
    }
}
```

`overall_soil_health_score` is 0–100. `overall_soil_health_label` buckets are `good` (80–100), `moderate` (50–79.99), `poor` (0–49.99), per `module2_field_options.json` → `module2_orchestrator_output_schema`.

`ph_value`, `soil_moisture_pct`, and `light_intensity_lux` are required (see Request Parameters above) — `module2b`'s comparison entries always reflect a real farmer reading, never a fabricated or defaulted one.

---

### Success Response — Unsupported Crop

Status Code

200 OK

```json
{
    "success": true,
    "message": "Soil & nutrient health check completed.",
    "data": {
        "crop_supported": false,
        "message": "Nutrient and soil-condition analysis isn't available yet for this crop.",
        "module2a": null,
        "module2b": null,
        "overall_soil_health_score": null,
        "overall_soil_health_label": null,
        "recommendation_notes": null
    }
}
```

### Unsupported Crop Behavior

Per `module2_field_options.json` → `crop_model_support`:

**Trained and supported (all 15 catalog crops):** `wheat`, `rice`, `cotton`, `sugarcane`, `maize`, `potato`, `tomato`, `chickpea`, `eggplant`, `cucumber`, `bitter_gourd`, `snake_gourd`, `ridge_gourd`, `ash_gourd`, `bottle_gourd`.

**Resolved 2026-09-10:** all 15 crops are now trained and served by `module2a-v5` — there is no longer a "pending retrain" subset, and no client-side crop gate is needed. Send any of the 15 crop values straight to Module 2, no special-casing.

The "Unsupported Crop" response above is retained as documented contract for a crop value outside this list of 15 (which Django's own categorical whitelist would already reject with a 422 validation error before this branch is reached — see "Validation Errors" below). The backend still short-circuits before calling Module 2 for any crop not in `trained_and_supported`, so the branch is exercised defensively rather than by any value currently reachable through the public API.

---

### Validation Errors

Status Code

422 Validation Error

```json
{
    "success": false,
    "message": "Validation failed.",
    "errors": {
        "crop": ["\"maize \" is not a valid crop value."],
        "days_since_fertilizer": ["days_since_fertilizer must be \"not_applicable\" when last_fertilizer_type is \"No_Fertilizer\"."]
    }
}
```

Validation rules:

• All categorical fields must be one of the values listed in `module2_field_options.json`.

• `days_since_fertilizer` conditional rule (`not_applicable` iff `last_fertilizer_type == "No_Fertilizer"`) is enforced server-side, not just client-side.

• `symptoms` must include every key listed in `symptom_fields.keys`, all boolean. `none_visible` mutually exclusive with the rest.

• `ph_value`, `soil_moisture_pct`, `light_intensity_lux` are **required** (0–14, 0–100, and ≥0 respectively) — missing, `null`, or out-of-range values are rejected with 422, never defaulted or silently accepted.

---

### Other Error Responses

| Status | Condition | Message |
|--------|-----------|---------|
| 401 | Missing/invalid JWT | "Authentication credentials were not provided." |
| 404 | `farm_id` does not belong to the authenticated user | "Farm not found." |
| 422 | Invalid categorical value, missing required field, or conditional-rule violation | See "Validation Errors" above |
| 503 | Weather resolution failed (Module 3 Weather Module unreachable) | "Weather service is temporarily unavailable." |
| 500 | Module 2 Orchestrator unreachable or errored | "AI module is currently unavailable." |

---

### Module 2 Rules

• The frontend must never call Module 2A or Module 2B directly — only `POST /api/v1/module2/analyze/`.

• The farmer never manually enters `temperature_c`, `humidity_pct`, or `rainfall_mm_last_7_days` — these are resolved server-side via `farm_id` using the Module 3 Weather Module. No second weather integration may be created.

• `ph_value`, `soil_moisture_pct`, `light_intensity_lux` are required soil-meter readings (never a lab measurement) — the frontend must collect all three before allowing submission.

• The backend must not invent, rename, or restructure any field in the Module 2 request or response beyond what is documented here and in `module2_field_options.json` / `module2_io_examples.json`.

• A Soil & Nutrient Health Check is not automatically stored as a `predictions` row — see DATABASE_SPECIFICATION.md; no schema change accompanies this endpoint.

# 8B. Module 1 — Disease Detection APIs

## Overview

Module 1 ("Disease Check") is a standalone, farmer-facing leaf-photo check backed by the AI team's real, live Disease Module service (see `ai/API_CONTRACT.md`). The same live service also supplies the `module1` section of every Quick Scan report (`POST /api/v1/predictions/analyze/`, Section 3), stored verbatim in the same contract shown below.

The older placeholder Module 1 contract (`disease`/`nutrient_deficiency`/`insect`) is retired — it was never delivered, and no GreenGuard module detects nutrient deficiencies or insects from the leaf photo.

Architecture

```
Frontend
   ↓
POST /api/v1/module1/analyze/   (single public endpoint)
   ↓
Django Backend
   ↓
Module 1 Live Service (external, e.g. https://gg-module1.onrender.com)
   ↓
Django Backend
   ↓
Frontend
```

The frontend NEVER calls the live Disease Module directly — no CORS is configured for it and it requires a server-side `X-API-Key` the frontend never receives. One upload, one submit action, one API call.

---

## Module 1 Endpoint

| Method | Endpoint | Authentication | Description |
|--------|-----------------------------|-----------------|--------------------------------------------|
| POST | /api/v1/module1/analyze/ | Required | Run a live disease check on one leaf photo for a farm |

---

## Analyze Disease

Endpoint

POST

/api/v1/module1/analyze/

Authentication

Required

Authorization

Bearer <JWT_TOKEN>

Content Type

multipart/form-data

### Request Parameters

| Field | Type | Required | Notes |
|---|---|---|---|
| image | file | Yes | JPG, JPEG, or PNG. Max 10 MB. The live service itself decodes/validates further (min 100px per side, max 50 megapixels, and formats beyond JPG/PNG) — see `ai/API_CONTRACT.md`. |
| farm_id | UUID | Yes | Must belong to the authenticated user. Forwarded to the live service so its response can be traced back to this farm. |
| crop | string | No | One of `wheat`, `rice`, `cotton`, `maize`, `sugarcane`, `tomato`, `potato` (case-insensitive). Should be sent whenever the farmer has selected a crop — the live service's own accuracy is materially worse without it. Never defaulted or invented by the backend when the farmer hasn't chosen one. |

---

### Success Response — Confident (`status: "ok"`)

Status Code

200 OK

```json
{
    "success": true,
    "message": "Disease check completed successfully.",
    "data": {
        "status": "ok",
        "farm_id": "8f14e45f-ceea-4c9a-b3f4-000000000001",
        "timestamp": "2026-09-26T04:55:12Z",
        "prediction": {
            "class_id": "wheat_yellow_rust",
            "crop": "wheat",
            "disease": "yellow_rust",
            "display_name": "Yellow Rust",
            "is_healthy": false,
            "confidence": 0.8812
        },
        "top3": [
            { "class_id": "wheat_yellow_rust", "crop": "wheat", "disease": "yellow_rust", "display_name": "Yellow Rust", "is_healthy": false, "confidence": 0.8812 },
            { "class_id": "wheat_brown_rust", "crop": "wheat", "disease": "brown_rust", "display_name": "Brown Rust", "is_healthy": false, "confidence": 0.0713 },
            { "class_id": "wheat_septoria", "crop": "wheat", "disease": "septoria", "display_name": "Septoria", "is_healthy": false, "confidence": 0.0208 }
        ],
        "crop_source": "user",
        "detected_crop": "wheat",
        "warnings": [],
        "message": null,
        "model_version": "efficientnet_b0-1.0",
        "inference_ms": 14.2,
        "request_id": "3f9a1c2b7d4e"
    }
}
```

`data` is the live service's exact JSON response, forwarded unmodified (see "Module 1 Rules" below). The frontend shows `prediction` as the main result and the OTHER `top3` entries (filtered by `class_id`, never by `display_name`) as "closely related."

---

### Success Response — Uncertain (`status: "uncertain"`)

Status Code

200 OK

```json
{
    "success": true,
    "message": "Disease check completed successfully.",
    "data": {
        "status": "uncertain",
        "prediction": null,
        "top3": [
            { "class_id": "wheat_yellow_rust", "crop": "wheat", "disease": "yellow_rust", "display_name": "Yellow Rust", "is_healthy": false, "confidence": 0.3821 },
            { "class_id": "wheat_brown_rust", "crop": "wheat", "disease": "brown_rust", "display_name": "Brown Rust", "is_healthy": false, "confidence": 0.2944 },
            { "class_id": "wheat_healthy", "crop": "wheat", "disease": "healthy", "display_name": "Healthy", "is_healthy": true, "confidence": 0.2015 }
        ],
        "warnings": ["BLURRY_IMAGE"],
        "message": "Image unclear. Please retake the photo in good light, close to one leaf.",
        "crop_source": "model",
        "detected_crop": "wheat",
        "farm_id": "8f14e45f-ceea-4c9a-b3f4-000000000001",
        "timestamp": "2026-09-26T04:55:13Z",
        "model_version": "efficientnet_b0-1.0",
        "inference_ms": 15.9,
        "request_id": "7c1e4a90b3d2"
    }
}
```

`prediction` is `null` and must never be invented. `top3` is still fully populated and must still be shown — as "possible results," not "closely related" — per `ai/API_CONTRACT.md`'s explicit instruction to render `top3` on every response regardless of `status`.

---

### Error Responses

| Status | Condition | Message |
|--------|-----------|---------|
| 401 | Missing/invalid JWT | "Authentication credentials were not provided." |
| 404 | `farm_id` does not belong to the authenticated user | "Farm not found." |
| 422 | Local validation failure (missing `image`/`farm_id`, malformed UUID) | "Validation failed." + field errors |
| 400 | Live service rejected the image (`MISSING_IMAGE` / `INVALID_IMAGE` / `IMAGE_TOO_SMALL` / `INVALID_REQUEST`) | A friendly, code-specific message — never the raw upstream error |
| 413 | Live service rejected an oversized file (`FILE_TOO_LARGE`) | "Image size must not exceed 10 MB." |
| 422 | Live service rejected the crop (`INVALID_CROP`) | The live service's own farmer-facing message (lists the valid crops) |
| 503 | Live service unreachable, timed out (after one retry), starting up (`MODEL_NOT_READY`), or its `X-API-Key` was rejected (`UNAUTHORIZED`) | "Disease detection service is currently unavailable. Please try again later." |
| 500 | Live service internal error (`INTERNAL_ERROR`) or any other unmapped failure | "Prediction Failed" |

A misconfigured/rejected `X-API-Key` is always reported as a generic 503 "unavailable," never surfaced as an authentication problem — that failure is the deployment's fault, never the farmer's.

---

### Module 1 Rules

• The frontend must never call the live Disease Module directly — only `POST /api/v1/module1/analyze/`. No `NEXT_PUBLIC_*` environment variable ever holds `GREENGUARD_API_KEY`.

• The backend adds the `X-API-Key` header server-side, from the `GREENGUARD_API_KEY` environment variable — never hard-coded, never logged, never returned in any response.

• The backend must not invent, rename, restructure, or recompute any field inside `data` — it is the live service's response, forwarded exactly as received, per `ai/API_CONTRACT.md`.

• `top3` must be rendered on every response, confident or uncertain — never hidden because `status` is `"uncertain"`, and the main prediction must never be duplicated inside it when confident.

• Every successful call (either `status`) is additionally persisted as a `DiseaseCheck` row (`backend/module1/models.py`) as an internal side effect — this does not alter the response above and is not automatically linked to a `predictions` row.

• A Disease Check is not stored as a `predictions` row. Quick Scan calls the same service separately and stores its own response in the analysis report.

# 9. Internal AI Service Contracts

## Overview

This section defines the communication between the Django Backend and the AI modules.

These APIs are **internal services** and are **NOT exposed to the frontend**.

The frontend communicates only with the Django REST API.

The Django backend communicates with the AI services.

The backend MUST NOT modify any AI prediction fields.

The backend MUST return the AI responses exactly as received.

---

# Internal Workflow

Frontend

↓

POST /api/v1/predictions/analyze/

↓

Django Backend

↓

Module 1 — Disease Detection (live service)

↓

Farm's Latest Persisted Module 2 (Soil & Nutrient Health) Result — not invoked live

↓

Module 3 — Weather Risk (local service)

↓

Module 4 — Integrated Analysis Report (stored as one Prediction; no model, no service)

↓

Return Saved Report

> Module 2 (Soil & Nutrient Health) is also invoked independently via its own public endpoint (Section 8A) for the standalone Soil Health feature; it is documented below for completeness of the AI service contracts.

---

# AI Module 1

## Disease Detection (live service)

Purpose

Detects plant disease from one leaf photo.

Service

Deployed independently (currently `https://gg-module1.onrender.com`), configured via `DISEASE_MODULE_URL`. Every `/v1/*` request carries the `X-API-Key` header from `GREENGUARD_API_KEY`.

Endpoint

`POST /v1/predict` — multipart `image` (required), `crop` (optional), `farm_id` (optional, echoed back).

Output — confident (abridged; the full contract is in `ai/API_CONTRACT.md`)

```json
{
  "status": "ok",
  "farm_id": "farm_001",
  "timestamp": "2026-09-26T04:55:12Z",
  "prediction": {
    "class_id": "wheat_yellow_rust",
    "crop": "wheat",
    "disease": "yellow_rust",
    "display_name": "Yellow Rust",
    "is_healthy": false,
    "confidence": 0.8812
  },
  "top3": [ { "class_id": "wheat_yellow_rust", "...": "..." } ],
  "crop_source": "user",
  "detected_crop": "wheat",
  "warnings": [],
  "message": null,
  "model_version": "efficientnet_b0-1.0",
  "inference_ms": 14.2,
  "request_id": "a1b2c3d4e5f6"
}
```

Output — uncertain

`status` is `"uncertain"` and `prediction` is `null`; `top3`, `warnings` and `message` are still returned. This is a normal HTTP 200 result: the backend stores it and the report shows all `top3` entries as possible results.

Module 1 does not return nutrient-deficiency or insect results.

Backend Rules

• Do not modify labels.

• Do not modify confidence values.

• Store response exactly.

---

# AI Module 2

## Soil & Nutrient Health (Orchestrator: Module 2A + Module 2B)

Purpose

Analyzes a farmer questionnaire (crop, growth stage, soil type, fertilizer history, irrigation, visible symptoms) plus weather and required soil-meter readings, and returns nutrient risk levels, growing-condition comparisons, a soil health score, and ready-to-display farmer-facing recommendation text.

**Delivered implementation:** `ai/Stress_Module` — a real, runnable FastAPI microservice ("Module 2" / "Stress Module", version 1.2.0) exposing a single public endpoint, `POST /predict` (default `http://localhost:8002`, configurable via `STRESS_MODULE_URL`). Module 2A (nutrient-risk ML, `module2a-v5`) and Module 2B (pH/moisture/light rule comparison) are internal to that service and have no routes of their own. See `ai/Stress_Module/docs/INTEGRATION_GUIDE.md` and `Module2_Orchestrator_Spec.md` for the module's own copy of this contract.

Public-facing contract: this module is exposed to the frontend as `POST /api/v1/module2/analyze/` (Section 8A) — the request/response shapes below are the exact contract between Django (`ai_services/module2_client.py`) and the Stress Module's `/predict`, which Django populates using the farmer's questionnaire plus weather values it resolves itself from `farm_id` (Module 3 Weather Module). Unlike Modules 1, 3, and 4, Module 2 is not invoked live as part of the `/api/v1/predictions/analyze/` chain; the farm's latest persisted `Module2Analysis` snapshot is consumed instead.

Input

```json
{
  "crop": "wheat",
  "growth_stage": "vegetative",
  "soil_type": "sandy",
  "last_fertilizer_type": "No_Fertilizer",
  "days_since_fertilizer": "not_applicable",
  "irrigation_source": "tube_well",
  "irrigation_adequacy": "excessive",
  "temperature_c": 30.0,
  "humidity_pct": 55,
  "rainfall_mm_last_7_days": 45.0,
  "ph_value": 4.5,
  "soil_moisture_pct": 62,
  "light_intensity_lux": 28000,
  "symptoms": {
    "yellowing_older_leaves": true,
    "purple_reddish_tint": false,
    "brown_scorched_leaf_edges": false,
    "stunted_growth": true,
    "poor_flowering_or_fruiting": false,
    "weak_stems": false,
    "interveinal_chlorosis_older_leaves": false,
    "interveinal_chlorosis_young_leaves": false,
    "leaf_curling_brittle": false,
    "short_internodes_small_leaves": false,
    "none_visible": false
  }
}
```

`temperature_c`, `humidity_pct`, and `rainfall_mm_last_7_days` are populated by Django from the Module 3 Weather Module (resolved via the request's `farm_id`) — never entered by the farmer and never a second weather integration. **`ph_value`, `soil_moisture_pct`, and `light_intensity_lux` are required** — a soil meter ships with the deployment; the Stress Module rejects a missing/null value with HTTP 422 and Django's own serializer validates this before ever calling it.

Output

```json
{
  "crop_supported": true,
  "module2a": {
    "nitrogen_risk": { "level": "high", "confidence": 0.95 },
    "phosphorus_risk": { "level": "low", "confidence": 0.39 },
    "potassium_risk": { "level": "medium", "confidence": 0.55 },
    "magnesium_risk": { "level": "high", "confidence": 0.41 },
    "zinc_risk": { "level": "low", "confidence": 0.7 },
    "boron_risk": { "level": "high", "confidence": 0.42 },
    "overall_nutrient_health": "moderate",
    "input_typicality": { "anomaly_score": 0.065, "flag": "typical" },
    "model_version": "module2a-v5"
  },
  "module2b": {
    "ph": {
      "current": 4.5,
      "ideal_range": [6.0, 7.5],
      "gap": 1.5,
      "status": "critical",
      "nutrient_lockout_note": "Soil is strongly acidic. This severely limits potassium, nitrogen, phosphorus, calcium, and magnesium — and can raise aluminum/manganese to toxic levels. Fertilizer alone will not fix this; consider liming. A laboratory soil test is recommended to confirm and guide correction."
    },
    "soil_moisture": { "current": 62.0, "ideal_range": [50.0, 70.0], "gap": 0.0, "status": "ok" },
    "light": { "current": 28000.0, "ideal_range": [25000.0, null], "gap": 0.0, "status": "ok" },
    "crop_supported": true
  },
  "overall_soil_health_score": 47.5,
  "overall_soil_health_label": "poor",
  "recommendation_notes": {
    "headline": "Nitrogen needs attention first.",
    "needs_attention": [
      { "nutrient": "Nitrogen", "level": "high", "confidence_pct": 95, "confidence_text": "95% confident — strong match", "why": "yellowing on your older leaves, sandy soil (nutrients wash out faster), no fertilizer applied" }
    ],
    "looking_fine": [
      { "nutrient": "Phosphorus", "level": "low", "confidence_pct": 39, "confidence_text": "39% confident — based on limited signs" }
    ],
    "caveat": "This advice is based on your answers and soil-meter readings. A soil lab test can add exact nutrient levels if you need them.",
    "soil_condition_note": "Soil is strongly acidic. This severely limits potassium, nitrogen, phosphorus, calcium, and magnesium — and can raise aluminum/manganese to toxic levels. Fertilizer alone will not fix this; consider liming. A laboratory soil test is recommended to confirm and guide correction.",
    "reliability_note": null
  },
  "model_version": "module2-orchestrator-v1",
  "module2a_model_version": "module2a-v5"
}
```

`recommendation_notes` is ready-to-display farmer-facing text built from the results above by `api/recommendations.py` (added in module version 1.1.0, Project Manager-approved 2026-09-11): `headline` (one-line summary), `needs_attention` (medium/high-risk nutrients, already sorted worst-first — never re-sort), `looking_fine` (low-risk nutrients), `caveat` (always present), `soil_condition_note` (present only when pH is outside the crop's ideal range), and `reliability_note` (present only when `module2a.input_typicality.flag` is `"unusual"`).

For an unsupported crop (see Section 8A, "Unsupported Crop Behavior"), the Orchestrator returns:

```json
{
  "crop_supported": false,
  "message": "Nutrient and soil-condition analysis isn't available yet for this crop.",
  "module2a": null,
  "module2b": null,
  "overall_soil_health_score": null,
  "overall_soil_health_label": null,
  "recommendation_notes": null
}
```

Full field definitions, valid categorical values, and the scoring formula (weights, severity fractions, label buckets) are defined in `docs/module2_field_options.json` and `docs/module2_io_examples.json` — treat those files as authoritative alongside this section.

Error Contract (Stress Module's own `/predict`, not Django's public endpoint)

| Status | When | Body |
|---|---|---|
| 422 | A field missing, of the wrong type, out of range, or breaking a validation rule | FastAPI's default `{"detail": [{"type": ..., "loc": [...], "msg": ...}, ...]}` |
| 503 | Model artifacts missing, or failed checksum verification at load | `{"message": "Prediction Failed: model artifacts unavailable."}` |
| 500 | Any other internal failure | `{"message": "Prediction Failed"}` |

`ai_services/module2_client.py` branches on the HTTP status code (never the message text), logs the detail, and raises a single `Module2ServiceError` for any of the above — Django's public endpoint then returns its own existing, unchanged external error contract (see Section 8A's error table below).

Backend Rules

• Store all returned values.

• Never calculate nutrient risk, soil health score, or recommendation text inside Django.

• Never modify AI output, never rename fields, never re-sort `recommendation_notes.needs_attention`.

• All 15 catalog crops are trained-and-supported as of `module2a-v5` (2026-09-10) — there is no longer a "pending retrain" crop subset to gate.

---

# AI Module 3

## Weather Risk Engine

**Delivered implementation:** `ai/Weather_Module` — a real, runnable FastAPI microservice (Open-Meteo + rule engine, with an additive LSTM next-day forecast). Not exposed to the frontend directly; only the Django backend calls it. See `ai/Weather_Module/Weather_Module/docs/INTEGRATION_GUIDE.md` for the module's own copy of this contract, and `docs/MODULE3_INTEGRATION_STATUS.md` for the earlier blocked delivery this replaces.

Purpose

Retrieves weather information and estimates environmental risks.

Service

FastAPI, default `http://localhost:8001` (configurable via `WEATHER_MODULE_URL`).

Health check

`GET /health` → `{"status": "ok", "service": "weather-risk-module"}`

Prediction endpoint

`POST /predict`

Input

```json
{
    "latitude":31.5204,
    "longitude":74.3587,
    "farm_id":"farm_001"
}
```

The Backend retrieves the farm's latitude and longitude from the database before calling the Weather Module.
The AI Weather Module does not access the project database.
`farm_id` is included for request tracking, logging, and correlation purposes only; it defaults to `"unknown"` if omitted.
Weather retrieval is performed using the provided latitude and longitude.
Latitude must be -90 to 90; longitude must be -180 to 180 (a 422 is returned otherwise).

Output — HTTP 200

```json
{
  "farm_id": "farm_001",
  "timestamp": "2026-07-31T10:15:10Z",

  "weather": {
    "temperature": 33.4,
    "humidity": 84,
    "rainfall_last_7_days_mm": 2.3,
    "wind_speed": 9.1
  },

  "units": {
    "temperature": "celsius",
    "humidity": "percent",
    "rainfall_last_7_days_mm": "mm",
    "wind_speed": "m/s"
  },

  "risk_assessment": {
    "fungal_disease_risk": "High",
    "fungal_disease_reason": "Today's temperature (33.4°C)... [plain-English explanation]",
    "heat_stress_risk": "Moderate",
    "heat_stress_reason": "...",
    "drought_risk": "Low",
    "drought_reason": "..."
  },

  "forecast": {
    "temperature": 31.5,
    "humidity": 63.5,
    "rainfall_mm": 2.0
  },

  "predicted_risk_assessment": {
    "fungal_disease_risk": "Low",
    "fungal_disease_reason": "...",
    "heat_stress_risk": "Low",
    "heat_stress_reason": "...",
    "drought_risk": "High",
    "drought_reason": "..."
  }
}
```

`units` is a fixed, self-describing object — always present, values never change per-request.

Every `*_risk` field (in both `risk_assessment` and `predicted_risk_assessment`) has a sibling `*_reason` string — a plain-English sentence naming the threshold/value that produced it. Safe to display to the user; **never parse it for logic** — branch on `*_risk` (`Low`/`Moderate`/`High`) only, since reason wording may change between module versions.

`forecast` and `predicted_risk_assessment` are **nullable** — a best-effort, additive LSTM forecast one day ahead. Both come back `null` together if the model/scaler can't produce a prediction for any reason; `weather` and `risk_assessment` are unaffected either way and always populated on a 200 response. Never treat a `null` as zero/Low, and never fabricate a value to fill it. Per the module's own evaluation (`ai/Weather_Module/Weather_Module/docs/MODEL_DOCUMENTATION.md`), the forecast currently beats a same-as-today baseline on humidity and rainfall, but not yet on temperature — do not present it as guaranteed-accurate. It also predicts only one day ahead, never a multi-day or hourly forecast.

Error responses

| Status | Condition | Body |
|---|---|---|
| 422 | Invalid/missing latitude or longitude | FastAPI's default `{"detail": [...]}` |
| 500 | Weather provider (Open-Meteo) unreachable/rate-limited, or another internal failure | `{"message": "..."}` — always the `message` key, never `detail`, for this status |

Backend Rules

• Store weather values.

• Store risk values.

• Never change values returned by the Weather Module.

• Never recalculate `risk_assessment` or `predicted_risk_assessment` — the module owns that logic entirely.

• Never assume `forecast` / `predicted_risk_assessment` are present.

---

# Module 4

## Integrated Analysis Report (application layer — not an AI module)

Module 4 is not an AI model, not an ANN, and not a separate service. There is no Fusion API, no `/fusion/analyze/` endpoint, and no `AI_SERVICE_BASE_URL` dependency.

Module 4 is the backend's own record of one Quick Scan: the `prediction_report` JSON on a Prediction row, holding the three independent module results side by side:

```json
{
  "module1": { "...": "exact AI Module 1 output" },
  "module2": { "...": "latest persisted Module2Analysis.response_payload, verbatim — or null" },
  "module3": { "...": "exact AI Module 3 output" }
}
```

`module2` has three valid states, all passed through verbatim: the farm's latest supported-crop result, its latest unsupported-crop result, or `null` when the farm has no Module 2 analysis yet. The latest analysis on record is used regardless of age:

```python
Module2Analysis.objects.filter(farm=farm).order_by("-created_at").first()
```

Rules

• Never combine module results into a final diagnosis, combined confidence, score or recommendation.

• Never modify, rename or recompute any field inside a module result.

• Each module's result must remain displayed as its own, clearly labelled section.

> **History:** earlier versions of this specification described Module 4 as an "ANN Fusion Layer" returning `final_diagnosis`, `confidence`, `contributing_factors` and `recommendations`. That design was retired before any Fusion model was delivered. Records created under it may still carry a `module4` key and populated legacy columns; they are left untouched and shown as legacy reports.

---

# Backend Responsibilities

The Django Backend is responsible for:

• Validating frontend requests

• Saving uploaded images

• Calling AI services

• Receiving AI responses

• Saving prediction history

• Returning the final response to the frontend

The backend must never implement AI logic.

---

# AI Responsibilities

The AI Team is responsible for:

• Image preprocessing

• Disease detection (Module 1)

• Soil & nutrient health analysis (Module 2)

• Weather risk estimation (Module 3)

---

# Communication Rules

• All AI services return JSON.

• UTF-8 encoding.

• Content-Type: application/json

• HTTPS communication.

• Timeout should be configurable.

• All timestamps use ISO 8601 format.

• Confidence values should be decimal numbers between 0 and 1.

---

# Contract Rules

The JSON contracts defined in this section are fixed.

The backend team and AI team must not rename, remove, or restructure any JSON fields without updating this specification.

These JSON contracts serve as the official interface between the backend and AI modules.

# 10. Request & Response Standards

All GreenGuard REST APIs follow a consistent request and response structure to ensure predictable communication between the frontend, backend, and AI modules.

---

## Request Standards

All requests must:

• Use HTTPS

• Use UTF-8 encoding

• Include the correct Content-Type

• Be validated before processing

• Return JSON responses

---

## Content Types

JSON Requests

Content-Type

application/json

File Upload Requests

Content-Type

multipart/form-data

---

## Authorization Header

Protected APIs require JWT Authentication. Browsers send the HttpOnly `gg_access` cookie, plus `X-CSRFToken` on unsafe requests. Non-browser clients may send the access token as a header instead (see Section 1).

Example

Authorization: Bearer <ACCESS_TOKEN>

---

# Standard Success Response

```json
{
    "success": true,
    "message": "Operation completed successfully.",
    "data": {}
}
```

---

# Standard Error Response

```json
{
    "success": false,
    "message": "Something went wrong."
}
```

---

# Validation Error Response

```json
{
    "success": false,
    "message": "Validation failed.",
    "errors": {
        "field_name": [
            "Error message"
        ]
    }
}
```

---

# 11. Validation Rules

Every incoming request must be validated before processing.

---

## User Registration

Full Name

• Required

• Maximum 100 characters

Email

• Required

• Valid email format

• Must be unique

Password

• Required

• Minimum 8 characters

• Must match confirmation password

---

## Login

Email

• Required

Password

• Required

---

## Farm

Farm Name

• Required

• Maximum 100 characters

Address

• Required

Latitude

• Required

• Range -90 to +90

Longitude

• Required

• Range -180 to +180

---

## Image Upload

Supported Formats

• JPG

• JPEG

• PNG

Maximum Size

10 MB

Minimum Resolution

224 × 224 pixels

Invalid images must be rejected.

---

## Soil Parameters

The following fields are required:

• Nitrogen

• Phosphorus

• Potassium

• pH

• EC

• Organic Carbon

• Zinc

• Iron

• Copper

• Manganese

• Boron

• Sulfur

Rules

• Numeric values only

• Missing values are not allowed

---

## Location

Latitude

Range

-90 to +90

Longitude

Range

-180 to +180

---

# 12. HTTP Status Codes

| Code | Meaning |
|------|----------------------------|
| 200 | Request Successful |
| 201 | Resource Created |
| 204 | Resource Deleted Successfully |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Resource Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 429 | Too Many Requests |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

---

# 13. Error Handling

The backend should return meaningful error messages.

Common Errors

Authentication Error

```json
{
    "success": false,
    "message": "Authentication credentials were not provided."
}
```

---

Unauthorized

```json
{
    "success": false,
    "message": "Invalid or expired access token."
}
```

---

Validation Failed

```json
{
    "success": false,
    "message": "Validation failed."
}
```

---

Prediction Failed

```json
{
    "success": false,
    "message": "Prediction could not be completed."
}
```

---

Weather Service Unavailable

```json
{
    "success": false,
    "message": "Weather service is temporarily unavailable."
}
```

---

AI Service Error

```json
{
    "success": false,
    "message": "AI module is currently unavailable."
}
```

---

# 14. Security Guidelines

GreenGuard follows secure API development practices.

Authentication

• JWT Authentication in HttpOnly cookies; tokens are never exposed to JavaScript

Authorization

• Role-Based Access Control (RBAC)

Passwords

• Stored using secure hashing

HTTPS

• Required for all API communication

Input Validation

• Validate every request

SQL Injection

• Use Django ORM

Cross-Site Scripting (XSS)

• Sanitize user input

Cross-Site Request Forgery (CSRF)

• Django CSRF validation (token + trusted Origin) on login, refresh, logout and every cookie-authenticated unsafe request (see Section 1)

Sensitive Information

• Never expose passwords

• Never expose AI model paths

• Never expose database credentials

---

# 15. Rate Limiting

To prevent abuse, APIs should be rate limited.

Suggested Limits

Authentication APIs

10 requests per minute

Prediction APIs

20 requests per minute

Dashboard APIs

60 requests per minute

Admin APIs

30 requests per minute

---

# 16. File Upload Rules

Supported Formats

• JPG

• JPEG

• PNG

Maximum File Size

10 MB

Storage

Uploaded images are stored securely on the server.

File Naming

Each uploaded image should receive a unique generated filename.

Example

leaf_20260731_103015.jpg

---

# 17. Logging

The backend should maintain logs for:

• User Login

• User Logout

• Prediction Requests

• Prediction Errors

• AI Service Failures

• Admin Actions

• System Errors

---

# 18. API Best Practices

• Keep endpoints RESTful.

• Return consistent JSON responses.

• Validate every request.

• Never expose internal AI logic.

• Store prediction history after successful analysis.

• Return appropriate HTTP status codes.

• Use ISO 8601 timestamps.

• Keep frontend independent of AI implementation.

• Maintain backward compatibility when introducing future API versions.

# 19. API Communication Flow

GreenGuard follows a Client–Server architecture.

The frontend never communicates directly with AI modules.

All communication passes through the Django Backend.

---

## Authentication Flow

User

↓

Frontend (Next.js)

↓

POST /api/v1/auth/login/

↓

Django Backend

↓

PostgreSQL

↓

Generate JWT Tokens

↓

Set HttpOnly Cookies (tokens never in the response body)

↓

Browser Sends Cookies Automatically

---

## Prediction Flow

User Uploads Image

↓

Frontend

↓

POST /api/v1/predictions/analyze/

↓

Django Backend

↓

Validate Request

↓

Store Uploaded Image

↓

Call Module 1 — Disease Detection

↓

Retrieve Farm's Latest Persisted Module 2 (Soil & Nutrient Health) Result — not invoked live

↓

Call Module 3 — Weather Risk

↓

Save Prediction (Module 4 — Integrated Analysis Report: the three results side by side)

↓

Return Saved Report

↓

Frontend Displays Report

---

## Dashboard Flow

User Opens Dashboard

↓

GET /api/v1/dashboard/

↓

Django Backend

↓

PostgreSQL

↓

Return Dashboard Data

↓

Frontend Displays Dashboard

---

## History Flow

User Opens Prediction History

↓

GET /api/v1/history/

↓

Django Backend

↓

PostgreSQL

↓

Return Prediction History

↓

Frontend Displays History

---

## Notification Flow

User Opens Notifications

↓

GET /api/v1/notifications/

↓

Django Backend

↓

PostgreSQL

↓

Return Notifications

↓

Frontend Displays Notifications

---

# 20. Database Interaction

The backend is the only component allowed to access PostgreSQL.

Frontend

↓

REST API

↓

Django ORM

↓

PostgreSQL

AI modules never access the database directly.

---

# 21. Mock Development Mode

During frontend development, AI modules may not be available.

The backend should support Mock Mode.

Environment Variable

ENABLE_MOCK_AI=True

When enabled

• AI responses are returned from predefined JSON files.

• JSON structure must exactly match the AI contract.

When disabled

• Backend communicates with actual AI services.

No frontend changes should be required when switching between Mock Mode and Production Mode.

---

# 22. Development Environment

Frontend

Next.js

Backend

Django REST Framework

Database

PostgreSQL

Authentication

JWT

AI Frameworks

TensorFlow / PyTorch

Weather API

Open-Meteo, via the ai/Weather_Module Module 3 microservice (FastAPI + rule engine + optional LSTM forecast)

Version Control

Git

Repository

GitHub

---

# 23. Production Environment

Frontend

Next.js

Backend

Django

Database

PostgreSQL

Reverse Proxy

Nginx

Application Server

Gunicorn

Hosting

Cloud Platform (AWS, Azure, Railway, etc.)

HTTPS

SSL Enabled

---

# 24. API Design Principles

GreenGuard APIs must always be

• RESTful

• Stateless

• Secure

• Modular

• Scalable

• Consistent

• Maintainable

• Well Documented

---

# 25. Naming Conventions

Endpoints

Use lowercase.

Use hyphens when necessary.

Examples

/api/v1/auth/login/

/api/v1/history/

/api/v1/dashboard/

JSON Keys

Use snake_case.

Examples

recommended_crop

recommended_variety

fungal_disease_risk

heat_stress_risk

---

# 26. Complete Endpoint Summary

## Authentication

GET /api/v1/auth/csrf/

POST /api/v1/auth/register/

POST /api/v1/auth/login/

POST /api/v1/auth/logout/

POST /api/v1/auth/refresh/

POST /api/v1/auth/forgot-password/

POST /api/v1/auth/reset-password/

POST /api/v1/auth/change-password/

POST /api/v1/auth/verify-email/

POST /api/v1/auth/resend-verification/

---

## Farms

GET /api/v1/farms/

POST /api/v1/farms/

GET /api/v1/farms/{farm_id}/

PUT /api/v1/farms/{farm_id}/

DELETE /api/v1/farms/{farm_id}/

---

## User

GET /api/v1/profile/

PUT /api/v1/profile/

DELETE /api/v1/profile/

---

## Dashboard

GET /api/v1/dashboard/

GET /api/v1/dashboard/weather/

GET /api/v1/dashboard/recent-predictions/

GET /api/v1/dashboard/recommendations/

---

## Weather

GET /api/v1/weather/current/

---

## Predictions

POST /api/v1/predictions/analyze/

GET /api/v1/predictions/

GET /api/v1/predictions/{prediction_id}/

DELETE /api/v1/predictions/{prediction_id}/

---

## Module 2 — Soil & Nutrient Health

POST /api/v1/module2/analyze/

---

## History

GET /api/v1/history/

GET /api/v1/history/{prediction_id}/

DELETE /api/v1/history/{prediction_id}/

---

## Notifications

GET /api/v1/notifications/

PUT /api/v1/notifications/{notification_id}/read/

DELETE /api/v1/notifications/{notification_id}/

---

## Admin

GET /api/v1/admin/dashboard/

GET /api/v1/admin/users/

GET /api/v1/admin/users/{user_id}/

PUT /api/v1/admin/users/{user_id}/status/

DELETE /api/v1/admin/users/{user_id}/

GET /api/v1/admin/predictions/

DELETE /api/v1/admin/predictions/{prediction_id}/

GET /api/v1/admin/ai-monitoring/

GET /api/v1/admin/system-health/

GET /api/v1/admin/statistics/

---

# 27. Final Notes

This document is the official REST API specification for GreenGuard.

All frontend, backend, and AI development must follow this specification.

Changes to API endpoints, request formats, response formats, or JSON contracts must be documented and approved before implementation.

The JSON contracts defined for the AI modules are considered fixed interfaces and must not be modified without agreement between the backend and AI teams.

End of Document.

