"""Forward geocoding for the Farm form: address text -> candidate coordinates.

The frontend never calls a geocoding provider itself -- it calls
POST /api/v1/farms/geocode/ (see views.FarmGeocodeView), so any provider
API key stays server-side. Results are only *candidates*: the farmer must
pick/confirm one, and the chosen coordinates are then saved through the
unchanged Farm create/update endpoints.

Two providers, selected by GEOCODING_PROVIDER:

* ``open_meteo`` (default) -- Open-Meteo's keyless Geocoding API (GeoNames
  data, good coverage of Pakistani villages/towns). It searches place NAMES,
  not full postal addresses, so the free-text address is split into its
  comma-separated parts and searched part by part, and the remaining parts
  (district, tehsil, province...) are used to rank the matches. Free for
  non-commercial use only (https://open-meteo.com/en/terms).
* ``google`` -- Google Maps Platform Geocoding API. Understands full
  free-form addresses and landmarks; needs GOOGLE_MAPS_GEOCODING_API_KEY
  (a server key, restricted to the Geocoding API).
"""

import hashlib
import logging
import re

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("greenguard")

MAX_RESULTS = 5
# Each address part may cost one provider request; bounds worst-case latency.
MAX_PARTS_SEARCHED = 4
SUPPORTED_LANGUAGES = {"en", "ur"}
_CACHE_TTL_SECONDS = 60 * 60 * 24

OPEN_METEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
GOOGLE_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Words farmers commonly put around a place name that are not part of it.
_FILLER_WORDS = re.compile(
    r"\b(village|vill|mouza|mauza|moza|tehsil|tahsil|district|distt|dist|"
    r"union council|uc|near|nearby|post office|p\.?o)\b\.?",
    re.IGNORECASE,
)
# Province / territory names: useful context for ranking, but far too broad
# to locate a farm on their own.
_REGION_NAMES = {
    "punjab", "sindh", "sind", "balochistan", "baluchistan", "khyber pakhtunkhwa",
    "kpk", "kp", "gilgit baltistan", "gilgit-baltistan", "azad kashmir", "ajk",
    "islamabad capital territory", "ict",
}
# Country / province-level matches are far too coarse to locate a farm.
_TOO_VAGUE_OPEN_METEO_CODES = {"PCLI", "ADM1"}
_TOO_VAGUE_GOOGLE_TYPES = {"country", "administrative_area_level_1"}


class GeocodingError(Exception):
    """The provider is unreachable, misconfigured, or returned an unusable response."""


def geocode_address(address: str, language: str = "en") -> list[dict]:
    """Return up to MAX_RESULTS ``{"label", "latitude", "longitude"}``
    candidates for ``address``, best match first. An empty list means
    nothing usable was found. Raises GeocodingError on provider failure."""
    language = language if language in SUPPORTED_LANGUAGES else "en"
    provider = settings.GEOCODING_PROVIDER
    normalized = " ".join(address.split()).lower()
    cache_key = "geocode:" + hashlib.sha256(
        f"{provider}|{language}|{settings.GEOCODING_COUNTRY_CODE}|{normalized}".encode()
    ).hexdigest()

    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    if provider == "google":
        results = _geocode_google(address, language)
    elif provider == "open_meteo":
        results = _geocode_open_meteo(address, language)
    else:
        logger.error("Unknown GEOCODING_PROVIDER %r.", provider)
        raise GeocodingError("Location service is not configured.")

    if results:
        cache.set(cache_key, results, _CACHE_TTL_SECONDS)
    return results


def _candidate(label: str, latitude, longitude) -> dict:
    return {
        "label": label,
        "latitude": round(float(latitude), 8),
        "longitude": round(float(longitude), 8),
    }


def _get_json(url: str, params: dict) -> dict:
    try:
        response = requests.get(
            url, params=params, timeout=settings.GEOCODING_REQUEST_TIMEOUT_SECONDS
        )
    except requests.RequestException as exc:
        logger.error("Geocoding request failed: %s", exc)
        raise GeocodingError("Location service is temporarily unavailable.") from exc

    if response.status_code >= 400:
        logger.error("Geocoding provider returned HTTP %s", response.status_code)
        raise GeocodingError("Location service is temporarily unavailable.")

    try:
        return response.json()
    except ValueError as exc:
        logger.error("Geocoding provider returned malformed JSON: %s", exc)
        raise GeocodingError("Location service is temporarily unavailable.") from exc


# --------------------------------------------------------------------------
# Open-Meteo
# --------------------------------------------------------------------------

def _address_parts(address: str) -> list[str]:
    parts = []
    for raw in re.split(r"[,،\n;]+", address):
        part = " ".join(_FILLER_WORDS.sub(" ", raw).split())
        if len(part) >= 2 and part.lower() not in ("pakistan", "pk"):
            parts.append(part)
    return parts


def _open_meteo_label(item: dict) -> str:
    pieces = [item.get("name"), item.get("admin3"), item.get("admin2"), item.get("admin1"), item.get("country")]
    label = []
    for piece in pieces:
        if piece and piece not in label:
            label.append(piece)
    return ", ".join(label)


def _context_score(item: dict, context: list[str]) -> int:
    """How many of the other address parts (district, tehsil, province...)
    appear in this match's administrative names."""
    admin_text = " ".join(
        str(item.get(key) or "") for key in ("admin1", "admin2", "admin3", "admin4")
    ).lower()
    return sum(1 for part in context if part.lower() in admin_text)


def _matches_query(item: dict, part: str) -> bool:
    """Open-Meteo also returns fuzzy matches ("Punjab" -> "Chak Number Two");
    keep only places whose name actually contains what the farmer typed.
    Skipped for non-Latin queries, whose matches may come back under an
    English name."""
    if not part.isascii():
        return True
    return part.lower() in str(item.get("name") or "").lower()


def _geocode_open_meteo(address: str, language: str) -> list[dict]:
    parts = _address_parts(address)
    # Most specific part first (farmers usually write village, then district,
    # then province); the first part that matches anything anchors the search.
    for index, part in enumerate(parts[:MAX_PARTS_SEARCHED]):
        if part.lower() in _REGION_NAMES:
            continue
        params = {"name": part, "count": 10, "language": language, "format": "json"}
        if settings.GEOCODING_COUNTRY_CODE:
            params["countryCode"] = settings.GEOCODING_COUNTRY_CODE
        data = _get_json(OPEN_METEO_URL, params)

        items = [
            item
            for item in data.get("results") or []
            if item.get("feature_code") not in _TOO_VAGUE_OPEN_METEO_CODES
            and _matches_query(item, part)
            and item.get("latitude") is not None
            and item.get("longitude") is not None
        ]
        if not items:
            continue

        context = parts[:index] + parts[index + 1:]
        # sorted() is stable, so equally-scored matches keep the provider's
        # own relevance (population) order.
        items = sorted(items, key=lambda item: _context_score(item, context), reverse=True)
        return [
            _candidate(_open_meteo_label(item), item["latitude"], item["longitude"])
            for item in items[:MAX_RESULTS]
        ]
    return []


# --------------------------------------------------------------------------
# Google Maps Platform
# --------------------------------------------------------------------------

def _geocode_google(address: str, language: str) -> list[dict]:
    if not settings.GOOGLE_MAPS_GEOCODING_API_KEY:
        logger.error("GEOCODING_PROVIDER=google but GOOGLE_MAPS_GEOCODING_API_KEY is not set.")
        raise GeocodingError("Location service is not configured.")

    params = {
        "address": address,
        "key": settings.GOOGLE_MAPS_GEOCODING_API_KEY,
        "language": language,
    }
    if settings.GEOCODING_COUNTRY_CODE:
        params["region"] = settings.GEOCODING_COUNTRY_CODE.lower()
        params["components"] = f"country:{settings.GEOCODING_COUNTRY_CODE}"

    data = _get_json(GOOGLE_URL, params)
    api_status = data.get("status")
    if api_status == "ZERO_RESULTS":
        return []
    if api_status != "OK":
        # Never log the request URL -- it carries the API key.
        logger.error("Google Geocoding returned status %s", api_status)
        raise GeocodingError("Location service is temporarily unavailable.")

    results = []
    for item in data.get("results") or []:
        if _TOO_VAGUE_GOOGLE_TYPES.intersection(item.get("types") or []):
            continue
        location = (item.get("geometry") or {}).get("location") or {}
        if location.get("lat") is None or location.get("lng") is None:
            continue
        results.append(_candidate(item.get("formatted_address", ""), location["lat"], location["lng"]))
    return results[:MAX_RESULTS]
