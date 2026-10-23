"""插件启停状态：停用的插件从左侧导航消失、不加载进舞台，但代码与数据原地保留。

状态是**本机易失配置**，落在根 data 目录（与工作区无关）的一个 JSON 里，只记被停用的 id。
新装 / 未登记的插件一律默认启用——白嫖不可撤销（PLUGIN_SPEC §1.1）的反面是：
底座绝不替用户默认关掉任何插件，也不远程禁用；停用只能由用户当场点。
"""

from __future__ import annotations

import json
import threading
from typing import Any

from app.core.config import root_data_dir

STATE_FILENAME = "plugin_state.json"
_lock = threading.Lock()


def _state_path():
    return root_data_dir() / STATE_FILENAME


def _load_raw() -> dict[str, Any]:
    path = _state_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def disabled_ids() -> set[str]:
    raw = _load_raw()
    items = raw.get("disabled")
    return {item for item in items if isinstance(item, str)} if isinstance(items, list) else set()


def is_enabled(plugin_id: str) -> bool:
    return plugin_id not in disabled_ids()


def set_enabled(plugin_id: str, enabled: bool) -> set[str]:
    """把某插件设为启用/停用，返回最新的停用集合。原子写盘，读回校验不静默吞错。"""
    with _lock:
        raw = _load_raw()
        current = {item for item in (raw.get("disabled") or []) if isinstance(item, str)}
        if enabled:
            current.discard(plugin_id)
        else:
            current.add(plugin_id)
        payload = {"disabled": sorted(current)}
        path = _state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        return current
