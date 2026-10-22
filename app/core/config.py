"""全局配置。所有路径以仓库根目录为锚点，不依赖当前工作目录。

支持多工作区（Workspace）隔离：每个工作区拥有独立的数据库、上传资源和配置。
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# 题库数据库文件名的唯一事实来源（AGENTS §4：路径唯一入口在 config.py）。
# 曾经 config 写 "questions.db" 而 db.py 写 "jiuzhang.db"，导致工作区登记表里
# 记的是一条永不落地的虚构路径；实际数据一直写在 jiuzhang.db。此处收敛为一处。
DATABASE_FILENAME = "jiuzhang.db"


def root_data_dir() -> Path:
    """根 data 目录，与当前活跃工作区无关。

    工作区登记表、default 工作区路径都要用它，绝不能读 ``settings.data_dir``
    （那会随当前工作区漂移，把 default 的库指到别的库上）。
    """
    return Path(os.environ.get("JZO_DATA_DIR", str(PROJECT_ROOT / "data")))


def default_database_path() -> Path:
    """default 工作区（根 data 目录）的数据库路径。"""
    return root_data_dir() / DATABASE_FILENAME


class Settings:
    project_root: Path = PROJECT_ROOT
    static_dir: Path = PROJECT_ROOT / "static"
    schemas_dir: Path = PROJECT_ROOT / "schemas"
    # 插件目录允许环境变量覆盖：测试与便携部署专用，业务代码禁止另拼路径
    plugins_dir: Path = Path(os.environ.get("JZO_PLUGINS_DIR", str(PROJECT_ROOT / "plugins")))
    
    # Workspace support
    workspace_id: str | None = None  # Current workspace ID, None means default
    
    @property
    def data_dir(self) -> Path:
        """Return data directory for current workspace."""
        base = root_data_dir()
        if self.workspace_id:
            return base / "workspaces" / self.workspace_id
        return base
    
    @property
    def database_path(self) -> Path:
        """Return database path for current workspace."""
        return self.data_dir / DATABASE_FILENAME
    
    @property
    def uploads_dir(self) -> Path:
        """Return uploads directory for current workspace."""
        return self.data_dir / "uploads"
    
    @property
    def config_path(self) -> Path:
        """Return workspace config path."""
        return self.data_dir / "config.json"
    
    host: str = os.environ.get("JZO_HOST", "127.0.0.1")
    port: int = int(os.environ.get("JZO_PORT", "8000"))


settings = Settings()


def switch_workspace(workspace_id: str | None) -> None:
    """Switch to a different workspace (thread-safe)."""
    settings.workspace_id = workspace_id
