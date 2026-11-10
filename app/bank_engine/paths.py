"""题库引擎 v2 的路径口径：schema 来自插件包，数据库落在当前工作区。"""

from __future__ import annotations

from pathlib import Path

from app.core.config import PROJECT_ROOT, plugins_dir, settings

PLUGIN_ID = "org.jiuzhang.bank-engine"
ENGINE_DB_FILENAME = f"{PLUGIN_ID}.v2.db"
SCHEMA_VERSION = 8


def schema_path() -> Path:
    # 开发工作树以仓库根插件源码为准；发行包（根 plugins 已迁入工作区）用安装副本。
    source = PROJECT_ROOT / "plugins" / PLUGIN_ID / "bank" / "schema.sql"
    if source.is_file():
        return source
    return plugins_dir() / PLUGIN_ID / "bank" / "schema.sql"


def engine_db_path() -> Path:
    return Path(settings.data_dir) / "banks" / ENGINE_DB_FILENAME
