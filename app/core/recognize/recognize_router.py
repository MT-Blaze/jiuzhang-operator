"""识别引擎总调度：本地永远第一，之后按选择逐级降级。

- 自动：local → ai → mineru（本地无坏题就停；有坏题只补坏题，坏题率 ≥30% 转全量）
- 全量OCR：local → ai（整批）→ mineru
- MinerU：local → mineru（跳过 AI）
"""

from __future__ import annotations

from typing import Any, Callable

from app.core import ai_center
from app.core.recognize import recognize_ai, recognize_local, recognize_mineru, recognize_shared

RECOGNIZE_AUTO = "auto"
RECOGNIZE_FULL_OCR = "full_ocr"
RECOGNIZE_MINERU = "mineru"
RECOGNIZE_ENGINES = (RECOGNIZE_AUTO, RECOGNIZE_FULL_OCR, RECOGNIZE_MINERU)
BAD_RATE_THRESHOLD = 0.30

_PLANS = {
    RECOGNIZE_AUTO: ("local", "ai", "mineru"),
    RECOGNIZE_FULL_OCR: ("local", "ai", "mineru"),
    RECOGNIZE_MINERU: ("local", "mineru"),
}


# 老插件只会发四通道名：映射到新的识别引擎，旧调用方不必跟着改。
_LEGACY_CHANNELS = {
    "auto": RECOGNIZE_AUTO,
    "local_ai": RECOGNIZE_AUTO,
    "full_ocr": RECOGNIZE_FULL_OCR,
    "mineru": RECOGNIZE_MINERU,
}


def normalize_engine(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if text in RECOGNIZE_ENGINES else RECOGNIZE_AUTO


def from_legacy_channel(value: Any) -> str:
    """四通道老口径 → 识别引擎；认不出就当自动。"""
    return _LEGACY_CHANNELS.get(str(value or "").strip().lower(), RECOGNIZE_AUTO)


def plan(engine: Any) -> tuple[str, ...]:
    return _PLANS[normalize_engine(engine)]


async def fill_batch(batch_id: str, items: list[dict[str, Any]], engine: str,
                     report: dict[str, Any], route: dict[str, Any],
                     on_progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """按选择跑完整条瀑布流，把结果写进批次路由并返回它。"""
    picked = normalize_engine(engine)
    total = len(items)
    rate = float(report.get("rate") or 0.0)
    local = recognize_local.probe(items, report)
    if not local["bad_indexes"] and picked == RECOGNIZE_AUTO:
        route["mode"] = "local"
        route["note"] = "本地提取 %d 题未发现坏题，无需调用 AI。" % total
        route["phase"] = "done"
        route["done"] = True
        return route
    full = picked == RECOGNIZE_FULL_OCR or (
        picked == RECOGNIZE_AUTO and rate >= BAD_RATE_THRESHOLD)
    pending = list(range(total)) if full or picked == RECOGNIZE_MINERU else local["bad_indexes"]
    ai = mineru = None
    if pending:
        for step in plan(picked)[1:]:
            if not pending:
                break
            if step == "ai":
                ai = await recognize_shared.guard(recognize_ai.run, batch_id, items,
                                                  "all" if full else "bad", report)
                pending = recognize_shared.remaining(pending, ai)
            else:
                binding = ai_center.find_mineru()
                if binding is None:
                    mineru = {"ok": False, "attempted": 0, "filled": 0,
                              "filled_indexes": [],
                              "detail": "没有可用的 MinerU 账号", "binding": False}
                    break
                mineru = await recognize_shared.guard(
                    recognize_mineru.run, batch_id, items, pending, binding,
                    route, on_progress)
                mineru["binding"] = True
                pending = recognize_shared.remaining(pending, mineru)
    route["mode"] = ("mineru" if picked == RECOGNIZE_MINERU
                     else "full_ocr" if full else "local" if not local["bad_indexes"]
                     else "partial_ai")
    route["note"] = recognize_shared.note_for(
        picked, full, rate, ai, mineru, total, pending, BAD_RATE_THRESHOLD)
    route["phase"] = "done"
    route["done"] = True
    return route
