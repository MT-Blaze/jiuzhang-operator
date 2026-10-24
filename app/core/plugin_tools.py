"""已安装插件 → OpenAI Function Calling 工具桥。

设计边界（2026-10-24 v0.5.1 军令）：
- 底座扫描 ``plugins/`` 的 ``plugin.json``，把插件**声明过的能力**翻译成
  OpenAI ``tools`` 格式；没有可执行能力的插件不出现，避免给模型假工具。
- 当前可执行的是前端插件可被宿主代劳的两种只读能力：
  ``question.import``（读取插件自带 ``seed/questions.json``）与
  ``question.render``（按题号/题目 id 生成题卡结构）。
- 插件脚本仍运行在沙箱 iframe 内；后端不执行插件 JS，也不给插件任何写权限。
  工具只读插件自己的数据与当前工作区题库，不触网、不写库。
- 工具参数来自模型，一律视为不可信：动作枚举、题号范围、题目 id 格式全部
  在底座侧重新校验。
"""

from __future__ import annotations

import json
import random
import re
import sqlite3
from pathlib import Path
from typing import Any

from app.core import bank as bank_store
from app.core import bank_provider
from app.core import questions as question_store
from app.core.config import settings
from app.core.contract import DIFFICULTY_LABELS as CONTRACT_DIFFICULTY_LABELS
from app.core.contract import normalize_difficulty
from app.core.plugins import discover_plugins

TOOL_PREFIX = "plugin_"
MAX_TOOLS = 32
MAX_TOOL_CALLS = 3
MAX_SEED_BYTES = 2 * 1024 * 1024
MAX_SEED_QUESTIONS = 200
MAX_RESULT_QUESTIONS = 20

ACTION_IMPORT = "import_questions"
ACTION_RENDER = "render_question"

_CAPABILITY_ACTIONS = {
    "question.import": ACTION_IMPORT,
    "question.render": ACTION_RENDER,
}

TYPE_LABELS = {
    "single_choice": "单选",
    "multiple_choice": "多选",
    "fill_blank": "填空",
    "solution": "解答",
    "proof": "证明",
    "unknown": "待定",
}
DIFFICULTY_LABELS = dict(CONTRACT_DIFFICULTY_LABELS)

_QUESTION_ID = re.compile(r"^q_[A-Za-z0-9_-]{1,64}$")
_CN_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


class PluginToolError(Exception):
    """工具名、参数或插件数据不可用。"""


def tool_name_for(plugin_id: str) -> str:
    """插件 id → OpenAI 函数名（只留字母数字下划线连字符，截断到 64）。"""
    slug = re.sub(r"[^A-Za-z0-9_-]", "_", plugin_id)
    return (TOOL_PREFIX + slug)[:64]


def _actions_for(plugin: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    for capability in plugin.get("capabilities") or []:
        action = _CAPABILITY_ACTIONS.get(capability)
        if action and action not in actions:
            actions.append(action)
    return actions


def _action_description(plugin_name: str, action: str) -> str:
    if action == ACTION_IMPORT:
        return (
            f"读取「{plugin_name}」插件自带的题库（seed/questions.json），可按题号取出单题或列出前几题。"
            "用户说「拆分第 X 题」「导入题目」「看看题库」时用这个动作。"
        )
    return (
        f"把一道题渲染成「{plugin_name}」的题卡结构（题型、题干、选项、答案、解析）。"
        "可传 question_no（题库序号）或 question_id（已有题目 id）。"
    )


def _tool_schema(plugin: dict[str, Any], actions: list[str]) -> dict[str, Any]:
    has_import = ACTION_IMPORT in actions
    has_render = ACTION_RENDER in actions
    properties: dict[str, Any] = {
        "action": {
            "type": "string",
            "enum": actions,
            "description": "要执行的插件动作。拆分/导入题目用 import_questions；生成题卡用 render_question。",
        }
    }
    if has_import or has_render:
        properties["question_no"] = {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_SEED_QUESTIONS,
            "description": "题号：第一题填 1，第二题填 2，以此类推。",
        }
    if has_import:
        properties["limit"] = {
            "type": "integer",
            "minimum": 1,
            "maximum": MAX_RESULT_QUESTIONS,
            "description": "未指定题号时最多列出几题，默认 5。",
        }
        properties["random"] = {
            "type": "boolean",
            "description": "为 true 时从题库随机抽一题；与 question_no 二选一。",
        }
        properties["difficulty"] = {
            "type": "string",
            "enum": list(DIFFICULTY_LABELS.keys()),
            "description": "随机抽题时按难度筛选：L1=基础，L2=中档，L3=难，L4=压轴；缺省不限。",
        }
        properties["grade"] = {
            "type": "string",
            "enum": ["高一", "高二", "高三"],
            "description": "随机抽题时按年级筛选；题库未标注年级时底座会如实说明未过滤。",
        }
    if has_render:
        properties["question_id"] = {
            "type": "string",
            "pattern": "^q_[A-Za-z0-9_-]{1,64}$",
            "description": "当前工作区题库里已有题目的 id；与 question_no 二选一。",
        }

    hints = [_action_description(plugin["name"], action) for action in actions]
    return {
        "type": "function",
        "function": {
            "name": tool_name_for(plugin["id"]),
            "description": (
                f"{plugin['name']}（{plugin['id']}）：{plugin['description']} "
                + " ".join(hints)
            )[:1024],
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": ["action"],
                "additionalProperties": False,
            },
        },
    }


def build_tools() -> list[dict[str, Any]]:
    """扫描已安装插件，返回可直接塞进 OpenAI 请求体的 ``tools`` 数组。"""
    tools: list[dict[str, Any]] = []
    for plugin in discover_plugins().get("plugins", []):
        actions = _actions_for(plugin)
        if not actions:
            continue
        tools.append(_tool_schema(plugin, actions))
        if len(tools) >= MAX_TOOLS:
            break
    return tools


def tool_names(tools: list[dict[str, Any]]) -> list[str]:
    return [
        item.get("function", {}).get("name", "")
        for item in tools
        if isinstance(item, dict)
    ]


# --- 宿主内置工具：按关键词检索当前工作区题库（军令 #15 任务 3）---
# 边界：模型与插件都只交出关键词。读 SQLite、算命中数、取示例题全部由底座在
# 本进程里代劳（bank / bank_provider 都是宿主模块），示例题只回前几条，
# 不把整库递给模型；命中数与「前往题库并搜索」跳转动作一起回传给对话插件。
HOST_BANK_TOOL = "search_question_bank"
BANK_MAX_QUERY = 40
BANK_PREVIEW_LIMIT = 3

_BANK_SCOPE_WORDS = ("题库", "题集")
_BANK_COUNT_RE = re.compile(r"(?:多少|几)\s*(?:道|题|个)")
_BANK_QUERY_WORDS = ("搜", "查", "找", "检索", "统计", "看")
_BANK_KEYWORD_RE = re.compile(r"(?:多少|几)\s*道\s*([^\s，,。？?、！!]{1,24}?)\s*题")
_BANK_QUOTED_RE = re.compile(r"[「“\"'《]([^」”\"'》]{1,24})[」”\"'》]")
_BANK_SCOPED_RE = re.compile(r"(?:里的|中的|的)\s*([^\s，,。？?、！!]{2,12}?)\s*(?:题目|题)")
_BANK_STOP_QUERIES = {"多少", "这些", "那些", "哪些", "题目", "题", "导数题"}


def build_bank_tool() -> dict[str, Any]:
    """把题库检索工具塞进 OpenAI ``tools``：参数只有关键词，动作在底座侧。"""
    return {
        "type": "function",
        "function": {
            "name": HOST_BANK_TOOL,
            "description": (
                "按关键词检索当前工作区题库并由底座统计命中数量。"
                "用户问「题库里有多少道导数题」「查一下含数列的题目」「题库一共有多少题」时调用；"
                "query 传题干关键词（如「导数」「立体几何」），留空则统计全库总数。"
                "底座会回总数、命中数与前几道示例题，并附一个「前往题库并搜索」跳转动作。"
                "你不得编造底座没返回的题目或数量。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "maxLength": BANK_MAX_QUERY,
                        "description": "题干关键词，例如「导数」「数列」「立体几何」；留空表示不限关键词。",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": BANK_PREVIEW_LIMIT,
                        "description": "最多回几道示例题，默认 3。",
                    },
                },
                "additionalProperties": False,
            },
        },
    }


def _bank_jump(keyword: str, provider: dict[str, Any]) -> dict[str, Any]:
    """跳转动作：AI 只声明「去哪、带什么参数」，打开与注入由底座执行。"""
    return {
        "type": "open_bank",
        "label": "前往题库并搜索" if keyword else "前往题库",
        "query": keyword,
        "plugin_id": str(provider.get("plugin_id") or ""),
    }


def _run_bank_search(args: dict[str, Any]) -> dict[str, Any]:
    keyword_raw = args.get("query", "")
    if keyword_raw is not None and not isinstance(keyword_raw, str):
        raise PluginToolError("query 必须是字符串")
    keyword = str(keyword_raw or "").strip()[:BANK_MAX_QUERY]
    limit = args.get("limit", BANK_PREVIEW_LIMIT)
    limit = max(1, min(int(limit), BANK_PREVIEW_LIMIT))

    provider = bank_provider.resolve()
    provider_id = str(provider.get("plugin_id") or "")
    provider_name = str(provider.get("name") or provider_id or "本地题库")
    base = {
        "ok": True,
        "host_tool": True,
        "plugin": {"id": provider_id, "name": provider_name},
        "action": HOST_BANK_TOOL,
    }
    try:
        items, matched = bank_store.list_questions(
            provider_id, search=keyword, page=1, page_size=limit
        )
        total_all = int(bank_store.stats(provider_id).get("total") or 0)
    except (bank_store.BankError, sqlite3.Error, OSError, ValueError) as exc:
        return {
            **base,
            "ok": False,
            "error": str(exc),
            "summary": f"读取题库「{provider_name}」失败：{exc}",
        }

    questions = [_normalize_question(item, index + 1) for index, item in enumerate(items)]
    if keyword:
        summary = (
            f"题库「{provider_name}」共 {total_all} 题，含「{keyword}」的有 {matched} 道。"
        )
        if questions:
            summary += _format_list(questions, matched)
        else:
            summary += "没有找到匹配的题目，可以换个关键词再查。"
    else:
        summary = f"题库「{provider_name}」共 {total_all} 题。"
        if questions:
            summary += _format_list(questions, total_all)
    return {
        **base,
        "summary": summary,
        "data": {
            "total": total_all,
            "matched": matched,
            "query": keyword,
            "questions": questions,
        },
        "jump": _bank_jump(keyword, provider),
    }


def execute_bank_tool(arguments: Any) -> dict[str, Any]:
    """执行题库检索工具；参数不可信，失败也回可读结果而不是抛到路由层。"""
    try:
        args = _coerce_arguments(arguments)
        return _run_bank_search(args)
    except (PluginToolError, ValueError, TypeError) as exc:
        return {
            "ok": False,
            "host_tool": True,
            "plugin": {"id": "builtin.bank", "name": "本地题库"},
            "action": HOST_BANK_TOOL,
            "error": str(exc),
            "summary": f"题库检索失败：{exc}",
        }


def _coerce_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments or "{}")
        except json.JSONDecodeError as exc:
            raise PluginToolError(f"工具参数不是合法 JSON：{exc}") from exc
    else:
        parsed = arguments
    if not isinstance(parsed, dict):
        raise PluginToolError("工具参数必须是 JSON 对象")
    return parsed


def _extract_bank_query(text: str) -> str:
    quoted = _BANK_QUOTED_RE.search(text)
    if quoted:
        return quoted.group(1).strip()
    for pattern in (_BANK_KEYWORD_RE, _BANK_SCOPED_RE):
        match = pattern.search(text)
        if match:
            token = match.group(1).strip()
            if token and token not in _BANK_STOP_QUERIES:
                return token
    return ""


def match_bank_intent(user_input: str) -> dict[str, Any] | None:
    """「题库里有多少道导数题」这类句式在无 tool_calls 时由宿主直连题库检索工具。"""
    text = str(user_input or "").strip()
    if not text:
        return None
    if not any(word in text for word in _BANK_SCOPE_WORDS):
        return None
    wants_count = _BANK_COUNT_RE.search(text) is not None
    wants_query = any(word in text for word in _BANK_QUERY_WORDS)
    if not (wants_count or wants_query):
        return None
    # 「拆分/导入题目」是插件工具的活，别被题库检索抢走。
    if any(word in text for word in ("拆", "导入", "取回", "组卷")):
        return None
    return {"tool": HOST_BANK_TOOL, "arguments": {"query": _extract_bank_query(text)[:BANK_MAX_QUERY]}}


def _find_plugin(tool_name: str) -> dict[str, Any]:
    for plugin in discover_plugins().get("plugins", []):
        if tool_name_for(plugin["id"]) == tool_name:
            return plugin
    raise PluginToolError(f"没有找到工具对应的已安装插件：{tool_name}")


def _seed_path(plugin_id: str) -> Path | None:
    root = (Path(settings.plugins_dir) / plugin_id).resolve()
    path = (root / "seed" / "questions.json").resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    if not path.is_file():
        return None
    if path.stat().st_size > MAX_SEED_BYTES:
        raise PluginToolError(f"插件「{plugin_id}」的题库文件超过 {MAX_SEED_BYTES // 1024} KB 上限")
    return path


def _load_seed(plugin_id: str) -> list[dict[str, Any]] | None:
    path = _seed_path(plugin_id)
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PluginToolError(f"读取插件题库失败：{exc}") from exc
    if not isinstance(payload, list):
        raise PluginToolError("插件题库必须是 JSON 数组")
    return [item for item in payload if isinstance(item, dict)][:MAX_SEED_QUESTIONS]


def _answer_text(answer: Any) -> str:
    if answer is None:
        return ""
    if isinstance(answer, str):
        return answer.strip()
    if isinstance(answer, dict):
        for key in ("final", "content", "text"):
            value = answer.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        keys = answer.get("choice_keys")
        if isinstance(keys, list) and keys:
            return "、".join(str(item) for item in keys)
        return json.dumps(answer, ensure_ascii=False, separators=(",", ":"))
    return str(answer)


def _normalize_question(raw: dict[str, Any], question_no: int | None = None) -> dict[str, Any]:
    options: list[dict[str, str]] = []
    for option in raw.get("options") or []:
        if isinstance(option, dict) and option.get("key") is not None:
            options.append(
                {
                    "key": str(option.get("key")),
                    "content": str(option.get("content") or ""),
                }
            )
    tags = [str(item) for item in (raw.get("tags") or []) if isinstance(item, (str, int, float))]
    question_type = raw.get("type") if raw.get("type") in TYPE_LABELS else "unknown"
    difficulty = normalize_difficulty(raw.get("difficulty"))
    if difficulty not in DIFFICULTY_LABELS:
        difficulty = "L1"
    return {
        "question_no": question_no,
        "id": str(raw.get("id") or ""),
        "type": question_type,
        "type_label": TYPE_LABELS[question_type],
        "difficulty": difficulty,
        "difficulty_label": DIFFICULTY_LABELS[difficulty],
        "stem": str(raw.get("stem") or "").strip(),
        "options": options,
        "answer": _answer_text(raw.get("answer")),
        "solution": str(raw.get("solution") or "").strip(),
        "tags": tags,
    }


def _format_question(question: dict[str, Any]) -> str:
    head = f"【{question['type_label']} · {question['difficulty_label']}】{question['stem']}"
    lines = [head]
    if question["options"]:
        lines.append(
            "选项：" + " / ".join(f"{item['key']}. {item['content']}" for item in question["options"])
        )
    if question["answer"]:
        lines.append("答案：" + question["answer"])
    if question["solution"]:
        lines.append("解析：" + question["solution"])
    if question["tags"]:
        lines.append("标签：" + "、".join(question["tags"]))
    return "\n".join(lines)


def _format_list(questions: list[dict[str, Any]], total: int) -> str:
    lines = [f"共 {total} 题，先列出前 {len(questions)} 题："]
    for question in questions:
        number = question["question_no"] or "?"
        lines.append(
            f"{number}. 【{question['type_label']}·{question['difficulty_label']}】{question['stem']}"
        )
    return "\n".join(lines)


def _select_by_number(questions: list[dict[str, Any]], question_no: int) -> dict[str, Any]:
    if question_no < 1 or question_no > len(questions):
        raise PluginToolError(f"第 {question_no} 题不存在（该插件题库共 {len(questions)} 题）")
    return _normalize_question(questions[question_no - 1], question_no)


def _question_grade(raw: dict[str, Any]) -> str:
    """题目的年级标注可能在顶层、meta 或标签里；没有就返回空串。"""
    for key in ("grade", "school_grade"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    meta = raw.get("meta")
    if isinstance(meta, dict):
        value = meta.get("grade")
        if isinstance(value, str) and value.strip():
            return value.strip()
    for tag in raw.get("tags") or []:
        if isinstance(tag, str) and tag.strip() in ("高一", "高二", "高三"):
            return tag.strip()
    return ""


def _run_random(
    plugin: dict[str, Any], seed: list[dict[str, Any]], args: dict[str, Any]
) -> dict[str, Any]:
    """随机抽一题（右侧面板「随机出题」与「随机出一道中档题」共用）。"""
    difficulty = normalize_difficulty(args.get("difficulty"))
    grade = args.get("grade")
    pool = list(enumerate(seed))
    notes: list[str] = []

    if difficulty in DIFFICULTY_LABELS:
        # 插件种子库可能仍写着 1.0 口径的旧难度值，两侧都归一到 L 码再比
        filtered = [
            (index, item)
            for index, item in pool
            if normalize_difficulty(item.get("difficulty")) == difficulty
        ]
        if not filtered:
            raise PluginToolError(
                "题库里没有难度为「%s」的题目" % DIFFICULTY_LABELS[difficulty]
            )
        pool = filtered

    if grade in ("高一", "高二", "高三"):
        if any(_question_grade(item) for _, item in pool):
            filtered = [(index, item) for index, item in pool if _question_grade(item) == grade]
            if not filtered:
                raise PluginToolError("题库里没有年级为「%s」的题目" % grade)
            pool = filtered
        else:
            notes.append("题库未标注年级，本次未按年级过滤")

    index, raw = random.choice(pool)
    question = _normalize_question(raw, index + 1)
    summary = (
        "已调用插件「%s」随机抽取第 %d 题（共 %d 题）：\n"
        % (plugin["name"], index + 1, len(seed))
        + _format_question(question)
    )
    if notes:
        summary += "\n（" + "；".join(notes) + "）"
    return {
        "ok": True,
        "plugin": {"id": plugin["id"], "name": plugin["name"]},
        "action": ACTION_IMPORT,
        "summary": summary,
        "data": {"total": len(seed), "questions": [question], "random": True},
    }


def _run_import(plugin: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    seed = _load_seed(plugin["id"])
    if seed is None:
        raise PluginToolError(
            f"插件「{plugin['name']}」没有提供可供宿主读取的题库数据（seed/questions.json）"
        )
    if not seed:
        raise PluginToolError(f"插件「{plugin['name']}」的题库是空的")

    if args.get("random"):
        return _run_random(plugin, seed, args)

    question_no = args.get("question_no")
    if question_no is not None:
        question = _select_by_number(seed, question_no)
        summary = (
            f"已调用插件「{plugin['name']}」拆分第 {question_no} 题（共 {len(seed)} 题）：\n"
            + _format_question(question)
        )
        return {
            "ok": True,
            "plugin": {"id": plugin["id"], "name": plugin["name"]},
            "action": ACTION_IMPORT,
            "summary": summary,
            "data": {"total": len(seed), "questions": [question]},
        }

    limit = args.get("limit", 5)
    limit = max(1, min(int(limit), MAX_RESULT_QUESTIONS, len(seed)))
    questions = [_normalize_question(item, index + 1) for index, item in enumerate(seed[:limit])]
    summary = (
        f"已调用插件「{plugin['name']}」读取题库：" + _format_list(questions, len(seed))
    )
    return {
        "ok": True,
        "plugin": {"id": plugin["id"], "name": plugin["name"]},
        "action": ACTION_IMPORT,
        "summary": summary,
        "data": {"total": len(seed), "questions": questions},
    }


def _question_from_library(question_id: str) -> dict[str, Any]:
    document = question_store.get_question(question_id)
    return _normalize_question(document)


def _run_render(plugin: dict[str, Any], args: dict[str, Any]) -> dict[str, Any]:
    question_id = args.get("question_id")
    if question_id:
        if not isinstance(question_id, str) or _QUESTION_ID.fullmatch(question_id) is None:
            raise PluginToolError("question_id 必须是 q_ 开头的题目 id")
        try:
            question = _question_from_library(question_id)
        except question_store.QuestionNotFound as exc:
            raise PluginToolError(f"题库里没有题目 {question_id}") from exc
        summary = f"已调用插件「{plugin['name']}」渲染题卡：\n" + _format_question(question)
        return {
            "ok": True,
            "plugin": {"id": plugin["id"], "name": plugin["name"]},
            "action": ACTION_RENDER,
            "summary": summary,
            "data": {"questions": [question]},
        }

    seed = _load_seed(plugin["id"])
    if seed:
        number = args.get("question_no", 1)
        question = _select_by_number(seed, number)
        summary = (
            f"已调用插件「{plugin['name']}」渲染第 {number} 题题卡：\n"
            + _format_question(question)
        )
        return {
            "ok": True,
            "plugin": {"id": plugin["id"], "name": plugin["name"]},
            "action": ACTION_RENDER,
            "summary": summary,
            "data": {"questions": [question]},
        }

    items, total = question_store.list_questions(page=1, page_size=1)
    if not items:
        raise PluginToolError(
            f"插件「{plugin['name']}」没有自带题库，当前工作区题库也是空的，暂无题可渲染"
        )
    question = _normalize_question(items[0], 1)
    summary = f"已调用插件「{plugin['name']}」渲染题卡：\n" + _format_question(question)
    return {
        "ok": True,
        "plugin": {"id": plugin["id"], "name": plugin["name"]},
        "action": ACTION_RENDER,
        "summary": summary,
        "data": {"total": total, "questions": [question]},
    }


def execute_tool(tool_name: str, arguments: Any) -> dict[str, Any]:
    """执行一次工具调用。参数不可信，失败也返回可读结果而不是抛到路由层。"""
    try:
        plugin = _find_plugin(tool_name)
        actions = _actions_for(plugin)
        if isinstance(arguments, str):
            try:
                args = json.loads(arguments or "{}")
            except json.JSONDecodeError as exc:
                raise PluginToolError(f"工具参数不是合法 JSON：{exc}") from exc
        else:
            args = arguments
        if not isinstance(args, dict):
            raise PluginToolError("工具参数必须是 JSON 对象")
        action = args.get("action")
        if action not in actions:
            raise PluginToolError(
                f"插件「{plugin['name']}」不支持动作 {action!r}，可用：{', '.join(actions)}"
            )
        if action == ACTION_IMPORT:
            return _run_import(plugin, args)
        return _run_render(plugin, args)
    except (PluginToolError, ValueError, TypeError) as exc:
        return {
            "ok": False,
            "error": str(exc),
            "summary": f"插件调用失败：{exc}",
        }


# --- 宿主意图兜底：模型没发 tool_calls 时，按明确句式路由到插件 ---
_QUESTION_NO_RE = re.compile(r"第\s*([0-9]{1,3}|[零一二两三四五六七八九十]{1,3})\s*题")


def _cn_to_int(text: str) -> int | None:
    if text.isdigit():
        return int(text)
    if text == "十":
        return 10
    if "十" in text:
        left, _, right = text.partition("十")
        tens = _CN_DIGITS.get(left, 1) if left else 1
        ones = _CN_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    return _CN_DIGITS.get(text)


def parse_question_no(text: str) -> int | None:
    match = _QUESTION_NO_RE.search(text or "")
    if not match:
        return None
    value = _cn_to_int(match.group(1))
    if value is None or value < 1 or value > MAX_SEED_QUESTIONS:
        return None
    return value


_RENDER_HINTS = ("渲染", "预览", "题卡", "看看", "显示", "展示")
_SPLIT_HINTS = ("拆", "导入", "取回")
_LIST_HINTS = ("题库", "有哪些题", "题目列表", "示例题")
_RANDOM_HINTS = ("随机", "随便", "抽一", "抽个")
_DIFFICULTY_HINTS = (
    ("压轴", "L4"),
    ("新定义", "L4"),
    ("基础", "L1"),
    ("简单", "L1"),
    ("中档", "L2"),
    ("中等", "L2"),
    ("困难", "L3"),
    ("较难", "L3"),
)
_GRADE_RE = re.compile(r"(高一|高二|高三)")


def _extract_difficulty(text: str) -> str | None:
    for word, value in _DIFFICULTY_HINTS:
        if word in text:
            return value
    return None


def _extract_grade(text: str) -> str | None:
    match = _GRADE_RE.search(text or "")
    return match.group(1) if match else None


def match_intent(user_input: str, tools: list[dict[str, Any]]) -> dict[str, Any] | None:
    """把明确句式路由到某个插件工具；return ``{tool, arguments}`` 或 None。

    只认高置信句式，避免「拆分一份试卷」这类没有题号、也可能指上传原卷的
    指令被误判成读取示例题库。模型正常发出 tool_calls 时不会走到这里。
    """
    text = str(user_input or "").strip()
    if not text or not tools:
        return None

    question_no = parse_question_no(text)
    wants_render = any(word in text for word in _RENDER_HINTS)
    wants_list = any(word in text for word in _LIST_HINTS)
    wants_split = any(word in text for word in _SPLIT_HINTS)
    wants_random = any(word in text for word in _RANDOM_HINTS)
    if question_no is None and not wants_list and not wants_random:
        return None
    if question_no is not None and not (wants_split or wants_render or wants_random):
        return None

    action = ACTION_IMPORT if wants_random else (ACTION_RENDER if wants_render else ACTION_IMPORT)
    best: tuple[int, dict[str, Any]] | None = None
    for tool in tools:
        function = tool.get("function") if isinstance(tool, dict) else None
        if not isinstance(function, dict):
            continue
        name = function.get("name") or ""
        properties = (function.get("parameters") or {}).get("properties") or {}
        action_spec = properties.get("action") or {}
        actions = action_spec.get("enum") or []
        if action not in actions:
            continue
        try:
            plugin = _find_plugin(name)
        except PluginToolError:
            continue
        score = 0
        if ACTION_IMPORT in actions:
            score += 2
        try:
            if _seed_path(plugin["id"]) is not None:
                score += 3
        except PluginToolError:
            score -= 1
        if best is None or score > best[0]:
            best = (score, tool)

    if best is None:
        return None
    chosen = best[1]["function"]
    arguments: dict[str, Any] = {"action": action}
    if question_no is not None:
        arguments["question_no"] = question_no
    if wants_random:
        arguments["random"] = True
        difficulty = _extract_difficulty(text)
        if difficulty:
            arguments["difficulty"] = difficulty
        grade = _extract_grade(text)
        if grade:
            arguments["grade"] = grade
    return {"tool": chosen["name"], "arguments": arguments}
