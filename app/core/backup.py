"""当前工作区备份子系统：对外接口（组合根）。

实现在同目录四块里，按「谁管什么」切分（PLUGIN_SPEC §2.8 同款口径，Python 侧同理）：

- ``backup_files.py``    —— 路径、命名、白/黑名单与文件计划：什么该进包、什么绝不；
- ``backup_manifest.py`` —— 一致性快照与 manifest：SQLite backup API、逐题哈希、目录摘要；
- ``backup_package.py``  —— 成品层：压缩打包、本地保留策略、清单读取；
- ``backup_settings.py`` —— 本机配置：开关、本地目录、WebDAV 凭据（凭据绝不进包）。

本文件只做一件事：把这四块的对外名字汇总成「备份子系统」这一个入口，
调用方（``app/api/settings.py``、``app/core/restore.py``、``app/core/webdav.py``、测试）
一律 ``from app.core import backup``，不需要知道里面切了几刀、以后还会切几刀。

边界与禁令写在 ``backup_files.py`` 的模块文档里，这里不重复。
"""

from __future__ import annotations

from app.core.config import root_data_dir
from app.core.backup_files import (
    BACKUP_FILE_RE,
    BACKUP_STEM_RE,
    GLOBAL_FILES,
    HOST_ONLY_FILES,
    MANIFEST_FILE_RE,
    OVERLAY_PLUGINS_PREFIX,
    OVERLAY_PREFIX,
    OVERLAY_STATE_FILES,
    PLUGIN_ID_RE,
    SECRET_FILES,
    SIDECAR_SUFFIXES,
    SQLITE_MAGIC,
    WORKSPACE_ID_RE,
    WORKSPACE_SKIP_DIRS,
    BackupError,
    backup_file_plan,
    backup_settings_path,
    category_of,
    current_workspace_id,
    default_local_dir,
    is_sqlite,
    iter_overlay_files,
    iter_workspace_files,
    now_iso,
    overlay_dir,
    overlay_rel,
    overlay_target,
    sha256_file,
    stamp_now,
    validate_local_dir,
    workspace_dir,
)
from app.core.backup_manifest import (
    MANIFEST_VERSION,
    build_manifest,
    manifest_question_hashes_ok,
    plugins_inventory,
    question_hashes,
    select_bank_db,
    snapshot_workspace,
    sqlite_snapshot,
    verify_manifest_hashes,
    workspace_snapshot,
)
from app.core.backup_package import (
    create_local_backup,
    list_local_backups,
    load_local_backup_manifest,
    package_snapshot,
    prune_local_backups,
)
from app.core.backup_settings import (
    default_backup_settings,
    load_backup_settings,
    normalize_toggles,
    public_backup_settings,
    record_upload_result,
    save_backup_settings,
)

__all__ = [
    # 常量与命名
    "BACKUP_FILE_RE", "BACKUP_STEM_RE", "GLOBAL_FILES", "HOST_ONLY_FILES",
    "MANIFEST_FILE_RE", "MANIFEST_VERSION", "OVERLAY_PLUGINS_PREFIX", "OVERLAY_PREFIX",
    "OVERLAY_STATE_FILES", "PLUGIN_ID_RE", "SECRET_FILES", "SIDECAR_SUFFIXES", "SQLITE_MAGIC",
    "WORKSPACE_ID_RE", "WORKSPACE_SKIP_DIRS", "BackupError",
    # 路径与清单
    "backup_file_plan", "backup_settings_path", "category_of", "current_workspace_id",
    "default_local_dir", "is_sqlite", "iter_overlay_files", "iter_workspace_files",
    "now_iso", "overlay_dir", "overlay_rel", "overlay_target",
    "root_data_dir", "sha256_file", "stamp_now", "validate_local_dir", "workspace_dir",
    # 快照与 manifest
    "build_manifest", "manifest_question_hashes_ok", "plugins_inventory",
    "question_hashes", "select_bank_db", "snapshot_workspace", "sqlite_snapshot",
    "verify_manifest_hashes", "workspace_snapshot",
    # 成品层
    "create_local_backup", "list_local_backups", "load_local_backup_manifest",
    "package_snapshot", "prune_local_backups",
    # 本机配置
    "default_backup_settings", "load_backup_settings", "normalize_toggles",
    "public_backup_settings", "record_upload_result", "save_backup_settings",
]
