"""模型配置状态（插件财产，四合一卡 §2）：启用/停用＋默认选择。

状态文件 ``model_prefs.toml`` 住**插件目录**（与 model_config.toml、models/
同户），读写由宿主 relay 代笔，绝不落宿主 data/。插件更新是合并语义
（lifecycle/update.py 的 _preserve_local_files）：新包没有的文件原地保住
（carried），下架/升级不丢老师的勾选。本模块不解释引擎语义，只存勾选。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from app.core import config, toml_io

PLUGIN_ID = "org.jiuzhang.editor"
FILENAME = "model_prefs.toml"
DEFAULT_ENGINE = "auto"


class PrefsError(ValueError):
    """勾选或默认值不合法（不认识的引擎 id 等）。"""


def path() -> Path:
    return config.plugins_dir() / PLUGIN_ID / FILENAME


def load() -> dict[str, Any]:
    """每次现读；缺失或损坏一律当「全启用＋默认自动」，绝不挡配置页。"""
    document = toml_io.load(path(), {})
    disabled = [str(item) for item in (document.get("disabled") or [])
                if isinstance(item, str) and item and item != DEFAULT_ENGINE]
    result: dict[str, Any] = {"disabled": list(dict.fromkeys(disabled))}
    for key in ("default_layout", "default_recognize"):
        result[key] = str(document.get(key) or DEFAULT_ENGINE)
    return result


def save(payload: dict[str, Any], valid_ids: Iterable[str]) -> dict[str, Any]:
    """整块覆写勾选；缺的键沿用现值。id 必须来自目录，auto 不许停用。"""
    if not isinstance(payload, dict):
        raise PrefsError("请求体必须是对象")
    catalog_ids = set(valid_ids)
    current = load()
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
    toml_io.write(path(), document)
    return load()