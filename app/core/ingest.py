"""拖入文件的分拣与解析：PDF / Word / TeX / MD / 图片 → 中转站里的一批待审题。

分拣**只看后缀**：老师拖进来的是什么就按什么走，绝不信文件自报的 MIME。

- 文本类（``.tex`` / ``.md`` / ``.txt``）：轻量解析。认得两种版式——
  录题工作台的 exam-zh 源码（``\\begin{question}`` / ``\\begin{solution}``），
  以及普通文本（按题号切题，再拆选项、提答案）。
- ``.docx``：标准库 ``zipfile`` 解出 ``word/document.xml`` 的纯文本，再走文本类同一条路。
- ``.pdf``：**一律当原卷大图**，逐页渲染成页图；文本层抽出题号、文字与坐标，
  左栏自动画切分框。解析完成后底座直接按每块坐标从原 PDF 裁图，把识别出的
  题全部生成待审题排进中间栏。
- 图片：走 OCR（AI 视觉）。
- ``.zip``：**静默忽略**——插件安装包走的是另一条道。

**认不出就不编**：OCR 失败时如实记一条「待识别」的待审题（图片挂在那儿，题干留占位），
老师自己在审核台里补。底座宁可交白卷，也不生成一道凭空捏造的题。

本文件只负责批次编排与后台作业；文本切题在 ``ingest_text``，
单文件分拣与 OCR 在 ``ingest_media``，版面与识别引擎各自住在 ``layout/``、``recognize/``。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core import page_render, text_health, wire
from app.core.ingest_media import _items_from_file, _page_of, _placeholder
from app.core.ingest_route import (
    attach_layout,
    auto_split_pages,
    fill_scan_batch,
    log_documents,
    route_payload,
    save_route,
    scan_route,
)
from app.core.ingest_text import (
    DEFAULT_DIFFICULTY,
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_IMAGE_BYTES,
    IngestError,
    _document,
    build_documents,
    classify,
    decode_bytes,
    decode_text,
    extract_docx_text,
)
from app.core.layout import layout_router
from app.core.recognize import recognize_router

__all__ = [
    "classify",
    "decode_text",
    "extract_docx_text",
    "build_documents",
    "ingest_files",
    "stage_ingest",
    "run_ingest_jobs",
]


async def ingest_files(files: Any, layout_engine: str = layout_router.LAYOUT_AUTO,
                       recognize_engine: str = recognize_router.RECOGNIZE_AUTO) -> dict[str, Any]:
    """把拖进来的一批文件变成中转站里的待审题（**同步跑完**）。

    ``files`` 形如 ``[{"name": "卷子.pdf", "data_url": "data:application/pdf;base64,..."}]``。
    **一个文件一个批次**，各批独立解析；返回聚合账：
    ``{"batch_id", "batch_ids", "batches", "saved_ids", "warnings", "ignored", "kinds"}``。

    线上走的是两段式（``stage_ingest`` + ``run_ingest_jobs``）：批次先立起来，
    识别放后台，老师不用盯着屏幕等 OCR。这里保留同步版给脚本与测试用。
    """
    staged = stage_ingest(files, layout_engine=layout_engine,
                          recognize_engine=recognize_engine)
    groups = staged.pop("jobs", [])
    for group in groups:
        await run_ingest_jobs(group["batch_id"], group["jobs"],
                              group["layout_engine"], group["recognize_engine"])
    if groups:
        # 同步版跑完要按解析后的真账回报：题数与 id 都可能变了。
        from app.core import pending_bank
        refreshed: list[dict[str, Any]] = []
        saved_ids: list[str] = []
        for one in staged["batches"]:
            rows = pending_bank.list_batch_questions(one["batch_id"])
            ids = [row["id"] for row in rows["items"]]
            saved_ids.extend(ids)
            card = one.get("batch")
            for entry in pending_bank.batch_list()["batches"]:
                if entry["batch_id"] == one["batch_id"]:
                    card = entry
                    break
            refreshed.append({**one, "saved_ids": ids, "batch": card})
        staged["batches"] = refreshed
        staged["saved_ids"] = saved_ids
    return staged


def stage_ingest(files: Any, layout_engine: str = layout_router.LAYOUT_AUTO,
                 recognize_engine: str = recognize_router.RECOGNIZE_AUTO) -> dict[str, Any]:
    """第一段：分拣、解码，**按文件各立一个批次**。

    老师拖进 9 份卷子就立 9 个批次（B-002、B-003……），各认各的、各解析各的。
    Word / 文本类先放一条「正在解析」占位题；PDF 一律当原卷大图，连占位题都不放，
    后台渲染出页图后挂到批次上，并按题块坐标自动裁图、用题块文字填出待审题。

    返回聚合账：``{"batch_id", "batch_ids", "batches", "saved_ids", "warnings",
    "ignored", "kinds", "jobs"}``；``jobs`` 按批次分组，``batch_id`` 是第一份的批次号。
    """
    if not isinstance(files, list) or not files:
        raise IngestError("没有要处理的文件")
    if len(files) > MAX_FILES:
        raise IngestError(f"一次最多处理 {MAX_FILES} 个文件")
    picked_layout = layout_router.normalize_engine(layout_engine)
    picked_recognize = recognize_router.normalize_engine(recognize_engine)

    ignored: list[str] = []
    loaded: list[tuple[str, bytes]] = []

    # 先把整包验一遍再落批次：后面的文件不合格时，前面的批次不该已经建出来。
    for entry in files:
        if not isinstance(entry, dict):
            raise IngestError("每个文件都要是对象")
        name = str(entry.get("name") or "").strip() or "未命名文件"
        if classify(name) == "zip":
            # 插件安装包走另一条道：这里静默忽略，不提示、不建批次。
            ignored.append(name)
            continue
        data = decode_bytes(entry.get("data_url") or entry.get("data"))
        if len(data) > MAX_FILE_BYTES:
            raise IngestError(f"{name}：文件太大（上限 32 MiB）")
        if not data:
            raise IngestError(f"{name}：文件是空的")
        loaded.append((name, data))

    if not loaded:
        return {"batch_id": "", "batch_ids": [], "batches": [], "saved_ids": [],
                "warnings": [], "ignored": ignored, "kinds": [], "jobs": []}

    batches: list[dict[str, Any]] = []
    warnings: list[str] = []
    kinds: list[str] = []
    saved_ids: list[str] = []
    job_groups: list[dict[str, Any]] = []
    for name, data in loaded:
        one = _stage_one_batch(name, data)
        one_jobs = one.pop("jobs", [])
        if one_jobs:
            job_groups.append({"batch_id": one["batch_id"], "jobs": one_jobs,
                               "layout_engine": picked_layout,
                               "recognize_engine": picked_recognize})
        batches.append(one)
        warnings.extend(one.get("warnings") or [])
        kinds.extend(one.get("kinds") or [])
        saved_ids.extend(one.get("saved_ids") or [])

    first = batches[0]
    return {
        "batch_id": first["batch_id"],
        "batch": first.get("batch"),
        "batch_ids": [one["batch_id"] for one in batches],
        "batches": batches,
        "saved_ids": saved_ids,
        "warnings": warnings,
        "ignored": ignored,
        "kinds": kinds,
        "layout_engine": picked_layout,
        "recognize_engine": picked_recognize,
        "jobs": job_groups,
    }


def _is_scan_source(name: str) -> bool:
    """这份文件是不是按「原卷大图」走：PDF 一律是（坐标由 page_render 附上）。"""
    return classify(name) == "pdf"


def _stage_one_batch(name: str, data: bytes) -> dict[str, Any]:
    """一份文件立一个批次。

    Word / 文本类先放一条「正在解析」的占位题，识别完就地替换；
    PDF 一律当原卷大图，连占位题都不放——只立批次，页图由后台渲染后挂到批次上。
    """
    from app.core import pending_bank

    # 原件在老师自己的盘上，底座只在工作区里留一份只读副本，批次审完即删。
    backup = wire.dumps([pending_bank.store_source_backup(name, data)],
                        ensure_ascii=False, separators=(",", ":"))
    scan_only = _is_scan_source(name)
    if scan_only:
        result = pending_bank.create_batch(source_backup=backup, source_name=name,
                                           scan=True)
        warnings = [f"{name}：已按原卷大图导入。页面图渲染完成后，"
                    "识别出的每道题会自动裁好并排进待审池，左侧绿框可拖拽微调。"]
    else:
        result = pending_bank.save_draft(
            [{"question": _placeholder(f"（正在解析：{name}）")}],
            source_backup=backup,
            source_name=name,
            origin="ingest",
        )
        warnings = []
    result["warnings"] = warnings
    result["ignored"] = []
    result["kinds"] = [classify(name)]
    result["page_only"] = scan_only
    result["jobs"] = [{
        "pending_id": result["saved_ids"][0] if result.get("saved_ids") else "",
        "name": name,
        "data": data,
        "page_only": scan_only,
    }]
    return result


def _image_shell(name: str, page_images: list[dict[str, Any]]) -> dict[str, Any]:
    """图片走全量 OCR 前先落一条占位题：题图立刻可见，正文等模型回填。"""
    entry = page_images[0] if page_images else {}
    uri = str(entry.get("uri") or "")
    asset_id = str(entry.get("name") or "page_1")
    return {
        "schema_version": "2.0",
        "type": "solution",
        "stem": f"（自动 OCR：{name}，正在识别）",
        "difficulty": DEFAULT_DIFFICULTY,
        "source": {"paper_title": Path(name or "").stem},
        "images": ([{"id": asset_id, "role": "stem", "uri": uri}] if uri else []),
    }


def _apply_layout(page_images: list[dict[str, Any]],
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


async def run_ingest_jobs(batch_id: str, jobs: list[dict[str, Any]],
                          layout_engine: str = layout_router.LAYOUT_AUTO,
                          recognize_engine: str = recognize_router.RECOGNIZE_AUTO) -> None:
    """第二段：识别。

    - Word / 文本类：识别出来的题**就地替换**那条「正在解析」的占位题；
    - PDF：先出原卷页图，版面引擎（纯 Python 永远第一）探出题块，再自动切图；
      切完由识别引擎（本地 → AI → MinerU）按坏题率决定补哪些题。
    """
    from app.core import pending_bank
    from app.core.pending_assets import drop_assets

    picked_layout = layout_router.normalize_engine(layout_engine)
    picked_recognize = recognize_router.normalize_engine(recognize_engine)
    for job in jobs or []:
        pending_id = str((job or {}).get("pending_id") or "")
        name = str((job or {}).get("name") or "")
        data = (job or {}).get("data") or b""
        page_only = bool((job or {}).get("page_only"))
        if not name or not batch_id:
            continue
        if not page_only and not pending_id:
            continue
        page_images: list[dict[str, Any]] = []
        doc_pages: list[int] = []
        scan_mode = page_only
        image_ocr = False
        if page_only:
            documents, kind, source_text = [], "pdf", ""
        else:
            kind = classify(name)
            image_ocr = kind == "image" and len(data) <= MAX_IMAGE_BYTES
            if image_ocr:
                # 图片本身就是页图：先落占位壳，再交给识别引擎（本地 → AI/MinerU）。
                documents, kind, source_text, scan_mode = [], "image", "", False
            else:
                try:
                    documents, _notes, kind, source_text, scan_mode = await _items_from_file(name, data)
                except Exception:  # noqa: BLE001 - 后台单份失败不许带崩整批
                    documents = []
                    kind = ""
                    source_text = ""
                    scan_mode = False
        # 原卷页在识别之后立刻出：哪怕一道题都没拆出来，老师也得能对着原卷补录。
        try:
            page_images, doc_pages, _page_notes = page_render.build_pages(
                name, kind, data, source_text, documents)
        except Exception:  # noqa: BLE001 - 页面图失败只影响左栏，不耽误拆题
            page_images, doc_pages = [], []

        if scan_mode:
            health = page_render.pdf_text_health(data)
            route = scan_route(picked_layout, picked_recognize, health)
            if page_images:
                layout = await layout_router.run(name, data, page_images, picked_layout)
                _apply_layout(page_images, layout)
                attach_layout(route, layout)
                try:
                    pending_bank.set_batch_pages(batch_id, page_images)
                except Exception:  # noqa: BLE001 — 挂不上页图就清掉文件，批次留着
                    drop_assets(page_images)
                    continue
                # 自动切图入池：坐标已经算好，不再等老师逐框点确认。
                auto_split_pages(name, data, batch_id, page_images)
                if any((entry.get("regions") or []) for entry in page_images):
                    route = await fill_scan_batch(
                        batch_id, picked_recognize, health, picked_layout, layout)
            if pending_id:
                # 老式占位轮留下的那条占位题：页图已挂上，清掉它不再占池。
                try:
                    pending_bank.delete_pending(pending_id)
                except pending_bank.PendingError:
                    pass
            save_route(pending_bank, batch_id, route)
            continue

        if image_ocr:
            health = {"has_text_layer": False, "garbled": False,
                      "text_chars": 0, "missing_chars": 0}
            route = scan_route(picked_layout, picked_recognize, health)
            shell = _image_shell(name, page_images)
            try:
                pending_bank.save_draft(
                    [{"question": shell, "pending_id": pending_id, "page_no": 1}],
                    batch_id=batch_id, origin="ingest.ai_ocr", page_images=page_images)
            except Exception:  # noqa: BLE001 - 写不进去就退回占位题，卷子不能丢
                if page_images:
                    drop_assets(page_images)
                continue
            route = await fill_scan_batch(batch_id, picked_recognize, health, picked_layout)
            save_route(pending_bank, batch_id, route)
            continue

        health = text_health.text_health(source_text)
        route = route_payload("image" if kind == "image" else "text", health,
                               False if kind == "image" else None)
        items: list[dict[str, Any]] = []
        if documents:
            items.append({"question": documents[0], "pending_id": pending_id,
                          "page_no": _page_of(doc_pages, 0)})
            items.extend({"question": document, "page_no": _page_of(doc_pages, index)}
                         for index, document in enumerate(documents[1:], start=1))
        else:
            items.append({
                "question": _placeholder(f"（待识别：{name}，识别没成功，请老师补录）"),
                "pending_id": pending_id,
                "page_no": 1,
            })
        try:
            pending_bank.save_draft(items, batch_id=batch_id, origin="ingest",
                                    page_images=page_images)
        except Exception:  # noqa: BLE001 - 这一份写不进去就留着占位题，不动别的
            if page_images:
                drop_assets(page_images)
            continue
        log_documents(documents)
        save_route(pending_bank, batch_id, route)
