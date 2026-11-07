"""TOML 读写：全仓配置文件与运行时状态的唯一格式出入口。

读侧直接用标准库 ``tomllib``；写侧只实现本项目实际用到的 TOML 子集：
标量、字符串、标量数组、嵌套表、表数组。写入是原子的（临时文件 + ``os.replace``），
落盘失败不会留下半截配置。

JSON 不是本模块的备选格式。旧 JSON 的迁移由 ``app.core.wire`` 统一接管，
迁移完成后本模块只认 TOML。
"""

from __future__ import annotations

import os
import re
import tomllib
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

__all__ = ["TomlEncodeError", "dumps", "load", "loads", "write"]

_BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


class TomlEncodeError(ValueError):
    """值无法无损表达为 TOML。"""


def loads(text: str) -> dict[str, Any]:
    return tomllib.loads(text)


def load(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """读一份 TOML；文件缺失或损坏时返回 ``default``，绝不把启动路径打断。"""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return {} if default is None else default
    try:
        data = tomllib.loads(raw)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError):
        return {} if default is None else default
    return data


def write(path: Path, value: dict[str, Any]) -> None:
    """原子写 TOML：父目录自动创建，临时文件与目标同目录以保证 replace 原子。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(dumps(value), encoding="utf-8")
    os.replace(tmp, path)


def dumps(value: dict[str, Any]) -> str:
    if not isinstance(value, dict):
        raise TomlEncodeError("TOML 顶层必须是表（dict）")
    lines: list[str] = []
    _emit_table(value, "", lines)
    return ("\n".join(lines).rstrip() + "\n") if lines else ""


def _emit_table(table: dict[str, Any], prefix: str, lines: list[str]) -> None:
    scalars: list[tuple[str, Any]] = []
    subtables: list[tuple[str, dict[str, Any]]] = []
    arrays: list[tuple[str, list[dict[str, Any]]]] = []
    for raw_key, item in table.items():
        key = str(raw_key)
        if item is None:
            continue
        if isinstance(item, dict):
            subtables.append((key, item))
        elif isinstance(item, list) and item and all(isinstance(row, dict) for row in item):
            arrays.append((key, item))
        else:
            scalars.append((key, item))
    for key, item in scalars:
        lines.append("%s = %s" % (_key(key), _value(item)))
    for key, item in subtables:
        lines.append("")
        lines.append("[%s]" % (prefix + _key(key)))
        _emit_table(item, prefix + _key(key) + ".", lines)
    for key, rows in arrays:
        header = prefix + _key(key)
        for row in rows:
            lines.append("")
            lines.append("[[%s]]" % header)
            _emit_table(row, header + ".", lines)


def _key(value: str) -> str:
    return value if _BARE_KEY.fullmatch(value) else _quote(value)


def _value(item: Any) -> str:
    if isinstance(item, bool):
        return "true" if item else "false"
    if isinstance(item, int):
        return str(item)
    if isinstance(item, float):
        return repr(item)
    if isinstance(item, str):
        return _quote(item)
    if isinstance(item, (datetime, date, time)):
        return _quote(item.isoformat())
    if isinstance(item, (list, tuple)):
        for child in item:
            if child is None:
                raise TomlEncodeError("TOML 数组里不能有 null")
            if isinstance(child, (dict, list, tuple)):
                raise TomlEncodeError("标量数组里不能嵌套对象或数组")
        return "[" + ", ".join(_value(child) for child in item) + "]"
    if isinstance(item, dict):
        raise TomlEncodeError("对象必须写成独立表，不能作为行内值")
    raise TomlEncodeError("不支持的值类型：%s" % type(item).__name__)


def _quote(value: str) -> str:
    out = ['"']
    for char in value:
        code = ord(char)
        if char == '"':
            out.append('\\"')
        elif char == "\\":
            out.append("\\\\")
        elif char == "\n":
            out.append("\\n")
        elif char == "\r":
            out.append("\\r")
        elif char == "\t":
            out.append("\\t")
        elif code < 0x20 or code == 0x7F:
            out.append("\\u%04x" % code)
        else:
            out.append(char)
    out.append('"')
    return "".join(out)
