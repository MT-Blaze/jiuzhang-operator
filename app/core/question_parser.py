"""录题文本的纯逻辑清洗与解析（无 IO、无网络、无数据库）。

老师从旧题库、试卷 PDF、OCR 里粘进来的题干通常带四类脏数据：
LaTeX 定界符不统一（``\\(`` / ``\\[`` / 半角混排）、选项挤在题干里、
填空答案混在解析段里，以及肉眼看不出的公式括号失衡。这里把
「清洗 → 拆分 → 提取 → 体检」拆成互不依赖的纯函数，宿主与插件可复用同一口径。

口径来自 ``schemas/question.json`` 与 PLUGIN_SPEC（Markdown + LaTeX，
行内 ``$...$``、独立 ``$$...$$``），实现独立完成，不引用旧题库源码。
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

__all__ = [
    "normalize_latex",
    "split_options",
    "extract_answer",
    "count_blanks",
    "sanity_check",
    "parse_question",
]

# 只在数学环境里做的记号归一：等价写法收敛到 KaTeX 都能稳定渲染的那一种。
_SYMBOLS = re.compile(r"\\(dfrac|tfrac|leq|leqslant|geq|geqslant|neq)(?![A-Za-z])")
_SYMBOL_MAP = {
    "dfrac": "frac",
    "tfrac": "frac",
    "leq": "le",
    "leqslant": "le",
    "geq": "ge",
    "geqslant": "ge",
    "neq": "ne",
}

_OPTION_LINE = re.compile(
    r"^\s*(?:[（(]\s*([A-HＡ-Ｈ])\s*[)）]|([A-HＡ-Ｈ])\s*[.．、:：)）])\s*(.*)$"
)
_OPTION_INLINE = re.compile(r"(?:^|[\s；;：:（(])([A-HＡ-Ｈ])\s*[.．、:：)）]\s*")

_ANSWER_PATTERNS = (
    re.compile(r"【\s*答\s*案\s*】\s*([^\n]*)"),
    re.compile(r"(?:故\s*)?答\s*案\s*[：:]\s*([^\n]*)"),
    re.compile(r"^[ \t]*答\s*[：:]\s*([^\n]*)", re.M),
)
_ANSWER_TAIL = re.compile(r"【\s*(?:解析|分析|详解|点睛|点评)\s*】|(?:解析|分析)\s*[：:]")
_SECTION_START = re.compile(r"^\s*(?:【|解析|分析|详解|点睛|点评|答案|答\s*[：:])")
_HTML_TAG = re.compile(r"<[A-Za-z/][^>]*>")
_REMOTE_ASSET = re.compile(r"(?:https?:)?//|data:[a-zA-Z]+/|file:")
_IMAGE_REF = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{[^}]*\}|!\[[^\]]*\]\([^)]*\)")
_BLANK = re.compile(r"_{2,}|＿{2,}|\\underline\{\s*\}")


def _line_math_state(text: str) -> list[bool]:
    """逐字符记录「是否处于数学环境」，用于不把公式里的 A. 当选项标记。"""
    state: list[bool] = []
    inside = False
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "\\" and i + 1 < n:
            state.append(inside)
            state.append(inside)
            i += 2
            continue
        if text.startswith("$$", i):
            state.append(inside)
            state.append(inside)
            i += 2
            inside = not inside
            continue
        if text[i] == "$":
            inside = not inside
        state.append(inside)
        i += 1
    return state


def _math_spans(text: str) -> list[tuple[int, int, bool]]:
    """返回 (起, 止, 是否为未闭合段)；未闭合段会一直延到文末。"""
    spans: list[tuple[int, int, bool]] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] == "\\" and i + 1 < n:
            i += 2
            continue
        if text.startswith("$$", i):
            end = text.find("$$", i + 2)
            if end < 0:
                spans.append((i, n, True))
                break
            spans.append((i, end + 2, False))
            i = end + 2
            continue
        if text[i] == "$":
            end = i + 1
            while end < n:
                if text[end] == "\\":
                    end += 2
                    continue
                if text[end] == "$":
                    break
                end += 1
            if end >= n:
                spans.append((i, n, True))
                break
            spans.append((i, end + 1, False))
            i = end + 1
            continue
        i += 1
    return spans


def normalize_latex(text: str) -> str:
    """定界符与等价记号归一；不动正文里的中文与人名，也不改写公式内容本身。"""
    if not isinstance(text, str):
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u200b", "").replace("\ufeff", "")

    # 反斜杠定界符：\( \) → $ ；\[ \] → $$。`\\[1ex]` 这类换行间距不能被误伤。
    text = re.sub(r"(?<!\\)\\\(", "$", text)
    text = re.sub(r"(?<!\\)\\\)", "$", text)
    text = re.sub(r"(?<!\\)\\\[", "$$", text)
    text = re.sub(r"(?<!\\)\\\]", "$$", text)

    def unify_math(segment: str) -> str:
        return _SYMBOLS.sub(lambda m: "\\" + _SYMBOL_MAP[m.group(1)], segment)

    pieces: list[str] = []
    cursor = 0
    for start, end, _unclosed in _math_spans(text):
        pieces.append(text[cursor:start])
        pieces.append(unify_math(text[start:end]))
        cursor = end
    pieces.append(text[cursor:])
    text = "".join(pieces)

    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _label(raw: str) -> str:
    return unicodedata.normalize("NFKC", raw).upper()


def _consecutive(labels: list[str]) -> bool:
    return bool(labels) and labels == [chr(ord("A") + index) for index in range(len(labels))]


def split_options(text: str) -> dict[str, Any]:
    """把「A. … B. …」这类选项从题干里剥出来；剥不出合法序列就原样返回。"""
    if not isinstance(text, str) or not text.strip():
        return {"stem": "", "options": [], "split": False, "tail": ""}

    math_state = _line_math_state(text)
    lines = text.split("\n")
    offset = 0
    line_starts: list[int] = []
    for line in lines:
        line_starts.append(offset)
        offset += len(line) + 1

    first = -1
    for index, line in enumerate(lines):
        match = _OPTION_LINE.match(line)
        if not match:
            continue
        start = line_starts[index] + match.start(1) if match.group(1) else line_starts[index] + match.start(2)
        if start < len(math_state) and math_state[start]:
            continue
        if _label(match.group(1) or match.group(2)) == "A":
            first = index
            break

    if first >= 0:
        options: list[dict[str, str]] = []
        labels: list[str] = []
        tail_start = len(lines)
        for index in range(first, len(lines)):
            match = _OPTION_LINE.match(lines[index])
            if not match:
                # 选项文字可能折行；但「解析/答案/【…】」是下一段，不能被吞进最后一个选项
                if options and lines[index].strip() and not _SECTION_START.match(lines[index]):
                    options[-1]["text"] = (options[-1]["text"] + "\n" + lines[index].strip()).strip()
                elif options and _SECTION_START.match(lines[index]):
                    tail_start = index
                    break
                continue
            label = _label(match.group(1) or match.group(2))
            expected = chr(ord("A") + len(labels))
            if label != expected:
                tail_start = index
                break
            labels.append(label)
            options.append({"label": label, "text": match.group(3).strip()})
        if len(options) >= 2 and options[0]["text"]:
            stem = "\n".join(lines[:first]).strip()
            tail = "\n".join(lines[tail_start:]).strip()
            return {"stem": stem, "options": options, "split": True, "tail": tail}

    matches = []
    for match in _OPTION_INLINE.finditer(text):
        start = match.start(1)
        if start < len(math_state) and math_state[start]:
            continue
        matches.append(match)
    labels = [_label(match.group(1)) for match in matches]
    if len(matches) >= 2 and _consecutive(labels):
        options = []
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            options.append({"label": labels[index], "text": text[match.end():end].strip(" \t；;，,")})
        if all(option["text"] for option in options):
            stem = text[: matches[0].start(1)].strip()
            return {"stem": stem, "options": options, "split": True, "tail": ""}

    return {"stem": text.strip(), "options": [], "split": False, "tail": ""}


def extract_answer(text: str) -> dict[str, Any]:
    """抓「【答案】/答案：/答：」后面的填空答案，并把该标签从正文里摘掉。"""
    if not isinstance(text, str) or not text.strip():
        return {"answer": "", "body": "", "matched": False}
    for pattern in _ANSWER_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue
        raw = match.group(1)
        value = _ANSWER_TAIL.split(raw, maxsplit=1)[0]
        value = value.strip().strip("；;，,。")
        if not value:
            continue
        body = (text[: match.start()] + text[match.end():]).strip()
        body = re.sub(r"\n{3,}", "\n\n", body).strip()
        return {"answer": value, "body": body, "matched": True}
    return {"answer": "", "body": text.strip(), "matched": False}


def count_blanks(stem: str) -> int:
    """数填空题的空：连续下划线或 `\\underline{}` 都算一个空。"""
    if not isinstance(stem, str):
        return 0
    return len(_BLANK.findall(stem))


def _issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def sanity_check(
    stem: str, options: list[dict[str, Any]] | None = None, answer: str = ""
) -> list[dict[str, str]]:
    """录题体检：只报告，不改写。每条带稳定 code，UI 可按 code 归类。"""
    issues: list[dict[str, str]] = []
    text = stem if isinstance(stem, str) else ""
    if not text.strip():
        issues.append(_issue("empty_stem", "题干为空"))
        return issues

    if _HTML_TAG.search(text):
        issues.append(_issue("stray_html", "题干含 HTML 标签：题目只接受 Markdown + LaTeX"))

    spans = _math_spans(text)
    if any(unclosed for _start, _end, unclosed in spans):
        issues.append(_issue("unbalanced_math", "数学定界符 $ / $$ 未配对"))

    for start, end, unclosed in spans:
        if unclosed:
            continue
        segment = text[start:end]
        opened = segment.count("{") - segment.count("\\{")
        closed = segment.count("}") - segment.count("\\}")
        if opened != closed:
            issues.append(_issue("unbalanced_braces", f"公式内花括号不配对：{segment[:40]}"))
        if segment.count("\\left") != segment.count("\\right"):
            issues.append(_issue("unbalanced_left_right", f"公式内 \\left 与 \\right 数量不一致：{segment[:40]}"))
        for name in re.findall(r"\\begin\{([^}]+)\}", segment):
            if f"\\end{{{name}}}" not in segment:
                issues.append(_issue("unmatched_environment", f"环境 {name} 没有对应的 \\end"))

    for reference in _IMAGE_REF.findall(text):
        if _REMOTE_ASSET.search(reference):
            issues.append(_issue("remote_asset", f"图片引用必须走 asset:// 或底座托管路径：{reference[:60]}"))
            break

    if options:
        labels = [str(option.get("label", "")) for option in options]
        if len(set(labels)) != len(labels) or not _consecutive(labels):
            issues.append(_issue("option_labels", "选项标号必须从 A 起连续且不重复"))
        if any(not str(option.get("text", "")).strip() for option in options):
            issues.append(_issue("empty_option", "存在空选项"))

    if answer and _HTML_TAG.search(answer):
        issues.append(_issue("stray_html_answer", "答案含 HTML 标签"))

    return issues


def parse_question(text: str) -> dict[str, Any]:
    """一条流水线：归一 → 拆选项 → 提答案 → 体检。行为等价于手工按顺序调用。"""
    normalized = normalize_latex(text)
    split = split_options(normalized)
    head = extract_answer(split["stem"])
    # 选项后面还挂着「【答案】/解析」：答案在尾段里，题干不能被它污染
    tail = extract_answer(split["tail"]) if split.get("tail") else {"answer": ""}
    answer = head["answer"] or tail["answer"]
    stem = head["body"].strip()
    issues = sanity_check(stem, split["options"], answer)
    return {
        "stem": stem,
        "options": split["options"],
        "answer": answer,
        "blanks": count_blanks(stem),
        "issues": issues,
    }
