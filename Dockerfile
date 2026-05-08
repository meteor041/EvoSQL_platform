# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
COPY assets/ ../assets/
RUN npm exec vite -- build

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8000

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY pyproject.toml requirements.txt ./
COPY src/ ./src/
COPY main.py ./
COPY --from=frontend-builder /app/frontend/dist/ ./src/evosql_platform/app/static/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

RUN mkdir -p /app/data /app/upload && chown -R app:app /app
USER app

EXPOSE 8000
VOLUME ["/app/data", "/app/upload"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/audit/logs?limit=1', timeout=3).read()" || exit 1

CMD ["sh", "-c", "uvicorn evosql_platform.app.main:app --host ${HOST} --port ${PORT}"]
