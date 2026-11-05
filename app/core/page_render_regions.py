"""PDF 文本层 → 题块坐标：自动切分框的底账。

只认「行」：每行拿到 PDF 点坐标后换算成页面图像素坐标。题号连续递增的
一串才算一列题，页眉页脚的说明数字不参与；找不到题号就交空清单。
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Any

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
_REGION_TEXT_LIMIT = 2000
_REGION_LABEL_LIMIT = 48
# 题块上下各留一点呼吸位；相邻题之间至少留 5pt（约 14 像素 @200dpi），
# 绿框不再首尾相接，老师不会把下一题的选项误看成这一题的。
_HEAD_PAD_PT = 1.5
_REGION_GAP_PT = 5.0
_INK_PAD_PX = 6
# 页面图背景是白的；行内只要有明显偏暗的像素就算「有墨」，用于裁掉题块尾部空白。
_INK_TABLE = bytes(0 if value >= 245 else 1 for value in range(256))
# 同一行的词之间留多大缝才算分开（点）。中文字与字之间不补空格。
_WORD_GAP_PT = 0.8
# 上下相邻两行的词，纵向中心差多少以内算同一行（点）；试卷行距远大于它。
_WORD_LINE_TOL_PT = 7.5
# 词的底边比正文基线高出多少就算上标；低于多少就算下标（点）。
_SCRIPT_SHIFT_PT = 1.5


def _pdf_page_regions(page: Any, pixel_width: int, pixel_height: int, *,
                      ink_rows: bytearray | None = None,
                      first_page: bool = False,
                      words: Any = None) -> list[dict[str, Any]]:
    """一页 PDF → 题块清单（页面图像素坐标）；文本层读不出来就当没有。

    ``words`` 可以是词清单，也可以是按需返回词清单的函数——只在某一行真有
    读不出的字形时才会被调用。
    """
    try:
        page_width, page_height = (float(value) for value in page.get_size())
        lines = _pdf_text_lines(page)
    except Exception:  # noqa: BLE001 - 文本层坏了只影响自动框，不影响页图
        return []
    return _question_regions(lines, page_width, page_height, pixel_width, pixel_height,
                             ink_rows=ink_rows, first_page=first_page, words=words)


def _pdf_text_lines(page: Any) -> list[dict[str, Any]]:
    """按 PDFium 给出的换行符切行，并记下每行的点坐标包围盒。

    ``missing`` 记这一行有多少个读不出字的字形（常见于没有 ToUnicode 的
    数学字体）：这些字形的包围盒照样算进行宽，否则带公式的行会被裁窄。
    """
    textpage = page.get_textpage()
    try:
        total = int(textpage.count_chars())
        lines: list[dict[str, Any]] = []
        chars: list[str] = []
        bounds = [math.inf, math.inf, -math.inf, -math.inf]
        missing = 0

        def flush() -> None:
            nonlocal chars, bounds, missing
            text = "".join(chars).strip()
            if text and bounds[0] < bounds[2] and bounds[1] < bounds[3]:
                lines.append({
                    "text": text,
                    "left": bounds[0],
                    "bottom": bounds[1],
                    "right": bounds[2],
                    "top": bounds[3],
                    "missing": missing,
                })
            chars = []
            bounds = [math.inf, math.inf, -math.inf, -math.inf]
            missing = 0

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
            if not char:
                # 有框无字的字形：字体里没有 Unicode 映射（数学字母多半如此）。
                missing += 1
                bounds[0] = min(bounds[0], left)
                bounds[1] = min(bounds[1], bottom)
                bounds[2] = max(bounds[2], right)
                bounds[3] = max(bounds[3], top)
                if chars and chars[-1] != " ":
                    chars.append(" ")
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
                      first_page: bool = False,
                      words: Any = None) -> list[dict[str, Any]]:
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
        body = content[position:stop]
        text = "\n".join(part["text"] for part in body).strip()
        if words is not None and any(part.get("missing") for part in body):
            word_lines = words() if callable(words) else words
            enriched = _words_region_text(word_lines, box_x, y, box_w, h,
                                          scale_x, scale_y)
            # 外部工具要是读少了，宁可保留原样，也不让题干凭空掉字。
            if enriched and len(enriched) >= len(text) * 0.75:
                text = enriched
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


def _has_cjk(text: str) -> bool:
    return any(unicodedata.east_asian_width(char) in ("W", "F") for char in text)


def _starts_cjk(text: str) -> bool:
    return bool(text) and unicodedata.east_asian_width(text[0]) in ("W", "F")


def _ends_cjk(text: str) -> bool:
    return bool(text) and unicodedata.east_asian_width(text[-1]) in ("W", "F")


def _line_words_text(words: list[dict[str, Any]]) -> str:
    """一行词 → 文字；比正文基线高的词补 ``^{}``，低的补 ``_{}``。

    中文与中文之间不补空格（``pdftotext`` 常把一个词拆成几截），中文与
    公式之间补一个空格；上下标紧贴前一个词，不留缝。相邻的上下标并进同一
    对花括号——``^{1}^{2}`` 是非法公式，公式引擎会直接报错。
    """
    ordered = sorted(words, key=lambda word: word["left"])
    if not ordered:
        return ""
    heights = [word["bottom"] - word["top"] for word in ordered]
    tallest = max(heights)
    base = sorted(word["bottom"] for word, height in zip(ordered, heights)
                  if height >= tallest * 0.85)
    if not base:
        baseline = min(heights)
    elif len(base) % 2:
        baseline = base[len(base) // 2]
    else:
        middle = len(base) // 2
        baseline = (base[middle - 1] + base[middle]) / 2
    pieces: list[tuple[str, str]] = []
    previous: dict[str, Any] | None = None
    previous_kind = ""
    for word in ordered:
        text = word["text"]
        shift = word["bottom"] - baseline
        kind = ""
        if not _has_cjk(text):
            if shift < -_SCRIPT_SHIFT_PT:
                kind = "sup"
            elif shift > _SCRIPT_SHIFT_PT:
                kind = "sub"
        if kind and pieces and previous_kind == kind:
            pieces[-1] = (pieces[-1][0] + " " + text, kind)
            previous = word
            continue
        if previous is not None and not kind:
            if word["left"] - previous["right"] > _WORD_GAP_PT and not (
                    _ends_cjk(previous["text"]) and _starts_cjk(text)):
                pieces.append((" ", ""))
        pieces.append((text, kind))
        previous = word
        previous_kind = kind
    rendered = []
    for text, kind in pieces:
        if kind == "sup":
            rendered.append("^{" + text + "}")
        elif kind == "sub":
            rendered.append("_{" + text + "}")
        else:
            rendered.append(text)
    return "".join(rendered)


def _words_region_text(words: Any, x: float, y: float, width: float, height: float,
                       scale_x: float, scale_y: float) -> str:
    """把落在题块框里的词按「同一水平线」重新排队，再拼成文字。

    Poppler 的 ``-bbox-layout`` 会把左右并排的选项拆进不同 block，阅读顺序
    并不总是从左到右；这里只信词的坐标：先按纵坐标聚成行，行内再按横坐标
    排，选项就回到 ``A. … B. …`` 的本来次序。
    """
    if not words:
        return ""
    left = x / scale_x
    right = (x + width) / scale_x
    top = y / scale_y
    bottom = (y + height) / scale_y
    picked = [word for word in words
              if left <= (word["left"] + word["right"]) / 2 <= right
              and top <= (word["top"] + word["bottom"]) / 2 <= bottom]
    if not picked:
        return ""
    picked.sort(key=lambda word: ((word["top"] + word["bottom"]) / 2, word["left"]))
    rows: list[dict[str, Any]] = []
    for word in picked:
        center = (word["top"] + word["bottom"]) / 2
        if rows and abs(center - rows[-1]["center"]) <= _WORD_LINE_TOL_PT:
            rows[-1]["words"].append(word)
        else:
            rows.append({"center": center, "words": [word]})
    return "\n".join(_line_words_text(row["words"]) for row in rows).strip()


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
