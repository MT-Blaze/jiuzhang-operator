"""本地极速提取的坏题体检：四特征判定，只报不改。

本地提取追求速度，代价是公式字体、题块切分与版式怪癖会把个别题啃坏。
这里不猜「怎么修」，只回答「哪几道看起来坏了」——修补由 ``ingest_route``
按坏题率决定：低于阈值只补坏题，高于阈值整批改走并发全量 OCR。

四条特征都只认**看得见的残缺**，绝不因为模型不认识某个公式就判坏：
1. 连续空选项：选择题选项连空两格，多半是版式或 OCR 串行；
2. 掉变量句式：出现「求的值」「已知，」或 ``$+$`` 这类被吃掉变量的公式；
3. 内联小图多但无公式：题面挂着好几张占位小图、却一个公式都没有；
4. 长文无符号：题干很长却没有任何数字、等号或数学运算符。
"""

from __future__ import annotations

import re
from typing import Any

_MISSING_VAR_RE = re.compile(r"(求|已知|设|若|则)\s*(?:的值|的取值|的范围|，|。|；|、)")
_BARE_OPERATOR_RE = re.compile(r"\$\s*[+\-*/=<>]\s*\$")
_EMPTY_SCRIPT_RE = re.compile(r"[$^_]\s*\{\s*\}")
_INLINE_IMAGE_RE = re.compile(r"\\includegraphics|\\begin\{tikzpicture\}|\[无法辨认\]|\ufffc")
_MATH_SYMBOL_RE = re.compile(r"[$=＝≠≤≥<>+\-×÷·/^_\\\d]")
_PLACEHOLDER_HEADS = ("（自动切题", "（待识别", "（自动 OCR", "（正在解析")

MAX_STEM_CHARS_WITHOUT_SYMBOL = 120


def _options(document: dict[str, Any]) -> list[dict[str, Any]]:
    raw = document.get("options")
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def _longest_empty_option_run(options: list[dict[str, Any]]) -> int:
    longest = streak = 0
    for option in options:
        if str(option.get("content") or "").strip():
            streak = 0
            continue
        streak += 1
        longest = max(longest, streak)
    return longest


def question_reasons(document: dict[str, Any]) -> list[str]:
    """一道题的坏题特征；空清单表示本地提取看起来没问题。"""
    reasons: list[str] = []
    stem = str(document.get("stem") or "").strip()
    if not stem or stem.startswith(_PLACEHOLDER_HEADS):
        reasons.append("空题干")
    if _longest_empty_option_run(_options(document)) >= 2:
        reasons.append("连续空选项")
    if (_MISSING_VAR_RE.search(stem) or _BARE_OPERATOR_RE.search(stem)
            or _EMPTY_SCRIPT_RE.search(stem)):
        reasons.append("掉变量句式")
    if len(_INLINE_IMAGE_RE.findall(stem)) >= 2 and "$" not in stem:
        reasons.append("内联小图多但无公式")
    if len(stem) >= MAX_STEM_CHARS_WITHOUT_SYMBOL and not _MATH_SYMBOL_RE.search(stem):
        reasons.append("长文无符号")
    return reasons


def triage_documents(documents: list[Any]) -> dict[str, Any]:
    """整批题目的坏题账：总题数、坏题数、坏题率与每一道的理由。"""
    docs = [document for document in documents if isinstance(document, dict)]
    bad_indexes: list[int] = []
    reasons: dict[int, list[str]] = {}
    for index, document in enumerate(docs):
        found = question_reasons(document)
        if not found:
            continue
        bad_indexes.append(index)
        reasons[index] = found
    total = len(docs)
    bad = len(bad_indexes)
    return {
        "total": total,
        "bad": bad,
        "rate": (bad / total) if total else 0.0,
        "bad_indexes": bad_indexes,
        "reasons": reasons,
    }
