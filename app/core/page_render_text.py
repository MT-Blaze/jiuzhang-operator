"""Word / 纯文本 → 一页页 SVG 文本还原图（纯标准库，不联网）。"""

from __future__ import annotations

import html
import re
import unicodedata
from typing import Any

from app.core.pending_assets import write_generated_asset
from app.core.page_render_common import (
    FONT_SIZE, FOOTER_Y, LINE_HEIGHT, MARGIN_TOP, MARGIN_X, MAX_LINES,
    PAGE_HEIGHT, PAGE_WIDTH, TEXT_WIDTH, _FONT_FAMILY, _entry, _spread_pages,
)

# ---------------------------------------------------------------- 文本还原页


def _facsimile(name: str, text: str, documents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[int]]:
    pages = _paginate(text)
    if not pages:
        return [], []
    anchored = _anchors(text, documents, pages)
    total = len(pages)
    entries: list[dict[str, Any]] = []
    for index, page in enumerate(pages, start=1):
        svg = _svg_page(page["lines"], index, total, name)
        try:
            stored = write_generated_asset(svg.encode("utf-8"), "image/svg+xml")
        except Exception:  # noqa: BLE001 - 一页写不进去，其余页照常
            continue
        entries.append(_entry(stored, index))
    if not entries:
        return [], []
    if anchored:
        return entries, anchored
    return entries, _spread_pages(len(entries), len(documents))


def _anchors(text: str, documents: list[dict[str, Any]],
             pages: list[dict[str, Any]]) -> list[int]:
    """每道题在源文本里的起点 → 页码。认不出锚就回空表，由调用方均匀摊开。"""
    starts = [page["start"] for page in pages]
    numbers = [str((document.get("source") or {}).get("question_no") or "")
               for document in documents]
    offsets: list[int] = []
    if numbers and all(numbers):
        position = 0
        for number in numbers:
            pattern = re.compile(r"(?m)^\s*" + re.escape(number) + r"\s*[.．、:：)）]")
            hit = pattern.search(text, position)
            if hit is None:
                offsets = []
                break
            offsets.append(hit.start())
            position = hit.end()
    if not offsets:
        envs = list(re.finditer(r"\\begin\{(?:question|problem)\}", text))
        if envs and len(envs) >= len(documents):
            offsets = [hit.start() for hit in envs[:len(documents)]]
    if not offsets:
        return []
    doc_pages: list[int] = []
    for offset in offsets:
        page_no = 1
        for index, start in enumerate(starts, start=1):
            if offset >= start:
                page_no = index
            else:
                break
        doc_pages.append(page_no)
    return doc_pages


def _paginate(text: str) -> list[dict[str, Any]]:
    """按行折页：每页记下它从源文本的第几个字符开始，供题号锚点定位。"""
    pages: list[dict[str, Any]] = []
    page_lines: list[str] = []
    page_start = 0
    offset = 0
    for raw_line in text.split("\n"):
        for display, line_start in _wrap_line(raw_line, offset):
            if not page_lines:
                page_start = line_start
            if len(page_lines) >= MAX_LINES:
                pages.append({"start": page_start, "lines": page_lines})
                page_lines = []
                page_start = line_start
            page_lines.append(display)
        offset += len(raw_line) + 1
    if page_lines or not pages:
        pages.append({"start": page_start, "lines": page_lines})
    return pages


def _wrap_line(raw: str, offset: int) -> list[tuple[str, int]]:
    if not raw.strip():
        return [("", offset)]
    parts: list[tuple[str, int]] = []
    current: list[str] = []
    current_start = offset
    width = 0.0
    for index, char in enumerate(raw):
        char_width = _char_width(char)
        if current and width + char_width > TEXT_WIDTH:
            parts.append(("".join(current), current_start))
            current = []
            current_start = offset + index
            width = 0.0
        current.append("    " if char == "\t" else char)
        width += char_width if char != "\t" else FONT_SIZE * 2
    parts.append(("".join(current), current_start))
    return parts


def _char_width(char: str) -> float:
    if char == "\t":
        return FONT_SIZE * 2
    if unicodedata.east_asian_width(char) in ("W", "F"):
        return float(FONT_SIZE)
    return FONT_SIZE * 0.55


def _svg_page(lines: list[str], page: int, total: int, title: str) -> str:
    body = []
    for index, line in enumerate(lines):
        y = MARGIN_TOP + index * LINE_HEIGHT
        body.append(f'<tspan x="{MARGIN_X}" y="{y}">{html.escape(line)}</tspan>')
    label = "第 " + str(page) + " 页 / 共 " + str(total) + " 页"
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_WIDTH}"'
        f' height="{PAGE_HEIGHT}" viewBox="0 0 {PAGE_WIDTH} {PAGE_HEIGHT}">'
        f'<rect width="{PAGE_WIDTH}" height="{PAGE_HEIGHT}" fill="#ffffff"/>'
        f'<text x="{PAGE_WIDTH - MARGIN_X}" y="52" text-anchor="end"'
        f' font-family="{_FONT_FAMILY}" font-size="18" fill="#9a9388">'
        f'{html.escape(title)}</text>'
        f'<text font-family="{_FONT_FAMILY}" font-size="{FONT_SIZE}"'
        f' fill="#1d1a16" xml:space="preserve">'
        + "".join(body)
        + '</text>'
        f'<text x="{PAGE_WIDTH // 2}" y="{FOOTER_Y}" text-anchor="middle"'
        f' font-family="{_FONT_FAMILY}" font-size="18" fill="#9a9388">'
        f'{label}</text>'
        '</svg>'
    )
