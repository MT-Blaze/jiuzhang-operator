"""页面渲染的共享常量与条目标签（page_render 家族内部使用）。"""

from __future__ import annotations

from typing import Any

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
# 原卷页图按 200 dpi 出：A4 约 1654×2339，框选裁下来的公式足够清楚。
PDF_RENDER_DPI = 200
# 自动切图另按 300 dpi 从原 PDF 直接裁：成品题图不经过 200 dpi 页图的二次采样。
PDF_CROP_DPI = 300

# XML 里禁用标签的检查在 pending_assets；这里只负责生成干净内容。
_FONT_FAMILY = ("'Microsoft YaHei','PingFang SC','Noto Sans CJK SC',"
                "'SimSun',sans-serif")


def _entry(name: str, page: int, **extra: Any) -> dict[str, Any]:
    entry = {"name": name, "uri": PENDING_ASSET_URI_PREFIX + name, "page": page}
    for key, value in extra.items():
        if value not in (None, [], ""):
            entry[key] = value
    return entry


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

