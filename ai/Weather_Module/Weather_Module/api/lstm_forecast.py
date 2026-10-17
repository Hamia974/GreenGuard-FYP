"""
lstm_forecast.py
-----------------
Additive forecast feature. Predicts tomorrow's weather from the same
7-day daily_summary weather_service.py already builds for its consecutive
-day risk logic, then reuses assess_risk() UNMODIFIED on the forecasted
day to produce a forward-looking "predicted risk".

This does not touch or replace the existing current-conditions
risk_assessment in any way. If the model/scaler files are missing or a
prediction fails for any reason, main.py catches it and simply omits the
forecast/predicted_risk_assessment fields (they're Optional in the
schema) rather than failing the whole /predict request over it.
"""

import json
import os

import torch

from lstm_model import WeatherLSTM, SEQUENCE_LENGTH
from weather_service import assess_risk, _consecutive_days, _is_fungal_conducive, _is_hot_day, _is_dry_day

MODEL_DIR = os.path.join(os.path.dirname(__file__), "..", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "weather_lstm.pt")
SCALER_PATH = os.path.join(MODEL_DIR, "scaler.json")

_model = None
_scaler = None


def _load():
    global _model, _scaler
    if _model is not None:
        return
    with open(SCALER_PATH) as f:
        _scaler = json.load(f)
    model = WeatherLSTM()
    model.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
    model.eval()
    _model = model


def _normalize(day: dict) -> list:
    mean, std = _scaler["mean"], _scaler["std"]
    return [
        (day["avg_temp"] - mean[0]) / std[0],
        (day["avg_humidity"] - mean[1]) / std[1],
        (day["rainfall"] - mean[2]) / std[2],
    ]


def _denormalize(vec: list) -> dict:
    mean, std = _scaler["mean"], _scaler["std"]
    return {
        "avg_temp": vec[0] * std[0] + mean[0],
        "avg_humidity": min(100.0, max(0.0, vec[1] * std[1] + mean[1])),
        "rainfall": max(0.0, vec[2] * std[2] + mean[2]),
    }


def predict_next_day(daily_summary: list) -> dict:
    """Takes weather_service.py's own 7-day daily_summary and returns a
    predicted {avg_temp, avg_humidity, rainfall} for the day after the
    most recent one in it."""
    if len(daily_summary) < SEQUENCE_LENGTH:
        raise ValueError(f"Need {SEQUENCE_LENGTH} days of history for a forecast, got {len(daily_summary)}")
    _load()
    window = daily_summary[-SEQUENCE_LENGTH:]
    x = torch.tensor([[_normalize(day) for day in window]], dtype=torch.float32)
    with torch.no_grad():
        prediction = _model(x)[0].tolist()
    return _denormalize(prediction)


def forecast_and_assess(daily_summary: list) -> tuple:
    """Returns (forecast_dict, predicted_risk_dict).

    forecast_dict matches the ForecastData schema (temperature/humidity/
    rainfall_mm). predicted_risk_dict is produced by calling the existing,
    unmodified assess_risk() on the forecasted day rolled into the same
    7-day trailing window used for today's risk_assessment -- so "forecast
    risk" is computed with exactly the same rules as "current risk",
    just one day further ahead.
    """
    forecast_day = predict_next_day(daily_summary)

    rolled_window = daily_summary[-(SEQUENCE_LENGTH - 1):] + [forecast_day]
    consecutive_conducive = _consecutive_days(rolled_window, _is_fungal_conducive)
    consecutive_heat = _consecutive_days(rolled_window, _is_hot_day)
    consecutive_dry = _consecutive_days(rolled_window, _is_dry_day)
    rainfall_7d = sum(day["rainfall"] for day in rolled_window)

    # Round before assess_risk() (not after) so its reason strings match the
    # 1-decimal precision used everywhere else in the API -- assess_risk()
    # embeds these values verbatim into fungal_disease_reason etc.
    predicted_risk = assess_risk(
        temperature=round(forecast_day["avg_temp"], 1),
        humidity=round(forecast_day["avg_humidity"], 1),
        rainfall_7d=round(rainfall_7d, 1),
        consecutive_conducive_days=consecutive_conducive,
        consecutive_heat_days=consecutive_heat,
        consecutive_dry_days=consecutive_dry,
    )

    forecast = {
        "temperature": round(forecast_day["avg_temp"], 1),
        "humidity": round(forecast_day["avg_humidity"], 1),
        "rainfall_mm": round(forecast_day["rainfall"], 1),
    }
    return forecast, predicted_risk
