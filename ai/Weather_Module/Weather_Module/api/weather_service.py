"""
weather_service.py
-------------------
Fetches real-time weather from Open-Meteo and turns it into risk
assessments. No machine learning here on purpose — Module 3 is
rule-based per the architecture doc.

On top of the basic fetch, this adds:
  - A simple in-memory TTL CACHE, so repeated requests for the same
    farm within a few minutes don't re-hit the network.
  - Input/output VALIDATION (sanity-checks provider values, checks
    hourly arrays are well-formed before using them).
  - HTTP RETRY with backoff for transient failures / rate limits.
  - CONSECUTIVE-DAY analysis for ALL THREE risk types (fungal, heat,
    drought), not just fungal, since sustained conditions matter for
    heat stress and drought too.
"""

import time
from collections import defaultdict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# ---------------------------------------------------------------------
# CACHE
# ---------------------------------------------------------------------
CACHE_TTL_SECONDS = 15 * 60  # how long a cache entry is "fresh"

_weather_cache: dict = {}  # key -> (saved_at_timestamp, result_dict)

# NOTE for production: this is a single-process in-memory cache — fine
# for this FYP/demo deployment. If this module ever runs as multiple
# server processes, replace with a shared cache like Redis.


def _cache_key(latitude: float, longitude: float) -> tuple:
    return (round(latitude, 2), round(longitude, 2))


# ---------------------------------------------------------------------
# HTTP SESSION WITH RETRY + RATE-LIMIT HANDLING
# ---------------------------------------------------------------------
def _build_session() -> requests.Session:
    retry_strategy = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        respect_retry_after_header=True,
        allowed_methods=["GET"],
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
    return session


# ---------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------
def _validate_current_reading(temperature, humidity, wind_speed) -> None:
    """Sanity-check the provider's numbers are physically plausible.
    Protects us from silently passing through garbage/corrupted data."""
    if not (-60 <= temperature <= 60):
        raise ValueError(f"Implausible temperature from weather provider: {temperature}°C")
    if not (0 <= humidity <= 100):
        raise ValueError(f"Implausible humidity from weather provider: {humidity}%")
    if not (0 <= wind_speed <= 150):
        raise ValueError(f"Implausible wind speed from weather provider: {wind_speed} m/s")


def _validate_hourly_arrays(hourly: dict) -> None:
    """Ensure the hourly time/temperature/humidity arrays are the same
    length before we zip them together — a mismatch (partial outage on
    the provider's end) would otherwise silently produce wrong daily
    averages instead of failing loudly."""
    lengths = {
        "time": len(hourly.get("time", [])),
        "temperature_2m": len(hourly.get("temperature_2m", [])),
        "relative_humidity_2m": len(hourly.get("relative_humidity_2m", [])),
    }
    if len(set(lengths.values())) != 1:
        raise ValueError(f"Weather provider returned mismatched hourly data arrays: {lengths}")


# ---------------------------------------------------------------------
# PUBLIC ENTRY POINT
# ---------------------------------------------------------------------
def fetch_weather(latitude: float, longitude: float) -> dict:
    """
    Returns weather data for Backend, plus internal-only keys
    (prefixed with `_`) that main.py strips before building the
    response. Serves from the TTL cache when fresh, otherwise fetches
    live from Open-Meteo.
    """
    key = _cache_key(latitude, longitude)

    cached = _weather_cache.get(key)
    if cached and (time.time() - cached[0]) < CACHE_TTL_SECONDS:
        return dict(cached[1])

    result = _fetch_live(latitude, longitude)
    _weather_cache[key] = (time.time(), result)
    return dict(result)


def _fetch_live(latitude: float, longitude: float) -> dict:
    """Actually calls Open-Meteo and builds the result dict. Raises on
    any failure or implausible data — caller decides how to handle it."""
    session = _build_session()
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "hourly": "temperature_2m,relative_humidity_2m",
        "daily": "precipitation_sum",
        "past_days": 7,
        "forecast_days": 1,
        "wind_speed_unit": "ms",
        "timezone": "auto",
    }

    try:
        response = session.get(OPEN_METEO_URL, params=params, timeout=15)
        response.raise_for_status()
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status == 429:
            raise RuntimeError(
                "Weather provider rate limit reached even after retries. Try again shortly."
            ) from exc
        raise
    finally:
        session.close()

    data = response.json()

    current = data["current"]
    temperature = current["temperature_2m"]
    humidity = current["relative_humidity_2m"]
    wind_speed = current["wind_speed_10m"]
    _validate_current_reading(temperature, humidity, wind_speed)

    daily_precip = data["daily"]["precipitation_sum"][:-1]  # drop today (partial day)
    rainfall_last_7_days_mm = sum(v for v in daily_precip if v is not None)
    if rainfall_last_7_days_mm < 0:
        raise ValueError(f"Implausible negative rainfall total: {rainfall_last_7_days_mm}mm")

    _validate_hourly_arrays(data["hourly"])
    daily_summary = _build_daily_summary(data["hourly"], data["daily"])

    consecutive_fungal = _consecutive_days(daily_summary, _is_fungal_conducive)
    consecutive_heat = _consecutive_days(daily_summary, _is_hot_day)
    consecutive_dry = _consecutive_days(daily_summary, _is_dry_day)

    return {
        "temperature": round(temperature, 1),
        "humidity": round(humidity, 1),
        "rainfall_last_7_days_mm": round(rainfall_last_7_days_mm, 1),
        "wind_speed": round(wind_speed, 1),
        "_consecutive_conducive_days": consecutive_fungal,
        "_consecutive_heat_days": consecutive_heat,
        "_consecutive_dry_days": consecutive_dry,
        "_daily_summary": daily_summary,
    }


# ---------------------------------------------------------------------
# DAILY SUMMARY + CONSECUTIVE-DAY LOGIC (shared by all 3 risk types)
# ---------------------------------------------------------------------
def _build_daily_summary(hourly: dict, daily: dict, lookback_days: int = 7) -> list:
    """
    Combines hourly temp/humidity averages with the daily rainfall
    totals into one list of {date, avg_temp, avg_humidity, rainfall}
    dicts, sorted oldest -> newest, EXCLUDING today (incomplete day).
    """
    times = hourly["time"]
    temps = hourly["temperature_2m"]
    humidities = hourly["relative_humidity_2m"]

    daily_temps = defaultdict(list)
    daily_humidities = defaultdict(list)
    for t, temp, hum in zip(times, temps, humidities):
        date_str = t.split("T")[0]
        if temp is not None:
            daily_temps[date_str].append(temp)
        if hum is not None:
            daily_humidities[date_str].append(hum)

    all_dates_sorted = sorted(daily_temps.keys())
    if not all_dates_sorted:
        return []

    today_str = all_dates_sorted[-1]
    past_full_dates = [d for d in all_dates_sorted if d != today_str][-lookback_days:]

    # Map rainfall totals (from the `daily` block) to the same dates.
    # Open-Meteo's daily.time array should line up with past_days+forecast_days.
    daily_dates = daily.get("time", [])
    daily_rain = daily.get("precipitation_sum", [])
    rain_by_date = dict(zip(daily_dates, daily_rain))

    summary = []
    for date_str in past_full_dates:
        if not daily_temps[date_str] or not daily_humidities[date_str]:
            continue
        summary.append({
            "date": date_str,
            "avg_temp": sum(daily_temps[date_str]) / len(daily_temps[date_str]),
            "avg_humidity": sum(daily_humidities[date_str]) / len(daily_humidities[date_str]),
            "rainfall": rain_by_date.get(date_str, 0) or 0,
        })
    return summary


def _is_fungal_conducive(day: dict) -> bool:
    return (15 <= day["avg_temp"] <= 30) and (day["avg_humidity"] >= 80)


def _is_hot_day(day: dict) -> bool:
    return day["avg_temp"] > 35


def _is_dry_day(day: dict) -> bool:
    return day["rainfall"] < 1


def _consecutive_days(daily_summary: list, predicate, lookback_days: int = 3) -> int:
    """Counts how many of the most recent `lookback_days` full days, in
    a row (most recent first), satisfy `predicate`. Stops at the first
    day that doesn't qualify."""
    recent = daily_summary[-lookback_days:]
    consecutive = 0
    for day in reversed(recent):
        if predicate(day):
            consecutive += 1
        else:
            break
    return consecutive


# ---------------------------------------------------------------------
# RISK RULES
# ---------------------------------------------------------------------
def assess_risk(
    temperature: float,
    humidity: float,
    rainfall_7d: float,
    consecutive_conducive_days: int = 0,
    consecutive_heat_days: int = 0,
    consecutive_dry_days: int = 0,
) -> dict:
    """
    IMPROVED DEFAULT thresholds — still PLACEHOLDERS pending your
    biotech-validated numbers. All three risk types now consider both
    today's snapshot AND recent multi-day trends, since sustained
    conditions matter more than a single reading for all of them:

    - Fungal: needs sustained humidity + moderate temp over days to
      establish, not just one humid moment.
    - Heat stress: cumulative heat exposure over consecutive hot days
      causes more crop damage than one hot day.
    - Drought: consecutive dry days is a stronger signal than a 7-day
      rainfall sum alone (a sum can hide "one shower, then bone dry").
    """
    # Fungal disease risk
    today_very_humid = (15 <= temperature <= 30) and humidity >= 85
    if today_very_humid or consecutive_conducive_days >= 3:
        fungal_disease_risk = "High"
        if today_very_humid:
            fungal_disease_reason = (
                f"Today's temperature ({temperature}°C) and humidity ({humidity}%) both fall in the "
                f"fungal-conducive range (15-30°C, humidity 85% or higher)."
            )
        else:
            fungal_disease_reason = (
                f"The last {consecutive_conducive_days} days in a row have had conducive conditions "
                f"(15-30°C, humidity 80% or higher), long enough for fungal pathogens to establish."
            )
    elif humidity >= 65 or consecutive_conducive_days >= 1:
        fungal_disease_risk = "Moderate"
        if humidity >= 65:
            fungal_disease_reason = (
                f"Humidity is {humidity}%, above the 65% threshold that raises fungal risk, though "
                f"today's temperature/humidity combination isn't in the high-risk range."
            )
        else:
            fungal_disease_reason = (
                f"{consecutive_conducive_days} of the last 3 days had fungal-conducive conditions "
                f"(15-30°C, humidity 80% or higher)."
            )
    else:
        fungal_disease_risk = "Low"
        fungal_disease_reason = (
            f"Humidity ({humidity}%) is below the 65% risk threshold and no day in the last 3 was "
            f"fungal-conducive."
        )

    # Heat stress risk
    if temperature > 40 or consecutive_heat_days >= 3:
        heat_stress_risk = "High"
        if temperature > 40:
            heat_stress_reason = f"Current temperature ({temperature}°C) exceeds 40°C, the high heat-stress threshold."
        else:
            heat_stress_reason = (
                f"The last {consecutive_heat_days} days in a row averaged above 35°C, indicating "
                f"sustained heat exposure."
            )
    elif temperature > 35 or consecutive_heat_days >= 1:
        heat_stress_risk = "Moderate"
        if temperature > 35:
            heat_stress_reason = f"Current temperature ({temperature}°C) exceeds 35°C, the moderate heat-stress threshold."
        else:
            heat_stress_reason = f"{consecutive_heat_days} of the last 3 days averaged above 35°C."
    else:
        heat_stress_risk = "Low"
        heat_stress_reason = (
            f"Current temperature ({temperature}°C) is at or below 35°C and no recent day averaged "
            f"above that threshold."
        )

    # Drought risk
    if rainfall_7d < 10 or consecutive_dry_days >= 5:
        drought_risk = "High"
        if rainfall_7d < 10:
            drought_reason = f"Only {rainfall_7d}mm of rain fell in the last 7 days, below the 10mm high-drought threshold."
        else:
            # NOTE: consecutive_dry_days can currently reach at most 3 (see
            # _consecutive_days' lookback_days default below), so this branch
            # is unreachable as written -- flagged, not fixed, since changing
            # the threshold changes real behavior and needs a call on intent.
            drought_reason = (
                f"{consecutive_dry_days} of the last 3 days in a row were dry (under 1mm each), "
                f"indicating sustained drought."
            )
    elif rainfall_7d < 25 or consecutive_dry_days >= 3:
        drought_risk = "Moderate"
        if rainfall_7d < 25:
            drought_reason = f"{rainfall_7d}mm of rain fell in the last 7 days, below the 25mm moderate-drought threshold."
        else:
            drought_reason = (
                f"All of the last 3 days were dry (under 1mm rain each), even though the 7-day total "
                f"({rainfall_7d}mm) is at or above 25mm."
            )
    else:
        drought_risk = "Low"
        drought_reason = (
            f"{rainfall_7d}mm of rain fell in the last 7 days, at or above the 25mm threshold, with "
            f"no sustained dry streak."
        )

    return {
        "fungal_disease_risk": fungal_disease_risk,
        "fungal_disease_reason": fungal_disease_reason,
        "heat_stress_risk": heat_stress_risk,
        "heat_stress_reason": heat_stress_reason,
        "drought_risk": drought_risk,
        "drought_reason": drought_reason,
    }
