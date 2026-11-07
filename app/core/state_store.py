"""运行时状态的统一读写：新文件一律 TOML，旧 ``.json`` 首次读取即迁移。

状态文件属于用户目录（``data/``），但格式仍归基座管。这里的迁移只发生在读取路径上：
TOML 不存在时才看同名旧 JSON，迁移成功立即写 TOML 并移除旧文件；写入永远只写 TOML。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.core import toml_io, wire


def _legacy_path(path: Path) -> Path:
    return path.with_suffix(".json")


def load_table(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """读一份以表为根的运行时状态。"""
    fallback: dict[str, Any] = {} if default is None else default
    if path.is_file():
        return toml_io.load(path, fallback)
    legacy = _legacy_path(path)
    if legacy.is_file():
        data = wire.read_object(legacy, {})
        if data:
            return _migrated(path, legacy, data)
    return fallback


def load_records(path: Path, key: str) -> list[dict[str, Any]]:
    """读一份以数组为根的状态（TOML 顶层不能是数组，统一挂在 ``key`` 下）。"""
    if path.is_file():
        rows = toml_io.load(path, {}).get(key)
        return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
    legacy = _legacy_path(path)
    if legacy.is_file():
        try:
            rows = wire.read(legacy)
        except (OSError, ValueError):
            rows = None
        if isinstance(rows, list):
            table = {key: [row for row in rows if isinstance(row, dict)]}
            return _migrated(path, legacy, table).get(key) or []
    return []


def save(path: Path, value: dict[str, Any]) -> None:
    toml_io.write(path, value)


def _migrated(path: Path, legacy: Path, table: dict[str, Any]) -> dict[str, Any]:
    try:
        save(path, table)
    except (OSError, toml_io.TomlEncodeError):
        return table
    try:
        legacy.unlink()
    except OSError:
        pass
    return table
