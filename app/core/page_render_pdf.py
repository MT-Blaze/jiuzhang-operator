"""PDF → 原卷页图、自动切图与词级文字兜底。"""

from __future__ import annotations

import glob
import html
import os
import re
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path
from typing import Any

from app.core.pending_assets import write_generated_asset
from app.core.page_render_common import MAX_PAGES, PDF_CROP_DPI, PDF_RENDER_DPI, _entry
from app.core.page_render_regions import _ink_rows, _pdf_page_regions, _pdf_text_lines

try:  # 内置渲染器缺席只该降级，不该让整个模块导入失败。
    import pypdfium2 as _pdfium
except Exception:  # noqa: BLE001 - 缺库、坏 wheel 都按「没装上」处理
    _pdfium = None

def pdf_text_health(data: bytes) -> dict[str, Any]:
    """PDF 文本层体检：有没有字、读不读得出。

    ``has_text_layer`` 为假才走 MinerU 兜底；``garbled`` 只做提示，
    通道一绝不因为它自动调 AI（老师手动点识别）。
    """
    if _pdfium is None:
        return {"pages": 0, "text_chars": 0, "missing_chars": 0,
                "has_text_layer": False, "garbled": False}
    try:
        document = _pdfium.PdfDocument(data)
    except Exception:  # noqa: BLE001 - 打不开就当没有文本层
        return {"pages": 0, "text_chars": 0, "missing_chars": 0,
                "has_text_layer": False, "garbled": False}
    pages = 0
    text_chars = 0
    missing = 0
    try:
        total = len(document)
        for index in range(min(total, MAX_PAGES)):
            try:
                page = document[index]
                try:
                    lines = _pdf_text_lines(page)
                finally:
                    page.close()
            except Exception:  # noqa: BLE001 - 单页坏字不影响整份体检
                continue
            pages += 1
            for line in lines:
                text_chars += len(line.get("text") or "")
                missing += int(line.get("missing") or 0)
    finally:
        document.close()
    ratio = missing / (missing + text_chars) if (missing + text_chars) else 0.0
    return {
        "pages": pages,
        "text_chars": text_chars,
        "missing_chars": missing,
        "has_text_layer": text_chars >= 20,
        "garbled": missing >= 5 and ratio >= 0.2,
    }


def pdf_page_lines(data: bytes) -> list[dict[str, Any]]:
    """PDF 文本层 → 每页行清单（页面点数尺寸 + 行坐标），版面探路专用。

    只交出坐标与文字，不渲染、不落盘；读取失败就交空表，由调用方决定
    是退回渲染时算好的题块，还是继续降级到 YOLO / 云端。
    """
    if _pdfium is None:
        return []
    try:
        document = _pdfium.PdfDocument(data)
    except Exception:  # noqa: BLE001 - 打不开就当没有文本层
        return []
    pages: list[dict[str, Any]] = []
    try:
        total = len(document)
        for index in range(min(total, MAX_PAGES)):
            try:
                page = document[index]
                try:
                    width, height = (float(value) for value in page.get_size())
                    lines = _pdf_text_lines(page)
                finally:
                    page.close()
            except Exception:  # noqa: BLE001 - 单页读不出不影响别的页
                continue
            if lines:
                pages.append({"page": index + 1, "width_pt": width,
                              "height_pt": height, "lines": lines})
    finally:
        document.close()
    return pages


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
        words_by_page: dict[int, list[dict[str, Any]]] | None = None

        def page_words(page_no: int) -> list[dict[str, Any]]:
            # 只在这一页真有读不出的字形时才动外部工具：多数 PDF 用不上。
            nonlocal words_by_page
            if words_by_page is None:
                words_by_page = _pdftotext_words(data, min(total_pages, MAX_PAGES))
            return words_by_page.get(page_no) or []

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
                    regions = _pdf_page_regions(
                        page, width, height, ink_rows=ink, first_page=index == 0,
                        words=lambda page_no=index + 1: page_words(page_no))
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


# ---------------------------------------------------------------- 词级文字兜底
#
# PDFium 遇到没有 ToUnicode 的数学字体只能交出空字形；Poppler 的
# ``pdftotext -bbox-layout`` 能按词还原 Unicode，还带上下标的几何位置。
# 它和 ``pdftoppm`` 一样只是开发机的兜底：找不到就退回 PDFium 的原样文字。

_PDFTOTEXT_PAGE = re.compile(r"<page\b[^>]*>(.*?)</page>", re.S)
_PDFTOTEXT_WORD = re.compile(r"<word\b([^>]*)>(.*?)</word>", re.S)
_PDFTOTEXT_BOX = re.compile(r'(xMin|yMin|xMax|yMax)="([-0-9.]+)"')
_pdftotext_paths: list[str] | None = None


def _pdftotext_candidates() -> list[str]:
    """本机上所有 ``pdftotext``：PATH 优先，再补 TeX Live / MiKTeX / Poppler 的常见位置。

    同样是 ``pdftotext``，Poppler 版才认 ``-bbox-layout``；Xpdf 版会直接报用法错误，
    所以调用处逐个试，谁能干这活就用谁。
    """
    found: list[str] = []

    def add(path: Any) -> None:
        text = str(path or "")
        if text and os.path.isfile(text) and text not in found:
            found.append(text)

    add(shutil.which("pdftotext"))
    for folder in os.environ.get("PATH", "").split(os.pathsep):
        if folder:
            add(Path(folder) / ("pdftotext.exe" if os.name == "nt" else "pdftotext"))
    patterns = (
        "C:/texlive/*/bin/windows/pdftotext.exe",
        "C:/texlive/*/bin/win32/pdftotext.exe",
        "C:/Program Files/MiKTeX/miktex/bin/x64/pdftotext.exe",
        "C:/Program Files/poppler*/bin/pdftotext.exe",
        "C:/Program Files (x86)/poppler*/bin/pdftotext.exe",
        "/usr/bin/pdftotext",
        "/usr/local/bin/pdftotext",
        "/opt/homebrew/bin/pdftotext",
    )
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            add(path)
    return found


def _parse_pdftotext(raw: bytes) -> dict[int, list[dict[str, Any]]]:
    """``-bbox-layout`` 的 XHTML → ``{页码: [词]}``；词坐标是左上原点的点。

    只留词的坐标与文字，不保留 Poppler 自己的 block/line 分组——阅读顺序
    由调用方按坐标重排，左右并排的选项才不会被拼反。
    """
    text = raw.decode("utf-8", "replace")
    pages: dict[int, list[dict[str, Any]]] = {}
    for page_no, block in enumerate(_PDFTOTEXT_PAGE.findall(text), start=1):
        words: list[dict[str, Any]] = []
        for attrs, content in _PDFTOTEXT_WORD.findall(block):
            box = dict(_PDFTOTEXT_BOX.findall(attrs))
            try:
                word = {
                    "text": html.unescape(content).strip(),
                    "left": float(box["xMin"]),
                    "top": float(box["yMin"]),
                    "right": float(box["xMax"]),
                    "bottom": float(box["yMax"]),
                }
            except (KeyError, ValueError):
                continue
            if word["text"]:
                words.append(word)
        if words:
            pages[page_no] = words
    return pages


def _pdftotext_words(data: bytes, max_pages: int) -> dict[int, list[dict[str, Any]]]:
    """PDF → 按页的词清单；没有能用的 Poppler 就交空表（不报警、不阻挡流程）。"""
    global _pdftotext_paths
    if max_pages <= 0:
        return {}
    if _pdftotext_paths is None:
        _pdftotext_paths = _pdftotext_candidates()
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    for index, exe in enumerate(list(_pdftotext_paths)):
        command = [exe, "-bbox-layout", "-enc", "UTF-8", "-f", "1",
                   "-l", str(max_pages), "-", "-"]
        try:
            result = subprocess.run(command, input=data, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, check=False,
                                    timeout=90, creationflags=flags)
        except (OSError, subprocess.SubprocessError):
            continue
        if result.returncode != 0 or b"<word" not in result.stdout:
            continue
        pages = _parse_pdftotext(result.stdout)
        if not pages:
            continue
        if index:
            _pdftotext_paths.insert(0, _pdftotext_paths.pop(index))
        return pages
    return {}


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

