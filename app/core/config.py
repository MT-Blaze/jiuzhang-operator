"""全局配置。所有路径以仓库根目录为锚点，不依赖当前工作目录。

支持多工作区（Workspace）隔离：每个工作区拥有独立的数据库、上传资源和配置。
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings:
    project_root: Path = PROJECT_ROOT
    static_dir: Path = PROJECT_ROOT / "static"
    schemas_dir: Path = PROJECT_ROOT / "schemas"
    plugins_dir: Path = PROJECT_ROOT / "plugins"
    
    # Workspace support
    workspace_id: str | None = None  # Current workspace ID, None means default
    
    @property
    def data_dir(self) -> Path:
        """Return data directory for current workspace."""
        base = Path(os.environ.get("JZO_DATA_DIR", str(PROJECT_ROOT / "data")))
        if self.workspace_id:
            return base / "workspaces" / self.workspace_id
        return base
    
    @property
    def database_path(self) -> Path:
        """Return database path for current workspace."""
        return self.data_dir / "questions.db"
    
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
