"""解析路由账本与自动切图（从 ``ingest.service`` 拆出；具体引擎在 layout/ 与 recognize/）。

本模块只做三件事：解析体检 → 批次路由标记；页图题块 → 自动切图入池；
切完题后的坏题统计与「交给识别调度员」。版面探测与识别算法本身归
``app.core.ingest.layout`` / ``app.core.ingest.recognize``，这里只传参、只记账。
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from app.core.ingest import quality as ingest_quality
from app.core.ingest.render import service as page_render
from app.core.ingest.layout import router as layout_router
from app.core.ingest.recognize import (
    crosspage, guards, local as recognize_local, router as recognize_router,
)

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


def save_route(service: Any, batch_id: str, route: dict[str, Any]) -> None:
    """路由标记是增强信息：写不进去只影响提示，绝不回滚已入池的题目。

    失败显性化（2026-11-18 卡）：识别调度员中途会用全新 route 快照重写批次，
    快照里没带 failures/progress 时把库里已有的那两份旧账保全进来，
    成因与过程流水不因快照重写而丢。note 等其余键语义一字不动。
    """
    try:
        if "failures" not in route or "progress" not in route:
            stored = service.read_batch_route(batch_id)
            for key in ("failures", "progress"):
                if key not in route and stored.get(key):
                    route[key] = stored[key]
        service.set_batch_route(batch_id, route)
    except Exception:  # noqa: BLE001 - 老批次/并发删除都不该拖垮解析
        pass


# ---------------------------------------------------------------- 失败显性化账本
# 口径（2026-11-18 拍板）：过程进运行日志、成因进报错诊断、成因落盘挂批次。
# 账本随每次解析在内存里累积，经 save_route 落进 route_json 的 failures/progress
# 两键（零 schema 迁移，route_json 本身即先例）。整块下架：删掉本段与
# service.py 里的 ledger_* 调用点即可，保批保卷行为不受影响。

PROGRESS_LIMIT = 40


def new_ledger() -> dict[str, Any]:
    """一份文件一个账本：failures 按 file+step 去重，progress 环形上限 40 条。"""
    return {"failures": [], "progress": [], "seq": 0}


def ledger_progress(ledger: dict[str, Any], text: str, level: str = "info") -> None:
    """记一条过程摘要（人话一句）；seq 单调递增，前端据此增量播报不刷屏。"""
    ledger["seq"] = int(ledger.get("seq") or 0) + 1
    ledger["progress"].append(
        {"seq": ledger["seq"], "text": str(text)[:400], "level": str(level)})
    if len(ledger["progress"]) > PROGRESS_LIMIT:
        del ledger["progress"][:len(ledger["progress"]) - PROGRESS_LIMIT]


def failure_reason(error: BaseException, fallback: str) -> str:
    """成因翻成人话：质检拒收有固定口径，其余异常按步骤给兜底句。"""
    from app.core.bank import questions

    if isinstance(error, questions.QuestionValidationError):
        return "识别结果没通过题目质检（缺必填字段），已留占位，可对着原卷补录"
    return fallback


def failure_detail(error: BaseException) -> str:
    """完整现场：质检拒收给 ValidationError 原文，其余给异常原文＋堆栈尾段。"""
    import traceback

    from app.core.bank import questions

    if isinstance(error, questions.QuestionValidationError):
        return "QuestionValidationError: " + "；".join(error.errors)
    lines = traceback.format_exception(type(error), error, error.__traceback__)
    return "".join(lines)[-2000:]


def ledger_failure(ledger: dict[str, Any], *, file: str, page_no: int, step: str,
                   reason: str, detail: str, retryable: bool = True) -> None:
    """记一条失败成因：按 file+step 去重追加，同时落一条 error 级过程行。"""
    key = (str(file), str(step))
    for entry in ledger["failures"]:
        if (entry.get("file"), entry.get("step")) == key:
            return
    ledger["failures"].append({
        "file": str(file), "page_no": int(page_no or 0), "step": str(step),
        "reason": str(reason)[:400], "detail": str(detail)[:4000],
        "retryable": bool(retryable),
    })
    ledger_progress(ledger, "%s %s失败：%s" % (file, step, reason), "error")


def attach_surface(route: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    """把账本挂到 route 上随 save_route 落盘；空账不挂键，成功批次不留失败痕。

    route 里已有的失败条目（识别具体档失败显性化）与账本按 file+step 合并，
    两边都不丢。
    """
    if ledger.get("failures"):
        merged = list(route.get("failures") or [])
        seen = {(entry.get("file"), entry.get("step")) for entry in merged}
        for entry in ledger["failures"]:
            if (entry.get("file"), entry.get("step")) not in seen:
                merged.append(entry)
        route["failures"] = merged
    if ledger.get("progress"):
        route["progress"] = list(ledger["progress"])
    return route


def surface_failure(service: Any, batch_id: str, ledger: dict[str, Any], *,
                    file: str, page_no: int, step: str, error: BaseException,
                    fallback: str, persist: bool = False) -> None:
    """吞异常点的统一开口：成因翻人话落账；早退路径 persist=True 立刻落盘。"""
    ledger_failure(ledger, file=file, page_no=page_no, step=step,
                   reason=failure_reason(error, fallback),
                   detail=failure_detail(error))
    if persist:
        save_route(service, batch_id, attach_surface({}, ledger))


def ledger_stats(ledger: dict[str, Any], name: str, route: dict[str, Any]) -> None:
    """识别收口后把坏题账翻成一条过程摘要：无坏题绿字，有坏题黄字。"""
    stats = route.get("stats") or {}
    if stats:
        ledger_progress(
            ledger, "%s 识别完成：共 %s 题，坏题 %s 道" % (
                name, stats.get("total"), stats.get("bad")),
            "warn" if stats.get("bad") else "ok")


def append_notes(route: dict[str, Any], notes: list[str]) -> dict[str, Any]:
    """把单文件分拣的如实说明并进批次路由，老师重开批次时能看到。"""
    if notes:
        route["note"] = (str(route.get("note") or "") + " " + " ".join(notes)).strip()
    return route


def open_ledger(layout_engine: str, recognize_engine: str
                ) -> tuple[str, str, dict[str, Any], str]:
    """闸口＋开账（2026-11-18 拍板）：残留值未就绪 → 回 auto，原因进账本与批次 note，不静默。"""
    from app.core.ingest import registry

    picked_layout, layout_note = registry.gate_layout(layout_engine)
    picked_recognize, recognize_note = registry.gate_recognize(recognize_engine)
    gate_note = " ".join(note for note in (layout_note, recognize_note) if note)
    ledger = new_ledger()
    if gate_note:
        ledger_progress(ledger, gate_note, "warn")
    return picked_layout, picked_recognize, ledger, gate_note


def note_layout_failure(ledger: dict[str, Any], name: str,
                        picked_layout: str, layout: dict[str, Any] | None) -> None:
    """具体档版面失败显性化：只走选中引擎，没探到就如实记成因，不偷换。"""
    if picked_layout == layout_router.LAYOUT_AUTO or (layout or {}).get("ok"):
        return
    ledger_failure(ledger, file=name, page_no=0, step="版面探测",
                   reason=str((layout or {}).get("detail") or "选中的版面引擎没找到题块"),
                   detail=str((layout or {}).get("attempts") or ""))


def apply_layout(page_images: list[dict[str, Any]],
                 layout: dict[str, Any] | None) -> None:
    """把版面引擎探出的题块就地写回页图；没探到就保留原有绿框。"""
    found = (layout or {}).get("pages") or {}
    if not found:
        return
    for entry in page_images:
        try:
            page_no = int(entry.get("page") or 0)
        except (TypeError, ValueError):
            continue
        regions = found.get(page_no) or found.get(str(page_no))
        if isinstance(regions, list) and regions:
            entry["regions"] = regions


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
                     page_images: list[dict[str, Any]],
                     layout: dict[str, Any] | None = None,
                     ledger: dict[str, Any] | None = None) -> list[str]:
    """把页图上的题块全部裁成待审题；失败只记警告，绝不拖垮页图与手动框选。

    题块坐标是页面图像素，``page_render.crop_pdf_regions`` 换回 PDF 点后
    按 300 dpi 直接从原 PDF 裁图。19 块一次落池，顺序就是卷面顺序。
    裁前先过题号链门禁（回跳/密度），OCR 卷再判跨页续段并纵拼（T8）。
    """
    import base64

    from app.core.pending import service

    lines_by_page = (layout or {}).get("lines_by_page") or {}
    columns = (layout or {}).get("columns") or {}
    notes = guards.apply_chain_guards(page_images, lines_by_page,
                                      ledger=ledger, file=name)
    crops, crop_notes = page_render.crop_pdf_regions(data, page_images)
    notes += crop_notes
    if not crops:
        return notes
    extra, trace, cross_notes = crosspage.stitch_cross_questions(
        name, data, page_images, lines_by_page, columns, crops)
    notes += cross_notes
    if trace and ledger is not None:
        ledger_progress(ledger, "%s 跨页题 %d 道已按 D15 纵拼，两段原图随题留存"
                        % (name, len(trace)), "ok")
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
            key = (page_no, int(crop["index"]))
            region.update(trace.get(key) or {})
            asset_id = "img_auto_%d_%d" % key
            items.append({
                "question": auto_split_shell(page_no, crop.get("no"), asset_id,
                                             title, region),
                "assets": [{"id": asset_id,
                            "data_url": "data:image/png;base64,"
                                        + base64.b64encode(crop["png"]).decode("ascii")}]
                          + (extra.get(key) or []),
                "page_no": page_no,
            })
            regions.append(region)
    if not items:
        return notes
    try:
        result = service.save_draft(items, batch_id=batch_id,
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
        service.set_batch_pages(batch_id, page_images)
    except Exception:  # noqa: BLE001 - 绑定写不进去只影响重开批次的状态标记
        pass
    return notes


# ---------------------------------------------------------------- 坏题分诊与回填


def _engine_note(picked: str, kind: str, auto_note: str) -> str:
    """具体档的人话路由说明由 catalog 的 route_note_* 声明；自动档底座自述。"""
    if picked == "auto":
        return auto_note
    from app.core.ingest import registry
    for item in registry.catalog():
        if str(item.get("id")) == picked and item.get("route_note_" + kind):
            return str(item["route_note_" + kind])
    return "版面：只跑选中的版面引擎，失败不降级其他引擎。" if kind == "layout" else "识别：只交选中的识别引擎，失败不降级。"


def scan_route(layout_engine: str = layout_router.LAYOUT_AUTO,
               recognize_engine: str = recognize_router.RECOGNIZE_AUTO,
               health: dict[str, Any] | None = None,
               gate_note: str = "") -> dict[str, Any]:
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
    route["note"] = (
        _engine_note(picked_layout, "layout",
                     "版面：自动，图片卷先本地 OCR 切题，不达标退回文本层 → 本机 YOLO → 云端。")
        + _engine_note(picked_recognize, "recognize",
                       "识别：自动按卷型分流——纯图卷走默认整题座；文字卷文字直取＋公式裁图送默认公式座，失败显性不偷换。"))
    if not text_layer:
        route["note"] += " 本卷没有文本层，本地切题可能留下占位题。"
    if health.get("garbled"):
        route["note"] += (" 文本层有 %d 个字形读不出，已标记待人工核对。"
                          % int(health.get("missing_chars") or 0))
    append_notes(route, [gate_note])
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
                          layout: dict[str, Any] | None = None,
                          gate_note: str = "") -> dict[str, Any]:
    """切完题后的分诊：算坏题率、打一行静默统计，再交给识别调度员。

    返回值就是写回批次的 route：老师重开批次时能看到这次选了哪两个引擎、
    实际由谁探出题块、坏题率多少、最后补回几道；闸口归一原因不被识别汇总吞掉。
    """
    from app.core.pending import service

    try:
        items = service.list_batch_questions(batch_id).get("items") or []
    except Exception:  # noqa: BLE001 - 批次刚被删/库读不通时只影响统计
        items = []
    report = ingest_quality.triage_documents([item.get("question") for item in items])
    log_stats(report)
    route = scan_route(layout_engine, recognize_engine, health, gate_note)
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
        save_route(service, batch_id, snapshot)

    return append_notes(await recognize_router.fill_batch(
        batch_id, items, recognize_engine, report, route, progress), [gate_note])
