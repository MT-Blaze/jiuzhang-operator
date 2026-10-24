"""健康检查。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app import __version__
from app.core.host_restart import boot_id

router = APIRouter(tags=["system"])


@router.get("/healthz", summary="健康检查")
async def healthz() -> dict[str, str]:
    """``boot_id`` 每次进程启动都换新：切库重启时前端据此确认「已是新进程」。"""
    return {
        "status": "ok",
        "service": "jiuzhang-operator",
        "version": __version__,
        "boot_id": boot_id(),
        "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
