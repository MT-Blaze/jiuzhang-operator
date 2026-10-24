"""当前工作区备份的数据层：一致性快照与 manifest。

边界（军令 #17 + #18 第五步 / #18-终 阶段二）：
- 只认「当前工作区」；不自动备份、不联网；
- SQLite 一律走 backup API 生成自包含快照，绝不直接复制 .db 主文件，
  也不把 -wal / -shm 边车原样装包（边车语义已经并入快照）；
- **插件代码与工作区状态要进包**（#18-终 阶段二）：``data/workspaces/<id>/plugins/`` 的代码目录
  与 ``plugin_state.json`` / ``startup.json`` / ``bank_provider.json`` / ``update_state.json``
  以 ``ws/`` 前缀收录，恢复时只覆盖**当前工作区**自己那一份；其他工作区的目录一概不碰；
  版本库与缓存目录（``.git`` / ``__pycache__`` / ``node_modules`` 之类）不是插件代码，不打包；
- 凭据文件（``.env`` / ``backup.json``）绝不进包——备份里可以有代码与数据，不能有钥匙；
- manifest 描述快照里的全部文件，供恢复页做勾选。

本模块不碰 HTTP、不做压缩、不写 UI；打包与上传见同目录其它模块。
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import sqlite3
import tarfile
import tempfile
from compression import zstd
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator

from app.core.config import plugins_dir, root_data_dir, settings, workspace_storage_dir

MANIFEST_VERSION = 1
SQLITE_MAGIC = b"SQLite format 3\x00"
WORKSPACE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")

BACKUP_STEM_RE = re.compile(r"^(\d{8}_\d{6}_\d{3})$")
BACKUP_FILE_RE = re.compile(r"^backup_(\d{8}_\d{6}_\d{3})\.zst$")
MANIFEST_FILE_RE = re.compile(r"^manifest_(\d{8}_\d{6}_\d{3})\.json$")

# 不属于「当前工作区数据」的宿主级文件：备份既不打包它们，恢复也不碰。
GLOBAL_FILES = {
    ".local_token",
    "workspaces.json",
    "plugin_state.json",
    "plugin_index_cache.json",
    "startup.json",
    "bank_provider.json",
    "backup_settings.json",
    "deletion_audit.json",
    "update_state.json",
}
# 凭据文件可以备份到本机以外？不。它只属于本机配置，绝不进包。
SECRET_FILES = {"backup.json", ".env"}
# 宿主级路由/账本文件：装在数据根上，描述的却是「本机现在开哪个区、谁还能写」。
# 进包等于把别的机器的指针盖回来，恢复它足以把工作区切走——打包与恢复两头都禁。
# 打包侧漏一个名字，恢复侧就会把整包判废，所以这张表与 GLOBAL_FILES 同处维护。
HOST_ONLY_FILES = SECRET_FILES | {
    ".local_token",
    "workspaces.json",
    "deletion_audit.json",
    "current_workspace",
}
# 工作区目录里不属于「业务数据」的代码/宿主目录：插件代码由军令 #18 第五步
# 单独按 manifest 收录，这里先整目录跳过，避免把插件包当普通文件扫进快照。
WORKSPACE_SKIP_DIRS = {"workspaces", "backups", "audit", "plugins"}
SIDECAR_SUFFIXES = (".db-wal", ".db-shm", ".db-journal")

# ---------- 工作区覆盖层：配置 + 插件代码（军令 #18-终 阶段二） ----------
# 覆盖层文件住在 data/workspaces/<id>/（default 也一样），而 default 的**数据**住在根 data/，
# 两套根不一样。快照里用 ws/ 前缀标出「这是覆盖层的文件」，恢复时据此挑落点，
# 保证包里的 plugins/ 只会落回当前工作区自己那份。
OVERLAY_PREFIX = "ws/"
OVERLAY_PLUGINS_PREFIX = OVERLAY_PREFIX + "plugins/"
OVERLAY_STATE_FILES = (
    "plugin_state.json",
    "startup.json",
    "bank_provider.json",
    "update_state.json",
)
# 版本库、缓存与虚拟环境不是插件代码，卷进包里只会让备份变大且恢复无用。
PLUGIN_SKIP_DIRS = {
    ".git", ".svn", ".hg", "__pycache__", ".pytest_cache", ".mypy_cache",
    "node_modules", ".venv", "venv", ".idea",
}
PLUGIN_SKIP_SUFFIXES = (".pyc", ".pyo", ".tmp")
PLUGIN_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{2,80}$")
PLUGIN_FILE_LIMIT = 3000   # 单包插件文件上限：正常插件十几到几十个文件，超了说明卷进了缓存目录


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
    """凭据与开关落点：data/workspaces/<ws_id>/backup.json（含 default）。"""
    ws_id = workspace_id or current_workspace_id()
    if not WORKSPACE_ID_RE.fullmatch(ws_id):
        raise BackupError("工作区 ID 非法")
    root = root_data_dir().resolve()
    path = (root / "workspaces" / ws_id / "backup.json").resolve()
    if root not in path.parents:
        raise BackupError("备份配置路径越界")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sqlite(path: Path) -> bool:
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


def overlay_plugins_dir(workspace_id: str | None = None) -> Path:
    """该区插件代码目录。

    ``JZO_PLUGINS_DIR`` 是探针与便携部署的显式指路口子，只对**当前工作区**生效——
    备份必须跟着底座实际加载的那一份代码走，否则探针对里跑出来的环境会备出一份空包。
    """
    ws_id = workspace_id or current_workspace_id()
    override = os.environ.get("JZO_PLUGINS_DIR", "").strip()
    if override and ws_id == current_workspace_id():
        return Path(override).resolve()
    return overlay_dir(ws_id) / "plugins"


def overlay_rel(path: Path, workspace_id: str | None = None) -> str:
    """覆盖层文件的快照内路径：插件带 ``ws/plugins/``，状态文件带 ``ws/``。"""
    resolved = Path(path).resolve()
    plugins_root = overlay_plugins_dir(workspace_id)
    try:
        return OVERLAY_PLUGINS_PREFIX + resolved.relative_to(plugins_root).as_posix()
    except ValueError:
        pass
    return OVERLAY_PREFIX + resolved.relative_to(overlay_dir(workspace_id)).as_posix()


def overlay_target(relative: str, workspace_id: str | None = None) -> Path:
    """``ws/...`` → 本机落点；越界与非覆盖层路径一律拒。"""
    if not isinstance(relative, str) or not relative.startswith(OVERLAY_PREFIX):
        raise BackupError("不是覆盖层路径")
    tail = relative[len(OVERLAY_PREFIX):]
    if not tail or tail.startswith("/"):
        raise BackupError("覆盖层路径非法")
    if tail.startswith("plugins/"):
        root = overlay_plugins_dir(workspace_id)
        target = (root / tail[len("plugins/"):]).resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise BackupError("插件恢复目标越界") from exc
        return target
    root = overlay_dir(workspace_id)
    target = (root / tail).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise BackupError("配置恢复目标越界") from exc
    return target


def iter_overlay_files(workspace_id: str | None = None) -> list[Path]:
    """列出该区的工作区状态文件与插件代码文件（绝对路径，按快照内路径排序）。"""
    ws_id = workspace_id or current_workspace_id()
    root = overlay_dir(ws_id)
    found: list[tuple[str, Path]] = []
    for name in OVERLAY_STATE_FILES:
        path = root / name
        if path.is_file() and name not in SECRET_FILES:
            found.append((OVERLAY_PREFIX + name, path.resolve()))
    plugins_root = overlay_plugins_dir(ws_id)
    if plugins_root.is_dir():
        for base, dirs, files in os.walk(plugins_root):
            dirs[:] = sorted(name for name in dirs if name not in PLUGIN_SKIP_DIRS and not name.startswith("."))
            for name in sorted(files):
                if name.startswith(".") or name.lower().endswith(PLUGIN_SKIP_SUFFIXES):
                    continue
                if name.endswith(SIDECAR_SUFFIXES) or _skip_name(name):
                    continue
                path = Path(base) / name
                try:
                    resolved = path.resolve()
                    resolved.relative_to(plugins_root.resolve())
                except (OSError, ValueError):
                    continue
                if resolved.is_file():
                    found.append((overlay_rel(resolved, ws_id), resolved))
    if len(found) > PLUGIN_FILE_LIMIT:
        raise BackupError(f"覆盖层文件超过 {PLUGIN_FILE_LIMIT} 个，已拒绝打包（疑似卷进缓存目录）")
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


def _jsonable(value: Any) -> Any:
    if isinstance(value, bytes):
        return {"__bytes__": base64.b64encode(value).decode("ascii")}
    return value


def sqlite_snapshot(source: Path, target: Path) -> None:
    """用 SQLite backup API 落一份自包含快照（自动带上 WAL 里已提交的内容）。"""
    target.parent.mkdir(parents=True, exist_ok=True)
    src = sqlite3.connect(f"file:{source.as_posix()}?mode=ro", uri=True, timeout=15.0)
    try:
        dst = sqlite3.connect(target, timeout=15.0)
        try:
            src.backup(dst)
            dst.commit()
        finally:
            dst.close()
    finally:
        src.close()


def snapshot_workspace(workspace_id: str | None = None, stage_dir: Path | None = None) -> tuple[Path, dict[str, Any]]:
    """生成一致快照与 manifest；调用方负责 stage_dir 的生命周期。

    返回 ``(stage_dir, manifest)``。manifest 的 ``package.sha256`` 此时为空，
    由打包模块在写完成品后回填。
    """
    ws_id = workspace_id or current_workspace_id()
    root = workspace_dir(ws_id)
    if not root.is_dir():
        raise BackupError("当前工作区目录不存在")
    stage = Path(stage_dir) if stage_dir else Path(tempfile.mkdtemp(prefix="jzo-backup-"))
    stage.mkdir(parents=True, exist_ok=True)
    for rel, source in backup_file_plan(ws_id):
        target = stage / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix.lower() == ".db" and _is_sqlite(source):
            sqlite_snapshot(source, target)
        else:
            shutil.copy2(source, target)
    manifest = build_manifest(ws_id, stage)
    return stage, manifest


@contextmanager
def workspace_snapshot(workspace_id: str | None = None) -> Iterator[tuple[Path, dict[str, Any]]]:
    stage, manifest = snapshot_workspace(workspace_id)
    try:
        yield stage, manifest
    finally:
        shutil.rmtree(stage, ignore_errors=True)


def _select_bank_db(stage: Path) -> Path | None:
    """挑出当前工作区的题库库：活跃 provider 优先，其次任意 banks/*.db。"""
    wanted = ""
    try:
        from app.core import bank_provider

        wanted = bank_provider.resolve().get("plugin_id") or ""
    except Exception:  # noqa: BLE001 - 发现层异常不该阻断备份
        wanted = ""
    if wanted:
        candidate = stage / "banks" / f"{wanted}.db"
        if candidate.is_file():
            return candidate
    for candidate in sorted((stage / "banks").glob("*.db")):
        if candidate.is_file():
            return candidate
    host_db = stage / "jiuzhang.db"
    if host_db.is_file():
        return host_db
    return None


def _has_questions(path: Path) -> bool:
    try:
        con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=10.0)
    except sqlite3.Error:
        return False
    try:
        row = con.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='questions'"
        ).fetchone()
        return row is not None
    except sqlite3.Error:
        return False
    finally:
        con.close()


def question_hashes(db_path: Path) -> tuple[int, dict[str, str], int]:
    """返回 (题目数, {题目 id: 规范化行哈希}, user_version)。

    行哈希按 PRAGMA table_info 的列序取全字段，JSON 键排序后求 SHA-256，
    任何一次复算都必须得到同一串；不依赖 SELECT * 的偶然列序。
    """
    con = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True, timeout=10.0)
    try:
        user_version = int(con.execute("PRAGMA user_version").fetchone()[0])
        if not _has_table(con, "questions"):
            return 0, {}, user_version
        columns = [row[1] for row in con.execute("PRAGMA table_info(questions)")]
        rows = con.execute("SELECT * FROM questions ORDER BY id").fetchall()
        hashes: dict[str, str] = {}
        for row in rows:
            payload = {column: _jsonable(row[index]) for index, column in enumerate(columns)}
            canonical = json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            hashes[str(row[columns.index("id")])] = hashlib.sha256(canonical).hexdigest()
        return len(rows), hashes, user_version
    finally:
        con.close()


def _has_table(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _digest_rows(rows: list[dict[str, Any]]) -> str:
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def plugins_inventory(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按插件目录汇总：id、文件数、字节数与目录摘要。

    目录摘要是对 ``[{path, sha256}]`` 排序后再求 SHA-256——任何一个文件动过，串必变；
    恢复时拿它复核整目录，比逐文件比对照多一道「清单没被篡改」的门禁。
    """
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in files:
        if item.get("category") != "plugins":
            continue
        parts = str(item["path"]).split("/")
        if len(parts) < 4 or parts[0] != "ws" or parts[1] != "plugins":
            raise BackupError(f"插件条目路径非法：{item['path']}")
        groups.setdefault(parts[2], []).append(item)
    out: list[dict[str, Any]] = []
    for plugin_id, items in sorted(groups.items()):
        if not PLUGIN_ID_RE.fullmatch(plugin_id):
            raise BackupError(f"插件目录名非法：{plugin_id}")
        out.append({
            "id": plugin_id,
            "files": len(items),
            "bytes": sum(int(item["size"]) for item in items),
            "sha256": _digest_rows(
                [{"path": item["path"], "sha256": item["sha256"]} for item in items]
            ),
        })
    return out


def build_manifest(workspace_id: str, stage_dir: Path) -> dict[str, Any]:
    """从快照目录生成 manifest（package 哈希留空，等打包后回填）。

    ``manifest_version`` 仍是 1：阶段二只往 ``files`` 里**新增** ``ws/`` 条目与 ``plugins`` 汇总，
    旧包在新底座照样能验能恢复，不需要破坏性的版本号跳变。
    """
    stage = Path(stage_dir)
    files: list[dict[str, Any]] = []
    for path in sorted(stage.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(stage).as_posix()
        if path.name.endswith(SIDECAR_SUFFIXES):
            continue
        category, required = category_of(rel)
        files.append({
            "path": rel,
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "category": category,
            "required": required,
        })
    images = [
        {"path": item["path"], "size": item["size"], "sha256": item["sha256"]}
        for item in files if item["category"] == "uploads"
    ]
    images_digest = _digest_rows(images)

    bank = _select_bank_db(stage)
    question_count = 0
    hashes: dict[str, str] = {}
    user_version = 0
    library: dict[str, Any] = {"plugin_id": "", "path": "", "sha256": "", "user_version": 0}
    if bank is not None and _has_questions(bank):
        question_count, hashes, user_version = question_hashes(bank)
        rel_bank = bank.relative_to(stage).as_posix()
        library = {
            "plugin_id": bank.stem,
            "path": rel_bank,
            "sha256": sha256_file(bank),
            "user_version": user_version,
        }

    return {
        "manifest_version": MANIFEST_VERSION,
        "workspace_id": workspace_id,
        "schema_version": user_version,
        "library": library,
        "question_count": question_count,
        "question_hashes": hashes,
        "images": images,
        "images_hash": images_digest,
        "plugins": plugins_inventory(files),
        "files": files,
        "generated_at": now_iso(),
        "host_version": _host_version(),
        "package": {
            "filename": "",
            "sha256": "",
            "size": 0,
        },
    }


def _host_version() -> str:
    try:
        from app import __version__

        return str(__version__)
    except Exception:  # noqa: BLE001 - 版本号只作附注
        return ""


def verify_manifest_hashes(manifest: dict[str, Any], root: Path) -> list[str]:
    """按 manifest 复核目录里的文件；返回不匹配的清单（空表示全过）。

    ``root`` 是快照/解包临时区：那里 ``ws/`` 就是真子目录，不映射到本机工作区。
    """
    problems: list[str] = []
    for item in manifest.get("files") or []:
        path = (Path(root) / str(item.get("path") or "")).resolve()
        try:
            path.relative_to(Path(root).resolve())
        except ValueError:
            problems.append(f"{item.get('path')}: 路径越界")
            continue
        if not path.is_file():
            problems.append(f"{item.get('path')}: 文件缺失")
            continue
        if path.stat().st_size != int(item.get("size") or 0):
            problems.append(f"{item.get('path')}: 大小不符")
            continue
        if sha256_file(path) != item.get("sha256"):
            problems.append(f"{item.get('path')}: 哈希不符")
            continue
    return problems


def manifest_question_hashes_ok(manifest: dict[str, Any], db_path: Path) -> bool:
    """逐题哈希可复算：给定库重算后必须与 manifest 完全一致。"""
    count, hashes, _ = question_hashes(db_path)
    return count == int(manifest.get("question_count") or 0) and hashes == (
        manifest.get("question_hashes") or {}
    )


# ---------- Zstd 打包与本地备份 ----------

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


def package_snapshot(
    stage_dir: Path,
    manifest: dict[str, Any],
    out_dir: Path,
    stamp: str | None = None,
) -> dict[str, Any]:
    """把快照目录打成 ``backup_<stamp>.zst``（tar 流经 zstd 压缩）并写同名 manifest。

    **只装 manifest 点名的文件**：读一份 WAL 库会在同目录落下 ``-wal``/``-shm`` 边车，
    早先「整目录 rglob」的写法会把边车一起装进包，而 manifest 里没有它们，
    恢复侧的「清单外文件」门禁当场判废——整个包一份都恢复不出来。
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = stamp or stamp_now()
    if not BACKUP_STEM_RE.fullmatch(stamp):
        raise BackupError("备份时间戳格式非法")
    stage = Path(stage_dir).resolve()
    listed = [str(item["path"]) for item in (manifest.get("files") or [])]
    if not listed:
        raise BackupError("清单里没有任何文件，已拒绝打包")
    for rel in sorted(listed):
        path = (stage / rel).resolve()
        try:
            path.relative_to(stage)
        except ValueError as exc:
            raise BackupError(f"清单路径越界：{rel}") from exc
        if not path.is_file():
            raise BackupError(f"快照缺少文件：{rel}")
    package_path = out / f"backup_{stamp}.zst"
    manifest_path = out / f"manifest_{stamp}.json"
    temp_path = out / f".backup_{stamp}.part"
    try:
        with zstd.ZstdFile(temp_path, "wb", level=10) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for rel in sorted(listed):
                    archive.add(
                        stage / rel,
                        arcname=rel,
                        recursive=False,
                    )
        temp_path.replace(package_path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        package_path.unlink(missing_ok=True)
        raise
    manifest = dict(manifest)
    manifest["package"] = {
        "filename": package_path.name,
        "sha256": sha256_file(package_path),
        "size": package_path.stat().st_size,
    }
    temp_manifest = out / f".manifest_{stamp}.part"
    temp_manifest.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    temp_manifest.replace(manifest_path)
    return {"package": package_path, "manifest_path": manifest_path, "manifest": manifest}


def create_local_backup(
    workspace_id: str | None = None,
    local_dir: str | os.PathLike[str] | None = None,
    keep: int = 3,
) -> dict[str, Any]:
    """生成一次本地备份，并按保留策略清理旧份。返回给前端的结果不含凭据。"""
    ws_id = workspace_id or current_workspace_id()
    out = validate_local_dir(local_dir, ws_id) if local_dir else validate_local_dir(
        load_backup_settings(ws_id).get("local_dir"), ws_id
    )
    with workspace_snapshot(ws_id) as (stage, manifest):
        result = package_snapshot(stage, manifest, out)
    deleted = prune_local_backups(out, keep=keep)
    return {
        "ok": True,
        "workspace_id": ws_id,
        "local_dir": str(out),
        "package": str(result["package"]),
        "package_name": result["package"].name,
        "manifest": str(result["manifest_path"]),
        "package_sha256": result["manifest"]["package"]["sha256"],
        "package_size": result["manifest"]["package"]["size"],
        "question_count": result["manifest"]["question_count"],
        "generated_at": result["manifest"]["generated_at"],
        "pruned": [path.name for path in deleted],
    }


def prune_local_backups(directory: str | os.PathLike[str], keep: int = 3) -> list[Path]:
    """只删本工具命名的 backup_*.zst / manifest_*.json，保留最近 keep 份。"""
    folder = Path(directory)
    if not folder.is_dir():
        return []
    keep = max(1, int(keep))
    backups = sorted(
        (path for path in folder.iterdir() if path.is_file() and BACKUP_FILE_RE.match(path.name)),
        key=lambda path: path.name,
        reverse=True,
    )
    kept_stems = {BACKUP_FILE_RE.match(path.name).group(1) for path in backups[:keep]}
    deleted: list[Path] = []
    for path in backups[keep:]:
        try:
            path.unlink()
            deleted.append(path)
        except OSError:
            continue
    for path in folder.iterdir():
        if not path.is_file():
            continue
        match = MANIFEST_FILE_RE.match(path.name)
        if match and match.group(1) not in kept_stems:
            try:
                path.unlink()
                deleted.append(path)
            except OSError:
                continue
    return deleted


def list_local_backups(
    directory: str | os.PathLike[str] | None = None,
    workspace_id: str | None = None,
) -> list[dict[str, Any]]:
    """列出本地备份（按时间倒序），只读 manifest，不拆包。"""
    ws_id = workspace_id or current_workspace_id()
    folder = Path(directory) if directory else Path(
        load_backup_settings(ws_id).get("local_dir") or default_local_dir(ws_id)
    )
    if not folder.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for package in sorted(folder.iterdir(), key=lambda path: path.name, reverse=True):
        match = BACKUP_FILE_RE.match(package.name) if package.is_file() else None
        if not match:
            continue
        stem = match.group(1)
        manifest_path = folder / f"manifest_{stem}.json"
        entry: dict[str, Any] = {
            "stem": stem,
            "package": package.name,
            "package_size": package.stat().st_size,
            "manifest": manifest_path.name,
            "ok": False,
            "error": "",
        }
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry["ok"] = True
            entry["workspace_id"] = manifest.get("workspace_id", "")
            entry["question_count"] = manifest.get("question_count", 0)
            entry["generated_at"] = manifest.get("generated_at", "")
            entry["package_sha256"] = (manifest.get("package") or {}).get("sha256", "")
            entry["file_count"] = len(manifest.get("files") or [])
            entry["image_count"] = len(manifest.get("images") or [])
            entry["plugin_count"] = len(manifest.get("plugins") or [])
        except (OSError, ValueError) as exc:
            entry["error"] = str(exc)
        entries.append(entry)
    return entries


def load_local_backup_manifest(
    stem: str,
    directory: str | os.PathLike[str] | None = None,
    workspace_id: str | None = None,
) -> tuple[dict[str, Any], Path]:
    """按 stem 读取本地 manifest 与包路径；stem 先过白名单，防路径拼接。"""
    if not isinstance(stem, str) or not BACKUP_STEM_RE.fullmatch(stem):
        raise BackupError("备份标识非法")
    ws_id = workspace_id or current_workspace_id()
    folder = Path(directory) if directory else Path(
        load_backup_settings(ws_id).get("local_dir") or default_local_dir(ws_id)
    )
    manifest_path = folder / f"manifest_{stem}.json"
    package_path = folder / f"backup_{stem}.zst"
    if not manifest_path.is_file() or not package_path.is_file():
        raise BackupError("该备份不存在或缺少包文件")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BackupError(f"manifest 无法读取：{exc}") from exc
    return manifest, package_path


# ---------- 本机备份配置（开关、路径、WebDAV 凭据） ----------

def default_backup_settings(workspace_id: str | None = None) -> dict[str, Any]:
    ws_id = workspace_id or current_workspace_id()
    return {
        "local_enabled": False,
        "webdav_enabled": False,
        "local_dir": str(default_local_dir(ws_id)),
        "url": "",
        "username": "",
        "password": "",
        "remote_dir": "jiuzhang-backups",
        "last_upload": {},
    }


def load_backup_settings(workspace_id: str | None = None) -> dict[str, Any]:
    ws_id = workspace_id or current_workspace_id()
    defaults = default_backup_settings(ws_id)
    path = backup_settings_path(ws_id)
    if not path.is_file():
        return defaults
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaults
    if not isinstance(raw, dict):
        return defaults
    for key in ("url", "username", "password", "remote_dir", "local_dir"):
        if isinstance(raw.get(key), str):
            defaults[key] = raw[key].strip() if key != "password" else raw[key]
    defaults["local_enabled"] = bool(raw.get("local_enabled"))
    defaults["webdav_enabled"] = bool(raw.get("webdav_enabled")) and defaults["local_enabled"]
    if isinstance(raw.get("last_upload"), dict):
        defaults["last_upload"] = raw["last_upload"]
    if not defaults["local_dir"]:
        defaults["local_dir"] = str(default_local_dir(ws_id))
    return defaults


def save_backup_settings(values: dict[str, Any], workspace_id: str | None = None) -> dict[str, Any]:
    ws_id = workspace_id or current_workspace_id()
    current = load_backup_settings(ws_id)
    if isinstance(values.get("last_upload"), dict):
        current["last_upload"] = values["last_upload"]
    for key in ("url", "username", "remote_dir", "local_dir"):
        if key in values and isinstance(values[key], str):
            current[key] = values[key].strip()
    if isinstance(values.get("password"), str) and values["password"] != "••••••••":
        current["password"] = values["password"]
    if "local_dir" in values:
        current["local_dir"] = str(validate_local_dir(values.get("local_dir"), ws_id))
    local_off = "local_enabled" in values and not bool(values["local_enabled"])
    if "local_enabled" in values:
        current["local_enabled"] = bool(values["local_enabled"])
    if "webdav_enabled" in values:
        current["webdav_enabled"] = bool(values["webdav_enabled"])
    if local_off:
        # 用户亲手关掉本地备份：网盘一起关，绝不允许「无本地文件可传」的空转开关。
        current["webdav_enabled"] = False
    else:
        current = normalize_toggles(current)
    path = backup_settings_path(ws_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
    return current


def record_upload_result(result: dict[str, Any], workspace_id: str | None = None) -> dict[str, Any]:
    ws_id = workspace_id or current_workspace_id()
    current = load_backup_settings(ws_id)
    current["last_upload"] = dict(result)
    path = backup_settings_path(ws_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)
    return current


def normalize_toggles(values: dict[str, Any]) -> dict[str, Any]:
    """网盘备份依赖本地备份；关掉本地时网盘必须一起关。"""
    result = dict(values)
    result["local_enabled"] = bool(result.get("local_enabled"))
    result["webdav_enabled"] = bool(result.get("webdav_enabled"))
    if result["webdav_enabled"]:
        result["local_enabled"] = True
    if not result["local_enabled"]:
        result["webdav_enabled"] = False
    return result


def public_backup_settings(values: dict[str, Any]) -> dict[str, Any]:
    """给前端的视图：密码只报「有没有」，绝不回明文。"""
    out = dict(values)
    password = str(out.pop("password", "") or "")
    out["password_set"] = bool(password)
    out["password_masked"] = "••••••••" if password else ""
    out.pop("last_upload", None)
    return out
