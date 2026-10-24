"""题篮：跨插件共享的组卷选题集合（宿主托管）。

为什么不让插件自己存：
- 插件之间不得共享全局状态（AGENTS §2），题篮又是题库插件与组卷插件的交接口；
- 沙箱 iframe 没有 localStorage 可用，刷新就丢；
- 一次组卷可能跨多个题库插件，宿主必须按 ``plugin_id`` 分别取题并校验存在性。

存储为当前工作区的 ``data/basket.json``，原子写入；数量上限 200。
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from app.core.config import settings

MAX_BASKET = 200
LOCAL_TZ = timezone(timedelta(hours=8))
_lock = threading.Lock()


class BasketError(Exception):
    pass


def _path() -> Path:
    return Path(settings.data_dir) / "basket.json"


def _now() -> str:
    return datetime.now(LOCAL_TZ).isoformat(timespec="seconds")


def _read() -> dict[str, Any]:
    path = _path()
    if not path.is_file():
        return {"items": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"items": []}
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        return {"items": []}
    # question_id 与 plugin_id 缺一不算一条合法的篮内条目：写盘的两条路径（add/replace）
    # 都保证带齐，这里读到缺的只可能是手改过的 basket.json，下游按库分组取题会直接 KeyError。
    items = [
        item
        for item in data["items"]
        if isinstance(item, dict)
        and isinstance(item.get("question_id"), str) and item["question_id"]
        and isinstance(item.get("plugin_id"), str) and item["plugin_id"]
    ]
    return {"items": items[:MAX_BASKET]}


def _write(items: list[dict[str, Any]]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"updated_at": _now(), "items": items}
    tmp = path.with_suffix(".json.part")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def list_items() -> list[dict[str, Any]]:
    with _lock:
        return _read()["items"]


def add(plugin_id: str, question_ids: Iterable[str]) -> list[dict[str, Any]]:
    wanted = []
    for question_id in question_ids:
        if isinstance(question_id, str) and question_id.startswith("q_") and question_id not in wanted:
            wanted.append(question_id)
    if not wanted:
        raise BasketError("至少给一个合法的题目 ID")
    with _lock:
        items = _read()["items"]
        existing = {item["question_id"] for item in items}
        for question_id in wanted:
            if question_id in existing:
                continue
            if len(items) >= MAX_BASKET:
                raise BasketError(f"题篮最多 {MAX_BASKET} 题，请先移除一些题目。")
            items.append({"question_id": question_id, "plugin_id": plugin_id, "added_at": _now()})
            existing.add(question_id)
        _write(items)
        return items


def remove(question_id: str) -> list[dict[str, Any]]:
    with _lock:
        items = _read()["items"]
        kept = [item for item in items if item.get("question_id") != question_id]
        if len(kept) == len(items):
            raise BasketError(f"题篮里没有 {question_id}")
        _write(kept)
        return kept


def clear() -> list[dict[str, Any]]:
    with _lock:
        _write([])
        return []


def replace(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """整体替换（组卷插件一次性保存 50 题时使用），仍走存在性由 API 校验。"""
    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        question_id = item.get("question_id")
        plugin_id = item.get("plugin_id")
        if not isinstance(question_id, str) or not isinstance(plugin_id, str):
            continue
        if question_id in seen:
            continue
        seen.add(question_id)
        cleaned.append(
            {"question_id": question_id, "plugin_id": plugin_id, "added_at": item.get("added_at") or _now()}
        )
        if len(cleaned) >= MAX_BASKET:
            break
    with _lock:
        _write(cleaned)
        return cleaned
