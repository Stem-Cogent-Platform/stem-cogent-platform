from fastapi import APIRouter, Response, status

from app.core.database import check_database_connection
from app.core.redis import check_redis_connection

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def ready(response: Response) -> dict[str, object]:
    postgres_status = await check_database_connection()
    redis_status = await check_redis_connection()
    dependencies = {"postgres": postgres_status, "redis": redis_status}

    if all(dependency_status == "ok" for dependency_status in dependencies.values()):
        return {"status": "ready", "dependencies": dependencies}

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "not_ready", "dependencies": dependencies}
