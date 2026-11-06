"""大模型识别：单题截图并发交给视觉模型，按局部或全量两种口径回填。

只看单题截图，绝不整卷上传；每道题独立回填，一道失败不影响别家。
出网前必须先有「视觉识别(OCR)」任务指派，缺密钥时如实失败、不编题。
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core import ai_center, ai_recognize
from app.core.recognize import recognize_shared

OCR_CONCURRENCY = 5


def scope_indexes(items: list[dict[str, Any]], scope: str,
                  report: dict[str, Any] | None = None) -> list[int]:
    """本次要交给模型的下标：all 指整批，bad 只指本地体检出的坏题。"""
    if scope == "all":
        return list(range(len(items)))
    bad = (report or {}).get("bad_indexes") or []
    return [int(index) for index in bad if isinstance(index, int) and 0 <= index < len(items)]


async def run(batch_id: str, items: list[dict[str, Any]], scope: str = "bad",
              report: dict[str, Any] | None = None) -> dict[str, Any]:
    """并发识别指定范围；返回成功下标，供调度员决定是否继续降级。"""
    binding = ai_center.resolve_task("ocr")
    indexes = scope_indexes(items, scope, report)
    if not indexes:
        return {"ok": True, "attempted": 0, "filled": 0, "filled_indexes": [],
                "detail": "没有需要交给模型识别的题"}
    if not binding.is_configured:
        return {"ok": False, "attempted": 0, "filled": 0, "filled_indexes": [],
                "detail": "「视觉识别(OCR)」还没指派可用模型"}
    semaphore = asyncio.Semaphore(OCR_CONCURRENCY)

    async def one(index: int) -> bool:
        item = items[index]
        uri = recognize_shared.first_image_uri(item)
        if not uri:
            return False
        async with semaphore:
            try:
                outcome = await ai_recognize.recognize(
                    [uri], context=recognize_shared.context_of(item), task="ocr")
            except Exception:  # noqa: BLE001 - 出网失败只算这一道没回来
                return False
        if not outcome.get("ok") or not outcome.get("question"):
            return False
        document = recognize_shared.document_from_ai(
            outcome["question"], item.get("question") or {})
        return recognize_shared.save_back(item, document, batch_id, "ingest.ai_fill")

    results = await asyncio.gather(*(one(index) for index in indexes),
                                   return_exceptions=True)
    filled_indexes = [index for index, result in zip(indexes, results) if result is True]
    filled = len(filled_indexes)
    detail = "" if filled == len(indexes) else (
        "只有 %d/%d 道回来了" % (filled, len(indexes)))
    return {
        "ok": filled > 0,
        "attempted": len(indexes),
        "filled": filled,
        "filled_indexes": filled_indexes,
        "detail": detail,
    }
