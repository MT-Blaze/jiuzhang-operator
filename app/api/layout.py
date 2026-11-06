"""本地 YOLO 模型仓库的 HTTP 口子：查状态、按需下载。

查状态只读；下载是写操作且会出网，必须由老师点击后带写令牌发起。
下载地址只来自插件目录的 ``model_config.json``，请求体只能选 full / quantized。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.layout import layout_model_store as store
from app.core.security import require_write_token

router = APIRouter(tags=["layout"])


@router.get("/api/layout/models/status", summary="本地 YOLO 模型与硬件状态")
def models_status() -> dict[str, Any]:
    return store.status()


@router.post(
    "/api/layout/models/download",
    status_code=202,
    summary="按需下载本地 YOLO 模型（满血版 / 量化版）",
    dependencies=[Depends(require_write_token)],
)
def models_download(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是 JSON 对象")
    try:
        return store.start_download(str(payload.get("kind") or ""))
    except store.ModelStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
