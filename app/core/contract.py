"""题目契约的版本与难度口径（叶子模块，不依赖 app.core 任何其他模块）。

为什么单独一层：``schemas/question.json`` 的 L1–L4 口径同时被存储自举（db.py）、
仓储读写（questions.py）与插件题库（bank.py）使用，任何一处另写一份映射表都会
在下次升版时漏改；放在无依赖的叶子模块里，三者共用同一事实来源。
"""

from __future__ import annotations

from typing import Any

CONTRACT_VERSION = "2.0"
LEGACY_SCHEMA_VERSIONS = ("1.0",)
# 1.0 的难度口径已废弃；novel 并入 L4（主公 2026-10-23 裁决）。
LEGACY_DIFFICULTY = {
    "basic": "L1",
    "medium": "L2",
    "hard": "L3",
    "novel": "L4",
}
DIFFICULTY_LEVELS = ("L1", "L2", "L3", "L4")
DIFFICULTY_LABELS = {
    "L1": "基础",
    "L2": "中档",
    "L3": "难",
    "L4": "压轴",
}


def normalize_difficulty(value: Any) -> Any:
    """1.0 口径的难度值归一成 L1–L4；认不出的原样返回，交给 Schema 报可读错误。"""
    if isinstance(value, str) and value.strip() in LEGACY_DIFFICULTY:
        return LEGACY_DIFFICULTY[value.strip()]
    return value


def normalize_contract_version(value: Any) -> Any:
    """老插件仍会自报 1.0；版本号由底座裁定，旧值升认，未知值原样交给 Schema。"""
    if value is None or value in LEGACY_SCHEMA_VERSIONS:
        return CONTRACT_VERSION
    return value
