"""MinerU 云识别超量分批调度：按批顺序发送，前一批回来才发下一批。

2026-11-20 主公拍板：单批 40 页稳定；80 张虽在每日额度内，但第二批会进
云端排队、行为不可控。因此超过单批上限时由本模块拆批，逐批调用
``mineru_extract.extract_batch``（每批仍是一次申请、一次轮询），按原页序
合并结果。单批（页数 ≤ 上限）原样透传，不多一次请求、不改返回结构。

某批整批失败（该批每份都没成功）立即停发后续批：失败批逐份保留原有
失败文案并加「第 X/Y 批失败」前缀；未发送批逐份显性失败，不静默跳过、
不换引擎。批内个别题失败不算批失败，照旧逐题回填。
"""

from __future__ import annotations

import time
from typing import Any, Callable

from app.core.ingest.recognize import mineru_extract

ProgressFn = Callable[[int, int], None]
BatchFn = Callable[[int, int, int, int], None]


def batch_count(total: int) -> int:
    size = mineru_extract.BATCH_MAX_FILES
    return 0 if total <= 0 else (total + size - 1) // size


def extract_in_batches(
        files: list[tuple[str, bytes]], base_url: str, token: str, *,
        model: str = "", wait: float = mineru_extract.MAX_WAIT_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        on_progress: ProgressFn | None = None,
        on_batch: BatchFn | None = None) -> list[dict[str, Any]]:
    """返回与 files 同序的 outcome 列表；页数不超上限时与直接提交完全一致。

    ``on_batch(第几批, 总批数, 起始页序号, 结束页序号)`` 仅在真正拆批时回调，
    供调用方写「分批识别中（第 X/Y 批）」进度；``on_progress`` 的已回份数
    跨批累计，调用方无需自己偏移。
    """
    size = mineru_extract.BATCH_MAX_FILES
    total = len(files)
    if total <= 0:
        return []
    if total <= size:
        return mineru_extract.extract_batch(
            files, base_url, token, model=model, wait=wait, sleep=sleep,
            clock=clock, on_progress=on_progress)
    rounds = batch_count(total)
    merged: list[dict[str, Any]] = []
    for number, start in enumerate(range(0, total, size), start=1):
        chunk = files[start:start + size]
        if on_batch is not None:
            on_batch(number, rounds, start + 1, start + len(chunk))

        def relay(settled: int, _count: int, offset: int = start) -> None:
            if on_progress is not None:
                on_progress(offset + settled, total)

        chunk_outcomes = mineru_extract.extract_batch(
            chunk, base_url, token, model=model, wait=wait, sleep=sleep,
            clock=clock, on_progress=relay)
        merged.extend(chunk_outcomes)
        if not any(outcome.get("ok") for outcome in chunk_outcomes):
            merged[start:start + len(chunk_outcomes)] = [
                dict(outcome, detail="第 %d/%d 批失败：%s" % (
                    number, rounds, outcome.get("detail") or ""))
                for outcome in chunk_outcomes
            ]
            for later in range(number + 1, rounds + 1):
                later_start = (later - 1) * size
                later_end = min(later * size, total)
                merged.extend(
                    {"ok": False, "detail": "第 %d/%d 批未发送（第 %d/%d 批识别失败，已停止发送）"
                     % (later, rounds, number, rounds)}
                    for _ in range(later_end - later_start))
            break
    return merged
