"""原卷页面图：把拖进来的每一份卷子变成审核台左栏能看的页面。

页面图属**批次层**（中转站），不挂任何题身——它只是老师拿来做对照的原卷，
不参与查重指纹，也不随题目入库。三种来源三条路：

- 图片：原件本身就是页面图，复制进 ``pending_assets/``，不重采样；
- PDF：本机有 ``pdftoppm`` 就按 150 dpi 逐页出 PNG；没有就退到文本层还原；
- Word / 纯文本：没有 Word/LibreOffice 也能出一页页 SVG 文本还原图
  （纯标准库，不引第三方渲染器，不联网）。

SVG 页与 PNG 页在左栏是同一种东西：``<img>`` 读得出来、切图台裁得动。
"""

from __future__ import annotations

import html
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

from app.core.pending_assets import write_generated_asset
from app.core.pending_db import PENDING_ASSET_URI_PREFIX

# A4 @150dpi：1240 × 1754 像素。页面图只做对照，不冒充 300dpi 的成品切图。
PAGE_WIDTH = 1240
PAGE_HEIGHT = 1754
MARGIN_X = 96
MARGIN_TOP = 140
FONT_SIZE = 28
LINE_HEIGHT = 44
FOOTER_Y = PAGE_HEIGHT - 44
MAX_LINES = (PAGE_HEIGHT - MARGIN_TOP - 80) // LINE_HEIGHT
MAX_PAGES = 40
TEXT_WIDTH = PAGE_WIDTH - MARGIN_X * 2

# XML 里禁用标签的检查在 pending_assets；这里只负责生成干净内容。
_FONT_FAMILY = ("'Microsoft YaHei','PingFang SC','Noto Sans CJK SC',"
                "'SimSun',sans-serif")


def build_pages(name: str, kind: str, data: bytes, text: str,
                documents: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[int], list[str]]:
    """一个文件 → (页面图清单, 每道题来自第几页, 警告)。

    页面图清单的每一项都能直接回给插件：``{"name","uri","page"}``。
    ``doc_pages`` 与 ``documents`` 等长，1 起数。
    """
    warnings: list[str] = []
    count = max(0, len(documents))
    if kind == "image":
        mime = _image_mime(data)
        if not mime:
            return [], [], [f"{name}：图片格式认不出来，没生成原卷页"]
        name_on_disk = write_generated_asset(data, mime)
        return [_entry(name_on_disk, 1)], [1] * count, warnings
    if kind == "pdf":
        entries, pdf_warnings = _pdf_pages(data)
        warnings.extend(pdf_warnings)
        if entries:
            return entries, _spread_pages(len(entries), count), warnings
        if not text.strip():
            return [], [], warnings
        # 没有 pdftoppm 时退到文本层还原：至少有页可看，且明说这是文本还原。
        warnings.append(f"{name}：本机没有 PDF 页面渲染器，按文本层还原页面图")
        facsimile, doc_pages = _facsimile(name, text, documents)
        return facsimile, doc_pages, warnings
    if not text.strip():
        return [], [], warnings
    facsimile, doc_pages = _facsimile(name, text, documents)
    return facsimile, doc_pages, warnings


def _entry(name: str, page: int) -> dict[str, Any]:
    return {"name": name, "uri": PENDING_ASSET_URI_PREFIX + name, "page": page}


# ---------------------------------------------------------------- 图片与 PDF


def _image_mime(raw: bytes) -> str:
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if raw.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if len(raw) >= 12 and raw.startswith(b"RIFF") and raw[8:12] == b"WEBP":
        return "image/webp"
    return ""


def _pdf_pages(data: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    """PDF 逐页出 PNG；本机没有 ``pdftoppm`` 就如实返回空清单。"""
    exe = shutil.which("pdftoppm")
    if not exe:
        return [], []
    entries: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="jz-pdf-") as folder:
            source = Path(folder) / "source.pdf"
            source.write_bytes(data)
            prefix = Path(folder) / "page"
            command = [exe, "-png", "-r", "150", "-f", "1", "-l", str(MAX_PAGES),
                       str(source), str(prefix)]
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.run(command, check=False, timeout=180, creationflags=flags,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rendered = sorted(
                Path(folder).glob("page-*.png"),
                key=lambda path: int(re.sub(r"\D", "", path.stem) or 0),
            )
            for index, path in enumerate(rendered[:MAX_PAGES], start=1):
                raw = path.read_bytes()
                if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                    continue
                try:
                    entries.append(_entry(write_generated_asset(raw, "image/png"), index))
                except Exception:  # noqa: BLE001 - 单页太大事小，不拖垮整份卷子
                    continue
    except (OSError, subprocess.SubprocessError):
        return [], []
    return entries, []


def _spread_pages(page_count: int, item_count: int) -> list[int]:
    """PDF 没有逐题页号：按录入顺序把题均匀摊到页上，只做展示定位。"""
    if item_count <= 0:
        return []
    if page_count <= 0:
        return []
    if page_count == 1:
        return [1] * item_count
    return [min(page_count, 1 + (index * page_count) // item_count)
            for index in range(item_count)]


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
