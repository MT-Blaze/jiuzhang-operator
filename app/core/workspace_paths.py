"""工作区物理路径与当前工作区指针（军令 #18 第三步）。

这里是所有工作区路径的底层唯一出处：``config.py`` 与启动早期的 ``.env``
预加载都不得再另拼 ``data/workspaces/...``。

布局（所有工作区一致，default 也不例外）：

- ``data/workspaces/<id>/plugins/``        该区插件代码
- ``data/workspaces/<id>/plugin_state.json`` 该区启停/昵称/左栏树
- ``data/workspaces/<id>/startup.json``     该区启动界面
- ``data/workspaces/<id>/bank_provider.json`` 该区题库 provider
- ``data/workspaces/<id>/update_state.json`` 该区续更状态
- ``data/workspaces/<id>/.env``             该区凭据

default 工作区的**题库、图片与 config.json** 仍住在根 ``data/``（历史布局，
军令 #18 没有要求搬库，贸然搬动老师的题会带来不可逆风险）。

指针 ``data/current_workspace`` 只存一个工作区 id；缺失、损坏或 id 非法一律
回落 default——底座不能被一个坏指针关在门外。
"""

from __future__ import annotations

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_WORKSPACE_ID = "default"
CURRENT_WORKSPACE_FILENAME = "current_workspace"
DATABASE_FILENAME = "jiuzhang.db"

# 与 backup.WORKSPACE_ID_RE 同口径：只认字母数字下划线连字符，杜绝路径穿越。
WORKSPACE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")


def valid_workspace_id(value: object) -> bool:
    return isinstance(value, str) and WORKSPACE_ID_RE.fullmatch(value) is not None


def root_data_dir() -> Path:
    """根 data 目录，与当前活跃工作区无关。"""
    return Path(os.environ.get("JZO_DATA_DIR", str(PROJECT_ROOT / "data")))


def workspace_storage_dir(workspace_id: str) -> Path:
    """工作区**配置与插件**目录：``data/workspaces/<id>``（default 同口径）。"""
    if not valid_workspace_id(workspace_id):
        raise ValueError("工作区 ID 非法")
    return root_data_dir() / "workspaces" / workspace_id


def workspace_data_dir(workspace_id: str) -> Path:
    """工作区**业务数据**根：default 用根 data（历史布局），其余用工作区目录。"""
    if workspace_id == DEFAULT_WORKSPACE_ID:
        return root_data_dir()
    return workspace_storage_dir(workspace_id)


def current_workspace_pointer_path() -> Path:
    return root_data_dir() / CURRENT_WORKSPACE_FILENAME


def read_current_workspace_pointer() -> str:
    """读指针；缺失/不可读/非法一律返回空串，由调用方回落 default。"""
    try:
        value = current_workspace_pointer_path().read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return value if valid_workspace_id(value) else ""


def write_current_workspace_pointer(workspace_id: str) -> Path:
    """原子写指针（临时文件 + os.replace），返回指针路径。"""
    if not valid_workspace_id(workspace_id):
        raise ValueError("工作区 ID 非法")
    path = current_workspace_pointer_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(workspace_id + "\n", encoding="utf-8")
    os.replace(tmp, path)
    return path


def env_file_path_for(workspace_id: str) -> Path:
    """工作区凭据文件落点（``JZO_ENV_FILE`` 覆盖在 config.env_file_path 处理）。"""
    return workspace_storage_dir(workspace_id) / ".env"
