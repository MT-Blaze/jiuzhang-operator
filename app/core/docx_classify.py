"""Word 预分拣：只用标准库看清 docx 里到底有什么，不让内容静默消失。

钉住四类：

- A 结构完整：有原生公式 ``m:oMath``，没有图片型公式对象；
- B 文字好、公式是图：正文可用，且存在 ``w:drawing`` / ``w:object`` /
  ``v:imagedata`` / ``w:pict`` 这类图片或嵌入对象；
- C 整页扫描：``word/media/`` 只有 1~2 张整页大图，文字近乎为零；
- D 排版复杂：浮动图片锚点、文本框或多栏，本阶段只记录不下刀。

同时产出「图形对象顺序表」：inline 对象按文档流精确编号；anchor 只记录存在，
不做坐标换算。
"""

from __future__ import annotations

import io
import posixpath
import struct
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field

from app.core.docx_omml import omml_to_latex

__all__ = [
    "DocxProbeError",
    "GraphicObject",
    "ProbeResult",
    "classify_docx",
]

DOCUMENT_PART = "word/document.xml"
RELS_PART = "word/_rels/document.xml.rels"
MEDIA_PREFIX = "word/media/"
SCAN_TEXT_LIMIT = 32
WORDPROCESSINGML_HINT = "wordprocessingml"
_GRAPHIC_CONTAINERS = frozenset({"drawing", "object", "pict"})
_SKIP_INLINE = frozenset({
    "pPr", "rPr", "del", "moveFrom", "instrText", "proofErr",
    "bookmarkStart", "bookmarkEnd", "sdtPr", "txbxContent", "Fallback",
})
_EMU_PER_PX = 9525.0


class DocxProbeError(Exception):
    """docx 结构不可处理（缺正文、XML 解析失败等）；坏 zip 仍抛 BadZipFile。"""


@dataclass
class GraphicObject:
    """文档流里的一个图形对象；``index`` 从 1 起，与占位标记一致。"""

    index: int
    tag: str
    inline: bool
    paragraph: int
    has_image: bool
    rel_id: str = ""
    media: str = ""
    width_px: int = 0
    height_px: int = 0


@dataclass
class ProbeResult:
    kind: str
    reason: str
    text: str
    warnings: list[str] = field(default_factory=list)
    graphics: list[GraphicObject] = field(default_factory=list)
    media: list[str] = field(default_factory=list)
    text_chars: int = 0
    run_count: int = 0
    omml_count: int = 0
    carriers: dict[str, int] = field(default_factory=dict)

    @property
    def page_only(self) -> bool:
        return self.kind == "C"


@dataclass
class _FlowState:
    rels: dict[str, str]
    media_sizes: dict[str, tuple[int, int]]
    graphics: list[GraphicObject] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    paragraph: int = 0
    sequence: int = 0


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _namespace(tag: str) -> str:
    return tag[1:].split("}", 1)[0] if tag.startswith("{") else ""


def _is_wml(tag: str) -> bool:
    return WORDPROCESSINGML_HINT in _namespace(tag)


def _attr(node: ET.Element, name: str) -> str:
    for key, value in node.attrib.items():
        if _local(key) == name:
            return value
    return ""


def _children(node: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in node if _local(child.tag) == name]


def _has_descendant(node: ET.Element, name: str) -> bool:
    return any(_local(element.tag) == name for element in node.iter())


def _read_rels(archive: zipfile.ZipFile, names: list[str]) -> dict[str, str]:
    if RELS_PART not in names:
        return {}
    try:
        root = ET.fromstring(archive.read(RELS_PART))
    except ET.ParseError:
        return {}
    rels: dict[str, str] = {}
    for node in root.iter():
        if _local(node.tag) != "Relationship":
            continue
        rel_id = _attr(node, "Id")
        target = _attr(node, "Target")
        if not rel_id or not target:
            continue
        if target.startswith("/"):
            resolved = target.lstrip("/")
        else:
            resolved = posixpath.normpath(posixpath.join("word", target))
        rels[rel_id] = resolved
    return rels


def _image_size(raw: bytes) -> tuple[int, int]:
    """从文件头读图片像素尺寸；认不出就返回 (0, 0)，绝不猜。"""
    if raw.startswith(b"\x89PNG\r\n\x1a\n") and len(raw) >= 24 and raw[12:16] == b"IHDR":
        return struct.unpack(">II", raw[16:24])
    if raw.startswith(b"\xff\xd8"):
        return _jpeg_size(raw)
    if raw[:6] in (b"GIF87a", b"GIF89a") and len(raw) >= 10:
        return struct.unpack("<HH", raw[6:10])
    if raw.startswith(b"BM") and len(raw) >= 26:
        width, height = struct.unpack("<ii", raw[18:26])
        return abs(width), abs(height)
    if raw.startswith(b"RIFF") and raw[8:12] == b"WEBP" and raw[12:16] == b"VP8X" \
            and len(raw) >= 30:
        width = 1 + int.from_bytes(raw[24:27], "little")
        height = 1 + int.from_bytes(raw[27:30], "little")
        return width, height
    return 0, 0


def _jpeg_size(raw: bytes) -> tuple[int, int]:
    index = 2
    length = len(raw)
    while index + 9 <= length:
        if raw[index] != 0xFF:
            index += 1
            continue
        marker = raw[index + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            index += 2
            continue
        size = struct.unpack(">H", raw[index + 2:index + 4])[0]
        if size < 2:
            return 0, 0
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                      0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            height, width = struct.unpack(">HH", raw[index + 5:index + 9])
            return width, height
        index += 2 + size
    return 0, 0


def _archive_image_size(archive: zipfile.ZipFile, name: str) -> tuple[int, int]:
    try:
        with archive.open(name) as handle:
            return _image_size(handle.read(65536))
    except (KeyError, OSError, RuntimeError):
        return 0, 0


def _near_full_page(width: int, height: int) -> bool:
    if width <= 0 or height <= 0:
        return False
    return width >= 450 and height >= 650 and width * height >= 400000


def _find_rel_id(node: ET.Element) -> str:
    for element in node.iter():
        for key, value in element.attrib.items():
            if _local(key) in ("embed", "id") and value.startswith("rId"):
                return value
    return ""


def _extent_px(node: ET.Element) -> tuple[int, int]:
    for element in node.iter():
        if _local(element.tag) != "extent":
            continue
        try:
            width = int(_attr(element, "cx"))
            height = int(_attr(element, "cy"))
        except (TypeError, ValueError):
            continue
        return int(width / _EMU_PER_PX), int(height / _EMU_PER_PX)
    return 0, 0


def _record_graphic(node: ET.Element, state: _FlowState) -> str:
    state.sequence += 1
    rel_id = _find_rel_id(node)
    media = state.rels.get(rel_id, "")
    width, height = state.media_sizes.get(media, (0, 0))
    if not width or not height:
        width, height = _extent_px(node)
    state.graphics.append(GraphicObject(
        index=state.sequence,
        tag=_local(node.tag),
        inline=not _has_descendant(node, "anchor"),
        paragraph=state.paragraph,
        has_image=bool(media or rel_id),
        rel_id=rel_id,
        media=media,
        width_px=width,
        height_px=height,
    ))
    return "[公式图:%d]" % state.sequence


def _walk_inline(node: ET.Element, state: _FlowState) -> str:
    out: list[str] = []
    for child in node:
        name = _local(child.tag)
        if name in _SKIP_INLINE:
            continue
        if name == "t" and _is_wml(child.tag):
            out.append(child.text or "")
            continue
        if name == "tab" and _is_wml(child.tag):
            out.append("\t")
            continue
        if name in ("br", "cr") and _is_wml(child.tag):
            out.append("\n")
            continue
        if name == "oMath":
            result = omml_to_latex(child)
            state.warnings.extend(
                item for item in result.warnings if item not in state.warnings)
            latex = result.latex.strip()
            if latex:
                out.append("$" + latex + "$")
            else:
                out.append("[公式]")
                if "有一处公式转换结果为空，已保留占位标记" not in state.warnings:
                    state.warnings.append("有一处公式转换结果为空，已保留占位标记")
            continue
        if name in _GRAPHIC_CONTAINERS and _is_wml(child.tag):
            out.append(_record_graphic(child, state))
            continue
        if name == "imagedata" and _namespace(child.tag).endswith("vml"):
            out.append(_record_graphic(child, state))
            continue
        out.append(_walk_inline(child, state))
    return "".join(out)


def _walk_table(node: ET.Element, state: _FlowState) -> str:
    out: list[str] = []
    for row in _children(node, "tr"):
        for cell in _children(row, "tc"):
            out.append(_walk_block(cell, state))
            out.append("\t")
        out.append("\n")
    return "".join(out)


def _walk_block(node: ET.Element, state: _FlowState) -> str:
    out: list[str] = []
    for child in node:
        name = _local(child.tag)
        if name == "Fallback":
            continue
        if name == "p" and _is_wml(child.tag):
            state.paragraph += 1
            out.append(_walk_inline(child, state))
            out.append("\n")
            continue
        if name == "tbl":
            out.append(_walk_table(child, state))
            continue
        if name in ("sectPr", "tblPr", "trPr", "tcPr", "tblGrid"):
            continue
        out.append(_walk_block(child, state))
    return "".join(out)


def _text_stats(root: ET.Element) -> tuple[int, int]:
    chars = 0
    runs = 0
    stack = [root]
    while stack:
        node = stack.pop()
        if _local(node.tag) == "Fallback":
            continue
        if _is_wml(node.tag):
            name = _local(node.tag)
            if name == "t":
                chars += len((node.text or "").strip())
            elif name == "r":
                runs += 1
        stack.extend(reversed(list(node)))
    return chars, runs


def _carrier_counts(root: ET.Element) -> tuple[dict[str, int], bool]:
    keys = ("oMath", "drawing", "object", "pict", "imagedata", "anchor", "txbxContent")
    counts = {key: 0 for key in keys}
    multi_columns = False
    stack = [root]
    while stack:
        node = stack.pop()
        name = _local(node.tag)
        if name == "Fallback":
            continue
        if name in counts:
            counts[name] += 1
        if name == "cols" and _is_wml(node.tag):
            try:
                multi_columns = int(_attr(node, "num") or "1") > 1
            except ValueError:
                pass
        stack.extend(reversed(list(node)))
    return counts, multi_columns


def _classify(result: ProbeResult, state: _FlowState,
              multi_columns: bool) -> tuple[str, str]:
    media_big = [name for name in result.media
                 if _near_full_page(*state.media_sizes.get(name, (0, 0)))]
    if 1 <= len(media_big) <= 2 and result.text_chars <= SCAN_TEXT_LIMIT \
            and not result.omml_count:
        return "C", "word/media 有 %d 张整页大图、文字近乎为零" % len(media_big)
    if result.carriers.get("anchor") or result.carriers.get("txbxContent") or multi_columns:
        return "D", "存在浮动图片锚点、文本框或多栏排版"
    if result.omml_count and not result.graphics:
        return "A", "有 %d 处原生公式，无图片型公式对象" % result.omml_count
    if result.graphics:
        return "B", "正文可用，但有 %d 处图形/公式图片对象" % len(result.graphics)
    return "A", "没有公式与图形对象，按纯文字处理"


def _graphic_warnings(result: ProbeResult) -> list[str]:
    notes: list[str] = []
    for graphic in result.graphics:
        if graphic.has_image:
            notes.append("第 %d 处公式是图片，待后续识别" % graphic.index)
        else:
            notes.append("第 %d 处图形对象不是图片，待后续识别" % graphic.index)
    return notes


def classify_docx(data: bytes) -> ProbeResult:
    """docx 字节 → 分拣结果；坏 zip 抛 ``BadZipFile``，缺正文抛 ``DocxProbeError``。"""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        if DOCUMENT_PART not in names:
            raise DocxProbeError("这个 Word 文件里没有正文（document.xml）")
        raw = archive.read(DOCUMENT_PART)
        media = sorted(name for name in names
                       if name.startswith(MEDIA_PREFIX) and not name.endswith("/"))
        sizes = {name: _archive_image_size(archive, name) for name in media}
        rels = _read_rels(archive, names)
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise DocxProbeError("这个 Word 的正文 XML 解析失败") from exc
    counts, multi_columns = _carrier_counts(root)
    text_chars, run_count = _text_stats(root)
    state = _FlowState(rels=rels, media_sizes=sizes)
    flow_text = _walk_block(root, state)
    for graphic in state.graphics:
        if graphic.media and sizes.get(graphic.media) == (0, 0) \
                and graphic.width_px and graphic.height_px:
            sizes[graphic.media] = (graphic.width_px, graphic.height_px)
    result = ProbeResult(
        kind="A", reason="", text="", media=media, text_chars=text_chars,
        run_count=run_count, omml_count=counts["oMath"],
        carriers=counts, graphics=state.graphics, warnings=list(state.warnings),
    )
    result.kind, result.reason = _classify(result, state, multi_columns)
    if result.kind == "C":
        result.text = ""
        result.warnings.append(
            "整页扫描图：word/media 中检测到整页大图、文字近乎为零，"
            "按页面图处理，不生成题目")
        return result
    if result.kind == "D":
        result.text = ""
        result.warnings.append(
            "排版复杂（浮动图片锚点/文本框/多栏）：本阶段只提取文字，"
            "版式与浮动对象待后续阶段处理")
        return result
    result.text = flow_text.strip()
    if result.kind == "B":
        result.warnings.extend(_graphic_warnings(result))
    return result
