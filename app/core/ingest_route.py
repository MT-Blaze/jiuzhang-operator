"""解析体检 → 批次路由标记与自动切图（从 ``ingest`` 拆出，单文件 800 行上限）。

通道一只写提示、绝不自动调 AI；通道二先试 MinerU，连不上或没拆出题就退回切图。
切图落池要复用 ``ingest`` 里的文档构造函数，两处对 ``ingest`` 的取用一律延迟到
调用期——``ingest`` 在导入时会先加载本模块，模块级反向导入必成环。
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from app.core import ai_center, mineru_extract, page_render, scan_text


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
        note = "纯扫描件：文本层读不出字，已退回切图模式，可逐框确认或点【✨ AI 识别本题】。"
    elif channel == "mineru":
        note = "纯扫描件：已走 MinerU 识别，正文来自 MinerU，题图仍以原卷为准。"
    elif garbled:
        note = ("文本层有 %d 个字形读不出（疑似乱码/公式字体缺映射）："
                "不会自动调用 AI，需要时点【✨ AI 识别本题】。"
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
                         "可逐框确认或点【✨ AI 识别本题】。")
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
