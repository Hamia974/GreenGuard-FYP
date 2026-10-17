"use client";

import { useMessages } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { labelFor } from "@/lib/i18n/labels";

/**
 * Maps the honest, non-fabricated status strings adminpanel.services
 * returns ("Healthy"/"Unhealthy"/"Degraded"/"Mock Mode"/"Online"/
 * "Unreachable"/"Connected"/"Active"/"Inactive") to a badge tone. Unknown
 * values -- e.g. Module 4's "Not used — integration layer", which is not a
 * service and never an outage -- still render (as the neutral "secondary"
 * tone) rather than being hidden: this must never silently swallow a status
 * the backend reports.
 */
const POSITIVE = new Set(["Healthy", "Online", "Connected", "Active"]);
const NEUTRAL = new Set(["Mock Mode"]);
const NEGATIVE = new Set(["Unhealthy", "Unreachable", "Degraded", "Inactive"]);

export function StatusBadge({ status }: { status: string }) {
  const messages = useMessages();
  const variant = POSITIVE.has(status)
    ? "success"
    : NEGATIVE.has(status)
      ? "error"
      : NEUTRAL.has(status)
        ? "warning"
        : "secondary";

  // Tone is decided from the raw backend value; only the visible text is localized
  // (unknown statuses still show verbatim).
  return <Badge variant={variant}>{labelFor(messages.admin.statuses, status)}</Badge>;
}
