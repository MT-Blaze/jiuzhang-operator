"""原卷页面图：把拖进来的每一份卷子变成审核台左栏能看的页面。

页面图属**批次层**（中转站），不挂任何题身——它只是老师拿来做对照的原卷，
不参与查重指纹，也不随题目入库。三种来源三条路：

- 图片：原件本身就是页面图，复制进 ``pending_assets/``，不重采样；
- PDF：**一律**按 200 dpi 逐页渲染成 PNG 原卷大图，不区分有没有文本层。
  文本层只用来提取**题号、文字与坐标**，给左栏画自动切分框；页面图本身
  仍只认渲染结果，绝不拿文本层凑页面。渲染优先用随包分发的 ``pypdfium2``
  （Apache-2.0 / BSD-3-Clause，wheel 自带 PDFium，用户不用装 TeX Live 或
  Poppler）；内置引擎缺席或打不开时，才降级到开发机上的 ``pdftoppm``；
- Word / 纯文本：没有 Word/LibreOffice 也能出一页页 SVG 文本还原图
  （纯标准库，不引第三方渲染器，不联网）。

SVG 页与 PNG 页在左栏是同一种东西：``<img>`` 读得出来、切图台裁得动。
"""

from __future__ import annotations

import html
import math
import re
import shutil
import struct
import subprocess
import tempfile
import unicodedata
import zlib
from pathlib import Path
from typing import Any

from app.core.pending_assets import write_generated_asset
from app.core.pending_db import PENDING_ASSET_URI_PREFIX

try:  # 内置渲染器缺席只该降级，不该让整个模块导入失败。
    import pypdfium2 as _pdfium
except Exception:  # noqa: BLE001 - 缺库、坏 wheel 都按「没装上」处理
    _pdfium = None

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
# 原卷页图按 200 dpi 出：A4 约 1654×2339，框选裁下来的公式足够清楚。
PDF_RENDER_DPI = 200
# 自动切图另按 300 dpi 从原 PDF 直接裁：成品题图不经过 200 dpi 页图的二次采样。
PDF_CROP_DPI = 300

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
        # PDF 只出原卷大图：文本层不参与，渲染不出来就交白卷，绝不拿字凑页面。
        entries, pdf_warnings = _pdf_pages(data)
        warnings.extend(pdf_warnings)
        return entries, _spread_pages(len(entries), count), warnings
    if not text.strip():
        return [], [], warnings
    facsimile, doc_pages = _facsimile(name, text, documents)
    return facsimile, doc_pages, warnings


def _entry(name: str, page: int, **extra: Any) -> dict[str, Any]:
    entry = {"name": name, "uri": PENDING_ASSET_URI_PREFIX + name, "page": page}
    for key, value in extra.items():
        if value not in (None, [], ""):
            entry[key] = value
    return entry


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
    """PDF 逐页出 PNG：先走随包分发的 pypdfium2，出不了图再找本机 ``pdftoppm``。

    ``pdftoppm`` 只是开发机（TeX Live / Poppler）的兜底，不是产品依赖；
    两条路都不通就返回空清单并如实说明，绝不拿文本层凑页面。
    """
    entries, warnings = _pdf_pages_builtin(data)
    if entries:
        return entries, warnings
    fallback, fallback_warnings = _pdf_pages_pdftoppm(data)
    warnings.extend(fallback_warnings)
    if fallback:
        return fallback, warnings
    return [], warnings


def _pdf_pages_builtin(data: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    """pypdfium2（PDFium）逐页渲染；不落地临时 PDF，直接吃内存字节。"""
    if _pdfium is None:
        return [], ["内置 PDF 渲染器（pypdfium2）没有装上，原卷页图渲染不出来"]
    entries: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        document = _pdfium.PdfDocument(data)
    except Exception as error:  # noqa: BLE001 - 坏文件、加密、异种格式都交兜底
        return [], [f"内置 PDF 渲染器打不开这份文件（{error}）"]
    try:
        total_pages = len(document)
        for index in range(min(total_pages, MAX_PAGES)):
            try:
                page = document[index]
                bitmap = page.render(scale=PDF_RENDER_DPI / 72.0)
                try:
                    raw = bytes(bitmap.buffer)
                    width = int(bitmap.width)
                    height = int(bitmap.height)
                    png = _png_from_bitmap(bitmap, raw)
                    ink = _ink_rows(raw, width, height, int(bitmap.stride),
                                    int(bitmap.n_channels))
                    regions = _pdf_page_regions(page, width, height,
                                                ink_rows=ink, first_page=index == 0)
                finally:
                    bitmap.close()
                entries.append(_entry(write_generated_asset(png, "image/png"), index + 1,
                                      width=width, height=height, regions=regions))
            except Exception:  # noqa: BLE001 - 单页失败事小，不拖垮整份卷子
                warnings.append(f"第 {index + 1} 页渲染失败，已跳过")
        if total_pages > MAX_PAGES:
            warnings.append(f"只渲染前 {MAX_PAGES} 页（原件共 {total_pages} 页）")
    finally:
        document.close()
    return entries, warnings


# ---------- PDF 文本层 → 题块坐标（自动切分框的底账）----------
#
# 文本层只认「行」：每一行拿到 PDF 点坐标后换算成页面图像素坐标。题号连续
# 递增的一串才算一列题，页眉页脚的说明数字不参与；找不到任何题号就交空清单，
# 前端仍可手动框选——绝不按猜出来的区域硬切。
_PDF_HEAD = re.compile(r"^\s*(\d{1,2})\s*[.．、]\s*\S")
# 卷首说明与页眉页脚：这些行也常带「1. 2. 3.」，但都不是题。
_PDF_INSTRUCTION = re.compile(
    r"答题卡|答卷前|考试结束|考生|考场|座位号|注意事项|绝密|启用前|"
    r"姓名|班级|考号|准考证|密封线|本试卷共")
_PDF_SECTION = re.compile(r"^\s*[一二三四五六七八九十]+\s*[、.．]")
_PDF_FOOTER = re.compile(r"第\s*\d+\s*页\s*[（(]\s*共\s*\d+\s*页")
_REGION_TEXT_LIMIT = 1200
_REGION_LABEL_LIMIT = 48
# 题块上下各留一点呼吸位；相邻题之间至少留 5pt（约 14 像素 @200dpi），
# 绿框不再首尾相接，老师不会把下一题的选项误看成这一题的。
_HEAD_PAD_PT = 1.5
_REGION_GAP_PT = 5.0
_INK_PAD_PX = 6
# 页面图背景是白的；行内只要有明显偏暗的像素就算「有墨」，用于裁掉题块尾部空白。
_INK_TABLE = bytes(0 if value >= 245 else 1 for value in range(256))


def _pdf_page_regions(page: Any, pixel_width: int, pixel_height: int, *,
                      ink_rows: bytearray | None = None,
                      first_page: bool = False) -> list[dict[str, Any]]:
    """一页 PDF → 题块清单（页面图像素坐标）；文本层读不出来就当没有。"""
    try:
        page_width, page_height = (float(value) for value in page.get_size())
        lines = _pdf_text_lines(page)
    except Exception:  # noqa: BLE001 - 文本层坏了只影响自动框，不影响页图
        return []
    return _question_regions(lines, page_width, page_height, pixel_width, pixel_height,
                             ink_rows=ink_rows, first_page=first_page)


def _pdf_text_lines(page: Any) -> list[dict[str, Any]]:
    """按 PDFium 给出的换行符切行，并记下每行的点坐标包围盒。"""
    textpage = page.get_textpage()
    try:
        total = int(textpage.count_chars())
        lines: list[dict[str, Any]] = []
        chars: list[str] = []
        bounds = [math.inf, math.inf, -math.inf, -math.inf]

        def flush() -> None:
            nonlocal chars, bounds
            text = "".join(chars).strip()
            if text and bounds[0] < bounds[2] and bounds[1] < bounds[3]:
                lines.append({
                    "text": text,
                    "left": bounds[0],
                    "bottom": bounds[1],
                    "right": bounds[2],
                    "top": bounds[3],
                })
            chars = []
            bounds = [math.inf, math.inf, -math.inf, -math.inf]

        for index in range(total):
            char = textpage.get_text_range(index, 1)
            if char in ("\r", "\n"):
                flush()
                continue
            try:
                left, bottom, right, top = (float(value)
                                            for value in textpage.get_charbox(index))
            except Exception:  # noqa: BLE001 - 单个坏字形跳过，不拖垮整行
                continue
            if not all(math.isfinite(value) for value in (left, bottom, right, top)):
                continue
            if not char.strip():
                if chars and chars[-1] != " ":
                    chars.append(" ")
                continue
            chars.append(char)
            bounds[0] = min(bounds[0], left)
            bounds[1] = min(bounds[1], bottom)
            bounds[2] = max(bounds[2], right)
            bounds[3] = max(bounds[3], top)
        flush()
        return lines
    finally:
        textpage.close()


def _question_regions(lines: list[dict[str, Any]], page_width: float, page_height: float,
                      pixel_width: int, pixel_height: int, *,
                      ink_rows: bytearray | None = None,
                      first_page: bool = False) -> list[dict[str, Any]]:
    """行清单 → 每道题的像素包围盒。

    题号链只取「最长且连续递增」的一段：卷首作答说明也带「1. 2. 3.」，
    先按说明关键词滤掉；首页再从第一个大节标题（如「一、选择题」）之后找题号，
    双保险。纵向从本题题号行起、到下一题题号行前留一道缝；页尾题块最后按
    页面图的真实墨迹裁掉尾部空白（有图的地方墨迹会把它留住）。
    """
    if not lines or page_width <= 0 or page_height <= 0:
        return []
    if pixel_width <= 0 or pixel_height <= 0:
        return []
    footer_top = min((line["top"] for line in lines if _PDF_FOOTER.search(line["text"])),
                     default=None)
    content = [line for line in lines if not _PDF_FOOTER.search(line["text"])]
    start_at = 0
    if first_page:
        section = next((index for index, line in enumerate(content)
                        if _PDF_SECTION.match(line["text"])), None)
        if section is not None:
            start_at = section
    heads: list[tuple[int, int]] = []
    for position, line in enumerate(content):
        if position < start_at:
            continue
        matched = _PDF_HEAD.match(line["text"])
        if not matched or _PDF_INSTRUCTION.search(line["text"]):
            continue
        heads.append((position, int(matched.group(1))))
    run = _longest_number_run(heads)
    if not run:
        return []

    scale_x = pixel_width / page_width
    scale_y = pixel_height / page_height
    left = max(0.0, min(line["left"] for line in content) - 4.0)
    right = min(page_width, max(line["right"] for line in content) + 4.0)
    if right <= left:
        return []
    box_x = left * scale_x
    box_w = max(1.0, (right - left) * scale_x)
    page_bottom = (footer_top + _REGION_GAP_PT if footer_top is not None
                   else min(line["bottom"] for line in content) + _REGION_GAP_PT)

    regions: list[dict[str, Any]] = []
    for order, (position, number) in enumerate(run):
        line = content[position]
        top_pt = line["top"] + _HEAD_PAD_PT
        if order + 1 < len(run):
            stop = run[order + 1][0]
            bottom_pt = content[stop]["top"] + _REGION_GAP_PT
        else:
            stop = len(content)
            bottom_pt = page_bottom
        top_y = max(0.0, (page_height - top_pt) * scale_y)
        bottom_y = min(float(pixel_height), (page_height - bottom_pt) * scale_y)
        if bottom_y - top_y < 8.0:
            bottom_y = min(float(pixel_height), top_y + 8.0)
        y, h = _trim_to_ink(top_y, bottom_y - top_y, ink_rows, pixel_height)
        text = "\n".join(part["text"] for part in content[position:stop]).strip()
        regions.append({
            "no": number,
            "x": round(box_x, 1),
            "y": round(y, 1),
            "w": round(box_w, 1),
            "h": round(h, 1),
            "label": re.sub(r"\s+", " ", line["text"]).strip()[:_REGION_LABEL_LIMIT],
            "text": text[:_REGION_TEXT_LIMIT],
        })
    return regions


def _ink_rows(raw: bytes, width: int, height: int, stride: int,
              channels: int) -> bytearray:
    """逐行判断页面上有没有墨迹：背景纯白，任何明显偏暗的像素都算有内容。"""
    span = max(0, width * channels)
    rows = bytearray(height)
    if span <= 0:
        return rows
    for row in range(height):
        start = row * stride
        if 1 in raw[start:start + span].translate(_INK_TABLE):
            rows[row] = 1
    return rows


def _trim_to_ink(top: float, height: float, ink_rows: bytearray | None,
                 page_height: int) -> tuple[float, float]:
    """把题块的上下空白裁掉，四周留 ``_INK_PAD_PX`` 像素；裁完至少留 8 像素。"""
    if not ink_rows:
        return top, height
    start = max(0, int(round(top)))
    stop = min(page_height, int(round(top + height)))
    first = None
    last = None
    for row in range(start, stop):
        if ink_rows[row]:
            if first is None:
                first = row
            last = row
    if first is None or last is None:
        return top, height
    # 只许往框内收，不许向外扩：相邻两题的墨迹 padding 一旦外溢，
    # 绿框又会首尾叠在一起，正是这次要修掉的样子。
    new_top = max(start, first - _INK_PAD_PX)
    new_bottom = min(stop, last + 1 + _INK_PAD_PX)
    if new_bottom - new_top < 8:
        new_bottom = min(stop, new_top + 8)
        new_top = max(start, new_bottom - 8)
    return float(new_top), float(max(1, new_bottom - new_top))


def _longest_number_run(heads: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """最长的一段「题号连续递增」链；孤立的数字不切题。"""
    best: list[tuple[int, int]] = []
    current: list[tuple[int, int]] = []
    for head in heads:
        if current and head[1] == current[-1][1] + 1 and head[0] > current[-1][0]:
            current.append(head)
        else:
            if len(current) > len(best):
                best = current
            current = [head]
    if len(current) > len(best):
        best = current
    return best


def crop_pdf_regions(data: bytes, page_images: list[dict[str, Any]],
                     dpi: int = PDF_CROP_DPI) -> tuple[dict[int, list[dict[str, Any]]], list[str]]:
    """页图上的自动题块 → 从原 PDF 直接裁下来的 PNG（默认 300 dpi）。

    返回 ``{页码: [{index, no, region, png, width, height}]}`` 与警告。题块坐标
    是页面图像素；这里按页图与 PDF 点数的比例换回点数，再交给 PDFium 的
    ``crop=(left, bottom, right, top)``。任何一块裁不出来只跳过这一块，
    绝不拿空白图冒充切图。
    """
    if _pdfium is None:
        return {}, ["内置 PDF 渲染器（pypdfium2）没有装上，自动切图未执行"]
    crops: dict[int, list[dict[str, Any]]] = {}
    warnings: list[str] = []
    try:
        document = _pdfium.PdfDocument(data)
    except Exception as error:  # noqa: BLE001 - 打不开就交白卷，页图还在
        return {}, [f"自动切图打不开原 PDF（{error}）"]
    try:
        total = len(document)
        for entry in page_images or []:
            regions = entry.get("regions") if isinstance(entry, dict) else None
            if not isinstance(regions, list) or not regions:
                continue
            try:
                page_no = int(entry.get("page") or 0)
            except (TypeError, ValueError):
                continue
            if page_no < 1 or page_no > total:
                continue
            try:
                page = document[page_no - 1]
                page_width, page_height = (float(value) for value in page.get_size())
                pixel_width = float(entry.get("width") or 0) or page_width * PDF_RENDER_DPI / 72.0
                pixel_height = float(entry.get("height") or 0) or page_height * PDF_RENDER_DPI / 72.0
            except Exception:  # noqa: BLE001 - 单页尺寸读不出来只影响这一页
                warnings.append(f"第 {page_no} 页读不出尺寸，自动切图跳过")
                continue
            if page_width <= 0 or page_height <= 0 or pixel_width <= 0 or pixel_height <= 0:
                continue
            scale_x = page_width / pixel_width
            scale_y = page_height / pixel_height
            made: list[dict[str, Any]] = []
            for index, region in enumerate(regions):
                try:
                    x = float(region.get("x") or 0)
                    y = float(region.get("y") or 0)
                    w = float(region.get("w") or 0)
                    h = float(region.get("h") or 0)
                except (TypeError, ValueError):
                    continue
                left = max(0.0, x * scale_x)
                right = max(0.0, (pixel_width - x - w) * scale_x)
                top = max(0.0, y * scale_y)
                bottom = max(0.0, (pixel_height - y - h) * scale_y)
                if left + right >= page_width - 1 or top + bottom >= page_height - 1:
                    continue
                try:
                    bitmap = page.render(scale=dpi / 72.0,
                                         crop=(left, bottom, right, top))
                    try:
                        png = _png_from_bitmap(bitmap)
                        width = int(bitmap.width)
                        height = int(bitmap.height)
                    finally:
                        bitmap.close()
                except Exception as error:  # noqa: BLE001 - 单块失败不拖垮整页
                    warnings.append(
                        f"第 {page_no} 页第 {region.get('no') or index + 1} 块裁图失败（{error}）")
                    continue
                made.append({
                    "index": index,
                    "no": region.get("no") or index + 1,
                    "region": region,
                    "png": png,
                    "width": width,
                    "height": height,
                })
            if made:
                crops[page_no] = made
    except Exception as error:  # noqa: BLE001 - 整份裁图失败仍保留页图与手动框选
        warnings.append(f"自动切图中途失败（{error}）")
    finally:
        document.close()
    return crops, warnings


def _png_from_bitmap(bitmap: Any, raw: bytes | None = None) -> bytes:
    """PDFium 位图 → 纯标准库 PNG 字节（RGB，无依赖 Pillow）。

    200 dpi 的 A4 约 1654×2339：默认 3 通道 BGR；若遇到 4 通道就丢掉 alpha。
    """
    width = int(bitmap.width)
    height = int(bitmap.height)
    stride = int(bitmap.stride)
    channels = int(bitmap.n_channels)
    if channels not in (3, 4):
        raise ValueError("不认识的 PDF 位图通道数：" + str(channels))
    if raw is None:
        raw = bytes(bitmap.buffer)
    pixel_bytes = channels
    rows: list[bytes] = []
    for y in range(height):
        start = y * stride
        line = raw[start:start + width * pixel_bytes]
        rgb = bytearray(width * 3)
        if bitmap.rev_byteorder:
            rgb[0::3] = line[0::3]
            rgb[1::3] = line[1::3]
            rgb[2::3] = line[2::3]
        else:
            rgb[0::3] = line[2::3]
            rgb[1::3] = line[1::3]
            rgb[2::3] = line[0::3]
        rows.append(b"\x00" + bytes(rgb))
    return (_PNG_SIGNATURE
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + _png_chunk(b"IDAT", zlib.compress(b"".join(rows), 6))
            + _png_chunk(b"IEND", b""))


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(tag + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", checksum)


def _pdf_pages_pdftoppm(data: bytes) -> tuple[list[dict[str, Any]], list[str]]:
    """开发机兜底：本机有 ``pdftoppm`` 就逐页出 PNG，没有就交白卷说明。"""
    exe = shutil.which("pdftoppm")
    if not exe:
        return [], ["本机也没有 pdftoppm 兜底，原卷页图渲染不出来"]
    entries: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="jz-pdf-") as folder:
            source = Path(folder) / "source.pdf"
            source.write_bytes(data)
            prefix = Path(folder) / "page"
            command = [exe, "-png", "-r", str(PDF_RENDER_DPI), "-f", "1",
                       "-l", str(MAX_PAGES), str(source), str(prefix)]
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
