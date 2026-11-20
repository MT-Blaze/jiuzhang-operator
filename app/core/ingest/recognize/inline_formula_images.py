"""文字直取兜底：行内位图公式检测（#INLINE-BITMAP-FORMULA-01 刀 B）。

文字层只能拿到文字；被做成小图片的行内公式既没有文字、也没有公式坐标，
组合路（文字直取＋公式裁图）会把它们整体漏掉。这里用 pypdfium2 枚举页面
image object，按「尺寸 / 落文字行 / 左右邻接」三道筛选认出行内公式图，
输出与 ``formula._textlayer_spans`` 同构的 span：题块左上为原点的 300dpi
像素 bbox，``origin="inline_bitmap"``，由 ``formula.discover_spans`` 并进
公式裁图清单，下游原样消费。

可下架：删除本文件，并还原 ``formula.discover_spans`` 里一处合并调用。
"""

from __future__ import annotations

from typing import Any

# 侦查口径（.system_generated/bitmap-formula-recon）：I3 唯一命中卷。
MAX_HEIGHT_PT = 45.0
MAX_WIDTH_PT = 400.0
# 宽高比极端的水印与横线：I3 实测 85 张最大 6.33，留足余量。
MAX_ASPECT = 20.0
# 小于 3pt 的装饰碎片（A2 页眉有 0.7×0.7pt 图）不当公式。
MIN_SIDE_PT = 3.0
# 行内邻接间隙：I3 实测 85 张 p50=0.62pt、最大 7.74pt，取 12pt 兜住空格。
ADJACENT_GAP_PT = 12.0
# 与已有文字层公式 span 重叠达到该比例即视为重复项。
DUPLICATE_OVERLAP = 0.8
CROP_DPI = 300
MIN_SPAN_PX = 8.0
_PAGEOBJ_IMAGE = 3


def _image_boxes(page: Any) -> list[tuple[float, float, float, float]]:
    """页面所有 image object 的 PDF 点 bbox（left, bottom, right, top）。

    先走高层 ``get_objects``（带 max_depth 递归 Form XObject）；本机
    pypdfium2 5.9.0 的 raw 枚举只到顶层、且 bounds 签名特殊，仅作兜底。
    任一途失败交空清单，绝不编坐标。
    """
    try:
        boxes = []
        for obj in page.get_objects(filter=[_PAGEOBJ_IMAGE], max_depth=8):
            left, bottom, right, top = (float(value) for value in obj.get_bounds())
            boxes.append((left, bottom, right, top))
        return boxes
    except Exception:  # noqa: BLE001 - 走 raw 兜底
        pass
    try:
        import ctypes

        import pypdfium2.raw as raw

        handle = page.raw
        boxes = []
        for index in range(int(raw.FPDFPage_CountObjects(handle))):
            obj = raw.FPDFPage_GetObject(handle, index)
            if raw.FPDFPageObj_GetType(obj) != raw.FPDF_PAGEOBJ_IMAGE:
                continue
            left, bottom, right, top = (ctypes.c_float() for _ in range(4))
            raw.FPDFPageObj_GetBounds(obj, ctypes.byref(left), ctypes.byref(bottom),
                                      ctypes.byref(right), ctypes.byref(top))
            boxes.append((left.value, bottom.value, right.value, top.value))
        return boxes
    except Exception:  # noqa: BLE001 - 枚举不到只说明这页没有可用的图坐标
        return []


def _text_context(page: Any) -> tuple[bool, list[tuple[float, float, float, float]]]:
    """（本页是否真有文字层, 非空白字符框清单）。

    无文字层页面（纯图卷、文字转曲）在组合路里本来就整页走图像识别，
    这里直接空手而归，绝不越过刀 B 的边界。
    """
    textpage = page.get_textpage()
    try:
        boxes: list[tuple[float, float, float, float]] = []
        has_text = False
        for index in range(int(textpage.count_chars())):
            char = textpage.get_text_range(index, 1)
            if char in ("\r", "\n"):
                continue
            if char and not char.strip():
                continue
            if char:
                has_text = True
            try:
                left, bottom, right, top = (float(value)
                                            for value in textpage.get_charbox(index))
            except Exception:  # noqa: BLE001 - 单个坏字形跳过，不拖垮整页
                continue
            boxes.append((left, bottom, right, top))
        return has_text, boxes
    finally:
        textpage.close()


def _adjacent(left: float, right: float, bottom: float, top: float,
              char_boxes: list[tuple[float, float, float, float]]) -> bool:
    """同一行左或右紧挨着文字：取最近的水平间隙，阈值见 ADJACENT_GAP_PT。"""
    best: float | None = None
    for char_left, char_bottom, char_right, char_top in char_boxes:
        if char_top < bottom or char_bottom > top:
            continue
        if char_right <= left:
            gap = left - char_right
        elif char_left >= right:
            gap = char_left - right
        else:
            continue
        if best is None or gap < best:
            best = gap
    return best is not None and best <= ADJACENT_GAP_PT


def _duplicate(bbox: list[float], existing_spans: list[dict[str, Any]]) -> bool:
    """候选图与已有文字层 span 重叠 ≥80%（按候选图面积）即算重复。"""
    area = bbox[2] * bbox[3]
    if area <= 0:
        return False
    for span in existing_spans:
        box = span.get("bbox") if isinstance(span, dict) else None
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            continue
        width = min(bbox[0] + bbox[2], float(box[0]) + float(box[2])) - max(bbox[0], float(box[0]))
        height = min(bbox[1] + bbox[3], float(box[1]) + float(box[3])) - max(bbox[1], float(box[1]))
        if width > 0 and height > 0 and width * height / area >= DUPLICATE_OVERLAP:
            return True
    return False


def _line_text_at(center_y: float, lines: list[dict[str, Any]]) -> str:
    """样本回单用：图形中心所在文字行的文字（取不到交空串）。"""
    for line in lines:
        if line["bottom"] <= center_y <= line["top"]:
            return str(line.get("text") or "")
    return ""


def detect(page: Any, region: dict[str, Any], page_width: float, page_height: float,
           pixel_width: float, pixel_height: float,
           existing_spans: list[dict[str, Any]] | None = None,
           want_line_text: bool = False) -> list[dict[str, Any]]:
    """一页里落进指定题块的行内公式位图 → 公式裁图 span（题图像素 @300dpi）。"""
    from app.core.ingest.render.regions import _pdf_text_lines

    if page_width <= 0 or page_height <= 0 or pixel_width <= 0 or pixel_height <= 0:
        return []
    has_text, char_boxes = _text_context(page)
    if not has_text:
        return []
    lines = _pdf_text_lines(page)
    if not lines:
        return []
    scale_x = page_width / pixel_width
    scale_y = page_height / pixel_height
    origin_x = float(region.get("x") or 0) * scale_x
    origin_y = float(region.get("y") or 0) * scale_y
    region_w = float(region.get("w") or 0) * scale_x
    region_h = float(region.get("h") or 0) * scale_y
    factor = CROP_DPI / 72.0
    spans: list[dict[str, Any]] = []
    for left, bottom, right, top in _image_boxes(page):
        width, height = right - left, top - bottom
        if width <= 0 or height <= 0:
            continue
        if height > MAX_HEIGHT_PT or width > MAX_WIDTH_PT:
            continue
        if min(width, height) < MIN_SIDE_PT:
            continue
        if max(width, height) / min(width, height) > MAX_ASPECT:
            continue
        center_x = (left + right) / 2
        center_y = (bottom + top) / 2
        if not (0 <= center_x - origin_x <= region_w
                and 0 <= (page_height - center_y) - origin_y <= region_h):
            continue
        if not any(line["bottom"] <= center_y <= line["top"] for line in lines):
            continue
        if not _adjacent(left, right, bottom, top, char_boxes):
            continue
        bbox = [max(0.0, (left - origin_x) * factor),
                max(0.0, ((page_height - top) - origin_y) * factor),
                width * factor, height * factor]
        if bbox[2] < MIN_SPAN_PX or bbox[3] < MIN_SPAN_PX:
            continue
        if _duplicate(bbox, existing_spans or []):
            continue
        span: dict[str, Any] = {"bbox": bbox, "text": "", "latex": "",
                                "origin": "inline_bitmap"}
        if want_line_text:
            span["line_text"] = _line_text_at(center_y, lines)
        spans.append(span)
    return sort_spans(spans)


def sort_spans(spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按页内阅读顺序（先 y 后 x）稳定排序，重复检测结果顺序不变。"""
    return sorted(spans, key=lambda span: (round(float(span["bbox"][1]), 1),
                                           round(float(span["bbox"][0]), 1)))


def merge_spans(text_spans: list[dict[str, Any]],
                inline_spans: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """文字层 span ＋ 行内位图 span 并成一份裁图清单；原有条目一个不丢。"""
    return sort_spans(list(text_spans) + list(inline_spans))


def discover(item: dict[str, Any], page_images: list[dict[str, Any]],
             pdf_bytes: bytes,
             existing_spans: list[dict[str, Any]] | None = None,
             want_line_text: bool = False) -> list[dict[str, Any]]:
    """按题定位到页与题块，返回该题的行内位图公式 span；定位不到就空。"""
    pending_id = str(item.get("id") or "")
    region = entry = None
    for page in page_images or []:
        for candidate in page.get("regions") or []:
            if (isinstance(candidate, dict)
                    and str(candidate.get("pending_id") or "") == pending_id):
                region, entry = candidate, page
                break
        if region is not None:
            break
    if region is None or not pdf_bytes:
        return []
    import pypdfium2

    document = page = None
    try:
        page_no = int(entry.get("page") or 0)
        pixel_width = float(entry.get("width") or 0)
        pixel_height = float(entry.get("height") or 0)
        document = pypdfium2.PdfDocument(pdf_bytes)
        page = document[page_no - 1]
        page_width, page_height = (float(value) for value in page.get_size())
        return detect(page, region, page_width, page_height,
                      pixel_width, pixel_height, existing_spans, want_line_text)
    except Exception:  # noqa: BLE001 - 坐标探不到只影响这一题
        return []
    finally:
        if page is not None:
            page.close()
        if document is not None:
            document.close()
