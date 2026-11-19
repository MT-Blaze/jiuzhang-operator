"""审核重认的 HTTP 口子（T6 §4，add-host-api 动线）：写令牌＋输入校验。

一次点击只送一个席：core 在 recognize/reidentify，失败成因进批次失败清单
retryable；这里只做鉴权与形状校验，业务失败以 ok=False＋人话 detail 回报
（席位未就绪/无坐标/转写失败都照念，不偷换）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.core.ingest.recognize import reidentify as recognize_reidentify
from app.core.pending.db import PENDING_ID_RE, PendingNotFound
from app.core.security import require_write_token

router = APIRouter(tags=["pending"])


@router.get(
    "/api/pending/reidentify/spans",
    summary="审核重认公式块清单（只读）：有坐标逐块回报，无坐标回空列表",
)
async def reidentify_spans(pending_id: str = Query("")) -> dict[str, Any]:
    pid = pending_id.strip()
    if not PENDING_ID_RE.match(pid):
        raise HTTPException(status_code=400, detail="中转站编号不合法")
    try:
        return await recognize_reidentify.list_spans(pid)
    except PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/api/pending/reidentify",
    summary="审核重认：同张题图裁公式块/整题送选中席，原位替换（老师点击发起）",
    dependencies=[Depends(require_write_token)],
)
async def pending_reidentify(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="请求体必须是对象")
    pending_id = str(payload.get("pending_id") or "").strip()
    if not PENDING_ID_RE.match(pending_id):
        raise HTTPException(status_code=400, detail="中转站编号不合法")
    seat = str(payload.get("seat") or "").strip()
    if not seat or len(seat) > 80:
        raise HTTPException(status_code=400, detail="席位 id 不合法")
    target = str(payload.get("target") or "question").strip()
    if target not in ("question", "formula"):
        raise HTTPException(status_code=400, detail="target 只认 question / formula")
    try:
        span_index = int(payload.get("span_index") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="公式块序号必须是整数") from None
    if not 0 <= span_index <= 31:
        raise HTTPException(status_code=400, detail="公式块序号超出范围")
    try:
        return await recognize_reidentify.reidentify(pending_id, seat, target, span_index)
    except PendingNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc