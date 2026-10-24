"""九章算子底座。"""

from __future__ import annotations

import os
from pathlib import Path

__version__ = "0.10.0"


def _env_file_candidates() -> list[Path]:
    """凭据文件候选：当前工作区的 ``.env``；default 首启兼容旧根 ``.env``。"""
    override = os.environ.get("JZO_ENV_FILE", "").strip()
    if override:
        return [Path(override)]
    from app.core.workspace_paths import (
        DEFAULT_WORKSPACE_ID,
        env_file_path_for,
        read_current_workspace_pointer,
    )

    workspace_id = read_current_workspace_pointer() or DEFAULT_WORKSPACE_ID
    workspace_env = env_file_path_for(workspace_id)
    if workspace_id != DEFAULT_WORKSPACE_ID or workspace_env.is_file():
        return [workspace_env]
    # 旧版凭据住在仓库根：default 工作区还没有自己的 .env 时先按旧位置加载，
    # 启动自举会把它迁进 data/workspaces/default/.env。
    return [workspace_env, Path(__file__).resolve().parent.parent / ".env"]


def _load_local_env() -> None:
    """Load the current workspace's .env into os.environ before submodules read config.

    Already-exported variables win, so a shell can always override the file.
    军令 #18 起凭据按工作区隔离：非 default 工作区绝不回落到仓库根 .env。
    """
    for env_file in _env_file_candidates():
        try:
            lines = env_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            text = line.strip()
            if not text or text.startswith("#") or "=" not in text:
                continue
            key, value = text.split("=", 1)
            key = key.strip()
            if key:
                os.environ.setdefault(key, value.strip())


_load_local_env()
