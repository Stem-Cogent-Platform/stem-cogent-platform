FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 1000 --no-create-home appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app/ ./app/

RUN chmod -R a=rX /app

USER 1000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

CMD ["gunicorn", "app.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--workers", "2", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]
