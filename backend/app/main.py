from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request, Response

from app.api.v1.health import router as health_router
from app.core.config import get_settings
from app.core.database import close_database_connection
from app.core.redis import close_redis_connection


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_database_connection()
    await close_redis_connection()


settings = get_settings()
is_production = settings.ENVIRONMENT in {"prod", "production"}

app = FastAPI(
    title="Stem Cogent API",
    version="0.1.0",
    docs_url=None if is_production else "/api/v1/docs",
    openapi_url=None if is_production else "/api/v1/openapi.json",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response: Response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.include_router(health_router)
