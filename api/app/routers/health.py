from fastapi import APIRouter, Response, status

from app.deps import Db

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def liveness() -> dict[str, str]:
    """The process is up. The host uses this to decide whether to restart us."""
    return {"status": "ok"}


@router.get("/readyz")
async def readiness(db: Db, response: Response) -> dict[str, str]:
    """The process can reach its database. The uptime monitor watches this."""
    if await db.is_ready():
        return {"status": "ok", "database": "ok"}
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"status": "degraded", "database": "unreachable"}
