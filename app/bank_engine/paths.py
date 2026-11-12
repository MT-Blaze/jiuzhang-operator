"""题库引擎 v2 的路径口径：schema 来自插件包，数据库落在当前工作区。"""

from __future__ import annotations

from pathlib import Path

from app.core.config import plugin_source_root, plugins_dir, settings

PLUGIN_ID = "org.jiuzhang.bank-engine"
ENGINE_DB_FILENAME = f"{PLUGIN_ID}.v2.db"
SCHEMA_VERSION = 14


def schema_path() -> Path:
    # 开发工作树以兄弟插件仓库的源码为准；发行包（源码不在底座仓）用工作区安装副本。
    source_root = plugin_source_root()
    if source_root is not None:
        source = source_root / PLUGIN_ID / "bank" / "schema.sql"
        if source.is_file():
            return source
    return plugins_dir() / PLUGIN_ID / "bank" / "schema.sql"


def engine_db_path() -> Path:
    return Path(settings.data_dir) / "banks" / ENGINE_DB_FILENAME
