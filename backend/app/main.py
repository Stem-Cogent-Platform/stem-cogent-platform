from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

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
is_production = settings.ENVIRONMENT == "production"

app = FastAPI(
    title="Stem Cogent API",
    version="0.1.0",
    docs_url=None if is_production else "/api/v1/docs",
    openapi_url=None if is_production else "/api/v1/openapi.json",
    lifespan=lifespan,
)
app.include_router(health_router)
