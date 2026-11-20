"""exam-zh 源码的切块小助手：整段源码 → 题块，题干 → 选项块。"""

from __future__ import annotations

import re
from typing import Any

# exam-zh 版式（录题工作台的源码格式）。
_ENV_RE = re.compile(r"\\begin\{(question|problem)\}([\s\S]*?)\\end\{\1\}")
_SOLUTION_RE = re.compile(r"\\begin\{solution\}([\s\S]*?)\\end\{solution\}")
_CHOICES_RE = re.compile(r"\\begin\{choices\}([\s\S]*?)\\end\{choices\}")
_ITEM_SPLIT_RE = re.compile(r"\\item\b")


def split_exam_zh(text: str) -> list[dict[str, Any]]:
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


def choices_of(body: str) -> tuple[str, list[str]]:
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
