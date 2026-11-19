"""整批打回的 HTTP 口子（2.20.0 卡§2，add-host-api 动线）：写令牌＋形状校验。

pending.py 已冻结（485 行只减不增），打回是独立请求族，另立兄弟路由挂进 main。
业务语义全在 core/pending/return_batch：未入库随批作废、已入库留库不动。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException

from app.core.pending import return_batch as core_return
from app.core.pending.db import BATCH_ID_RE, PendingError, PendingNotFound
from app.core.security import require_write_token

router = APIRouter(tags=["pending"])


@router.post(
    "/api/pending/return_batch",
    summary="整批打回文件收集框：源文件＋元数据原样交回，未入库作废、已入库留库",
    dependencies=[Depends(require_write_token)],
)
async def pending_return_batch(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是对象")
    batch_id = str(payload.get("batch_id") or "").strip()
    if not BATCH_ID_RE.match(batch_id):
        raise HTTPException(status_code=400, detail="批次编号不合法")
    try:
        return core_return.return_batch(batch_id)
    except PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PendingError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc