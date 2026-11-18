"""T8 跨页题接线：续段归属 → 两段原图裁切 → D15 纵向拼接（只接单栏页）。

判定与拼图全在 ``render.cross``，这里只做编排：续段用合成页条目走同一条
``crop_pdf_regions`` 裁图口径（300 dpi 直裁原 PDF），拼好的图替换主题图，
两段原图作为附加资产随题留存，坐标写进题块 ``cross_page`` 供追溯。
双栏页的「末块」不等于阅读顺序末题，跨页判定不适用，登记欠账不硬拼。
"""

from __future__ import annotations

import base64
from typing import Any

from app.core.ingest.render import cross
from app.core.ingest.render import service as page_render
from app.core.ingest.render.common import PDF_CROP_DPI, PDF_RENDER_DPI

_PAD_PX = 4


def _asset(asset_id: str, png: bytes) -> dict[str, Any]:
    return {"id": asset_id,
            "data_url": "data:image/png;base64," + base64.b64encode(png).decode("ascii")}


def _segment(name: str, number: int, page_no: int, page_width: int,
             region: dict[str, Any], crop: dict[str, Any]) -> cross.Segment:
    """裁图是 300 dpi、坐标框是 200 dpi 页像素：按裁图实际尺寸换算回框。"""
    scale_x = crop["width"] / float(region["w"])
    scale_y = crop["height"] / float(region["h"])
    left = round(float(region["x"]) * scale_x)
    top = round(float(region["y"]) * scale_y)
    box = (left, top, left + crop["width"], top + crop["height"])
    return cross.Segment(document=name, question_no=number, page_no=page_no,
                         dpi=PDF_CROP_DPI, page_width=page_width, box=box,
                         png=crop["png"])


def stitch_cross_questions(name: str, data: bytes,
                           page_images: list[dict[str, Any]],
                           lines_by_page: dict[int, list[dict[str, Any]]],
                           columns: dict[int, int],
                           crops: dict[int, list[dict[str, Any]]]
                           ) -> tuple[dict[tuple[int, int], list[dict[str, Any]]],
                                      dict[tuple[int, int], dict[str, Any]], list[str]]:
    """返回 (附加原图资产, 题块追溯元数据, 失败说明)，键都是 (页码, 切图序号)。

    纵拼成功不在此记账：调用方按 trace 往过程账本播一条 ok，避免成功被当失败挂徽标。
    """
    extra: dict[tuple[int, int], list[dict[str, Any]]] = {}
    trace: dict[tuple[int, int], dict[str, Any]] = {}
    notes: list[str] = []
    views: dict[int, cross.PageView] = {}
    for entry in page_images or []:
        try:
            page_no = int(entry.get("page") or 0)
        except (TypeError, ValueError):
            continue
        views[page_no] = cross.PageView(
            document=name, page_no=page_no, dpi=PDF_RENDER_DPI,
            width=int(entry.get("width") or 0), height=int(entry.get("height") or 0),
            lines=tuple(lines_by_page.get(page_no) or ()),
            regions=tuple(entry.get("regions") or ()))
    for page_no in sorted(views):
        following = views.get(page_no + 1)
        if following is None or not crops.get(page_no):
            continue
        if columns.get(page_no, 1) != 1 or columns.get(page_no + 1, 1) != 1:
            continue
        cont = cross.select_continuation(views[page_no], following)
        if cont is None:
            continue
        top_crop = max(crops[page_no],
                       key=lambda c: float(c["region"]["y"]) + float(c["region"]["h"]))
        if int(top_crop["region"]["no"]) != cont.question_no:
            continue
        top_region = top_crop["region"]
        xs = [float(top_region["x"]), float(top_region["x"]) + float(top_region["w"])]
        xs += [float(line["left"]) for line in cont.lines]
        xs += [float(line["right"]) for line in cont.lines]
        left = max(0.0, min(xs) - _PAD_PX)
        right = min(float(views[page_no].width), max(xs) + _PAD_PX)
        union_top = dict(top_region, x=left, w=right - left)
        union_bottom = {"no": cont.question_no, "x": left, "y": float(cont.top),
                        "w": right - left, "h": float(cont.bottom - cont.top)}
        made, _warn = page_render.crop_pdf_regions(data, [
            {"page": page_no, "width": views[page_no].width,
             "height": views[page_no].height, "regions": [union_top]},
            {"page": page_no + 1, "width": following.width,
             "height": following.height, "regions": [union_bottom]},
        ])
        top_seg_crop = (made.get(page_no) or [None])[0]
        bottom_seg_crop = (made.get(page_no + 1) or [None])[0]
        if top_seg_crop is None or bottom_seg_crop is None:
            notes.append(f"第 {page_no} 页题 {cont.question_no} 跨页续段裁图失败，未拼接")
            continue
        try:
            stitched = cross.stitch_cross_page(
                _segment(name, cont.question_no, page_no, views[page_no].width,
                         union_top, top_seg_crop),
                _segment(name, cont.question_no, page_no + 1, following.width,
                         union_bottom, bottom_seg_crop))
        except cross.CrossPageError as error:
            notes.append(f"第 {page_no} 页题 {cont.question_no} 跨页拼接条件不满足"
                         f"（{error}），未拼接，可对着原卷页图核对")
            continue
        key = (page_no, int(top_crop["index"]))
        extra[key] = [
            _asset("img_auto_%d_%d_seg1" % key, top_seg_crop["png"]),
            _asset("img_auto_%d_%d_seg2" % key, bottom_seg_crop["png"]),
        ]
        trace[key] = {"cross_page": {
            "pages": [page_no, page_no + 1],
            "top_box": [union_top["x"], union_top["y"],
                        union_top["x"] + union_top["w"], union_top["y"] + union_top["h"]],
            "bottom_box": [union_bottom["x"], union_bottom["y"],
                           union_bottom["x"] + union_bottom["w"],
                           union_bottom["y"] + union_bottom["h"]],
            "seam_px": stitched.seam_px, "stop_kind": cont.stop_kind,
        }}
        top_crop["png"] = stitched.png
        top_crop["width"] = stitched.width
        top_crop["height"] = stitched.height
        # 续段的行文字并进题块正文：选项在下一页时，题干不再只有一半。
        tail = "\n".join(str(line.get("text") or "") for line in
                         sorted(cont.lines, key=lambda l: float(l["top"]),
                                reverse=True))
        merged = (str(top_region.get("text") or "") + "\n" + tail).strip()[:2000]
        top_region["text"] = merged
        source = views[page_no].regions
        position = int(top_crop["index"])
        if position < len(source) and source[position] is not top_region:
            source[position]["text"] = merged
    return extra, trace, notes