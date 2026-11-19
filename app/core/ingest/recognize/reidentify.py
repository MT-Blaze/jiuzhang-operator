"""审核重认（T6 §4）：老师手动点选席位 → 同张题图裁块/整题 → 原位替换。

不后台自动瀑布：一次点击只送一个席。坐标来源＝MinerU extensions 公式块
（归一化 bbox）或文字层 charbox；无坐标只给题级。失败进批次失败清单
retryable，人话成因照念；回填来源 "review.reidentify"。专科座 blocked
时选中显性「下一卡开」，不造假按钮、不偷换。
"""

from __future__ import annotations

import asyncio
import base64
import logging
from typing import Any

from app.core.ai.platform import center as ai_center
from app.core.ai.recognition import recognize as ai_recognize
from app.core.ingest.recognize import (
    formula as recognize_formula, mineru_extract, mineru_local, mineru_service,
    shared as recognize_shared, vlm_local, vlm_service,
)

logger = logging.getLogger(__name__)


def _attach_failure(batch_id: str, pending_id: str, reason: str, detail: str) -> None:
    """重认失败挂批次失败清单（复用失败显性化资产）；写不进去只影响提示。"""
    from app.core.pending import service

    try:
        route = service.read_batch_route(batch_id)
        failures = list(route.get("failures") or [])
        step = "审核·重认·%s" % pending_id
        failures = [entry for entry in failures if entry.get("step") != step]
        failures.append({"file": "", "page_no": 0, "step": step,
                         "reason": str(reason)[:400], "detail": str(detail)[:4000],
                         "retryable": True})
        route["failures"] = failures
        service.set_batch_route(batch_id, route)
    except Exception:  # noqa: BLE001 - 批次刚被删/并发写都不该拖垮重认回报
        logger.warning("[WARN] 重认失败清单写不进批次 %s", batch_id)


async def _whole_question(entry: dict[str, Any], png: bytes,
                          item: dict[str, Any]) -> dict[str, Any]:
    """整题重认：按 catalog 步骤名送席，返回契约题目或 MinerU markdown。"""
    steps = [str(step) for step in entry.get("plan_recognize") or []]
    step = steps[0] if steps else ""
    url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
    if step == "ai":
        binding = ai_center.resolve_task("ocr")
        if not binding.is_configured:
            return {"ok": False, "detail": "「视觉识别(OCR)」还没指派可用模型，请先在【API 配置】指派。"}
        try:
            outcome = await ai_recognize.recognize(
                [url], context=recognize_shared.context_of(item), task="ocr")
        except Exception as exc:  # noqa: BLE001 - 出网失败显性
            return {"ok": False, "detail": "云端视觉识别失败：%s" % str(exc)[:200]}
        if not outcome.get("ok") or not outcome.get("question"):
            return {"ok": False, "detail": str(outcome.get("detail") or "云端视觉没认出这道题")}
        return {"ok": True, "question": outcome["question"]}
    if step == "vlm_local":
        ready = await asyncio.to_thread(vlm_service.ensure_ready)
        if not ready.get("ok"):
            return {"ok": False, "detail": str(ready.get("detail") or "本地 VLM 不可用")}
        outcome = await asyncio.to_thread(
            vlm_local.recognize_image, png, ready, kind="question")
        if not outcome.get("ok"):
            return {"ok": False, "detail": str(outcome.get("detail") or "本地 VLM 没认出这道题")}
        return {"ok": True, "question": outcome["question"]}
    if step in ("mineru", "mineru_local"):
        if step == "mineru_local":
            ready = await asyncio.to_thread(mineru_service.ensure_ready)
            if not ready.get("ok"):
                return {"ok": False, "detail": str(ready.get("detail") or "本地 MinerU 不可用")}
            outcome = await asyncio.to_thread(
                mineru_local.parse_image, "整题重认.png", png, ready)
        else:
            binding = ai_center.find_mineru()
            if binding is None:
                return {"ok": False, "detail": "MinerU 没有可用的账号，请先在【API 配置】指派。"}
            outcome = await asyncio.to_thread(
                mineru_extract.extract, "整题重认.png", png,
                binding.base_url, binding.api_key, model=binding.model or "mineru")
        if not outcome.get("ok"):
            return {"ok": False, "detail": str(outcome.get("detail") or "MinerU 没认出这道题")}
        return {"ok": True, "markdown": str(outcome.get("markdown") or "")}
    return {"ok": False,
            "detail": str(entry.get("detail") or "")
            or "专科推理通道下一卡开（D 卡擂台），本卡只登记；请选其他就绪座。"}


async def list_spans(pending_id: str) -> dict[str, Any]:
    """公式块清单（只读）：有坐标逐块回报，无坐标回空列表，UI 只给题级。"""
    from app.core.pending.batch import batches

    item = batches.get_pending(pending_id)
    batch_id = str(item.get("batch_id") or "")
    page_images, pdf_bytes = await asyncio.to_thread(
        recognize_formula.batch_context, batch_id)
    spans = recognize_formula.discover_spans(item, page_images, pdf_bytes)
    rows = [{"index": index, "origin": str(span.get("origin") or ""),
             "preview": str(span.get("latex") or span.get("text") or "")[:80]}
            for index, span in enumerate(spans)]
    return {"ok": True, "spans": rows}


async def reidentify(pending_id: str, seat_id: str, target: str = "question",
                     span_index: int = 0) -> dict[str, Any]:
    """一次重认：选题 → 裁块/整题 → 送席 → 原位替换 → save_back。"""
    from app.core.ingest import registry
    from app.core.ingest.service import build_documents
    from app.core.pending.batch import batches

    item = batches.get_pending(pending_id)
    batch_id = str(item.get("batch_id") or "")
    entry = registry.entry_state(seat_id)
    if entry is None:
        return {"ok": False, "code": "SEAT_UNKNOWN",
                "detail": "模型目录里没有这个席位，请刷新【模型配置】后再选。"}
    if entry.get("state") != "ready" or not entry.get("enabled", True):
        return {"ok": False, "code": "SEAT_NOT_READY",
                "detail": "席位「%s」未就绪：%s" % (
                    entry.get("name") or seat_id, entry.get("detail") or "已停用")}
    png = recognize_shared.item_image_bytes(item)
    if not png:
        return {"ok": False, "code": "NO_IMAGE", "detail": "这道题的题图读不出来，没法重认。"}
    span = None
    if target == "formula":
        page_images, pdf_bytes = await asyncio.to_thread(
            recognize_formula.batch_context, batch_id)
        spans = recognize_formula.discover_spans(item, page_images, pdf_bytes)
        if not spans:
            return {"ok": False, "code": "NO_COORDS",
                    "detail": "这道题没有公式坐标（MinerU 公式块/文字层都没有），请用【整题重认】。"}
        if not 0 <= int(span_index) < len(spans):
            return {"ok": False, "code": "BAD_SPAN", "detail": "公式块序号不在范围内。"}
        span = spans[int(span_index)]
        png = recognize_formula.crop_png(png, span["bbox"])
        outcome = await recognize_formula.dispatch(entry, png, item)
    else:
        outcome = await _whole_question(entry, png, item)
    if not outcome.get("ok"):
        reason = "重认失败（%s）：%s" % (entry.get("name") or seat_id,
                                        outcome.get("detail") or "不可用")
        _attach_failure(batch_id, pending_id, reason, str(outcome.get("detail") or ""))
        return {"ok": False, "code": "RECOGNIZE_FAILED",
                "detail": str(outcome.get("detail") or "不可用")}
    document = dict(item.get("question") or {})
    if target == "formula":
        replaced = recognize_formula.replace_fragment(
            str(document.get("stem") or ""), span, str(outcome.get("latex") or ""))
        if replaced is None:
            reason = "认出了新公式，但题面里定位不到原公式片段，未原位替换（D12 不裸拼）。"
            _attach_failure(batch_id, pending_id, reason, str(outcome.get("latex") or ""))
            return {"ok": False, "code": "REPLACE_FAILED", "detail": reason}
        document["stem"] = replaced
    elif outcome.get("question"):
        document = recognize_shared.document_from_ai(
            outcome["question"], item.get("question") or {})
    else:
        documents, _notes = build_documents(str(outcome.get("markdown") or ""))
        if not documents:
            reason = "重认结果拆不出题目正文，未替换。"
            _attach_failure(batch_id, pending_id, reason, str(outcome.get("markdown") or "")[:400])
            return {"ok": False, "code": "REPLACE_FAILED", "detail": reason}
        document = documents[0]
    document = recognize_shared.merge_local(document, item.get("question") or {})
    extensions = dict(document.get("extensions") or {})
    editor = dict(extensions.get(recognize_formula.EDITOR_NS) or {})
    editor.pop("formula_pending", None)
    if editor:
        extensions[recognize_formula.EDITOR_NS] = editor
    if extensions:
        document["extensions"] = extensions
    if not recognize_shared.save_back(item, document, batch_id, "review.reidentify"):
        reason = "重认结果回填失败（池子写入被拒），原样保留。"
        _attach_failure(batch_id, pending_id, reason, "")
        return {"ok": False, "code": "SAVE_FAILED", "detail": reason}
    return {"ok": True, "question": document, "seat": seat_id, "target": target,
            "detail": "已按「%s」原位替换%s。" % (
                entry.get("name") or seat_id,
                "公式片段" if target == "formula" else "整题正文")}