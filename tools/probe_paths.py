# -*- coding: utf-8 -*-
"""真机探针共用的路径解析：偏好状态只从「当前工作区」读。

ADR-012 之后 ``plugin_state.json`` 住在 ``<data>/workspaces/<区>/`` 里，
根 ``data/plugin_state.json`` 是历史遗留、宿主根本不读。探针若还去根目录比对，
「偏好已还原」验的就是一份没人看的文件——等于没验。

优先级：
1. ``JZO_STATE_FILE``：隔离底座显式指路时直接用；
2. ``JZO_DATA_DIR``（或调用方给的根目录）下的 ``current_workspace`` 指针；
3. 指针缺失 / 损坏 / 非法 → ``default``——与宿主 ``read_current_workspace_pointer`` 同口径。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
DEFAULT_WORKSPACE_ID = "default"


def resolve_plugin_state_file(root: Path | None = None) -> Path:
    override = os.environ.get("JZO_STATE_FILE")
    if override:
        return Path(override)
    data_root = Path(os.environ.get("JZO_DATA_DIR") or root or (PROJECT_ROOT / "data"))
    workspace_id = ""
    try:
        workspace_id = (data_root / "current_workspace").read_text(encoding="utf-8").strip()
    except OSError:
        workspace_id = ""
    if not WORKSPACE_ID_RE.fullmatch(workspace_id):
        workspace_id = DEFAULT_WORKSPACE_ID
    return data_root / "workspaces" / workspace_id / "plugin_state.json"
