"""启动行为：老师选「打开软件先落在哪个界面」，选择落盘在当前工作区目录。

与 :mod:`app.core.plugin_state` 同款定位——只属于当前工作区的易失配置，
文件缺失或损坏一律当作「没配过」，回落默认欢迎页（自由对话），绝不抛错
挡住启动：底座的第一原则是「插件坏了，底座还能用」（AGENTS §2），启动
路径上更不允许因为一个失效的偏好把老师关在门外。

目标只有两种形状：``chat``（默认欢迎页）与 ``plugin:<id>``（某个已启用
插件的工作模式）。指向的插件被卸载或停用后，配置**原地保留**（用户可能
只是临时停用），但 :func:`resolve` 会如实回退并带上 ``fallback_reason``，
同时打一条 WARNING 日志，不静默换目标。
"""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any

from app.core.config import current_workspace_id, workspace_storage_dir
from app.core.plugins import discover_plugins

logger = logging.getLogger("jzo.startup")

STATE_FILENAME = "startup.json"
CHAT_TARGET = "chat"
PLUGIN_PREFIX = "plugin:"
_PLUGIN_ID_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")
_lock = threading.Lock()


class StartupRejected(Exception):
    """用户要设置的启动目标不合格：形状非法、插件没装、或已被停用。"""


def state_path() -> Path:
    return workspace_storage_dir(current_workspace_id()) / STATE_FILENAME


def _load_raw() -> dict[str, Any]:
    path = state_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def normalize(target: Any) -> str | None:
    """把任意输入归一成合法目标；不合法返回 None（读侧一律回落 chat）。"""
    if not isinstance(target, str):
        return None
    value = target.strip()
    if value == CHAT_TARGET:
        return CHAT_TARGET
    if value.startswith(PLUGIN_PREFIX):
        plugin_id = value[len(PLUGIN_PREFIX):]
        if _PLUGIN_ID_RE.match(plugin_id):
            return PLUGIN_PREFIX + plugin_id
    return None


def read_target() -> str:
    """已落盘的启动目标；缺失、损坏或形状非法一律当作默认欢迎页。"""
    return normalize(_load_raw().get("target")) or CHAT_TARGET


def installed_plugins() -> list[dict[str, Any]]:
    """已安装插件的启用态清单，供下拉数据源与校验共用一个口径。"""
    discovered = discover_plugins()
    return [item for item in (discovered.get("plugins") or []) if isinstance(item, dict)]


def candidates() -> list[dict[str, Any]]:
    """可被选为启动界面的插件：**只看启用态**，停用的不进下拉。

    ``show_in_sidebar=false`` 的插件照样列出（它仍然有工作模式，只是不在
    左栏占位），由前端在下拉里如实标注，不替用户隐藏能力。
    """
    out = []
    for plugin in installed_plugins():
        if plugin.get("enabled") is False:
            continue
        out.append({
            "target": PLUGIN_PREFIX + str(plugin.get("id")),
            "id": plugin.get("id"),
            "name": plugin.get("name") or plugin.get("id"),
            "version": plugin.get("version") or "",
            "show_in_sidebar": plugin.get("show_in_sidebar") is not False,
            "has_stage": bool(plugin.get("stage")),
        })
    return sorted(out, key=lambda item: str(item.get("name") or ""))


def set_target(target: Any) -> str:
    """校验并落盘用户选择；不合格直接抛，绝不写一个解析不出来的配置。

    与 :func:`resolve` 的分工是刻意的：写入时**严格**（插件必须已装且已启用，
    否则老师选完下次启动就静默回退，等于白选），读取时**宽容**（插件后来被
    删或被停用，回退默认页并说明原因）。
    """
    value = normalize(target)
    if value is None:
        raise StartupRejected("启动目标不合法：只接受 chat 或 plugin:<插件 id>")
    if value.startswith(PLUGIN_PREFIX):
        plugin_id = value[len(PLUGIN_PREFIX):]
        plugin = next((p for p in installed_plugins() if p.get("id") == plugin_id), None)
        if plugin is None:
            raise StartupRejected(f"插件 {plugin_id} 未安装，不能作为启动界面")
        if plugin.get("enabled") is False:
            raise StartupRejected(f"插件 {plugin_id} 已停用，先启用它再设为启动界面")
    with _lock:
        payload = {"target": value}
        path = state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(path)
    return value


def resolve() -> dict[str, Any]:
    """当前生效的启动行为，附回退原因与候选清单，供设置页与工作台启动共用。"""
    target = read_target()
    effective = target
    reason = ""
    plugin_name = ""
    if target.startswith(PLUGIN_PREFIX):
        plugin_id = target[len(PLUGIN_PREFIX):]
        plugin = next((p for p in installed_plugins() if p.get("id") == plugin_id), None)
        if plugin is None:
            reason = f"启动插件 {plugin_id} 已卸载，回落默认欢迎页"
        elif plugin.get("enabled") is False:
            reason = f"启动插件 {plugin_id} 已停用，回落默认欢迎页"
        else:
            plugin_name = str(plugin.get("name") or plugin_id)
        if reason:
            effective = CHAT_TARGET
            logger.warning("%s（配置 %s 原地保留）", reason, target)
    return {
        "target": target,
        "effective": effective,
        "kind": "plugin" if effective.startswith(PLUGIN_PREFIX) else "chat",
        "plugin_id": effective[len(PLUGIN_PREFIX):] if effective.startswith(PLUGIN_PREFIX) else "",
        "plugin_name": plugin_name,
        "fallback_reason": reason,
        "candidates": candidates(),
    }
