"""跨页题：续页归属与同题纵向拼接（决策台账 D15）。

判定只看机械判据，三条同时成立才算跨页题：

a) 本页最后一个题块的下沿已到页脚 / 页底（框下无内容行且框底紧贴末行墨迹时，空白不算内容）；
b) 下一页第一个内容行不是题号行（``_PDF_HEAD`` 不匹配）；
c) 下一页从顶部到下一个题号行（或下一节标题）之前的行，属于本题续段。

拼接严格按 D15 四条件，缺一不可：① 同题同卷 ② 同一 dpi 渲染
③ 页宽一致 ④ 拼接处留 8–12px 缝。两段原图与两段坐标由
``StitchedCrop`` 一并带回，只拼不留原图不算完成。

本模块只做「判据 + 拼图」，坐标一律用页面图像素系（y 向下），与
``regions`` 输出的 region 同一坐标系。
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from typing import Any

from app.core.ingest.render.regions import _PDF_FOOTER, _PDF_HEAD, _PDF_SECTION

SEAM_MIN_PX = 8
SEAM_MAX_PX = 12
DEFAULT_SEAM_PX = 10
# 续段裁切在截止线前留一点白，保证下一节标题一个像素都进不来。
_CUT_PAD_PX = 4
# 「下沿到页脚」的容差：12pt。题块墨迹裁边与页脚之间常留一道窄缝。
_REACH_TOL_PT = 12.0

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class CrossPageError(ValueError):
    """跨页题拼接条件不满足；``problems`` 逐条列出缺哪一条。"""

    def __init__(self, problems: list[str]) -> None:
        self.problems = tuple(problems)
        super().__init__("；".join(problems))


@dataclass(frozen=True)
class PageView:
    """一页的判定输入：卷子标识、页号、dpi、页面像素尺寸与行/题块。"""

    document: str
    page_no: int
    dpi: int
    width: int
    height: int
    lines: tuple[dict[str, Any], ...] = ()
    regions: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class Continuation:
    """续页归属结果：哪道题、续段在下一页的像素区间、续了哪些行。"""

    question_no: int
    top: int
    bottom: int
    stop_kind: str
    lines: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class Segment:
    """一段原图：页面像素坐标里的裁切框 + PNG 字节 + 渲染口径。"""

    document: str
    question_no: int
    page_no: int
    dpi: int
    page_width: int
    box: tuple[int, int, int, int]
    png: bytes

    @property
    def width(self) -> int:
        return self.box[2] - self.box[0]

    @property
    def height(self) -> int:
        return self.box[3] - self.box[1]


@dataclass(frozen=True)
class StitchedCrop:
    """拼好的题图 + 两段原图与坐标；原图不丢，才可追溯。"""

    png: bytes
    width: int
    height: int
    seam_px: int
    top: Segment
    bottom: Segment


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _content_lines(lines: tuple[dict[str, Any], ...] | list[dict[str, Any]]
                   ) -> list[dict[str, Any]]:
    """去掉空行与页脚；页眉按内容行保留，与「题号行之间的行」口径一致。"""
    kept: list[dict[str, Any]] = []
    for line in lines or ():
        text = str(line.get("text") or "").strip()
        if not text or _PDF_FOOTER.search(text):
            continue
        top = _number(line.get("top"))
        bottom = _number(line.get("bottom"))
        if top is None or bottom is None or bottom <= top:
            continue
        kept.append(line)
    return kept


def _footer_top(lines: list[dict[str, Any]]) -> float | None:
    tops = [_number(line.get("top")) for line in lines
            if _PDF_FOOTER.search(str(line.get("text") or ""))]
    known = [top for top in tops if top is not None]
    return min(known) if known else None


def _last_region(regions: tuple[dict[str, Any], ...] | list[dict[str, Any]]
                 ) -> dict[str, Any] | None:
    usable: list[dict[str, Any]] = []
    for region in regions or ():
        x = _number(region.get("x"))
        y = _number(region.get("y"))
        w = _number(region.get("w"))
        h = _number(region.get("h"))
        no = _number(region.get("no"))
        if None in (x, y, w, h, no) or w <= 0 or h <= 0:
            continue
        usable.append(region)
    if not usable:
        return None
    return max(usable, key=lambda region: float(region["y"]) + float(region["h"]))


def select_continuation(page: PageView, next_page: PageView) -> Continuation | None:
    """按三条机械判据判定续页归属；判不出就交 ``None``，绝不按「看着像」拼。

    下一页的截止点取「下一个题号行」与「下一节标题」中更靠上的一条：
    选项后面紧跟「二、多项选择题」时，下一节标题也是硬边界，不许吃进来。
    """
    if page.document != next_page.document:
        return None
    if next_page.page_no != page.page_no + 1:
        return None
    last = _last_region(page.regions)
    if last is None:
        return None

    page_lines = _content_lines(page.lines)
    footer_top = _footer_top(list(page.lines or ()))
    limit = footer_top if footer_top is not None else float(page.height)
    reach_tol = _REACH_TOL_PT * page.dpi / 72.0
    bottom = float(last["y"]) + float(last["h"])
    if limit - bottom > reach_tol:  # (a) 下沿没到页脚 / 页底
        # 墨迹裁边后题块与页脚之间常有一道空白：空白不算内容，
        # 框下再无任何内容行、且框底紧贴末行墨迹时，仍视为「写到页内容尽头」。
        below = [line for line in page_lines if float(line["top"]) >= bottom]
        if below:
            return None
        if page_lines:
            ink_bottom = max(float(line["bottom"]) for line in page_lines)
            if bottom - ink_bottom > reach_tol:
                return None  # 框内尾部还有一大段空白，不算写到尽头
    if page_lines:
        final = max(page_lines, key=lambda line: float(line["bottom"]))
        center = (float(final["top"]) + float(final["bottom"])) / 2
        if not (float(last["y"]) <= center <= bottom):
            return None  # (a) 最后一行的中心不在末题框里，说明下面还有别的内容

    following = _content_lines(next_page.lines)
    if not following:
        return None
    first = min(following, key=lambda line: float(line["top"]))
    if _PDF_HEAD.match(str(first["text"])):  # (b) 下一页开门就是新题
        return None

    stop_kind = "page_bottom"
    cutoff = float(next_page.height)
    for line in sorted(following, key=lambda item: float(item["top"])):
        text = str(line["text"])
        if _PDF_HEAD.match(text):
            stop_kind, cutoff = "next_head", float(line["top"])
            break
        if _PDF_SECTION.match(text):
            stop_kind, cutoff = "next_section", float(line["top"])
            break

    body = [line for line in following if float(line["bottom"]) <= cutoff]
    if not body:  # (c) 截止线以上没有续段
        return None
    top = max(0.0, min(float(line["top"]) for line in body) - _CUT_PAD_PX)
    last_body = max(float(line["bottom"]) for line in body) + _CUT_PAD_PX
    bottom = min(cutoff - _CUT_PAD_PX, last_body)
    if bottom - top < 8.0:
        return None
    return Continuation(question_no=int(last["no"]), top=int(round(top)),
                        bottom=int(round(bottom)), stop_kind=stop_kind,
                        lines=tuple(body))


def stitch_cross_page(top: Segment, bottom: Segment,
                      seam_px: int = DEFAULT_SEAM_PX) -> StitchedCrop:
    """按 D15 四条件纵向拼接；任何一条不满足都抛 ``CrossPageError``。"""
    problems: list[str] = []
    if top.document != bottom.document or top.question_no != bottom.question_no:
        problems.append("① 不是同题同卷")
    if top.dpi != bottom.dpi:
        problems.append("② 两段不是同一 dpi 渲染")
    if top.page_width != bottom.page_width:
        problems.append("③ 两页页宽不一致")
    if not isinstance(seam_px, int) or not SEAM_MIN_PX <= seam_px <= SEAM_MAX_PX:
        problems.append(f"④ 拼接缝 {seam_px}px 不在 {SEAM_MIN_PX}–{SEAM_MAX_PX}px")
    if problems:
        raise CrossPageError(problems)

    top_image = _decode_png(top.png)
    bottom_image = _decode_png(bottom.png)
    width, height = top_image.width, top_image.height
    if bottom_image.width != width:
        problems.append("③ 两段裁图宽度不一致（%d vs %d）"
                        % (width, bottom_image.width))
    if width != top.width or width != bottom.width:
        problems.append("③ 裁图宽度与坐标框宽度不一致")
    if top_image.height != top.height or bottom_image.height != bottom.height:
        problems.append("③ 裁图高度与坐标框高度不一致")
    if problems:
        raise CrossPageError(problems)

    rows: list[bytes] = list(top_image.rows)
    rows.extend([_white_row(width)] * seam_px)
    rows.extend(bottom_image.rows)
    stitched = _encode_png(width, len(rows), rows)
    return StitchedCrop(png=stitched, width=width, height=len(rows),
                        seam_px=seam_px, top=top, bottom=bottom)


# ------------------------------------------------------------------ PNG 编解码
#
# 生产环境只有标准库：PDFium 出来的是 8bit RGB PNG，这里按 PNG 规范解滤镜；
# 不支持隔行与调色板，遇到就直说，不猜。

@dataclass(frozen=True)
class _Raster:
    width: int
    height: int
    rows: list[bytes]


def _white_row(width: int) -> bytes:
    return b"\xff" * (width * 3)


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    dl = abs(estimate - left)
    du = abs(estimate - up)
    dul = abs(estimate - upper_left)
    if dl <= du and dl <= dul:
        return left
    return up if du <= dul else upper_left


def _decode_png(png: bytes) -> _Raster:
    if not png.startswith(_PNG_SIGNATURE):
        raise CrossPageError(["PNG 字节头不对，无法拼接"])
    position = 8
    width = height = depth = color = interlace = 0
    chunks: list[bytes] = []
    while position + 8 <= len(png):
        length = struct.unpack(">I", png[position:position + 4])[0]
        tag = png[position + 4:position + 8]
        payload = png[position + 8:position + 8 + length]
        position += 12 + length
        if tag == b"IHDR":
            width, height, depth, color, _comp, _filter, interlace = \
                struct.unpack(">IIBBBBB", payload)
        elif tag == b"IDAT":
            chunks.append(payload)
        elif tag == b"IEND":
            break
    if depth != 8 or color not in (0, 2, 4, 6) or interlace != 0:
        raise CrossPageError(["只支持 8bit 非隔行 RGB/灰度 PNG，实际 depth=%d color=%d"
                              % (depth, color)])
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[color]
    stride = width * channels
    raw = zlib.decompress(b"".join(chunks))
    if len(raw) < (stride + 1) * height:
        raise CrossPageError(["PNG 数据不完整"])
    rows: list[bytes] = []
    previous = bytearray(stride)
    offset = 0
    for _ in range(height):
        kind = raw[offset]
        offset += 1
        line = bytearray(raw[offset:offset + stride])
        offset += stride
        if kind == 1:
            for index in range(channels, stride):
                line[index] = (line[index] + line[index - channels]) & 0xFF
        elif kind == 2:
            for index in range(stride):
                line[index] = (line[index] + previous[index]) & 0xFF
        elif kind == 3:
            for index in range(stride):
                left = line[index - channels] if index >= channels else 0
                line[index] = (line[index] + ((left + previous[index]) >> 1)) & 0xFF
        elif kind == 4:
            for index in range(stride):
                left = line[index - channels] if index >= channels else 0
                upper_left = previous[index - channels] if index >= channels else 0
                line[index] = (line[index]
                               + _paeth(left, previous[index], upper_left)) & 0xFF
        elif kind != 0:
            raise CrossPageError(["PNG 行滤镜 %d 不认识" % kind])
        previous = line
        rows.append(_to_rgb(line, channels))
    return _Raster(width=width, height=height, rows=rows)


def _to_rgb(line: bytearray, channels: int) -> bytes:
    if channels == 3:
        return bytes(line)
    pixels = len(line) // channels
    out = bytearray(pixels * 3)
    if channels in (1, 2):  # 灰度（可带 alpha）：按原灰度铺三段
        for index in range(pixels):
            grey = line[index * channels]
            out[index * 3:index * 3 + 3] = bytes((grey, grey, grey))
    else:  # RGBA：丢掉 alpha
        for index in range(pixels):
            out[index * 3:index * 3 + 3] = line[index * 4:index * 4 + 3]
    return bytes(out)


def _encode_png(width: int, height: int, rows: list[bytes]) -> bytes:
    body = b"".join(b"\x00" + row for row in rows)
    return (_PNG_SIGNATURE
            + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + _png_chunk(b"IDAT", zlib.compress(body, 6))
            + _png_chunk(b"IEND", b""))


def _png_chunk(tag: bytes, payload: bytes) -> bytes:
    checksum = zlib.crc32(tag + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", checksum)
