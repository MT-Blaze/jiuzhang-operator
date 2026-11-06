"""解析体检 → 批次路由标记与自动切图（从 ``ingest`` 拆出，单文件 800 行上限）。

通道一只写提示、绝不自动调 AI；通道二先试 MinerU，连不上或没拆出题就退回切图。
切图落池要复用 ``ingest`` 里的文档构造函数，两处对 ``ingest`` 的取用一律延迟到
调用期——``ingest`` 在导入时会先加载本模块，模块级反向导入必成环。
"""

from __future__ import annotations

import asyncio
import base64
import logging
from pathlib import Path
from typing import Any

from app.core import (
    ai_center,
    ai_recognize,
    ingest_quality,
    mineru_extract,
    page_render,
    pending_assets,
    scan_text,
)

logger = logging.getLogger(__name__)

# 四个通道：老师选哪个就按哪个跑；auto 会在坏题率越线时自己改走全量 OCR。
CHANNEL_AUTO = "auto"
CHANNEL_LOCAL_AI = "local_ai"
CHANNEL_FULL_OCR = "full_ocr"
CHANNEL_MINERU = "mineru"
CHANNELS = (CHANNEL_AUTO, CHANNEL_LOCAL_AI, CHANNEL_FULL_OCR, CHANNEL_MINERU)

# 坏题率分诊线：低于它只补坏题，达到或越过就判定本地提取崩盘。
INGEST_BAD_RATE_THRESHOLD = 0.30
# 单题截图并发识别数：5 路足够把等待摊薄，又不会把模型接口打穿。
OCR_CONCURRENCY = 5
# MinerU 单题排队可能很久：放宽到 15 分钟，按题逐张等。
MINERU_WAIT_SECONDS = 900.0


def normalize_channel(value: Any) -> str:
    """前端交来的通道名 → 白名单内的一个；认不出就当自动，绝不猜。"""
    text = str(value or "").strip().lower()
    return text if text in CHANNELS else CHANNEL_AUTO


def route_payload(channel: str, health: dict[str, Any],
                  text_layer: bool | None = None) -> dict[str, Any]:
    """解析体检 → 批次上的路由标记。

    乱码只写提示、永远不在这里调 AI：通道一只负责把「值得人工看一眼」
    这件事说清楚，识别由老师在画布上亲手点。
    """
    garbled = bool(health.get("garbled"))
    has_layer = bool(health.get("has_text_layer")) if text_layer is None else bool(text_layer)
    note = ""
    if channel == "scan_image":
        note = "纯扫描件：文本层读不出字，已退回切图模式，可逐框确认或点【AI识题】。"
    elif channel == "mineru":
        note = "纯扫描件：已走 MinerU 识别，正文来自 MinerU，题图仍以原卷为准。"
    elif garbled:
        note = ("文本层有 %d 个字形读不出（疑似乱码/公式字体缺映射）："
                "不会自动调用 AI，需要时点【AI识题】。"
                % int(health.get("missing_chars") or 0))
    return {
        "channel": channel,
        "text_layer": has_layer,
        "garbled": garbled,
        "text_chars": int(health.get("text_chars") or 0),
        "missing_chars": int(health.get("missing_chars") or 0),
        "note": note,
    }


def route_scan_pdf(name: str, data: bytes) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """PDF 路由：有文本层走通道一，没有就试 MinerU，失败退回切图。

    返回 ``(route, 结构化题目)``。MinerU 只有在账号池里真的配了 Key 时才尝试，
    连不上/超时/没拆出题一律如实写进 note，再由调用方退回切图。
    """
    from app.core.ingest import build_documents

    health = page_render.pdf_text_health(data)
    if health.get("has_text_layer"):
        return route_payload("text", health), []
    mineru = ai_center.find_mineru()
    if mineru is None:
        route = route_payload("scan_image", health, text_layer=False)
        route["note"] = ("纯扫描件且没有配置 MinerU：已退回切图模式，"
                         "可逐框确认或点【AI识题】。")
        return route, []
    outcome = mineru_extract.extract(
        name, data, mineru.base_url, mineru.api_key, model=mineru.model)
    if not outcome.get("ok"):
        route = route_payload("scan_image", health, text_layer=False)
        route["note"] = "MinerU 没成功（%s），已退回切图模式。" % str(outcome.get("detail") or "")[:160]
        return route, []
    documents, notes = build_documents(str(outcome.get("markdown") or ""))
    if not documents:
        route = route_payload("scan_image", health, text_layer=False)
        route["note"] = "MinerU 返回了文本但没拆出题目，已退回切图模式。" + (
            "（%s）" % notes[0] if notes else "")
        return route, []
    route = route_payload("mineru", health, text_layer=False)
    route["note"] = "纯扫描件：已走 MinerU 识别，正文来自 MinerU，题图仍以原卷为准。"
    return route, documents


def scan_fallback_route(route: dict[str, Any], reason: str) -> dict[str, Any]:
    fallback = dict(route)
    fallback["channel"] = "scan_image"
    fallback["note"] = "MinerU 结果没能入池（%s），已退回切图模式。" % reason
    return fallback


def save_route(pending_bank: Any, batch_id: str, route: dict[str, Any]) -> None:
    """路由标记是增强信息：写不进去只影响提示，绝不回滚已入池的题目。"""
    try:
        pending_bank.set_batch_route(batch_id, route)
    except Exception:  # noqa: BLE001 - 老批次/并发删除都不该拖垮解析
        pass


def auto_split_shell(page_no: int, number: Any, asset_id: str, title: str,
                     region: dict[str, Any] | None = None) -> dict[str, Any]:
    """自动切图生成的一道待审题：文字层读得出就填正文，读不出才落占位提示。

    题干、选项、答案与解析都从题块坐标内的文字还原（Unicode 数学字符折成
    LaTeX，公式包 ``$...$``）；原题图始终挂在题身上，切图与文字互为对照。
    """
    from app.core.ingest import DEFAULT_DIFFICULTY, _document

    label = str(number or "")
    parsed = scan_text.parse_scan_text((region or {}).get("text"), label)
    source = {"question_no": label, "paper_title": title}
    images = [{
        "id": asset_id,
        "role": "stem",
        "uri": "/static/uploads/" + asset_id + ".png",
    }]
    if parsed["stem"]:
        document = _document(parsed["stem"], parsed["options"], parsed["answer"],
                             parsed["blanks"], parsed["solution"], label)
        document["source"] = source
        document["images"] = images
        return document
    return {
        "schema_version": "2.0",
        "type": "solution",
        "stem": "（自动切题：原卷第 %d 页第 %s 题，请对照题图录入题干与答案）"
                % (page_no, label or "?"),
        "difficulty": DEFAULT_DIFFICULTY,
        "source": source,
        "images": images,
    }


def auto_split_pages(name: str, data: bytes, batch_id: str,
                     page_images: list[dict[str, Any]]) -> list[str]:
    """把页图上的题块全部裁成待审题；失败只记警告，绝不拖垮页图与手动框选。

    题块坐标是页面图像素，``page_render.crop_pdf_regions`` 换回 PDF 点后
    按 300 dpi 直接从原 PDF 裁图。19 块一次落池，顺序就是卷面顺序。
    """
    from app.core import pending_bank

    crops, notes = page_render.crop_pdf_regions(data, page_images)
    if not crops:
        return notes
    title = str(Path(name or "").stem or name or "")[:120]
    items: list[dict[str, Any]] = []
    regions: list[dict[str, Any]] = []
    for entry in page_images:
        try:
            page_no = int(entry.get("page") or 0)
        except (TypeError, ValueError):
            continue
        for crop in crops.get(page_no) or []:
            region = crop["region"]
            asset_id = "img_auto_%d_%d" % (page_no, int(crop["index"]))
            items.append({
                "question": auto_split_shell(page_no, crop.get("no"), asset_id,
                                             title, region),
                "assets": [{
                    "id": asset_id,
                    "data_url": "data:image/png;base64,"
                                + base64.b64encode(crop["png"]).decode("ascii"),
                }],
                "page_no": page_no,
            })
            regions.append(region)
    if not items:
        return notes
    try:
        result = pending_bank.save_draft(items, batch_id=batch_id,
                                         origin="ingest.auto_split")
    except Exception as error:  # noqa: BLE001 - 自动落池失败仍保留页图与绿框
        notes.append(f"自动切图落池失败（{error}），可在左侧逐框确认切分")
        return notes
    saved_ids = [str(value) for value in (result.get("saved_ids") or [])]
    for region, pending_id in zip(regions, saved_ids):
        if pending_id:
            region["pending_id"] = pending_id
    try:
        # 题块与待审题绑定后再写回一次：老师重开批次时框上就知道「已入池」。
        pending_bank.set_batch_pages(batch_id, page_images)
    except Exception:  # noqa: BLE001 - 绑定写不进去只影响重开批次的状态标记
        pass
    return notes


# ---------------------------------------------------------------- 坏题分诊与回填


def scan_route(channel: str, health: dict[str, Any]) -> dict[str, Any]:
    """本次 PDF/图片解析走哪条路：只描述计划，真正的坏题率等切完再算。"""
    picked = normalize_channel(channel)
    text_layer = bool(health.get("has_text_layer"))
    route = route_payload(picked, health, text_layer=text_layer)
    route["requested_channel"] = picked
    route["phase"] = "parsing"
    route["done"] = False
    if picked == CHANNEL_MINERU:
        note = "MinerU 云端：先本地切出单题截图，再逐题发送识别。"
    elif picked == CHANNEL_FULL_OCR:
        note = "全量 OCR：按单题截图并发识别，互不干扰。"
    elif picked == CHANNEL_LOCAL_AI:
        note = "本地+AI：先本地极速提取，坏题再静默交 AI 修补。"
    elif text_layer:
        note = "自动路由：有文本层，先跑本地极速提取并按坏题率分诊。"
    else:
        note = "自动路由：无文本层，直接并发全量 OCR。"
    if health.get("garbled"):
        note += (" 文本层有 %d 个字形读不出，已标记待人工核对。"
                 % int(health.get("missing_chars") or 0))
    route["note"] = note
    return route


def log_stats(report: dict[str, Any]) -> None:
    """静默统计只写服务端日志：一行账，供老师回看时不被弹窗打断。"""
    logger.info(
        "[STAT] 本次解析总题数: %d, 坏题数: %d, 坏题率: %.1f%%",
        int(report.get("total") or 0),
        int(report.get("bad") or 0),
        float(report.get("rate") or 0.0) * 100.0,
    )


def log_documents(documents: list[Any]) -> dict[str, Any]:
    """文本/Word 这类不走切图的解析也记一笔坏题账（只记，不自动调 AI）。"""
    report = ingest_quality.triage_documents(documents)
    log_stats(report)
    return report


def _first_image_uri(item: dict[str, Any]) -> str:
    document = item.get("question") if isinstance(item.get("question"), dict) else {}
    for image in document.get("images") or []:
        if not isinstance(image, dict):
            continue
        uri = str(image.get("uri") or "")
        if uri.startswith("/static/pending/") or uri.startswith("/static/uploads/"):
            return uri
    for asset in item.get("assets") or []:
        if isinstance(asset, dict) and asset.get("name"):
            return "/static/pending/" + str(asset["name"])
    return ""


def _item_image_bytes(item: dict[str, Any]) -> bytes:
    """单题截图的原始 PNG：优先按池内资产名取，取不到再看题面里的 uri。"""
    for asset in item.get("assets") or []:
        name = str((asset or {}).get("name") or "") if isinstance(asset, dict) else ""
        if not name:
            continue
        try:
            return pending_assets.asset_path(name).read_bytes()
        except Exception:  # noqa: BLE001 - 单个资产读不到就试下一个，绝不编图
            continue
    uri = _first_image_uri(item)
    if uri.startswith("/static/pending/"):
        try:
            return pending_assets.asset_path(uri.rsplit("/", 1)[-1]).read_bytes()
        except Exception:  # noqa: BLE001
            return b""
    return b""


def _context_of(item: dict[str, Any]) -> dict[str, Any]:
    """交给视觉模型的上下文只留能帮它定位的字段，别把整题再传一遍。"""
    document = item.get("question") if isinstance(item.get("question"), dict) else {}
    return {
        "type": str(document.get("type") or ""),
        "stem": str(document.get("stem") or "")[:6000],
        "question_no": str((document.get("source") or {}).get("question_no") or ""),
    }


def _document_from_ai(question: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    """AI 识别结果 → 契约题目；题图与来源沿用本地切题那一条，绝不丢。"""
    from app.core.ingest import DEFAULT_DIFFICULTY, _document

    options = [
        {"key": str(option.get("key") or ""), "content": str(option.get("content") or "")}
        for option in (question.get("options") or [])
        if isinstance(option, dict) and str(option.get("content") or "").strip()
    ]
    kind = str(question.get("type") or "")
    document = _document(
        str(question.get("stem") or ""),
        options,
        str(question.get("answer") or ""),
        1 if kind == "fill_blank" else 0,
        str(question.get("solution") or ""),
        str(question.get("question_no") or (base.get("source") or {}).get("question_no") or ""),
    )
    difficulty = str(question.get("difficulty") or "").upper()
    if difficulty:
        document["difficulty"] = difficulty or DEFAULT_DIFFICULTY
    source = dict(base.get("source") or {})
    if question.get("question_no"):
        source["question_no"] = str(question["question_no"])
    if source:
        document["source"] = source
    if base.get("images"):
        document["images"] = list(base["images"])
    return document


def _merge_local(incoming: dict[str, Any], local: dict[str, Any]) -> dict[str, Any]:
    """云端正文字段替换，题图、来源与页面定位仍用本地那一条。"""
    if local.get("source"):
        incoming["source"] = dict(local["source"])
    if local.get("images"):
        incoming["images"] = list(local["images"])
    return incoming


def _save_back(item: dict[str, Any], document: dict[str, Any], batch_id: str,
               origin: str) -> bool:
    from app.core import pending_bank

    try:
        pending_bank.save_draft(
            [{"question": document, "pending_id": item.get("id"),
              "page_no": item.get("page_no", 1)}],
            batch_id=batch_id,
            origin=origin,
        )
        return True
    except Exception:  # noqa: BLE001 - 单题回填失败只丢这一道，不拖垮整批
        return False


async def _fill_with_ai(batch_id: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    """单题截图并发交视觉模型；每道题独立回填，谁失败都不影响别人。"""
    binding = ai_center.resolve_task("ocr")
    if not binding.is_configured:
        return {"filled": 0, "failed": len(items),
                "detail": "「视觉识别(OCR)」还没指派可用模型"}
    semaphore = asyncio.Semaphore(OCR_CONCURRENCY)

    async def one(item: dict[str, Any]) -> bool:
        uri = _first_image_uri(item)
        if not uri:
            return False
        async with semaphore:
            try:
                outcome = await ai_recognize.recognize(
                    [uri], context=_context_of(item), task="ocr")
            except Exception:  # noqa: BLE001 - 出网失败只算这一道没回来
                return False
        if not outcome.get("ok") or not outcome.get("question"):
            return False
        document = _document_from_ai(outcome["question"], item.get("question") or {})
        return _save_back(item, document, batch_id, "ingest.ai_fill")

    results = await asyncio.gather(*(one(item) for item in items), return_exceptions=True)
    filled = sum(1 for result in results if result is True)
    return {"filled": filled, "failed": len(items) - filled, "detail": ""}


async def _fill_with_mineru(batch_id: str, items: list[dict[str, Any]],
                            binding: ai_center.TaskBinding,
                            route: dict[str, Any]) -> tuple[int, int]:
    """逐题发送 MinerU：一张单题截图一次请求，回填只动那一道。"""
    from app.core import pending_bank
    from app.core.ingest import build_documents

    filled = failed = 0
    total = len(items)
    for index, item in enumerate(items, start=1):
        note = "正在将第 %d 题发送至 MinerU 云端解析..." % index
        logger.info(note)
        route["note"] = note
        save_route(pending_bank, batch_id, route)
        data = _item_image_bytes(item)
        if not data:
            failed += 1
            continue
        outcome = await asyncio.to_thread(
            mineru_extract.extract,
            "第%d题.png" % index,
            data,
            binding.base_url,
            binding.api_key,
            model=binding.model or "mineru",
            wait=MINERU_WAIT_SECONDS,
        )
        if not outcome.get("ok"):
            failed += 1
            route["note"] = "第 %d/%d 题 MinerU 没成功（%s），继续下一题。" % (
                index, total, str(outcome.get("detail") or "")[:120])
            save_route(pending_bank, batch_id, route)
            continue
        documents, _notes = build_documents(str(outcome.get("markdown") or ""))
        if not documents:
            failed += 1
            continue
        document = _merge_local(documents[0], item.get("question") or {})
        if _save_back(item, document, batch_id, "ingest.mineru"):
            filled += 1
        else:
            failed += 1
    return filled, failed


async def fill_scan_batch(batch_id: str, channel: str,
                          health: dict[str, Any]) -> dict[str, Any]:
    """切完题后的分诊：算坏题率、打一行静默统计，再按通道决定补哪些题。

    返回值就是写回批次的 route：老师重开批次时能看到这次走了哪条路、
    坏题率多少、最后补回几道。
    """
    from app.core import pending_bank

    picked = normalize_channel(channel)
    try:
        items = pending_bank.list_batch_questions(batch_id).get("items") or []
    except Exception:  # noqa: BLE001 - 批次刚被删/库读不通时只影响统计
        items = []
    report = ingest_quality.triage_documents([item.get("question") for item in items])
    log_stats(report)
    route = scan_route(picked, health)
    route["stats"] = {
        "total": int(report["total"]),
        "bad": int(report["bad"]),
        "rate": round(float(report["rate"]) * 100.0, 1),
    }
    if not items:
        route["note"] = route["note"] + " 这次没切出题目，可在左栏逐框确认。"
        route["phase"] = "done"
        route["done"] = True
        return route

    full_ocr = (picked == CHANNEL_FULL_OCR
                or float(report["rate"]) >= INGEST_BAD_RATE_THRESHOLD)
    if picked == CHANNEL_MINERU:
        binding = ai_center.find_mineru()
        if binding is None:
            route["note"] = "没有可用的 MinerU 账号：先在【API 配置】里指派 MinerU 云端解析。"
        else:
            filled, failed = await _fill_with_mineru(batch_id, items, binding, route)
            route["note"] = "MinerU 逐题解析完成：%d/%d 道回填成功%s。" % (
                filled, len(items),
                ("，%d 道保持本地切图" % failed) if failed else "")
    elif full_ocr or (picked in (CHANNEL_AUTO, CHANNEL_LOCAL_AI) and report["bad"]):
        targets = items if full_ocr else [items[index] for index in report["bad_indexes"]]
        outcome = await _fill_with_ai(batch_id, targets)
        filled = int(outcome.get("filled") or 0)
        if full_ocr:
            route["mode"] = "full_ocr"
            route["note"] = "坏题率 %.1f%%%s：已触发并发全量 OCR，%d/%d 道回填成功。" % (
                float(report["rate"]) * 100.0,
                "（达到分诊线）" if float(report["rate"]) >= INGEST_BAD_RATE_THRESHOLD else "",
                filled, len(targets))
        else:
            route["note"] = "坏题率 %.1f%% 低于分诊线，已局部修补 %d/%d 道坏题。" % (
                float(report["rate"]) * 100.0, filled, len(targets))
        if outcome.get("detail") and not filled:
            route["note"] += "（%s，坏题保留待人工核对）" % outcome["detail"]
    else:
        route["note"] = "本地提取 %d 题未发现坏题，无需调用 AI。" % len(items)
    route["phase"] = "done"
    route["done"] = True
    return route
