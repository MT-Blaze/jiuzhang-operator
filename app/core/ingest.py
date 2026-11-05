"""拖入文件的分拣与解析：PDF / Word / TeX / MD / 图片 → 中转站里的一批待审题。

分拣**只看后缀**：老师拖进来的是什么就按什么走，绝不信文件自报的 MIME。

- 文本类（``.tex`` / ``.md`` / ``.txt``）：轻量解析。认得两种版式——
  录题工作台的 exam-zh 源码（``\\begin{question}`` / ``\\begin{solution}``），
  以及普通文本（按题号切题，再拆选项、提答案）。
- ``.docx``：标准库 ``zipfile`` 解出 ``word/document.xml`` 的纯文本，再走文本类同一条路。
- ``.pdf``：先尽力抽文本层（本机没有 PDF 渲染器，抽不出就是抽不出）。
- 图片：走 OCR（AI 视觉）。
- ``.zip``：**静默忽略**——插件安装包走的是另一条道。

**认不出就不编**：OCR 失败时如实记一条「待识别」的待审题（图片挂在那儿，题干留占位），
老师自己在审核台里补。底座宁可交白卷，也不生成一道凭空捏造的题。
**纯图片 PDF 一道占位题都不放**：文本层不可用就只拆页图、立一个空批次；
老师进批次后在左侧【框选切题】，松开鼠标即生成一道新题。
"""

from __future__ import annotations

import base64
import binascii
import io
import json
import re
import zipfile
import zlib
from typing import Any

from app.core import page_render, question_parser

__all__ = [
    "classify",
    "decode_text",
    "extract_docx_text",
    "extract_pdf_text",
    "build_documents",
    "ingest_files",
    "stage_ingest",
    "run_ingest_jobs",
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

OCR_SYSTEM_PROMPT = (
    "你是试卷转写助手。把图片里的题目**逐字**转成 Markdown + LaTeX 文本："
    "保留题号、题干、选项（A/B/C/D 各占一行）、答案与解析；"
    "公式写成 $...$ 或 $$...$$；看不清的地方写 [无法辨认]，"
    "绝不补写图片上没有的内容。"
)

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


# ---------------------------------------------------------------- 分拣


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


# ---------------------------------------------------------------- 各类文件的取字


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
                candidates = [name for name in names if name.startswith("word/") and name.endswith(".xml")]
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


def _pdf_streams(data: bytes) -> list[bytes]:
    """把 PDF 里的 stream 段落取出来并尽力解压。"""
    streams: list[bytes] = []
    for match in re.finditer(rb"stream\r?\n", data):
        start = match.end()
        end = data.find(b"endstream", start)
        if end < 0:
            continue
        chunk = data[start:end]
        try:
            streams.append(zlib.decompressobj().decompress(chunk))
        except zlib.error:
            streams.append(chunk)
    return streams


def _decode_pdf_string(token: bytes) -> str:
    """PDF 里的字符串：字面串 ``(...)`` 与十六进制串 ``<...>``。"""
    if token.startswith(b"<"):
        raw = re.sub(rb"[^0-9A-Fa-f]", b"", token[1:-1])
        if len(raw) % 2:
            raw += b"0"
        data = bytes.fromhex(raw.decode("ascii"))
        for encoding in ("utf-16-be", "utf-8"):
            try:
                return data.decode(encoding)
            except UnicodeDecodeError:
                continue
        return data.decode("latin-1", errors="replace")
    body = token[1:-1]
    out = bytearray()
    index = 0
    escapes = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}
    while index < len(body):
        char = body[index]
        if char != 0x5C:  # 反斜杠
            out.append(char)
            index += 1
            continue
        index += 1
        if index >= len(body):
            break
        nxt = body[index]
        if nxt in escapes:
            out.append(escapes[nxt])
            index += 1
        elif 0x30 <= nxt <= 0x37:  # 八进制
            digits = bytearray()
            while index < len(body) and len(digits) < 3 and 0x30 <= body[index] <= 0x37:
                digits.append(body[index])
                index += 1
            out.append(int(digits.decode("ascii"), 8) & 0xFF)
        elif nxt == 0x0A:  # 续行
            index += 1
        else:
            out.append(nxt)
            index += 1
    return bytes(out).decode("latin-1", errors="replace")


def extract_pdf_text(data: bytes) -> tuple[str, int]:
    """PDF → (文本, 页数)。

    只取文本层里的字符串算子（``Tj`` / ``TJ``）；本机没有 PDF 渲染器，
    扫不出字就是扫不出——调用方据此决定是走 OCR 还是记「待识别」。
    """
    pages = len(re.findall(rb"/Type\s*/Page[^s]", data)) or 1
    pieces: list[str] = []
    for stream in _pdf_streams(data):
        if b"Tj" not in stream and b"TJ" not in stream:
            continue
        for match in re.finditer(rb"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]+>", stream):
            token = match.group(0)
            if not token.startswith(b"(") and not token.startswith(b"<"):
                continue
            try:
                pieces.append(_decode_pdf_string(token))
            except (ValueError, UnicodeDecodeError):
                continue
    text = "\n".join(piece for piece in pieces if piece.strip())
    return text, pages


def _text_usable(text: str) -> bool:
    """抽出来的字够不够看：太短或大量乱码就当没抽到。"""
    stripped = text.strip()
    if len(stripped) < 20:
        return False
    printable = sum(1 for char in stripped if char.isprintable() or char in "\n\t")
    return printable / max(1, len(stripped)) > 0.9


# ---------------------------------------------------------------- 切题与组卷


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


# ---------------------------------------------------------------- OCR


async def ocr_image(data: bytes, mime: str) -> tuple[str, str]:
    """图片 → 文字。返回 (文本, 失败原因)；失败时文本是空串。

    认不出就是认不出：失败时**不编**任何题目文字，由调用方记「待识别」。
    """
    from app.core import ai_client

    client = ai_client.get_client()
    if client.is_mock:
        return "", "本机没有配置可用的 AI Provider（缺密钥），图片认不出来"
    data_url = f"data:{mime};base64," + base64.b64encode(data).decode("ascii")
    try:
        result = await client.chat_completion(
            system_prompt=OCR_SYSTEM_PROMPT,
            user_message="请把这张图片里的题目逐字转写出来。",
            temperature=0.1,
            max_tokens=4000,
            images=[data_url],
        )
    except Exception as exc:  # noqa: BLE001 — 任何失败都如实报，绝不编题
        return "", f"OCR 调用失败：{exc}"
    return str(result.get("content") or ""), ""


# ---------------------------------------------------------------- 入口


def _placeholder(label: str) -> dict[str, Any]:
    """一条「待识别」的占位题：题干写明要老师补，不含任何编造内容。"""
    return {
        "type": "solution",
        "stem": label,
        "difficulty": DEFAULT_DIFFICULTY,
        "tags": ["待识别"],
    }


async def _items_from_file(name: str, data: bytes) -> tuple[list[dict[str, Any]], list[str], str, str, bool]:
    """一个文件 → (题目文档, 警告, 分拣类别, 抽出来的源文本, 是否纯图片卷)。

    最后一个 ``True`` 表示文本层不可用：这批**一道题都不落池**，
    只把 PDF 拆成原卷页面图，老师进批次后在左侧自己【框选切题】。
    """
    kind = classify(name)
    warnings: list[str] = []
    if kind == "text":
        text = decode_text(data)
        documents, notes = build_documents(text)
        return documents, warnings + notes, kind, text, False
    if kind == "docx":
        text = extract_docx_text(data)
        documents, notes = build_documents(text)
        return documents, warnings + notes, kind, text, False
    if kind == "pdf":
        text, _pages = extract_pdf_text(data)
        if _text_usable(text):
            documents, notes = build_documents(text)
            return documents, warnings + notes, kind, text, False
        warnings.append(
            f"{name}：未识别出文本（PDF 文本层不可用）。"
            "已拆成原卷页面图，请进批次后在左侧【框选切题】逐题框选录入。"
        )
        # 文本层不可用就只出页面图，一条占位题都不落池：老师直接对着原卷框选。
        return [], warnings, kind, "", True
    if kind == "image":
        mime = IMAGE_MIME.get(suffix_of(name), "image/png")
        if len(data) > MAX_IMAGE_BYTES:
            return [], warnings + [f"{name}：图片太大（上限 8 MiB），没认"], kind, "", False
        text, reason = await ocr_image(data, mime)
        if not text.strip():
            warnings.append(f"{name}：{reason or '认不出文字'}，留了一条待识别")
            return [_placeholder(f"（待识别：{name}，图片认不出文字，请老师补录）")], \
                warnings, kind, "", False
        documents, notes = build_documents(text)
        if not documents:
            warnings.append(f"{name}：认出来了，但没拆出题目，留了一条待识别")
            return [_placeholder(f"（待识别：{name}，认出了文字但没拆出题目）")], \
                warnings, kind, text, False
        return documents, warnings + notes, kind, text, False
    return [], warnings, kind, "", False


async def ingest_files(files: Any) -> dict[str, Any]:
    """把拖进来的一批文件变成中转站里的待审题（**同步跑完**）。

    ``files`` 形如 ``[{"name": "卷子.pdf", "data_url": "data:application/pdf;base64,..."}]``。
    **一个文件一个批次**，各批独立解析；返回聚合账：
    ``{"batch_id", "batch_ids", "batches", "saved_ids", "warnings", "ignored", "kinds"}``。

    线上走的是两段式（``stage_ingest`` + ``run_ingest_jobs``）：批次先立起来，
    识别放后台，老师不用盯着屏幕等 OCR。这里保留同步版给脚本与测试用。
    """
    staged = stage_ingest(files)
    groups = staged.pop("jobs", [])
    for group in groups:
        await run_ingest_jobs(group["batch_id"], group["jobs"])
    if groups:
        # 同步版跑完要按解析后的真账回报：题数与 id 都可能变了。
        from app.core import pending_bank
        refreshed: list[dict[str, Any]] = []
        saved_ids: list[str] = []
        for one in staged["batches"]:
            rows = pending_bank.list_batch_questions(one["batch_id"])
            ids = [row["id"] for row in rows["items"]]
            saved_ids.extend(ids)
            card = one.get("batch")
            for entry in pending_bank.batch_list()["batches"]:
                if entry["batch_id"] == one["batch_id"]:
                    card = entry
                    break
            refreshed.append({**one, "saved_ids": ids, "batch": card})
        staged["batches"] = refreshed
        staged["saved_ids"] = saved_ids
    return staged


def stage_ingest(files: Any) -> dict[str, Any]:
    """第一段：分拣、解码，**按文件各立一个批次**。

    老师拖进 9 份卷子就立 9 个批次（B-002、B-003……），各认各的、各解析各的。
    有文本层的先放一条「正在解析」占位题；纯图片 PDF 连占位题都不放，只在后台
    渲染出页图后挂到批次上，老师进批次自己【框选切题】。

    返回聚合账：``{"batch_id", "batch_ids", "batches", "saved_ids", "warnings",
    "ignored", "kinds", "jobs"}``；``jobs`` 按批次分组，``batch_id`` 是第一份的批次号。
    """
    if not isinstance(files, list) or not files:
        raise IngestError("没有要处理的文件")
    if len(files) > MAX_FILES:
        raise IngestError(f"一次最多处理 {MAX_FILES} 个文件")

    ignored: list[str] = []
    loaded: list[tuple[str, bytes]] = []

    # 先把整包验一遍再落批次：后面的文件不合格时，前面的批次不该已经建出来。
    for entry in files:
        if not isinstance(entry, dict):
            raise IngestError("每个文件都要是对象")
        name = str(entry.get("name") or "").strip() or "未命名文件"
        if classify(name) == "zip":
            # 插件安装包走另一条道：这里静默忽略，不提示、不建批次。
            ignored.append(name)
            continue
        data = decode_bytes(entry.get("data_url") or entry.get("data"))
        if len(data) > MAX_FILE_BYTES:
            raise IngestError(f"{name}：文件太大（上限 32 MiB）")
        if not data:
            raise IngestError(f"{name}：文件是空的")
        loaded.append((name, data))

    if not loaded:
        return {"batch_id": "", "batch_ids": [], "batches": [], "saved_ids": [],
                "warnings": [], "ignored": ignored, "kinds": [], "jobs": []}

    batches: list[dict[str, Any]] = []
    warnings: list[str] = []
    kinds: list[str] = []
    saved_ids: list[str] = []
    job_groups: list[dict[str, Any]] = []
    for name, data in loaded:
        one = _stage_one_batch(name, data)
        one_jobs = one.pop("jobs", [])
        if one_jobs:
            job_groups.append({"batch_id": one["batch_id"], "jobs": one_jobs})
        batches.append(one)
        warnings.extend(one.get("warnings") or [])
        kinds.extend(one.get("kinds") or [])
        saved_ids.extend(one.get("saved_ids") or [])

    first = batches[0]
    return {
        "batch_id": first["batch_id"],
        "batch": first.get("batch"),
        "batch_ids": [one["batch_id"] for one in batches],
        "batches": batches,
        "saved_ids": saved_ids,
        "warnings": warnings,
        "ignored": ignored,
        "kinds": kinds,
        "jobs": job_groups,
    }


def _page_only_pdf(name: str, data: bytes) -> bool:
    """是不是「只有图、没有字」的 PDF：是就只拆页图，不落任何占位题。"""
    if classify(name) != "pdf":
        return False
    try:
        text, _pages = extract_pdf_text(data)
    except Exception:  # noqa: BLE001 — 抽不出文本就按纯图片卷走
        return True
    return not _text_usable(text)


def _stage_one_batch(name: str, data: bytes) -> dict[str, Any]:
    """一份文件立一个批次。

    能抽出文本层的卷子先放一条「正在解析」的占位题，识别完就地替换；
    纯图片 PDF 连占位题都不放——只立批次，页面图由后台渲染后挂到批次上。
    """
    from app.core import pending_bank

    # 原件在老师自己的盘上，底座只在工作区里留一份只读副本，批次审完即删。
    backup = json.dumps([pending_bank.store_source_backup(name, data)],
                        ensure_ascii=False, separators=(",", ":"))
    scan_only = _page_only_pdf(name, data)
    if scan_only:
        result = pending_bank.create_batch(source_backup=backup, source_name=name,
                                           scan=True)
        warnings = [f"{name}：未识别出文本（PDF 文本层不可用）。已拆成原卷页面图，请进批次后在左侧【框选切题】逐题框选录入。"]
    else:
        result = pending_bank.save_draft(
            [{"question": _placeholder(f"（正在解析：{name}）")}],
            source_backup=backup,
            source_name=name,
            origin="ingest",
        )
        warnings = []
    result["warnings"] = warnings
    result["ignored"] = []
    result["kinds"] = [classify(name)]
    result["page_only"] = scan_only
    result["jobs"] = [{
        "pending_id": result["saved_ids"][0] if result.get("saved_ids") else "",
        "name": name,
        "data": data,
        "page_only": scan_only,
    }]
    return result


async def run_ingest_jobs(batch_id: str, jobs: list[dict[str, Any]]) -> None:
    """第二段：识别。

    - 有文本层：识别出来的题**就地替换**那条「正在解析」的占位题；
    - 纯图片 PDF：只把渲染出来的页面图挂到批次上，**一条题都不落池**——
      老师进批次后在左侧原卷上自己【框选切题】。
    """
    from app.core import pending_bank
    from app.core.pending_assets import drop_assets

    for job in jobs or []:
        pending_id = str((job or {}).get("pending_id") or "")
        name = str((job or {}).get("name") or "")
        data = (job or {}).get("data") or b""
        page_only = bool((job or {}).get("page_only"))
        if not name or not batch_id:
            continue
        if not page_only and not pending_id:
            continue
        page_images: list[dict[str, Any]] = []
        doc_pages: list[int] = []
        scan_mode = page_only
        if page_only:
            documents, kind, source_text = [], "pdf", ""
        else:
            try:
                documents, _notes, kind, source_text, scan_mode = await _items_from_file(name, data)
            except Exception as error:  # noqa: BLE001 - 后台单份失败不许带崩整批
                documents = []
                kind = ""
                source_text = ""
                scan_mode = False
        # 原卷页在识别之后立刻出：哪怕一道题都没拆出来，老师也得能对着原卷补录。
        try:
            page_images, doc_pages, _page_notes = page_render.build_pages(
                name, kind, data, source_text, documents)
        except Exception:  # noqa: BLE001 - 页面图失败只影响左栏，不耽误拆题
            page_images, doc_pages = [], []
        if scan_mode:
            if page_images:
                try:
                    pending_bank.set_batch_pages(batch_id, page_images)
                except Exception:  # noqa: BLE001 — 挂不上页图就清掉文件，批次留着
                    drop_assets(page_images)
                    continue
            if pending_id:
                # 老式占位轮留下的那条占位题：页图已挂上，清掉它不再占池。
                try:
                    pending_bank.delete_pending(pending_id)
                except pending_bank.PendingError:
                    pass
            continue
        items: list[dict[str, Any]] = []
        if documents:
            items.append({"question": documents[0], "pending_id": pending_id,
                          "page_no": _page_of(doc_pages, 0)})
            items.extend({"question": document, "page_no": _page_of(doc_pages, index)}
                         for index, document in enumerate(documents[1:], start=1))
        else:
            items.append({
                "question": _placeholder(f"（待识别：{name}，识别没成功，请老师补录）"),
                "pending_id": pending_id,
                "page_no": 1,
            })
        try:
            pending_bank.save_draft(items, batch_id=batch_id, origin="ingest",
                                    page_images=page_images)
        except Exception:  # noqa: BLE001 - 这一份写不进去就留着占位题，不动别的
            if page_images:
                drop_assets(page_images)
            continue


def _page_of(doc_pages: list[int], index: int) -> int:
    return doc_pages[index] if 0 <= index < len(doc_pages) else 1
