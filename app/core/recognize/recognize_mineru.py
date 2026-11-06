"""MinerU 云端识别：一张单题截图一次请求，回填只动那一道。

绝不整卷上传，也绝不把别家题的结果套到这一道上。单题等待放宽到
15 分钟；进度逐题写回批次路由，老师在底部日志里看得见排到第几题。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from app.core import ai_center, mineru_extract
from app.core.recognize import recognize_shared

logger = logging.getLogger(__name__)

MINERU_WAIT_SECONDS = 900.0


async def run(batch_id: str, items: list[dict[str, Any]], indexes: list[int],
              binding: ai_center.TaskBinding | None,
              route: dict[str, Any],
              on_progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """逐题发送 MinerU；返回成功下标，供调度员决定要不要再降级。"""
    if not indexes:
        return {"ok": True, "attempted": 0, "filled": 0, "filled_indexes": [],
                "detail": "没有需要交给 MinerU 的题"}
    if binding is None:
        return {"ok": False, "attempted": 0, "filled": 0, "filled_indexes": [],
                "detail": "没有可用的 MinerU 账号"}
    from app.core.ingest import build_documents

    filled_indexes: list[int] = []
    total = len(indexes)
    for position, index in enumerate(indexes, start=1):
        item = items[index]
        note = "正在将第 %d 题发送至 MinerU 云端解析..." % position
        logger.info(note)
        route["note"] = note
        _progress(on_progress, route)
        data = recognize_shared.item_image_bytes(item)
        if not data:
            continue
        outcome = await asyncio.to_thread(
            mineru_extract.extract,
            "第%d题.png" % position,
            data,
            binding.base_url,
            binding.api_key,
            model=binding.model or "mineru",
            wait=MINERU_WAIT_SECONDS,
        )
        if not outcome.get("ok"):
            route["note"] = "第 %d/%d 题 MinerU 没成功（%s），继续下一题。" % (
                position, total, str(outcome.get("detail") or "")[:120])
            _progress(on_progress, route)
            continue
        documents, _notes = build_documents(str(outcome.get("markdown") or ""))
        if not documents:
            continue
        document = recognize_shared.merge_local(
            documents[0], item.get("question") or {})
        if recognize_shared.save_back(item, document, batch_id, "ingest.mineru"):
            filled_indexes.append(index)
    filled = len(filled_indexes)
    return {
        "ok": filled > 0,
        "attempted": total,
        "filled": filled,
        "filled_indexes": filled_indexes,
        "detail": "" if filled == total else ("只有 %d/%d 道回来了" % (filled, total)),
    }


def _progress(callback: Callable[[dict[str, Any]], None] | None,
              route: dict[str, Any]) -> None:
    if callback is None:
        return
    try:
        callback(route)
    except Exception:  # noqa: BLE001 - 进度写不进去不该打断识别
        pass
