"""运行时状态的统一读写：只认 TOML。

状态文件属于用户目录（``data/``），但格式仍归基座管。基座彻底封杀 JSON：
本模块只读写 TOML，不再识别同名旧 ``.json``。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core import toml_io


def load_table(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """读一份以表为根的运行时状态。"""
    fallback: dict[str, Any] = {} if default is None else default
    if path.is_file():
        return toml_io.load(path, fallback)
    return fallback


def load_records(path: Path, key: str) -> list[dict[str, Any]]:
    """读一份以数组为根的状态（TOML 顶层不能是数组，统一挂在 ``key`` 下）。"""
    if path.is_file():
        rows = toml_io.load(path, {}).get(key)
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    return []


def save(path: Path, value: dict[str, Any]) -> None:
    toml_io.write(path, value)
