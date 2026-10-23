"""题库 provider 路由：底座认「当前活跃的题库插件」，不认死某个 ID。

官方 core-bank 只是**默认** provider。第三方只要装一个声明 ``bank.provider``
能力、并按 ``schemas/question.json`` 出参的插件，就可以被选为活跃题库
（PLUGIN_SPEC §2.6.1）。本模块只管三件事：

1. **读配置**：``data/bank_provider.json``（用户亲手在控制台里选的，没配就用默认）；
2. **验配置**：被选中的 id 必须已安装**且**声明 ``bank.provider``，否则不算数；
3. **兜底**：配置失效时回退默认 provider 并如实带 ``fallback_reason``——
   「插件坏了，底座还能用」（AGENTS §2），绝不静默换成别的插件。

这里不解释题目结构、不碰数据库：题目读写仍由 ``app/core/bank.py`` 与
``app/api/bank.py`` 按传入的 plugin_id 完成。
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.core.config import root_data_dir
from app.core.plugins import discover_plugins

# 默认 provider 的**唯一**出处：全仓其它地方一律读本常量，不许再写字面量。
DEFAULT_PROVIDER_ID = "org.jiuzhang.core-bank"
PROVIDER_CAPABILITY = "bank.provider"
# 跨页签共享的通道：非题库插件（如录题端）也要能读公共真题库、写新题。
SHARED_METHODS = (
    "bank.get", "bank.topics", "bank.topic_notes", "bank.review",
    "bank.create", "bank.update", "bank.delete",
    # 浏览型插件没有自己的题库，读题/入篮都要落在活跃 provider 上
    "bank.active_list", "bank.active_stats", "basket.active_add",
)
# 按页签自身 id 走的方法：题篮与题库浏览天然多库并存，不需要 provider。
PER_TAB_METHODS = ("bank.list", "bank.stats", "bank.random", "basket.add", "basket.remove")

_PLUGIN_ID_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")


class ProviderRejected(Exception):
    """用户要设置的 provider 不合格：id 非法、没装、或没声明能力。"""


def state_path() -> Path:
    return root_data_dir() / "bank_provider.json"


def _installed() -> dict[str, dict[str, Any]]:
    discovered = discover_plugins()
    return {item["id"]: item for item in discovered.get("plugins", []) or []}


def configured_id() -> str | None:
    """用户配置的 provider id；文件缺失/损坏一律当作「没配过」，不报错。"""
    path = state_path()
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    value = data.get("plugin_id") if isinstance(data, dict) else None
    if not isinstance(value, str) or not _PLUGIN_ID_RE.match(value):
        return None
    return value


def eligible(plugin: dict[str, Any]) -> bool:
    return PROVIDER_CAPABILITY in (plugin.get("capabilities") or [])


def resolve() -> dict[str, Any]:
    """当前生效的 provider，附回退原因与方法口径，供宿主与控制台展示。"""
    installed = _installed()
    wanted = configured_id() or DEFAULT_PROVIDER_ID
    plugin = installed.get(wanted)
    reason = ""
    active = wanted
    if plugin is None:
        reason = (f"配置的题库 {wanted} 未安装" if wanted != DEFAULT_PROVIDER_ID
                  else f"默认题库 {DEFAULT_PROVIDER_ID} 未安装")
        active = DEFAULT_PROVIDER_ID
    elif not eligible(plugin):
        reason = f"插件 {wanted} 未声明 {PROVIDER_CAPABILITY} 能力，不能作为题库 provider"
        active = DEFAULT_PROVIDER_ID
    result: dict[str, Any] = {
        "plugin_id": active,
        "requested_id": wanted,
        "default_id": DEFAULT_PROVIDER_ID,
        "is_default": active == DEFAULT_PROVIDER_ID,
        "installed": active in installed,
        "name": (installed.get(active) or {}).get("name") or active,
        "version": (installed.get(active) or {}).get("version") or "",
        "shared_methods": list(SHARED_METHODS),
        "per_tab_methods": list(PER_TAB_METHODS),
        "fallback_reason": reason,
    }
    return result


def candidates() -> list[dict[str, Any]]:
    """可被选为 provider 的已装插件（含默认库自己），供控制台下拉。"""
    out = []
    for plugin in _installed().values():
        if not eligible(plugin):
            continue
        out.append({"id": plugin["id"], "name": plugin["name"], "version": plugin["version"],
                    "writable": "questions:write" in (plugin.get("permissions") or [])})
    return sorted(out, key=lambda item: item["id"])


def set_provider(plugin_id: str) -> dict[str, Any]:
    """写入用户选择；不合格直接抛，绝不落一个解析不出来的配置。"""
    if not isinstance(plugin_id, str) or not _PLUGIN_ID_RE.match(plugin_id or ""):
        raise ProviderRejected("题库 ID 不合法")
    plugin = _installed().get(plugin_id)
    if plugin is None:
        raise ProviderRejected(f"插件 {plugin_id} 未安装，不能设为题库")
    if not eligible(plugin):
        raise ProviderRejected(f"插件 {plugin_id} 未声明 {PROVIDER_CAPABILITY} 能力，不能设为题库")
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"plugin_id": plugin_id}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    return resolve()
