"""全局配置。所有路径以仓库根目录为锚点，不依赖当前工作目录。"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings:
    project_root: Path = PROJECT_ROOT
    static_dir: Path = PROJECT_ROOT / "static"
    schemas_dir: Path = PROJECT_ROOT / "schemas"
    plugins_dir: Path = PROJECT_ROOT / "plugins"
    data_dir: Path = Path(os.environ.get("JZO_DATA_DIR", str(PROJECT_ROOT / "data")))
    host: str = os.environ.get("JZO_HOST", "127.0.0.1")
    port: int = int(os.environ.get("JZO_PORT", "8000"))


settings = Settings()
