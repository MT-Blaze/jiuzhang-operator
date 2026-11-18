"""全卷页眉页脚剥离：同一位置、同一文字跨页反复出现，才整行剔除。

只认「跨页共识」：一页、两页没有重复可言，行清单原样交回；三页必须三页
全中，四页起才允许 2/3（向上取整）。候选行还必须同时命中位置与文字——
同一位置上的 A./B./C./D. 选项文字各不相同，绝不会被当成页眉页脚删掉。

纯数字页码是唯一不看文字的例外：它在带内、且行高小于正文（含汉字行）
中位数，才认作页脚；三页卷仍要求同一位置三页都在。
"""

from __future__ import annotations

import math
import re
from difflib import SequenceMatcher
from typing import Any

# 页面上、下各 10% 是页眉页脚候选带。辽宁五校卷的页脚落在 8.7%，
# 沿用旧的 8% 会整条漏掉，所以这里必须是 10%。
_BAND_RATIO = 0.10
# 一页、两页没有「跨页重复」可言，不做任何剔除。
_MIN_CROSS_PAGES = 3
# 同一位置：纵向上沿差、左右边距差都不超过这些值（点）。
_POSITION_TOL_PT = 8.0
_COLUMN_TOL_PT = 12.0
# 文字归一化后（数字换成 #）的相似度门槛。
_TEXT_SIMILARITY = 0.85
# 纯数字页码的行高必须小于正文（含汉字行）中位数的这个倍率。
_NUMERIC_HEIGHT_RATIO = 0.85
# 选项行是正文，不是页眉页脚：位置再像、文字再像也不参与跨页判定。
_OPTION_START = re.compile(r"^\s*[A-Ha-hＡ-Ｈａ-ｈ]\s*[.．、]")
_BARE_NUMBER = re.compile(r"\d{1,3}")
_DIGITS = re.compile(r"\d+")


def filter_pages(pages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    """全卷行清单 → 逐页剔除页眉页脚后的行清单。

    ``pages`` 每项至少要有 ``height``（PDF 点）与 ``lines``。页数 ≤2 时直接
    返回原列表（同一个对象），保证上层「原样交给切题」。
    """
    if len(pages) < _MIN_CROSS_PAGES:
        return [page.get("lines") or [] for page in pages]

    removed: set[tuple[int, int]] = set()
    removed |= _off_page_lines(pages)
    removed |= _repeated_furniture(pages)
    removed |= _numeric_page_numbers(pages)
    return [
        [line for index, line in enumerate(page.get("lines") or [])
         if (page_index, index) not in removed]
        for page_index, page in enumerate(pages)
    ]


def _off_page_lines(pages: list[dict[str, Any]]) -> set[tuple[int, int]]:
    """可见区之外的行：文本层会把裁切掉的水印碎片记成 ``bottom < 0``。

    这类行在页面上根本看不见，既不是正文也不是页眉页脚候选，直接剔掉；
    页数 ≤2 时 filter_pages 不走到这里，单页/两页仍一行不剔。
    """
    removed: set[tuple[int, int]] = set()
    for page_index, page in enumerate(pages):
        height = _height(page)
        for line_index, line in enumerate(page.get("lines") or []):
            bottom = float(line.get("bottom") or 0)
            top = float(line.get("top") or 0)
            if bottom < 0 or (height > 0 and top > height):
                removed.add((page_index, line_index))
    return removed


def _repeated_furniture(pages: list[dict[str, Any]]) -> set[tuple[int, int]]:
    """位置相同、文字相同（或数字归一化后高度相似）的跨页重复行。"""
    required = _required_pages(len(pages))
    groups: list[dict[str, Any]] = []
    for page_index, page in enumerate(pages):
        height = _height(page)
        for line_index, line in enumerate(page.get("lines") or []):
            text = str(line.get("text") or "")
            if not _in_band(line, height) or _looks_like_option(text):
                continue
            if _BARE_NUMBER.fullmatch(_compact(text)):
                continue
            for group in groups:
                if page_index in group["pages"]:
                    continue
                if (_same_position(group["line"], line)
                        and _same_text(str(group["line"]["text"]), text)):
                    group["pages"].add(page_index)
                    group["items"].append((page_index, line_index))
                    break
            else:
                groups.append({"line": line, "pages": {page_index},
                               "items": [(page_index, line_index)]})
    removed: set[tuple[int, int]] = set()
    for group in groups:
        if len(group["pages"]) >= required:
            removed.update(group["items"])
    return removed


def _numeric_page_numbers(pages: list[dict[str, Any]]) -> set[tuple[int, int]]:
    """页底纯数字页码：在带内 + 行高明显小于正文中位数。

    四页起「少数页也认」；三页卷仍要求同一位置三页都在——孤零零一个
    贴底数字更可能是答案，不是页码。
    """
    small: list[tuple[int, int, dict[str, Any]]] = []
    for page_index, page in enumerate(pages):
        height = _height(page)
        lines = page.get("lines") or []
        candidates = [line for line in lines
                      if _in_bottom_band(line, height)
                      and _BARE_NUMBER.fullmatch(_compact(str(line.get("text") or "")))]
        if not candidates:
            continue
        candidate_ids = {id(line) for line in candidates}
        limit = _body_height_limit(lines, candidate_ids)
        if limit is None:
            continue
        for line_index, line in enumerate(lines):
            if id(line) in candidate_ids and _line_height(line) < limit:
                small.append((page_index, line_index, line))
    if not small:
        return set()
    if len(pages) == _MIN_CROSS_PAGES:
        groups: list[dict[str, Any]] = []
        for page_index, line_index, line in small:
            for group in groups:
                if page_index in group["pages"]:
                    continue
                if _same_position(group["line"], line):
                    group["pages"].add(page_index)
                    group["items"].append((page_index, line_index))
                    break
            else:
                groups.append({"line": line, "pages": {page_index},
                               "items": [(page_index, line_index)]})
        return {item for group in groups
                if len(group["pages"]) >= _MIN_CROSS_PAGES
                for item in group["items"]}
    return {(page_index, line_index) for page_index, line_index, _line in small}


def _required_pages(page_count: int) -> int:
    if page_count == _MIN_CROSS_PAGES:
        return _MIN_CROSS_PAGES
    return math.ceil(page_count * 2 / 3)


def _height(page: dict[str, Any]) -> float:
    try:
        return float(page.get("height") or 0)
    except (TypeError, ValueError):
        return 0.0


def _in_band(line: dict[str, Any], height: float) -> bool:
    if height <= 0:
        return False
    return (float(line.get("top") or 0) <= height * _BAND_RATIO
            or float(line.get("bottom") or 0) >= height * (1 - _BAND_RATIO))


def _in_bottom_band(line: dict[str, Any], height: float) -> bool:
    return height > 0 and float(line.get("top") or 0) <= height * _BAND_RATIO


def _same_position(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return (abs(float(first.get("top") or 0) - float(second.get("top") or 0))
            < _POSITION_TOL_PT
            and abs(float(first.get("left") or 0) - float(second.get("left") or 0))
            < _COLUMN_TOL_PT
            and abs(float(first.get("right") or 0) - float(second.get("right") or 0))
            < _COLUMN_TOL_PT)


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _same_text(first: str, second: str) -> bool:
    """页码数字逐页变化不算文字不同：先归一化成 # 再比。"""
    left = _DIGITS.sub("#", _compact(first))
    right = _DIGITS.sub("#", _compact(second))
    if not left or not right:
        return False
    if left == right:
        return True
    return SequenceMatcher(None, left, right).ratio() >= _TEXT_SIMILARITY


def _looks_like_option(text: str) -> bool:
    return bool(_OPTION_START.match(text))


def _line_height(line: dict[str, Any]) -> float:
    return float(line.get("top") or 0) - float(line.get("bottom") or 0)


def _body_height_limit(lines: list[dict[str, Any]], skip: set[int]) -> float | None:
    """正文行高中位数 × 0.85；正文行按含汉字判定，排除纯数字候选。"""
    body = [line for line in lines
            if id(line) not in skip and _has_hanzi(str(line.get("text") or ""))]
    if not body:
        body = [line for line in lines if id(line) not in skip]
    heights = sorted(_line_height(line) for line in body)
    if not heights:
        return None
    middle = len(heights) // 2
    median = (heights[middle] if len(heights) % 2
              else (heights[middle - 1] + heights[middle]) / 2)
    return median * _NUMERIC_HEIGHT_RATIO


def _has_hanzi(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)
