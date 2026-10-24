"""全局配置。所有路径以仓库根目录为锚点，不依赖当前工作目录。

支持多工作区（Workspace）隔离：每个工作区拥有独立的数据库、上传资源、配置、
插件代码与插件状态（军令 #18）。插件路径不再有导入期死值——每次调用
:func:`plugins_dir` 都按当前工作区重新求值。
"""

from __future__ import annotations

import os
from pathlib import Path

from app.core.workspace_paths import (
    CURRENT_WORKSPACE_FILENAME,
    DATABASE_FILENAME,
    DEFAULT_WORKSPACE_ID,
    PROJECT_ROOT,
    WORKSPACE_ID_RE,
    current_workspace_pointer_path,
    env_file_path_for,
    read_current_workspace_pointer,
    root_data_dir,
    valid_workspace_id,
    workspace_data_dir,
    workspace_storage_dir,
    write_current_workspace_pointer,
)

__all__ = [
    "CURRENT_WORKSPACE_FILENAME",
    "DATABASE_FILENAME",
    "DEFAULT_WORKSPACE_ID",
    "PROJECT_ROOT",
    "WORKSPACE_ID_RE",
    "Settings",
    "current_workspace_id",
    "current_workspace_pointer_path",
    "default_database_path",
    "env_file_path",
    "load_current_workspace",
    "plugins_dir",
    "root_data_dir",
    "settings",
    "switch_workspace",
    "workspace_data_dir",
    "workspace_storage_dir",
]


def default_database_path() -> Path:
    """default 工作区的数据库路径（历史布局：根 data 目录）。"""
    return root_data_dir() / DATABASE_FILENAME


class Settings:
    project_root: Path = PROJECT_ROOT
    static_dir: Path = PROJECT_ROOT / "static"
    schemas_dir: Path = PROJECT_ROOT / "schemas"

    # 当前工作区 id；None 表示 default。它是指针文件在本进程里的镜像：
    # 启动时由 load_current_workspace() 装载，切库时由 switch_workspace() 同步写回。
    workspace_id: str | None = None

    @property
    def data_dir(self) -> Path:
        """当前工作区的业务数据根（default 是根 data，其余是工作区目录）。"""
        return workspace_data_dir(self.workspace_id or DEFAULT_WORKSPACE_ID)

    @property
    def database_path(self) -> Path:
        return self.data_dir / DATABASE_FILENAME

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def config_path(self) -> Path:
        return self.data_dir / "config.json"

    host: str = os.environ.get("JZO_HOST", "127.0.0.1")
    port: int = int(os.environ.get("JZO_PORT", "8000"))


settings = Settings()


def current_workspace_id() -> str:
    """当前工作区 id（永不为空）；None 即 default。"""
    return settings.workspace_id or DEFAULT_WORKSPACE_ID


def plugins_dir() -> Path:
    """当前工作区的插件目录，每次调用重新求值。

    ``JZO_PLUGINS_DIR`` 是测试与便携部署的显式覆盖口子（探针整套依赖它），
    没设置时才按当前工作区解析到 ``data/workspaces/<id>/plugins``。
    """
    override = os.environ.get("JZO_PLUGINS_DIR", "").strip()
    if override:
        return Path(override)
    return workspace_storage_dir(current_workspace_id()) / "plugins"


def env_file_path() -> Path:
    """当前工作区的凭据文件；``JZO_ENV_FILE`` 可整体覆盖（测试/启动器专用）。"""
    override = os.environ.get("JZO_ENV_FILE", "").strip()
    if override:
        return Path(override)
    return env_file_path_for(current_workspace_id())


def load_current_workspace() -> str:
    """从指针装载当前工作区；指针缺失/损坏回落 default。返回解析后的 id。"""
    workspace_id = read_current_workspace_pointer() or DEFAULT_WORKSPACE_ID
    settings.workspace_id = None if workspace_id == DEFAULT_WORKSPACE_ID else workspace_id
    return workspace_id


def switch_workspace(workspace_id: str | None) -> None:
    """切到指定工作区：先原子写指针，再更新进程内镜像。

    指针写失败时内存不变——绝不出现「界面已切、重启后却回旧区」的分裂。
    """
    resolved = workspace_id or DEFAULT_WORKSPACE_ID
    if not valid_workspace_id(resolved):
        raise ValueError("工作区 ID 非法")
    write_current_workspace_pointer(resolved)
    settings.workspace_id = None if resolved == DEFAULT_WORKSPACE_ID else resolved
