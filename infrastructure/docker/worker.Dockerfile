FROM python:3.12.13-alpine3.23 AS builder

WORKDIR /build

RUN for i in 1 2 3; do apk add --no-cache build-base curl-dev && break || sleep 2; done

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt
RUN mkdir -p /opt/tiktoken && PYTHONPATH=/install/lib/python3.12/site-packages TIKTOKEN_CACHE_DIR=/opt/tiktoken python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

FROM python:3.12.13-alpine3.23 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN for i in 1 2 3; do apk upgrade --no-cache && apk add --no-cache libcurl && break || sleep 2; done \
    && addgroup -g 1000 -S workeruser \
    && adduser -u 1000 -S -D -H -G workeruser workeruser

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --from=builder /opt/tiktoken /opt/tiktoken
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken
COPY app/ ./app/
RUN chmod -R a=rX /app \
    && chmod 1777 /tmp

VOLUME ["/tmp"]

USER 1000

CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
