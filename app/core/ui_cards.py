"""ui_json 富卡片契约：底座生成结构化卡片，前端负责渲染。

对话气泡只承载自然语言与 ``ui_json`` 围栏；卡片里的所有字段都是**数据**，
不是 HTML。前端用 textContent / 安全 DOM 组装，LaTeX 由本地 KaTeX 渲染，
不执行任何插件或模型返回的标记。

三类卡片（2026-10-25 v0.5.5 军令）：
- ``question_card``：一道或多道题目，附题型/难度标签与「查看解析」；
- ``install_card``：插件安装建议，必须由用户点「确认安装」才触网下载；
- ``confirm_card``：操作确认，按钮把对应指令送回对话区。
"""

from __future__ import annotations

import json
from typing import Any

from app.core.contract import normalize_difficulty

CARD_VERSION = "1.0"
MAX_CARDS = 3
MAX_STEM = 4000
MAX_SOLUTION = 4000
MAX_OPTIONS = 10
MAX_TAGS = 8
MAX_TEXT = 240

_ALLOWED_TYPES = {"question_card", "install_card", "confirm_card"}


def _text(value: Any, limit: int = MAX_TEXT) -> str:
    if value is None:
        return ""
    return str(value).strip()[:limit]


def question_card(question: dict[str, Any]) -> dict[str, Any]:
    """把 plugin_tools 归一化后的题目裁剪成卡片载荷（只留展示必需字段）。"""
    options: list[dict[str, str]] = []
    for option in (question.get("options") or [])[:MAX_OPTIONS]:
        if not isinstance(option, dict):
            continue
        options.append(
            {
                "key": _text(option.get("key"), 8),
                "content": _text(option.get("content"), 1000),
            }
        )
    tags = [
        _text(item, 32)
        for item in (question.get("tags") or [])[:MAX_TAGS]
        if str(item).strip()
    ]
    return {
        "id": _text(question.get("id"), 80),
        "question_no": question.get("question_no")
        if isinstance(question.get("question_no"), int)
        else None,
        "type": _text(question.get("type"), 32) or "unknown",
        "type_label": _text(question.get("type_label"), 16) or "待定",
        "difficulty": normalize_difficulty(_text(question.get("difficulty"), 16)) or "L2",
        "difficulty_label": _text(question.get("difficulty_label"), 16) or "中档",
        "stem": _text(question.get("stem"), MAX_STEM),
        "options": options,
        "answer": _text(question.get("answer"), 1000),
        "solution": _text(question.get("solution"), MAX_SOLUTION),
        "tags": tags,
    }


def question_block(questions: list[dict[str, Any]]) -> dict[str, Any] | None:
    cards = [question_card(item) for item in questions[:MAX_CARDS] if isinstance(item, dict)]
    cards = [card for card in cards if card["stem"]]
    if not cards:
        return None
    return {"version": CARD_VERSION, "type": "question_card", "questions": cards}


def install_block(entry: dict[str, Any], reason: str = "") -> dict[str, Any]:
    """安装建议卡。zip 地址只用于用户点击后的那一次下载，不预下载、不自动装。"""
    return {
        "version": CARD_VERSION,
        "type": "install_card",
        "plugin": {
            "id": _text(entry.get("id"), 80),
            "name": _text(entry.get("name"), 64),
            "version": _text(entry.get("version"), 32),
            "kind": _text(entry.get("kind"), 16),
            "description": _text(entry.get("description"), 200),
            "homepage": _text(entry.get("homepage"), 300),
            "zip_url": _text(entry.get("zip_url"), 800),
            "mirrors": [
                _text(item, 800)
                for item in (entry.get("mirrors") or [])[:8]
                if _text(item, 800)
            ],
        },
        "reason": _text(reason, 200),
    }


def confirm_block(
    title: str, description: str, actions: list[dict[str, str]]
) -> dict[str, Any] | None:
    cleaned: list[dict[str, str]] = []
    for action in actions[:4]:
        if not isinstance(action, dict):
            continue
        label = _text(action.get("label"), 20)
        command = _text(action.get("command"), 200)
        if label and command:
            cleaned.append({"label": label, "command": command})
    if not cleaned:
        return None
    return {
        "version": CARD_VERSION,
        "type": "confirm_card",
        "title": _text(title, 60) or "操作确认",
        "description": _text(description, 400),
        "actions": cleaned,
    }


def _renderable(block: dict[str, Any]) -> bool:
    """空壳卡片不下发：前端认不出内容时只会留下一个空框。"""
    kind = block.get("type")
    if kind == "question_card":
        questions = block.get("questions")
        return isinstance(questions, list) and any(
            isinstance(item, dict) and str(item.get("stem") or "").strip() for item in questions
        )
    if kind == "install_card":
        plugin = block.get("plugin")
        return (
            isinstance(plugin, dict)
            and bool(str(plugin.get("name") or "").strip())
            and bool(str(plugin.get("zip_url") or "").strip())
        )
    if kind == "confirm_card":
        actions = block.get("actions")
        return isinstance(actions, list) and any(
            isinstance(item, dict) and item.get("label") and item.get("command") for item in actions
        )
    return False


def frame(block: dict[str, Any] | None) -> str:
    """把卡片载荷包成前端可拦截的 ```ui_json 围栏；非法或空壳卡片返回空串。"""
    if not isinstance(block, dict) or block.get("type") not in _ALLOWED_TYPES:
        return ""
    if not _renderable(block):
        return ""
    body = json.dumps(block, ensure_ascii=False, separators=(",", ":"))
    return "```ui_json\n" + body + "\n```"


def frames_for_blocks(blocks: list[dict[str, Any]]) -> str:
    parts = [frame(block) for block in blocks[:MAX_CARDS]]
    return "\n\n".join(part for part in parts if part)
