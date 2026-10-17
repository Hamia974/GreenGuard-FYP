import { AxiosError } from "axios";

interface ApiErrorBody {
  success: false;
  message: string;
  errors?: Record<string, string[]>;
}

/** Text used when the backend gave no message, or could not be reached. */
export interface ApiErrorFallbacks {
  generic: string;
  network: string;
  /** HTTP 429 -- DRF's throttle response carries no `message`. */
  rateLimited: string;
}

const DEFAULT_FALLBACKS: ApiErrorFallbacks = {
  generic: "Something went wrong. Please try again.",
  network: "Unable to reach the server. Please check your connection.",
  rateLimited: "Too many attempts. Please wait a minute and try again.",
};

/**
 * Extracts the friendly message + field errors from a REST_API_SPEC.md error envelope.
 * Components should call this through `useParseApiError()` (lib/i18n), which
 * supplies the fallbacks in the active language.
 */
export function parseApiError(
  error: unknown,
  fallbacks: ApiErrorFallbacks = DEFAULT_FALLBACKS
): {
  message: string;
  fieldErrors: Record<string, string>;
} {
  if (error instanceof AxiosError && error.response?.status === 429) {
    return { message: fallbacks.rateLimited, fieldErrors: {} };
  }

  if (error instanceof AxiosError && error.response?.data) {
    const body = error.response.data as Partial<ApiErrorBody>;
    const fieldErrors: Record<string, string> = {};
    if (body.errors) {
      for (const [field, messages] of Object.entries(body.errors)) {
        if (messages?.length) fieldErrors[field] = messages[0];
      }
    }
    return {
      message: body.message ?? fallbacks.generic,
      fieldErrors,
    };
  }

  return {
    message: fallbacks.network,
    fieldErrors: {},
  };
}
