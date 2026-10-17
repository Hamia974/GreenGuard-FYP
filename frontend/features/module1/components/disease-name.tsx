"use client";

import { useMessages } from "next-intl";

import { labelFor } from "@/lib/i18n/labels";

/** "Yellow Rust" -> "yellow_rust": Module 1's display names map 1:1 onto its disease slugs. */
function slugFromDisplayName(displayName: string): string {
  return displayName
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
}

interface DiseaseNameProps {
  /** Module 1's own `display_name` -- shown as-is when no translation exists. */
  displayName: string;
  /** Module 1's stable `disease` slug, when the caller has it (preferred lookup key). */
  disease?: string;
}

/**
 * Localized disease name for a Module 1 result. Looks the name up in
 * messages/<locale>/diseases.json by the stable slug (ai/API_CONTRACT.md:
 * "use it to look up treatment advice, Urdu names, etc."). When the
 * localized name differs from the model's English display name, the
 * original is kept beside it so farmers and agronomists can cross-check.
 * The API value itself is never altered.
 */
export function DiseaseName({ displayName, disease }: DiseaseNameProps) {
  const messages = useMessages();
  const label = labelFor(
    messages.diseases,
    disease ?? slugFromDisplayName(displayName),
    displayName
  );

  if (label === displayName) return <>{displayName}</>;

  return (
    <>
      {label}{" "}
      <span lang="en" dir="ltr" className="text-[0.85em] font-normal opacity-70">
        ({displayName})
      </span>
    </>
  );
}
