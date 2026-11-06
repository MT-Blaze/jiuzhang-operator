"""解析路由账本与自动切图（从 ``ingest`` 拆出；具体引擎在 layout/ 与 recognize/）。

本模块只做三件事：解析体检 → 批次路由标记；页图题块 → 自动切图入池；
切完题后的坏题统计与「交给识别调度员」。版面探测与识别算法本身归
``app.core.layout`` / ``app.core.recognize``，这里只传参、只记账。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core import ingest_quality, page_render
from app.core.layout import layout_router
from app.core.recognize import recognize_local, recognize_router

logger = logging.getLogger(__name__)

# 坏题率分诊线：低于它只补坏题，达到或越过就判定本地提取崩盘。
INGEST_BAD_RATE_THRESHOLD = recognize_router.BAD_RATE_THRESHOLD


def route_payload(kind: str, health: dict[str, Any],
                  text_layer: bool | None = None) -> dict[str, Any]:
    """解析体检 → 批次上的路由标记（版面/识别引擎由 ``scan_route`` 补）。"""
    garbled = bool(health.get("garbled"))
    has_layer = bool(health.get("has_text_layer")) if text_layer is None else bool(text_layer)
    note = ""
    if kind == "scan_image":
        note = "纯扫描件：文本层读不出字，已退回切图模式，可逐框确认或点【AI识题】。"
    elif garbled:
        note = ("文本层有 %d 个字形读不出（疑似乱码/公式字体缺映射）："
                "不会自动调用 AI，需要时点【AI识题】。"
                % int(health.get("missing_chars") or 0))
    return {
        "channel": kind,
        "text_layer": has_layer,
        "garbled": garbled,
        "text_chars": int(health.get("text_chars") or 0),
        "missing_chars": int(health.get("missing_chars") or 0),
        "note": note,
    }


def save_route(pending_bank: Any, batch_id: str, route: dict[str, Any]) -> None:
    """路由标记是增强信息：写不进去只影响提示，绝不回滚已入池的题目。"""
    try:
        pending_bank.set_batch_route(batch_id, route)
    except Exception:  # noqa: BLE001 - 老批次/并发删除都不该拖垮解析
        pass


def attach_layout(route: dict[str, Any], layout: dict[str, Any] | None) -> dict[str, Any]:
    """把 YOLO 实际用的版本、硬件与逐级状态挂到批次路由，宿主据此播报到运行日志。"""
    if not layout:
        return route
    if layout.get("status"):
        route["layout_status"] = list(layout["status"])
    if layout.get("model"):
        route["layout_model"] = dict(layout["model"])
    return route


def auto_split_shell(page_no: int, number: Any, asset_id: str, title: str,
                     region: dict[str, Any] | None = None) -> dict[str, Any]:
    """自动切图生成的一道待审题；纯本地提取由 ``recognize_local`` 统一实现。"""
    return recognize_local.build_document(region, page_no, number, asset_id, title)


def auto_split_pages(name: str, data: bytes, batch_id: str,
                     page_images: list[dict[str, Any]]) -> list[str]:
    """把页图上的题块全部裁成待审题；失败只记警告，绝不拖垮页图与手动框选。

    题块坐标是页面图像素，``page_render.crop_pdf_regions`` 换回 PDF 点后
    按 300 dpi 直接从原 PDF 裁图。19 块一次落池，顺序就是卷面顺序。
    """
    import base64

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


def scan_route(layout_engine: str = layout_router.LAYOUT_AUTO,
               recognize_engine: str = recognize_router.RECOGNIZE_AUTO,
               health: dict[str, Any] | None = None) -> dict[str, Any]:
    """本次解析走哪条路：只描述计划，真正的坏题率等切完再算。"""
    health = health or {}
    picked_layout = layout_router.normalize_engine(layout_engine)
    picked_recognize = recognize_router.normalize_engine(recognize_engine)
    text_layer = bool(health.get("has_text_layer"))
    route = route_payload("text" if text_layer else "scan_image", health,
                          text_layer=text_layer)
    route["layout_engine"] = picked_layout
    route["recognize_engine"] = picked_recognize
    route["phase"] = "parsing"
    route["done"] = False
    if picked_layout == layout_router.LAYOUT_CLOUD:
        layout_note = "版面：本地文本层优先，失败跳过 YOLO 直交云端。"
    elif picked_layout == layout_router.LAYOUT_YOLO:
        layout_note = "版面：本地文本层优先，失败强制交本机 YOLO，再失败交云端。"
    else:
        layout_note = "版面：本地文本层优先，失败交本机 YOLO，再失败交云端。"
    if picked_recognize == recognize_router.RECOGNIZE_MINERU:
        recognize_note = "识别：MinerU 云端，先本地切出单题截图再逐题发送。"
    elif picked_recognize == recognize_router.RECOGNIZE_FULL_OCR:
        recognize_note = "识别：全量 OCR，整批单题截图并发识别，失败再交 MinerU。"
    else:
        recognize_note = ("识别：自动，本地先提取；坏题交 AI 修补，"
                          "坏题率≥30% 转全量，最后 MinerU 兜底。")
    route["note"] = layout_note + recognize_note
    if not text_layer:
        route["note"] += " 本卷没有文本层，本地切题可能留下占位题。"
    if health.get("garbled"):
        route["note"] += (" 文本层有 %d 个字形读不出，已标记待人工核对。"
                          % int(health.get("missing_chars") or 0))
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


async def fill_scan_batch(batch_id: str,
                          recognize_engine: str = recognize_router.RECOGNIZE_AUTO,
                          health: dict[str, Any] | None = None,
                          layout_engine: str = layout_router.LAYOUT_AUTO,
                          layout: dict[str, Any] | None = None) -> dict[str, Any]:
    """切完题后的分诊：算坏题率、打一行静默统计，再交给识别调度员。

    返回值就是写回批次的 route：老师重开批次时能看到这次选了哪两个引擎、
    实际由谁探出题块、坏题率多少、最后补回几道。
    """
    from app.core import pending_bank

    try:
        items = pending_bank.list_batch_questions(batch_id).get("items") or []
    except Exception:  # noqa: BLE001 - 批次刚被删/库读不通时只影响统计
        items = []
    report = ingest_quality.triage_documents([item.get("question") for item in items])
    log_stats(report)
    route = scan_route(layout_engine, recognize_engine, health)
    attach_layout(route, layout)
    if layout:
        route["layout_detected"] = str(layout.get("engine") or "")
        route["layout_attempts"] = list(layout.get("attempts") or [])
    route["stats"] = {
        "total": int(report["total"]),
        "bad": int(report["bad"]),
        "rate": round(float(report["rate"]) * 100.0, 1),
    }
    if not items:
        route["note"] += " 这次没切出题目，可在左栏逐框确认。"
        route["phase"] = "done"
        route["done"] = True
        return route

    def progress(snapshot: dict[str, Any]) -> None:
        save_route(pending_bank, batch_id, snapshot)

    return await recognize_router.fill_batch(
        batch_id, items, recognize_engine, report, route, progress)
