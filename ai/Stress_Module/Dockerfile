# GreenGuard Module 2 — Soil & Nutrient Analysis
#
#   Build:   docker build -t greenguard-module2 .
#   Run:     docker run -p 8002:8002 greenguard-module2
#   Verify:  docker run --rm greenguard-module2 python -m pytest -p no:cacheprovider /app/tests/test_deployment.py

FROM python:3.13-slim

# XGBoost links against the OpenMP runtime, which the slim base image does not ship.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# The service only reads its files, so it runs as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser

COPY api/ ./api/
COPY models/ ./models/
# tests/ and samples/ let the deployment check run inside the image, against the exact
# libraries and model files that will serve traffic. They add under 50 KB.
COPY tests/ ./tests/
COPY samples/ ./samples/

USER appuser
WORKDIR /app/api

# Default port; override at runtime with `docker run -e PORT=9000 ...` or `--env-file .env`.
# `sh -c` inside the exec form is what lets ${PORT} expand -- a bare JSON-array CMD would
# pass the literal string "${PORT}" to uvicorn. Set WEB_CONCURRENCY to run more than one
# worker process (uvicorn reads it; each worker holds its own copy of the models, ~200 MB).
ENV PORT=8002
EXPOSE 8002

# The slim image has no curl, so the check uses Python's standard library.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('PORT', '8002'), timeout=4)"

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
