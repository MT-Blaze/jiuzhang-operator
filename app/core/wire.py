"""对外 JSON 适配层：全仓唯一允许接触 JSON 文本的入口。

基座内部的文件一律用 TOML + dataclass。JSON 只剩三种**只读/对外**场景：

1. 旧版安装留下的 ``plugin.json``、``suite.json`` 与旧状态文件（首次启动迁移一次）；
2. 远端插件索引（外部仓库仍发布 JSON，无法由本项目改造）；
3. 题目导入包里的旧 ``.json``（老师手里的存量数据）。

HTTP 报文由 FastAPI 自己编解码，不经过本模块。除以上边界外，任何新增代码
都不得 ``import json``。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

__all__ = ["JSONDecodeError", "dumps", "loads", "read", "read_object"]


JSONDecodeError = json.JSONDecodeError


def loads(text: str) -> Any:
    return json.loads(text)


def dumps(value: Any, **options: Any) -> str:
    """把外部协议/数据库列需要的数据编成 JSON 文本；只允许在本边界内出现。"""
    options.setdefault("ensure_ascii", False)
    return json.dumps(value, **options)


def read(path: Path) -> Any:
    """读一份旧 JSON；文件缺失返回 None，解析失败抛出 ``JSONDecodeError``。"""
    return json.loads(path.read_text(encoding="utf-8"))


def read_object(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """读旧 JSON 并要求顶层是对象；缺失/损坏/类型不符一律回落 ``default``。"""
    fallback: dict[str, Any] = {} if default is None else default
    try:
        data = read(path)
    except (OSError, ValueError):
        return fallback
    return data if isinstance(data, dict) else fallback
