"""TOML 读写：全仓配置文件与运行时状态的唯一格式出入口。

读侧直接用标准库 ``tomllib``；写侧覆盖项目实际用到的 TOML 子集：
标量、字符串、数组（可嵌套）、嵌套表、表数组、行内表。写入是原子的
（临时文件 + ``os.replace``），落盘失败不会留下半截配置。

探针产物等调试载荷可能带 ``Path``、``datetime`` 之类的非 TOML 对象，
调用方传 ``default=str`` 即可降级成字符串；TOML 没有 null，字典里的
``None`` 键会被丢弃，数组里的 ``None`` 会被跳过。

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


def dumps(value: dict[str, Any], default: Any = None) -> str:
    if not isinstance(value, dict):
        raise TomlEncodeError("TOML 顶层必须是表（dict）")
    lines: list[str] = []
    _emit_table(value, "", lines, default)
    return ("\n".join(lines).rstrip() + "\n") if lines else ""


def _emit_table(table: dict[str, Any], prefix: str, lines: list[str], default: Any = None) -> None:
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
        lines.append("%s = %s" % (_key(key), _value(item, default)))
    for key, item in subtables:
        lines.append("")
        lines.append("[%s]" % (prefix + _key(key)))
        _emit_table(item, prefix + _key(key) + ".", lines, default)
    for key, rows in arrays:
        header = prefix + _key(key)
        for row in rows:
            lines.append("")
            lines.append("[[%s]]" % header)
            _emit_table(row, header + ".", lines, default)


def _key(value: str) -> str:
    return value if _BARE_KEY.fullmatch(value) else _quote(value)


def _value(item: Any, default: Any = None) -> str:
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
    if isinstance(item, (list, tuple, set)):
        children = [_value(child, default) for child in item if child is not None]
        return "[" + ", ".join(children) + "]"
    if isinstance(item, dict):
        return _inline_table(item, default)
    if default is not None:
        return _value(default(item), default)
    raise TomlEncodeError("不支持的值类型：%s" % type(item).__name__)


def _inline_table(table: dict[str, Any], default: Any = None) -> str:
    fields = []
    for raw_key, item in table.items():
        if item is None:
            continue
        fields.append("%s = %s" % (_key(str(raw_key)), _value(item, default)))
    return "{ " + ", ".join(fields) + " }"


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
