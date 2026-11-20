"""MinerU 云端识别：本地切好单题截图后整批发送、逐题回填。

绝不整卷上传，也绝不把别家题的结果套到这一道上：一批 N 份单题截图一次
申请上传地址，轮询按 data_id 认行，题↔结果一一对应。整批等待上限沿用
15 分钟口径；到点已回的行照回填，未回的行逐题显性失败账本，不整批作废。
超过单批上限时由 ``mineru_batching`` 拆批顺序发送，前一批回来才发下一批；
进度逐题写回批次路由，老师在底部日志里看得见「已回 N/M 题」。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable

from app.core.ingest.recognize import mineru_batching
from app.core.ai.platform import center as ai_center
from app.core.ingest.recognize import shared as recognize_shared

logger = logging.getLogger(__name__)

MINERU_WAIT_SECONDS = 900.0


async def run(batch_id: str, items: list[dict[str, Any]], indexes: list[int],
              binding: ai_center.TaskBinding | None,
              route: dict[str, Any],
              on_progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """整批发送 MinerU；返回成功下标，供调度员决定要不要再降级。"""
    if not indexes:
        return {"ok": True, "attempted": 0, "filled": 0, "filled_indexes": [],
                "detail": "没有需要交给 MinerU 的题"}
    if binding is None:
        return {"ok": False, "attempted": 0, "filled": 0, "filled_indexes": [],
                "detail": "没有可用的 MinerU 账号"}
    from app.core.ingest.service import build_documents

    total = len(indexes)
    prepared: list[tuple[int, int, bytes]] = []
    for position, index in enumerate(indexes, start=1):
        data = recognize_shared.item_image_bytes(items[index])
        if not data:
            continue
        prepared.append((position, index, data))
    filled_indexes: list[int] = []
    if prepared:
        rounds = mineru_batching.batch_count(len(prepared))
        note = ("已将 %d 题单题截图分 %d 批发送至 MinerU 云端解析..." % (len(prepared), rounds)
                if rounds > 1
                else "已将 %d 题单题截图整批发送至 MinerU 云端解析..." % len(prepared))
        logger.info(note)
        route["note"] = note
        _progress(on_progress, route)

        def poll_progress(settled: int, count: int) -> None:
            route["note"] = "MinerU 云端整批解析中：已回 %d/%d 题" % (settled, count)
            _progress(on_progress, route)

        def poll_batch(number: int, total_batches: int, _first: int, _last: int) -> None:
            route["note"] = "分批识别中（第 %d/%d 批）" % (number, total_batches)
            _progress(on_progress, route)

        outcomes = await asyncio.to_thread(
            mineru_batching.extract_in_batches,
            [("第%d题.png" % position, data) for position, _index, data in prepared],
            binding.base_url,
            binding.api_key,
            model=binding.model or "mineru",
            wait=MINERU_WAIT_SECONDS,
            on_progress=poll_progress,
            on_batch=poll_batch,
        )
        for (position, index, _data), outcome in zip(prepared, outcomes):
            if not outcome.get("ok"):
                route["note"] = "第 %d/%d 题 MinerU 没成功（%s），继续下一题。" % (
                    position, total, str(outcome.get("detail") or "")[:120])
                _progress(on_progress, route)
                continue
            documents, _notes = build_documents(str(outcome.get("markdown") or ""))
            if not documents:
                continue
            document = recognize_shared.merge_local(
                documents[0], items[index].get("question") or {})
            if recognize_shared.save_back(items[index], document, batch_id,
                                          "ingest.mineru"):
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