"""纯本地版面探路：文本层坐标 → 单栏 / 双栏题块。

这是矩阵里永远排第一的一级——不联网、不加载模型、没有密钥也能跑。
标准单栏直接沿用 ``page_render`` 算好的题块，只把阅读顺序按坐标校正；
双栏卷则按栏切开，先左栏从上到下、再右栏从上到下重排，避免 PDF 内容流
把左右两栏的题号串成一条假链。
"""

from __future__ import annotations

from typing import Any

from app.core import page_render
from app.core.page_render_regions import (
    _HEAD_PAD_PT,
    _PDF_FOOTER,
    _PDF_HEAD,
    _PDF_INSTRUCTION,
    _REGION_GAP_PT,
    _REGION_LABEL_LIMIT,
    _REGION_TEXT_LIMIT,
    _question_regions,
)

_DEFAULT_DPI = 200.0
_EDGE_PAD_PT = 4.0
_GUTTER_MIN_PT = 8.0


def detect(request: dict[str, Any]) -> dict[str, Any]:
    """请求 → 每页题块；本地文本层读不出就如实交失败。"""
    entries = request.get("pages") or []
    try:
        layout_pages = page_render.pdf_page_lines(request.get("data") or b"")
    except Exception:  # noqa: BLE001 - 文本层坏掉只该降级，不该拖垮整批
        layout_pages = []
    by_page = {int(item["page"]): item for item in layout_pages}
    pages: dict[int, list[dict[str, Any]]] = {}
    columns: dict[int, int] = {}
    for entry in entries:
        try:
            page_no = int(entry.get("page") or 0)
        except (TypeError, ValueError):
            continue
        if page_no <= 0:
            continue
        info = by_page.get(page_no)
        existing = entry.get("regions") or []
        if info:
            regions, count = _arrange(info, entry, existing)
        else:
            regions, count = _ordered(existing), 1
        if regions:
            pages[page_no] = regions
            columns[page_no] = count
    ok = bool(pages)
    return {
        "ok": ok,
        "engine": "python",
        "pages": pages,
        "columns": columns,
        "detail": (f"本地文本层探出 {len(pages)} 页题块" if ok
                   else "本地文本层没有探出题块"),
    }


def _arrange(info: dict[str, Any], entry: dict[str, Any],
             existing: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """一页的行清单 → (题块, 栏数)；双栏切不开就退回单栏老路。"""
    split = _column_split(info)
    if split is not None:
        regions = _column_regions(info, entry, split)
        if regions:
            return regions, 2
    if existing:
        return _ordered(existing), 1
    return _fallback_regions(info, entry), 1


def _content_lines(info: dict[str, Any]) -> list[dict[str, Any]]:
    return [line for line in info.get("lines") or []
            if not _PDF_FOOTER.search(str(line.get("text") or ""))]


def _column_split(info: dict[str, Any]) -> float | None:
    """左右两半都有成串题号、且中间有空槽，才认作双栏；返回空槽中心。"""
    width = float(info.get("width_pt") or 0)
    lines = _content_lines(info)
    if width <= 0 or len(lines) < 8:
        return None
    heads = []
    for line in lines:
        matched = _PDF_HEAD.match(str(line.get("text") or ""))
        if matched and not _PDF_INSTRUCTION.search(str(line.get("text") or "")):
            heads.append(line)
    left = [line for line in heads if (line["left"] + line["right"]) / 2 < width * 0.5]
    right = [line for line in heads if (line["left"] + line["right"]) / 2 > width * 0.5]
    if len(left) < 2 or len(right) < 2:
        return None
    left_edge = max(line["right"] for line in left)
    right_edge = min(line["left"] for line in right)
    if right_edge - left_edge < max(_GUTTER_MIN_PT, width * 0.02):
        return None
    return (left_edge + right_edge) / 2


def _column_regions(info: dict[str, Any], entry: dict[str, Any],
                    split: float) -> list[dict[str, Any]]:
    """按栏切题：先左栏后右栏，栏内按纵向坐标从上到下。"""
    width = float(info["width_pt"])
    height = float(info["height_pt"])
    pixel_w, pixel_h = _pixels(entry, width, height)
    scale_x, scale_y = pixel_w / width, pixel_h / height
    lines = _content_lines(info)
    columns = ([line for line in lines if line["left"] < split],
               [line for line in lines if line["left"] >= split])
    regions: list[dict[str, Any]] = []
    for column_lines in columns:
        heads = []
        for line in column_lines:
            matched = _PDF_HEAD.match(str(line.get("text") or ""))
            if matched and not _PDF_INSTRUCTION.search(str(line.get("text") or "")):
                heads.append((int(matched.group(1)), line))
        heads.sort(key=lambda pair: pair[1]["top"], reverse=True)
        if not heads:
            continue
        floor_pt = min((line["bottom"] for line in column_lines), default=0.0)
        for index, (number, head) in enumerate(heads):
            top_pt = head["top"] + _HEAD_PAD_PT
            if index + 1 < len(heads):
                bottom_pt = heads[index + 1][1]["top"] + _REGION_GAP_PT
            else:
                bottom_pt = floor_pt + _REGION_GAP_PT
            if top_pt - bottom_pt < 2.0:
                continue
            body = [line for line in column_lines
                    if bottom_pt <= (line["top"] + line["bottom"]) / 2 <= top_pt]
            if not body:
                body = [head]
            left_pt = max(0.0, min(line["left"] for line in body) - _EDGE_PAD_PT)
            right_pt = min(width, max(line["right"] for line in body) + _EDGE_PAD_PT)
            text = "\n".join(line["text"] for line in
                             sorted(body, key=lambda line: line["top"], reverse=True))
            regions.append({
                "no": number,
                "x": round(left_pt * scale_x, 1),
                "y": round((height - top_pt) * scale_y, 1),
                "w": round(max(1.0, (right_pt - left_pt) * scale_x), 1),
                "h": round(max(8.0, (top_pt - bottom_pt) * scale_y), 1),
                "label": " ".join(str(head["text"]).split())[:_REGION_LABEL_LIMIT],
                "text": text.strip()[:_REGION_TEXT_LIMIT],
            })
    return regions


def _pixels(entry: dict[str, Any], width: float, height: float) -> tuple[float, float]:
    pixel_w = float(entry.get("width") or 0)
    pixel_h = float(entry.get("height") or 0)
    if pixel_w <= 0:
        pixel_w = width * _DEFAULT_DPI / 72.0
    if pixel_h <= 0:
        pixel_h = height * _DEFAULT_DPI / 72.0
    return pixel_w, pixel_h


def _fallback_regions(info: dict[str, Any],
                      entry: dict[str, Any]) -> list[dict[str, Any]]:
    width = float(info["width_pt"])
    height = float(info["height_pt"])
    pixel_w, pixel_h = _pixels(entry, width, height)
    return _question_regions(_content_lines(info), width, height, int(pixel_w), int(pixel_h))


def _ordered(regions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """单栏只校正阅读顺序：从上到下；同一高度按从左到右。"""
    return sorted(regions, key=lambda item: (float(item.get("y") or 0),
                                             float(item.get("x") or 0)))
