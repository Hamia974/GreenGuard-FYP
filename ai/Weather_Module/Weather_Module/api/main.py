"""
main.py
-------
This is the actual REST API. Run this file and it starts a live web
server that the Django Backend (or you, for testing) can send requests to.

How to run it (see README.md for full instructions):
    python main.py

The port comes from the PORT variable in .env (defaults to 8001 if unset).
Once running, open http://localhost:<PORT>/docs in your browser to test
it interactively.
"""

import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from schemas import WeatherRequest, WeatherRiskResponse, WeatherData, RiskAssessment, ForecastData
from weather_service import fetch_weather, assess_risk
from lstm_forecast import forecast_and_assess

load_dotenv()
PORT = int(os.getenv("PORT", 8001))

app = FastAPI(
    title="GreenGuard - Weather Risk Module (Module 3)",
    description="Internal AI microservice. Not exposed to the frontend directly.",
    version="1.12.0",
)


@app.get("/health")
def health_check():
    """Simple endpoint so the Backend team can check the service is alive."""
    return {"status": "ok", "service": "weather-risk-module"}


@app.post("/predict", response_model=WeatherRiskResponse)
def predict_weather_risk(request: WeatherRequest):
    """
    Main endpoint. Backend sends latitude/longitude (and optionally
    farm_id) -> we return live weather + risk assessment.

    Matches the exact JSON contract in REST_API_SPEC.md, section
    "AI Module 3 - Weather Risk Engine".
    """
    try:
        weather_raw = fetch_weather(request.latitude, request.longitude)
    except Exception as exc:
        # Per REST_API_SPEC.md error responses: weather service failure -> 500
        raise HTTPException(
            status_code=500,
            detail="Prediction Failed: weather service unavailable.",
        ) from exc

    # Internal-only signals (not part of the public JSON contract) used
    # to decide risk based on sustained multi-day conditions.
    consecutive_conducive_days = weather_raw.pop("_consecutive_conducive_days", 0)
    consecutive_heat_days = weather_raw.pop("_consecutive_heat_days", 0)
    consecutive_dry_days = weather_raw.pop("_consecutive_dry_days", 0)
    daily_summary = weather_raw.pop("_daily_summary", [])
    weather = weather_raw

    risk = assess_risk(
        temperature=weather["temperature"],
        humidity=weather["humidity"],
        rainfall_7d=weather["rainfall_last_7_days_mm"],
        consecutive_conducive_days=consecutive_conducive_days,
        consecutive_heat_days=consecutive_heat_days,
        consecutive_dry_days=consecutive_dry_days,
    )

    # LSTM forecast is additive and best-effort: a missing/broken model
    # must never take down the core (rule-based) prediction above.
    forecast, predicted_risk = None, None
    try:
        forecast, predicted_risk = forecast_and_assess(daily_summary)
    except Exception:
        pass

    response = WeatherRiskResponse(
        farm_id=request.farm_id,
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        weather=WeatherData(**weather),
        risk_assessment=RiskAssessment(**risk),
        forecast=ForecastData(**forecast) if forecast else None,
        predicted_risk_assessment=RiskAssessment(**predicted_risk) if predicted_risk else None,
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # FastAPI's own HTTPException handler defaults to {"detail": ...} and
    # takes priority over generic_error_handler below (it's registered for
    # the exact HTTPException class), which would otherwise make our two
    # error paths -- an HTTPException raised deliberately (e.g. weather
    # service unavailable) vs. any other uncaught exception -- return two
    # different JSON shapes for the same documented 500 contract. Override
    # it so every error response uses the one documented {"message": ...}
    # shape, regardless of which path failed.
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"message": "Prediction Failed"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
