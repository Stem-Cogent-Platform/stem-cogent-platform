import asyncio

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import close_database_connection
from app.core.redis import close_redis_connection
from app.main import app


@pytest.mark.asyncio
async def test_readiness_checks_postgres_and_redis_services() -> None:
    transport = ASGITransport(app=app)

    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/ready")

            for _ in range(15):
                if response.status_code == 200:
                    break
                await asyncio.sleep(1)
                response = await client.get("/health/ready")
    finally:
        await close_database_connection()
        await close_redis_connection()

    assert response.status_code == 200, response.text
    assert response.json() == {
        "status": "ready",
        "dependencies": {"postgres": "ok", "redis": "ok"},
    }
