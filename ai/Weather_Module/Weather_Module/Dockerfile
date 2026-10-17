FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api/ ./api/
COPY models/ ./models/

WORKDIR /app/api

# Default; override at runtime with `docker run -e PORT=9000 ...` or
# `--env-file .env`. Explicitly invoking sh -c (exec form, one shell layer)
# so ${PORT} gets substituted -- a bare JSON-array CMD like
# ["uvicorn", ..., "--port", "${PORT}"] would pass the literal string
# "${PORT}" straight to uvicorn instead of expanding it, since no shell
# is involved to do that substitution.
ENV PORT=8001
EXPOSE 8001

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
