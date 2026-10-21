"""健康检查。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app import __version__

router = APIRouter(tags=["system"])


@router.get("/healthz", summary="健康检查")
async def healthz() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "jiuzhang-operator",
        "version": __version__,
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
