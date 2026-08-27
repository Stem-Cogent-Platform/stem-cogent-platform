FROM python:3.12.13-alpine3.23 AS builder

WORKDIR /build

RUN apk add --no-cache build-base curl-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12.13-alpine3.23 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apk upgrade --no-cache \
    && apk add --no-cache libcurl \
    && addgroup -g 1000 -S workeruser \
    && adduser -u 1000 -S -D -H -G workeruser workeruser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app/ ./app/
RUN chmod -R a=rX /app \
    && chmod 1777 /tmp

VOLUME ["/tmp"]

USER 1000

CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
