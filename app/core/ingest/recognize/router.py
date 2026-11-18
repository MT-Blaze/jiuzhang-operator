"""识别引擎总调度：自动走瀑布，选了谁就只走谁（2026-11-18 主公拍板）。

- 自动：local → ai → mineru（本地无坏题就停；有坏题只补坏题，坏题率 ≥30% 转全量）；
- 云端视觉：整批单题截图只交视觉模型，失败显性化，不偷换 MinerU；
- MinerU：整批单题截图只交 MinerU，失败显性化，不偷换视觉模型。

老插件的四通道名兼容映射：local_ai→自动、full_ocr→云端视觉（旧「全量OCR」
兜底 MinerU 的瀑布语义随主公拍板退场，只走选中的通道）。
"""

from __future__ import annotations

from typing import Any, Callable

from app.core.ai.platform import center as ai_center
from app.core.ingest.recognize import ai as recognize_ai, local as recognize_local, mineru as recognize_mineru, shared as recognize_shared

RECOGNIZE_AUTO = "auto"
RECOGNIZE_CLOUD = "cloud_vision"
RECOGNIZE_MINERU = "mineru"
RECOGNIZE_ENGINES = (RECOGNIZE_AUTO, RECOGNIZE_CLOUD, RECOGNIZE_MINERU)
BAD_RATE_THRESHOLD = 0.30

_PLANS = {
    RECOGNIZE_AUTO: ("local", "ai", "mineru"),
    RECOGNIZE_CLOUD: ("ai",),
    RECOGNIZE_MINERU: ("mineru",),
}

# 老插件只会发四通道名：映射到新的识别引擎，旧调用方不必跟着改。
_LEGACY_CHANNELS = {
    "auto": RECOGNIZE_AUTO,
    "local_ai": RECOGNIZE_AUTO,
    "full_ocr": RECOGNIZE_CLOUD,
    "mineru": RECOGNIZE_MINERU,
}


def normalize_engine(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in RECOGNIZE_ENGINES:
        return text
    return _LEGACY_CHANNELS.get(text, RECOGNIZE_AUTO)


def from_legacy_channel(value: Any) -> str:
    """四通道老口径 → 识别引擎；认不出就当自动。"""
    return _LEGACY_CHANNELS.get(str(value or "").strip().lower(), RECOGNIZE_AUTO)


def plan(engine: Any) -> tuple[str, ...]:
    return _PLANS[normalize_engine(engine)]


def _surface(route: dict[str, Any], step: str, reason: str, detail: str) -> None:
    """具体档失败进失败清单（复用失败显性化资产）：人话成因＋现场，可重试。"""
    failures = route.setdefault("failures", [])
    for entry in failures:
        if entry.get("step") == step:
            return
    failures.append({"file": "", "page_no": 0, "step": step,
                     "reason": reason[:400], "detail": detail[:4000],
                     "retryable": True})


async def _fill_single(picked: str, batch_id: str, items: list[dict[str, Any]],
                       total: int, route: dict[str, Any],
                       on_progress: Callable[[dict[str, Any]], None] | None) -> dict[str, Any]:
    """具体档：整批只走选中的通道，失败 ok=False 显性化，不级联不偷换。"""
    pending = list(range(total))
    if picked == RECOGNIZE_CLOUD:
        ai = await recognize_shared.guard(recognize_ai.run, batch_id, items, "all",
                                          {"total": total, "bad": total, "rate": 1.0,
                                           "bad_indexes": pending})
        pending = recognize_shared.remaining(pending, ai)
        route["mode"] = "cloud_vision"
        if ai.get("ok") and not pending:
            route["note"] = "云端视觉逐题识别完成：%d/%d 道回填成功。" % (
                ai["filled"], ai["attempted"])
        else:
            reason = "云端视觉识别未全部成功（%s），只走选中引擎，不降级，保留本地切图待人工核对。" % (
                ai.get("detail") or "不可用")
            route["note"] = reason + (("，%d 道保持本地切图" % len(pending)) if pending else "")
            _surface(route, "识别·云端视觉", reason, str(ai.get("detail") or ""))
    else:
        binding = ai_center.find_mineru()
        if binding is None:
            route["mode"] = "mineru"
            reason = "MinerU 没有可用的账号：先在【API 配置】里指派云端解析，保留本地切图待人工核对。"
            route["note"] = reason
            _surface(route, "识别·MinerU", reason, "账号池里没有可用的 MinerU 指派")
        else:
            mineru = await recognize_shared.guard(
                recognize_mineru.run, batch_id, items, pending, binding,
                route, on_progress)
            mineru["binding"] = True
            pending = recognize_shared.remaining(pending, mineru)
            route["mode"] = "mineru"
            if mineru.get("ok") and not pending:
                route["note"] = "MinerU 逐题解析完成：%d/%d 道回填成功。" % (
                    mineru["filled"], mineru["attempted"])
            else:
                reason = "MinerU 解析未全部成功（%s），只走选中引擎，不降级，保留本地切图待人工核对。" % (
                    mineru.get("detail") or "不可用")
                route["note"] = reason + (("，%d 道保持本地切图" % len(pending)) if pending else "")
                _surface(route, "识别·MinerU", reason, str(mineru.get("detail") or ""))
    route["phase"] = "done"
    route["done"] = True
    return route


async def fill_batch(batch_id: str, items: list[dict[str, Any]], engine: str,
                     report: dict[str, Any], route: dict[str, Any],
                     on_progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    """自动档跑完整条瀑布流；具体档只走选中的通道。结果写进批次路由并返回它。"""
    picked = normalize_engine(engine)
    total = len(items)
    if picked != RECOGNIZE_AUTO:
        return await _fill_single(picked, batch_id, items, total, route, on_progress)
    rate = float(report.get("rate") or 0.0)
    local = recognize_local.probe(items, report)
    if not local["bad_indexes"]:
        route["mode"] = "local"
        route["note"] = "本地提取 %d 题未发现坏题，无需调用 AI。" % total
        route["phase"] = "done"
        route["done"] = True
        return route
    full = rate >= BAD_RATE_THRESHOLD
    pending = list(range(total)) if full else local["bad_indexes"]
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
    route["mode"] = ("full_ocr" if full else "local" if not local["bad_indexes"]
                     else "partial_ai")
    route["note"] = recognize_shared.note_for(
        picked, full, rate, ai, mineru, total, pending, BAD_RATE_THRESHOLD)
    route["phase"] = "done"
    route["done"] = True
    return route