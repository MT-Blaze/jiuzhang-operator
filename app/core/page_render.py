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

实现按域拆在同目录的 ``page_render_*`` 模块里；本文件是对外入口，并把
分域模块的名字重新导出——``ingest`` 与测试都按 ``page_render.xxx`` 取用。
"""

from __future__ import annotations

from typing import Any

from app.core.pending_assets import write_generated_asset
from app.core.page_render_common import (  # noqa: F401 - 常量沿用旧路径对外
    FONT_SIZE,
    FOOTER_Y,
    LINE_HEIGHT,
    MARGIN_TOP,
    MARGIN_X,
    MAX_LINES,
    MAX_PAGES,
    PAGE_HEIGHT,
    PAGE_WIDTH,
    PDF_CROP_DPI,
    PDF_RENDER_DPI,
    TEXT_WIDTH,
    _FONT_FAMILY,
    _entry,
    _spread_pages,
)
from app.core.page_render_pdf import (  # noqa: F401 - 测试按旧路径打桩
    _pdf_pages_builtin,
    _pdf_pages_pdftoppm,
    _pdfium,
    _parse_pdftotext,
    _pdftotext_words,
    _png_from_bitmap,
    crop_pdf_regions,
    pdf_page_lines,
    pdf_text_health,
)
from app.core.page_render_regions import (  # noqa: F401 - 测试按旧路径取用
    _ink_rows,
    _line_words_text,
    _longest_number_run,
    _pdf_page_regions,
    _pdf_text_lines,
    _question_regions,
    _trim_to_ink,
    _words_region_text,
)
from app.core.page_render_text import (  # noqa: F401 - 测试按旧路径取用
    _anchors,
    _char_width,
    _facsimile,
    _paginate,
    _svg_page,
    _wrap_line,
)


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

    两条实现按本模块的全局名查：测试用 ``mock.patch.object`` 打桩时，
    替换的是本模块属性，包装函数必须跟着换。
    """
    entries, warnings = _pdf_pages_builtin(data)
    if entries:
        return entries, warnings
    fallback, fallback_warnings = _pdf_pages_pdftoppm(data)
    warnings.extend(fallback_warnings)
    if fallback:
        return fallback, warnings
    return [], warnings
