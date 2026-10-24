"""插件卸载：删代码目录；可选地连本地数据一起物理销毁。

两种口径（军令 v0.8.0 任务 2.2、#18-续4 修订）：
- 保留数据：只删 ``plugins/<id>/`` 代码目录；当前工作区的物理 ``.db`` 原样留下，
  以后重装同名插件即恢复取数。
- 彻底删除：代码目录 + **当前工作区**里该插件的物理库（含 WAL/SHM/journal 边车）
  一并销毁，不可恢复——所以前端务必二次确认并给红色警告。

**绝不跨工作区**（军令 #18-续4）：其他工作区的 ``.db`` 是老师各自的财产，卸载当前区
的插件不能连坐。``uploads/`` 是工作区级扁平命名空间，文件不带插件标记，无法可靠归属，
因此这里一律不删（宁可多留，不可误毁老师的图）。

安全：插件 id 必须先过格式校验；只在本底座 plugins_dir 与当前工作区 data_dir 之内操作，
绝不接受外部路径；被删路径必须落在对应根目录内（防穿越）。
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

from app.core.config import plugins_dir, settings

_PLUGIN_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,80}$")
_DB_SIDECAR_SUFFIXES = (".db-shm", ".db-wal", ".db-journal")


class PluginUninstallError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


def _validate_id(plugin_id: str) -> str:
    if not isinstance(plugin_id, str) or not _PLUGIN_ID.fullmatch(plugin_id):
        raise PluginUninstallError("插件 ID 非法")
    return plugin_id


def _is_within(child: Path, root: Path) -> bool:
    try:
        child.relative_to(root)
        return True
    except ValueError:
        return False


def _db_family(bank_file: Path) -> list[Path]:
    """给定 a.db，收集它和它的边车兄弟（a.db-shm / -wal / -journal）。"""
    paths = [bank_file]
    for suffix in _DB_SIDECAR_SUFFIXES:
        paths.append(bank_file.with_name(bank_file.name.replace(".db", suffix)))
    return paths


def _current_workspace_bank(plugin_id: str) -> Path:
    """当前工作区里该插件的物理题库路径；其他工作区一概不碰。"""
    return Path(settings.data_dir) / "banks" / f"{plugin_id}.db"


def uninstall_plugin(plugin_id: str, *, keep_data: bool) -> dict[str, Any]:
    _validate_id(plugin_id)
    plugins_root = plugins_dir().resolve()
    plugin_dir = (plugins_root / plugin_id).resolve()
    if not _is_within(plugin_dir, plugins_root) or plugin_dir == plugins_root:
        raise PluginUninstallError("插件路径越界")

    removed_code = False
    if plugin_dir.is_dir():
        shutil.rmtree(plugin_dir)
        removed_code = True
    else:
        raise PluginUninstallError(f"插件不存在：{plugin_id}", status=404)

    removed_data: list[str] = []
    if not keep_data:
        data_root = Path(settings.data_dir).resolve()
        for path in _db_family(_current_workspace_bank(plugin_id)):
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if not _is_within(resolved, data_root):
                continue
            if resolved.is_file():
                try:
                    resolved.unlink()
                    removed_data.append(str(resolved.relative_to(data_root)))
                except OSError:
                    pass

    return {
        "id": plugin_id,
        "uninstalled": True,
        "keep_data": keep_data,
        "removed_code": removed_code,
        "removed_data": removed_data,
    }
