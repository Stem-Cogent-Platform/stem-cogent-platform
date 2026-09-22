FROM python:3.12.13-alpine3.23 AS builder

WORKDIR /build

RUN for i in 1 2 3; do apk add --no-cache build-base curl-dev && break || sleep 2; done

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12.13-alpine3.23 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN for i in 1 2 3; do apk upgrade --no-cache && apk add --no-cache libcurl && break || sleep 2; done \
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
