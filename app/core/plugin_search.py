"""半自主插件扩展：在**用户已拉取的索引缓存**里搜索插件，并生成安装建议卡。

红线（AGENTS 铁律二 / PLUGIN_SPEC §1.3）：
- 本模块**不发起任何网络请求**。搜索只读用户此前在「设置与控制」页点【拉取清单】
  得到的缓存；没有缓存就如实让用户先去拉取，绝不偷偷替用户联网。
- 搜到插件后只生成 ``install_card``，**不安装、不下载**。只有用户点击卡片上的
  【确认安装】，前端才带写令牌调用 ``POST /api/plugins/install-url``。
- 索引条目里的名称、描述、zip 地址均为不可信数据：展示走 textContent，
  地址只在下一次用户确认安装时交给后端地址守卫重新校验。
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core import plugin_index, ui_cards
from app.core.config import root_data_dir
from app.core.plugins import discover_plugins

TOOL_SEARCH = "search_available_plugins"
TOOL_SUGGEST = "suggest_install"
TOOL_NAMES = {TOOL_SEARCH, TOOL_SUGGEST}
HOST_PLUGIN = {"id": "builtin.plugin-index", "name": "插件索引"}

CACHE_FILENAME = "plugin_index_cache.json"
MAX_QUERY = 200
MAX_RESULTS = 5
MAX_REASON = 200
MAX_ID = 100

_STOPWORDS = (
    "我想",
    "帮我",
    "请",
    "一个",
    "一款",
    "能够",
    "可以",
    "支持",
    "插件",
    "找",
    "搜",
    "搜索",
    "推荐",
    "有没有",
    "能",
    "的",
    "吗",
    "呢",
    "吧",
    "啊",
    "我",
    "要",
    "想",
    "个",
    "给",
    "看看",
    "下",
)

# 关键词 → 索引 kind；命中 kind 记 4 分，足以单独触发建议卡。
_KIND_HINTS = (
    (("导出", "pdf", "docx", "word", "tex", "latex", "打印"), "exporter", "导出"),
    (("题卡", "渲染", "卡片", "预览"), "renderer", "题卡渲染"),
    (("导入", "拆题", "题库", "ocr", "识别"), "importer", "题库导入"),
    (("工具", "tool", "计算"), "tool", "工具"),
)

_SEARCH_HINTS = ("找", "搜", "推荐", "有没有", "想要", "安装", "装个")
_KIND_LABELS = {"renderer": "渲染", "importer": "导入", "exporter": "导出", "tool": "工具"}


def cache_path() -> Path:
    return root_data_dir() / CACHE_FILENAME


def save_index_cache(index: dict[str, Any]) -> None:
    """把一次成功拉取的索引落盘，供离线搜索；失败只影响搜索，不影响拉取结果。"""
    payload = {
        "saved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_url": index.get("source_url", ""),
        "source_host": index.get("source_host", ""),
        "index_name": index.get("index_name", ""),
        "updated_at": index.get("updated_at", ""),
        "entries": index.get("entries") or [],
        # host 块是同一份索引文档里的底座自更新声明（PLUGIN_SPEC §1.3）：
        # 一起缓存，用户点【检查更新】时才能在离线路径上比对底座版本。
        "host": index.get("host") if isinstance(index.get("host"), dict) else None,
    }
    path = cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
    except OSError:
        # 缓存是增强能力：磁盘只读或空间不足时，不让拉取清单本身失败。
        return


def load_index_cache() -> dict[str, Any] | None:
    path = cache_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return None
    try:
        parsed = plugin_index.parse_index(
            {
                "index_version": plugin_index.INDEX_VERSION,
                "name": payload.get("index_name", ""),
                "updated_at": payload.get("updated_at", ""),
                "entries": entries,
                "host": payload.get("host"),
            }
        )
    except (plugin_index.IndexRejected, ValueError):
        return None
    return {
        "entries": parsed["entries"],
        "host": parsed["host"],
        "host_rejected": parsed["host_rejected"],
        "source_host": str(payload.get("source_host") or ""),
        "source_url": str(payload.get("source_url") or ""),
        "saved_at": str(payload.get("saved_at") or ""),
        "index_name": parsed["index_name"],
        "updated_at": parsed["updated_at"],
    }


def _normalize_query(text: str) -> str:
    query = str(text or "").strip().lower()
    for word in sorted(_STOPWORDS, key=len, reverse=True):
        query = query.replace(word, " ")
    query = re.sub(r"[，。；;、/|]+", " ", query)
    return re.sub(r"\s+", " ", query).strip()[:MAX_QUERY]


def _score(entry: dict[str, Any], query: str) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    haystack = " ".join(
        str(entry.get(key) or "") for key in ("id", "name", "description", "kind")
    ).lower()
    compact = query.replace(" ", "")
    if compact and compact in haystack:
        score += 6
        reasons.append("名称或描述直接命中")
    else:
        for token in query.split(" "):
            if len(token) >= 2 and token in haystack:
                score += 3
                reasons.append("命中「%s」" % token)
    for keywords, kind, label in _KIND_HINTS:
        if entry.get("kind") == kind and any(word in query for word in keywords):
            score += 4
            reasons.append("属于「%s」类插件" % label)
    return score, reasons[:3]


def search_entries(query: str, limit: int = MAX_RESULTS) -> list[dict[str, Any]]:
    cache = load_index_cache()
    if cache is None:
        return []
    normalized = _normalize_query(query)
    ranked: list[tuple[int, dict[str, Any], list[str]]] = []
    for entry in cache["entries"]:
        if normalized:
            score, reasons = _score(entry, normalized)
            if score <= 0:
                continue
        else:
            score, reasons = 0, []
        ranked.append((score, entry, reasons))
    ranked.sort(key=lambda item: (-item[0], item[1].get("name") or ""))
    if not normalized:
        return [
            {"entry": entry, "score": score, "reasons": reasons}
            for score, entry, reasons in ranked[:limit]
        ]
    return [
        {"entry": entry, "score": score, "reasons": reasons}
        for score, entry, reasons in ranked[:limit]
    ]


def _public_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": entry.get("id", ""),
        "name": entry.get("name", ""),
        "version": entry.get("version", ""),
        "kind": entry.get("kind", ""),
        "kind_label": _KIND_LABELS.get(entry.get("kind", ""), "插件"),
        "description": entry.get("description", ""),
        "homepage": entry.get("homepage", ""),
    }


def _installed_ids() -> set[str]:
    try:
        return {item.get("id", "") for item in discover_plugins().get("plugins", [])}
    except Exception:
        return set()


def _cache_descriptor(cache: dict[str, Any]) -> str:
    host = cache.get("source_host") or "本机缓存"
    saved = cache.get("saved_at") or ""
    return host + (" · " + saved if saved else "")


def _search_outcome(query: str) -> dict[str, Any]:
    cache = load_index_cache()
    if cache is None:
        return {
            "ok": False,
            "host_tool": True,
            "plugin": HOST_PLUGIN,
            "action": TOOL_SEARCH,
            "error": "尚未拉取插件索引",
            "summary": (
                "还没拉取过插件索引，无法搜索。请到「设置与控制」页点【拉取清单】，"
                "成功后再让我找插件；底座不会替我偷偷联网。"
            ),
        }

    results = search_entries(query)
    if not results:
        return {
            "ok": True,
            "host_tool": True,
            "plugin": HOST_PLUGIN,
            "action": TOOL_SEARCH,
            "summary": (
                "当前索引（%s）里没有匹配「%s」的插件。换个关键词，"
                "或到设置页重新拉取最新清单后再试。"
                % (_cache_descriptor(cache), _normalize_query(query) or "插件")
            ),
            "data": {"entries": [], "cache": {"source_host": cache.get("source_host"), "saved_at": cache.get("saved_at")}},
        }

    installed = _installed_ids()
    lines = [
        "已从插件索引（%s）找到 %d 个候选：" % (_cache_descriptor(cache), len(results))
    ]
    for position, item in enumerate(results[:3], start=1):
        entry = item["entry"]
        reason = "；".join(item["reasons"])
        installed_note = "（本机已装）" if entry.get("id") in installed else ""
        lines.append(
            "%d. %s v%s · %s%s%s"
            % (
                position,
                entry.get("name", entry.get("id")),
                entry.get("version", "?"),
                _KIND_LABELS.get(entry.get("kind", ""), "插件"),
                installed_note,
                "：" + reason if reason else "",
            )
        )

    best = results[0]
    cards: list[dict[str, Any]] = []
    if best["score"] >= 4 and best["entry"].get("id") not in installed:
        card = ui_cards.install_block(
            best["entry"],
            "与你说的「%s」最匹配" % (_normalize_query(query) or "需求"),
        )
        cards.append(card)
        lines.append("")
        lines.append(
            "已生成「%s」的安装确认卡。只有你点击卡片上的【确认安装】，底座才会"
            "下载这一个 zip 并走完整校验；我不会自动安装。" % best["entry"].get("name", "该插件")
        )
    elif best["score"] >= 4 and best["entry"].get("id") in installed:
        lines.append("")
        lines.append("最匹配的插件本机已安装，无需重复安装。")
    else:
        lines.append("")
        lines.append("匹配还不够确定，先不生成安装卡。请补充用途（如「导出 PDF」「题卡渲染」）。")

    return {
        "ok": True,
        "host_tool": True,
        "plugin": HOST_PLUGIN,
        "action": TOOL_SEARCH,
        "summary": "\n".join(lines),
        "data": {
            "entries": [_public_entry(item["entry"]) for item in results],
            "cache": {
                "source_host": cache.get("source_host"),
                "saved_at": cache.get("saved_at"),
            },
        },
        "ui_cards": cards,
    }


def _suggest_outcome(plugin_id: str, reason: str) -> dict[str, Any]:
    cache = load_index_cache()
    if cache is None:
        return {
            "ok": False,
            "host_tool": True,
            "plugin": HOST_PLUGIN,
            "action": TOOL_SUGGEST,
            "error": "尚未拉取插件索引",
            "summary": "还没拉取过插件索引，无法给出安装建议。请先到「设置与控制」页拉取清单。",
        }
    entry = None
    for item in cache["entries"]:
        if item.get("id") == plugin_id:
            entry = item
            break
    if entry is None:
        return {
            "ok": False,
            "host_tool": True,
            "plugin": HOST_PLUGIN,
            "action": TOOL_SUGGEST,
            "error": "索引里没有该插件",
            "summary": "当前索引里没有 id 为「%s」的插件，先搜索一下再选择。" % plugin_id,
        }
    if plugin_id in _installed_ids():
        return {
            "ok": True,
            "host_tool": True,
            "plugin": HOST_PLUGIN,
            "action": TOOL_SUGGEST,
            "summary": "「%s」已经装在本机，无需重复安装。" % entry.get("name", plugin_id),
            "data": {"entry": _public_entry(entry), "installed": True},
        }
    card = ui_cards.install_block(entry, reason or "根据你的需求推荐")
    return {
        "ok": True,
        "host_tool": True,
        "plugin": HOST_PLUGIN,
        "action": TOOL_SUGGEST,
        "summary": (
            "已找到「%s」v%s（%s）：%s\n\n已生成安装确认卡。点击【确认安装】后，"
            "底座才会下载这一个 zip 并通过本机安装同款校验；在此之前不会安装。"
            % (
                entry.get("name", plugin_id),
                entry.get("version", "?"),
                _KIND_LABELS.get(entry.get("kind", ""), "插件"),
                entry.get("description", ""),
            )
        ),
        "data": {"entry": _public_entry(entry), "installed": False},
        "ui_cards": [card],
    }


def _parse_arguments(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, str):
        try:
            payload = json.loads(arguments or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("工具参数不是合法 JSON：%s" % exc) from exc
    else:
        payload = arguments
    if not isinstance(payload, dict):
        raise ValueError("工具参数必须是 JSON 对象")
    return payload


def execute_tool(name: str, arguments: Any) -> dict[str, Any]:
    if name not in TOOL_NAMES:
        return {
            "ok": False,
            "host_tool": True,
            "plugin": HOST_PLUGIN,
            "action": name,
            "error": "未知工具",
            "summary": "未知工具：%s" % name,
        }
    try:
        args = _parse_arguments(arguments)
        if name == TOOL_SEARCH:
            query = args.get("query")
            if query is not None and not isinstance(query, str):
                raise ValueError("query 必须是字符串")
            return _search_outcome(str(query or "")[:MAX_QUERY])
        plugin_id = args.get("plugin_id")
        if not isinstance(plugin_id, str) or not plugin_id.strip():
            raise ValueError("plugin_id 必须是非空字符串")
        reason = args.get("reason")
        if reason is not None and not isinstance(reason, str):
            raise ValueError("reason 必须是字符串")
        return _suggest_outcome(plugin_id.strip()[:MAX_ID], str(reason or "")[:MAX_REASON])
    except ValueError as exc:
        return {
            "ok": False,
            "host_tool": True,
            "plugin": HOST_PLUGIN,
            "action": name,
            "error": str(exc),
            "summary": "插件搜索失败：%s" % exc,
        }


def build_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": TOOL_SEARCH,
                "description": (
                    "在用户已拉取的插件索引里搜索插件（不联网、不安装、不下载）。"
                    "用户说「我想找个能导出 PDF 的插件」「推荐一个题卡渲染插件」时调用。"
                    "参数 query 传用途关键词（如「导出 PDF」「题卡」「OCR」）。"
                    "找到匹配项时底座会生成安装确认卡，必须由用户点击确认，你不得声称已安装。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "maxLength": MAX_QUERY,
                            "description": "插件用途关键词，例如「导出 PDF」「题卡渲染」「题库导入」。",
                        }
                    },
                    "required": ["query"],
                    "additionalProperties": False,
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": TOOL_SUGGEST,
                "description": (
                    "对索引里的某个插件生成安装建议卡（只建议，不安装）。"
                    "只有用户询问安装或你已从搜索结果里确定 plugin_id 时使用。"
                    "底座会渲染确认卡，用户点【确认安装】才会真正下载。"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plugin_id": {
                            "type": "string",
                            "maxLength": MAX_ID,
                            "description": "索引条目的反向域名 id，必须来自搜索结果。",
                        },
                        "reason": {
                            "type": "string",
                            "maxLength": MAX_REASON,
                            "description": "一句话说明为什么推荐这个插件。",
                        },
                    },
                    "required": ["plugin_id"],
                    "additionalProperties": False,
                },
            },
        },
    ]


def match_intent(user_input: str) -> dict[str, Any] | None:
    """宿主兜底：模型没发 tool_calls 时，把「找个插件」类句式路由到搜索。"""
    text = str(user_input or "").strip()
    if not text or "插件" not in text:
        return None
    if "zip" in text.lower():
        return None
    if not any(word in text for word in _SEARCH_HINTS):
        return None
    query = _normalize_query(text) or "插件"
    return {"tool": TOOL_SEARCH, "arguments": {"query": query}}
