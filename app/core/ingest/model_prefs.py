"""模型配置状态（插件财产，配置归插件卡）：启用/停用＋默认选择。

状态文件 ``model_prefs.toml`` 住**请求插件自己的目录**（与 catalog.toml、
models/ 同户），读写由宿主 relay 用 tab.plugin.id 代笔，绝不落宿主 data/。
插件更新是合并语义（lifecycle/update.py 的 _preserve_local_files）：新包没有
的文件原地保住（carried），下架/升级不丢老师的勾选；catalog.toml 则随新包
覆盖（清单可更新）。本模块不解释引擎语义，只存勾选，不认死任何插件 id。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from app.core import config, toml_io

FILENAME = "model_prefs.toml"
DEFAULT_ENGINE = "auto"
_PLUGIN_ID = re.compile(r"^[a-z0-9]+(\.[a-z0-9-]+)+$")


class PrefsError(ValueError):
    """勾选或默认值不合法（不认识的引擎 id、非法插件 id 等）。"""


def path(plugin_id: str) -> Path:
    if not _PLUGIN_ID.fullmatch(plugin_id or ""):
        raise PrefsError("插件 ID 不合法")
    return config.plugins_dir() / plugin_id / FILENAME


def load(plugin_id: str) -> dict[str, Any]:
    """每次现读；缺失或损坏一律当「全启用＋默认自动」，绝不挡配置页。"""
    document = toml_io.load(path(plugin_id), {})
    disabled = [str(item) for item in (document.get("disabled") or [])
                if isinstance(item, str) and item and item != DEFAULT_ENGINE]
    result: dict[str, Any] = {"disabled": list(dict.fromkeys(disabled))}
    for key in ("default_layout", "default_recognize"):
        result[key] = str(document.get(key) or DEFAULT_ENGINE)
    return result


def save(payload: dict[str, Any], valid_ids: Iterable[str],
         plugin_id: str) -> dict[str, Any]:
    """整块覆写勾选；缺的键沿用现值。id 必须来自目录，auto 不许停用。"""
    if not isinstance(payload, dict):
        raise PrefsError("请求体必须是对象")
    catalog_ids = set(valid_ids)
    current = load(plugin_id)
    disabled = current["disabled"]
    if "disabled" in payload:
        raw = payload.get("disabled")
        if not isinstance(raw, list):
            raise PrefsError("disabled 必须是引擎 id 数组")
        picked: list[str] = []
        for item in raw:
            entry_id = str(item or "")
            if entry_id == DEFAULT_ENGINE:
                raise PrefsError("「自动」是兜底瀑布，不能停用")
            if entry_id not in catalog_ids:
                raise PrefsError("目录里没有这个引擎：%s" % entry_id)
            if entry_id not in picked:
                picked.append(entry_id)
        disabled = picked
    document: dict[str, Any] = {"disabled": disabled}
    for key in ("default_layout", "default_recognize"):
        value = str(payload.get(key) or current[key]) if key in payload else current[key]
        if value != DEFAULT_ENGINE and value not in catalog_ids:
            raise PrefsError("目录里没有这个引擎：%s" % value)
        document[key] = value
    toml_io.write(path(plugin_id), document)
    return load(plugin_id)