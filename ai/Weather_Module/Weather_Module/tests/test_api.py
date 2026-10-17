"""
test_api.py
-----------
Run with:  pytest tests/test_api.py -v

Uses MOCK weather responses so tests run instantly without needing
real internet access.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "api"))

import requests
from fastapi.testclient import TestClient
import main
import weather_service

client = TestClient(main.app)

FAKE_WEATHER = {
    "temperature": 33.4,
    "humidity": 84.0,
    "rainfall_last_7_days_mm": 2.3,
    "wind_speed": 9.1,
}


def make_hourly(conducive_day_indices=(), hot_day_indices=(), num_days=4):
    """Builds a fake hourly Open-Meteo block. The last day index is
    treated as 'today' and dropped by the real parsing logic."""
    dates = [f"2026-08-{i:02d}" for i in range(1, num_days + 1)]
    times, temps, hums = [], [], []
    for i, date in enumerate(dates):
        if i in conducive_day_indices:
            temp, hum = 25, 85
        elif i in hot_day_indices:
            temp, hum = 38, 40
        else:
            temp, hum = 15, 40
        for hour in range(24):
            times.append(f"{date}T{hour:02d}:00")
            temps.append(temp)
            hums.append(hum)
    return {"time": times, "temperature_2m": temps, "relative_humidity_2m": hums}


def make_daily(dates, rainfall_values):
    return {"time": dates, "precipitation_sum": rainfall_values}


def make_full_response(hourly=None, daily=None, temperature=33.4, humidity=84, wind=9.1):
    return {
        "current": {"temperature_2m": temperature, "relative_humidity_2m": humidity, "wind_speed_10m": wind},
        "daily": daily or {"precipitation_sum": [0.0] * 8, "time": [f"2026-08-{i:02d}" for i in range(1, 9)]},
        "hourly": hourly or make_hourly(),
    }


def clear_state():
    weather_service._weather_cache.clear()


# ---------------------------------------------------------------------
# API-LEVEL TESTS
# ---------------------------------------------------------------------

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_success():
    with patch("main.fetch_weather", return_value={
        **FAKE_WEATHER,
        "_consecutive_conducive_days": 0,
        "_consecutive_heat_days": 0,
        "_consecutive_dry_days": 0,
    }):
        response = client.post(
            "/predict",
            json={"latitude": 31.5204, "longitude": 74.3587, "farm_id": "farm_001"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["farm_id"] == "farm_001"
    assert "weather" in body
    assert "risk_assessment" in body
    assert body["risk_assessment"]["fungal_disease_risk"] in ["Low", "Moderate", "High"]
    assert isinstance(body["risk_assessment"]["fungal_disease_reason"], str) and body["risk_assessment"]["fungal_disease_reason"]
    assert isinstance(body["risk_assessment"]["heat_stress_reason"], str) and body["risk_assessment"]["heat_stress_reason"]
    assert isinstance(body["risk_assessment"]["drought_reason"], str) and body["risk_assessment"]["drought_reason"]
    assert body["units"] == {
        "temperature": "celsius",
        "humidity": "percent",
        "rainfall_last_7_days_mm": "mm",
        "wind_speed": "m/s",
    }
    # internal-only keys must never leak into the response Backend receives
    assert "_consecutive_conducive_days" not in body["weather"]
    # no _daily_summary in this mocked fetch_weather -> LSTM forecast has
    # nothing to work with and must degrade to null, not fail the request
    assert body["forecast"] is None
    assert body["predicted_risk_assessment"] is None


# ---------------------------------------------------------------------
# LSTM FORECAST ADD-ON (additive: must never affect the core prediction)
# ---------------------------------------------------------------------

def test_predict_includes_forecast_when_available():
    with patch("main.fetch_weather", return_value={**FAKE_WEATHER, "_consecutive_conducive_days": 0,
                                                     "_consecutive_heat_days": 0, "_consecutive_dry_days": 0}), \
         patch("main.forecast_and_assess", return_value=(
             {"temperature": 31.8, "humidity": 62.7, "rainfall_mm": 1.9},
             {
                 "fungal_disease_risk": "Low", "fungal_disease_reason": "test reason",
                 "heat_stress_risk": "Low", "heat_stress_reason": "test reason",
                 "drought_risk": "High", "drought_reason": "test reason",
             },
         )):
        response = client.post(
            "/predict",
            json={"latitude": 31.5204, "longitude": 74.3587, "farm_id": "farm_001"},
        )
    body = response.json()
    assert body["forecast"] == {"temperature": 31.8, "humidity": 62.7, "rainfall_mm": 1.9}
    assert body["predicted_risk_assessment"]["drought_risk"] == "High"
    # the LSTM add-on must never change the existing, rule-based risk_assessment
    assert body["risk_assessment"]["fungal_disease_risk"] in ["Low", "Moderate", "High"]


def test_predict_survives_forecast_failure():
    """If the LSTM model/scaler is missing or prediction throws for any
    reason, /predict must still return 200 with the core contract intact
    -- the forecast add-on is best-effort, not load-bearing."""
    with patch("main.fetch_weather", return_value={**FAKE_WEATHER, "_consecutive_conducive_days": 0,
                                                     "_consecutive_heat_days": 0, "_consecutive_dry_days": 0}), \
         patch("main.forecast_and_assess", side_effect=RuntimeError("model file missing")):
        response = client.post(
            "/predict",
            json={"latitude": 31.5204, "longitude": 74.3587, "farm_id": "farm_001"},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["forecast"] is None
    assert body["predicted_risk_assessment"] is None
    assert body["risk_assessment"]["fungal_disease_risk"] in ["Low", "Moderate", "High"]


def test_predict_invalid_latitude():
    response = client.post(
        "/predict",
        json={"latitude": 999, "longitude": 74.3587, "farm_id": "farm_001"},
    )
    assert response.status_code == 422


def test_predict_missing_fields():
    response = client.post("/predict", json={"latitude": 31.5204})
    assert response.status_code == 422


def test_weather_service_failure_returns_500():
    with patch("main.fetch_weather", side_effect=Exception("weather API down")):
        response = client.post(
            "/predict",
            json={"latitude": 31.5204, "longitude": 74.3587, "farm_id": "farm_001"},
        )
    assert response.status_code == 500
    body = response.json()
    # Regression guard: this is an HTTPException raised inside main.py, which
    # FastAPI's built-in handler would format as {"detail": ...} by default --
    # a DIFFERENT shape than the {"message": ...} contract documented for
    # every other 500. main.py's custom http_exception_handler exists
    # specifically to keep this path consistent with that contract.
    assert "message" in body
    assert "detail" not in body


# ---------------------------------------------------------------------
# CONSECUTIVE-DAY LOGIC (fungal, heat, drought)
# ---------------------------------------------------------------------

def test_consecutive_fungal_days():
    hourly = make_hourly(conducive_day_indices={0, 1, 2})  # last 3 full days all conducive
    daily = {"precipitation_sum": [0.0] * 4, "time": [f"2026-08-{i:02d}" for i in range(1, 5)]}
    summary = weather_service._build_daily_summary(hourly, daily)
    result = weather_service._consecutive_days(summary, weather_service._is_fungal_conducive)
    assert result == 3


def test_consecutive_fungal_days_streak_broken():
    hourly = make_hourly(conducive_day_indices={2})  # only the day right before "today"
    daily = {"precipitation_sum": [0.0] * 4, "time": [f"2026-08-{i:02d}" for i in range(1, 5)]}
    summary = weather_service._build_daily_summary(hourly, daily)
    result = weather_service._consecutive_days(summary, weather_service._is_fungal_conducive)
    assert result == 1


def test_consecutive_hot_days():
    hourly = make_hourly(hot_day_indices={1, 2})  # 2 of the last 3 full days
    daily = {"precipitation_sum": [0.0] * 4, "time": [f"2026-08-{i:02d}" for i in range(1, 5)]}
    summary = weather_service._build_daily_summary(hourly, daily)
    result = weather_service._consecutive_days(summary, weather_service._is_hot_day)
    assert result == 2


def test_consecutive_dry_days():
    hourly = make_hourly()  # temp/humidity content irrelevant for this test
    dates = [f"2026-08-{i:02d}" for i in range(1, 5)]
    # rainfall per day (oldest -> newest): 5mm, 0mm, 0.2mm, 0mm -> last 3 full days = [0, 0.2, 0]
    daily = {"precipitation_sum": [5.0, 0.0, 0.2, 0.0], "time": dates}
    summary = weather_service._build_daily_summary(hourly, daily)
    result = weather_service._consecutive_days(summary, weather_service._is_dry_day)
    assert result == 2  # both 0.2mm and 0mm count as "dry" (<1mm)


# ---------------------------------------------------------------------
# RISK REASONS (each reason must name the condition that actually fired)
# ---------------------------------------------------------------------

def test_reason_cites_todays_humidity_for_high_fungal():
    result = weather_service.assess_risk(temperature=22, humidity=90, rainfall_7d=50)
    assert result["fungal_disease_risk"] == "High"
    assert "90" in result["fungal_disease_reason"] and "22" in result["fungal_disease_reason"]


def test_reason_cites_consecutive_days_for_high_fungal():
    result = weather_service.assess_risk(temperature=10, humidity=30, rainfall_7d=50, consecutive_conducive_days=3)
    assert result["fungal_disease_risk"] == "High"
    assert "3 days" in result["fungal_disease_reason"]


def test_reason_cites_temperature_for_high_heat():
    result = weather_service.assess_risk(temperature=42, humidity=30, rainfall_7d=50)
    assert result["heat_stress_risk"] == "High"
    assert "42" in result["heat_stress_reason"]


def test_reason_cites_rainfall_for_high_drought():
    result = weather_service.assess_risk(temperature=25, humidity=30, rainfall_7d=5)
    assert result["drought_risk"] == "High"
    assert "5" in result["drought_reason"]


def test_reason_present_for_low_risk():
    result = weather_service.assess_risk(temperature=20, humidity=30, rainfall_7d=50)
    assert result["fungal_disease_risk"] == "Low"
    assert result["heat_stress_risk"] == "Low"
    assert result["drought_risk"] == "Low"
    assert result["fungal_disease_reason"] and result["heat_stress_reason"] and result["drought_reason"]


# ---------------------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------------------

def test_validation_rejects_impossible_temperature():
    try:
        weather_service._validate_current_reading(temperature=999, humidity=50, wind_speed=5)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_validation_rejects_impossible_humidity():
    try:
        weather_service._validate_current_reading(temperature=25, humidity=150, wind_speed=5)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_validation_accepts_normal_reading():
    weather_service._validate_current_reading(temperature=32.5, humidity=60, wind_speed=4.2)
    # no exception raised = pass


def test_validation_rejects_mismatched_hourly_arrays():
    bad_hourly = {"time": ["2026-08-01T00:00"], "temperature_2m": [20, 21], "relative_humidity_2m": [50]}
    try:
        weather_service._validate_hourly_arrays(bad_hourly)
        assert False, "expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------
# CACHING
# ---------------------------------------------------------------------

def test_weather_cache_avoids_duplicate_calls():
    clear_state()
    mock_resp = MagicMock()
    mock_resp.json.return_value = make_full_response()
    mock_resp.raise_for_status.return_value = None

    with patch("weather_service.requests.Session.get", return_value=mock_resp) as mocked_get:
        weather_service.fetch_weather(12.34, 56.78)
        weather_service.fetch_weather(12.34, 56.78)  # should reuse cache
        assert mocked_get.call_count == 1


def test_fetch_failure_raises_when_no_cache():
    clear_state()
    with patch("weather_service.requests.Session.get", side_effect=requests.exceptions.ConnectionError("network down")):
        try:
            weather_service.fetch_weather(1.23, 4.56)
            assert False, "expected an exception since there is no cache and the live fetch failed"
        except requests.exceptions.ConnectionError:
            pass


# ---------------------------------------------------------------------
# RATE LIMIT HANDLING
# ---------------------------------------------------------------------

def test_rate_limit_raises_clear_error():
    clear_state()
    mock_resp = MagicMock()
    mock_resp.status_code = 429
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=mock_resp)

    with patch("weather_service.requests.Session.get", return_value=mock_resp):
        try:
            weather_service.fetch_weather(7.77, 8.88)
            assert False, "expected RuntimeError to be raised"
        except RuntimeError as e:
            assert "rate limit" in str(e).lower()
