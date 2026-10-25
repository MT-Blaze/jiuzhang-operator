"""AI 命令面：把 ``command.list`` / ``command.execute`` 接进工具链（军令 #20 第三部分）。

三条硬边界：

1. **字典只认清单**：``command_list`` 读的是 ``discover_plugins()`` 已经归一好的
   能力字典；AI 看到的命令、参数声明与风险等级都和设置页逐字同源。
2. **上下文反绑架**：``command_execute`` 只收 ``params_schema`` 声明过的字段，
   封口后再拦一层底层键（SQL / 表名 / 行号 / 路径 / 令牌）。题目、考向、教材的
   id 必须是 ``q_`` / ``tp_`` / ``tb_`` 公开 id——AI 不得把数据库行号当身份透传。
3. **高副作用先确认**：清单标了 ``requires_user`` 的命令一律不执行，先发一次性
   确认令牌与确认卡；用户点「确认执行」才真正转发，点「取消」或令牌过期即作废。
   无界面引擎的数据命令由底座直接执行；有界面的插件命令回一条 ``command_request``，
   由对话插件经宿主 ``command.execute`` 转发（宿主自己的 requires_user 闸仍然生效）。

本模块只做校验、编排与确认令牌；不写数据库、不执行插件 JS、不碰宿主 DOM。
"""

from __future__ import annotations

import json
import math
import re
import secrets
import sqlite3
import threading
import time
from typing import Any

from app.core import bank as bank_store
from app.core import bank_provider
from app.core.plugins import discover_plugins

COMMAND_LIST_TOOL = "command_list"
COMMAND_EXECUTE_TOOL = "command_execute"

MAX_COMMAND_ID = 96
MAX_CONTEXT_CHARS = 16384          # 与宿主 stage.js 的 COMMAND_CONTEXT_MAX 同口径
MAX_LISTED_COMMANDS = 32
MAX_QUERY_TEXT = 100
MAX_PREVIEW_ITEMS = 20
CONFIRM_TTL_SECONDS = 300
MAX_PENDING = 64

_CATEGORY_LABELS = {
    "input": "输入",
    "process": "处理",
    "output": "输出",
    "data": "数据",
    "view": "视图",
}

# 这些键一旦出现在上下文里就直接拒收：AI 只该交业务字段，不该把底座怎么存数据的
# 细节（SQL、表名、行号、文件路径、令牌）带进插件。
_FORBIDDEN_KEYS = {
    "sql", "sqlite", "sql_query", "query_sql", "raw_sql", "statement",
    "table", "table_name", "tables", "column", "columns",
    "rowid", "row_id", "rowids",
    "database", "database_path", "db", "db_path",
    "path", "file", "file_path", "filename", "dir", "directory",
    "token", "secret", "password", "api_key", "apikey", "access_token",
    "dsn", "connection", "connection_string",
    "workspace_id", "bank_path", "plugin_dir",
}
# 公开 id 白名单：题目 / 考向 / 教材。行号（纯数字）与其它内部主键一律不算身份。
_PUBLIC_ID_RE = re.compile(r"^(?:q_|tp_|tb_)[A-Za-z0-9_-]{1,80}$")
_CONFIRM_RE = re.compile(
    r"^\s*确认执行命令\s*[（(]\s*确认码\s*([A-Za-z0-9_-]{8,64})\s*[)）]\s*$"
)
_CANCEL_RE = re.compile(
    r"^\s*取消执行命令\s*[（(]\s*确认码\s*([A-Za-z0-9_-]{8,64})\s*[)）]\s*$"
)
_LIST_HINTS = ("命令清单", "能力字典", "有哪些命令", "能调用哪些命令", "列出命令", "命令列表")

_pending: dict[str, dict[str, Any]] = {}
_pending_lock = threading.Lock()


class CommandToolError(Exception):
    """命令名、上下文或确认令牌不可用。"""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _coerce_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments or "{}")
        except json.JSONDecodeError as exc:
            raise CommandToolError("BAD_ARGUMENTS", f"工具参数不是合法 JSON：{exc}") from exc
    else:
        parsed = arguments
    if not isinstance(parsed, dict):
        raise CommandToolError("BAD_ARGUMENTS", "工具参数必须是 JSON 对象")
    return parsed


def _plugin_index() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    discovered = discover_plugins()
    plugins = {
        str(item.get("id") or ""): item
        for item in discovered.get("plugins") or []
        if isinstance(item, dict)
    }
    entries: dict[str, dict[str, Any]] = {}
    for raw in discovered.get("commands") or []:
        if not isinstance(raw, dict):
            continue
        command_id = str(raw.get("id") or "")
        plugin_id = str(raw.get("plugin_id") or "")
        if not command_id or not plugin_id:
            continue
        plugin = plugins.get(plugin_id) or {}
        entry = dict(raw)
        entry["plugin_id"] = plugin_id
        entry["plugin_name"] = str(raw.get("plugin_name") or plugin.get("name") or plugin_id)
        entry["headless"] = plugin.get("headless") is True
        entry["category"] = _category_of(command_id)
        entries[command_id] = entry
    return entries, plugins


def _category_of(command_id: str) -> str:
    parts = command_id.split(".")
    if len(parts) >= 4 and parts[:3] == ["org", "jiuzhang", "action"]:
        return parts[3]
    return ""


def _risk_for(entry: dict[str, Any]) -> dict[str, str]:
    """风险等级只从清单声明推导：requires_user 即高，其余按官方分类保守估计。"""
    if entry.get("requires_user") is True:
        return {"level": "high", "label": "高", "reason": "会改动数据或外部状态"}
    category = entry.get("category") or ""
    if category in ("data", "view"):
        return {"level": "low", "label": "低", "reason": "只读查询或只改变当前视图"}
    if category == "input":
        return {"level": "medium", "label": "中", "reason": "会改变界面上的编辑状态"}
    if category == "process":
        return {"level": "medium", "label": "中", "reason": "会在插件内生成或改写内容"}
    if category == "output":
        return {"level": "high", "label": "高", "reason": "会产出文件或触发外部动作"}
    return {"level": "medium", "label": "中", "reason": "第三方命令，按中风险保守处理"}


def _id_like(key: str) -> bool:
    low = str(key or "").lower()
    return low == "id" or low == "ids" or low.endswith("_id") or low.endswith("_ids")


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _value_problem(schema: dict[str, Any], value: Any, path: str) -> str:
    key = path.rsplit(".", 1)[-1]
    if _id_like(key) and value not in (None, "", []):
        if isinstance(value, list):
            for position, item in enumerate(value):
                if not isinstance(item, str) or _PUBLIC_ID_RE.fullmatch(item) is None:
                    return f"{path}[{position}] 必须是 q_/tp_/tb_ 公开 id，不得透传底层行号"
        elif not isinstance(value, str) or _PUBLIC_ID_RE.fullmatch(value) is None:
            return f"{path} 必须是 q_/tp_/tb_ 公开 id，不得透传底层行号或整数行号"

    expected = schema.get("type")
    actual = _json_type(value)
    if expected == "integer":
        if actual != "integer":
            return f"{path} 必须是整数（收到 {actual}）"
    elif expected == "number":
        if actual not in ("integer", "number"):
            return f"{path} 必须是数字（收到 {actual}）"
        if not math.isfinite(float(value)):
            return f"{path} 必须是有限数字"
    elif expected == "boolean":
        if actual != "boolean":
            return f"{path} 必须是布尔值（收到 {actual}）"
    elif expected == "string":
        if actual != "string":
            return f"{path} 必须是字符串（收到 {actual}）"
        if any(ord(ch) < 32 and ch not in "\n\r\t" for ch in value):
            return f"{path} 含控制字符"
        if len(value) < int(schema.get("minLength") or 0):
            return f"{path} 少于 {schema['minLength']} 个字符"
        if "maxLength" in schema and len(value) > int(schema["maxLength"]):
            return f"{path} 超过 {schema['maxLength']} 个字符"
    elif expected == "array":
        if actual != "array":
            return f"{path} 必须是数组（收到 {actual}）"
        if len(value) < int(schema.get("minItems") or 0):
            return f"{path} 少于 {schema['minItems']} 项"
        if "maxItems" in schema and len(value) > int(schema["maxItems"]):
            return f"{path} 超过 {schema['maxItems']} 项"
        items = schema.get("items")
        if isinstance(items, dict):
            for position, item in enumerate(value):
                problem = _value_problem(items, item, f"{path}[{position}]")
                if problem:
                    return problem
    elif expected == "object":
        return _object_problem(schema, value, path)

    if "enum" in schema and value not in schema["enum"]:
        return f"{path} 只能是：{' / '.join(str(item) for item in schema['enum'])}"
    if expected in ("integer", "number"):
        if "minimum" in schema and value < schema["minimum"]:
            return f"{path} 不得小于 {schema['minimum']}"
        if "maximum" in schema and value > schema["maximum"]:
            return f"{path} 不得大于 {schema['maximum']}"
    return ""


def _object_problem(schema: dict[str, Any], value: Any, path: str) -> str:
    if not isinstance(value, dict):
        return f"{path or 'context'} 必须是 JSON 对象"
    for key in value:
        if str(key).lower() in _FORBIDDEN_KEYS:
            return (
                f"{path or 'context'} 含底层保留键 {key!r}：只允许标准业务字段，"
                "禁止 SQL、表名、行号、文件路径与令牌"
            )
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        properties = {}
    if schema.get("additionalProperties") is False:
        unknown = sorted(str(key) for key in value if key not in properties)
        if unknown:
            return f"{path or 'context'} 含未声明参数：{'、'.join(unknown)}"
    for name in schema.get("required") or []:
        if name not in value:
            return f"{path or 'context'} 缺少必填参数 {name}"
    for name, child in properties.items():
        if name in value and isinstance(child, dict):
            prefix = f"{path}." if path else ""
            problem = _value_problem(child, value[name], prefix + str(name))
            if problem:
                return problem
    return ""


def normalize_context(schema: Any, context: Any) -> tuple[dict[str, Any], str]:
    """按命令声明的 ``params_schema`` 校验上下文；返回 ``(归一副本, 问题)``。

    缺省 ``context`` 归一成空对象；非对象、未声明键、底层保留键、越界值、
    非公开 id 一律返回问题串，由调用方转成可读错误——不静默丢字段。
    """
    if not isinstance(schema, dict):
        return {}, "命令缺少可用的参数声明"
    if context is None:
        context = {}
    if not isinstance(context, dict):
        return {}, "context 必须是 JSON 对象"
    problem = _object_problem(schema, context, "")
    if problem:
        return {}, problem
    try:
        encoded = json.dumps(context, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        return {}, f"context 不是可序列化的 JSON：{exc}"
    if len(encoded) > MAX_CONTEXT_CHARS:
        return {}, f"context 超过 {MAX_CONTEXT_CHARS} 字符上限"
    return json.loads(encoded), ""


def _data_volume(context: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in context.items():
        low = key.lower()
        if low in ("copy_ids", "question_ids", "ids") and isinstance(value, list):
            parts.append(f"{len(value)} 条 {key}")
        elif low == "markdown" and isinstance(value, str):
            parts.append(f"Markdown {len(value)} 字符")
        elif low == "limit":
            parts.append(f"最多 {value} 条")
        elif low in ("query", "search") and isinstance(value, str) and value:
            parts.append(f"关键词「{value[:24]}」")
        elif _id_like(low) and isinstance(value, str) and value:
            parts.append(f"1 条 {key}={value}")
    if not parts:
        return "无附加数据（0 条记录）" if not context else f"{len(context)} 个参数"
    return "；".join(parts)[:160]


def _prune_pending(now: float) -> None:
    expired = [
        token for token, record in _pending.items()
        if now - float(record.get("created") or 0) > CONFIRM_TTL_SECONDS
    ]
    for token in expired:
        _pending.pop(token, None)
    while len(_pending) > MAX_PENDING:
        oldest = min(_pending, key=lambda item: float(_pending[item].get("created") or 0))
        _pending.pop(oldest, None)


def _remember(entry: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    token = secrets.token_hex(8)
    record = {
        "token": token,
        "command_id": entry["id"],
        "title": entry.get("title") or entry["id"],
        "plugin_id": entry["plugin_id"],
        "plugin_name": entry["plugin_name"],
        "context": context,
        "created": time.time(),
    }
    with _pending_lock:
        _prune_pending(time.time())
        _pending[token] = record
    return record


def _take(token: str) -> dict[str, Any] | None:
    with _pending_lock:
        _prune_pending(time.time())
        return _pending.pop(token, None)


def _confirm_card(
    entry: dict[str, Any], context: dict[str, Any], token: str, risk: dict[str, str]
) -> dict[str, Any]:
    description = entry.get("description") or entry.get("title") or ""
    return {
        "version": "1.0",
        "type": "confirm_card",
        "title": f"确认执行「{_text(entry.get('title'), 40)}」",
        "description": (
            f"调用插件：{_text(entry.get('plugin_name'), 32)}（{entry['plugin_id']}）\n"
            f"功能：{_text(description, 120)}\n"
            f"涉及数据：{_data_volume(context)}\n"
            f"风险等级：{risk['label']}（{risk['reason']}）"
        ),
        "actions": [
            {
                "label": "确认执行",
                "command": f"确认执行命令（确认码 {token}）",
                "silent": True,
            },
            {
                "label": "取消",
                "command": f"取消执行命令（确认码 {token}）",
                "silent": True,
            },
        ],
    }


def build_tools() -> list[dict[str, Any]]:
    """返回 AI 侧的两件命令工具；字典内容在调用时按当前清单现查。"""
    return [
        {
            "type": "function",
            "function": {
                "name": COMMAND_LIST_TOOL,
                "description": (
                    "列出当前启用插件声明的命令（能力路由字典）。用户问「有哪些命令」"
                    "「某个插件能做什么」时调用。返回每条命令的 id、标题、提供方、说明、"
                    "参数声明、返回值与风险等级；只能按返回内容回答，不得编造命令。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plugin_id": {
                            "type": "string",
                            "maxLength": 96,
                            "description": "只看某个插件的命令，例如 org.jiuzhang.bank-engine；留空列全部。",
                        },
                        "requires_user": {
                            "type": "boolean",
                            "description": "true 只看需要确认的高副作用命令；false 只看直接执行的命令。",
                        },
                        "category": {
                            "type": "string",
                            "enum": list(_CATEGORY_LABELS.keys()),
                            "description": "按官方分类筛选：input/process/output/data/view。",
                        },
                    },
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": COMMAND_EXECUTE_TOOL,
                "description": (
                    "执行能力字典里的一条命令。context 必须严格符合该命令的 params_schema，"
                    "题目/考向/教材只传 q_/tp_/tb_ 公开 id，禁止 SQL、表名、数据库行号、文件路径或令牌。"
                    "高副作用命令不会直接执行：底座会返回确认卡，必须由用户点「确认执行」才生效。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command_id": {
                            "type": "string",
                            "maxLength": MAX_COMMAND_ID,
                            "description": "命令 id，例如 org.jiuzhang.action.data.bank_search。",
                        },
                        "context": {
                            "type": "object",
                            "description": "命令参数对象，键名与 params_schema 一致；没有参数就传空对象。",
                            "additionalProperties": True,
                        },
                    },
                    "required": ["command_id"],
                    "additionalProperties": False,
                },
            },
        },
    ]


def _base(action: str) -> dict[str, Any]:
    return {"ok": True, "host_tool": True, "action": action}


def list_commands(arguments: Any) -> dict[str, Any]:
    """``command_list``：按清单返回字典，支持按插件、风险与分类过滤。"""
    try:
        args = _coerce_arguments(arguments)
        plugin_id = _text(args.get("plugin_id"), 96)
        category = args.get("category")
        if category is not None and category not in _CATEGORY_LABELS:
            raise CommandToolError("BAD_ARGUMENTS", "category 只能是 input/process/output/data/view")
        requires_user = args.get("requires_user")
        if requires_user is not None and not isinstance(requires_user, bool):
            raise CommandToolError("BAD_ARGUMENTS", "requires_user 必须是布尔值")
        entries, plugins = _plugin_index()
        commands: list[dict[str, Any]] = []
        for command_id in sorted(entries):
            entry = entries[command_id]
            if plugin_id and entry["plugin_id"] != plugin_id:
                continue
            if category and entry.get("category") != category:
                continue
            if requires_user is not None and bool(entry.get("requires_user")) != requires_user:
                continue
            commands.append({
                "id": command_id,
                "title": entry.get("title") or command_id,
                "plugin_id": entry["plugin_id"],
                "plugin_name": entry["plugin_name"],
                "headless": bool(entry.get("headless")),
                "requires_user": bool(entry.get("requires_user")),
                "description": entry.get("description") or "",
                "params_schema": entry.get("params_schema") or {},
                "returns": entry.get("returns") or "",
                "risk": _risk_for(entry),
            })
        commands = commands[:MAX_LISTED_COMMANDS]
        if plugin_id and plugin_id not in plugins:
            raise CommandToolError("COMMAND_NOT_FOUND", f"没有安装插件「{plugin_id}」")
        if commands:
            lines = [f"当前启用插件共 {len(commands)} 条命令："]
            for item in commands[:12]:
                flag = "需确认" if item["requires_user"] else "直接执行"
                lines.append(
                    f"- {item['id']}（{item['plugin_name']}）：{item['description'] or item['title']}"
                    f"；风险{item['risk']['label']}，{flag}"
                )
            if len(commands) > 12:
                lines.append(f"……其余 {len(commands) - 12} 条见结构化结果。")
            summary = "\n".join(lines)
        else:
            summary = "当前没有符合筛选条件的命令。"
        return {
            **_base("command.list"),
            "summary": summary,
            "data": {"total": len(commands), "commands": commands},
        }
    except CommandToolError as exc:
        return {
            **_base("command.list"),
            "ok": False,
            "error": exc.message,
            "error_code": exc.code,
            "summary": f"读取命令字典失败：{exc.message}",
        }


def _headless_data(entry: dict[str, Any], context: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """无界面引擎的数据命令在底座侧直接执行；出参按 §2.15 的命令契约裁剪。"""
    if entry["plugin_id"] != bank_provider.DEFAULT_PROVIDER_ID:
        raise CommandToolError(
            "COMMAND_UNSUPPORTED",
            f"无界面插件的「{entry['id']}」目前没有底座内置执行器",
        )
    provider = bank_provider.resolve()
    plugin_id = str(provider.get("plugin_id") or entry["plugin_id"])
    plugin_name = str(provider.get("name") or entry["plugin_name"])
    command = entry["id"].rsplit(".", 1)[-1]
    try:
        if command == "bank_stats":
            stats = bank_store.stats(plugin_id)
            summary = (
                f"题库「{plugin_name}」共 {int(stats.get('total') or 0)} 题。"
                f"年级：{_join_counts(stats.get('grades'))}；"
                f"难度：{_join_counts(stats.get('difficulties'))}。"
            )
            return stats, summary[:500]
        if command == "bank_search":
            limit = max(1, min(int(context.get("limit") or 5), MAX_PREVIEW_ITEMS))
            items, total = bank_store.list_questions(
                plugin_id,
                grade=str(context.get("grade") or ""),
                difficulty=str(context.get("difficulty") or ""),
                question_type=str(context.get("type") or ""),
                search=str(context.get("query") or ""),
                page=1,
                page_size=limit,
            )
            preview = [
                {
                    "id": str(item.get("id") or ""),
                    "type": str(item.get("type") or ""),
                    "difficulty": str(item.get("difficulty") or ""),
                    "stem": str(item.get("stem") or "").strip()[:120],
                }
                for item in items
            ]
            lines = [f"题库「{plugin_name}」共 {total} 道匹配。"]
            for position, item in enumerate(preview[:3], start=1):
                lines.append(f"{position}. [{item['type']}·{item['difficulty']}] {item['stem']}")
            return {"total": total, "items": preview}, "\n".join(lines)[:800]
        if command == "bank_topics":
            nodes = bank_store.topics(
                plugin_id,
                parent_id=str(context.get("parent_id") or ""),
                search=str(context.get("search") or ""),
                textbook_id=str(context.get("textbook_id") or ""),
            )
            items = [
                {
                    "id": str(node.get("id") or ""),
                    "parent_id": str(node.get("parent_id") or ""),
                    "name": str(node.get("name") or ""),
                    "layer": str(node.get("layer") or ""),
                    "has_children": bool(node.get("has_children")),
                    "question_count": int(node.get("question_count") or 0),
                    "note_count": int(node.get("note_count") or 0),
                }
                for node in nodes[:MAX_PREVIEW_ITEMS]
            ]
            names = "、".join(item["name"] for item in items[:5] if item["name"])
            summary = f"题库「{plugin_name}」返回 {len(items)} 个大纲节点"
            summary += f"：{names}。" if names else "。"
            return {"items": items}, summary[:500]
    except (bank_store.BankError, sqlite3.Error, OSError, ValueError) as exc:
        raise CommandToolError("COMMAND_FAILED", f"读取题库失败：{exc}") from exc
    raise CommandToolError(
        "COMMAND_UNSUPPORTED", f"没有为无界面命令「{entry['id']}」实现底座执行器"
    )


def _join_counts(groups: Any) -> str:
    if not isinstance(groups, list):
        return "无"
    parts = [
        f"{item.get('name')} {int(item.get('count') or 0)}"
        for item in groups[:5]
        if isinstance(item, dict) and item.get("name")
    ]
    return "、".join(parts) or "无"


def _dispatch(entry: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """按插件形态分流：无界面引擎就地执行，有界面插件交回宿主转发。"""
    risk = _risk_for(entry)
    base = {
        **_base("command.execute"),
        "command_id": entry["id"],
        "title": entry.get("title") or entry["id"],
        "plugin": {"id": entry["plugin_id"], "name": entry["plugin_name"]},
        "risk": risk,
        "context": context,
    }
    if entry.get("headless"):
        data, detail = _headless_data(entry, context)
        return {
            **base,
            "executed": True,
            "pending": False,
            "summary": f"已由底座直接执行「{base['title']}」。{detail}",
            "data": data,
        }
    return {
        **base,
        "executed": False,
        "pending": True,
        "command_request": {
            "command_id": entry["id"],
            "title": base["title"],
            "plugin_id": entry["plugin_id"],
            "plugin_name": entry["plugin_name"],
            "context": context,
            "risk": risk,
        },
        "summary": (
            f"已把「{base['title']}」交给宿主转发给「{entry['plugin_name']}」，"
            "结果由目标插件返回。"
        ),
    }


def _execute_now(entry: dict[str, Any], context: dict[str, Any], *, confirmed: bool) -> dict[str, Any]:
    result = _dispatch(entry, context)
    if confirmed:
        result["confirmed"] = True
        result["summary"] = "确认已核销。" + str(result.get("summary") or "")
    return result


def _confirm(token: str) -> dict[str, Any]:
    record = _take(token)
    if record is None:
        raise CommandToolError(
            "COMMAND_CONFIRM_EXPIRED",
            "确认码已失效、已被使用或已被取消；命令没有执行，请重新发起。",
        )
    entries, _ = _plugin_index()
    entry = entries.get(str(record.get("command_id") or ""))
    if entry is None:
        raise CommandToolError(
            "COMMAND_NOT_FOUND",
            "命令已从能力字典退场（插件被停用、卸载或改写了声明），本次不执行。",
        )
    context, problem = normalize_context(entry.get("params_schema"), record.get("context"))
    if problem:
        raise CommandToolError("CONTEXT_INVALID", f"上下文未通过校验：{problem}")
    return _execute_now(entry, context, confirmed=True)


def _cancel(token: str) -> dict[str, Any]:
    record = _take(token)
    if record is None:
        return {
            **_base("command.execute"),
            "executed": False,
            "cancelled": False,
            "summary": "没有找到待确认的命令（可能已执行或已过期），本次未执行任何操作。",
        }
    return {
        **_base("command.execute"),
        "executed": False,
        "cancelled": True,
        "command_id": str(record.get("command_id") or ""),
        "title": str(record.get("title") or ""),
        "summary": f"已取消「{record.get('title') or record.get('command_id')}」，命令没有发送给插件。",
    }


def execute_command(arguments: Any) -> dict[str, Any]:
    """``command_execute``：校验 → 高副作用发卡 / 低风险执行 → 返回可读结果。

    参数不可信，任何失败都回可读结果而不抛到路由层；失败一定 ``executed=false``。
    """
    try:
        args = _coerce_arguments(arguments)
        confirm_token = args.get("confirm_token")
        cancel_token = args.get("cancel_token")
        if confirm_token is not None:
            if not isinstance(confirm_token, str):
                raise CommandToolError("BAD_ARGUMENTS", "confirm_token 必须是字符串")
            return _confirm(confirm_token.strip())
        if cancel_token is not None:
            if not isinstance(cancel_token, str):
                raise CommandToolError("BAD_ARGUMENTS", "cancel_token 必须是字符串")
            return _cancel(cancel_token.strip())

        command_id = _text(args.get("command_id"), MAX_COMMAND_ID)
        if not command_id:
            raise CommandToolError("BAD_ARGUMENTS", "缺少 command_id")
        entries, _ = _plugin_index()
        entry = entries.get(command_id)
        if entry is None:
            raise CommandToolError(
                "COMMAND_NOT_FOUND",
                f"能力字典里没有「{command_id}」：目标插件未安装、已停用或没有声明它",
            )
        context, problem = normalize_context(entry.get("params_schema"), args.get("context"))
        if problem:
            raise CommandToolError("CONTEXT_INVALID", f"上下文未通过校验：{problem}")

        risk = _risk_for(entry)
        if entry.get("requires_user") is True:
            record = _remember(entry, context)
            card = _confirm_card(entry, context, record["token"], risk)
            return {
                **_base("command.execute"),
                "command_id": command_id,
                "title": entry.get("title") or command_id,
                "plugin": {"id": entry["plugin_id"], "name": entry["plugin_name"]},
                "risk": risk,
                "context": context,
                "executed": False,
                "pending": True,
                "confirmation": {
                    "token": record["token"],
                    "expires_in": CONFIRM_TTL_SECONDS,
                    "data_volume": _data_volume(context),
                },
                "ui_cards": [card],
                "summary": (
                    f"「{entry.get('title') or command_id}」属于高副作用命令（风险：{risk['label']}），"
                    "本次没有执行。请先核对确认卡上的调用插件、功能、涉及数据量与风险等级，"
                    "再点「确认执行」；点「取消」不会发送给插件。"
                ),
            }
        return _execute_now(entry, context, confirmed=False)
    except CommandToolError as exc:
        return {
            **_base("command.execute"),
            "ok": False,
            "executed": False,
            "error": exc.message,
            "error_code": exc.code,
            "summary": f"命令未执行：{exc.message}",
        }


def match_intent(user_input: str) -> dict[str, Any] | None:
    """宿主兜底：确认码与命令清单这类确定性句式不经模型，直接路由到命令工具。"""
    text = str(user_input or "").strip()
    if not text:
        return None
    match = _CONFIRM_RE.match(text)
    if match:
        return {"tool": COMMAND_EXECUTE_TOOL, "arguments": {"confirm_token": match.group(1)}}
    match = _CANCEL_RE.match(text)
    if match:
        return {"tool": COMMAND_EXECUTE_TOOL, "arguments": {"cancel_token": match.group(1)}}
    if len(text) <= 40 and any(word in text for word in _LIST_HINTS):
        return {"tool": COMMAND_LIST_TOOL, "arguments": {}}
    return None
