"""备份子系统的「路径与文件清单」层：什么该进包、什么绝不。

边界（军令 #17 + #18 + #34）：
- 只认「当前工作区」；不自动备份、不联网；
- 凭据文件（``.env`` / ``backup.toml``）绝不进包——备份里可以有数据，不能有钥匙；
- 宿主级路由/账本文件（``workspaces.toml`` / ``current_workspace`` 等）进包等于把别的机器的
  指针盖回来，恢复它足以把工作区切走，打包与恢复两头都禁；
- **插件代码不进包**（#34 插件全局化）：插件代码全机只有一份，与工作区数据无关；
  工作区的 ``plugin_state.toml`` / ``startup.toml`` / ``bank_provider.toml`` /
  ``update_state.toml`` 仍以 ``ws/`` 前缀收录，恢复时只覆盖**当前工作区**自己那一份；
- 版本库与缓存目录（``.git`` / ``__pycache__`` / ``node_modules`` 之类）不进包。

本模块只算路径与清单，不碰 SQLite、不做压缩、不写配置。
"""

from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.core.config import plugins_dir, root_data_dir, settings, workspace_storage_dir

SQLITE_MAGIC = b"SQLite format 3\x00"
WORKSPACE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")

BACKUP_STEM_RE = re.compile(r"^(\d{8}_\d{6}_\d{3})$")
BACKUP_FILE_RE = re.compile(r"^backup_(\d{8}_\d{6}_\d{3})\.zst$")
MANIFEST_FILE_RE = re.compile(r"^manifest_(\d{8}_\d{6}_\d{3})\.(?:toml|json)$")

# 不属于「当前工作区数据」的宿主级文件：备份既不打包它们，恢复也不碰。
GLOBAL_FILES = {
    ".local_token",
    "workspaces.toml", "workspaces.json",
    "plugin_state.toml", "plugin_state.json",
    "plugin_index_cache.toml", "plugin_index_cache.json",
    "startup.toml", "startup.json",
    "bank_provider.toml", "bank_provider.json",
    "backup_settings.toml", "backup_settings.json",
    "deletion_audit.toml", "deletion_audit.json",
    "update_state.toml", "update_state.json",
}
# 凭据文件可以备份到本机以外？不。它只属于本机配置，绝不进包。
SECRET_FILES = {"backup.toml", "backup.json", ".env"}
# 宿主级路由/账本文件：装在数据根上，描述的却是「本机现在开哪个区、谁还能写」。
# 进包等于把别的机器的指针盖回来，恢复它足以把工作区切走——打包与恢复两头都禁。
# 打包侧漏一个名字，恢复侧就会把整包判废，所以这张表与 GLOBAL_FILES 同处维护。
HOST_ONLY_FILES = SECRET_FILES | {
    ".local_token",
    "workspaces.toml", "workspaces.json",
    "deletion_audit.toml", "deletion_audit.json",
    "current_workspace",
}
# 工作区目录里不属于「业务数据」的代码/宿主目录：旧版插件副本、备份产物与
# 工作区容器都整目录跳过。插件代码现在是全局一份，不再参与工作区备份。
WORKSPACE_SKIP_DIRS = {"workspaces", "backups", "audit", "plugins"}
SIDECAR_SUFFIXES = (".db-wal", ".db-shm", ".db-journal")

# ---------- 工作区覆盖层：仅配置状态（军令 #34） ----------
# 覆盖层文件住在 data/workspaces/<id>/（default 也一样），而 default 的**数据**住在根 data/，
# 两套根不一样。快照里用 ws/ 前缀标出「这是覆盖层的文件」，恢复时据此挑落点。
# 旧版备份里可能还有 ws/plugins/ 条目（插件代码），恢复时一律跳过并如实回报。
OVERLAY_PREFIX = "ws/"
OVERLAY_PLUGINS_PREFIX = OVERLAY_PREFIX + "plugins/"
# 覆盖层状态文件名单（插件代码不在此列：全局一份，见文件头）。
OVERLAY_STATE_FILES = (
    "plugin_state.toml", "plugin_state.json",
    "startup.toml", "startup.json",
    "bank_provider.toml", "bank_provider.json",
    "update_state.toml", "update_state.json",
)
PLUGIN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,80}$")


class BackupError(Exception):
    """备份/快照失败；message 可直接回给前端。"""


def now_iso() -> str:
    return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")


def stamp_now() -> str:
    current = datetime.now()
    return current.strftime("%Y%m%d_%H%M%S_") + f"{current.microsecond // 1000:03d}"


def current_workspace_id() -> str:
    return settings.workspace_id or "default"


def workspace_dir(workspace_id: str | None = None) -> Path:
    """工作区数据根；default 就是 root data 目录。"""
    ws_id = workspace_id or current_workspace_id()
    if not WORKSPACE_ID_RE.fullmatch(ws_id):
        raise BackupError("工作区 ID 非法")
    root = root_data_dir().resolve()
    target = root if ws_id == "default" else root / "workspaces" / ws_id
    resolved = target.resolve()
    if resolved != root and root not in resolved.parents:
        raise BackupError("工作区路径越界")
    return resolved


def backup_settings_path(workspace_id: str | None = None) -> Path:
    """凭据与开关落点：data/workspaces/<ws_id>/backup.toml（含 default）。"""
    ws_id = workspace_id or current_workspace_id()
    if not WORKSPACE_ID_RE.fullmatch(ws_id):
        raise BackupError("工作区 ID 非法")
    root = root_data_dir().resolve()
    path = (root / "workspaces" / ws_id / "backup.toml").resolve()
    if root not in path.parents:
        raise BackupError("备份配置路径越界")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_sqlite(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return handle.read(len(SQLITE_MAGIC)) == SQLITE_MAGIC
    except OSError:
        return False


def _skip_name(name: str) -> bool:
    lower = name.lower()
    if lower in GLOBAL_FILES or lower in HOST_ONLY_FILES:
        return True
    if lower.endswith(".pre-restore.bak") or lower.endswith(".tmp"):
        return True
    if BACKUP_FILE_RE.match(name) or MANIFEST_FILE_RE.match(name):
        return True
    return False


def iter_workspace_files(workspace_id: str | None = None) -> list[Path]:
    """扫描当前工作区的数据文件（绝对路径，已按相对路径排序）。

    跳过：宿主级状态文件、凭据文件、备份产物自身、SQLite 边车、
    default 根下的 workspaces/backups/audit 与 plugins 等代码目录。
    """
    root = workspace_dir(workspace_id)
    if not root.is_dir():
        return []
    skip_dirs = set(WORKSPACE_SKIP_DIRS)
    found: list[Path] = []
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(
            name for name in dirs
            if name not in skip_dirs and not name.startswith(".")
        )
        for name in sorted(files):
            if _skip_name(name):
                continue
            if name.endswith(SIDECAR_SUFFIXES):
                continue
            path = Path(base) / name
            try:
                resolved = path.resolve()
                resolved.relative_to(root)
            except (OSError, ValueError):
                continue
            if resolved.is_file():
                found.append(resolved)
    return found


def _relative(path: Path, workspace_id: str | None = None) -> str:
    return path.relative_to(workspace_dir(workspace_id)).as_posix()


def overlay_dir(workspace_id: str | None = None) -> Path:
    """工作区覆盖层根：``data/workspaces/<id>``（default 同口径，与业务数据根不同）。"""
    ws_id = workspace_id or current_workspace_id()
    if not WORKSPACE_ID_RE.fullmatch(ws_id):
        raise BackupError("工作区 ID 非法")
    root = root_data_dir().resolve()
    target = workspace_storage_dir(ws_id).resolve()
    if root not in target.parents:
        raise BackupError("工作区配置路径越界")
    return target


def overlay_rel(path: Path, workspace_id: str | None = None) -> str:
    """覆盖层状态文件的快照内路径：一律 ``ws/<名字>``。"""
    return OVERLAY_PREFIX + Path(path).resolve().relative_to(overlay_dir(workspace_id)).as_posix()


def overlay_target(relative: str, workspace_id: str | None = None) -> Path:
    """``ws/...`` → 本机落点；越界与旧插件代码路径一律拒。"""
    if not isinstance(relative, str) or not relative.startswith(OVERLAY_PREFIX):
        raise BackupError("不是覆盖层路径")
    tail = relative[len(OVERLAY_PREFIX):]
    if not tail or tail.startswith("/"):
        raise BackupError("覆盖层路径非法")
    if tail.startswith("plugins/"):
        raise BackupError("插件代码已全局化，工作区备份不再恢复插件目录")
    root = overlay_dir(workspace_id)
    target = (root / tail).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise BackupError("配置恢复目标越界") from exc
    return target


def iter_overlay_files(workspace_id: str | None = None) -> list[Path]:
    """列出该区的工作区状态文件（绝对路径，按快照内路径排序）。"""
    ws_id = workspace_id or current_workspace_id()
    root = overlay_dir(ws_id)
    found: list[tuple[str, Path]] = []
    for name in OVERLAY_STATE_FILES:
        path = root / name
        if path.is_file() and name not in SECRET_FILES:
            found.append((OVERLAY_PREFIX + name, path.resolve()))
    found.sort(key=lambda pair: pair[0])
    return [path for _, path in found]


def backup_file_plan(workspace_id: str | None = None) -> list[tuple[str, Path]]:
    """本次备份的完整文件计划：``[(快照内相对路径, 绝对路径), ...]``。"""
    ws_id = workspace_id or current_workspace_id()
    pairs = [(_relative(path, ws_id), path) for path in iter_workspace_files(ws_id)]
    pairs += [(overlay_rel(path, ws_id), path) for path in iter_overlay_files(ws_id)]
    seen = {rel for rel, _ in pairs}
    if len(seen) != len(pairs):
        raise BackupError("快照内路径冲突，已拒绝备份")
    return sorted(pairs, key=lambda pair: pair[0])


def category_of(relative: str) -> tuple[str, bool]:
    """返回 (分组, 是否必选)。题库与图片资产必选，其他文件默认勾选但可取消。"""
    if relative.startswith(OVERLAY_PLUGINS_PREFIX):
        # 插件代码可以只恢复数据不动代码——老师可能刚手动装了新版本。
        return "plugins", False
    if relative.endswith(".db"):
        return "bank", True
    if relative == "uploads" or relative.startswith("uploads/"):
        return "uploads", True
    return "other", False


def default_local_dir(workspace_id: str | None = None) -> Path:
    return root_data_dir().resolve() / "backups" / (workspace_id or current_workspace_id())


def validate_local_dir(value: str | os.PathLike[str] | None, workspace_id: str | None = None) -> Path:
    """校验并准备本地备份目录：必须是绝对路径、可写，且不得落在 plugins/ 内。"""
    raw = str(value or "").strip()
    target = Path(os.path.expandvars(os.path.expanduser(raw))) if raw else default_local_dir(workspace_id)
    if not target.is_absolute():
        raise BackupError("本地备份地址必须是绝对路径")
    try:
        resolved = target.resolve()
    except OSError as exc:
        raise BackupError(f"本地备份地址无法解析：{exc}") from exc
    plugins_root = plugins_dir().resolve()
    if resolved == plugins_root or plugins_root in resolved.parents:
        raise BackupError("本地备份地址不得落在 plugins/ 目录内")
    try:
        resolved.mkdir(parents=True, exist_ok=True)
        probe = resolved / ".jzo-write-probe"
        probe.write_bytes(b"ok")
        probe.unlink()
    except OSError as exc:
        raise BackupError(f"本地备份目录不可写：{exc}") from exc
    return resolved
