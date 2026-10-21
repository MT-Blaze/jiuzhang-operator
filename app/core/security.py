"""本地写操作令牌。

读取类接口保持开放；任何修改类请求都必须携带 ``X-JZO-Token``。
采用一次性令牌机制：令牌用后即焚，二次使用必被拦截。
主令牌存储在 .local_token 文件中，每次验证成功后立即轮换。
"""

from __future__ import annotations

import os
import secrets
import threading
from pathlib import Path

from fastapi import Header, HTTPException

from app.core.config import settings

TOKEN_FILENAME = ".local_token"
HEADER_NAME = "X-JZO-Token"

# Thread-safe token rotation lock
_token_lock = threading.Lock()


def token_path() -> Path:
    return Path(settings.data_dir) / TOKEN_FILENAME


def _read_token_file() -> str | None:
    """Read current token from file."""
    path = token_path()
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return None


def _write_token_file(value: str) -> None:
    """Write new token to file atomically."""
    path = token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Write to temp file then rename for atomicity
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(value + "\n", encoding="utf-8")
    tmp_path.replace(path)
    # Set restrictive permissions (Unix only)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass  # Windows doesn't support chmod


def local_write_token() -> str:
    """Return the current valid token (generates if missing)."""
    env_token = os.environ.get("JZO_LOCAL_TOKEN", "").strip()
    if env_token:
        return env_token

    token = _read_token_file()
    if token:
        return token

    # Generate initial token
    value = secrets.token_urlsafe(32)
    _write_token_file(value)
    return value


def require_write_token(
    x_jzo_token: str | None = Header(default=None, alias=HEADER_NAME),
) -> None:
    """Validate one-time write token and rotate it.
    
    The token is consumed on first use: after successful validation,
    a new token is generated and written to disk. Any subsequent
    request with the old token will be rejected.
    """
    # Check environment variable override (for development)
    env_token = os.environ.get("JZO_LOCAL_TOKEN", "").strip()
    if env_token:
        if not x_jzo_token or not secrets.compare_digest(x_jzo_token, env_token):
            raise HTTPException(
                status_code=401,
                detail="写操作需要有效的 X-JZO-Token（见 JZO_LOCAL_TOKEN 环境变量）。",
            )
        return

    # One-time token validation with rotation
    with _token_lock:
        expected = _read_token_file()
        
        if not expected:
            # No token file - generate initial token and reject
            new_token = secrets.token_urlsafe(32)
            _write_token_file(new_token)
            raise HTTPException(
                status_code=401,
                detail="写操作需要有效的 X-JZO-Token（见 data/.local_token）。首次使用请查看该文件获取初始令牌。",
            )
        
        if not x_jzo_token or not secrets.compare_digest(x_jzo_token, expected):
            raise HTTPException(
                status_code=401,
                detail="令牌无效或已过期。写操作需要有效的 X-JZO-Token（见 data/.local_token），令牌用后即焚。",
            )
        
        # Token validated successfully - rotate to new token
        new_token = secrets.token_urlsafe(32)
        _write_token_file(new_token)
