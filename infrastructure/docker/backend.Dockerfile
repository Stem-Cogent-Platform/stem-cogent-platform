FROM python:3.12.13-alpine3.23 AS builder

WORKDIR /build

RUN apk add --no-cache build-base curl-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12.13-alpine3.23 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk add --no-cache libcurl \
    && addgroup -g 1000 -S appuser \
    && adduser -u 1000 -S -D -H -G appuser appuser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/
COPY app/ ./app/

RUN chmod -R a=rX /app \
    && chmod 1777 /tmp

# ECS Fargate bind mounts otherwise default to root:root mode 0755. Declaring
# the same path as a Docker volume makes ECS preserve the image-defined 1777
# permissions when it mounts writable ephemeral storage over the read-only
# root filesystem.
VOLUME ["/tmp"]

USER 1000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health/ready', timeout=5).close()"

CMD ["gunicorn", "app.main:app", "--worker-class", "uvicorn.workers.UvicornWorker", "--logger-class", "app.core.logging.StructuredGunicornLogger", "--workers", "2", "--bind", "0.0.0.0:8000", "--access-logfile", "-", "--error-logfile", "-", "--log-level", "info"]
