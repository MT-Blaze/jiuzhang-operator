"""文本、Word 与题号切分：从字节到契约题目文档，不碰批次与网络。"""

from __future__ import annotations

import base64
import binascii
import io
import re
import zipfile
from typing import Any

from app.core import question_parser

__all__ = [
    "DEFAULT_DIFFICULTY",
    "IMAGE_MIME",
    "IMAGE_SUFFIXES",
    "IngestError",
    "MAX_FILE_BYTES",
    "MAX_FILES",
    "MAX_IMAGE_BYTES",
    "TEXT_SUFFIXES",
    "build_documents",
    "classify",
    "decode_bytes",
    "decode_text",
    "extract_docx_text",
    "suffix_of",
]

# 单个文件的上限：老师拖的是试卷，不是硬盘。
MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_FILES = 20
# 单张图片的上限（OCR 走网络，再大也没意义）。
MAX_IMAGE_BYTES = 8 * 1024 * 1024
# 难度只能先给一个默认档：机器不许替老师判断题目难不难。
DEFAULT_DIFFICULTY = "L2"

TEXT_SUFFIXES = (".tex", ".md", ".markdown", ".txt", ".text")
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")
PDF_SUFFIXES = (".pdf",)
DOCX_SUFFIXES = (".docx",)
ZIP_SUFFIXES = (".zip",)

IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg",
              ".jpeg": "image/jpeg", ".webp": "image/webp"}

_DATA_URL_RE = re.compile(r"^data:([\w./+-]+);base64,([A-Za-z0-9+/=]+)$")

# exam-zh 版式（录题工作台的源码格式）。
_ENV_RE = re.compile(r"\\begin\{(question|problem)\}([\s\S]*?)\\end\{\1\}")
_SOLUTION_RE = re.compile(r"\\begin\{solution\}([\s\S]*?)\\end\{solution\}")
_CHOICES_RE = re.compile(r"\\begin\{choices\}([\s\S]*?)\\end\{choices\}")
_ITEM_SPLIT_RE = re.compile(r"\\item\b")
_ANSWER_HEAD_RE = re.compile(r"^\s*答案\s*[:：]\s*([^\n]*)")

# 普通文本的题号头：「1.」「1、」「（1）」「第 1 题」。
_HEAD_NUM_RE = re.compile(
    r"^\s*(?:第\s*([0-9]{1,3})\s*题|[\(（]?\s*([0-9]{1,3})\s*[\)）\.．、:：])"
)
_FILLIN_RE = re.compile(r"\\fillin(?![A-Za-z])")

# 无题号兜底段的发问词：求、证、算、判这类才像是在问一道题。
_ASK_RE = re.compile(
    r"(求|证明|试证|解答|解方程|解不等式|计算|化简|判断|辨析|作图|作出|"
    r"填空|填写|写出|列举|讨论|估计|估算|回答|比较|试算|论述|探究)"
)
# 数学内容的痕迹：有公式、等号、上下标或数字。
_MATH_HINT_RE = re.compile(r"(\$|=|＝|≠|≤|≥|×|÷|\^|\d)")


class IngestError(Exception):
    """拖进来的东西没法处理（后缀不认识、文件太大、编码不对等）。"""


def suffix_of(filename: Any) -> str:
    """文件名后缀（小写，带点）。"""
    text = str(filename or "").strip()
    if "." not in text:
        return ""
    return "." + text.rsplit(".", 1)[-1].lower()


def classify(filename: Any) -> str:
    """按后缀分拣：text / docx / pdf / image / zip / unknown。"""
    suffix = suffix_of(filename)
    if suffix in TEXT_SUFFIXES:
        return "text"
    if suffix in DOCX_SUFFIXES:
        return "docx"
    if suffix in PDF_SUFFIXES:
        return "pdf"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in ZIP_SUFFIXES:
        return "zip"
    return "unknown"


def decode_bytes(data: bytes) -> bytes:
    """data URL → 字节；不是 data URL 就当裸字节。"""
    if isinstance(data, str):
        match = _DATA_URL_RE.match(data.strip())
        if match:
            try:
                return base64.b64decode(match.group(2), validate=False)
            except (binascii.Error, ValueError) as exc:
                raise IngestError("文件内容不是合法的 base64") from exc
        raise IngestError("文件内容必须是 data URL")
    if not isinstance(data, (bytes, bytearray)):
        raise IngestError("文件内容必须是字节")
    return bytes(data)


def decode_text(data: bytes) -> str:
    """文本解码：UTF-8 优先，GBK 兜底（老师的卷子多是 GBK 存的）。"""
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def extract_docx_text(data: bytes) -> str:
    """``.docx`` → 纯文本。

    docx 就是个 zip：正文在 ``word/document.xml`` 里。这里只用标准库解，
    不引第三方依赖——题库侧不因老师拖进来一个 Word 就多背一个包。
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            names = archive.namelist()
            part = "word/document.xml"
            if part not in names:
                candidates = [name for name in names
                              if name.startswith("word/") and name.endswith(".xml")]
                if not candidates:
                    raise IngestError("这个 Word 文件里没有正文（document.xml）")
                part = candidates[0]
            raw = archive.read(part)
    except zipfile.BadZipFile as exc:
        raise IngestError("这个 .docx 文件损坏，解不开") from exc
    text = raw.decode("utf-8", errors="replace")
    # XML 里标签之间的空白没有意义：先收掉，否则每个段落之间会多出一个空行，
    # 切题时一段题会被劈成好几段。
    text = re.sub(r">\s+<", "><", text)
    # 段落与换行先变成真字符，再把剩下的标签剥掉。
    text = re.sub(r"</w:p>", "\n", text)
    text = re.sub(r"<w:br[^>]*/>", "\n", text)
    text = re.sub(r"<w:tab[^>]*/>", "\t", text)
    text = re.sub(r"<[^>]+>", "", text)
    return _unescape_xml(text)


def _unescape_xml(text: str) -> str:
    return (text.replace("&lt;", "<").replace("&gt;", ">")
            .replace("&quot;", '"').replace("&apos;", "'").replace("&amp;", "&"))


def _split_exam_zh(text: str) -> list[dict[str, Any]]:
    """把整段 exam-zh 源码切成一道道题。"""
    blocks: list[dict[str, Any]] = []
    matches = list(_ENV_RE.finditer(text))
    for index, match in enumerate(matches):
        stop = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        tail = text[match.end():stop]
        solution = _SOLUTION_RE.search(tail)
        blocks.append({
            "env": match.group(1),
            "body": match.group(2),
            "solution": solution.group(1) if solution else "",
        })
    return blocks


def _choices_of(body: str) -> tuple[str, list[str]]:
    """从题干里摘出 ``\\begin{choices}`` 选项块，返回 (剩下的题干, 选项列表)。"""
    match = _CHOICES_RE.search(body)
    if not match:
        return body, []
    items = [item.strip() for item in _ITEM_SPLIT_RE.split(match.group(1))]
    choices = [item for item in items if item]
    if len(choices) < 2:
        return body, []
    rest = body[:match.start()] + body[match.end():]
    return rest, choices


def _match_choice_keys(answer_text: str, options: list[dict[str, str]]) -> list[str]:
    """把答案文字对上选项字母：对不上就返回空（**绝不猜**）。"""
    text = str(answer_text or "").strip()
    if not text:
        return []
    upper = text.upper()
    letters = re.findall(r"[A-H]", upper)
    residue = re.sub(r"[A-H\s,，、;；]", "", upper)
    if letters and not residue:
        keys = [item for item in letters if item in {option["key"] for option in options}]
        return list(dict.fromkeys(keys))
    for option in options:
        if option["content"].strip() == text:
            return [option["key"]]
    return []


def _document(stem: str, options: list[dict[str, str]], answer_text: str,
              blanks: int, solution: str = "", question_no: str = "") -> dict[str, Any]:
    """按解析结果拼一道**契约口径**的题目文档。"""
    stem = question_parser.normalize_latex(stem)
    stem = _FILLIN_RE.sub("＿＿＿＿", stem)
    document: dict[str, Any] = {"stem": stem, "difficulty": DEFAULT_DIFFICULTY}
    clean_options = [
        {"key": option["key"], "content": question_parser.normalize_latex(option["content"])}
        for option in options
    ]
    if clean_options:
        keys = _match_choice_keys(answer_text, clean_options)
        multi = "（多选）" in stem or "(多选)" in stem
        document["type"] = "multiple_choice" if (multi and len(keys) >= 2) else "single_choice"
        document["options"] = clean_options
        if keys:
            if document["type"] == "multiple_choice":
                document["answer"] = {"kind": "choice", "choice_keys": keys,
                                      "final": "".join(keys)}
            elif len(keys) == 1:
                document["answer"] = {"kind": "choice", "choice_keys": keys,
                                      "final": keys[0]}
    elif blanks > 0:
        document["type"] = "fill_blank"
        if answer_text:
            document["answer"] = {"kind": "text", "content": answer_text, "final": answer_text}
    else:
        document["type"] = "solution"
        if answer_text:
            document["answer"] = {"kind": "text", "content": answer_text, "final": answer_text}
    if solution:
        document["solution"] = question_parser.normalize_latex(solution)
    if question_no:
        document["source"] = {"question_no": question_no}
    return document


def _document_from_exam_zh(block: dict[str, Any]) -> dict[str, Any] | None:
    """一段 exam-zh 源码 → 一道题；拆不出题干就返回 None（如实跳过）。"""
    body, choices = _choices_of(block["body"])
    stem = body.strip()
    if not stem:
        return None
    answer_text = ""
    analysis = ""
    solution = str(block["solution"] or "").strip()
    if solution:
        head = _ANSWER_HEAD_RE.match(solution)
        if head:
            answer_text = head.group(1).strip()
            analysis = solution[head.end():].strip()
        else:
            analysis = solution
    options = [{"key": chr(ord("A") + index), "content": item}
               for index, item in enumerate(choices)]
    blanks = len(_FILLIN_RE.findall(stem))
    return _document(stem, options, answer_text, blanks, analysis)


def _split_numbered(text: str) -> list[tuple[str, str]]:
    """按题号切段；题号不成串就退回按空行切段。返回 [(段落, 题号)]。"""
    lines = text.split("\n")
    heads: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        match = _HEAD_NUM_RE.match(line)
        if not match:
            continue
        number = match.group(1) or match.group(2)
        if number:
            heads.append((index, int(number)))
    if len(heads) >= 2:
        run = _longest_number_run(heads)
        if len(run) >= 2:
            segments: list[tuple[str, str]] = []
            for order, (line_index, number) in enumerate(run):
                stop = run[order + 1][0] if order + 1 < len(run) else len(lines)
                segment = "\n".join(lines[line_index:stop]).strip()
                if segment:
                    segments.append((segment, str(number)))
            return segments
    return [(part.strip(), "") for part in _split_paragraphs(text)]


def _longest_number_run(heads: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """找出最长的一段「题号连续递增」的题号链。

    只有连续递增才算一列题；孤零零一个「2.」多半是句子里的数字，不切。
    """
    best: list[tuple[int, int]] = []
    current: list[tuple[int, int]] = []
    for head in heads:
        if current and head[1] == current[-1][1] + 1:
            current.append(head)
        else:
            if len(current) > len(best):
                best = current
            current = [head]
    if len(current) > len(best):
        best = current
    return best


def _split_paragraphs(text: str) -> list[str]:
    """按空行切段：没有题号的纸卷也只能这么切。"""
    parts = re.split(r"\n\s*\n+", text)
    return [part.strip() for part in parts if len(part.strip()) >= 8]


def _looks_like_question(segment: str, parsed: dict[str, Any]) -> bool:
    """无题号的兜底段要**像一道数学题**才收下。

    早先的兜底是「有字就算题」，于是老师拖进来一段说明文字，审核台里就躺着一道
    「题」——内容确实是老师的原话，但它不是题。这里只收有数学题特征的段：
    有选项、有空、有答案标记，或者有求/证这类发问词且带数学内容。
    """
    if parsed.get("options"):
        return True
    if int(parsed.get("blanks") or 0) > 0:
        return True
    if str(parsed.get("answer") or "").strip():
        return True
    if not _ASK_RE.search(segment):
        return False
    return bool(_MATH_HINT_RE.search(segment))


def build_documents(text: str) -> tuple[list[dict[str, Any]], list[str]]:
    """整段文本 → 一批题目文档（契约口径）与警告。

    先认 exam-zh 版式；认不出再按题号切；再不行按空行切。
    """
    warnings: list[str] = []
    blocks = _split_exam_zh(text)
    if blocks:
        documents: list[dict[str, Any]] = []
        for block in blocks:
            document = _document_from_exam_zh(block)
            if document is None:
                warnings.append("有一段 exam-zh 源码没拆出题干，已跳过")
                continue
            documents.append(document)
        if documents:
            return documents, warnings
    documents = []
    for segment, number in _split_numbered(text):
        parsed = question_parser.parse_question(segment)
        if not str(parsed.get("stem") or "").strip():
            continue
        if not number and not _looks_like_question(segment, parsed):
            continue
        options = [
            {"key": str(option.get("label") or ""), "content": str(option.get("text") or "")}
            for option in parsed.get("options") or []
        ]
        documents.append(_document(
            str(parsed.get("stem") or ""),
            options,
            str(parsed.get("answer") or ""),
            int(parsed.get("blanks") or 0),
            question_no=number,
        ))
    if not documents:
        warnings.append("这份文件里没拆出任何题目")
    return documents, warnings
