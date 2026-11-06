"""重题池的元数据差异账（军令·查重三栏）。

裁判台只该看「两边确实不一样」的东西：标签 / 来源给并集，题型 / 难度是唯一属性，
两边都有且不同时必须由老师二选一。本模块只做纯计算，不碰库、不发请求，
``pending_pool`` 与后续调用方共用这一份口径。

``resolutions`` 是唯一属性的裁决参数：只收 ``main`` / ``incoming``，别的键与值
一律拒绝——界面上的锁只是提示，真正的闸门在这里。

单文件拆出的理由与 ``pending_pool`` 相同：PLUGIN_SPEC §2.8 的单文件行数上限。
"""

from __future__ import annotations

from typing import Any

from app.core import bank
from app.core.pending_db import PendingError

SOURCE_TITLE_FIELD = "paper_title"
REQUIRED_UNIQUE_FIELDS = ("type", "difficulty")
FIELD_LABELS = {
    "type": "题型",
    "difficulty": "难度",
    "tags": "标签",
    "source": "来源",
    "grade": "年级",
}
TYPE_LABELS = {
    "single_choice": "单选题",
    "multiple_choice": "多选题",
    "fill_blank": "填空题",
    "solution": "解答题",
}


def source_view(document: dict[str, Any]) -> dict[str, Any] | None:
    raw = document.get("source")
    if not isinstance(raw, dict):
        return None
    entry = {key: raw.get(key) for key in bank.SOURCE_FIELDS
             if raw.get(key) not in (None, "")}
    return entry or None


def source_key(entry: dict[str, Any]) -> tuple[str, str]:
    return (str(entry.get(SOURCE_TITLE_FIELD) or ""), str(entry.get("question_no") or ""))


def meta_value(document: dict[str, Any], field: str) -> str:
    return str(document.get(field) or "").strip()


def meta_diff(main: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """只列两侧**确实不同**的元数据，供裁判台一眼看完。

    - 多选属性（标签 / 来源）给并集，并点名「并进来的是哪几条」；
    - 唯一属性（题型 / 难度）两侧都有且不同 → ``conflict=true`` 并要求老师二选一，
      未选之前合并动作在底座就被拒（不靠界面自觉）；
    - 两侧一样、只有一侧有值的字段不制造噪声：一样的不列，单边有值的列为可补项。
    """
    multi: list[dict[str, Any]] = []
    main_tags = [str(item) for item in (main.get("tags") or []) if isinstance(item, str)]
    incoming_tags = [str(item) for item in (incoming.get("tags") or []) if isinstance(item, str)]
    tag_union = list(dict.fromkeys([*main_tags, *incoming_tags]))
    if set(main_tags) != set(incoming_tags):
        multi.append({
            "field": "tags", "label": FIELD_LABELS["tags"],
            "main": main_tags, "incoming": incoming_tags, "union": tag_union,
            "added": [item for item in tag_union if item not in main_tags],
        })

    main_source = source_view(main)
    incoming_source = source_view(incoming)
    source_union: list[dict[str, Any]] = []
    for source in (main_source, incoming_source):
        if source and source_key(source) not in {source_key(item) for item in source_union}:
            source_union.append(source)
    if main_source != incoming_source:
        multi.append({
            "field": "source", "label": FIELD_LABELS["source"],
            "main": main_source, "incoming": incoming_source, "union": source_union,
            "added": ([incoming_source] if incoming_source
                      and source_key(incoming_source)
                      != source_key(main_source or {}) else []),
        })

    unique: list[dict[str, Any]] = []
    requires: list[str] = []
    conflicts: list[dict[str, Any]] = []
    for field in REQUIRED_UNIQUE_FIELDS:
        main_value = meta_value(main, field)
        incoming_value = meta_value(incoming, field)
        if main_value == incoming_value:
            continue
        conflict = bool(main_value and incoming_value)
        item = {
            "field": field, "label": FIELD_LABELS[field],
            "main": main_value, "incoming": incoming_value, "conflict": conflict,
        }
        if field == "type":
            item["main_label"] = TYPE_LABELS.get(main_value, main_value)
            item["incoming_label"] = TYPE_LABELS.get(incoming_value, incoming_value)
        unique.append(item)
        if conflict:
            requires.append(field)
            conflicts.append({"field": field, "main": main_value,
                              "incoming": incoming_value})
    return {
        "multi": multi,
        "unique": unique,
        "conflicts": conflicts,
        "requires_resolution": requires,
        "has_difference": bool(multi or unique),
    }


def resolutions(raw: Any) -> dict[str, str]:
    """只认 ``{"type": "main"|"incoming", "difficulty": ...}``；别的键一律不收。"""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise PendingError("冲突裁决参数必须是对象")
    picked: dict[str, str] = {}
    for field in REQUIRED_UNIQUE_FIELDS:
        value = str(raw.get(field) or "").strip()
        if value in ("main", "incoming"):
            picked[field] = value
        elif value:
            raise PendingError(f"「{FIELD_LABELS[field]}」冲突只能选主库或新题")
    return picked
