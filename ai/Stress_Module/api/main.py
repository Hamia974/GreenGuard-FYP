"""FastAPI entry point for GreenGuard Module 2: Soil & Nutrient Analysis.

Module 2 is the only public endpoint. It orchestrates Module 2A (ML nutrient risk) and
Module 2B (pH/moisture/light rules) internally -- neither is reachable from outside.

How to run it (see README.md for full instructions):
    python main.py

The port comes from the PORT variable in .env (defaults to 8002 if unset). Once running,
open http://localhost:<PORT>/docs to test it interactively.
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

import module2a_service
from manifest import ArtifactIntegrityError
from orchestrator_service import analyze_soil
from schemas import Module2Request, SoilAnalysisResponse, UnsupportedCropResponse

logger = logging.getLogger(__name__)

# Load only Stress Module configuration. This prevents the repository-level
# Weather Module `.env` (which uses port 8001) from changing this service's
# default port.
load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env")
PORT = int(os.getenv("PORT", 8002))

# Missing artifacts, or artifacts that fail their manifest checksum.
MODEL_UNAVAILABLE_ERRORS = (FileNotFoundError, ArtifactIntegrityError)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Load and verify Module 2A's artifacts at boot rather than on the first request.

    Loading them lazily costs roughly 2.4s on the first call, which a farmer would
    otherwise wait through. This is best-effort: if the artifacts are missing or fail
    verification the service still starts and /predict reports 503, so a model problem
    never stops the health check from answering.
    """
    try:
        module2a_service.warm_up()
        logger.info("Module 2A artifacts pre-loaded (%s)", module2a_service.get_model_version())
    except MODEL_UNAVAILABLE_ERRORS as exc:
        logger.warning("Module 2A artifacts unavailable at startup: %s", exc)
    yield


app = FastAPI(
    title="GreenGuard - Soil & Nutrient Module (Module 2)",
    description="Internal AI microservice. Module 2A and 2B are internal-only.",
    version="1.1.0",
    lifespan=lifespan,
)


@app.get("/health")
def health_check():
    """Endpoint used by the Backend team for service availability checks."""
    return {"status": "ok", "service": "soil-nutrient-module"}


@app.post(
    "/predict",
    response_model=SoilAnalysisResponse | UnsupportedCropResponse,
    # The orchestrator omits `message` from a fully scored response. Without this the
    # response model would add it back as null, changing the documented JSON.
    response_model_exclude_unset=True,
)
def predict_soil_health(request: Module2Request):
    """Combined Module 2 prediction: nutrient risk + growing conditions + score."""
    try:
        return analyze_soil(request.model_dump())
    except MODEL_UNAVAILABLE_ERRORS as exc:
        # Surfaced as service-unavailable rather than a generic 500 so the cause is
        # obvious in deployment. The file-level detail goes to the log, not the client.
        logger.error("Module 2A artifacts unavailable: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Prediction Failed: model artifacts unavailable.",
        ) from exc


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # FastAPI's default HTTPException body is {"detail": ...}. Override it so every
    # error this service raises uses the one documented {"message": ...} shape, the
    # same as the generic handler below and the Weather module. Request-validation
    # failures (422) keep FastAPI's standard {"detail": [...]} body.
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error in %s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={"message": "Prediction Failed"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
