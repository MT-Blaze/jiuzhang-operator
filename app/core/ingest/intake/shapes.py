# -*- coding: utf-8 -*-
"""MinerU 转写四形状的确定性归一（BDP-01）：进 ``parse_question`` 之前把版式修直。

云端转写本身正确，损失在产品自己的 markdown→题目解析段。这里只治四种版式形状，
每一种都用精确的形状谓词守住边界——对已经能解析的存量文本**逐字不动**：

1. 选项独立成行：选项被空行劈成碎段（``A. 1\\n\\nB. 2…``），短段被切段器丢掉。
   只并「跑到文末的选项块」；选项后面还跟着节标题（如「三、填空题…」）的不并，
   因为那是另一段内容，并了会改变存量解析。
2. 卷首图片行：整行只有 ``![](images/….jpg)``。剥行＋如实登记警告——该相对路径
   不合契约 ``Image.uri`` 口径（只收 asset:// 与 /static/uploads/），且 mineru 回填路
   的题图以本地切图为准（``recognize.shared.merge_local``），剥行不丢题图。
3. 整题 ``$$…$$`` display 包裹＋题号拆裂：整段被包进一个 display 块、题号拆成
   「1 3.」。只在「整段恰是一个 display 块且块内有题号头」时 unwrap，并只修块首
   裂题号；正常文本里的数字不碰。
4. 填空 ``\\_\\_\\_\\_`` 无选项：转义下划线让 ``count_blanks`` 数不到空。只在
   「有转义空、无选项、无发问词」时还原下划线——已有发问词的存量题（它本来就解析
   得动）不动它的空，避免改写存量题型。

归一是纯函数、无 IO、无网络。``normalize`` 返回 ``(归一文本, 警告)``：没认出任何
形状时原样返回 ``(text, [])``。题号仍由题干头号承载（与存量解析同口径，mineru 回填路
的 ``source.question_no`` 由 ``merge_local`` 用本地切题题号覆盖）；裂题号「1 3.」修成
「13.」后，``intake.text`` 对「整段就一道带题号的题」直接认下，不再靠发问词兜底。
"""

from __future__ import annotations

import re

from app.core.content import question_parser
# 发问词与题号头复用 text.py 的同口径正则（单源）。text.py 在 build_documents 内
# 延迟导入本模块，故此处顶层反向导入不构成加载环。
from app.core.ingest.intake.text import _ASK_RE, _HEAD_NUM_RE

__all__ = ["normalize"]

_IMAGE_LINE = re.compile(r"^[ \t]*!\[[^\]]*\]\([^)]*\)[ \t]*$")
_DISPLAY_WRAP = re.compile(r"^\s*\$\$\s*([\s\S]+?)\s*\$\$\s*$")
_SPLIT_NUM = re.compile(r"^(\s*)(\d{1,3})[ \t]+(\d{1,3})([ \t]*[\.．、:：])")
_CHOICE_HEAD = re.compile(r"^\s*(?:[（(]\s*[A-HＡ-Ｈ]\s*[)）]|[A-HＡ-Ｈ]\s*[.．、:：)）])")
_CHOICE_A = re.compile(r"^\s*(?:[（(]\s*[AＡ]\s*[)）]|[AＡ]\s*[.．、:：)）])")
_ESCAPED_UNDERSCORE = re.compile(r"\\_")
_PARA_SPLIT = re.compile(r"\n\s*\n+")


def _strip_image_lines(text: str) -> tuple[str, list[str], bool]:
    """剥掉整行只有 markdown 图片的行，逐条登记警告（不静默丢）。"""
    kept: list[str] = []
    dropped: list[str] = []
    for line in text.split("\n"):
        if _IMAGE_LINE.match(line):
            target = line[line.find("](") + 2:line.rfind(")")]
            dropped.append(target.strip())
        else:
            kept.append(line)
    if not dropped:
        return text, [], False
    warnings = ["题干图片行已剥离（MinerU 转写图，题图以本地切图为准）：%s" % name
                for name in dropped]
    return "\n".join(kept), warnings, True


def _unwrap_display(text: str) -> tuple[str, bool]:
    """整段恰是一个 ``$$…$$`` 块且块内有题号头时 unwrap，并修块首裂题号。"""
    match = _DISPLAY_WRAP.match(text)
    if not match:
        return text, False
    inner = match.group(1)
    split = _SPLIT_NUM.match(inner)
    if split:
        inner = (split.group(1) + split.group(2) + split.group(3)
                 + split.group(4) + inner[split.end():])
    if not _HEAD_NUM_RE.match(inner):
        return text, False
    return inner.strip(), True


def _rejoin_terminal_options(text: str) -> tuple[str, bool]:
    """把跑到文末、被空行劈碎的选项块并回题干，选项各占一行（规范形）。"""
    paragraphs = [part.strip() for part in _PARA_SPLIT.split(text) if part.strip()]
    if len(paragraphs) < 2:
        return text, False
    start = -1
    for index in range(1, len(paragraphs)):
        if not _CHOICE_A.match(paragraphs[index]):
            continue
        if all(_CHOICE_HEAD.match(part) for part in paragraphs[index:]):
            start = index
            break
    if start < 0:
        return text, False
    block = " ".join(paragraphs[start:])
    split = question_parser.split_options(block)
    options = split.get("options") or []
    if not split.get("split") or len(options) < 2:
        return text, False
    canonical = "\n".join("%s. %s" % (option["label"], option["text"])
                          for option in options)
    stem = "\n\n".join(paragraphs[:start])
    return stem + "\n" + canonical, True


def _unescape_blanks(text: str) -> tuple[str, bool]:
    """无选项、无发问词的转义填空还原下划线，让 count_blanks 数得到空。"""
    if not _ESCAPED_UNDERSCORE.search(text):
        return text, False
    if _ASK_RE.search(text):
        return text, False
    if question_parser.split_options(text).get("split"):
        return text, False
    return text.replace("\\_", "_"), True


def normalize(text: str) -> tuple[str, list[str]]:
    """四形状归一；没认出形状就逐字原样返回 ``(text, [])``。"""
    if not isinstance(text, str) or not text.strip():
        return text, []
    warnings: list[str] = []
    working = text
    working, image_warnings, image_changed = _strip_image_lines(working)
    warnings.extend(image_warnings)
    working, display_changed = _unwrap_display(working)
    working, options_changed = _rejoin_terminal_options(working)
    working, blanks_changed = _unescape_blanks(working)
    if not (image_changed or display_changed or options_changed or blanks_changed):
        return text, []
    working = re.sub(r"\n{3,}", "\n\n", working).strip()
    return working, warnings