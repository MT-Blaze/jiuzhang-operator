"""结构化题目 → exam-zh 源码（方案 A 的底座侧套壳）。

前端只向模型要「题干 / 选项 / 答案 / 解析」这些正文，环境骨架一律由这里套：
选择题 ``question + choices``、填空 ``question + \\fillin``、解答 ``problem``，
解析统一进 ``solution`` 且首行必须是「答案：」。口径与插件里的
``buildExamSource`` 逐字一致，两边都不许各自发挥。
"""

from __future__ import annotations

import re
from typing import Any

OPTION_KEYS = "ABCDEFGH"
_EMPTY_BRACKET = re.compile(r"[（(][ \t\u3000]*[）)]")
_DUP_BRACKET = re.compile(r"([（(][ \t\u3000]*[）)])(?:[ \t]*[（(][ \t\u3000]*[）)])+")
_CHOICES_ENV = re.compile(r"\\begin\{choices\}[\s\S]*?\\end\{choices\}")


def ensure_choice_bracket(stem: str, multi: bool) -> str:
    text = _DUP_BRACKET.sub(r"\1", str(stem or "").rstrip())
    if multi and "（多选）" not in text:
        text += "（多选）"
    if not _EMPTY_BRACKET.search(text):
        text += "（  ）"
    return text


def answer_text(question: dict[str, Any]) -> str:
    answer = question.get("answer")
    if isinstance(answer, dict):
        keys = answer.get("choice_keys")
        if isinstance(keys, list) and keys:
            return "".join(str(item) for item in keys)
        for name in ("final", "content"):
            value = str(answer.get(name) or "").strip()
            if value:
                return value
        return ""
    return str(answer or "").strip()


def solution_block(question: dict[str, Any]) -> str:
    head = "答案：" + answer_text(question)
    body = str(question.get("solution") or "").strip()
    return head + ("\n" + body if body else "")


def build_exam_source(question: dict[str, Any]) -> str:
    item = question or {}
    kind = str(item.get("type") or "solution")
    stem = _CHOICES_ENV.sub("", str(item.get("stem") or "")).strip()
    out = ""
    if kind in ("single_choice", "multiple_choice"):
        options = [option for option in (item.get("options") or [])
                   if str(option.get("content") or "").strip()]
        lines = ["  \\item " + str(option.get("content") or "").strip() for option in options]
        out += ("\\begin{question}\n" + ensure_choice_bracket(stem, kind == "multiple_choice")
                + "\n\\begin{choices}\n" + "\n".join(lines) + "\n\\end{choices}\n"
                + "\\end{question}\n\n")
    elif kind == "fill_blank":
        out += "\\begin{question}\n" + stem + "\n\\end{question}\n\n"
    else:
        out += "\\begin{problem}\n" + stem + "\n\\end{problem}\n\n"
    return out + "\\begin{solution}\n" + solution_block(item) + "\n\\end{solution}\n"
