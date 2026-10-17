import type { FarmLocation } from "./types";

/** Whitespace/case-insensitive form of an address, so trivial edits don't invalidate a location. */
export function normalizeAddress(address: string): string {
  return address.trim().replace(/\s+/g, " ").toLowerCase();
}

/** True when `location` still belongs to the address currently typed in the form. */
export function isLocationCurrent(location: FarmLocation | null, address: string): location is FarmLocation {
  if (!location) return false;
  return location.source === "device" || location.addressKey === normalizeAddress(address);
}
