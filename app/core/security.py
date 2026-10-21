"""本地写操作令牌。

读取类接口保持开放；任何修改类请求都必须携带 ``X-JZO-Token``。
令牌优先取环境变量 ``JZO_LOCAL_TOKEN``，否则首次使用时生成到
``<data_dir>/.local_token``（仅本机可读）。
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import Header, HTTPException

from app.core.config import settings

TOKEN_FILENAME = ".local_token"
HEADER_NAME = "X-JZO-Token"


def token_path() -> Path:
    return Path(settings.data_dir) / TOKEN_FILENAME


def local_write_token() -> str:
    env_token = os.environ.get("JZO_LOCAL_TOKEN", "").strip()
    if env_token:
        return env_token

    path = token_path()
    if path.is_file():
        stored = path.read_text(encoding="utf-8").strip()
        if stored:
            return stored

    path.parent.mkdir(parents=True, exist_ok=True)
    value = secrets.token_urlsafe(32)
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()

    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(value + "\n")
    return value


def require_write_token(
    x_jzo_token: str | None = Header(default=None, alias=HEADER_NAME),
) -> None:
    expected = local_write_token()
    if not x_jzo_token or not secrets.compare_digest(x_jzo_token, expected):
        raise HTTPException(
            status_code=401,
            detail="写操作需要有效的 X-JZO-Token（见 data/.local_token 或 JZO_LOCAL_TOKEN）。",
        )
