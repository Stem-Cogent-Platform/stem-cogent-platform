from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.cil import router as cil_router
from app.api.v1.auth_sessions import router as auth_sessions_router
from app.api.v1.billing import router as billing_router
from app.api.v1.compliance import router as compliance_router
from app.api.v1.context import router as context_router
from app.api.v1.health import router as health_router
from app.api.v1.product import router as product_router
from app.api.v1.realtime import router as realtime_router
from app.api.v1.reviews import router as reviews_router
from app.core.config import get_settings
from app.core.database import close_database_connection
from app.core.logging import (
    bind_log_context,
    configure_logging,
    get_logger,
    reset_log_context,
)
from app.core.redis import close_redis_connection
from app.core.runtime_config import validate_runtime_configuration
from app.core.tracing import configure_tracing


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    validate_runtime_configuration()
    yield
    await close_database_connection()
    await close_redis_connection()


settings = get_settings()
configure_logging()
logger = get_logger(__name__)
is_production = settings.ENVIRONMENT in {"prod", "production"}

app = FastAPI(
    title="Stem Cogent API",
    version="0.1.0",
    docs_url=None if is_production else "/api/v1/docs",
    openapi_url=None if is_production else "/api/v1/openapi.json",
    lifespan=lifespan,
)
configure_tracing(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_PUBLIC_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Correlation-ID"],
)


def _request_identifier(value: str | None) -> str:
    """Accept bounded printable IDs or generate an opaque request UUID."""

    if value and len(value) <= 128 and value.isascii() and value.isprintable():
        return value
    return str(uuid4())


@app.middleware("http")
async def add_request_context(request: Request, call_next) -> Response:
    request_id = _request_identifier(request.headers.get("x-request-id"))
    correlation_header = request.headers.get("x-correlation-id")
    correlation_id = _request_identifier(correlation_header) if correlation_header else request_id
    tokens = bind_log_context(request_id=request_id, correlation_id=correlation_id)
    started = perf_counter()

    try:
        response: Response = await call_next(request)
        duration_ms = round((perf_counter() - started) * 1000, 3)
        logger.info(
            "HTTP request completed",
            extra={
                "duration_ms": duration_ms,
                "status_code": response.status_code,
                "http_method": request.method,
                "http_path": request.url.path,
            },
        )
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        return response
    except Exception:
        logger.exception(
            "HTTP request failed",
            extra={
                "duration_ms": round((perf_counter() - started) * 1000, 3),
                "status_code": 500,
                "error_code": "UNHANDLED_REQUEST_ERROR",
                "http_method": request.method,
                "http_path": request.url.path,
            },
        )
        raise
    finally:
        reset_log_context(tokens)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response: Response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.include_router(health_router)
app.include_router(auth_sessions_router)
app.include_router(billing_router)
app.include_router(compliance_router)
# SC-DOC-006 defines /api/v1 as the global API base. Keep the older
# unprefixed context routes as hidden compatibility aliases while clients
# migrate to the canonical contract.
app.include_router(context_router, prefix="/api/v1")
app.include_router(context_router, include_in_schema=False)
app.include_router(product_router)
app.include_router(realtime_router)
app.include_router(cil_router)
app.include_router(reviews_router)
