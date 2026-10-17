export interface Farm {
  farmId: string;
  farmName: string;
  address: string;
  latitude: number;
  longitude: number;
  createdAt: string;
  updatedAt: string;
}

export interface FarmPayload {
  farmName: string;
  address: string;
  latitude: number;
  longitude: number;
}

/** One candidate from POST /farms/geocode/ -- the farmer must confirm it. */
export interface GeocodeResult {
  label: string;
  latitude: number;
  longitude: number;
}

/**
 * The coordinates the form will submit, plus where they came from. Address
 * lookups and saved farm coordinates are tied to `addressKey` (the address
 * they were found for): once the farmer edits the address they no longer
 * count, so stale coordinates can never be submitted. Device GPS does not
 * depend on the typed address.
 */
export interface FarmLocation {
  latitude: number;
  longitude: number;
  label: string | null;
  source: "saved" | "address" | "device";
  addressKey: string;
}
