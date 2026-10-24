"""插件主机状态：启停、停用时间、自定义昵称与左栏文件夹树。

状态是**当前工作区自己的配置**，落在 ``data/workspaces/<id>/plugin_state.json``
（军令 #18：全局状态随插件一起按工作区物理隔离）。
写范围有且仅有这一个文件——ADR-007 的禁令不只约束「停用」，而是约束整个状态层：
题目数据、插件代码、工作区文件一律不许被这里顺手碰掉。

设计口径（军令 #16）：
- 老师给插件起的**昵称**、左栏的**文件夹分组**都是视图层偏好，
  不属于插件清单（清单是发布件，改了要重出包；这些是每台机器自己的组织方式）。
- 新装 / 未登记的插件一律默认启用——白嫖不可撤销（PLUGIN_SPEC §1.1）的反面是：
  底座绝不替用户默认关掉任何插件，也不远程禁用；停用只能由用户当场点。
- 全局快捷键注册与改绑已在军令 #18 第二步整层删除，本文件不再持有任何键位。
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime
from typing import Any

from app.core.config import current_workspace_id, workspace_storage_dir

STATE_FILENAME = "plugin_state.json"
_lock = threading.Lock()

NICKNAME_MAX = 40
FOLDER_NAME_MAX = 24
FOLDER_MAX = 20
SIDEBAR_MAX = 200
CHILDREN_MAX = 40

# 条目 key 与左栏 data-key 同构：plugin:<插件 id> / folder:<文件夹 id>
# 插件 id 段与 plugins._PLUGIN_ID 同口径（反向域名），免得幽灵键混进偏好表。
_KEY_RE = re.compile(r"^(?:plugin:[a-z0-9]+(?:\.[a-z0-9-]+)+|folder:[A-Za-z0-9_-]{1,60})$")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _clean_text(raw: Any, limit: int) -> str:
    return " ".join(str(raw or "").split())[:limit]


def _state_path():
    return workspace_storage_dir(current_workspace_id()) / STATE_FILENAME


def _load_raw() -> dict[str, Any]:
    path = _state_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _write(raw: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _mutate(apply) -> dict[str, Any]:
    """读→改→写的唯一出口：整份读回、只替换认识的键、未知键原样带着走，原子落盘。"""
    with _lock:
        raw = _load_raw()
        view = _normalize(raw)
        apply(view)
        payload = dict(raw)
        payload["disabled"] = sorted(view["disabled"])
        payload["disabled_at"] = view["disabled_at"]
        payload["nicknames"] = view["nicknames"]
        payload["sidebar"] = view["sidebar"]
        _write(payload)
        return view


def normalize_sidebar(raw: Any) -> list[dict[str, Any]]:
    """归一左栏树：文件夹条目带 name/children，插件条目只有 key。

    宽容归一（与 stage/ui 同口径）：非法条目丢掉，不该因为一处手滑让整棵树一键清零；
    同一个插件只认第一次出现的位置，文件夹超量截断。
    """
    if not isinstance(raw, list):
        return []
    seen: set[str] = set()
    folders = 0
    tree: list[dict[str, Any]] = []
    for item in raw[:SIDEBAR_MAX]:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        key = str(item.get("id") or "")
        if kind == "plugin" and _KEY_RE.fullmatch(key) and key.startswith("plugin:"):
            if key in seen:
                continue
            seen.add(key)
            tree.append({"kind": "plugin", "id": key})
        elif kind == "folder" and _KEY_RE.fullmatch(key) and key.startswith("folder:"):
            if key in seen or folders >= FOLDER_MAX:
                continue
            seen.add(key)
            folders += 1
            children: list[str] = []
            for child in (item.get("children") or [])[:CHILDREN_MAX]:
                child_key = str(child or "")
                if not _KEY_RE.fullmatch(child_key) or not child_key.startswith("plugin:"):
                    continue
                if child_key in seen:
                    continue
                seen.add(child_key)
                children.append(child_key)
            tree.append({
                "kind": "folder",
                "id": key,
                "name": _clean_text(item.get("name"), FOLDER_NAME_MAX) or "未命名文件夹",
                "children": children,
            })
    return tree


def prune_sidebar(tree: list[dict[str, Any]], installed: set[str]) -> list[dict[str, Any]]:
    """抹掉树上已经不在盘的插件；文件夹被掏空就整个消失。

    卸载是终态（ADR-007 里状态文件只记停用与否），所以这里只投影、不写盘——
    插件装回来时用户排的序还在原处，底座不动他的树。
    """
    kept: list[dict[str, Any]] = []
    for item in tree:
        if item["kind"] == "plugin":
            if item["id"].split(":", 1)[1] in installed:
                kept.append(dict(item))
            continue
        children = [child for child in item["children"] if child.split(":", 1)[1] in installed]
        if not children:
            continue
        folder = dict(item)
        folder["children"] = children
        kept.append(folder)
    return kept


def normalize_nicknames(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for plugin_id, value in raw.items():
        if not isinstance(plugin_id, str) or not _KEY_RE.fullmatch(f"plugin:{plugin_id}"):
            continue
        text = _clean_text(value, NICKNAME_MAX)
        if text:
            out[plugin_id] = text
    return out


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    disabled = {item for item in (raw.get("disabled") or []) if isinstance(item, str)}
    stamps = raw.get("disabled_at")
    disabled_at = {
        key: str(value)
        for key, value in (stamps.items() if isinstance(stamps, dict) else [])
        if isinstance(key, str) and value
    }
    return {
        "disabled": disabled,
        "disabled_at": disabled_at,
        "nicknames": normalize_nicknames(raw.get("nicknames")),
        "sidebar": normalize_sidebar(raw.get("sidebar")),
    }


def state() -> dict[str, Any]:
    """一次读全的主机状态视图（已归一）。"""
    return _normalize(_load_raw())


def disabled_ids() -> set[str]:
    return _normalize(_load_raw())["disabled"]


def is_enabled(plugin_id: str) -> bool:
    return plugin_id not in disabled_ids()


def set_enabled(plugin_id: str, enabled: bool) -> set[str]:
    """把某插件设为启用/停用，返回最新的停用集合。原子写盘，读回校验不静默吞错。

    停用的那一刻盖一个时间戳（控制台「已停用」列表按它排序）；重新启用不抹掉它，
    下次停用再覆盖——留着比抹掉诚实：那是这台机器上真实发生过的动作。
    """

    def apply(view: dict[str, Any]) -> None:
        if enabled:
            view["disabled"].discard(plugin_id)
        else:
            view["disabled"].add(plugin_id)
            view["disabled_at"][plugin_id] = _now_iso()

    return _mutate(apply)


def set_nickname(plugin_id: str, nickname: str) -> str:
    """写自定义昵称；空串等于交回官方原名（视图层回落，不改插件清单）。"""
    if not isinstance(plugin_id, str) or not _KEY_RE.fullmatch("plugin:" + plugin_id):
        return ""
    text = _clean_text(nickname, NICKNAME_MAX)

    def apply(view: dict[str, Any]) -> None:
        if text:
            view["nicknames"][plugin_id] = text
        else:
            view["nicknames"].pop(plugin_id, None)

    _mutate(apply)
    return text


def set_sidebar(tree: Any) -> list[dict[str, Any]]:
    """整棵左栏树一次性落盘（拖拽与右键改组的唯一写口）。"""

    def apply(view: dict[str, Any]) -> None:
        view["sidebar"] = normalize_sidebar(tree)

    return _mutate(apply)["sidebar"]


def folder_of(tree: list[dict[str, Any]]) -> dict[str, str]:
    """左栏树反查出 {插件 key → 文件夹 key}，未分组不在表里。"""
    mapping: dict[str, str] = {}
    for item in tree:
        if item.get("kind") != "folder":
            continue
        for child in item.get("children") or []:
            mapping[child] = item["id"]
    return mapping
